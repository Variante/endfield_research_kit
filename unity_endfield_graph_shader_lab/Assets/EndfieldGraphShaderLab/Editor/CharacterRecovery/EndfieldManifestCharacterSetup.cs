using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace EndfieldGraphShaderLabEditor
{
    public static partial class EndfieldManifestCharacterSetup
    {
        private const string GeneratedRoot = "Assets/EndfieldGraphShaderLab/Generated/Characters";
        private const string ViewerScenePath = GeneratedRoot + "/Scenes/CharacterRecoveryViewer.unity";
        private const string AllCharacterViewerScenePath =
            GeneratedRoot + "/Scenes/AllCharacterRecoveryViewer.unity";
        private const string FastRenderStyleScenePath =
            GeneratedRoot + "/Scenes/CharacterRenderStyleFast.unity";
        private const string FastRenderStyleCapturePlayerRelativePath =
            "Builds/CharacterRenderStyleCapture/EndfieldCharacterRenderStyleCapture.exe";
        private const string ManifestScenePath = GeneratedRoot + "/Scenes/ManifestCharacterRecovery.unity";
        private const string ViewerRootObjectName = "CharacterRecoveryViewerRoot";
        private const string HGCompatRenderPipelineAssetPath = "Assets/EndfieldGraphShaderLab/Generated/HGCompatRenderPipeline.asset";
        private const string WulfaManifestAssetPath =
            GeneratedRoot + "/Playable/Wulfa/wulfa_ui_recovery_manifest.json";
        private const string ZhuangfyManifestAssetPath =
            GeneratedRoot + "/Playable/Zhuangfy/zhuangfy_ui_recovery_manifest.json";
        private const string ZhuangfyWidget03ManifestAssetPath =
            GeneratedRoot + "/Playable/Zhuangfy/zhuangfy_ui_recovery_manifest.json";
        private const string MifuManifestAssetPath =
            GeneratedRoot + "/Playable/Mifu/mifu_ui_recovery_manifest.json";
        private const string PlayableCharacterUiCatalogAssetPath =
            GeneratedRoot + "/Catalog/playable_character_ui_catalog.json";
        private const string AllCharacterModelCatalogAssetPath =
            GeneratedRoot + "/Catalog/all_character_model_catalog.json";
        private const string PlayableCharacterManifestRoot = GeneratedRoot + "/Playable/";
        private const string NonPlayableCharacterManifestRoot =
            GeneratedRoot + "/NonPlayable/";
        private const string LegacyWulfaManifestAssetPath = WulfaManifestAssetPath;
        private const string LegacyZhuangfyManifestAssetPath = ZhuangfyManifestAssetPath;
        private const string LegacyMifuManifestAssetPath = MifuManifestAssetPath;
        private const string ReferenceBackdropMaterialPath = GeneratedRoot + "/Shared/Materials/M_ReferenceBackdrop.mat";
        private const string WhiteReferenceBackdropMaterialPath = GeneratedRoot + "/Shared/Materials/M_ReferenceBackdropWhite.mat";
        private const string RecoveredCharInfoSkyMaterialPath =
            GeneratedRoot + "/Shared/Materials/M_RecoveredCharInfoSky.mat";
        private const long CharacterNprSkinShaderPathId = 4484747192473637154L;
        private const long CharacterNprClothShaderPathId = -7822190029627442914L;
        private const long WulfaBodySkinMaterialPathId = 7152188194418193687L;
        private const long ZhuangfyBodySkinMaterialPathId = -6228499253811589790L;
        private const long EndminfBodySkinMaterialPathId = -8084013477027282831L;
        private const long LastRiteSilkStockingsMaterialPathId = -1435421870657246405L;
        private const long CharacterNprEyeShaderPathId = -1706220712117210762L;
        private const long ZhuangfyPiaodaiVfxShaderPathId = -1430105248647086886L;
        private const long ZhuangfyPiaodaiMaterial01PathId = 4571906004733137860L;
        private const long ZhuangfyPiaodaiMaterial02PathId = 3802462879898881764L;
        private const long ZhuangfyPiaodaiMaterial03PathId = 8849676924582144711L;
        private const string ZhuangfyPiaodaiRecoveredShaderName =
            "Endfield/Recovered/VFXBaseV2SampleStack";
        private const string ZhuangfyPiaodaiSceneMVTag =
            "ExactSelectedPiaodaiThree";
        private const string ZhuangfyPiaodaiEffectRootPath =
            "RecoveredProps/P_fxui_zhuangfy_ui_overview_start_01_piaodai";
        private const string ZhuangfyPiaodaiRendererPath =
            ZhuangfyPiaodaiEffectRootPath +
            "/GameObject/Mesh_all/lod0/S_item_widget_zhuangfy_03_lod0";
        private const string ZhuangfyPiaodaiClipName =
            "A_fx_ui_zhuangfy_ui_overview_start_01_piaodai";
        private const string EyeBrowForwardContractAssetPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/RenderParameters/eye_brow_forward_contract.json";
        private const string ReferenceBackdropObjectName = "ReferenceBackdrop";
        private const int PreviewRenderWidth = 2048;
        private const int PreviewRenderHeight = 1900;
        private const int PlayableCharInfoPreviewRenderWidth = 1920;
        private const int PlayableCharInfoPreviewRenderHeight = 1080;
        private const int RuntimeReferenceRenderWidth = 3840;
        private const int RuntimeReferenceRenderHeight = 2160;
        private const float CharacterLineupHorizontalSpacing = 3.5f;
        private const int HighestMeshLod = 0;
        private const float PreviewNearClip = 0.05f;
        private const float PreviewFieldOfView = 32f;
        private const float PreviewReferenceVerticalCoverage = 0.64f;
        private const float PreviewReferenceTopBias = 0.50f;
        private const float PreviewAnimationSampleNormalizedTime = 0.42f;
        private const float ItemWidgetPreviewMinimumVisibleScale = 0.01f;
        private const int ItemWidgetPreviewMaximumScanSamples = 4097;
        // All-roster captures frame the full finite actor bounds. Multiplying
        // the limiting half-extent by 1.08 leaves a stable eight-percent margin
        // regardless of whether the vertical or horizontal FOV is limiting.
        private const float PlayablePreviewFrameMargin = 1.08f;
        private const float PlayablePreviewMinimumBoundsSpan = 0.01f;
        private const int PlayablePreviewValidationGrid = 128;
        private const float PlayablePreviewMinimumLuminanceRange = 4f / 255f;
        private const float PlayablePreviewMinimumColorRange = 4f / 255f;
        private const float PlayablePreviewMinimumLuminanceStdDev = 0.001f;
        private const float PlayablePreviewMinimumForegroundFraction = 0.002f;
        private const float PreviewKeyIntensity = 0.55f;
        private const string FittedCompositorTranslationEnvironmentVariable =
            "ENDFIELD_REFERENCE_FITTED_COMPOSITOR_TRANSLATION";
        private const string ComparisonCameraEnvironmentVariable =
            "ENDFIELD_COMPARISON_CAMERA_JSON";
        private const string ComparisonLightingActorEnvironmentVariable =
            "ENDFIELD_COMPARISON_LIGHTING_ACTOR";
        private const string ApproximateOperatorLightingEnvironmentVariable =
            "ENDFIELD_REFERENCE_APPROXIMATE_OPERATOR_LIGHTING";
        private const string RecoveredClusteredNprLightLoopEnvironmentVariable =
            "ENDFIELD_RECOVERED_CLUSTERED_NPR_LIGHT_LOOP";
        private const string RecoveredLightBinningMembershipEnvironmentVariable =
            "ENDFIELD_RECOVERED_LIGHT_BINNING_MEMBERSHIP";
        private const string RecoveredIsolatedPunctualSoftShadowsEnvironmentVariable =
            "ENDFIELD_RECOVERED_ISOLATED_PUNCTUAL_SOFT_SHADOWS";
        private const string RecoveredPunctualShadowTileResolutionEnvironmentVariable =
            "ENDFIELD_RECOVERED_PUNCTUAL_SHADOW_TILE_RESOLUTION";
        private const string CumulativeCharInfoDiagnosticEnvironmentVariable =
            "ENDFIELD_RECOVERED_CHARINFO_CUMULATIVE_DIAGNOSTIC";
        private const string
            MultiCharacterShadowReverseCreationAuditEnvironmentVariable =
                "ENDFIELD_RECOVERED_MULTI_CHARACTER_SHADOW_REVERSE_CREATION_AUDIT";
        private const int CumulativeDiagnosticValidationWidth = 640;
        private const int CumulativeDiagnosticValidationHeight = 720;
        private static readonly Color PreviewAmbientColor = new Color(0.72f, 0.73f, 0.72f, 1f);
        private static readonly Color PreviewBackgroundColor = new Color(0.70f, 0.71f, 0.70f, 1f);
        private static readonly Vector3 PreviewKeyDirectionToLight = new Vector3(-0.28f, 0.78f, 0.56f).normalized;
        private static readonly Dictionary<string, Texture2D> TextureImportCache =
            new Dictionary<string, Texture2D>(StringComparer.OrdinalIgnoreCase);
        private static Dictionary<long, Dictionary<string, object>> EyeBrowForwardContracts;
        private static readonly string[] WulfaPreviewClipPreference =
        {
            "A_actor_wulfa_ui_overview_loop_01",
            "A_actor_wulfa_ui_overview_start_01",
            "A_actor_wulfa_uiteam_idle_01",
            "A_actor_wulfa_relax_loop",
            "A_actor_wulfa_t_pose",
            "A_actor_wulfa_dialog_state_observe_loop",
        };
        private static readonly string[] ZhuangfyPreviewClipPreference =
        {
            "A_actor_zhuangfy_ui_overview_loop_01",
            "A_actor_zhuangfy_uiteam_idle01",
            "A_actor_zhuangfy_relax_loop",
            "A_actor_zhuangfy_t_pose",
            "A_actor_zhuangfy_dialog_single_touch_high",
        };
        private static readonly string[] MifuPreviewClipPreference =
        {
            "A_actor_mifu_dialog_virtual_single_idle_talklefthand1",
            "A_actor_mifu_dialog_virtual_single_idle_nod",
            "A_actor_mifu_walk_loop_u",
            "A_actor_mifu_t_pose",
        };

        public sealed class ManifestCharacterSpec
        {
            public readonly string ManifestAssetPath;
            public readonly string PrefabAssetPath;
            public readonly string RootName;
            public readonly string DisplayName;
            public readonly Vector3 SceneOffset;
            public readonly bool Active;
            public readonly string[] PreviewClipPreference;
            public readonly bool IncludeVariants;

            public ManifestCharacterSpec(
                string manifestAssetPath,
                string rootName,
                string displayName,
                Vector3 sceneOffset,
                bool active,
                string[] previewClipPreference,
                bool includeVariants,
                string prefabAssetPath = "")
            {
                ManifestAssetPath = manifestAssetPath;
                PrefabAssetPath = prefabAssetPath;
                RootName = rootName;
                DisplayName = displayName;
                SceneOffset = sceneOffset;
                Active = active;
                PreviewClipPreference = previewClipPreference;
                IncludeVariants = includeVariants;
            }
        }

        [Serializable]
        private sealed class PlayableCharacterPreviewRenderRecord
        {
            public string display = "";
            public string root = "";
            public string manifest = "";
            public string prefab = "";
            public string png = "";
            public string clip = "";
            public float sample;
            public float sample_seconds;
            public int eligible_renderer_count;
            public float bounds_size_x;
            public float bounds_size_y;
            public float bounds_size_z;
            public bool validation_finite;
            public bool validation_passed;
            public int validation_sample_count;
            public float validation_luminance_min;
            public float validation_luminance_max;
            public float validation_luminance_stddev;
            public float validation_color_range;
            public float validation_foreground_fraction;
            public string status = "pending";
            public string error = "";
        }

        [Serializable]
        private sealed class PlayableCharacterPreviewRenderManifest
        {
            public int schema_version = 3;
            public string status = "running";
            public string scene = ViewerScenePath;
            public string catalog = PlayableCharacterUiCatalogAssetPath;
            public string output_directory = "";
            public int width = PlayableCharInfoPreviewRenderWidth;
            public int height = PlayableCharInfoPreviewRenderHeight;
            public string camera_source =
                "installed-game CharInfo vcam_overview + centered Composer LookAt";
            public string presentation_source =
                "installed-game HGCharacterVolume modifier and overview light group; optional installed-game portrait disabled for model-only capture";
            public int character_count;
            public int attempted;
            public int succeeded;
            public int failed;
            public int pending;
            public string error = "";
            public PlayableCharacterPreviewRenderRecord[] renders =
                Array.Empty<PlayableCharacterPreviewRenderRecord>();
        }

        [Serializable]
        private sealed class PlayableItemWidgetRendererSample
        {
            public string name = "";
            public string path = "";
            public string root_bone = "";
            public string isolated_png = "";
            public string exclusion_png = "";
            public bool enabled;
            public bool active;
            public float root_bone_position_x;
            public float root_bone_position_y;
            public float root_bone_position_z;
            public float root_bone_lossy_scale_x;
            public float root_bone_lossy_scale_y;
            public float root_bone_lossy_scale_z;
            public float bounds_center_x;
            public float bounds_center_y;
            public float bounds_center_z;
            public float bounds_size_x;
            public float bounds_size_y;
            public float bounds_size_z;
        }

        [Serializable]
        private sealed class PlayableItemWidgetPreviewRecord
        {
            public string display = "";
            public string root = "";
            public string prefab = "";
            public string png = "";
            public string body_clip = "";
            public float sample = PreviewAnimationSampleNormalizedTime;
            public float body_sample_seconds;
            public string sample_evidence = "fixed_42_percent_fallback";
            public bool sample_fallback_used = true;
            public float sample_interval_normalized_start = -1f;
            public float sample_interval_normalized_end = -1f;
            public float sample_interval_seconds_start = -1f;
            public float sample_interval_seconds_end = -1f;
            public int sample_scan_count;
            public string[] sample_overlap_renderer_paths = Array.Empty<string>();
            public string[] prop_paths = Array.Empty<string>();
            public string[] widget_clips = Array.Empty<string>();
            public string[] activation_evidence = Array.Empty<string>();
            public PlayableItemWidgetRendererSample[] widget_renderers =
                Array.Empty<PlayableItemWidgetRendererSample>();
            public PlayableItemWidgetRendererSample[] body_accessory_renderers =
                Array.Empty<PlayableItemWidgetRendererSample>();
            public int eligible_renderer_count;
            public bool validation_finite;
            public bool validation_passed;
            public int validation_sample_count;
            public float validation_luminance_min;
            public float validation_luminance_max;
            public float validation_luminance_stddev;
            public float validation_color_range;
            public float validation_foreground_fraction;
            public string status = "pending";
            public string error = "";
        }

        private sealed class ItemWidgetDiagnosticSampleSelection
        {
            public float normalized = PreviewAnimationSampleNormalizedTime;
            public bool fallbackUsed = true;
            public string evidence = "fixed_42_percent_fallback";
            public float intervalNormalizedStart = -1f;
            public float intervalNormalizedEnd = -1f;
            public int scanCount;
            public string[] overlapRendererPaths = Array.Empty<string>();
            public Dictionary<SkinnedMeshRenderer, bool> sourceEnabledPropRendererVisibility =
                new Dictionary<SkinnedMeshRenderer, bool>();
        }

        [Serializable]
        private sealed class PlayableItemWidgetPreviewManifest
        {
            public int schema_version = 3;
            public string status = "running";
            public string scene = ViewerScenePath;
            public string catalog = PlayableCharacterUiCatalogAssetPath;
            public string output_directory = "";
            public int width = PreviewRenderWidth;
            public int height = PreviewRenderHeight;
            public float sample = PreviewAnimationSampleNormalizedTime;
            public int source_bound_character_count;
            public int succeeded;
            public int failed;
            public PlayableItemWidgetPreviewRecord[] renders =
                Array.Empty<PlayableItemWidgetPreviewRecord>();
        }

        private static ManifestCharacterSpec[] SharedViewerCharacters()
        {
            ManifestCharacterSpec[] playableCharacters = PlayableCatalogCharacters();
            foreach (ManifestCharacterSpec character in playableCharacters)
            {
                string manifestPath = Path.Combine(
                    Directory.GetCurrentDirectory(),
                    character.ManifestAssetPath);
                if (File.Exists(manifestPath))
                    return playableCharacters;
            }
            return LegacySharedViewerCharacters();
        }

        private static ManifestCharacterSpec[] PlayableCatalogCharacters()
        {
            return CatalogCharacters(
                PlayableCharacterUiCatalogAssetPath,
                PlayableCharacterManifestRoot,
                "Playable character",
                enforceActorClassRoots: false);
        }

        private static ManifestCharacterSpec[] AllCharacterCatalogCharacters()
        {
            return CatalogCharacters(
                AllCharacterModelCatalogAssetPath,
                PlayableCharacterManifestRoot,
                "All-character",
                enforceActorClassRoots: true);
        }

        private static ManifestCharacterSpec[] CatalogCharacters(
            string catalogAssetPath,
            string allowedManifestRoot,
            string catalogLabel,
            bool enforceActorClassRoots)
        {
            string catalogPath = Path.Combine(
                Directory.GetCurrentDirectory(),
                catalogAssetPath);
            if (!File.Exists(catalogPath))
                return Array.Empty<ManifestCharacterSpec>();

            var catalog = Dict(ManifestMiniJson.Deserialize(
                File.ReadAllText(catalogPath, Encoding.UTF8)));
            var result = new List<ManifestCharacterSpec>();
            foreach (object characterObj in List(
                catalog.TryGetValue("characters", out object charactersObj)
                    ? charactersObj
                    : null))
            {
                var character = Dict(characterObj);
                bool importEnabled = !character.TryGetValue(
                    "import_enabled",
                    out object importEnabledObj) || Bool(importEnabledObj);
                if (!importEnabled)
                    continue;

                string manifestAssetPath = Str(
                    character.TryGetValue("manifest_asset_path", out object manifestObj)
                        ? manifestObj
                        : null).Replace('\\', '/');
                string prefabAssetPath = Str(
                    character.TryGetValue("prefab_asset_path", out object prefabObj)
                        ? prefabObj
                        : null).Replace('\\', '/');
                string rootName = Str(
                    character.TryGetValue("root_name", out object rootObj)
                        ? rootObj
                        : null);
                string displayName = Str(
                    character.TryGetValue("display_name", out object displayObj)
                        ? displayObj
                        : null,
                    rootName);
                string entryAllowedRoot = allowedManifestRoot;
                if (enforceActorClassRoots)
                {
                    string actorClass = Str(
                        character.TryGetValue("actor_class", out object actorClassObj)
                            ? actorClassObj
                            : null);
                    entryAllowedRoot = string.Equals(
                            actorClass,
                            "playable",
                            StringComparison.OrdinalIgnoreCase)
                        ? PlayableCharacterManifestRoot
                        : NonPlayableCharacterManifestRoot;
                }
                if (!manifestAssetPath.StartsWith(
                        entryAllowedRoot,
                        StringComparison.OrdinalIgnoreCase) ||
                    !manifestAssetPath.EndsWith(".json", StringComparison.OrdinalIgnoreCase))
                {
                    throw new InvalidOperationException(
                        $"{catalogLabel} catalog manifest path is outside its generated " +
                        $"root: {manifestAssetPath}");
                }
                if (!prefabAssetPath.StartsWith(
                        entryAllowedRoot,
                        StringComparison.OrdinalIgnoreCase) ||
                    !prefabAssetPath.EndsWith(".prefab", StringComparison.OrdinalIgnoreCase))
                {
                    throw new InvalidOperationException(
                        $"{catalogLabel} catalog prefab path is outside its generated " +
                        $"root: {prefabAssetPath}");
                }
                if (rootName.Length == 0)
                    throw new InvalidOperationException(
                        $"{catalogLabel} catalog entry has no root_name: {manifestAssetPath}");

                var previewPreference = new List<string>();
                foreach (object preferenceObj in List(
                    character.TryGetValue(
                        "preview_clip_preference",
                        out object preferenceListObj)
                            ? preferenceListObj
                            : null))
                {
                    string preference = Str(preferenceObj);
                    if (preference.Length > 0)
                        previewPreference.Add(preference);
                }
                result.Add(new ManifestCharacterSpec(
                    manifestAssetPath,
                    rootName,
                    displayName,
                    Vector3.zero,
                    Bool(character.TryGetValue("active", out object activeObj) ? activeObj : false),
                    previewPreference.ToArray(),
                    includeVariants: false,
                    prefabAssetPath: prefabAssetPath));
            }
            int activeCount = 0;
            foreach (ManifestCharacterSpec character in result)
            {
                if (character.Active)
                    activeCount++;
            }
            if (result.Count > 0 && activeCount != 1)
            {
                throw new InvalidOperationException(
                    $"{catalogLabel} catalog must mark exactly one enabled actor active; " +
                    $"found {activeCount} across {result.Count} enabled entries.");
            }
            return result.ToArray();
        }

        private static ManifestCharacterSpec[] LegacySharedViewerCharacters()
        {
            return new[]
            {
                new ManifestCharacterSpec(
                    ResolveManifestAssetPath(WulfaManifestAssetPath, LegacyWulfaManifestAssetPath),
                    "Wulfa",
                    "Wulfa",
                    Vector3.zero,
                    true,
                    WulfaPreviewClipPreference,
                    includeVariants: false),
                new ManifestCharacterSpec(
                    ResolveManifestAssetPath(ZhuangfyManifestAssetPath, LegacyZhuangfyManifestAssetPath),
                    "Zhuangfy",
                    "Zhuangfy",
                    Vector3.zero,
                    false,
                    ZhuangfyPreviewClipPreference,
                    includeVariants: false),
                new ManifestCharacterSpec(
                    ResolveManifestAssetPath(MifuManifestAssetPath, LegacyMifuManifestAssetPath),
                    "Mifu",
                    "Mifu",
                    Vector3.zero,
                    false,
                    MifuPreviewClipPreference,
                    includeVariants: false),
            };
        }

        [MenuItem("Endfield/Character Recovery Lab/Refresh Recovered Character Materials")]
        public static void RefreshRecoveredCharacterMaterials()
        {
            EnsureFolders();
            TextureImportCache.Clear();
            int manifestCount = 0;
            int materialCount = 0;
            var existingGuids = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

            // Texture reprofiling must be as GUID-stable as the material-only
            // refresh. Several shipped data maps share bytes across aliases,
            // so replacing assets instead of reimporting them in place would
            // silently break generated material references.
            foreach (string guid in AssetDatabase.FindAssets(
                "t:Texture2D",
                new[] { GeneratedRoot }))
            {
                string assetPath = AssetDatabase.GUIDToAssetPath(guid);
                existingGuids[assetPath] = guid;
            }

            foreach (ManifestCharacterSpec character in SharedViewerCharacters())
            {
                string manifestPath = Path.Combine(
                    Directory.GetCurrentDirectory(),
                    character.ManifestAssetPath);
                if (!File.Exists(manifestPath))
                    continue;

                var manifest = Dict(ManifestMiniJson.Deserialize(
                    File.ReadAllText(manifestPath, Encoding.UTF8)));
                string actorPrefix = Str(
                    manifest.TryGetValue("model", out object modelObj) ? modelObj : null,
                    character.RootName);
                string actorGeneratedRoot = ActorGeneratedRoot(
                    character.ManifestAssetPath,
                    character.RootName);
                EnsureActorFolders(actorGeneratedRoot, clearGeneratedAssets: false);

                foreach (string guid in AssetDatabase.FindAssets(
                    "t:Material",
                    new[] { $"{actorGeneratedRoot}/Materials" }))
                {
                    string assetPath = AssetDatabase.GUIDToAssetPath(guid);
                    existingGuids[assetPath] = guid;
                }

                Dictionary<string, Material> refreshed = BuildMaterials(
                    Dict(manifest["materials"]),
                    actorPrefix,
                    actorGeneratedRoot);
                manifestCount++;
                materialCount += refreshed.Count;
            }

            // Repair every generated texture, including assets not reached by
            // the active material manifests. Filename classification first
            // removes AnimeStudio's _p<hash> identity suffix, so normal,
            // packed, mask, and ramp profiles are deterministic.
            ApplyGeneratedTextureImportProfiles();
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            foreach (var pair in existingGuids)
            {
                string guidAfter = AssetDatabase.AssetPathToGUID(pair.Key);
                if (!string.Equals(pair.Value, guidAfter, StringComparison.OrdinalIgnoreCase))
                {
                    throw new InvalidOperationException(
                        $"Material/texture refresh changed an existing GUID: {pair.Key} {pair.Value} -> {guidAfter}");
                }
            }

            Debug.Log(
                $"Recovered character material refresh complete: manifests={manifestCount} " +
                $"materials={materialCount}; existing material/texture GUIDs preserved.");
        }

        public static void RefreshSelectedPlayableCharacterMaterials()
        {
            EnsureFolders();
            TextureImportCache.Clear();
            ManifestCharacterSpec[] selected = FilterPreviewCharacters(
                PlayableCatalogCharacters());
            if (selected.Length == 0)
                throw new InvalidOperationException(
                    "ENDFIELD_PREVIEW_ACTORS selected no playable characters.");

            int materialCount = 0;
            foreach (ManifestCharacterSpec character in selected)
            {
                var manifest = Dict(ManifestMiniJson.Deserialize(File.ReadAllText(
                    Path.Combine(Directory.GetCurrentDirectory(), character.ManifestAssetPath),
                    Encoding.UTF8)));
                string actorPrefix = Str(
                    manifest.TryGetValue("model", out object modelObj) ? modelObj : null,
                    character.RootName);
                string actorRoot = ActorGeneratedRoot(
                    character.ManifestAssetPath,
                    character.RootName);
                EnsureActorFolders(actorRoot, clearGeneratedAssets: false);
                materialCount += BuildMaterials(
                    Dict(manifest["materials"]),
                    actorPrefix,
                    actorRoot).Count;
            }
            ApplyGeneratedTextureImportProfiles(
                selected.Select(CharacterGeneratedAssetRoot).ToArray());
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log(
                $"Targeted character material refresh complete: actors={selected.Length}, " +
                $"materials={materialCount}.");
        }

        public static void BuildSharedViewer()
        {
            BuildCharacterViewer(
                SharedViewerCharacters(),
                ViewerScenePath,
                allowMissingPresentationProfiles: false,
                preserveExistingGeneratedAssets: false,
                previewFileName: "character_recovery_viewer.png",
                viewerLabel: "Shared character viewer");
        }

        private static void BuildCharacterViewer(
            ManifestCharacterSpec[] viewerCharacters,
            string scenePath,
            bool allowMissingPresentationProfiles,
            bool preserveExistingGeneratedAssets,
            string previewFileName,
            string viewerLabel,
            bool neutralWhiteBackground = false)
        {
            EnsureFolders();
            EnsureHGCompatRenderPipelineAssigned();
            TextureImportCache.Clear();
            Dictionary<string, CharacterRecoveryPresentationProfile>
                presentationProfiles =
                    EndfieldPlayableCharInfoProfileBuilder.BuildAllProfiles();

            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            ViewerSceneLayout layout = CreateViewerSceneLayout();

            ActorBuildResult activeActor = null;
            var builtActors = new List<ActorBuildResult>();
            bool releaseInactiveSceneInstances =
                viewerCharacters.Length > 3 && AllCharacterManifestsExist(viewerCharacters);
            foreach (ManifestCharacterSpec character in viewerCharacters)
            {
                string manifestPath = Path.Combine(Directory.GetCurrentDirectory(), character.ManifestAssetPath);
                if (!File.Exists(manifestPath))
                {
                    Debug.LogWarning($"Skipping missing character manifest: {character.ManifestAssetPath}");
                    continue;
                }

                bool active = character.Active && activeActor == null;
                bool preserveExisting = preserveExistingGeneratedAssets &&
                    character.PrefabAssetPath.StartsWith(
                        PlayableCharacterManifestRoot,
                        StringComparison.OrdinalIgnoreCase) &&
                    AssetDatabase.LoadAssetAtPath<GameObject>(
                        character.PrefabAssetPath) != null;
                ActorBuildResult actor = preserveExisting
                    ? InstantiateExistingActor(character, active)
                    : BuildActor(
                        character.ManifestAssetPath,
                        character.RootName,
                        character.DisplayName,
                        character.SceneOffset,
                        active,
                        character.PreviewClipPreference,
                        character.IncludeVariants);
                builtActors.Add(actor);
                actor.Root.transform.SetParent(layout.CharactersRoot, true);
                if (active)
                    activeActor = actor;
                else if (releaseInactiveSceneInstances)
                {
                    UnityEngine.Object.DestroyImmediate(actor.Root);
                    actor.Root = null;
                }
            }

            if (activeActor == null && builtActors.Count > 0)
            {
                activeActor = builtActors[0];
                activeActor.Root.SetActive(true);
            }
            if (activeActor == null)
                throw new InvalidOperationException("No character recovery manifests were found under Generated/Characters.");

            ConfigureScene(activeActor.Root, activeActor.MeshObjects, layout);
            EnsureCharacterRecoveryActorCatalog(
                layout,
                builtActors,
                presentationProfiles,
                allowMissingPresentationProfiles);
            activeActor = EnsureHorizontalCharacterLineup(
                SceneManager.GetActiveScene(),
                layout,
                builtActors,
                activeActor.RootName);
            EnsureCharacterRecoveryViewerUi(layout);
            Camera viewerCamera = Camera.main ??
                UnityEngine.Object.FindObjectOfType<Camera>(true);
            if (viewerCamera == null)
                throw new InvalidOperationException(
                    "Shared character viewer has no camera for the source-authored CharInfo portrait.");
            ConfigureOperatorReferenceLighting(
                SceneManager.GetActiveScene(),
                layout.LightingRoot,
                viewerCamera,
                activeActor.RootName,
                activeActor.Root.transform);
            EndfieldRecoveredCharInfoBackgroundPortrait portrait =
                EndfieldRecoveredCharInfoBackgroundPortraitBuilder.EnsureAndBind(
                viewerCamera,
                activeActor.Root.name,
                activeActor.Root.transform);
            EnsureOriginalStylePresentationScene(
                SceneManager.GetActiveScene());
            EnsureCharacterRecoveryPresentation(
                viewerCamera,
                portrait,
                activeActor,
                presentationProfiles);
            if (neutralWhiteBackground)
                ApplyNeutralWhiteViewerBackground(viewerCamera);

            EditorBuildSettings.scenes = new[]
            {
                new EditorBuildSettingsScene(scenePath, true),
            };
            EditorSceneManager.SaveScene(SceneManager.GetActiveScene(), scenePath);

            string previewPath = Path.GetFullPath(Path.Combine(
                Application.dataPath,
                "../../scratch/character_recovery/" + previewFileName));
            Directory.CreateDirectory(Path.GetDirectoryName(previewPath) ?? ".");
            RenderPreview(previewPath);

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();

            Debug.Log(
                $"{viewerLabel} built: actors={builtActors.Count} " +
                $"active={activeActor.Root.name} scene={scenePath}");
        }

        private static ActorBuildResult InstantiateExistingActor(
            ManifestCharacterSpec character,
            bool active)
        {
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(
                character.PrefabAssetPath);
            if (prefab == null)
            {
                throw new FileNotFoundException(
                    $"Existing character prefab is missing: {character.RootName}",
                    character.PrefabAssetPath);
            }
            GameObject root = PrefabUtility.InstantiatePrefab(
                prefab,
                SceneManager.GetActiveScene()) as GameObject;
            if (root == null)
                throw new InvalidOperationException(
                    $"Could not instantiate existing character prefab: {character.RootName}");
            root.name = character.RootName;
            root.transform.position = character.SceneOffset;
            root.transform.rotation = Quaternion.identity;
            root.transform.localScale = Vector3.one;
            root.SetActive(active);
            CharacterRecoveryRig rig = root.GetComponent<CharacterRecoveryRig>();
            if (rig == null)
                throw new InvalidDataException(
                    $"Existing character prefab has no recovery rig: {character.RootName}");
            rig.displayName = character.DisplayName;
            return new ActorBuildResult
            {
                Root = root,
                RootName = character.RootName,
                DisplayName = character.DisplayName,
                PrefabAssetPath = character.PrefabAssetPath,
                MeshObjects = root.GetComponentsInChildren<SkinnedMeshRenderer>(true)
                    .Select(renderer => renderer.gameObject)
                    .ToList(),
                Clips = new List<AnimationClip>(),
            };
        }

        public static void BuildPlayableCharacterUiViewer()
        {
            ManifestCharacterSpec[] characters = PlayableCatalogCharacters();
            if (characters.Length == 0)
            {
                throw new InvalidOperationException(
                    $"No enabled playable characters were found in {PlayableCharacterUiCatalogAssetPath}. " +
                    "Refresh the game-data catalog before running the Unity importer.");
            }

            var missing = new List<string>();
            foreach (ManifestCharacterSpec character in characters)
            {
                string manifestPath = Path.Combine(
                    Directory.GetCurrentDirectory(),
                    character.ManifestAssetPath);
                if (!File.Exists(manifestPath))
                    missing.Add(character.ManifestAssetPath);
            }
            if (missing.Count > 0)
            {
                throw new FileNotFoundException(
                    $"Playable UI import requires all {characters.Length} enabled manifests; " +
                    $"missing {missing.Count}: {string.Join(", ", missing.ToArray())}");
            }

            BuildSharedViewer();
            Debug.Log(
                $"Playable-character UI viewer complete: catalogActors={characters.Length}, " +
                $"catalog={PlayableCharacterUiCatalogAssetPath}.");
        }

        public static void BuildAllCharacterModelViewer()
        {
            ManifestCharacterSpec[] characters = AllCharacterCatalogCharacters();
            if (characters.Length == 0)
            {
                throw new InvalidOperationException(
                    $"No canonical characters were found in {AllCharacterModelCatalogAssetPath}. " +
                    "Refresh the source-derived all-character catalog first.");
            }

            var missing = new List<string>();
            foreach (ManifestCharacterSpec character in characters)
            {
                string manifestPath = Path.Combine(
                    Directory.GetCurrentDirectory(),
                    character.ManifestAssetPath);
                if (!File.Exists(manifestPath))
                    missing.Add(character.ManifestAssetPath);
            }
            if (missing.Count > 0)
            {
                throw new FileNotFoundException(
                    $"All-character import requires all {characters.Length} canonical manifests; " +
                    $"missing {missing.Count}: {string.Join(", ", missing.ToArray())}");
            }

            BuildCharacterViewer(
                characters,
                AllCharacterViewerScenePath,
                allowMissingPresentationProfiles: true,
                preserveExistingGeneratedAssets: true,
                previewFileName: "all_character_recovery_viewer.png",
                viewerLabel: "All-character resident viewer",
                neutralWhiteBackground: true);
            Debug.Log(
                $"All-character model viewer complete: catalogActors={characters.Length}, " +
                $"catalog={AllCharacterModelCatalogAssetPath}.");
        }

        [MenuItem("Endfield/Character Recovery Lab/Refresh Overview Controller Evidence")]
        public static void RefreshPlayableOverviewControllerEvidence()
        {
            int refreshed = 0;
            foreach (ManifestCharacterSpec character in PlayableCatalogCharacters())
            {
                string manifestPath = Path.Combine(
                    Directory.GetCurrentDirectory(),
                    character.ManifestAssetPath);
                if (!File.Exists(manifestPath))
                    throw new FileNotFoundException(
                        $"Playable character manifest is missing: {character.RootName}",
                        manifestPath);
                if (AssetDatabase.LoadAssetAtPath<GameObject>(character.PrefabAssetPath) == null)
                    throw new FileNotFoundException(
                        $"Playable character prefab is missing: {character.RootName}",
                        character.PrefabAssetPath);

                Dictionary<string, object> manifest = Dict(
                    ManifestMiniJson.Deserialize(
                        File.ReadAllText(manifestPath, Encoding.UTF8)));
                GameObject prefabRoot = PrefabUtility.LoadPrefabContents(
                    character.PrefabAssetPath);
                try
                {
                    ConfigureRecoveredOverviewPlayback(
                        prefabRoot,
                        manifest,
                        ActorGeneratedRoot(character.ManifestAssetPath, character.RootName));
                    PrefabUtility.SaveAsPrefabAsset(
                        prefabRoot,
                        character.PrefabAssetPath);
                    refreshed++;
                }
                finally
                {
                    PrefabUtility.UnloadPrefabContents(prefabRoot);
                }
            }

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log(
                $"Refreshed Overview controller evidence on playable prefabs: {refreshed}.");
        }

        /// <summary>
        /// Rebuilds only Zhuangfy's source-identified gacha piaodai Effect
        /// clone, its exact three materials, Timeline-baked motion/alpha clip,
        /// prefab, and viewer-scene instance. The separate Actor placeholder
        /// remains hidden and receives no recovered visibility binding.
        /// </summary>
        public static void RefreshZhuangfyPiaodaiEffectRecoveryAssets()
        {
            EnsureFolders();
            EnsureHGCompatRenderPipelineAssigned();

            string manifestAssetPath = ResolveManifestAssetPath(
                ZhuangfyManifestAssetPath,
                LegacyZhuangfyManifestAssetPath);
            string manifestPath = Path.Combine(Directory.GetCurrentDirectory(), manifestAssetPath);
            if (!File.Exists(manifestPath))
                throw new FileNotFoundException("Zhuangfy recovery manifest is missing.", manifestPath);

            var manifest = Dict(ManifestMiniJson.Deserialize(
                File.ReadAllText(manifestPath, Encoding.UTF8)));
            var effect = Dict(
                manifest.TryGetValue("recovered_effects", out object effectObj)
                    ? effectObj
                    : null);
            if (Str(effect.TryGetValue("status", out object statusObj) ? statusObj : null) !=
                    "exact_visible_effect_clone_imported_actor_placeholder_fail_closed" ||
                Long(effect.TryGetValue("renderer_path_id", out object rendererIdObj) ? rendererIdObj : null) !=
                    -2023935448362406633L ||
                Long(effect.TryGetValue("mesh_path_id", out object meshIdObj) ? meshIdObj : null) !=
                    7201013279525401889L ||
                Long(effect.TryGetValue("shader_path_id", out object shaderIdObj) ? shaderIdObj : null) !=
                    ZhuangfyPiaodaiVfxShaderPathId)
            {
                throw new InvalidOperationException(
                    "Zhuangfy piaodai Effect identity gate did not match the exact source contract.");
            }

            var materialPathIds = List(
                effect.TryGetValue("material_path_ids", out object materialIdsObj)
                    ? materialIdsObj
                    : null);
            long[] expectedMaterialPathIds =
            {
                ZhuangfyPiaodaiMaterial01PathId,
                ZhuangfyPiaodaiMaterial02PathId,
                ZhuangfyPiaodaiMaterial03PathId,
            };
            if (materialPathIds.Count != expectedMaterialPathIds.Length)
                throw new InvalidOperationException(
                    $"Expected three ordered Zhuangfy piaodai materials, found {materialPathIds.Count}.");
            for (int i = 0; i < expectedMaterialPathIds.Length; i++)
            {
                if (Long(materialPathIds[i]) != expectedMaterialPathIds[i])
                    throw new InvalidOperationException(
                        $"Zhuangfy piaodai material slot {i} failed its exact path-ID gate.");
            }

            var effectClips = new List<object>();
            foreach (object clipObj in List(manifest["clips"]))
            {
                var clipInfo = Dict(clipObj);
                if (Str(clipInfo.TryGetValue("name", out object nameObj) ? nameObj : null) !=
                    ZhuangfyPiaodaiClipName)
                {
                    continue;
                }

                string sampleJson = Str(
                    clipInfo.TryGetValue("sample_json", out object sampleObj) ? sampleObj : null);
                if (sampleJson.Length == 0 || !File.Exists(sampleJson) ||
                    Int(clipInfo.TryGetValue("matched_transform_count", out object matchedObj) ? matchedObj : null) != 39 ||
                    Int(clipInfo.TryGetValue("missing_transform_count", out object missingObj) ? missingObj : null) != 0 ||
                    List(clipInfo.TryGetValue("bones", out object bonesObj) ? bonesObj : null).Count != 39 ||
                    List(clipInfo.TryGetValue("material_float_curves", out object curvesObj) ? curvesObj : null).Count != 1)
                {
                    throw new InvalidOperationException(
                        "Zhuangfy piaodai motion/alpha clip failed its exact sampled-curve gate.");
                }
                effectClips.Add(clipObj);
            }
            if (effectClips.Count != 1)
                throw new InvalidOperationException(
                    $"Expected one exact Zhuangfy piaodai Effect clip, found {effectClips.Count}.");

            string actorGeneratedRoot = ActorGeneratedRoot(manifestAssetPath, "Zhuangfy");
            EnsureActorFolders(actorGeneratedRoot, clearGeneratedAssets: false);
            var guidBefore = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            RememberExistingGuid(
                guidBefore,
                $"{actorGeneratedRoot}/Animations/{Safe(ZhuangfyPiaodaiClipName)}.anim");
            RememberExistingGuid(
                guidBefore,
                $"{actorGeneratedRoot}/Meshes/{Safe("S_item_widget_zhuangfy_03_lod0_p63EF236CD4FB7521")}.asset");
            foreach (long materialPathId in expectedMaterialPathIds)
            {
                RememberExistingGuid(
                    guidBefore,
                    $"{actorGeneratedRoot}/Materials/{Safe("actor_zhuangfy")}_{Safe("pathid_" + materialPathId.ToString(CultureInfo.InvariantCulture))}.mat");
            }
            RememberExistingGuid(guidBefore, $"{actorGeneratedRoot}/Prefabs/Zhuangfy.prefab");

            List<AnimationClip> rebuilt = BuildAnimationClips(
                effectClips,
                null,
                actorGeneratedRoot);
            if (rebuilt.Count != 1)
                throw new InvalidOperationException(
                    $"Zhuangfy piaodai Effect clip refresh was incomplete: rebuilt={rebuilt.Count}.");

            if (!File.Exists(Path.Combine(Directory.GetCurrentDirectory(), ViewerScenePath)))
                throw new FileNotFoundException(
                    "Build the shared character viewer scene before refreshing Zhuangfy's piaodai Effect.",
                    ViewerScenePath);
            Scene scene = EditorSceneManager.OpenScene(ViewerScenePath, OpenSceneMode.Single);
            GameObject previous = FindSceneGameObject("Zhuangfy");
            Transform previousParent = previous != null
                ? previous.transform.parent
                : FindSceneGameObject("Characters")?.transform;
            int previousSiblingIndex = previous != null ? previous.transform.GetSiblingIndex() : 0;
            bool previousActive = previous == null || previous.activeSelf;
            Vector3 previousLocalPosition = previous != null ? previous.transform.localPosition : Vector3.zero;
            Quaternion previousLocalRotation = previous != null ? previous.transform.localRotation : Quaternion.identity;
            Vector3 previousLocalScale = previous != null ? previous.transform.localScale : Vector3.one;

            ActorBuildResult actor = BuildActor(
                manifestAssetPath,
                "Zhuangfy",
                "Zhuangfy",
                Vector3.zero,
                previousActive,
                ZhuangfyPreviewClipPreference,
                includeVariants: false,
                rebuildAnimationAssets: false,
                clearGeneratedAssets: false,
                rebuildMeshAssets: false,
                rebuildMaterialAssets: true);
            if (previous != null)
                UnityEngine.Object.DestroyImmediate(previous);
            if (previousParent != null)
            {
                actor.Root.transform.SetParent(previousParent, false);
                actor.Root.transform.SetSiblingIndex(
                    Mathf.Clamp(previousSiblingIndex, 0, previousParent.childCount - 1));
            }
            actor.Root.transform.localPosition = previousLocalPosition;
            actor.Root.transform.localRotation = previousLocalRotation;
            actor.Root.transform.localScale = previousLocalScale;
            actor.Root.SetActive(previousActive);

            Transform effectRoot = actor.Root.transform.Find(ZhuangfyPiaodaiEffectRootPath);
            Transform rendererTransform = actor.Root.transform.Find(ZhuangfyPiaodaiRendererPath);
            var renderer = rendererTransform != null
                ? rendererTransform.GetComponent<SkinnedMeshRenderer>()
                : null;
            if (effectRoot == null || renderer == null || renderer.sharedMesh == null ||
                renderer.sharedMaterials.Length != 3 || renderer.enabled)
            {
                throw new InvalidOperationException(
                    "Zhuangfy piaodai Effect must build as one hidden-by-default skinned renderer with three ordered materials.");
            }
            for (int i = 0; i < expectedMaterialPathIds.Length; i++)
            {
                Material material = renderer.sharedMaterials[i];
                if (material == null || material.shader == null ||
                    HasShaderCompilationErrors(material.shader) ||
                    !string.Equals(
                        material.shader.name,
                        ZhuangfyPiaodaiRecoveredShaderName,
                        StringComparison.Ordinal) ||
                    material.renderQueue != 3700 ||
                    material.enableInstancing ||
                    material.GetTag(
                        "EndfieldSceneMVMRT",
                        false,
                        string.Empty) != ZhuangfyPiaodaiSceneMVTag ||
                    !material.HasProperty("_RecoveredLODFade") ||
                    material.GetVector("_RecoveredLODFade") !=
                        EndfieldRecoveredLodFadePacking.Disabled)
                {
                    throw new InvalidOperationException(
                        $"Zhuangfy piaodai material slot {i} did not retain the exact recovered shader/queue/LOD contract.");
                }
            }

            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene, ViewerScenePath);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            VerifyExistingGuids(guidBefore, "Zhuangfy piaodai Effect refresh");

            Debug.Log(
                "Targeted Zhuangfy piaodai Effect recovery complete: effectTransforms=44, " +
                "motionTracks=39, timelineFrames=168, skinnedRenderers=1, materialSlots=3. " +
                "Actor placeholder remains fail-closed hidden; existing GUIDs were preserved.");
        }

        /// <summary>
        /// Reopens the saved piaodai materials in a separate editor process
        /// and validates the exact non-instanced retail-disabled LOD payload.
        /// This method deliberately performs no regeneration.
        /// </summary>
        public static void ValidateZhuangfyPiaodaiEffectRecoveryAssets()
        {
            string manifestAssetPath = ResolveManifestAssetPath(
                ZhuangfyManifestAssetPath,
                LegacyZhuangfyManifestAssetPath);
            string actorGeneratedRoot = ActorGeneratedRoot(
                manifestAssetPath,
                "Zhuangfy");
            long[] materialPathIds =
            {
                ZhuangfyPiaodaiMaterial01PathId,
                ZhuangfyPiaodaiMaterial02PathId,
                ZhuangfyPiaodaiMaterial03PathId,
            };
            foreach (long materialPathId in materialPathIds)
            {
                string materialPath =
                    $"{actorGeneratedRoot}/Materials/{Safe("actor_zhuangfy")}_{Safe("pathid_" + materialPathId.ToString(CultureInfo.InvariantCulture))}.mat";
                Material material = AssetDatabase.LoadAssetAtPath<Material>(
                    materialPath);
                if (material == null || material.shader == null ||
                    !material.shader.isSupported ||
                    HasShaderCompilationErrors(material.shader) ||
                    !string.Equals(
                        material.shader.name,
                        ZhuangfyPiaodaiRecoveredShaderName,
                        StringComparison.Ordinal) ||
                    material.renderQueue != 3700 ||
                    material.enableInstancing ||
                    material.GetTag(
                        "EndfieldSceneMVMRT",
                        false,
                        string.Empty) != ZhuangfyPiaodaiSceneMVTag ||
                    !material.HasProperty("_RecoveredLODFade") ||
                    material.GetVector("_RecoveredLODFade") !=
                        EndfieldRecoveredLodFadePacking.Disabled)
                {
                    throw new InvalidOperationException(
                        $"Saved Zhuangfy piaodai material failed its fresh-editor shader/queue/LOD validation: {materialPath}");
                }
            }
            Debug.Log(
                "Fresh-editor Zhuangfy piaodai validation complete: materials=3, " +
                "instancing=disabled, recoveredLODFade=(1000,0,0,0).");
        }

        private static bool HasShaderCompilationErrors(Shader shader)
        {
            return shader != null &&
                ShaderUtil.GetShaderMessages(shader).Any(
                    message =>
                        message.severity ==
                        UnityEditor.Rendering.ShaderCompilerMessageSeverity.Error);
        }

        /// <summary>
        /// Rebuilds only the selected actor assets from their current source
        /// manifests. Existing actors keep animation/mesh GUIDs while their
        /// mesh contents are refreshed in place; actors whose prefab is still
        /// missing also receive the complete animation build needed to join
        /// the shared viewer catalog.
        /// </summary>
        public static void RefreshPlayableCharacterAssets(IEnumerable<string> actorNames)
        {
            EnsureFolders();
            EnsureHGCompatRenderPipelineAssigned();
            TextureImportCache.Clear();

            var requested = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (string actorName in actorNames ?? Array.Empty<string>())
            {
                string trimmed = (actorName ?? string.Empty).Trim();
                if (trimmed.Length > 0)
                    requested.Add(trimmed);
            }
            if (requested.Count == 0)
                throw new ArgumentException("At least one playable actor name is required.", nameof(actorNames));

            ManifestCharacterSpec[] catalog = PlayableCatalogCharacters();
            var selected = new List<ManifestCharacterSpec>();
            foreach (ManifestCharacterSpec character in catalog)
            {
                if (requested.Contains(character.RootName))
                    selected.Add(character);
            }
            foreach (string requestedActor in requested)
            {
                if (!selected.Exists(character =>
                    string.Equals(character.RootName, requestedActor, StringComparison.OrdinalIgnoreCase)))
                {
                    throw new InvalidOperationException(
                        $"Selected actor is absent from the playable catalog: {requestedActor}");
                }
            }

            int completeBuilds = 0;
            int refreshedExistingBuilds = 0;
            foreach (ManifestCharacterSpec character in selected)
            {
                string manifestPath = Path.Combine(
                    Directory.GetCurrentDirectory(),
                    character.ManifestAssetPath);
                if (!File.Exists(manifestPath))
                    throw new FileNotFoundException(
                        $"Playable character manifest is missing: {character.RootName}",
                        manifestPath);

                bool prefabMissing = AssetDatabase.LoadAssetAtPath<GameObject>(
                    character.PrefabAssetPath) == null;
                ActorBuildResult actor = BuildActor(
                    character.ManifestAssetPath,
                    character.RootName,
                    character.DisplayName,
                    Vector3.zero,
                    false,
                    character.PreviewClipPreference,
                    includeVariants: false,
                    rebuildAnimationAssets: prefabMissing,
                    clearGeneratedAssets: false,
                    // A targeted source repair can change decoded vertex or
                    // skin streams without changing the prefab.  Reusing the
                    // cached Mesh here left stale bone weights behind.  The
                    // builder copies into the existing asset, so rebuilding
                    // preserves GUIDs and prefab references.
                    rebuildMeshAssets: true,
                    rebuildMaterialAssets: true);
                if (actor?.Root != null)
                    UnityEngine.Object.DestroyImmediate(actor.Root);
                if (prefabMissing)
                    completeBuilds++;
                else
                    refreshedExistingBuilds++;
            }

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log(
                $"Targeted playable-character asset refresh complete: actors={selected.Count} " +
                $"complete={completeBuilds} refreshedExisting={refreshedExistingBuilds}; " +
                "meshes, materials, and prefabs rebuilt from current manifests.");
        }

        /// <summary>
        /// Rebuild only source-bound item-widget clips and the selected actor
        /// prefabs. Existing body clips, meshes, materials, GUIDs, and the
        /// shared viewer scene/catalog remain untouched.
        /// </summary>
        public static void RefreshPlayableWidgetAnimationAssets(IEnumerable<string> actorNames)
        {
            EnsureFolders();
            EnsureHGCompatRenderPipelineAssigned();

            var requested = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (string actorName in actorNames ?? Array.Empty<string>())
            {
                string trimmed = (actorName ?? string.Empty).Trim();
                if (trimmed.Length > 0)
                    requested.Add(trimmed);
            }
            if (requested.Count == 0)
                throw new ArgumentException("At least one playable actor name is required.", nameof(actorNames));

            ManifestCharacterSpec[] catalog = PlayableCatalogCharacters();
            var selected = new List<ManifestCharacterSpec>();
            foreach (ManifestCharacterSpec character in catalog)
            {
                if (requested.Contains(character.RootName))
                    selected.Add(character);
            }
            var missingActors = new List<string>();
            foreach (string requestedActor in requested)
            {
                if (!selected.Exists(character =>
                    string.Equals(character.RootName, requestedActor, StringComparison.OrdinalIgnoreCase)))
                {
                    missingActors.Add(requestedActor);
                }
            }
            if (missingActors.Count > 0)
                throw new InvalidOperationException(
                    "Selected widget-refresh actors are absent from the enabled playable catalog: " +
                    string.Join(", ", missingActors.ToArray()));

            int rebuiltClipCount = 0;
            var guidBefore = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            foreach (ManifestCharacterSpec character in selected)
            {
                string manifestPath = Path.Combine(
                    Directory.GetCurrentDirectory(),
                    character.ManifestAssetPath);
                if (!File.Exists(manifestPath))
                    throw new FileNotFoundException(
                        $"Playable widget-refresh manifest is missing: {character.RootName}",
                        manifestPath);

                var manifest = Dict(ManifestMiniJson.Deserialize(
                    File.ReadAllText(manifestPath, Encoding.UTF8)));
                var widgetClips = new List<object>();
                foreach (object clipObj in List(manifest["clips"]))
                {
                    var clipInfo = Dict(clipObj);
                    string layerRole = Str(
                        clipInfo.TryGetValue("layer_role", out object roleObj) ? roleObj : null);
                    if (!string.Equals(layerRole, "ui_item_widget", StringComparison.OrdinalIgnoreCase))
                        continue;
                    string name = Str(
                        clipInfo.TryGetValue("name", out object nameObj) ? nameObj : null);
                    string sampleJson = Str(
                        clipInfo.TryGetValue("sample_json", out object sampleObj) ? sampleObj : null);
                    if (name.Length == 0 || sampleJson.Length == 0 || !File.Exists(sampleJson))
                        throw new InvalidOperationException(
                            $"Widget clip has no readable original-data sample: {character.RootName}/{name}");
                    widgetClips.Add(clipObj);
                }
                if (widgetClips.Count == 0)
                    throw new InvalidOperationException(
                        $"Selected actor has no recovered widget clips: {character.RootName}");

                string actorGeneratedRoot = ActorGeneratedRoot(
                    character.ManifestAssetPath,
                    character.RootName);
                EnsureActorFolders(actorGeneratedRoot, clearGeneratedAssets: false);
                RememberExistingGuid(
                    guidBefore,
                    $"{actorGeneratedRoot}/Prefabs/{Safe(character.RootName)}.prefab");
                foreach (object clipObj in widgetClips)
                {
                    string name = Str(Dict(clipObj)["name"]);
                    RememberExistingGuid(
                        guidBefore,
                        $"{actorGeneratedRoot}/Animations/{Safe(name)}.anim");
                }

                List<AnimationClip> rebuilt = BuildAnimationClips(
                    widgetClips,
                    null,
                    actorGeneratedRoot);
                if (rebuilt.Count != widgetClips.Count)
                    throw new InvalidOperationException(
                        $"Targeted widget animation refresh was incomplete for {character.RootName}: " +
                        $"selected={widgetClips.Count} rebuilt={rebuilt.Count}.");
                rebuiltClipCount += rebuilt.Count;

                ActorBuildResult actor = BuildActor(
                    character.ManifestAssetPath,
                    character.RootName,
                    character.DisplayName,
                    Vector3.zero,
                    false,
                    character.PreviewClipPreference,
                    false,
                    rebuildAnimationAssets: false,
                    clearGeneratedAssets: false,
                    rebuildMeshAssets: false,
                    rebuildMaterialAssets: false);
                if (actor?.Root != null)
                    UnityEngine.Object.DestroyImmediate(actor.Root);
            }

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            foreach (var pair in guidBefore)
            {
                string guidAfter = AssetDatabase.AssetPathToGUID(pair.Key);
                if (!string.Equals(pair.Value, guidAfter, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException(
                        $"Targeted widget refresh changed an existing GUID: " +
                        $"{pair.Key} {pair.Value} -> {guidAfter}");
            }
            Debug.Log(
                $"Targeted playable widget refresh complete: actors={selected.Count} " +
                $"clips={rebuiltClipCount}; body clips, meshes, materials, viewer scene, and catalog untouched.");
        }

        public static void RefreshPlayableMeshAssetsCommandLine()
        {
            string raw = Environment.GetEnvironmentVariable("ENDFIELD_CHARACTER_MESH_ACTORS") ?? string.Empty;
            string[] actorNames = raw.Split(
                new[] { ',', ';', ' ', '\t', '\r', '\n' },
                StringSplitOptions.RemoveEmptyEntries);
            RefreshPlayableMeshAssets(actorNames);
        }

        /// <summary>
        /// Rebuilds source meshes and the selected actor prefabs in place while
        /// preserving existing animation, material, mesh, and prefab GUIDs.
        /// The shared catalog and viewer scene are not regenerated.
        /// </summary>
        public static void RefreshPlayableMeshAssets(IEnumerable<string> actorNames)
        {
            EnsureFolders();
            EnsureHGCompatRenderPipelineAssigned();

            var requested = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (string actorName in actorNames ?? Array.Empty<string>())
            {
                string trimmed = (actorName ?? string.Empty).Trim();
                if (trimmed.Length > 0)
                    requested.Add(trimmed);
            }
            if (requested.Count == 0)
                throw new ArgumentException("At least one playable actor name is required.", nameof(actorNames));

            ManifestCharacterSpec[] catalog = PlayableCatalogCharacters();
            var selected = new List<ManifestCharacterSpec>();
            foreach (ManifestCharacterSpec character in catalog)
            {
                if (requested.Contains(character.RootName))
                    selected.Add(character);
            }
            foreach (string requestedActor in requested)
            {
                if (!selected.Exists(character =>
                    string.Equals(character.RootName, requestedActor, StringComparison.OrdinalIgnoreCase)))
                {
                    throw new InvalidOperationException(
                        $"Selected mesh-refresh actor is absent from the enabled playable catalog: {requestedActor}");
                }
            }

            var guidBefore = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            int uniqueMeshCount = 0;
            foreach (ManifestCharacterSpec character in selected)
            {
                string manifestPath = Path.Combine(Directory.GetCurrentDirectory(), character.ManifestAssetPath);
                if (!File.Exists(manifestPath))
                    throw new FileNotFoundException(
                        $"Playable mesh-refresh manifest is missing: {character.RootName}",
                        manifestPath);

                var manifest = Dict(ManifestMiniJson.Deserialize(File.ReadAllText(manifestPath, Encoding.UTF8)));
                string actorGeneratedRoot = ActorGeneratedRoot(character.ManifestAssetPath, character.RootName);
                EnsureActorFolders(actorGeneratedRoot, clearGeneratedAssets: false);
                RememberExistingGuid(
                    guidBefore,
                    $"{actorGeneratedRoot}/Prefabs/{Safe(character.RootName)}.prefab");

                var meshAssetNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                foreach (object meshObj in List(manifest["meshes"]))
                {
                    var mesh = Dict(meshObj);
                    string name = Str(mesh.TryGetValue("name", out object nameObj) ? nameObj : null);
                    string assetName = Str(
                        mesh.TryGetValue("mesh_asset_name", out object assetNameObj) ? assetNameObj : null,
                        name);
                    if (assetName.Length == 0 || !meshAssetNames.Add(assetName))
                        continue;
                    RememberExistingGuid(guidBefore, $"{actorGeneratedRoot}/Meshes/{Safe(assetName)}.asset");
                }
                uniqueMeshCount += meshAssetNames.Count;

                ActorBuildResult actor = BuildActor(
                    character.ManifestAssetPath,
                    character.RootName,
                    character.DisplayName,
                    Vector3.zero,
                    false,
                    character.PreviewClipPreference,
                    includeVariants: false,
                    rebuildAnimationAssets: false,
                    clearGeneratedAssets: false,
                    rebuildMeshAssets: true,
                    rebuildMaterialAssets: false);
                if (actor?.Root != null)
                    UnityEngine.Object.DestroyImmediate(actor.Root);
            }

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            foreach (var pair in guidBefore)
            {
                string guidAfter = AssetDatabase.AssetPathToGUID(pair.Key);
                if (!string.Equals(pair.Value, guidAfter, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException(
                        $"Targeted mesh refresh changed an existing GUID: {pair.Key} {pair.Value} -> {guidAfter}");
            }
            Debug.Log(
                $"Targeted playable mesh refresh complete: actors={selected.Count} " +
                $"uniqueMeshes={uniqueMeshCount}; animations, materials, viewer scene, and catalog untouched.");
        }

        [MenuItem("Endfield/Character Recovery Lab/Upgrade Viewer To All Source Profiles")]
        public static void UpgradeSharedViewerToAllSourceProfiles()
        {
            EnsureHGCompatRenderPipelineAssigned();
            string sceneFullPath = Path.Combine(
                Directory.GetCurrentDirectory(),
                ViewerScenePath);
            if (!File.Exists(sceneFullPath))
            {
                BuildSharedViewer();
                return;
            }

            Dictionary<string, CharacterRecoveryPresentationProfile>
                presentationProfiles =
                    EndfieldPlayableCharInfoProfileBuilder.BuildAllProfiles();
            Scene scene = EditorSceneManager.OpenScene(
                ViewerScenePath,
                OpenSceneMode.Single);
            GameObject viewerRoot = FindSceneGameObject(ViewerRootObjectName);
            Transform charactersRoot =
                viewerRoot != null
                    ? FindDirectChild(viewerRoot.transform, "Characters")
                    : null;
            Transform lightingRoot =
                viewerRoot != null
                    ? FindDirectChild(viewerRoot.transform, "Lighting")
                    : null;
            if (viewerRoot == null || charactersRoot == null || lightingRoot == null)
                throw new InvalidDataException(
                    "Existing CharacterRecoveryViewer scene hierarchy is incomplete.");

            var layout = new ViewerSceneLayout
            {
                Root = viewerRoot,
                BackdropRoot = FindDirectChild(viewerRoot.transform, "Backdrop"),
                CharactersRoot = charactersRoot,
                LightingRoot = lightingRoot,
            };
            var actors = new List<ActorBuildResult>();
            foreach (ManifestCharacterSpec character in PlayableCatalogCharacters())
            {
                actors.Add(new ActorBuildResult
                {
                    RootName = character.RootName,
                    DisplayName = character.DisplayName,
                    PrefabAssetPath = character.PrefabAssetPath,
                });
            }
            EnsureCharacterRecoveryActorCatalog(
                layout,
                actors,
                presentationProfiles);
            string preferredActiveRootName = "";
            foreach (CharacterRecoveryRig candidate in
                     UnityEngine.Object.FindObjectsOfType<CharacterRecoveryRig>(true))
            {
                if (candidate != null &&
                    candidate.gameObject.scene == scene &&
                    candidate.gameObject.activeInHierarchy)
                {
                    preferredActiveRootName = candidate.gameObject.name;
                    break;
                }
            }
            ActorBuildResult activeActor = EnsureHorizontalCharacterLineup(
                scene,
                layout,
                actors,
                preferredActiveRootName);
            EnsureCharacterRecoveryViewerUi(layout);

            CharacterRecoveryRig activeRig =
                activeActor.Root.GetComponent<CharacterRecoveryRig>();
            if (activeRig == null)
                throw new InvalidDataException(
                    "CharacterRecoveryViewer resident lineup has no active rig.");

            Camera camera = Camera.main ??
                UnityEngine.Object.FindObjectOfType<Camera>(true);
            if (camera == null)
                throw new InvalidDataException(
                    "CharacterRecoveryViewer has no camera.");
            ConfigureOperatorReferenceLighting(
                scene,
                lightingRoot,
                camera,
                activeRig.gameObject.name,
                activeRig.transform);
            EndfieldRecoveredCharInfoBackgroundPortrait portrait =
                EndfieldRecoveredCharInfoBackgroundPortraitBuilder.EnsureAndBind(
                camera,
                activeRig.gameObject.name,
                activeRig.transform);
            EnsureOriginalStylePresentationScene(scene);
            EnsureCharacterRecoveryPresentation(
                camera,
                portrait,
                activeActor,
                presentationProfiles);

            EditorBuildSettings.scenes = new[]
            {
                new EditorBuildSettingsScene(ViewerScenePath, true),
            };
            EditorSceneManager.MarkSceneDirty(scene);
            if (!EditorSceneManager.SaveScene(scene, ViewerScenePath, false))
                throw new IOException(
                    $"Could not save upgraded viewer scene: {ViewerScenePath}");
            AssetDatabase.SaveAssets();
            Debug.Log(
                $"CharacterRecoveryViewer upgraded: catalog={actors.Count}, " +
                $"profiles={presentationProfiles.Count}, active={activeRig.gameObject.name}.");
        }

        [MenuItem("Endfield/Character Recovery Lab/Validate Resident Character Lineup")]
        public static void ValidateResidentCharacterLineupCommandLine()
        {
            Scene scene = EditorSceneManager.OpenScene(
                ViewerScenePath,
                OpenSceneMode.Single);
            GameObject viewerRoot = FindSceneGameObject(ViewerRootObjectName);
            Transform charactersRoot = viewerRoot != null
                ? FindDirectChild(viewerRoot.transform, "Characters")
                : null;
            if (charactersRoot == null)
                throw new InvalidDataException(
                    "CharacterRecoveryViewer has no Characters root.");

            CharacterRecoveryActorCatalog catalog =
                charactersRoot.GetComponent<CharacterRecoveryActorCatalog>();
            if (catalog == null || !catalog.keepAllModelsResident)
                throw new InvalidDataException(
                    "CharacterRecoveryViewer resident catalog is missing or disabled.");
            if (catalog.entries == null || catalog.entries.Length != 31)
                throw new InvalidDataException(
                    $"Expected 31 resident catalog entries; found " +
                    $"{(catalog.entries != null ? catalog.entries.Length : 0)}.");

            CharacterRecoveryActorCatalogEntry[] ordered = catalog.entries
                .OrderBy(
                    entry => string.IsNullOrEmpty(entry.displayName)
                        ? entry.rootName
                        : entry.displayName,
                    StringComparer.Ordinal)
                .ToArray();
            var rigRoots = new List<Transform>();
            for (int index = 0; index < charactersRoot.childCount; index++)
            {
                Transform child = charactersRoot.GetChild(index);
                if (child.GetComponent<CharacterRecoveryRig>() != null)
                    rigRoots.Add(child);
            }
            if (rigRoots.Count != ordered.Length)
            {
                throw new InvalidDataException(
                    $"Resident lineup rig count differs from catalog: " +
                    $"rigs={rigRoots.Count} catalog={ordered.Length}.");
            }

            int recoveredMorphBindingCount = 0;
            int recoveredEarOwnerCount = 0;
            int automaticBlinkEligibleCount = 0;
            int exactAutomaticBlinkOwnerCount = 0;
            for (int index = 0; index < ordered.Length; index++)
            {
                CharacterRecoveryActorCatalogEntry entry = ordered[index];
                Transform root = FindDirectChild(charactersRoot, entry.rootName);
                if (root == null || root.GetComponent<CharacterRecoveryRig>() == null)
                    throw new InvalidDataException(
                        $"Resident lineup actor is missing: {entry.rootName}.");
                if (!root.gameObject.activeSelf)
                    throw new InvalidDataException(
                        $"Resident lineup actor is inactive: {entry.rootName}.");
                float expectedX =
                    (index - (ordered.Length - 1) * 0.5f) *
                    CharacterLineupHorizontalSpacing;
                Vector3 expectedPosition = new Vector3(expectedX, 0f, 0f);
                if ((root.localPosition - expectedPosition).sqrMagnitude > 0.000001f)
                {
                    throw new InvalidDataException(
                        $"Resident lineup position mismatch for {entry.rootName}: " +
                        $"expected={expectedPosition} actual={root.localPosition}.");
                }
                if (root.GetSiblingIndex() != index)
                    throw new InvalidDataException(
                        $"Resident lineup sibling order mismatch for {entry.rootName}.");

                EndfieldRecoveredSkeletalMorphBasePose morphBasePose =
                    root.GetComponent<EndfieldRecoveredSkeletalMorphBasePose>();
                if (morphBasePose == null ||
                    string.IsNullOrEmpty(morphBasePose.characterId) ||
                    morphBasePose.avatarAddresses == null ||
                    morphBasePose.avatarAddresses.Length == 0 ||
                    morphBasePose.bindings == null ||
                    morphBasePose.bindings.Length == 0)
                {
                    throw new InvalidDataException(
                        $"Resident lineup actor has no recovered skeletal-morph base pose: " +
                        $"{entry.rootName}.");
                }
                var morphTargets = new HashSet<int>();
                foreach (EndfieldRecoveredSkeletalMorphBoneBinding binding in
                    morphBasePose.bindings)
                {
                    if (binding.target == null || !binding.target.IsChildOf(root))
                        throw new InvalidDataException(
                            $"Resident skeletal-morph binding escaped its owner: " +
                            $"{entry.rootName}/{binding.boneName}.");
                    if (!morphTargets.Add(binding.target.GetInstanceID()))
                        throw new InvalidDataException(
                            $"Resident skeletal-morph target is bound twice: " +
                            $"{entry.rootName}/{binding.boneName}.");
                }
                recoveredMorphBindingCount += morphBasePose.bindings.Length;
                if (morphBasePose.avatarAddresses.Length == 2)
                    recoveredEarOwnerCount++;
                if (morphBasePose.automaticBlinkEligible)
                    automaticBlinkEligibleCount++;

                EndfieldRecoveredAutomaticFacialBlink exactBlink =
                    root.GetComponent<EndfieldRecoveredAutomaticFacialBlink>();
                if (exactBlink != null)
                {
                    bool expectedOwner =
                        string.Equals(entry.rootName, "Wulfa", StringComparison.Ordinal) ||
                        string.Equals(entry.rootName, "Lizhiyan", StringComparison.Ordinal);
                    if (!expectedOwner || !exactBlink.sourceEligible ||
                        !exactBlink.automaticBlinkEnabled ||
                        exactBlink.trackerType != 10 ||
                        exactBlink.controls == null || exactBlink.controls.Length != 6)
                    {
                        throw new InvalidDataException(
                            $"Resident exact automatic-blink ownership differs: " +
                            $"{entry.rootName}.");
                    }
                    exactAutomaticBlinkOwnerCount++;
                }
            }

            if (recoveredEarOwnerCount != 6 || automaticBlinkEligibleCount != 31 ||
                exactAutomaticBlinkOwnerCount != 2)
                throw new InvalidDataException(
                    $"Resident skeletal-morph ownership summary differs from installed data: " +
                    $"earOwners={recoveredEarOwnerCount}/6 " +
                    $"blinkEligible={automaticBlinkEligibleCount}/31 " +
                    $"exactAutomaticBlinkOwners={exactAutomaticBlinkOwnerCount}/2.");

            float span = CharacterLineupHorizontalSpacing * (ordered.Length - 1);
            int[] residentInstanceIds = rigRoots
                .Select(root => root.gameObject.GetInstanceID())
                .OrderBy(instanceId => instanceId)
                .ToArray();
            Camera camera = Camera.main ??
                UnityEngine.Object.FindObjectOfType<Camera>(true);
            CharacterRecoveryPresentationController presentation =
                camera != null
                    ? camera.GetComponent<CharacterRecoveryPresentationController>()
                    : null;
            CharacterRecoveryRig firstRig = FindDirectChild(
                charactersRoot,
                ordered[0].rootName).GetComponent<CharacterRecoveryRig>();
            CharacterRecoveryRig lastRig = FindDirectChild(
                charactersRoot,
                ordered[ordered.Length - 1].rootName)
                .GetComponent<CharacterRecoveryRig>();
            if (presentation == null ||
                ordered[0].presentationProfile == null ||
                ordered[ordered.Length - 1].presentationProfile == null ||
                !presentation.ApplyProfile(ordered[0].presentationProfile, firstRig))
            {
                throw new InvalidDataException(
                    "Resident lineup could not apply its first presentation profile.");
            }
            float firstCameraX = camera.transform.position.x;
            if (!presentation.ApplyProfile(
                    ordered[ordered.Length - 1].presentationProfile,
                    lastRig))
            {
                throw new InvalidDataException(
                    "Resident lineup could not apply its last presentation profile.");
            }
            float lastCameraX = camera.transform.position.x;
            int[] switchedInstanceIds = Enumerable.Range(0, charactersRoot.childCount)
                .Select(index => charactersRoot.GetChild(index))
                .Where(root => root.GetComponent<CharacterRecoveryRig>() != null)
                .Select(root => root.gameObject.GetInstanceID())
                .OrderBy(instanceId => instanceId)
                .ToArray();
            if (!residentInstanceIds.SequenceEqual(switchedInstanceIds))
                throw new InvalidDataException(
                    "Resident character instances changed while switching profiles.");
            if (Mathf.Abs(lastCameraX - firstCameraX) < span * 0.5f)
            {
                throw new InvalidDataException(
                    $"Resident camera did not traverse the lineup: " +
                    $"firstX={firstCameraX:R} lastX={lastCameraX:R} span={span:R}.");
            }
            presentation.ApplyProfile(ordered[0].presentationProfile, firstRig);
            Debug.Log(
                $"Resident character lineup validation passed: actors={ordered.Length}, " +
                $"spacing={CharacterLineupHorizontalSpacing:R}, span={span:R}, " +
                $"cameraTravel={Mathf.Abs(lastCameraX - firstCameraX):R}, " +
                $"instancesPreserved=true, allActive=true, " +
                $"runtimeLoadOnSelection=false, " +
                $"morphBindings={recoveredMorphBindingCount}, " +
                $"earOwners={recoveredEarOwnerCount}, " +
                $"blinkEligible={automaticBlinkEligibleCount}, " +
                $"exactAutomaticBlinkOwners={exactAutomaticBlinkOwnerCount}.");
        }

        [MenuItem("Endfield/Character Recovery Lab/Validate All-Character Resident Lineup")]
        public static void ValidateAllCharacterResidentLineupCommandLine()
        {
            Scene scene = EditorSceneManager.OpenScene(
                AllCharacterViewerScenePath,
                OpenSceneMode.Single);
            GameObject viewerRoot = FindSceneGameObject(ViewerRootObjectName);
            Transform charactersRoot = viewerRoot != null
                ? FindDirectChild(viewerRoot.transform, "Characters")
                : null;
            if (charactersRoot == null)
                throw new InvalidDataException(
                    "AllCharacterRecoveryViewer has no Characters root.");

            CharacterRecoveryActorCatalog catalog =
                charactersRoot.GetComponent<CharacterRecoveryActorCatalog>();
            if (catalog == null || !catalog.keepAllModelsResident)
                throw new InvalidDataException(
                    "AllCharacterRecoveryViewer resident catalog is missing or disabled.");
            if (catalog.entries == null || catalog.entries.Length != 33)
                throw new InvalidDataException(
                    $"Expected 33 canonical character entries; found " +
                    $"{(catalog.entries != null ? catalog.entries.Length : 0)}.");

            CharacterRecoveryActorCatalogEntry[] ordered = catalog.entries
                .OrderBy(
                    entry => string.IsNullOrEmpty(entry.displayName)
                        ? entry.rootName
                        : entry.displayName,
                    StringComparer.Ordinal)
                .ToArray();
            var residentIds = new List<int>();
            for (int index = 0; index < ordered.Length; index++)
            {
                CharacterRecoveryActorCatalogEntry entry = ordered[index];
                Transform root = FindDirectChild(charactersRoot, entry.rootName);
                CharacterRecoveryRig rig = root != null
                    ? root.GetComponent<CharacterRecoveryRig>()
                    : null;
                if (rig == null || !root.gameObject.activeSelf)
                    throw new InvalidDataException(
                        $"All-character resident actor is missing/inactive: {entry.rootName}.");
                float expectedX =
                    (index - (ordered.Length - 1) * 0.5f) *
                    CharacterLineupHorizontalSpacing;
                Vector3 expectedPosition = new Vector3(expectedX, 0f, 0f);
                if ((root.localPosition - expectedPosition).sqrMagnitude > 0.000001f ||
                    root.GetSiblingIndex() != index)
                {
                    throw new InvalidDataException(
                        $"All-character resident order/position differs for {entry.rootName}: " +
                        $"expected={expectedPosition} actual={root.localPosition} " +
                        $"sibling={root.GetSiblingIndex()}/{index}.");
                }
                if (entry.prefab == null ||
                    string.IsNullOrEmpty(entry.prefabAssetPath))
                    throw new InvalidDataException(
                        $"All-character catalog prefab binding is missing: {entry.rootName}.");
                residentIds.Add(root.gameObject.GetInstanceID());
            }

            foreach (string addition in new[] { "Liino", "Jsspsi", "Chenpast" })
            {
                if (!ordered.Any(entry => string.Equals(
                        entry.rootName,
                        addition,
                        StringComparison.Ordinal)))
                    throw new InvalidDataException(
                        $"All-character catalog addition is missing: {addition}.");
            }
            foreach (string noProfileActor in new[] { "Jsspsi", "Chenpast" })
            {
                CharacterRecoveryActorCatalogEntry entry = ordered.Single(row =>
                    string.Equals(
                        row.rootName,
                        noProfileActor,
                        StringComparison.Ordinal));
                if (entry.presentationProfile != null)
                    throw new InvalidDataException(
                        $"{noProfileActor} received a presentation profile without original source evidence.");
            }
            CharacterRecoveryActorCatalogEntry liinoEntry = ordered.Single(row =>
                string.Equals(row.rootName, "Liino", StringComparison.Ordinal));
            if (liinoEntry.presentationProfile == null)
                throw new InvalidDataException(
                    "Liino playable entry is missing its source-backed presentation profile.");

            Camera camera = Camera.main ??
                UnityEngine.Object.FindObjectOfType<Camera>(true);
            CharacterRecoveryCameraController cameraController = camera != null
                ? camera.GetComponent<CharacterRecoveryCameraController>()
                : null;
            Transform jsspsiRoot = FindDirectChild(charactersRoot, "Jsspsi");
            CharacterRecoveryRig jsspsiRig = jsspsiRoot != null
                ? jsspsiRoot.GetComponent<CharacterRecoveryRig>()
                : null;
            if (camera == null || cameraController == null || jsspsiRig == null)
                throw new InvalidDataException(
                    "All-character bounds-framing validation prerequisites are missing.");
            Vector3 cameraBefore = camera.transform.position;
            cameraController.SetFocus(
                jsspsiRig.FocusTarget,
                jsspsiRig.CalculateBounds());
            cameraController.FrameTarget();
            int[] afterIds = Enumerable.Range(0, charactersRoot.childCount)
                .Select(index => charactersRoot.GetChild(index))
                .Where(root => root.GetComponent<CharacterRecoveryRig>() != null)
                .Select(root => root.gameObject.GetInstanceID())
                .OrderBy(value => value)
                .ToArray();
            if (!residentIds.OrderBy(value => value).SequenceEqual(afterIds))
                throw new InvalidDataException(
                    "All-character instances changed during source-profile-null camera framing.");
            float cameraTravel = Vector3.Distance(cameraBefore, camera.transform.position);
            if (!float.IsFinite(cameraTravel))
                throw new InvalidDataException(
                    "All-character camera framing produced a non-finite transform.");

            Debug.Log(
                $"All-character resident lineup validation passed: actors={ordered.Length}, " +
                $"spacing={CharacterLineupHorizontalSpacing:R}, span=" +
                $"{CharacterLineupHorizontalSpacing * (ordered.Length - 1):R}, " +
                $"instancesPreserved=true, allActive=true, runtimeLoadOnSelection=false, " +
                $"sourceProfileNullBoundsFallback=Jsspsi, cameraTravel={cameraTravel:R}.");
        }

        /// <summary>
        /// Applies the uniform white presentation background to the existing
        /// all-character resident lineup scene without rebuilding the actors,
        /// then re-renders its preview. Scene rebuilds keep this configuration
        /// via BuildAllCharacterModelViewer's neutralWhiteBackground flag.
        /// </summary>
        [MenuItem("Endfield/Character Recovery Lab/Apply White Background To All-Character Viewer")]
        public static void ApplyAllCharacterViewerWhiteBackground()
        {
            Scene scene = EditorSceneManager.OpenScene(
                AllCharacterViewerScenePath,
                OpenSceneMode.Single);
            Camera camera = Camera.main ??
                UnityEngine.Object.FindObjectOfType<Camera>(true);
            if (camera == null)
                throw new InvalidOperationException(
                    "AllCharacterRecoveryViewer has no camera.");

            ApplyNeutralWhiteViewerBackground(camera);
            AssetDatabase.SaveAssets();
            EditorSceneManager.SaveScene(scene);

            string previewPath = Path.GetFullPath(Path.Combine(
                Application.dataPath,
                "../../scratch/character_recovery/all_character_recovery_viewer.png"));
            Directory.CreateDirectory(Path.GetDirectoryName(previewPath) ?? ".");
            RenderPreview(previewPath);
            Debug.Log(
                $"[WhiteBackdrop] White background applied to {AllCharacterViewerScenePath}; " +
                $"preview={previewPath}");
        }

        public static void RebuildSharedViewerSceneFromCachedAssets()
        {
            RebuildSharedViewerScene(rebuildMeshAssets: false);
        }

        /// <summary>
        /// Repairs mesh geometry, weights, and bindposes directly from the
        /// recovered original mesh JSON while reusing existing animation clips.
        /// This is the authoritative recovery path after an interrupted full
        /// build has created mesh assets but exited before dirty skin data was
        /// saved.
        /// </summary>
        [MenuItem("Endfield/Character Recovery Lab/Rebuild Viewer From Original Meshes")]
        public static void RebuildSharedViewerSceneFromOriginalMeshes()
        {
            RebuildSharedViewerScene(rebuildMeshAssets: true);
        }

        private static void RebuildSharedViewerScene(bool rebuildMeshAssets)
        {
            EnsureFolders();
            EnsureHGCompatRenderPipelineAssigned();
            TextureImportCache.Clear();
            Dictionary<string, CharacterRecoveryPresentationProfile>
                presentationProfiles =
                    EndfieldPlayableCharInfoProfileBuilder.BuildAllProfiles();

            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            ViewerSceneLayout layout = CreateViewerSceneLayout();

            ActorBuildResult activeActor = null;
            var builtActors = new List<ActorBuildResult>();
            ManifestCharacterSpec[] viewerCharacters = SharedViewerCharacters();
            bool releaseInactiveSceneInstances =
                viewerCharacters.Length > 3 && AllCharacterManifestsExist(viewerCharacters);
            foreach (ManifestCharacterSpec character in viewerCharacters)
            {
                string manifestPath = Path.Combine(Directory.GetCurrentDirectory(), character.ManifestAssetPath);
                if (!File.Exists(manifestPath))
                {
                    Debug.LogWarning($"Skipping missing character manifest: {character.ManifestAssetPath}");
                    continue;
                }

                bool active = character.Active && activeActor == null;
                ActorBuildResult actor = BuildActor(
                    character.ManifestAssetPath,
                    character.RootName,
                    character.DisplayName,
                    character.SceneOffset,
                    active,
                    character.PreviewClipPreference,
                    includeVariants: false,
                    rebuildAnimationAssets: false,
                    clearGeneratedAssets: false,
                    rebuildMeshAssets: rebuildMeshAssets);
                builtActors.Add(actor);
                actor.Root.transform.SetParent(layout.CharactersRoot, true);
                if (active)
                    activeActor = actor;
                else if (releaseInactiveSceneInstances)
                {
                    UnityEngine.Object.DestroyImmediate(actor.Root);
                    actor.Root = null;
                }
            }

            if (activeActor == null && builtActors.Count > 0)
            {
                activeActor = builtActors[0];
                activeActor.Root.SetActive(true);
            }
            if (activeActor == null)
                throw new InvalidOperationException("No character recovery manifests were found under Generated/Characters.");

            ConfigureScene(activeActor.Root, activeActor.MeshObjects, layout);
            EnsureCharacterRecoveryActorCatalog(
                layout,
                builtActors,
                presentationProfiles);
            activeActor = EnsureHorizontalCharacterLineup(
                SceneManager.GetActiveScene(),
                layout,
                builtActors,
                activeActor.RootName);
            EnsureCharacterRecoveryViewerUi(layout);
            Camera viewerCamera = Camera.main ??
                UnityEngine.Object.FindObjectOfType<Camera>(true);
            if (viewerCamera == null)
                throw new InvalidOperationException(
                    "Cached character viewer has no camera for the source-authored CharInfo portrait.");
            ConfigureOperatorReferenceLighting(
                SceneManager.GetActiveScene(),
                layout.LightingRoot,
                viewerCamera,
                activeActor.RootName,
                activeActor.Root.transform);
            EndfieldRecoveredCharInfoBackgroundPortrait portrait =
                EndfieldRecoveredCharInfoBackgroundPortraitBuilder.EnsureAndBind(
                viewerCamera,
                activeActor.Root.name,
                activeActor.Root.transform);
            EnsureOriginalStylePresentationScene(
                SceneManager.GetActiveScene());
            EnsureCharacterRecoveryPresentation(
                viewerCamera,
                portrait,
                activeActor,
                presentationProfiles);
            EditorBuildSettings.scenes = new[]
            {
                new EditorBuildSettingsScene(ViewerScenePath, true),
            };
            EditorSceneManager.SaveScene(SceneManager.GetActiveScene(), ViewerScenePath);

            string previewPath = Path.GetFullPath(Path.Combine(Application.dataPath, "../../scratch/character_recovery/character_recovery_viewer.png"));
            Directory.CreateDirectory(Path.GetDirectoryName(previewPath) ?? ".");
            RenderPreview(previewPath);

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log(
                $"Character viewer scene rebuilt: actors={builtActors.Count} " +
                $"active={activeActor.Root.name} originalMeshes={rebuildMeshAssets} " +
                $"scene={ViewerScenePath}");
        }

        /// <summary>
        /// Builds a static-pose material/rendering viewer with no AnimationClip
        /// dependencies. The full recovery scene and actor prefabs are preserved.
        /// This is the default scene for shader and lighting iteration while the
        /// multi-gigabyte animation cache is not being investigated.
        /// </summary>
        [MenuItem("Endfield/Character Recovery Lab/Build Fast Render Style Viewer")]
        public static void BuildFastRenderStyleViewer()
        {
            EnsureFolders();
            EnsureHGCompatRenderPipelineAssigned();
            if (!File.Exists(Path.Combine(Directory.GetCurrentDirectory(), ViewerScenePath)))
            {
                throw new FileNotFoundException(
                    "Build the full character viewer once before deriving its fast render-style scene.",
                    ViewerScenePath);
            }

            Scene scene = EditorSceneManager.OpenScene(ViewerScenePath, OpenSceneMode.Single);
            Transform charactersRoot = FindSceneGameObject("Characters")?.transform;
            if (charactersRoot == null)
                throw new InvalidOperationException("Full character viewer has no Characters root.");

            GameObject wulfa = EnsureFastSceneActor(
                scene,
                charactersRoot,
                "Wulfa",
                $"{GeneratedRoot}/Playable/Wulfa/Prefabs/Wulfa.prefab");
            GameObject zhuangfy = EnsureFastSceneActor(
                scene,
                charactersRoot,
                "Zhuangfy",
                $"{GeneratedRoot}/Playable/Zhuangfy/Prefabs/Zhuangfy.prefab");

            int strippedComponents = 0;
            strippedComponents += BakeAndStripFastSceneActor(
                wulfa,
                "A_actor_wulfa_ui_overview_loop_01",
                0.95f,
                active: true);
            strippedComponents += BakeAndStripFastSceneActor(
                zhuangfy,
                "A_actor_zhuangfy_ui_overview_loop_01",
                0.275f,
                active: false);

            foreach (CharacterRecoveryRig rig in UnityEngine.Object.FindObjectsOfType<CharacterRecoveryRig>(true))
            {
                if (rig == null || !rig.gameObject.scene.IsValid())
                    continue;
                if (rig.gameObject == wulfa || rig.gameObject == zhuangfy)
                    continue;
                UnityEngine.Object.DestroyImmediate(rig.gameObject);
            }

            foreach (CharacterRecoveryActorCatalog catalog in
                UnityEngine.Object.FindObjectsOfType<CharacterRecoveryActorCatalog>(true))
            {
                if (catalog == null || !catalog.gameObject.scene.IsValid())
                    continue;
                // Both fast actors are embedded. Emptying the catalog prevents an
                // accidental selection from loading a full animation-bearing prefab.
                catalog.entries = Array.Empty<CharacterRecoveryActorCatalogEntry>();
                catalog.keepAllModelsResident = false;
                EditorUtility.SetDirty(catalog);
            }

            CharacterRecoveryCameraController controller =
                UnityEngine.Object.FindObjectOfType<CharacterRecoveryCameraController>(true);
            CharacterRecoveryRig wulfaRig = wulfa.GetComponent<CharacterRecoveryRig>();
            if (controller != null && wulfaRig != null)
            {
                Bounds bounds = wulfaRig.CalculateBounds();
                controller.SetFocus(wulfaRig.FocusTarget, bounds);
                controller.FrameTarget();
                EditorUtility.SetDirty(controller);
            }

            Camera fastViewerCamera = Camera.main ??
                UnityEngine.Object.FindObjectOfType<Camera>(true);
            if (fastViewerCamera == null)
                throw new InvalidOperationException(
                    "Fast render-style viewer has no camera for the source-sky marker.");
            // The marker/material/cubemap references are inert while the
            // source selector is off, but make the saved viewer usable by a
            // later standalone -endfield-recovered-source-energy-core launch.
            ConfigureRecoveredCharInfoSky(fastViewerCamera);
            EndfieldRecoveredCharInfoBackgroundPortraitBuilder.EnsureAndBind(
                fastViewerCamera,
                "Wulfa",
                wulfa.transform);

            EditorSceneManager.MarkSceneDirty(scene);
            if (!EditorSceneManager.SaveScene(scene, FastRenderStyleScenePath, false))
                throw new IOException($"Could not save fast render-style scene: {FastRenderStyleScenePath}");

            EditorBuildSettings.scenes = new[]
            {
                new EditorBuildSettingsScene(FastRenderStyleScenePath, true),
            };
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();

            FastRenderStyleDependencyStats stats = InspectFastRenderStyleDependencies();
            if (stats.FastAnimationDependencyCount != 0)
            {
                throw new InvalidOperationException(
                    $"Fast render-style scene still references {stats.FastAnimationDependencyCount} AnimationClip assets.");
            }

            Debug.Log(
                $"Fast render-style viewer built: scene={FastRenderStyleScenePath}, " +
                $"actors=2, strippedComponents={strippedComponents}, " +
                $"animationDependencies=0; fullViewerAnimationDependencies=" +
                $"{stats.FullAnimationDependencyCount} ({stats.FullAnimationDependencyBytes / (1024.0 * 1024.0 * 1024.0):0.00} GiB)." );
        }

        [MenuItem("Endfield/Character Recovery Lab/Open Fast Render Style Viewer")]
        public static void OpenFastRenderStyleViewer()
        {
            string fullPath = Path.Combine(Directory.GetCurrentDirectory(), FastRenderStyleScenePath);
            if (!File.Exists(fullPath))
                BuildFastRenderStyleViewer();
            else
                EditorSceneManager.OpenScene(FastRenderStyleScenePath, OpenSceneMode.Single);
        }

        /// <summary>
        /// Builds a development D3D12 standalone player for frame-debugger and
        /// timing-profiler work. Keeping capture tooling out of the Editor avoids
        /// recording unrelated Editor windows and render loops.
        /// </summary>
        [MenuItem("Endfield/Character Recovery Lab/Build Fast Render Style Capture Player")]
        public static void BuildFastRenderStyleCapturePlayer()
        {
            string sceneFullPath = Path.Combine(
                Directory.GetCurrentDirectory(),
                FastRenderStyleScenePath);
            if (!File.Exists(sceneFullPath))
                BuildFastRenderStyleViewer();

            Scene scene = EditorSceneManager.OpenScene(
                FastRenderStyleScenePath,
                OpenSceneMode.Single);
            Camera captureCamera = Camera.main ??
                UnityEngine.Object.FindObjectOfType<Camera>(true);
            if (captureCamera == null)
                throw new InvalidOperationException(
                    "Fast render-style capture scene has no camera.");
            // Generic capture players are often built with the selector off
            // and enabled only by the standalone command line. Require and
            // serialize the source assets now so Unity cannot strip them.
            ConfigureRecoveredCharInfoSky(
                captureCamera,
                requireSourceAssets: true);
            GameObject captureActor = FindSceneGameObject("Wulfa");
            if (captureActor == null || !captureActor.activeInHierarchy)
                captureActor = FindSceneGameObject("Zhuangfy");
            if (captureActor == null)
                throw new InvalidOperationException(
                    "Fast render-style capture scene has no Wulfa or Zhuangfy actor for the source-authored CharInfo portrait.");
            EndfieldRecoveredCharInfoBackgroundPortraitBuilder.EnsureAndBind(
                captureCamera,
                captureActor.name,
                captureActor.transform);
            EditorSceneManager.MarkSceneDirty(scene);
            if (!EditorSceneManager.SaveScene(
                    scene,
                    FastRenderStyleScenePath,
                    false))
            {
                throw new IOException(
                    $"Could not save source-sky references in " +
                    FastRenderStyleScenePath);
            }
            EditorBuildSettings.scenes = new[]
            {
                new EditorBuildSettingsScene(FastRenderStyleScenePath, true),
            };

            string playerPath = Path.GetFullPath(Path.Combine(
                Directory.GetCurrentDirectory(),
                FastRenderStyleCapturePlayerRelativePath));
            Directory.CreateDirectory(Path.GetDirectoryName(playerPath) ?? ".");

            GraphicsDeviceType[] previousGraphicsApis =
                PlayerSettings.GetGraphicsAPIs(BuildTarget.StandaloneWindows64);
            bool previousUseDefaultGraphicsApis =
                PlayerSettings.GetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64);
            try
            {
                PlayerSettings.SetUseDefaultGraphicsAPIs(
                    BuildTarget.StandaloneWindows64,
                    false);
                PlayerSettings.SetGraphicsAPIs(
                    BuildTarget.StandaloneWindows64,
                    new[] { GraphicsDeviceType.Direct3D12 });

                var options = new BuildPlayerOptions
                {
                    scenes = new[] { FastRenderStyleScenePath },
                    locationPathName = playerPath,
                    target = BuildTarget.StandaloneWindows64,
                    options = BuildOptions.Development,
                };
                BuildReport report = BuildPipeline.BuildPlayer(options);
                if (report.summary.result != BuildResult.Succeeded)
                {
                    throw new InvalidOperationException(
                        $"Fast render-style capture player build failed: " +
                        $"result={report.summary.result}, errors={report.summary.totalErrors}, " +
                        $"warnings={report.summary.totalWarnings}.");
                }

                Debug.Log(
                    $"Fast render-style capture player built: path={playerPath}, " +
                    $"size={report.summary.totalSize} bytes, " +
                    $"time={report.summary.totalTime.TotalSeconds:0.0}s, api=D3D12.");
            }
            finally
            {
                PlayerSettings.SetUseDefaultGraphicsAPIs(
                    BuildTarget.StandaloneWindows64,
                    previousUseDefaultGraphicsApis);
                if (!previousUseDefaultGraphicsApis &&
                    previousGraphicsApis != null &&
                    previousGraphicsApis.Length != 0)
                {
                    PlayerSettings.SetGraphicsAPIs(
                        BuildTarget.StandaloneWindows64,
                        previousGraphicsApis);
                }
            }
        }

        [MenuItem("Endfield/Character Recovery Lab/Verify Fast Render Style Viewer")]
        public static void VerifyFastRenderStyleViewer()
        {
            string fullPath = Path.Combine(Directory.GetCurrentDirectory(), FastRenderStyleScenePath);
            if (!File.Exists(fullPath))
                throw new FileNotFoundException("Fast render-style scene has not been built.", fullPath);

            var stopwatch = System.Diagnostics.Stopwatch.StartNew();
            Scene scene = EditorSceneManager.OpenScene(FastRenderStyleScenePath, OpenSceneMode.Single);
            stopwatch.Stop();

            int animationComponents = 0;
            int animatorComponents = 0;
            var actorNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            int activeActors = 0;
            foreach (Animation animation in UnityEngine.Object.FindObjectsOfType<Animation>(true))
            {
                if (animation != null && animation.gameObject.scene == scene)
                    animationComponents++;
            }
            foreach (Animator animator in UnityEngine.Object.FindObjectsOfType<Animator>(true))
            {
                if (animator != null && animator.gameObject.scene == scene)
                    animatorComponents++;
            }
            foreach (CharacterRecoveryRig rig in UnityEngine.Object.FindObjectsOfType<CharacterRecoveryRig>(true))
            {
                if (rig == null || rig.gameObject.scene != scene)
                    continue;
                actorNames.Add(rig.gameObject.name);
                if (rig.gameObject.activeSelf)
                    activeActors++;
                if (rig.Animation != null ||
                    (rig.clipMetadata != null && rig.clipMetadata.Length != 0) ||
                    (rig.recoveredStates != null && rig.recoveredStates.Length != 0))
                    throw new InvalidOperationException($"Fast actor retained animation state: {rig.gameObject.name}");
            }

            FastRenderStyleDependencyStats stats = InspectFastRenderStyleDependencies();
            if (animationComponents != 0 || animatorComponents != 0)
                throw new InvalidOperationException(
                    $"Fast scene contains Animation={animationComponents}, Animator={animatorComponents} components.");
            if (!actorNames.SetEquals(new[] { "Wulfa", "Zhuangfy" }) || activeActors != 1)
                throw new InvalidOperationException(
                    $"Fast scene actor contract failed: actors={string.Join(",", actorNames)} active={activeActors}.");
            if (stats.FastAnimationDependencyCount != 0)
                throw new InvalidOperationException(
                    $"Fast scene retained {stats.FastAnimationDependencyCount} animation dependencies.");
            if (UnityEngine.Object.FindObjectOfType<CharacterRecoveryViewerUI>(true) == null)
                throw new InvalidOperationException("Fast scene has no character viewer UI.");
            if (Camera.main == null)
                throw new InvalidOperationException("Fast scene has no MainCamera.");

            EndfieldRecoveredCharInfoBackgroundPortrait[] portraits =
                UnityEngine.Object.FindObjectsOfType<EndfieldRecoveredCharInfoBackgroundPortrait>(true);
            EndfieldRecoveredCharInfoBackgroundPortrait scenePortrait = null;
            int scenePortraitCount = 0;
            foreach (EndfieldRecoveredCharInfoBackgroundPortrait portrait in portraits)
            {
                if (portrait == null || portrait.gameObject.scene != scene)
                    continue;
                scenePortrait = portrait;
                scenePortraitCount++;
            }
            if (scenePortraitCount != 1 ||
                scenePortrait == null ||
                scenePortrait.portraitRenderer == null ||
                scenePortrait.portraitRenderer != scenePortrait.GetComponent<Renderer>() ||
                scenePortrait.gameObject.layer !=
                    EndfieldRecoveredCharInfoBackgroundPortrait.SourceUiLayer ||
                scenePortrait.portraitRenderer.sharedMaterial == null ||
                scenePortrait.portraitRenderer.sharedMaterial.shader == null ||
                scenePortrait.portraitRenderer.sharedMaterial.shader.name !=
                    EndfieldRecoveredCharInfoBackgroundPortrait.ShaderName ||
                scenePortrait.wulfaTexture == null ||
                scenePortrait.zhuangfyTexture == null ||
                scenePortrait.sourceManifest == null)
            {
                throw new InvalidOperationException(
                    "Fast scene source-authored CharInfo portrait binding is missing or malformed.");
            }

            Debug.Log(
                $"Fast render-style viewer verified: openMs={stopwatch.ElapsedMilliseconds}, " +
                $"actors={actorNames.Count}, activeActors={activeActors}, animationComponents=0, " +
                $"animationDependencies=0, fullViewerAnimationDependencies=" +
                $"{stats.FullAnimationDependencyCount} ({stats.FullAnimationDependencyBytes / (1024.0 * 1024.0 * 1024.0):0.00} GiB)." );
        }

        [MenuItem("Endfield/Character Recovery Lab/Render Fast Render Style Preview")]
        public static void RenderFastRenderStylePreview()
        {
            string fullPath = Path.Combine(Directory.GetCurrentDirectory(), FastRenderStyleScenePath);
            if (!File.Exists(fullPath))
                throw new FileNotFoundException("Fast render-style scene has not been built.", fullPath);

            EditorSceneManager.OpenScene(FastRenderStyleScenePath, OpenSceneMode.Single);
            string outputPath = Path.GetFullPath(Path.Combine(
                Application.dataPath,
                "../../scratch/character_render_style_fast.png"));
            Directory.CreateDirectory(Path.GetDirectoryName(outputPath) ?? ".");
            RenderPreview(outputPath);
            Debug.Log($"Rendered fast character render-style preview: {outputPath}");
        }

        private sealed class FastRenderStyleDependencyStats
        {
            public int FastAnimationDependencyCount;
            public int FullAnimationDependencyCount;
            public long FullAnimationDependencyBytes;
        }

        private static GameObject EnsureFastSceneActor(
            Scene scene,
            Transform charactersRoot,
            string actorName,
            string prefabAssetPath)
        {
            GameObject actor = FindSceneGameObject(actorName);
            if (actor == null)
            {
                GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabAssetPath);
                if (prefab == null)
                    throw new FileNotFoundException($"Fast-viewer actor prefab is missing: {actorName}", prefabAssetPath);
                actor = PrefabUtility.InstantiatePrefab(prefab, scene) as GameObject;
                if (actor == null)
                    throw new InvalidOperationException($"Could not instantiate fast-viewer actor: {actorName}");
                actor.name = actorName;
                actor.transform.SetParent(charactersRoot, false);
            }

            GameObject prefabRoot = PrefabUtility.GetOutermostPrefabInstanceRoot(actor);
            if (prefabRoot != null)
            {
                PrefabUtility.UnpackPrefabInstance(
                    prefabRoot,
                    PrefabUnpackMode.Completely,
                    InteractionMode.AutomatedAction);
            }
            actor.transform.SetParent(charactersRoot, false);
            actor.transform.localPosition = Vector3.zero;
            actor.transform.localRotation = Quaternion.identity;
            actor.transform.localScale = Vector3.one;
            return actor;
        }

        private static int BakeAndStripFastSceneActor(
            GameObject actor,
            string referenceClipName,
            float sampleTime,
            bool active)
        {
            if (actor == null)
                throw new ArgumentNullException(nameof(actor));

            actor.SetActive(true);
            Animation animation = actor.GetComponent<Animation>();
            AnimationState state = animation != null ? animation[referenceClipName] : null;
            AnimationClip clip = state != null ? state.clip : null;
            if (clip == null)
            {
                throw new InvalidOperationException(
                    $"Fast-viewer reference clip is missing on {actor.name}: {referenceClipName}");
            }

            SetRecoveredPropVisibility(actor, Array.Empty<string>());
            clip.SampleAnimation(actor, Mathf.Clamp(sampleTime, 0f, clip.length));
            CharacterProceduralIk poseCorrection = actor.GetComponent<CharacterProceduralIk>();
            if (poseCorrection != null)
                poseCorrection.Evaluate();

            int stripped = 0;
            foreach (EndfieldOverviewPlayback playback in
                actor.GetComponentsInChildren<EndfieldOverviewPlayback>(true))
            {
                if (playback == null)
                    continue;
                UnityEngine.Object.DestroyImmediate(playback);
                stripped++;
            }
            foreach (CharacterAnimationLayerSync layerSync in
                actor.GetComponentsInChildren<CharacterAnimationLayerSync>(true))
            {
                if (layerSync == null)
                    continue;
                UnityEngine.Object.DestroyImmediate(layerSync);
                stripped++;
            }
            foreach (Animator animator in actor.GetComponentsInChildren<Animator>(true))
            {
                if (animator == null)
                    continue;
                UnityEngine.Object.DestroyImmediate(animator);
                stripped++;
            }
            foreach (Animation source in actor.GetComponentsInChildren<Animation>(true))
            {
                if (source == null)
                    continue;
                UnityEngine.Object.DestroyImmediate(source);
                stripped++;
            }
            foreach (CharacterProceduralIk ik in
                actor.GetComponentsInChildren<CharacterProceduralIk>(true))
            {
                if (ik == null)
                    continue;
                UnityEngine.Object.DestroyImmediate(ik);
                stripped++;
            }

            CharacterRecoveryRig rig = actor.GetComponent<CharacterRecoveryRig>();
            if (rig == null)
                rig = actor.AddComponent<CharacterRecoveryRig>();
            rig.displayName = actor.name;
            rig.animationSource = null;
            rig.focusTarget = actor.transform;
            rig.poseCorrection = null;
            rig.clipMetadata = Array.Empty<CharacterRecoveryClipMetadata>();
            rig.recoveredStates = Array.Empty<CharacterRecoveryState>();
            actor.SetActive(active);
            EditorUtility.SetDirty(rig);
            EditorUtility.SetDirty(actor);
            return stripped;
        }

        private static FastRenderStyleDependencyStats InspectFastRenderStyleDependencies()
        {
            var stats = new FastRenderStyleDependencyStats();
            string[] fastDependencies = AssetDatabase.GetDependencies(
                FastRenderStyleScenePath,
                recursive: true);
            foreach (string dependency in fastDependencies)
            {
                if (dependency.EndsWith(".anim", StringComparison.OrdinalIgnoreCase))
                    stats.FastAnimationDependencyCount++;
            }

            string[] fullDependencies = AssetDatabase.GetDependencies(
                ViewerScenePath,
                // The scene references clips directly through its two legacy
                // Animation components. Avoid recursively traversing every
                // texture/material dependency in this already-large audit.
                recursive: false);
            foreach (string dependency in fullDependencies)
            {
                if (!dependency.EndsWith(".anim", StringComparison.OrdinalIgnoreCase))
                    continue;
                stats.FullAnimationDependencyCount++;
                string fullPath = Path.Combine(Directory.GetCurrentDirectory(), dependency);
                if (File.Exists(fullPath))
                    stats.FullAnimationDependencyBytes += new FileInfo(fullPath).Length;
            }
            return stats;
        }

        /// <summary>
        /// Rebuilds only the small set of clips used for visual reference renders.
        /// The complete generated animation cache is roughly 25 GB, so routine
        /// recovery iterations should not rewrite every clip just to validate
        /// importer/channel changes.
        /// </summary>
        public static void RefreshReferenceAnimationAssets()
        {
            EnsureFolders();
            int rebuiltCount = 0;
            foreach (ManifestCharacterSpec character in SharedViewerCharacters())
            {
                string manifestPath = Path.Combine(Directory.GetCurrentDirectory(), character.ManifestAssetPath);
                if (!File.Exists(manifestPath))
                    continue;

                var manifest = Dict(ManifestMiniJson.Deserialize(File.ReadAllText(manifestPath, Encoding.UTF8)));
                var preferredNames = new HashSet<string>(character.PreviewClipPreference, StringComparer.OrdinalIgnoreCase);
                var selectedClips = new List<object>();
                foreach (object clipObj in List(manifest["clips"]))
                {
                    var clipInfo = Dict(clipObj);
                    string clipName = Str(clipInfo.TryGetValue("name", out object nameObj) ? nameObj : null);
                    if (preferredNames.Contains(clipName))
                        selectedClips.Add(clipObj);
                }

                string actorGeneratedRoot = ActorGeneratedRoot(character.ManifestAssetPath, character.RootName);
                EnsureActorFolders(actorGeneratedRoot, clearGeneratedAssets: false);
                List<AnimationClip> rebuilt = BuildAnimationClips(selectedClips, null, actorGeneratedRoot);
                rebuiltCount += rebuilt.Count;
                Debug.Log($"Refreshed {rebuilt.Count} reference animation clips for {character.DisplayName}.");
            }

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log($"Reference animation refresh complete: clips={rebuiltCount}.");
        }

        /// <summary>
        /// Rebuilds only the Wulfa/Zhuangfy overview body clips measured in the
        /// original 60 Hz runtime captures. Existing assets are updated in place
        /// so their GUIDs remain stable; missing Zhuangfy assets are created only
        /// after their original-data ACL samples have been recovered.
        /// </summary>
        [MenuItem("Endfield/Character Recovery Lab/Refresh Runtime-Captured Overview Animations")]
        public static void RefreshRuntimeCapturedOverviewAnimationAssets()
        {
            EnsureFolders();
            var targetNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
            {
                "A_actor_wulfa_ui_overview_loop_01",
                "A_actor_wulfa_ui_overview_start_01",
                "A_actor_zhuangfy_ui_overview_loop_01",
                "A_actor_zhuangfy_ui_overview_start_01",
            };
            var rebuiltNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var preservedGuids = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

            foreach (ManifestCharacterSpec character in SharedViewerCharacters())
            {
                if (!string.Equals(character.RootName, "Wulfa", StringComparison.OrdinalIgnoreCase)
                    && !string.Equals(character.RootName, "Zhuangfy", StringComparison.OrdinalIgnoreCase))
                    continue;

                string manifestPath = Path.Combine(Directory.GetCurrentDirectory(), character.ManifestAssetPath);
                if (!File.Exists(manifestPath))
                    throw new FileNotFoundException($"{character.DisplayName} recovery manifest is missing.", manifestPath);

                var manifest = Dict(ManifestMiniJson.Deserialize(File.ReadAllText(manifestPath, Encoding.UTF8)));
                string actorGeneratedRoot = ActorGeneratedRoot(character.ManifestAssetPath, character.RootName);
                EnsureActorFolders(actorGeneratedRoot, clearGeneratedAssets: false);
                var selectedClips = new List<object>();
                foreach (object clipObj in List(manifest["clips"]))
                {
                    var clipInfo = Dict(clipObj);
                    string name = Str(clipInfo.TryGetValue("name", out object nameObj) ? nameObj : null);
                    if (!targetNames.Contains(name))
                        continue;

                    string sampleJson = Str(clipInfo.TryGetValue("sample_json", out object sampleObj) ? sampleObj : null);
                    if (sampleJson.Length == 0 || !File.Exists(sampleJson))
                        throw new FileNotFoundException($"Original-data overview sample is missing for {name}.", sampleJson);

                    string assetPath = $"{actorGeneratedRoot}/Animations/{Safe(name)}.anim";
                    string guidBefore = AssetDatabase.AssetPathToGUID(assetPath);
                    if (!string.IsNullOrEmpty(guidBefore))
                        preservedGuids[assetPath] = guidBefore;
                    selectedClips.Add(clipObj);
                }

                List<AnimationClip> rebuilt = BuildAnimationClips(selectedClips, null, actorGeneratedRoot);
                foreach (AnimationClip clip in rebuilt)
                {
                    if (clip != null)
                        rebuiltNames.Add(clip.name);
                }

                foreach (object clipObj in selectedClips)
                {
                    var clipInfo = Dict(clipObj);
                    string name = Str(clipInfo["name"]);
                    string assetPath = $"{actorGeneratedRoot}/Animations/{Safe(name)}.anim";
                    AnimationClip clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(assetPath);
                    float expectedDuration = Float(
                        clipInfo.TryGetValue("duration", out object durationObj) ? durationObj : null,
                        0f);
                    bool expectedLoopBlend = Bool(
                        clipInfo.TryGetValue("loop_blend", out object loopBlendObj) ? loopBlendObj : false);
                    if (clip == null)
                        throw new InvalidOperationException($"Overview animation was not created: {assetPath}");
                    if (expectedDuration > 0f && Mathf.Abs(clip.length - expectedDuration) > 0.0001f)
                        throw new InvalidOperationException(
                            $"Overview animation duration mismatch: {name} Unity={clip.length:0.########} " +
                            $"source={expectedDuration:0.########}");
                    AnimationClipSettings settings = AnimationUtility.GetAnimationClipSettings(clip);
                    if (settings.loopBlend != expectedLoopBlend)
                        throw new InvalidOperationException(
                            $"Overview loop-blend mismatch: {name} Unity={settings.loopBlend} " +
                            $"source={expectedLoopBlend}");
                }
            }

            if (rebuiltNames.Count != targetNames.Count || !rebuiltNames.SetEquals(targetNames))
                throw new InvalidOperationException(
                    $"Runtime-captured overview refresh was incomplete: rebuilt={rebuiltNames.Count} expected={targetNames.Count}.");

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            foreach (var pair in preservedGuids)
            {
                string guidAfter = AssetDatabase.AssetPathToGUID(pair.Key);
                if (!string.Equals(pair.Value, guidAfter, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException(
                        $"Runtime overview refresh changed an existing GUID: {pair.Key} {pair.Value} -> {guidAfter}");
            }

            Debug.Log(
                "Runtime-captured overview refresh complete: Wulfa loop=140 frames/2.333333s, " +
                "Zhuangfy loop=200-frame period/3.333333s, bodyClips=4, existing GUIDs preserved.");
        }

        /// <summary>
        /// Resumes Wulfa animation generation after an interrupted build
        /// without clearing or rewriting any existing actor animation asset.
        /// Zhuangfy and Mifu are deliberately outside this repair entry point
        /// because their source sample directories may not be present.
        /// </summary>
        [MenuItem("Endfield/Character Recovery Lab/Refresh Missing Wulfa Animations")]
        public static void RefreshMissingWulfaAnimationAssets()
        {
            EnsureFolders();

            string manifestAssetPath = ResolveManifestAssetPath(
                WulfaManifestAssetPath,
                LegacyWulfaManifestAssetPath);
            string manifestPath = Path.Combine(Directory.GetCurrentDirectory(), manifestAssetPath);
            if (!File.Exists(manifestPath))
                throw new FileNotFoundException("Wulfa recovery manifest is missing.", manifestPath);

            var manifest = Dict(ManifestMiniJson.Deserialize(File.ReadAllText(manifestPath, Encoding.UTF8)));
            string actorGeneratedRoot = ActorGeneratedRoot(manifestAssetPath, "Wulfa");
            EnsureActorFolders(actorGeneratedRoot, clearGeneratedAssets: false);

            int manifestCount = 0;
            int existingCount = 0;
            int missingSampleCount = 0;
            int invalidCount = 0;
            var selectedClips = new List<object>();
            var targetAssetPaths = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (object clipObj in List(manifest["clips"]))
            {
                manifestCount++;
                var clipInfo = Dict(clipObj);
                string name = Str(clipInfo.TryGetValue("name", out object nameObj) ? nameObj : null);
                string sampleJson = Str(clipInfo.TryGetValue("sample_json", out object sampleObj) ? sampleObj : null);
                if (name.Length == 0 || sampleJson.Length == 0)
                {
                    invalidCount++;
                    continue;
                }

                string assetPath = $"{actorGeneratedRoot}/Animations/{Safe(name)}.anim";
                if (!targetAssetPaths.Add(assetPath))
                    throw new InvalidOperationException($"Duplicate Wulfa animation target in manifest: {assetPath}");
                string assetDiskPath = Path.Combine(
                    Directory.GetCurrentDirectory(),
                    assetPath.Replace('/', Path.DirectorySeparatorChar));
                if (AssetDatabase.LoadAssetAtPath<AnimationClip>(assetPath) != null)
                {
                    existingCount++;
                    continue;
                }
                if (File.Exists(assetDiskPath))
                    throw new InvalidOperationException(
                        $"Refusing to replace an existing Wulfa animation file which Unity could not load: {assetPath}");

                string sampleDiskPath = Path.IsPathRooted(sampleJson)
                    ? sampleJson
                    : Path.Combine(Directory.GetCurrentDirectory(), sampleJson);
                if (!File.Exists(sampleDiskPath))
                {
                    missingSampleCount++;
                    Debug.LogWarning($"Skipping missing Wulfa animation sample: clip={name} sample={sampleJson}");
                    continue;
                }

                selectedClips.Add(clipObj);
            }

            if (missingSampleCount > 0 || invalidCount > 0)
                throw new InvalidOperationException(
                    "Missing-only Wulfa animation preflight failed: " +
                    $"manifest={manifestCount} existing={existingCount} selected={selectedClips.Count} " +
                    $"missingSamples={missingSampleCount} invalid={invalidCount}.");

            Debug.Log(
                "Missing-only Wulfa animation preflight complete: " +
                $"manifest={manifestCount} existing={existingCount} create={selectedClips.Count}. " +
                "No existing asset will be rewritten; Zhuangfy and Mifu are excluded.");

            List<AnimationClip> rebuilt = BuildAnimationClips(selectedClips, null, actorGeneratedRoot);
            if (rebuilt.Count != selectedClips.Count)
                throw new InvalidOperationException(
                    $"Missing-only Wulfa animation refresh was incomplete: selected={selectedClips.Count} rebuilt={rebuilt.Count}.");

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log(
                "Missing-only Wulfa animation refresh complete: " +
                $"manifest={manifestCount} existing={existingCount} created={rebuilt.Count} " +
                $"missingSamples={missingSampleCount} invalid={invalidCount}. " +
                "Zhuangfy and Mifu animation caches were not touched.");
        }

        /// <summary>
        /// Rebuilds only Wulfa's 11 item-widget clips, two private widget
        /// skeleton/mesh assets, prefab, and existing viewer-scene instance.
        /// Existing animation, mesh, and prefab assets are updated in place so
        /// their Unity GUIDs remain stable; the rest of the animation cache is
        /// loaded but never regenerated.
        /// </summary>
        public static void RefreshWulfaItemWidgetRecoveryAssets()
        {
            EnsureFolders();
            EnsureHGCompatRenderPipelineAssigned();

            string manifestAssetPath = ResolveManifestAssetPath(
                WulfaManifestAssetPath,
                LegacyWulfaManifestAssetPath);
            string manifestPath = Path.Combine(Directory.GetCurrentDirectory(), manifestAssetPath);
            if (!File.Exists(manifestPath))
                throw new FileNotFoundException("Wulfa recovery manifest is missing.", manifestPath);

            var manifest = Dict(ManifestMiniJson.Deserialize(File.ReadAllText(manifestPath, Encoding.UTF8)));
            string actorGeneratedRoot = ActorGeneratedRoot(manifestAssetPath, "Wulfa");
            EnsureActorFolders(actorGeneratedRoot, clearGeneratedAssets: false);

            var widgetClips = new List<object>();
            var guidBefore = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            foreach (object clipObj in List(manifest["clips"]))
            {
                var clipInfo = Dict(clipObj);
                string name = Str(clipInfo.TryGetValue("name", out object nameObj) ? nameObj : null);
                if (name.IndexOf("A_item_widget_wulfa_", StringComparison.OrdinalIgnoreCase) < 0)
                    continue;

                string sampleJson = Str(clipInfo.TryGetValue("sample_json", out object sampleObj) ? sampleObj : null);
                int matched = Int(clipInfo.TryGetValue("matched_transform_count", out object matchedObj) ? matchedObj : null);
                int missing = Int(clipInfo.TryGetValue("missing_transform_count", out object missingObj) ? missingObj : null);
                if (name.Length == 0 || sampleJson.Length == 0 || !File.Exists(sampleJson))
                    throw new InvalidOperationException($"Wulfa widget clip has no readable sample: {name} {sampleJson}");
                if (matched != 3 || missing != 0 || List(clipInfo["bones"]).Count != 3)
                    throw new InvalidOperationException(
                        $"Wulfa widget clip is not fully rebound: {name} matched={matched} missing={missing} " +
                        $"bones={List(clipInfo["bones"]).Count}");

                widgetClips.Add(clipObj);
                string assetPath = $"{actorGeneratedRoot}/Animations/{Safe(name)}.anim";
                string guid = AssetDatabase.AssetPathToGUID(assetPath);
                if (!string.IsNullOrEmpty(guid))
                    guidBefore[assetPath] = guid;
            }
            if (widgetClips.Count != 11)
                throw new InvalidOperationException($"Expected 11 Wulfa item-widget clips, found {widgetClips.Count}.");

            string prefabPath = $"{actorGeneratedRoot}/Prefabs/Wulfa.prefab";
            string prefabGuid = AssetDatabase.AssetPathToGUID(prefabPath);
            if (!string.IsNullOrEmpty(prefabGuid))
                guidBefore[prefabPath] = prefabGuid;
            foreach (string meshName in new[] { "S_item_widget_wulfa_01", "S_item_widget_wulfa_02" })
            {
                string meshPath = $"{actorGeneratedRoot}/Meshes/{Safe(meshName)}.asset";
                string meshGuid = AssetDatabase.AssetPathToGUID(meshPath);
                if (!string.IsNullOrEmpty(meshGuid))
                    guidBefore[meshPath] = meshGuid;
            }

            List<AnimationClip> rebuilt = BuildAnimationClips(widgetClips, null, actorGeneratedRoot);
            if (rebuilt.Count != widgetClips.Count)
                throw new InvalidOperationException(
                    $"Wulfa item-widget animation refresh was incomplete: selected={widgetClips.Count} rebuilt={rebuilt.Count}.");

            if (!File.Exists(Path.Combine(Directory.GetCurrentDirectory(), ViewerScenePath)))
                throw new FileNotFoundException("Build the shared character viewer scene before refreshing Wulfa widgets.", ViewerScenePath);
            Scene scene = EditorSceneManager.OpenScene(ViewerScenePath, OpenSceneMode.Single);
            GameObject previousWulfa = FindSceneGameObject("Wulfa");
            Transform previousParent = previousWulfa != null ? previousWulfa.transform.parent : FindSceneGameObject("Characters")?.transform;
            int previousSiblingIndex = previousWulfa != null ? previousWulfa.transform.GetSiblingIndex() : 0;
            bool previousActive = previousWulfa == null || previousWulfa.activeSelf;
            Vector3 previousLocalPosition = previousWulfa != null ? previousWulfa.transform.localPosition : Vector3.zero;
            Quaternion previousLocalRotation = previousWulfa != null ? previousWulfa.transform.localRotation : Quaternion.identity;
            Vector3 previousLocalScale = previousWulfa != null ? previousWulfa.transform.localScale : Vector3.one;

            ActorBuildResult actor = BuildActor(
                manifestAssetPath,
                "Wulfa",
                "Wulfa",
                Vector3.zero,
                previousActive,
                WulfaPreviewClipPreference,
                includeVariants: false,
                rebuildAnimationAssets: false,
                clearGeneratedAssets: false,
                rebuildMeshAssets: false);
            if (previousWulfa != null)
                UnityEngine.Object.DestroyImmediate(previousWulfa);
            if (previousParent != null)
            {
                actor.Root.transform.SetParent(previousParent, false);
                actor.Root.transform.SetSiblingIndex(Mathf.Clamp(previousSiblingIndex, 0, previousParent.childCount - 1));
            }
            actor.Root.transform.localPosition = previousLocalPosition;
            actor.Root.transform.localRotation = previousLocalRotation;
            actor.Root.transform.localScale = previousLocalScale;
            actor.Root.SetActive(previousActive);

            SampleActivePreviewAnimations(scene);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene, ViewerScenePath);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();

            foreach (var pair in guidBefore)
            {
                string guidAfter = AssetDatabase.AssetPathToGUID(pair.Key);
                if (!string.Equals(pair.Value, guidAfter, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException(
                        $"Targeted Wulfa widget refresh changed an existing GUID: {pair.Key} {pair.Value} -> {guidAfter}");
            }

            Debug.Log(
                "Targeted Wulfa item-widget refresh complete: clips=11 skinnedWidgets=2 unmatchedTracks=0. " +
                "Existing GUIDs were preserved; non-widget animation assets were not regenerated.");
        }

        /// <summary>
        /// Adds Zhuangfy's controller-proven widget03 entrance rig without
        /// rebuilding the body animation/mesh caches. The separately recovered
        /// widget loop is imported for inspection but is not auto-paired because
        /// its settled activation policy is still unsupported by runtime evidence.
        /// </summary>
        public static void RefreshZhuangfyWidget03RecoveryAssets()
        {
            EnsureFolders();
            EnsureHGCompatRenderPipelineAssigned();

            string manifestAssetPath = ResolveManifestAssetPath(
                ZhuangfyManifestAssetPath,
                LegacyZhuangfyManifestAssetPath);
            string manifestPath = Path.Combine(Directory.GetCurrentDirectory(), manifestAssetPath);
            string supplementPath = Path.Combine(
                Directory.GetCurrentDirectory(),
                ZhuangfyWidget03ManifestAssetPath);
            if (!File.Exists(manifestPath))
                throw new FileNotFoundException("Zhuangfy recovery manifest is missing.", manifestPath);
            if (!File.Exists(supplementPath))
                throw new FileNotFoundException(
                    "Build the Zhuangfy widget03 supplemental manifest first.",
                    supplementPath);

            var mainManifest = Dict(ManifestMiniJson.Deserialize(
                File.ReadAllText(manifestPath, Encoding.UTF8)));
            var supplement = Dict(ManifestMiniJson.Deserialize(
                File.ReadAllText(supplementPath, Encoding.UTF8)));
            string actorGeneratedRoot = ActorGeneratedRoot(manifestAssetPath, "Zhuangfy");
            EnsureActorFolders(actorGeneratedRoot, clearGeneratedAssets: false);

            var widgetClips = new List<object>();
            var guidBefore = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            foreach (object clipObj in List(supplement["clips"]))
            {
                var clipInfo = Dict(clipObj);
                string name = Str(clipInfo.TryGetValue("name", out object nameObj) ? nameObj : null);
                string sampleJson = Str(
                    clipInfo.TryGetValue("sample_json", out object sampleObj) ? sampleObj : null);
                int matched = Int(
                    clipInfo.TryGetValue("matched_transform_count", out object matchedObj) ? matchedObj : null);
                int missing = Int(
                    clipInfo.TryGetValue("missing_transform_count", out object missingObj) ? missingObj : null);
                if (name.Length == 0 || sampleJson.Length == 0 || !File.Exists(sampleJson))
                    throw new InvalidOperationException(
                        $"Zhuangfy widget03 clip has no readable sample: {name} {sampleJson}");
                if (matched != 39 || missing != 0 || List(clipInfo["bones"]).Count != 39)
                    throw new InvalidOperationException(
                        $"Zhuangfy widget03 clip is not fully rebound: {name} matched={matched} " +
                        $"missing={missing} bones={List(clipInfo["bones"]).Count}");

                widgetClips.Add(clipObj);
                RememberExistingGuid(
                    guidBefore,
                    $"{actorGeneratedRoot}/Animations/{Safe(name)}.anim");
            }
            if (widgetClips.Count != 2)
                throw new InvalidOperationException(
                    $"Expected two Zhuangfy widget03 clips, found {widgetClips.Count}.");

            string actorPrefix = Str(
                mainManifest.TryGetValue("model", out object modelObj) ? modelObj : null,
                "actor_zhuangfy");
            RememberExistingGuid(
                guidBefore,
                $"{actorGeneratedRoot}/Meshes/{Safe("S_item_widget_zhuangfy_03_lod0")}.asset");
            RememberExistingGuid(
                guidBefore,
                $"{actorGeneratedRoot}/Materials/{Safe(actorPrefix)}_{Safe("pathid_6143140184279625830")}.mat");
            RememberExistingGuid(guidBefore, $"{actorGeneratedRoot}/Prefabs/Zhuangfy.prefab");

            List<AnimationClip> rebuilt = BuildAnimationClips(widgetClips, null, actorGeneratedRoot);
            if (rebuilt.Count != 2)
                throw new InvalidOperationException(
                    $"Zhuangfy widget03 clip refresh was incomplete: rebuilt={rebuilt.Count}.");

            if (!File.Exists(Path.Combine(Directory.GetCurrentDirectory(), ViewerScenePath)))
                throw new FileNotFoundException(
                    "Build the shared character viewer scene before refreshing Zhuangfy widget03.",
                    ViewerScenePath);
            Scene scene = EditorSceneManager.OpenScene(ViewerScenePath, OpenSceneMode.Single);
            GameObject previous = FindSceneGameObject("Zhuangfy");
            Transform previousParent = previous != null
                ? previous.transform.parent
                : FindSceneGameObject("Characters")?.transform;
            int previousSiblingIndex = previous != null ? previous.transform.GetSiblingIndex() : 0;
            bool previousActive = previous == null || previous.activeSelf;
            Vector3 previousLocalPosition = previous != null ? previous.transform.localPosition : Vector3.zero;
            Quaternion previousLocalRotation = previous != null ? previous.transform.localRotation : Quaternion.identity;
            Vector3 previousLocalScale = previous != null ? previous.transform.localScale : Vector3.one;

            ActorBuildResult actor = BuildActor(
                manifestAssetPath,
                "Zhuangfy",
                "Zhuangfy",
                Vector3.zero,
                previousActive,
                ZhuangfyPreviewClipPreference,
                includeVariants: false,
                rebuildAnimationAssets: false,
                clearGeneratedAssets: false,
                rebuildMeshAssets: false);
            if (previous != null)
                UnityEngine.Object.DestroyImmediate(previous);
            if (previousParent != null)
            {
                actor.Root.transform.SetParent(previousParent, false);
                actor.Root.transform.SetSiblingIndex(
                    Mathf.Clamp(previousSiblingIndex, 0, previousParent.childCount - 1));
            }
            actor.Root.transform.localPosition = previousLocalPosition;
            actor.Root.transform.localRotation = previousLocalRotation;
            actor.Root.transform.localScale = previousLocalScale;
            actor.Root.SetActive(previousActive);

            Transform widgetRoot = actor.Root.transform.Find(
                "RecoveredProps/Zhuangfy_Deco_3_Item_Widget_03");
            if (widgetRoot == null)
                throw new InvalidOperationException("Zhuangfy widget03 private root was not built.");
            var widgetRenderer = widgetRoot.GetComponentInChildren<SkinnedMeshRenderer>(true);
            if (widgetRenderer == null || widgetRenderer.sharedMesh == null || widgetRenderer.enabled)
                throw new InvalidOperationException(
                    "Zhuangfy widget03 must have one cached skinned mesh and remain hidden by default.");

            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene, ViewerScenePath);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            VerifyExistingGuids(guidBefore, "Zhuangfy widget03 refresh");

            Debug.Log(
                "Targeted Zhuangfy widget03 recovery complete: privateTransforms=39, " +
                "clips=2, skinnedWidgets=1, unmatchedTracks=0. Entrance pairing enabled; " +
                "unproven widget loop remains disabled; existing GUIDs preserved.");
        }

        private static void RememberExistingGuid(
            Dictionary<string, string> guidByPath,
            string assetPath)
        {
            string guid = AssetDatabase.AssetPathToGUID(assetPath);
            if (!string.IsNullOrEmpty(guid))
                guidByPath[assetPath] = guid;
        }

        private static void VerifyExistingGuids(
            Dictionary<string, string> guidBefore,
            string operation)
        {
            foreach (var pair in guidBefore)
            {
                string guidAfter = AssetDatabase.AssetPathToGUID(pair.Key);
                if (!string.Equals(pair.Value, guidAfter, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException(
                        $"{operation} changed an existing GUID: {pair.Key} {pair.Value} -> {guidAfter}");
            }
        }

        public static void RenderSharedViewerPreview()
        {
            EnsureHGCompatRenderPipelineAssigned();
            if (!File.Exists(Path.Combine(Directory.GetCurrentDirectory(), ViewerScenePath)))
                throw new FileNotFoundException("Build the shared character viewer scene before rendering a preview.", ViewerScenePath);

            var scene = EditorSceneManager.OpenScene(ViewerScenePath, OpenSceneMode.Single);
            EnsureOriginalStylePresentationScene(scene);
            ApplyGeneratedMaterialProfileFlags();
            ApplyGeneratedTextureImportProfiles();
            PruneLowerQualityMeshLodsFromOpenScene();
            CharacterRecoveryPresentationController presentation =
                UnityEngine.Object.FindObjectOfType<
                    CharacterRecoveryPresentationController>(true);
            CharacterRecoveryRig activeRig = null;
            CharacterRecoveryActorCatalog catalog =
                UnityEngine.Object.FindObjectOfType<CharacterRecoveryActorCatalog>(true);
            CharacterRecoveryActorCatalogEntry previewEntry =
                catalog != null && catalog.entries != null
                    ? catalog.entries
                        .Where(entry => entry != null)
                        .OrderBy(
                            entry => string.IsNullOrEmpty(entry.displayName)
                                ? entry.rootName
                                : entry.displayName,
                            StringComparer.Ordinal)
                        .FirstOrDefault()
                    : null;
            if (previewEntry != null)
            {
                GameObject characters = FindSceneGameObject("Characters");
                Transform root = characters != null
                    ? FindDirectChild(characters.transform, previewEntry.rootName)
                    : null;
                activeRig = root != null
                    ? root.GetComponent<CharacterRecoveryRig>()
                    : null;
            }
            if (activeRig == null)
                activeRig = UnityEngine.Object.FindObjectsOfType<CharacterRecoveryRig>(true)
                    .FirstOrDefault(candidate =>
                        candidate != null && candidate.gameObject.activeInHierarchy);
            SampleActivePreviewAnimations(scene, activeRig);
            CharacterRecoveryPresentationProfile profile =
                activeRig != null
                    ? EndfieldPlayableCharInfoProfileBuilder.LoadProfile(
                        activeRig.gameObject.name)
                    : null;
            if (presentation == null ||
                activeRig == null ||
                profile == null ||
                !presentation.ApplyProfile(profile, activeRig))
                throw new InvalidDataException(
                    "Shared viewer has no active source-recovered presentation profile.");

            string previewPath = Path.GetFullPath(Path.Combine(
                Application.dataPath,
                "../../scratch/character_recovery/character_recovery_viewer.png"));
            Directory.CreateDirectory(Path.GetDirectoryName(previewPath) ?? ".");
            RenderPreview(
                previewPath,
                Camera.main ?? UnityEngine.Object.FindObjectOfType<Camera>(true),
                PlayableCharInfoPreviewRenderWidth,
                PlayableCharInfoPreviewRenderHeight);
            AssetDatabase.Refresh();
            Debug.Log($"Rendered character recovery viewer preview: {previewPath}");
        }

        [MenuItem("Endfield/Character Recovery Lab/Render All Playable Character Previews")]
        public static void RenderPlayableCharacterPreviews()
        {
            string outputDirectory = Path.GetFullPath(Path.Combine(
                Application.dataPath,
                "../../scratch/character_ui_import/renders"));
            string reportPath = Path.Combine(
                outputDirectory,
                "playable_character_preview_manifest.json");
            Directory.CreateDirectory(outputDirectory);

            var report = new PlayableCharacterPreviewRenderManifest
            {
                output_directory = outputDirectory,
            };
            var records = new List<PlayableCharacterPreviewRenderRecord>();
            Exception fatalError = null;

            try
            {
                ManifestCharacterSpec[] characters = FilterPreviewCharacters(
                    PlayableCatalogCharacters());
                report.character_count = characters.Length;
                var expectedPngNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                foreach (ManifestCharacterSpec character in characters)
                {
                    PlayableCharacterPreviewRenderRecord record =
                        CreatePlayableCharacterPreviewRecord(character);
                    if (!expectedPngNames.Add(record.png))
                    {
                        throw new InvalidOperationException(
                            $"Playable-character preview PNG name is not unique: {record.png}");
                    }
                    records.Add(record);
                }
                WritePlayableCharacterPreviewReport(reportPath, report, records);
                if (characters.Length == 0)
                {
                    throw new InvalidOperationException(
                        $"No enabled playable characters were found in " +
                        $"{PlayableCharacterUiCatalogAssetPath}.");
                }
                foreach (PlayableCharacterPreviewRenderRecord record in records)
                {
                    string expectedPng = Path.Combine(outputDirectory, record.png);
                    if (File.Exists(expectedPng))
                        File.Delete(expectedPng);
                }

                EnsureHGCompatRenderPipelineAssigned();
                if (!File.Exists(Path.Combine(Directory.GetCurrentDirectory(), ViewerScenePath)))
                {
                    throw new FileNotFoundException(
                        "Build the shared character viewer scene before rendering playable-character previews.",
                        ViewerScenePath);
                }

                Scene scene = EditorSceneManager.OpenScene(ViewerScenePath, OpenSceneMode.Single);
                EnsureOriginalStylePresentationScene(scene);
                Transform charactersRoot = FindSceneGameObject("Characters")?.transform;
                if (charactersRoot == null)
                    throw new InvalidOperationException("Shared viewer scene has no Characters root.");
                Camera camera = Camera.main ?? UnityEngine.Object.FindObjectOfType<Camera>(true);
                if (camera == null)
                    throw new InvalidOperationException("Shared viewer scene has no camera.");

                Transform lightingRoot = FindSceneGameObject("Lighting")?.transform;
                ConfigurePreviewLighting(scene, lightingRoot);
                ApplyGeneratedMaterialProfileFlags();
                ApplyGeneratedTextureImportProfiles(
                    characters.Select(CharacterGeneratedAssetRoot).ToArray());
                ClearPlayableCharacterPreviewActors(charactersRoot);
                AssertPlayableCharacterPreviewIsolation(charactersRoot, null);
                EditorUtility.UnloadUnusedAssetsImmediate();

                for (int index = 0; index < characters.Length; index++)
                {
                    ManifestCharacterSpec character = characters[index];
                    PlayableCharacterPreviewRenderRecord record = records[index];
                    AssertPlayableCharacterPreviewIsolation(charactersRoot, null);
                    RenderPlayableCharacterPreview(
                        scene,
                        charactersRoot,
                        camera,
                        character,
                        outputDirectory,
                        record);

                    // Actor cleanup and isolation are hard invariants. If either
                    // fails, continuing could render two actors into later PNGs.
                    AssertPlayableCharacterPreviewIsolation(charactersRoot, null);
                    EditorUtility.UnloadUnusedAssetsImmediate();
                    WritePlayableCharacterPreviewReport(reportPath, report, records);
                }

                WritePlayableCharacterPreviewReport(reportPath, report, records);
                if (!TryValidatePlayableCharacterPreviewCompleteness(
                        report,
                        records,
                        out string completenessError))
                {
                    throw new InvalidOperationException(completenessError);
                }
                report.status = report.failed > 0 ? "partial_failure" : "ok";
            }
            catch (Exception exception)
            {
                fatalError = exception;
                report.status = "failed";
                report.error = exception.ToString();
            }
            finally
            {
                try
                {
                    string viewerSceneFullPath = Path.Combine(
                        Directory.GetCurrentDirectory(),
                        ViewerScenePath);
                    if (File.Exists(viewerSceneFullPath))
                        EditorSceneManager.OpenScene(ViewerScenePath, OpenSceneMode.Single);
                }
                catch (Exception restoreException)
                {
                    string restoreError =
                        "Could not restore the saved shared viewer scene: " + restoreException;
                    report.status = "failed";
                    report.error = string.IsNullOrEmpty(report.error)
                        ? restoreError
                        : report.error + "\n" + restoreError;
                    if (fatalError == null)
                        fatalError = restoreException;
                }
                try
                {
                    WritePlayableCharacterPreviewReport(reportPath, report, records);
                }
                catch (Exception reportException)
                {
                    if (fatalError == null)
                        fatalError = reportException;
                    else
                        Debug.LogException(reportException);
                }
            }

            if (fatalError != null)
            {
                throw new InvalidOperationException(
                    $"Playable-character preview rendering failed before completion. " +
                    $"See {reportPath}",
                    fatalError);
            }
            if (report.failed > 0)
            {
                throw new InvalidOperationException(
                    $"Playable-character preview rendering completed with " +
                    $"{report.failed}/{report.character_count} failed actor(s). " +
                    $"See {reportPath}");
            }

            AssetDatabase.Refresh();
            Debug.Log(
                $"Rendered {report.succeeded} playable-character previews: " +
                $"{outputDirectory}");
        }

        private static ManifestCharacterSpec[] FilterPreviewCharacters(
            ManifestCharacterSpec[] characters)
        {
            string raw = Environment.GetEnvironmentVariable(
                "ENDFIELD_PREVIEW_ACTORS") ?? string.Empty;
            if (string.IsNullOrWhiteSpace(raw))
                return characters ?? Array.Empty<ManifestCharacterSpec>();

            var requested = new HashSet<string>(
                raw.Split(new[] { ',', ';' }, StringSplitOptions.RemoveEmptyEntries)
                    .Select(value => value.Trim())
                    .Where(value => !string.IsNullOrEmpty(value)),
                StringComparer.OrdinalIgnoreCase);
            ManifestCharacterSpec[] selected = (characters ?? Array.Empty<ManifestCharacterSpec>())
                .Where(character =>
                    requested.Contains(character.RootName) ||
                    requested.Contains(character.DisplayName))
                .ToArray();
            if (selected.Length != requested.Count)
            {
                var matched = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                foreach (ManifestCharacterSpec character in selected)
                {
                    matched.Add(character.RootName);
                    matched.Add(character.DisplayName);
                }
                string[] missing = requested.Where(value => !matched.Contains(value)).ToArray();
                if (missing.Length > 0)
                    throw new InvalidDataException(
                        "Requested preview actors are absent from the playable catalog: " +
                        string.Join(", ", missing));
            }
            return selected;
        }

        private static string CharacterGeneratedAssetRoot(
            ManifestCharacterSpec character)
        {
            string prefabPath = character != null
                ? character.PrefabAssetPath ?? string.Empty
                : string.Empty;
            int marker = prefabPath.IndexOf(
                "/Prefabs/",
                StringComparison.OrdinalIgnoreCase);
            if (marker <= 0)
                throw new InvalidDataException(
                    "Playable-character prefab path has no generated actor root: " +
                    prefabPath);
            return prefabPath.Substring(0, marker);
        }

        [MenuItem("Endfield/Character Recovery Lab/Render Source-Bound Item Widget Previews")]
        public static void RenderPlayableCharacterItemWidgetPreviews()
        {
            string outputDirectory = Path.GetFullPath(Path.Combine(
                Application.dataPath,
                "../../scratch/character_ui_import/widget_renders"));
            string reportPath = Path.Combine(
                outputDirectory,
                "playable_item_widget_preview_manifest.json");
            Directory.CreateDirectory(outputDirectory);
            foreach (string stalePng in Directory.GetFiles(outputDirectory, "*.png"))
                File.Delete(stalePng);

            var report = new PlayableItemWidgetPreviewManifest
            {
                output_directory = outputDirectory,
            };
            var records = new List<PlayableItemWidgetPreviewRecord>();
            Exception fatalError = null;

            try
            {
                EnsureHGCompatRenderPipelineAssigned();
                if (!File.Exists(Path.Combine(Directory.GetCurrentDirectory(), ViewerScenePath)))
                {
                    throw new FileNotFoundException(
                        "Build the shared character viewer scene before rendering item-widget previews.",
                        ViewerScenePath);
                }

                Scene scene = EditorSceneManager.OpenScene(ViewerScenePath, OpenSceneMode.Single);
                EnsureOriginalStylePresentationScene(scene);
                Transform charactersRoot = FindSceneGameObject("Characters")?.transform;
                if (charactersRoot == null)
                    throw new InvalidOperationException("Shared viewer scene has no Characters root.");
                Camera camera = Camera.main ?? UnityEngine.Object.FindObjectOfType<Camera>(true);
                if (camera == null)
                    throw new InvalidOperationException("Shared viewer scene has no camera.");

                ConfigurePreviewLighting(scene, FindSceneGameObject("Lighting")?.transform);
                ApplyGeneratedMaterialProfileFlags();
                ApplyGeneratedTextureImportProfiles();
                ClearPlayableCharacterPreviewActors(charactersRoot);

                foreach (ManifestCharacterSpec character in PlayableCatalogCharacters())
                {
                    GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(
                        character.PrefabAssetPath);
                    EndfieldOverviewPlayback prefabPlayback = prefab != null
                        ? prefab.GetComponent<EndfieldOverviewPlayback>()
                        : null;
                    if (prefabPlayback == null || prefabPlayback.itemWidgets == null ||
                        prefabPlayback.itemWidgets.Length == 0)
                    {
                        continue;
                    }

                    var record = new PlayableItemWidgetPreviewRecord
                    {
                        display = character.DisplayName,
                        root = character.RootName,
                        prefab = character.PrefabAssetPath,
                        png = Safe(character.RootName).ToLowerInvariant() + "_ui_entry.png",
                    };
                    records.Add(record);
                    GameObject actorInstance = null;
                    try
                    {
                        actorInstance = PrefabUtility.InstantiatePrefab(prefab, scene) as GameObject;
                        if (actorInstance == null)
                            throw new InvalidOperationException(
                                $"Could not instantiate item-widget preview prefab: {character.PrefabAssetPath}");
                        actorInstance.name = character.RootName;
                        actorInstance.transform.SetParent(charactersRoot, false);
                        actorInstance.transform.localPosition = Vector3.zero;
                        actorInstance.transform.localRotation = Quaternion.identity;
                        actorInstance.transform.localScale = Vector3.one;
                        actorInstance.SetActive(true);
                        AssertPlayableCharacterPreviewIsolation(charactersRoot, actorInstance);

                        Animation animation = actorInstance.GetComponent<Animation>();
                        EndfieldOverviewPlayback playback =
                            actorInstance.GetComponent<EndfieldOverviewPlayback>();
                        if (animation == null || playback == null)
                            throw new InvalidOperationException(
                                $"Item-widget preview components are missing on {character.RootName}.");
                        AnimationState bodyState = animation[playback.startClip];
                        if (bodyState == null || bodyState.clip == null)
                            throw new InvalidOperationException(
                                $"Recovered overview start clip is missing on {character.RootName}: " +
                                playback.startClip);

                        animation.Stop();
                        SetRecoveredPropVisibility(actorInstance, Array.Empty<string>());

                        var propPaths = new List<string>();
                        var widgetClips = new List<string>();
                        var widgetAnimationClips = new List<AnimationClip>();
                        var activationEvidence = new List<string>();
                        foreach (EndfieldOverviewItemWidgetBinding binding in playback.itemWidgets)
                        {
                            string clipName = !string.IsNullOrEmpty(binding.startClip)
                                ? binding.startClip
                                : binding.loopClip;
                            if (string.IsNullOrEmpty(binding.propPath) || string.IsNullOrEmpty(clipName))
                                continue;
                            AnimationState widgetState = animation[clipName];
                            if (widgetState == null || widgetState.clip == null)
                            {
                                throw new InvalidOperationException(
                                    $"Recovered item-widget clip is missing on {character.RootName}: " +
                                    $"clip={clipName} prop={binding.propPath}");
                            }
                            propPaths.Add(binding.propPath);
                            widgetClips.Add(clipName);
                            widgetAnimationClips.Add(widgetState.clip);
                            activationEvidence.Add(binding.activationEvidence ?? "");
                        }
                        if (propPaths.Count == 0)
                            throw new InvalidOperationException(
                                $"No source-bound item-widget entry clips were sampleable on {character.RootName}.");
                        SetRecoveredPropVisibility(actorInstance, propPaths);
                        Dictionary<SkinnedMeshRenderer, bool>
                            sourceEnabledPropRendererVisibility = actorInstance
                                .GetComponentsInChildren<SkinnedMeshRenderer>(true)
                                .Where(renderer =>
                                    renderer != null && IsRecoveredPropRenderer(renderer))
                                .ToDictionary(renderer => renderer, renderer => renderer.enabled);

                        // Direct AnimationClip sampling does not execute the
                        // runtime Overview Start path. Apply only its recovered
                        // parameter consumers so source-hidden embedded weapons
                        // cannot contaminate the interaction preview.
                        playback.ApplyRecoveredParametersNow();
                        ItemWidgetDiagnosticSampleSelection sampleSelection =
                            SelectItemWidgetDiagnosticSample(
                                actorInstance,
                                playback,
                                bodyState.clip,
                                widgetAnimationClips,
                                sourceEnabledPropRendererVisibility);
                        SampleItemWidgetDiagnosticPose(
                            actorInstance,
                            playback,
                            bodyState.clip,
                            widgetAnimationClips,
                            sampleSelection.normalized,
                            sampleSelection.sourceEnabledPropRendererVisibility);
                        float bodySampleSeconds = Mathf.Clamp(
                            bodyState.clip.length * sampleSelection.normalized,
                            0f,
                            Mathf.Max(bodyState.clip.length, 0f));
                        EndfieldOverviewRendererVisibility rendererVisibility =
                            actorInstance.GetComponent<EndfieldOverviewRendererVisibility>();
                        if (rendererVisibility != null &&
                            playback.weaponHide >= rendererVisibility.hiddenAtOrAbove)
                        {
                            foreach (Renderer weaponRenderer in rendererVisibility.weaponRenderers)
                            {
                                if (weaponRenderer != null && weaponRenderer.enabled)
                                {
                                    throw new InvalidOperationException(
                                        $"Overview weapon visibility was not applied on {character.RootName}: " +
                                        weaponRenderer.name);
                                }
                            }
                        }

                        CharacterRecoveryRig rig =
                            actorInstance.GetComponent<CharacterRecoveryRig>();
                        CharacterProceduralIk poseCorrection = rig != null
                            ? rig.PoseCorrection
                            : actorInstance.GetComponentInChildren<CharacterProceduralIk>(true);
                        if (poseCorrection != null)
                            poseCorrection.Evaluate();

                        if (!TryComputePlayableCharacterPreviewBounds(
                                actorInstance,
                                out Bounds bounds,
                                out int eligibleRendererCount,
                                out string boundsError))
                        {
                            throw new InvalidOperationException(
                                $"Could not compute item-widget preview bounds for " +
                                $"{character.DisplayName}: {boundsError}");
                        }
                        float outputAspect = (float)PreviewRenderWidth / PreviewRenderHeight;
                        FramePlayableCharacterPreviewCamera(camera, bounds, outputAspect);
                        ConfigureReferenceBackdrop(
                            scene,
                            FindBackdropRoot(),
                            camera,
                            bounds,
                            outputAspect);
                        CharacterRecoveryCameraController controller =
                            camera.GetComponent<CharacterRecoveryCameraController>();
                        if (controller != null)
                        {
                            ConfigureCameraController(controller);
                            controller.SetFocus(
                                rig != null ? rig.FocusTarget : actorInstance.transform,
                                bounds);
                        }
                        ConfigureRosterFeaturePresentation(
                            scene,
                            camera,
                            character.RootName,
                            actorInstance,
                            rig);

                        string outputPath = Path.Combine(outputDirectory, record.png);
                        AssertItemWidgetOverlapRenderersVisibleBeforeRender(
                            actorInstance,
                            sampleSelection.overlapRendererPaths);
                        record.widget_renderers = CaptureItemWidgetRendererDiagnostics(
                            actorInstance,
                            camera,
                            outputDirectory,
                            character.RootName);
                        RenderPreview(
                            outputPath,
                            camera,
                            PreviewRenderWidth,
                            PreviewRenderHeight);
                        ValidateRosterFeatureWidgetPng(outputPath, record);
                        record.body_accessory_renderers =
                            CaptureBodyAccessoryRendererDiagnostics(
                                actorInstance,
                                camera,
                                outputDirectory,
                                character.RootName);
                        record.body_clip = bodyState.clip.name;
                        record.sample = sampleSelection.normalized;
                        record.body_sample_seconds = bodySampleSeconds;
                        record.sample_evidence = sampleSelection.evidence;
                        record.sample_fallback_used = sampleSelection.fallbackUsed;
                        record.sample_interval_normalized_start =
                            sampleSelection.intervalNormalizedStart;
                        record.sample_interval_normalized_end =
                            sampleSelection.intervalNormalizedEnd;
                        record.sample_interval_seconds_start =
                            sampleSelection.intervalNormalizedStart >= 0f
                                ? bodyState.clip.length * sampleSelection.intervalNormalizedStart
                                : -1f;
                        record.sample_interval_seconds_end =
                            sampleSelection.intervalNormalizedEnd >= 0f
                                ? bodyState.clip.length * sampleSelection.intervalNormalizedEnd
                                : -1f;
                        record.sample_scan_count = sampleSelection.scanCount;
                        record.sample_overlap_renderer_paths =
                            sampleSelection.overlapRendererPaths;
                        record.prop_paths = propPaths.ToArray();
                        record.widget_clips = widgetClips.ToArray();
                        record.activation_evidence = activationEvidence.ToArray();
                        record.eligible_renderer_count = eligibleRendererCount;
                        record.status = "ok";
                        report.succeeded++;
                        Debug.Log(
                            $"Rendered source-bound item-widget preview: " +
                            $"root={character.RootName} widgets={widgetClips.Count} path={outputPath}");
                    }
                    catch (Exception exception)
                    {
                        record.status = "failed";
                        record.error = exception.ToString();
                        report.failed++;
                        Debug.LogError(
                            $"Item-widget preview failed: root={character.RootName}, " +
                            $"error={exception}");
                    }
                    finally
                    {
                        if (actorInstance != null)
                            UnityEngine.Object.DestroyImmediate(actorInstance);
                        AssertPlayableCharacterPreviewIsolation(charactersRoot, null);
                        EditorUtility.UnloadUnusedAssetsImmediate();
                    }
                }
                report.source_bound_character_count = records.Count;
                report.status = report.failed == 0 ? "ok" : "partial_failure";
            }
            catch (Exception exception)
            {
                fatalError = exception;
                report.status = "failed";
            }
            finally
            {
                report.renders = records.ToArray();
                File.WriteAllText(
                    reportPath,
                    JsonUtility.ToJson(report, true) + Environment.NewLine,
                    Encoding.UTF8);
                string viewerSceneFullPath = Path.Combine(
                    Directory.GetCurrentDirectory(),
                    ViewerScenePath);
                if (File.Exists(viewerSceneFullPath))
                    EditorSceneManager.OpenScene(ViewerScenePath, OpenSceneMode.Single);
            }

            if (fatalError != null)
                throw new InvalidOperationException(
                    $"Source-bound item-widget preview rendering failed. See {reportPath}",
                    fatalError);
            if (report.failed > 0)
                throw new InvalidOperationException(
                    $"Source-bound item-widget preview rendering completed with " +
                    $"{report.failed} failed actor(s). See {reportPath}");

            AssetDatabase.Refresh();
            Debug.Log(
                $"Rendered {report.succeeded} source-bound item-widget previews: " +
                outputDirectory);
        }

        private static ItemWidgetDiagnosticSampleSelection SelectItemWidgetDiagnosticSample(
            GameObject actorRoot,
            EndfieldOverviewPlayback playback,
            AnimationClip bodyClip,
            IReadOnlyList<AnimationClip> widgetClips,
            IReadOnlyDictionary<SkinnedMeshRenderer, bool>
                sourceEnabledPropRendererVisibility)
        {
            if (actorRoot == null)
                throw new ArgumentNullException(nameof(actorRoot));
            if (bodyClip == null)
                throw new ArgumentNullException(nameof(bodyClip));

            float maximumSampleFrames = Mathf.Max(
                bodyClip.length * Mathf.Max(bodyClip.frameRate, 1f),
                1f);
            foreach (AnimationClip clip in widgetClips ?? Array.Empty<AnimationClip>())
            {
                if (clip == null)
                    continue;
                maximumSampleFrames = Mathf.Max(
                    maximumSampleFrames,
                    clip.length * Mathf.Max(clip.frameRate, 1f));
            }
            int scanCount = Mathf.Clamp(
                Mathf.CeilToInt(maximumSampleFrames) + 1,
                2,
                ItemWidgetPreviewMaximumScanSamples);
            var selection = new ItemWidgetDiagnosticSampleSelection
            {
                scanCount = scanCount,
                sourceEnabledPropRendererVisibility =
                    sourceEnabledPropRendererVisibility != null
                        ? new Dictionary<SkinnedMeshRenderer, bool>(
                            sourceEnabledPropRendererVisibility)
                        : new Dictionary<SkinnedMeshRenderer, bool>(),
            };

            int intervalStart = -1;
            int intervalEnd = -1;
            for (int index = 0; index < scanCount; index++)
            {
                float normalized = (float)index / (scanCount - 1);
                SampleItemWidgetDiagnosticPose(
                    actorRoot,
                    playback,
                    bodyClip,
                    widgetClips,
                    normalized,
                    selection.sourceEnabledPropRendererVisibility);
                bool overlaps = TryGetItemWidgetOverlapRendererPaths(
                    actorRoot,
                    out _).Length > 0;
                if (overlaps)
                {
                    if (intervalStart < 0)
                        intervalStart = index;
                    intervalEnd = index;
                }
                else if (intervalStart >= 0)
                {
                    break;
                }
            }

            if (intervalStart < 0 || intervalEnd < intervalStart)
                return selection;

            selection.intervalNormalizedStart =
                (float)intervalStart / (scanCount - 1);
            selection.intervalNormalizedEnd =
                (float)intervalEnd / (scanCount - 1);
            selection.normalized =
                (selection.intervalNormalizedStart + selection.intervalNormalizedEnd) * 0.5f;
            selection.fallbackUsed = false;
            selection.evidence =
                "midpoint_of_first_continuous_source_sampled_widget_body_overlap_interval";
            SampleItemWidgetDiagnosticPose(
                actorRoot,
                playback,
                bodyClip,
                widgetClips,
                selection.normalized,
                selection.sourceEnabledPropRendererVisibility);
            selection.overlapRendererPaths =
                TryGetItemWidgetOverlapRendererPaths(actorRoot, out _);
            if (selection.overlapRendererPaths.Length == 0)
            {
                throw new InvalidOperationException(
                    "Item-widget diagnostic interval midpoint did not preserve its " +
                    "source-sampled body overlap evidence.");
            }
            return selection;
        }

        private static void SampleItemWidgetDiagnosticPose(
            GameObject actorRoot,
            EndfieldOverviewPlayback playback,
            AnimationClip bodyClip,
            IReadOnlyList<AnimationClip> widgetClips,
            float normalized,
            IReadOnlyDictionary<SkinnedMeshRenderer, bool>
                sourceEnabledPropRendererVisibility = null)
        {
            if (sourceEnabledPropRendererVisibility != null)
            {
                foreach (SkinnedMeshRenderer renderer in
                         actorRoot.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                {
                    if (renderer != null && IsRecoveredPropRenderer(renderer))
                    {
                        renderer.enabled =
                            sourceEnabledPropRendererVisibility.TryGetValue(
                                renderer,
                                out bool propFamilyEnabled) && propFamilyEnabled;
                    }
                }
            }
            float clampedNormalized = Mathf.Clamp01(normalized);
            bodyClip.SampleAnimation(
                actorRoot,
                Mathf.Clamp(
                    bodyClip.length * clampedNormalized,
                    0f,
                    Mathf.Max(bodyClip.length, 0f)));
            foreach (AnimationClip clip in widgetClips ?? Array.Empty<AnimationClip>())
            {
                if (clip == null)
                    continue;
                clip.SampleAnimation(
                    actorRoot,
                    Mathf.Clamp(
                        clip.length * clampedNormalized,
                        0f,
                        Mathf.Max(clip.length, 0f)));
            }
            if (playback != null)
                playback.ApplyRecoveredParametersNow();
        }

        private static string[] TryGetItemWidgetOverlapRendererPaths(
            GameObject actorRoot,
            out Bounds bodyBounds)
        {
            if (!TryComputePlayableCharacterPreviewBounds(
                    actorRoot,
                    out bodyBounds,
                    out _,
                    out _))
            {
                return Array.Empty<string>();
            }

            var paths = new List<string>();
            foreach (SkinnedMeshRenderer renderer in
                     actorRoot.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                if (renderer == null ||
                    !renderer.enabled ||
                    !renderer.gameObject.activeInHierarchy ||
                    renderer.sharedMesh == null ||
                    renderer.sharedMesh.vertexCount <= 0 ||
                    !IsRecoveredPropRenderer(renderer))
                {
                    continue;
                }

                Transform rootBone = renderer.rootBone;
                Vector3 scale = rootBone != null ? rootBone.lossyScale : renderer.transform.lossyScale;
                Bounds widgetBounds = renderer.bounds;
                if (!IsFinite(scale) ||
                    Mathf.Max(Mathf.Abs(scale.x), Mathf.Abs(scale.y), Mathf.Abs(scale.z)) <
                    ItemWidgetPreviewMinimumVisibleScale ||
                    !IsFinite(widgetBounds.center) ||
                    !IsFinite(widgetBounds.size) ||
                    Mathf.Max(widgetBounds.size.x, widgetBounds.size.y, widgetBounds.size.z) <
                    PlayablePreviewMinimumBoundsSpan)
                {
                    continue;
                }

                bool overlapsBodyFraming =
                    widgetBounds.min.x <= bodyBounds.max.x &&
                    widgetBounds.max.x >= bodyBounds.min.x &&
                    widgetBounds.min.y <= bodyBounds.max.y &&
                    widgetBounds.max.y >= bodyBounds.min.y;
                if (overlapsBodyFraming)
                {
                    paths.Add(RelativeTransformPath(
                        actorRoot.transform,
                        renderer.transform));
                }
            }
            paths.Sort(StringComparer.Ordinal);
            return paths.ToArray();
        }

        private static PlayableCharacterPreviewRenderRecord CreatePlayableCharacterPreviewRecord(
            ManifestCharacterSpec character)
        {
            string outputFileName = Safe(character.RootName).ToLowerInvariant() + ".png";
            return new PlayableCharacterPreviewRenderRecord
            {
                display = character.DisplayName,
                root = character.RootName,
                manifest = character.ManifestAssetPath,
                prefab = character.PrefabAssetPath,
                png = outputFileName,
                clip = character.PreviewClipPreference != null &&
                       character.PreviewClipPreference.Length > 0
                    ? character.PreviewClipPreference[0]
                    : "",
                // Animation recovery is intentionally out of scope here. Use
                // the source overview-loop entry rather than fitting a pose to
                // a screenshot.
                sample = 0.0f,
            };
        }

        private static void RenderPlayableCharacterPreview(
            Scene scene,
            Transform charactersRoot,
            Camera camera,
            ManifestCharacterSpec character,
            string outputDirectory,
            PlayableCharacterPreviewRenderRecord record)
        {
            string outputPath = Path.Combine(outputDirectory, record.png);
            GameObject actorInstance = null;
            Exception infrastructureFailure = null;

            try
            {
                string manifestPath = Path.Combine(
                    Directory.GetCurrentDirectory(),
                    character.ManifestAssetPath);
                if (!File.Exists(manifestPath))
                {
                    throw new FileNotFoundException(
                        $"Playable-character manifest is missing: {character.DisplayName}",
                        character.ManifestAssetPath);
                }

                GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(
                    character.PrefabAssetPath);
                if (prefab == null)
                {
                    throw new FileNotFoundException(
                        $"Playable-character prefab is missing: {character.DisplayName}",
                        character.PrefabAssetPath);
                }

                actorInstance = PrefabUtility.InstantiatePrefab(prefab, scene) as GameObject;
                if (actorInstance == null)
                {
                    throw new InvalidOperationException(
                        $"Could not instantiate playable-character prefab: " +
                        $"{character.PrefabAssetPath}");
                }
                actorInstance.name = character.RootName;
                actorInstance.transform.SetParent(charactersRoot, false);
                actorInstance.transform.localPosition = Vector3.zero;
                actorInstance.transform.localRotation = Quaternion.identity;
                actorInstance.transform.localScale = Vector3.one;
                actorInstance.SetActive(true);
                AssertPlayableCharacterPreviewIsolation(charactersRoot, actorInstance);

                Animation animation = actorInstance.GetComponent<Animation>();
                if (animation == null)
                    animation = actorInstance.GetComponentInChildren<Animation>(true);
                if (animation == null)
                {
                    throw new InvalidOperationException(
                        $"Playable-character prefab has no Animation component: " +
                        $"{character.PrefabAssetPath}");
                }

                var clips = new List<AnimationClip>();
                foreach (AnimationState state in animation)
                {
                    if (state != null && state.clip != null)
                        clips.Add(state.clip);
                }
                string[] requestedClipPreference = !string.IsNullOrEmpty(record.clip)
                    ? new[] { record.clip }
                    : character.PreviewClipPreference;
                AnimationClip clip = SelectPreviewClip(
                    clips,
                    requestedClipPreference);
                if (clip == null)
                {
                    throw new InvalidOperationException(
                        $"No configured overview preview clip was found for " +
                        $"{character.DisplayName} ({character.RootName}).");
                }

                animation.Stop();
                animation.clip = clip;
                animation.playAutomatically = false;
                SetRecoveredPropVisibility(animation.gameObject, Array.Empty<string>());
                float sampleSeconds = Mathf.Clamp01(record.sample) * clip.length;
                clip.SampleAnimation(animation.gameObject, sampleSeconds);
                record.clip = clip.name;
                record.sample_seconds = sampleSeconds;

                CharacterRecoveryRig rig = actorInstance.GetComponent<CharacterRecoveryRig>();
                if (rig == null)
                    rig = actorInstance.GetComponentInChildren<CharacterRecoveryRig>(true);
                CharacterProceduralIk poseCorrection =
                    rig != null ? rig.PoseCorrection :
                    actorInstance.GetComponentInChildren<CharacterProceduralIk>(true);
                if (poseCorrection != null)
                    poseCorrection.Evaluate();

                if (!TryComputePlayableCharacterPreviewBounds(
                        actorInstance,
                        out Bounds bounds,
                        out int eligibleRendererCount,
                        out string boundsError))
                {
                    throw new InvalidOperationException(
                        $"Could not compute playable-character preview bounds for " +
                        $"{character.DisplayName}: {boundsError}");
                }
                record.eligible_renderer_count = eligibleRendererCount;
                record.bounds_size_x = bounds.size.x;
                record.bounds_size_y = bounds.size.y;
                record.bounds_size_z = bounds.size.z;

                if (rig == null)
                    throw new InvalidOperationException(
                        $"Playable-character prefab has no CharacterRecoveryRig: {character.RootName}.");
                CharacterRecoveryPresentationProfile profile =
                    EndfieldPlayableCharInfoProfileBuilder.LoadProfile(
                        character.RootName);
                if (profile == null)
                    throw new InvalidDataException(
                        $"Source-recovered CharInfo profile is missing: {character.RootName}.");
                ConfigureOperatorReferenceLighting(
                    scene,
                    FindSceneGameObject("Lighting")?.transform,
                    camera,
                    character.RootName,
                    actorInstance.transform);
                EndfieldRecoveredCharInfoBackgroundPortrait portrait =
                    EndfieldRecoveredCharInfoBackgroundPortraitBuilder.EnsureAndBind(
                        camera,
                        character.RootName,
                        actorInstance.transform);
                CharacterRecoveryPresentationController presentation =
                    camera.GetComponent<CharacterRecoveryPresentationController>();
                if (presentation == null)
                    presentation =
                        camera.gameObject.AddComponent<CharacterRecoveryPresentationController>();
                presentation.viewerCamera = camera;
                presentation.backgroundPortrait = portrait;
                presentation.characterLighting =
                    camera.GetComponent<EndfieldHGRPCharacterLightingVolume>();
                presentation.operatorLightRig =
                    camera.GetComponent<EndfieldHGOperatorLightRig>();
                presentation.physicalPresentation =
                    UnityEngine.Object.FindObjectOfType<
                        EndfieldRecoveredCharInfoPresentation>(true);
                // The source CharInfo portrait is real UI data, but it reads as
                // a second pale character in model-recovery captures. Dedicated
                // portrait/feature probes keep exercising it; roster previews
                // intentionally show only the recovered 3D actor.
                presentation.enableRecoveredPortrait = false;
                presentation.enableRecoveredSourceEnergyCore = false;
                presentation.enableRecoveredEyeResponse = true;
                presentation.enableRecoveredFaceHighlight = true;
                presentation.enableRecoveredPostSemantics = true;
                presentation.enableRecoveredReadyPresentationSubset = true;
                presentation.enableSourceBackedClusteredNprLights = true;
                presentation.enableSourceBackedLightBinning = true;
                presentation.enableIsolatedPunctualSoftShadows = false;
                if (!presentation.ApplyProfile(profile, rig))
                    throw new InvalidOperationException(
                        $"Could not apply source CharInfo profile for {character.RootName}.");

                RenderPreview(
                    outputPath,
                    camera,
                    PlayableCharInfoPreviewRenderWidth,
                    PlayableCharInfoPreviewRenderHeight);
                ValidatePlayableCharacterPreviewPng(outputPath, record);
                record.status = "ok";
                Debug.Log(
                    $"Rendered playable-character preview: root={character.RootName}, " +
                    $"clip={clip.name}, sample={sampleSeconds:0.###}s, path={outputPath}");
            }
            catch (Exception exception)
            {
                record.status = "failed";
                record.error = exception.ToString();
                try
                {
                    if (File.Exists(outputPath))
                        File.Delete(outputPath);
                }
                catch (Exception deleteException)
                {
                    record.error += "\nCould not remove failed/stale PNG: " + deleteException;
                    infrastructureFailure = new AggregateException(
                        "Actor render and failed-PNG cleanup both failed.",
                        exception,
                        deleteException);
                }
                Debug.LogError(
                    $"Playable-character preview failed: root={character.RootName}, " +
                    $"error={exception}");
            }
            finally
            {
                if (actorInstance != null)
                {
                    try
                    {
                        UnityEngine.Object.DestroyImmediate(actorInstance);
                    }
                    catch (Exception cleanupException)
                    {
                        record.status = "failed";
                        string cleanupError =
                            "Actor-instance cleanup failed: " + cleanupException;
                        record.error = string.IsNullOrEmpty(record.error)
                            ? cleanupError
                            : record.error + "\n" + cleanupError;
                        infrastructureFailure = infrastructureFailure == null
                            ? cleanupException
                            : new AggregateException(
                                "Multiple playable-character capture infrastructure failures.",
                                infrastructureFailure,
                                cleanupException);
                    }
                }
                try
                {
                    AssertPlayableCharacterPreviewIsolation(charactersRoot, null);
                }
                catch (Exception isolationException)
                {
                    record.status = "failed";
                    string isolationError =
                        "Actor isolation was not restored after capture: " +
                        isolationException;
                    record.error = string.IsNullOrEmpty(record.error)
                        ? isolationError
                        : record.error + "\n" + isolationError;
                    infrastructureFailure = infrastructureFailure == null
                        ? isolationException
                        : new AggregateException(
                            "Multiple playable-character capture infrastructure failures.",
                            infrastructureFailure,
                            isolationException);
                }
                if (infrastructureFailure != null)
                {
                    try
                    {
                        if (File.Exists(outputPath))
                            File.Delete(outputPath);
                    }
                    catch (Exception deleteException)
                    {
                        record.error +=
                            "\nCould not remove PNG after infrastructure failure: " +
                            deleteException;
                        infrastructureFailure = new AggregateException(
                            infrastructureFailure,
                            deleteException);
                    }
                }
            }

            if (infrastructureFailure != null)
            {
                throw new InvalidOperationException(
                    $"Playable-character capture cleanup failed for " +
                    $"{character.DisplayName}; aborting to preserve actor isolation.",
                    infrastructureFailure);
            }
        }

        private static string RelativeTransformPath(Transform root, Transform target)
        {
            if (root == null || target == null)
                return "";
            if (target == root)
                return "";
            var names = new List<string>();
            Transform current = target;
            while (current != null && current != root)
            {
                names.Add(current.name);
                current = current.parent;
            }
            if (current != root)
                return target.name;
            names.Reverse();
            return string.Join("/", names);
        }

        private static void AssertItemWidgetOverlapRenderersVisibleBeforeRender(
            GameObject actorRoot,
            IEnumerable<string> overlapRendererPaths)
        {
            var renderersByPath = actorRoot
                .GetComponentsInChildren<SkinnedMeshRenderer>(true)
                .Where(renderer => renderer != null && IsRecoveredPropRenderer(renderer))
                .ToDictionary(
                    renderer => RelativeTransformPath(
                        actorRoot.transform,
                        renderer.transform),
                    renderer => renderer,
                    StringComparer.Ordinal);
            foreach (string path in overlapRendererPaths ?? Array.Empty<string>())
            {
                if (!renderersByPath.TryGetValue(path, out SkinnedMeshRenderer renderer) ||
                    !renderer.enabled ||
                    !renderer.gameObject.activeInHierarchy)
                {
                    throw new InvalidOperationException(
                        $"Item-widget overlap evidence is not enabled and active " +
                        $"immediately before final render: {path}");
                }
            }
        }

        private static PlayableItemWidgetRendererSample[]
            CaptureItemWidgetRendererDiagnostics(
                GameObject actorRoot,
                Camera camera,
                string outputDirectory,
                string rootName)
        {
            var renderers = actorRoot
                .GetComponentsInChildren<SkinnedMeshRenderer>(true)
                .Where(renderer => renderer != null && IsRecoveredPropRenderer(renderer))
                .OrderBy(renderer => RelativeTransformPath(
                    actorRoot.transform,
                    renderer.transform),
                    StringComparer.Ordinal)
                .ToArray();
            var samples = new List<PlayableItemWidgetRendererSample>();
            bool captureIsolates = rootName.Equals("Dapan", StringComparison.OrdinalIgnoreCase);
            bool[] originalEnabled = renderers.Select(renderer => renderer.enabled).ToArray();
            bool[] originalActive = renderers
                .Select(renderer => renderer.gameObject.activeInHierarchy)
                .ToArray();
            try
            {
                for (int index = 0; index < renderers.Length; index++)
                {
                    for (int restore = 0; restore < renderers.Length; restore++)
                        renderers[restore].enabled = originalEnabled[restore];
                    SkinnedMeshRenderer renderer = renderers[index];
                    Transform rootBone = renderer.rootBone;
                    Bounds bounds = renderer.bounds;
                    var sample = new PlayableItemWidgetRendererSample
                    {
                        name = renderer.name,
                        path = RelativeTransformPath(actorRoot.transform, renderer.transform),
                        root_bone = RelativeTransformPath(actorRoot.transform, rootBone),
                        enabled = originalEnabled[index],
                        active = originalActive[index],
                        root_bone_position_x = rootBone != null ? rootBone.position.x : 0f,
                        root_bone_position_y = rootBone != null ? rootBone.position.y : 0f,
                        root_bone_position_z = rootBone != null ? rootBone.position.z : 0f,
                        root_bone_lossy_scale_x = rootBone != null ? rootBone.lossyScale.x : 0f,
                        root_bone_lossy_scale_y = rootBone != null ? rootBone.lossyScale.y : 0f,
                        root_bone_lossy_scale_z = rootBone != null ? rootBone.lossyScale.z : 0f,
                        bounds_center_x = bounds.center.x,
                        bounds_center_y = bounds.center.y,
                        bounds_center_z = bounds.center.z,
                        bounds_size_x = bounds.size.x,
                        bounds_size_y = bounds.size.y,
                        bounds_size_z = bounds.size.z,
                    };
                    if (captureIsolates)
                    {
                        for (int other = 0; other < renderers.Length; other++)
                            renderers[other].enabled = other == index && originalEnabled[other];
                        sample.isolated_png =
                            Safe(rootName).ToLowerInvariant() + "_widget_" +
                            (index + 1).ToString("D2") + "_" +
                            Safe(renderer.name).ToLowerInvariant() + ".png";
                        RenderPreview(
                            Path.Combine(outputDirectory, sample.isolated_png),
                            camera,
                            PreviewRenderWidth,
                            PreviewRenderHeight);
                        for (int restore = 0; restore < renderers.Length; restore++)
                            renderers[restore].enabled = originalEnabled[restore];
                    }
                    samples.Add(sample);
                }
            }
            finally
            {
                for (int index = 0; index < renderers.Length; index++)
                    renderers[index].enabled = originalEnabled[index];
            }
            return samples.ToArray();
        }

        private static PlayableItemWidgetRendererSample[]
            CaptureBodyAccessoryRendererDiagnostics(
                GameObject actorRoot,
                Camera camera,
                string outputDirectory,
                string rootName)
        {
            if (!rootName.Equals("Dapan", StringComparison.OrdinalIgnoreCase))
                return Array.Empty<PlayableItemWidgetRendererSample>();
            var renderers = actorRoot
                .GetComponentsInChildren<SkinnedMeshRenderer>(true)
                .Where(renderer =>
                    renderer != null &&
                    !IsRecoveredPropRenderer(renderer) &&
                    renderer.name.StartsWith(
                        "S_actor_dapan_cloth_",
                        StringComparison.OrdinalIgnoreCase))
                .OrderBy(renderer => renderer.name, StringComparer.Ordinal)
                .ToArray();
            var samples = new List<PlayableItemWidgetRendererSample>();
            bool[] originalEnabled = renderers.Select(renderer => renderer.enabled).ToArray();
            try
            {
                for (int index = 0; index < renderers.Length; index++)
                {
                    SkinnedMeshRenderer renderer = renderers[index];
                    Transform rootBone = renderer.rootBone;
                    Bounds bounds = renderer.bounds;
                    var sample = new PlayableItemWidgetRendererSample
                    {
                        name = renderer.name,
                        path = RelativeTransformPath(actorRoot.transform, renderer.transform),
                        root_bone = RelativeTransformPath(actorRoot.transform, rootBone),
                        enabled = renderer.enabled,
                        active = renderer.gameObject.activeInHierarchy,
                        root_bone_position_x = rootBone != null ? rootBone.position.x : 0f,
                        root_bone_position_y = rootBone != null ? rootBone.position.y : 0f,
                        root_bone_position_z = rootBone != null ? rootBone.position.z : 0f,
                        root_bone_lossy_scale_x = rootBone != null ? rootBone.lossyScale.x : 0f,
                        root_bone_lossy_scale_y = rootBone != null ? rootBone.lossyScale.y : 0f,
                        root_bone_lossy_scale_z = rootBone != null ? rootBone.lossyScale.z : 0f,
                        bounds_center_x = bounds.center.x,
                        bounds_center_y = bounds.center.y,
                        bounds_center_z = bounds.center.z,
                        bounds_size_x = bounds.size.x,
                        bounds_size_y = bounds.size.y,
                        bounds_size_z = bounds.size.z,
                    };
                    if (originalEnabled[index])
                    {
                        renderer.enabled = false;
                        sample.exclusion_png =
                            Safe(rootName).ToLowerInvariant() + "_without_" +
                            Safe(renderer.name).ToLowerInvariant() + ".png";
                        RenderPreview(
                            Path.Combine(outputDirectory, sample.exclusion_png),
                            camera,
                            PreviewRenderWidth,
                            PreviewRenderHeight);
                        renderer.enabled = true;
                    }
                    samples.Add(sample);
                }
            }
            finally
            {
                for (int index = 0; index < renderers.Length; index++)
                    renderers[index].enabled = originalEnabled[index];
            }
            return samples.ToArray();
        }

        private static bool TryComputePlayableCharacterPreviewBounds(
            GameObject actorRoot,
            out Bounds bounds,
            out int eligibleRendererCount,
            out string error)
        {
            bounds = new Bounds(Vector3.zero, Vector3.zero);
            eligibleRendererCount = 0;
            int rendererCount = 0;
            foreach (SkinnedMeshRenderer renderer in
                     actorRoot.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                rendererCount++;
                if (renderer == null ||
                    !renderer.enabled ||
                    !renderer.gameObject.activeInHierarchy ||
                    renderer.sharedMesh == null ||
                    renderer.sharedMesh.vertexCount <= 0 ||
                    IsRecoveredPropRenderer(renderer))
                {
                    continue;
                }

                Bounds candidate = renderer.bounds;
                if (!IsFinite(candidate.center) ||
                    !IsFinite(candidate.size) ||
                    Mathf.Max(candidate.size.x, candidate.size.y, candidate.size.z) <
                    PlayablePreviewMinimumBoundsSpan)
                {
                    continue;
                }

                if (eligibleRendererCount == 0)
                    bounds = candidate;
                else
                    bounds.Encapsulate(candidate);
                eligibleRendererCount++;
            }

            if (eligibleRendererCount == 0)
            {
                error =
                    $"no eligible finite nontrivial renderer bounds " +
                    $"(renderers={rendererCount})";
                return false;
            }
            if (!IsFinite(bounds.center) ||
                !IsFinite(bounds.size) ||
                bounds.size.x < PlayablePreviewMinimumBoundsSpan ||
                bounds.size.y < PlayablePreviewMinimumBoundsSpan)
            {
                error =
                    $"combined bounds are invalid or trivial: " +
                    $"center={bounds.center}, size={bounds.size}, " +
                    $"eligible={eligibleRendererCount}/{rendererCount}";
                return false;
            }

            error = "";
            return true;
        }

        private static bool IsFinite(Vector3 value)
        {
            return IsFinite(value.x) && IsFinite(value.y) && IsFinite(value.z);
        }

        private static bool IsFinite(float value)
        {
            return !float.IsNaN(value) && !float.IsInfinity(value);
        }

        private static void FramePlayableCharacterPreviewCamera(
            Camera camera,
            Bounds bounds,
            float outputAspect)
        {
            if (camera == null)
                throw new ArgumentNullException(nameof(camera));
            if (!IsFinite(outputAspect) || outputAspect <= 0f)
                throw new ArgumentOutOfRangeException(nameof(outputAspect));

            camera.orthographic = false;
            camera.fieldOfView = PreviewFieldOfView;
            camera.aspect = outputAspect;
            float tangent = Mathf.Tan(camera.fieldOfView * 0.5f * Mathf.Deg2Rad);
            float verticalHalfExtent = Mathf.Max(
                bounds.extents.y,
                PlayablePreviewMinimumBoundsSpan * 0.5f);
            float horizontalHalfExtentAsVertical = Mathf.Max(
                bounds.extents.x / outputAspect,
                PlayablePreviewMinimumBoundsSpan * 0.5f);
            float limitingHalfExtent = Mathf.Max(
                verticalHalfExtent,
                horizontalHalfExtentAsVertical) * PlayablePreviewFrameMargin;
            float distance = bounds.extents.z + limitingHalfExtent / tangent;
            distance = Mathf.Max(distance, bounds.extents.z + 0.5f);

            Vector3 target = bounds.center;
            camera.transform.position = target + Vector3.forward * distance;
            camera.transform.rotation = Quaternion.LookRotation(
                target - camera.transform.position,
                Vector3.up);
            camera.nearClipPlane = PreviewNearClip;
            camera.farClipPlane = Mathf.Max(
                100f,
                distance + bounds.extents.z + 10f);
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = PreviewBackgroundColor;
        }

        private static void ValidatePlayableCharacterPreviewPng(
            string path,
            PlayableCharacterPreviewRenderRecord record,
            int expectedWidth = PlayableCharInfoPreviewRenderWidth,
            int expectedHeight = PlayableCharInfoPreviewRenderHeight)
        {
            byte[] data = File.ReadAllBytes(path);
            var texture = new Texture2D(2, 2, TextureFormat.RGBA32, false, true);
            try
            {
                if (!texture.LoadImage(data, false))
                    throw new InvalidDataException($"Unity could not decode rendered PNG: {path}");
                if (texture.width != expectedWidth || texture.height != expectedHeight)
                {
                    throw new InvalidDataException(
                        $"Rendered PNG has unexpected dimensions " +
                        $"{texture.width}x{texture.height}: {path}");
                }

                Color background =
                    (texture.GetPixel(0, 0) +
                     texture.GetPixel(texture.width - 1, 0) +
                     texture.GetPixel(0, texture.height - 1) +
                     texture.GetPixel(texture.width - 1, texture.height - 1)) * 0.25f;
                if (!IsFinite(new Vector3(background.r, background.g, background.b)))
                    throw new InvalidDataException("Rendered PNG corner color is non-finite.");

                int gridX = Mathf.Min(PlayablePreviewValidationGrid, texture.width);
                int gridY = Mathf.Min(PlayablePreviewValidationGrid, texture.height);
                int sampleCount = 0;
                int foregroundCount = 0;
                double luminanceSum = 0.0;
                double luminanceSquaredSum = 0.0;
                float luminanceMin = float.PositiveInfinity;
                float luminanceMax = float.NegativeInfinity;
                Vector3 colorMin = new Vector3(
                    float.PositiveInfinity,
                    float.PositiveInfinity,
                    float.PositiveInfinity);
                Vector3 colorMax = new Vector3(
                    float.NegativeInfinity,
                    float.NegativeInfinity,
                    float.NegativeInfinity);

                for (int gridYIndex = 0; gridYIndex < gridY; gridYIndex++)
                {
                    int pixelY = gridY <= 1
                        ? 0
                        : Mathf.RoundToInt(
                            (texture.height - 1) * gridYIndex / (float)(gridY - 1));
                    for (int gridXIndex = 0; gridXIndex < gridX; gridXIndex++)
                    {
                        int pixelX = gridX <= 1
                            ? 0
                            : Mathf.RoundToInt(
                                (texture.width - 1) * gridXIndex / (float)(gridX - 1));
                        Color color = texture.GetPixel(pixelX, pixelY);
                        var rgb = new Vector3(color.r, color.g, color.b);
                        if (!IsFinite(rgb))
                            throw new InvalidDataException("Rendered PNG contains a non-finite sampled color.");

                        float luminance =
                            color.r * 0.2126f +
                            color.g * 0.7152f +
                            color.b * 0.0722f;
                        luminanceMin = Mathf.Min(luminanceMin, luminance);
                        luminanceMax = Mathf.Max(luminanceMax, luminance);
                        colorMin = Vector3.Min(colorMin, rgb);
                        colorMax = Vector3.Max(colorMax, rgb);
                        luminanceSum += luminance;
                        luminanceSquaredSum += luminance * luminance;
                        sampleCount++;

                        float backgroundDifference = Mathf.Max(
                            Mathf.Abs(color.r - background.r),
                            Mathf.Abs(color.g - background.g),
                            Mathf.Abs(color.b - background.b));
                        if (backgroundDifference >= PlayablePreviewMinimumColorRange)
                            foregroundCount++;
                    }
                }

                double mean = luminanceSum / sampleCount;
                double variance = Math.Max(
                    0.0,
                    luminanceSquaredSum / sampleCount - mean * mean);
                float luminanceStdDev = (float)Math.Sqrt(variance);
                float luminanceRange = luminanceMax - luminanceMin;
                Vector3 channelRanges = colorMax - colorMin;
                float colorRange = Mathf.Max(
                    channelRanges.x,
                    channelRanges.y,
                    channelRanges.z);
                float foregroundFraction = foregroundCount / (float)sampleCount;

                record.validation_finite = true;
                record.validation_sample_count = sampleCount;
                record.validation_luminance_min = luminanceMin;
                record.validation_luminance_max = luminanceMax;
                record.validation_luminance_stddev = luminanceStdDev;
                record.validation_color_range = colorRange;
                record.validation_foreground_fraction = foregroundFraction;
                record.validation_passed =
                    luminanceRange >= PlayablePreviewMinimumLuminanceRange &&
                    luminanceStdDev >= PlayablePreviewMinimumLuminanceStdDev &&
                    colorRange >= PlayablePreviewMinimumColorRange &&
                    foregroundFraction >= PlayablePreviewMinimumForegroundFraction;
                if (!record.validation_passed)
                {
                    throw new InvalidDataException(
                        $"Rendered PNG failed the conservative nonblank check: " +
                        $"luminanceRange={luminanceRange:0.######}, " +
                        $"luminanceStdDev={luminanceStdDev:0.######}, " +
                        $"colorRange={colorRange:0.######}, " +
                        $"foregroundFraction={foregroundFraction:0.######}, " +
                        $"samples={sampleCount}.");
                }
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(texture);
            }
        }

        private static void AssertPlayableCharacterPreviewIsolation(
            Transform charactersRoot,
            GameObject expectedActor)
        {
            var actorRoots = new List<GameObject>();
            foreach (Transform child in charactersRoot)
            {
                // The saved viewer scene is restored after the batch, so the
                // temporary capture scene deliberately reserves every direct
                // Characters child for the one actor being rendered. Counting
                // all children prevents an unrecognised helper or malformed
                // prefab root from silently contaminating a later PNG.
                if (child != null)
                    actorRoots.Add(child.gameObject);
            }

            if (expectedActor == null && actorRoots.Count == 0)
                return;
            if (expectedActor != null &&
                actorRoots.Count == 1 &&
                actorRoots[0] == expectedActor &&
                expectedActor.activeInHierarchy)
            {
                return;
            }

            var names = new List<string>();
            foreach (GameObject actorRoot in actorRoots)
                names.Add(actorRoot != null ? actorRoot.name : "<null>");
            throw new InvalidOperationException(
                $"Playable-character preview actor isolation failed: " +
                $"expected={(expectedActor != null ? expectedActor.name : "<none>")}, " +
                $"found={actorRoots.Count} [{string.Join(", ", names.ToArray())}].");
        }

        private static void ClearPlayableCharacterPreviewActors(Transform charactersRoot)
        {
            for (int index = charactersRoot.childCount - 1; index >= 0; index--)
            {
                Transform child = charactersRoot.GetChild(index);
                if (child == null)
                    continue;
                UnityEngine.Object.DestroyImmediate(child.gameObject);
            }
        }

        private static bool TryValidatePlayableCharacterPreviewCompleteness(
            PlayableCharacterPreviewRenderManifest report,
            List<PlayableCharacterPreviewRenderRecord> records,
            out string error)
        {
            if (records.Count != report.character_count)
            {
                error =
                    $"Preview report record count is incomplete: " +
                    $"records={records.Count}, expected={report.character_count}.";
                return false;
            }
            if (report.attempted != report.character_count ||
                report.succeeded + report.failed != report.attempted ||
                report.pending != 0)
            {
                error =
                    $"Preview report attempt accounting is incomplete: " +
                    $"characters={report.character_count}, attempted={report.attempted}, " +
                    $"succeeded={report.succeeded}, failed={report.failed}, " +
                    $"pending={report.pending}.";
                return false;
            }
            error = "";
            return true;
        }

        private static void WritePlayableCharacterPreviewReport(
            string reportPath,
            PlayableCharacterPreviewRenderManifest report,
            List<PlayableCharacterPreviewRenderRecord> records)
        {
            report.renders = records.ToArray();
            report.attempted = 0;
            report.succeeded = 0;
            report.failed = 0;
            report.pending = 0;
            foreach (PlayableCharacterPreviewRenderRecord record in records)
            {
                if (record.status == "ok")
                {
                    report.attempted++;
                    report.succeeded++;
                }
                else if (record.status == "failed")
                {
                    report.attempted++;
                    report.failed++;
                }
                else
                {
                    report.pending++;
                }
            }
            File.WriteAllText(
                reportPath,
                JsonUtility.ToJson(report, true) + "\n",
                new UTF8Encoding(false));
        }

        [MenuItem("Endfield/Character Recovery Lab/Render Runtime Reference/Wulfa")]
        public static void RenderRuntimeReferenceWulfaPreview()
        {
            RenderRuntimeReferenceActorPreview(
                "Wulfa",
                "A_actor_wulfa_ui_overview_loop_01",
                0.95f,
                "runtime_reference_wulfa.png");
        }

        [MenuItem("Endfield/Character Recovery Lab/Render Runtime Reference/Zhuangfy")]
        public static void RenderRuntimeReferenceZhuangfyPreview()
        {
            RenderRuntimeReferenceActorPreview(
                "Zhuangfy",
                "A_actor_zhuangfy_ui_overview_loop_01",
                0.275f,
                "runtime_reference_zhuangfy.png");
        }

        [MenuItem(
            "Endfield/Character Recovery Lab/Render Diagnostics/Multi-Character Shadow Atlas")]
        public static void RenderRecoveredMultiCharacterShadowAtlasPreview()
        {
            RenderRecoveredMultiCharacterShadowAtlasPreview(
                diagnosticActorCount: 2);
        }

        [MenuItem(
            "Endfield/Character Recovery Lab/Render Diagnostics/" +
            "Five-Character Shadow Atlas Row Transition")]
        public static void RenderRecoveredFiveCharacterShadowAtlasPreview()
        {
            RenderRecoveredMultiCharacterShadowAtlasPreview(
                diagnosticActorCount: 5);
        }

        [MenuItem(
            "Endfield/Character Recovery Lab/Render Diagnostics/" +
            "Nine-Character Shadow Atlas Third Row")]
        public static void RenderRecoveredNineCharacterShadowAtlasPreview()
        {
            RenderRecoveredMultiCharacterShadowAtlasPreview(
                diagnosticActorCount: 9);
        }

        [MenuItem(
            "Endfield/Character Recovery Lab/Render Diagnostics/" +
            "Thirteen-Character Shadow Atlas Fourth Row")]
        public static void RenderRecoveredThirteenCharacterShadowAtlasPreview()
        {
            RenderRecoveredMultiCharacterShadowAtlasPreview(
                diagnosticActorCount: 13);
        }

        [MenuItem(
            "Endfield/Character Recovery Lab/Render Diagnostics/" +
            "Fourteen-Character Shadow Atlas Maximum Slot")]
        public static void RenderRecoveredFourteenCharacterShadowAtlasPreview()
        {
            RenderRecoveredMultiCharacterShadowAtlasPreview(
                diagnosticActorCount: 14);
        }

        private static void RenderRecoveredMultiCharacterShadowAtlasPreview(
            int diagnosticActorCount)
        {
            bool fiveCharacterRowTransitionAudit =
                diagnosticActorCount == 5;
            bool nineCharacterThirdRowAudit =
                diagnosticActorCount == 9;
            bool thirteenCharacterFourthRowAudit =
                diagnosticActorCount == 13;
            bool fourteenCharacterMaximumSlotAudit =
                diagnosticActorCount == 14;
            bool expandedAtlasAudit =
                fiveCharacterRowTransitionAudit ||
                nineCharacterThirdRowAudit ||
                thirteenCharacterFourthRowAudit ||
                fourteenCharacterMaximumSlotAudit;
            if (diagnosticActorCount != 2 && !expandedAtlasAudit)
            {
                throw new ArgumentOutOfRangeException(
                    nameof(diagnosticActorCount));
            }
            EnsureHGCompatRenderPipelineAssigned();
            bool originalRealtimeCasterAudit = HDRenderPipeline
                .IsRecoveredOriginalRealtimeCharacterShadowCastersRequested();
            if (!HDRenderPipeline
                    .IsRecoveredMultiCharacterShadowAtlasRequested())
            {
                throw new InvalidOperationException(
                    "Set ENDFIELD_RECOVERED_MULTI_CHARACTER_SHADOW_ATLAS=1 " +
                    "and ENDFIELD_RECOVERED_SEPARATE_CHARACTER_SHADOW=1. " +
                    "The multi-character atlas remains default-off.");
            }
            if (!File.Exists(
                    Path.Combine(
                        Directory.GetCurrentDirectory(),
                        ViewerScenePath)))
            {
                throw new FileNotFoundException(
                    "Build the shared character viewer scene before rendering " +
                    "the multi-character atlas diagnostic.",
                    ViewerScenePath);
            }

            Scene scene = EditorSceneManager.OpenScene(
                ViewerScenePath,
                OpenSceneMode.Single);
            EnsureOriginalStylePresentationScene(scene);
            Transform charactersRoot =
                FindSceneGameObject("Characters")?.transform;
            if (charactersRoot == null)
            {
                throw new InvalidOperationException(
                    "Shared viewer scene has no Characters root.");
            }

            string[] actorNames = fourteenCharacterMaximumSlotAudit
                ? new[]
                {
                    "Wulfa",
                    "Zhuangfy",
                    "Lifeng",
                    "Mifu",
                    "Pelica",
                    "Endminm",
                    "Endminf",
                    "Chen",
                    "Wolfgd",
                    "Aglina",
                    "Aurora",
                    "Antal",
                    "Ardelia",
                    "Bounda"
                }
                : thirteenCharacterFourthRowAudit
                ? new[]
                {
                    "Wulfa",
                    "Zhuangfy",
                    "Lifeng",
                    "Mifu",
                    "Pelica",
                    "Endminm",
                    "Endminf",
                    "Chen",
                    "Wolfgd",
                    "Aglina",
                    "Aurora",
                    "Antal",
                    "Ardelia"
                }
                : nineCharacterThirdRowAudit
                ? new[]
                {
                    "Wulfa",
                    "Zhuangfy",
                    "Lifeng",
                    "Mifu",
                    "Pelica",
                    "Endminm",
                    "Endminf",
                    "Chen",
                    "Wolfgd"
                }
                : fiveCharacterRowTransitionAudit
                    ? new[] { "Wulfa", "Zhuangfy", "Lifeng", "Mifu", "Pelica" }
                    : new[] { "Wulfa", "Zhuangfy" };
            string[] clipNames = fourteenCharacterMaximumSlotAudit
                ? new[]
                {
                    "A_actor_wulfa_ui_overview_loop_01",
                    "A_actor_zhuangfy_ui_overview_loop_01",
                    "A_actor_lifeng_ui_overview_loop",
                    "A_actor_mifu_ui_overview_loop_01",
                    "A_actor_pelica_ui_overview_loop",
                    "A_actor_endminm_ui_overview_loop",
                    "A_actor_endminf_ui_overview_loop",
                    "A_actor_chen_ui_overview_loop",
                    "A_actor_wolfgd_ui_overview_loop",
                    "A_actor_aglina_ui_overview_loop",
                    "A_actor_aurora_ui_overview_loop",
                    "A_actor_antal_ui_overview_loop_01",
                    "A_actor_ardelia_ui_overview_loop_01",
                    "A_actor_bounda_ui_overview_loop_01"
                }
                : thirteenCharacterFourthRowAudit
                ? new[]
                {
                    "A_actor_wulfa_ui_overview_loop_01",
                    "A_actor_zhuangfy_ui_overview_loop_01",
                    "A_actor_lifeng_ui_overview_loop",
                    "A_actor_mifu_ui_overview_loop_01",
                    "A_actor_pelica_ui_overview_loop",
                    "A_actor_endminm_ui_overview_loop",
                    "A_actor_endminf_ui_overview_loop",
                    "A_actor_chen_ui_overview_loop",
                    "A_actor_wolfgd_ui_overview_loop",
                    "A_actor_aglina_ui_overview_loop",
                    "A_actor_aurora_ui_overview_loop",
                    "A_actor_antal_ui_overview_loop_01",
                    "A_actor_ardelia_ui_overview_loop_01"
                }
                : nineCharacterThirdRowAudit
                ? new[]
                {
                    "A_actor_wulfa_ui_overview_loop_01",
                    "A_actor_zhuangfy_ui_overview_loop_01",
                    "A_actor_lifeng_ui_overview_loop",
                    "A_actor_mifu_ui_overview_loop_01",
                    "A_actor_pelica_ui_overview_loop",
                    "A_actor_endminm_ui_overview_loop",
                    "A_actor_endminf_ui_overview_loop",
                    "A_actor_chen_ui_overview_loop",
                    "A_actor_wolfgd_ui_overview_loop"
                }
                : fiveCharacterRowTransitionAudit
                    ? new[]
                {
                    "A_actor_wulfa_ui_overview_loop_01",
                    "A_actor_zhuangfy_ui_overview_loop_01",
                    "A_actor_lifeng_ui_overview_loop",
                    "A_actor_mifu_ui_overview_loop_01",
                    "A_actor_pelica_ui_overview_loop"
                }
                    : new[]
                    {
                        "A_actor_wulfa_ui_overview_loop_01",
                        "A_actor_zhuangfy_ui_overview_loop_01"
                    };
            float[] sampleTimes = fourteenCharacterMaximumSlotAudit
                ? new[]
                {
                    0.95f,
                    0.275f,
                    0.35f,
                    0.35f,
                    0.35f,
                    0.35f,
                    0.35f,
                    0.35f,
                    0.35f,
                    0.35f,
                    0.35f,
                    0.35f,
                    0.35f,
                    0.35f
                }
                : thirteenCharacterFourthRowAudit
                ? new[]
                {
                    0.95f,
                    0.275f,
                    0.35f,
                    0.35f,
                    0.35f,
                    0.35f,
                    0.35f,
                    0.35f,
                    0.35f,
                    0.35f,
                    0.35f,
                    0.35f,
                    0.35f
                }
                : nineCharacterThirdRowAudit
                ? new[]
                {
                    0.95f,
                    0.275f,
                    0.35f,
                    0.35f,
                    0.35f,
                    0.35f,
                    0.35f,
                    0.35f,
                    0.35f
                }
                : fiveCharacterRowTransitionAudit
                    ? new[] { 0.95f, 0.275f, 0.35f, 0.35f, 0.35f }
                    : new[] { 0.95f, 0.275f };
            float[] horizontalOffsets = fourteenCharacterMaximumSlotAudit
                ? new[]
                {
                    -7.54f,
                    -6.38f,
                    -5.22f,
                    -4.06f,
                    -2.90f,
                    -1.74f,
                    -0.58f,
                    0.58f,
                    1.74f,
                    2.90f,
                    4.06f,
                    5.22f,
                    6.38f,
                    7.54f
                }
                : thirteenCharacterFourthRowAudit
                ? new[]
                {
                    -6.96f,
                    -5.80f,
                    -4.64f,
                    -3.48f,
                    -2.32f,
                    -1.16f,
                    0.0f,
                    1.16f,
                    2.32f,
                    3.48f,
                    4.64f,
                    5.80f,
                    6.96f
                }
                : nineCharacterThirdRowAudit
                ? new[]
                {
                    -4.64f,
                    -3.48f,
                    -2.32f,
                    -1.16f,
                    0.0f,
                    1.16f,
                    2.32f,
                    3.48f,
                    4.64f
                }
                : fiveCharacterRowTransitionAudit
                    ? new[] { -2.32f, -1.16f, 0.0f, 1.16f, 2.32f }
                    : new[] { -0.58f, 0.58f };
            bool reverseCreationAudit = IsEnvironmentFlagEnabled(
                MultiCharacterShadowReverseCreationAuditEnvironmentVariable);
            if (reverseCreationAudit)
            {
                foreach (string actorName in actorNames)
                {
                    GameObject existing = FindSceneGameObject(actorName);
                    if (existing != null)
                        UnityEngine.Object.DestroyImmediate(existing);
                }
                // Recreate in display order. Editor-created instance IDs
                // descend through negative values, so this reverses the
                // recovered ascending GetInstanceID tie-break.
                for (int actorIndex = 0;
                     actorIndex < actorNames.Length;
                     actorIndex++)
                {
                    string actorName = actorNames[actorIndex];
                    string prefabPath =
                        $"{GeneratedRoot}/Playable/{actorName}/Prefabs/{actorName}.prefab";
                    GameObject prefab =
                        AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
                    GameObject recreated =
                        prefab != null
                            ? PrefabUtility.InstantiatePrefab(
                                prefab,
                                scene) as GameObject
                            : null;
                    if (recreated == null)
                    {
                        throw new InvalidOperationException(
                            "Could not recreate multi-character transport " +
                            "audit actor: " + actorName);
                    }
                    recreated.name = actorName;
                    recreated.transform.SetParent(charactersRoot, false);
                }
            }
            var actors = new List<GameObject>();
            for (int actorIndex = 0;
                 actorIndex < actorNames.Length;
                 actorIndex++)
            {
                string actorName = actorNames[actorIndex];
                GameObject actorRoot = FindSceneGameObject(actorName);
                if (actorRoot == null)
                {
                    string prefabPath =
                        $"{GeneratedRoot}/Playable/{actorName}/Prefabs/{actorName}.prefab";
                    GameObject prefab =
                        AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
                    if (prefab == null)
                    {
                        throw new FileNotFoundException(
                            "Multi-character diagnostic actor prefab is " +
                            "missing: " + actorName,
                            prefabPath);
                    }
                    actorRoot =
                        PrefabUtility.InstantiatePrefab(prefab, scene) as
                        GameObject;
                    if (actorRoot == null)
                    {
                        throw new InvalidOperationException(
                            "Could not instantiate multi-character actor: " +
                            actorName);
                    }
                    actorRoot.name = actorName;
                    actorRoot.transform.SetParent(charactersRoot, false);
                }
                actors.Add(actorRoot);
            }

            foreach (Transform child in charactersRoot)
            {
                if (child != null)
                {
                    child.gameObject.SetActive(
                        actors.Contains(child.gameObject));
                }
            }
            for (int actorIndex = 0;
                 actorIndex < actors.Count;
                 actorIndex++)
            {
                GameObject actorRoot = actors[actorIndex];
                actorRoot.transform.localPosition =
                    new Vector3(horizontalOffsets[actorIndex], 0.0f, 0.0f);
                actorRoot.transform.localRotation = Quaternion.identity;
                actorRoot.transform.localScale = Vector3.one;
                actorRoot.SetActive(true);
                SetRecoveredPropVisibility(
                    actorRoot,
                    Array.Empty<string>());

                string clipName = clipNames[actorIndex];
                string clipPath =
                    $"{GeneratedRoot}/Playable/{actorNames[actorIndex]}/Animations/{Safe(clipName)}.anim";
                AnimationClip clip =
                    AssetDatabase.LoadAssetAtPath<AnimationClip>(clipPath);
                if (clip == null)
                {
                    throw new FileNotFoundException(
                        "Multi-character overview clip is missing: " +
                        clipName,
                        clipPath);
                }
                Animation animation =
                    actorRoot.GetComponent<Animation>();
                if (animation == null)
                    animation = actorRoot.AddComponent<Animation>();
                if (animation[clipName] == null)
                    animation.AddClip(clip, clipName);
                animation.clip = clip;
                animation.Stop();
                clip.SampleAnimation(
                    actorRoot,
                    Mathf.Clamp(
                        sampleTimes[actorIndex],
                        0.0f,
                        clip.length));
                CharacterProceduralIk poseCorrection =
                    actorRoot.GetComponent<CharacterProceduralIk>();
                if (poseCorrection != null)
                    poseCorrection.Evaluate();
            }

            Transform lightingRoot =
                FindSceneGameObject("Lighting")?.transform;
            ConfigurePreviewLighting(scene, lightingRoot);
            ApplyGeneratedMaterialProfileFlags();
            ApplyGeneratedTextureImportProfiles(
                actorNames.Select(
                    actorName =>
                        $"{GeneratedRoot}/Playable/{actorName}")
                    .ToArray());
            PruneLowerQualityMeshLodsFromOpenScene();

            Camera camera =
                Camera.main ??
                UnityEngine.Object.FindObjectOfType<Camera>();
            if (camera == null)
            {
                throw new InvalidOperationException(
                    "Shared viewer scene has no camera.");
            }
            ConfigureOperatorReferenceLighting(
                scene,
                lightingRoot,
                camera,
                "Wulfa",
                actors[0].transform);
            SkinnedMeshRenderer[] combinedRenderers =
                actors.SelectMany(
                    actor =>
                        actor.GetComponentsInChildren<
                            SkinnedMeshRenderer>(true))
                    .ToArray();
            Bounds combinedBounds = CombinedBounds(combinedRenderers);
            if (expandedAtlasAudit)
            {
                FrameMultiCharacterShadowAuditCamera(
                    camera,
                    combinedBounds,
                    (float)RuntimeReferenceRenderWidth /
                        RuntimeReferenceRenderHeight);
            }
            else
            {
                FrameCamera(camera, combinedBounds);
            }
            EndfieldRecoveredCharInfoBackgroundPortraitBuilder.EnsureAndBind(
                camera,
                "Wulfa",
                actors[0].transform);
            ConfigureReferenceBackdrop(
                scene,
                FindBackdropRoot(),
                camera,
                combinedBounds,
                (float)RuntimeReferenceRenderWidth /
                    RuntimeReferenceRenderHeight);

            string evidenceDirectory = originalRealtimeCasterAudit
                ? "character_shadow_original_realtime_caster_recovery_20260724/"
                : fourteenCharacterMaximumSlotAudit
                ? "character_shadow_fourteen_actor_recovery_20260724/"
                : thirteenCharacterFourthRowAudit
                ? "character_shadow_thirteen_actor_recovery_20260723/"
                : nineCharacterThirdRowAudit
                ? "character_shadow_nine_actor_recovery_20260723/"
                : fiveCharacterRowTransitionAudit
                    ? "character_shadow_five_actor_recovery_20260723/"
                    : "multi_character_shadow_atlas_20260723/";
            string outputFileName = originalRealtimeCasterAudit
                ? fourteenCharacterMaximumSlotAudit
                    ? "fourteen_original_realtime_character_shadow_atlas.png"
                    : "original_realtime_character_shadow_atlas.png"
                : fourteenCharacterMaximumSlotAudit
                ? reverseCreationAudit
                    ? "fourteen_character_shadow_atlas_reversed_creation.png"
                    : "fourteen_character_shadow_atlas.png"
                : thirteenCharacterFourthRowAudit
                ? reverseCreationAudit
                    ? "thirteen_character_shadow_atlas_reversed_creation.png"
                    : "thirteen_character_shadow_atlas.png"
                : nineCharacterThirdRowAudit
                ? reverseCreationAudit
                    ? "nine_character_shadow_atlas_reversed_creation.png"
                    : "nine_character_shadow_atlas.png"
                : fiveCharacterRowTransitionAudit
                    ? reverseCreationAudit
                        ? "five_character_shadow_atlas_reversed_creation.png"
                        : "five_character_shadow_atlas.png"
                    : reverseCreationAudit
                        ? "multi_character_shadow_atlas_reversed_creation.png"
                        : "multi_character_shadow_atlas.png";
            string outputPath = Path.GetFullPath(
                Path.Combine(
                    Application.dataPath,
                    "../../scratch/character_recovery/" +
                    evidenceDirectory +
                    outputFileName));
            Directory.CreateDirectory(
                Path.GetDirectoryName(outputPath) ?? ".");
            RenderPreview(
                outputPath,
                RuntimeReferenceRenderWidth,
                RuntimeReferenceRenderHeight);
            AssetDatabase.Refresh();
            Debug.Log(
                "Rendered recovered multi-character shadow atlas diagnostic: " +
                outputPath +
                (fiveCharacterRowTransitionAudit
                    ? " (five-character 4x2 row-transition audit)"
                    : fourteenCharacterMaximumSlotAudit
                        ? " (fourteen-character 4x4 maximum-slot audit)"
                    : thirteenCharacterFourthRowAudit
                        ? " (thirteen-character 4x4 fourth-row audit)"
                    : nineCharacterThirdRowAudit
                        ? " (nine-character 4x3 third-row audit)"
                    : string.Empty) +
                (reverseCreationAudit
                    ? " (reverse-creation transport audit)"
                    : string.Empty) +
                (originalRealtimeCasterAudit
                    ? " (original regular LOD0 m_RealtimeShadowCaster=1 " +
                      "membership audit; retail desktop proxies excluded)"
                    : string.Empty));
        }

        // The reference eye midpoint and span that used to be passed here were
        // inputs to the image-fitted eye-line framing that the recovered
        // overview camera replaced, and field of view now comes from that same
        // contract, so none of the three reach the render any more.
        private static void RenderRuntimeReferenceActorPreview(
            string actorName,
            string clipName,
            float sampleTime,
            string outputFileName)
        {
            EnsureHGCompatRenderPipelineAssigned();
            if (!File.Exists(Path.Combine(Directory.GetCurrentDirectory(), ViewerScenePath)))
                throw new FileNotFoundException("Build the shared character viewer scene before rendering a runtime reference.", ViewerScenePath);

            Scene scene = EditorSceneManager.OpenScene(ViewerScenePath, OpenSceneMode.Single);
            EnsureOriginalStylePresentationScene(scene);
            Transform charactersRoot = FindSceneGameObject("Characters")?.transform;
            if (charactersRoot == null)
                throw new InvalidOperationException("Shared viewer scene has no Characters root.");

            GameObject actorRoot = FindSceneGameObject(actorName);
            if (actorRoot == null)
            {
                string prefabPath =
                    $"{GeneratedRoot}/Playable/{actorName}/Prefabs/{actorName}.prefab";
                GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
                if (prefab == null)
                    throw new FileNotFoundException($"Runtime-reference actor prefab is missing: {actorName}", prefabPath);
                actorRoot = PrefabUtility.InstantiatePrefab(prefab, scene) as GameObject;
                if (actorRoot == null)
                    throw new InvalidOperationException($"Could not instantiate runtime-reference actor: {actorName}");
                actorRoot.name = actorName;
                actorRoot.transform.SetParent(charactersRoot, false);
            }

            foreach (Transform child in charactersRoot)
            {
                if (child != null)
                    child.gameObject.SetActive(child.gameObject == actorRoot);
            }
            actorRoot.transform.localPosition = Vector3.zero;
            actorRoot.transform.localRotation = Quaternion.identity;
            actorRoot.transform.localScale = Vector3.one;
            actorRoot.SetActive(true);

            string clipPath =
                $"{GeneratedRoot}/Playable/{actorName}/Animations/{Safe(clipName)}.anim";
            AnimationClip clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(clipPath);
            if (clip == null)
                throw new FileNotFoundException($"Runtime-reference overview clip is missing: {clipName}", clipPath);
            Animation animation = actorRoot.GetComponent<Animation>();
            if (animation == null)
                animation = actorRoot.AddComponent<Animation>();
            if (animation[clipName] == null)
                animation.AddClip(clip, clipName);
            animation.clip = clip;
            animation.Stop();
            SetRecoveredPropVisibility(actorRoot, Array.Empty<string>());
            clip.SampleAnimation(actorRoot, Mathf.Clamp(sampleTime, 0f, clip.length));
            CharacterProceduralIk poseCorrection = actorRoot.GetComponent<CharacterProceduralIk>();
            if (poseCorrection != null)
                poseCorrection.Evaluate();

            var lightingRoot = FindSceneGameObject("Lighting")?.transform;
            ConfigurePreviewLighting(scene, lightingRoot);
            ApplyGeneratedMaterialProfileFlags();
            ApplyGeneratedTextureImportProfiles();
            PruneLowerQualityMeshLodsFromOpenScene();

            Camera camera = Camera.main ?? UnityEngine.Object.FindObjectOfType<Camera>();
            if (camera == null)
                throw new InvalidOperationException("Shared viewer scene has no camera.");
            ConfigureOperatorReferenceLighting(
                scene,
                lightingRoot,
                camera,
                actorName,
                actorRoot.transform);
            FrameCameraToRecoveredOperatorCamera(camera, actorName);
            ApplyComparisonCameraOverrideIfRequested(camera);
            EndfieldRecoveredCharInfoBackgroundPortraitBuilder.EnsureAndBind(
                camera,
                actorName,
                actorRoot.transform);
            if (IsEnvironmentFlagEnabled(FittedCompositorTranslationEnvironmentVariable))
            {
                // The translation is measured from supplied screenshots, not
                // recovered game state. Keep it available for registration
                // diagnostics, but never apply it in the original-data path.
                ApplyRuntimeReferenceCompositorTranslation(camera, actorName);
            }
            Bounds bounds = CombinedBounds(actorRoot.GetComponentsInChildren<SkinnedMeshRenderer>(true));
            ConfigureReferenceBackdrop(
                scene,
                FindBackdropRoot(),
                camera,
                bounds,
                (float)RuntimeReferenceRenderWidth / RuntimeReferenceRenderHeight);

            string outputPath = Path.GetFullPath(Path.Combine(Application.dataPath, "../../scratch", outputFileName));
            Directory.CreateDirectory(Path.GetDirectoryName(outputPath) ?? ".");
            RenderPreview(outputPath, RuntimeReferenceRenderWidth, RuntimeReferenceRenderHeight);
            AssetDatabase.Refresh();
            Debug.Log(
                $"Rendered {actorName} runtime reference at {sampleTime:0.###}s: {outputPath}");
        }

        /// <summary>
        /// Renders a fixed phase list without reopening the viewer scene for
        /// every sample. The single-sample entry point is useful for
        /// interactive recovery, but a source-rate identity sweep must keep
        /// one scene, camera, lighting profile, and render pipeline alive.
        /// </summary>
        internal static void RenderRuntimeReferenceActorSweep(
            string actorName,
            string clipName,
            float[] sampleTimes,
            string outputDirectory,
            string stem)
        {
            if (sampleTimes == null || sampleTimes.Length == 0)
                throw new ArgumentException("Sweep requires at least one sample.", nameof(sampleTimes));
            if (string.IsNullOrWhiteSpace(outputDirectory) ||
                Path.IsPathRooted(outputDirectory) ||
                outputDirectory.Contains(".."))
            {
                throw new ArgumentException(
                    "Sweep output directory must be a relative path.",
                    nameof(outputDirectory));
            }

            EnsureHGCompatRenderPipelineAssigned();
            if (!File.Exists(Path.Combine(Directory.GetCurrentDirectory(), ViewerScenePath)))
            {
                throw new FileNotFoundException(
                    "Build the shared character viewer scene before rendering a runtime sweep.",
                    ViewerScenePath);
            }

            Scene scene = EditorSceneManager.OpenScene(ViewerScenePath, OpenSceneMode.Single);
            EnsureOriginalStylePresentationScene(scene);
            Transform charactersRoot = FindSceneGameObject("Characters")?.transform;
            if (charactersRoot == null)
                throw new InvalidOperationException("Shared viewer scene has no Characters root.");

            GameObject actorRoot = FindSceneGameObject(actorName);
            if (actorRoot == null)
            {
                string prefabPath =
                    $"{GeneratedRoot}/Playable/{actorName}/Prefabs/{actorName}.prefab";
                GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
                if (prefab == null)
                    throw new FileNotFoundException(
                        $"Runtime-reference actor prefab is missing: {actorName}",
                        prefabPath);
                actorRoot = PrefabUtility.InstantiatePrefab(prefab, scene) as GameObject;
                if (actorRoot == null)
                {
                    throw new InvalidOperationException(
                        $"Could not instantiate runtime-reference actor: {actorName}");
                }
                actorRoot.name = actorName;
                actorRoot.transform.SetParent(charactersRoot, false);
            }

            foreach (Transform child in charactersRoot)
            {
                if (child != null)
                    child.gameObject.SetActive(child.gameObject == actorRoot.transform);
            }
            actorRoot.transform.localPosition = Vector3.zero;
            actorRoot.transform.localRotation = Quaternion.identity;
            actorRoot.transform.localScale = Vector3.one;
            actorRoot.SetActive(true);

            string clipPath =
                $"{GeneratedRoot}/Playable/{actorName}/Animations/{Safe(clipName)}.anim";
            AnimationClip clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(clipPath);
            if (clip == null)
                throw new FileNotFoundException(
                    $"Runtime-reference overview clip is missing: {clipName}",
                    clipPath);
            Animation animation = actorRoot.GetComponent<Animation>();
            if (animation == null)
                animation = actorRoot.AddComponent<Animation>();
            if (animation[clipName] == null)
                animation.AddClip(clip, clipName);
            animation.clip = clip;
            animation.Stop();
            SetRecoveredPropVisibility(actorRoot, Array.Empty<string>());

            var lightingRoot = FindSceneGameObject("Lighting")?.transform;
            ConfigurePreviewLighting(scene, lightingRoot);
            ApplyGeneratedMaterialProfileFlags();
            ApplyGeneratedTextureImportProfiles();
            PruneLowerQualityMeshLodsFromOpenScene();

            Camera camera = Camera.main ?? UnityEngine.Object.FindObjectOfType<Camera>();
            if (camera == null)
                throw new InvalidOperationException("Shared viewer scene has no camera.");
            ConfigureOperatorReferenceLighting(
                scene,
                lightingRoot,
                camera,
                actorName,
                actorRoot.transform);
            FrameCameraToRecoveredOperatorCamera(camera, actorName);
            ApplyComparisonCameraOverrideIfRequested(camera);
            EndfieldRecoveredCharInfoBackgroundPortraitBuilder.EnsureAndBind(
                camera,
                actorName,
                actorRoot.transform);
            if (IsEnvironmentFlagEnabled(FittedCompositorTranslationEnvironmentVariable))
                ApplyRuntimeReferenceCompositorTranslation(camera, actorName);

            Bounds bounds = CombinedBounds(
                actorRoot.GetComponentsInChildren<SkinnedMeshRenderer>(true));
            ConfigureReferenceBackdrop(
                scene,
                FindBackdropRoot(),
                camera,
                bounds,
                (float)RuntimeReferenceRenderWidth / RuntimeReferenceRenderHeight);

            string outputRoot = Path.GetFullPath(
                Path.Combine(Application.dataPath, "../../scratch", outputDirectory));
            Directory.CreateDirectory(outputRoot);
            for (int index = 0; index < sampleTimes.Length; index++)
            {
                float sampleTime = sampleTimes[index];
                if (float.IsNaN(sampleTime) || float.IsInfinity(sampleTime) || sampleTime < 0f)
                {
                    throw new InvalidDataException(
                        $"Sweep sample {index} is not a finite non-negative time: {sampleTime}.");
                }
                clip.SampleAnimation(actorRoot, Mathf.Clamp(sampleTime, 0f, clip.length));
                CharacterProceduralIk poseCorrection =
                    actorRoot.GetComponent<CharacterProceduralIk>();
                if (poseCorrection != null)
                    poseCorrection.Evaluate();

                string fileName = stem + "_t" +
                    sampleTime.ToString("0.000", CultureInfo.InvariantCulture)
                        .Replace('.', 'p') + ".png";
                string outputPath = Path.Combine(outputRoot, fileName);
                RenderPreview(outputPath, RuntimeReferenceRenderWidth, RuntimeReferenceRenderHeight);
                RenderRuntimeReferenceActorBackgroundOnly(
                    actorRoot,
                    Path.Combine(outputRoot, Path.GetFileNameWithoutExtension(fileName) + "_background_only.png"));
                Debug.Log(
                    $"Rendered {actorName} sweep sample {index + 1}/{sampleTimes.Length} " +
                    $"at {sampleTime:0.###}s: {outputPath}");
            }
            Debug.Log(
                $"Runtime reference sweep complete: actor={actorName}, " +
                $"samples={sampleTimes.Length}, output={outputRoot}");
        }

        private static void RenderRuntimeReferenceActorBackgroundOnly(GameObject actorRoot, string outputPath)
        {
            Renderer[] renderers = actorRoot.GetComponentsInChildren<Renderer>(true);
            bool[] states = renderers.Select(r => r.enabled).ToArray();
            try
            {
                for (int i = 0; i < renderers.Length; i++) renderers[i].enabled = false;
                RenderPreview(outputPath, RuntimeReferenceRenderWidth, RuntimeReferenceRenderHeight);
            }
            finally
            {
                for (int i = 0; i < renderers.Length; i++)
                    if (renderers[i] != null) renderers[i].enabled = states[i];
            }
            if (!File.Exists(outputPath) || new FileInfo(outputPath).Length == 0)
                throw new InvalidOperationException("Background-only capture was not written.");
        }

        // This pass is deliberately separate from the beauty capture. It uses
        // the same camera/pose but a temporary actor-only culling layer and a
        // replacement unlit shader, producing a binary object-coverage mask.
        // No material, lighting, backdrop, or beauty-camera state is retained.
        private static void RenderRuntimeReferenceActorObjectIdMask(
            GameObject actorRoot,
            Camera camera,
            string outputPath)
        {
            RenderRuntimeReferenceActorObjectIdMaskCommandBuffer(actorRoot, camera, outputPath);
            return;
            /* Legacy camera isolation implementation retained below for audit
             * history; the command-buffer path bypasses HGCompat postprocess. */
            #pragma warning disable CS0162
            if (actorRoot == null || camera == null)
                throw new ArgumentNullException(actorRoot == null ? nameof(actorRoot) : nameof(camera));
            Shader replacement = Shader.Find("Hidden/Endfield/ActorObjectIdMask");
            if (replacement == null)
                throw new InvalidOperationException("Exact actor object-ID mask requires Unlit/Color replacement shader.");
            int savedMask = camera.cullingMask;
            CameraClearFlags savedFlags = camera.clearFlags;
            Color savedBackground = camera.backgroundColor;
            RenderTexture savedTarget = camera.targetTexture;
            var transforms = actorRoot.GetComponentsInChildren<Transform>(true);
            var layers = new int[transforms.Length];
            var allRenderers = UnityEngine.Object.FindObjectsOfType<Renderer>(true);
            var rendererStates = new bool[allRenderers.Length];
            var rendererMaterials = new Material[allRenderers.Length][];
            var allCanvases = UnityEngine.Object.FindObjectsOfType<Canvas>(true);
            var canvasStates = new bool[allCanvases.Length];
            const int maskLayer = 31;
            try
            {
                for (int i = 0; i < allRenderers.Length; i++)
                {
                    rendererStates[i] = allRenderers[i].enabled;
                    bool owned = allRenderers[i].transform.IsChildOf(actorRoot.transform) || allRenderers[i].transform == actorRoot.transform;
                    allRenderers[i].enabled = owned && rendererStates[i];
                    if (owned && allRenderers[i].enabled)
                    {
                        rendererMaterials[i] = allRenderers[i].sharedMaterials;
                        var maskMaterials = new Material[rendererMaterials[i].Length];
                        for (int j = 0; j < maskMaterials.Length; j++) maskMaterials[j] = new Material(replacement);
                        allRenderers[i].sharedMaterials = maskMaterials;
                    }
                }
                for (int i = 0; i < allCanvases.Length; i++)
                {
                    canvasStates[i] = allCanvases[i].enabled;
                    allCanvases[i].enabled = false;
                }
                for (int i = 0; i < transforms.Length; i++)
                {
                    layers[i] = transforms[i].gameObject.layer;
                    transforms[i].gameObject.layer = maskLayer;
                }
                camera.cullingMask = 1 << maskLayer;
                camera.clearFlags = CameraClearFlags.SolidColor;
                camera.backgroundColor = Color.white;
                var target = new RenderTexture(RuntimeReferenceRenderWidth, RuntimeReferenceRenderHeight, 24, RenderTextureFormat.ARGB32);
                var texture = new Texture2D(RuntimeReferenceRenderWidth, RuntimeReferenceRenderHeight, TextureFormat.RGB24, false, true);
                try
                {
                    camera.targetTexture = target;
                    RenderTexture previousForClear = RenderTexture.active;
                    RenderTexture.active = target;
                    GL.Clear(true, true, Color.black);
                    RenderTexture.active = previousForClear;
                camera.Render();
                    RenderTexture previous = RenderTexture.active;
                    RenderTexture.active = target;
                    texture.ReadPixels(new Rect(0, 0, target.width, target.height), 0, 0, false);
                    texture.Apply(false, false);
                    RenderTexture.active = previous;
                    Color32[] pixels = texture.GetPixels32();
                    int nonEmpty = 0;
                    for (int i = 0; i < pixels.Length; i++)
                    {
                        byte value = (byte)(pixels[i].r < 248 || pixels[i].g < 248 || pixels[i].b < 248 ? 255 : 0);
                        if (value != 0) nonEmpty++;
                        pixels[i] = new Color32(value, value, value, 255);
                    }
                    float coverage = (float)nonEmpty / pixels.Length;
                    if (nonEmpty == 0 || coverage > 0.80f)
                        throw new InvalidOperationException($"Actor object-ID mask coverage implausible: {coverage:0.0000}.");
                    int corner = 32;
                    if (pixels[corner * target.width + corner].r != 0 ||
                        pixels[corner * target.width + target.width - corner - 1].r != 0 ||
                        pixels[(target.height - corner - 1) * target.width + corner].r != 0 ||
                        pixels[(target.height - corner - 1) * target.width + target.width - corner - 1].r != 0)
                        throw new InvalidOperationException("Actor object-ID mask background corners are not black.");
                    texture.SetPixels32(pixels);
                    texture.Apply(false, false);
                    Directory.CreateDirectory(Path.GetDirectoryName(outputPath) ?? ".");
                    File.WriteAllBytes(outputPath, texture.EncodeToPNG());
                }
                finally
                {
                    UnityEngine.Object.DestroyImmediate(texture);
                    UnityEngine.Object.DestroyImmediate(target);
                }
            }
            finally
            {
                for (int i = 0; i < transforms.Length; i++)
                    if (transforms[i] != null) transforms[i].gameObject.layer = layers[i];
                for (int i = 0; i < allRenderers.Length; i++)
                    if (allRenderers[i] != null)
                    {
                        if (rendererMaterials[i] != null)
                        {
                            Material[] temporary = allRenderers[i].sharedMaterials;
                            allRenderers[i].sharedMaterials = rendererMaterials[i];
                            for (int j = 0; j < temporary.Length; j++)
                                if (temporary[j] != null) UnityEngine.Object.DestroyImmediate(temporary[j]);
                        }
                        allRenderers[i].enabled = rendererStates[i];
                    }
                for (int i = 0; i < allCanvases.Length; i++)
                    if (allCanvases[i] != null) allCanvases[i].enabled = canvasStates[i];
                camera.cullingMask = savedMask;
                camera.clearFlags = savedFlags;
                camera.backgroundColor = savedBackground;
                camera.targetTexture = savedTarget;
            }
        }

        private static void RenderRuntimeReferenceActorObjectIdMaskCommandBuffer(
            GameObject actorRoot, Camera camera, string outputPath)
        {
            Shader shader = Shader.Find("Hidden/Endfield/ActorObjectIdMask");
            if (shader == null) throw new InvalidOperationException("Actor mask shader missing.");
            var renderers = actorRoot.GetComponentsInChildren<Renderer>(true)
                .Where(r => r.enabled && r.transform.IsChildOf(actorRoot.transform)).ToArray();
            if (renderers.Length == 0) throw new InvalidOperationException("Actor has no enabled renderers.");
            var material = new Material(shader);
            var target = new RenderTexture(RuntimeReferenceRenderWidth, RuntimeReferenceRenderHeight, 24, RenderTextureFormat.ARGB32);
            var texture = new Texture2D(RuntimeReferenceRenderWidth, RuntimeReferenceRenderHeight, TextureFormat.RGB24, false, true);
            var command = new CommandBuffer { name = "Endminf actor object-ID mask" };
            try
            {
                target.Create();
                command.SetRenderTarget(target);
                command.ClearRenderTarget(true, true, Color.black);
                command.SetViewProjectionMatrices(camera.worldToCameraMatrix,
                    GL.GetGPUProjectionMatrix(camera.projectionMatrix, true));
                foreach (Renderer renderer in renderers)
                {
                    int submeshes = renderer is SkinnedMeshRenderer skinned && skinned.sharedMesh != null
                        ? skinned.sharedMesh.subMeshCount
                        : renderer.GetComponent<MeshFilter>()?.sharedMesh?.subMeshCount ?? 1;
                    for (int submesh = 0; submesh < submeshes; submesh++)
                        command.DrawRenderer(renderer, material, submesh, 0);
                }
                Graphics.ExecuteCommandBuffer(command);
                RenderTexture previous = RenderTexture.active;
                RenderTexture.active = target;
                texture.ReadPixels(new Rect(0, 0, target.width, target.height), 0, 0, false);
                texture.Apply(false, false);
                RenderTexture.active = previous;
                Color32[] pixels = texture.GetPixels32();
                int nonEmpty = 0;
                for (int i = 0; i < pixels.Length; i++)
                {
                    byte value = pixels[i].r > 8 || pixels[i].g > 8 || pixels[i].b > 8 ? (byte)255 : (byte)0;
                    if (value != 0) nonEmpty++;
                    pixels[i] = new Color32(value, value, value, 255);
                }
                float coverage = (float)nonEmpty / pixels.Length;
                int w = target.width, h = target.height, c = 32;
                if (coverage <= 0f || coverage > .8f || pixels[c*w+c].r != 0 || pixels[c*w+w-c-1].r != 0 ||
                    pixels[(h-c-1)*w+c].r != 0 || pixels[(h-c-1)*w+w-c-1].r != 0)
                    throw new InvalidOperationException($"Command-buffer actor mask invalid: coverage={coverage:0.0000}.");
                texture.SetPixels32(pixels); texture.Apply(false, false);
                Directory.CreateDirectory(Path.GetDirectoryName(outputPath) ?? ".");
                File.WriteAllBytes(outputPath, texture.EncodeToPNG());
            }
            finally
            {
                command.Release();
                UnityEngine.Object.DestroyImmediate(material);
                UnityEngine.Object.DestroyImmediate(texture);
                UnityEngine.Object.DestroyImmediate(target);
            }
        }

        [MenuItem("Endfield/Character Recovery Lab/Render Far Shared Viewer Preview")]
        public static void RenderSharedViewerFarPreview()
        {
            EnsureHGCompatRenderPipelineAssigned();
            if (!File.Exists(Path.Combine(Directory.GetCurrentDirectory(), ViewerScenePath)))
                throw new FileNotFoundException("Build the shared character viewer scene before rendering a preview.", ViewerScenePath);

            var scene = EditorSceneManager.OpenScene(ViewerScenePath, OpenSceneMode.Single);
            var lightingRoot = FindSceneGameObject("Lighting")?.transform;
            ConfigurePreviewLighting(scene, lightingRoot);
            ApplyGeneratedMaterialProfileFlags();
            ApplyGeneratedTextureImportProfiles();
            PruneLowerQualityMeshLodsFromOpenScene();
            SampleActivePreviewAnimations(scene);

            var camera = Camera.main ?? UnityEngine.Object.FindObjectOfType<Camera>();
            var renderers = UnityEngine.Object.FindObjectsOfType<SkinnedMeshRenderer>();
            if (camera != null && renderers.Length > 0)
            {
                Bounds bounds = CombinedBounds(renderers);
                FrameFarCamera(camera, bounds);
                ConfigureReferenceBackdrop(scene, FindBackdropRoot(), camera, bounds);
            }

            string previewPath = Path.GetFullPath(Path.Combine(Application.dataPath, "../../scratch/character_recovery/character_recovery_viewer_far.png"));
            Directory.CreateDirectory(Path.GetDirectoryName(previewPath) ?? ".");
            RenderPreview(previewPath);
            AssetDatabase.Refresh();
            Debug.Log($"Rendered far character recovery viewer preview: {previewPath}");
        }

        private static void EnsureHGCompatRenderPipelineAssigned()
        {
            var pipelineAsset = AssetDatabase.LoadAssetAtPath<HGCompatRenderPipelineAsset>(
                HGCompatRenderPipelineAssetPath);
            if (pipelineAsset == null)
                throw new InvalidOperationException(
                    $"HG compatibility render-pipeline asset is missing or invalid: {HGCompatRenderPipelineAssetPath}");

            if (GraphicsSettings.renderPipelineAsset != pipelineAsset)
                GraphicsSettings.renderPipelineAsset = pipelineAsset;
            if (QualitySettings.renderPipeline != pipelineAsset)
                QualitySettings.renderPipeline = pipelineAsset;

            EditorUtility.SetDirty(pipelineAsset);
            Debug.Log($"HG compatibility render pipeline assigned: {HGCompatRenderPipelineAssetPath}");
        }

        private sealed class ViewerSceneLayout
        {
            public GameObject Root;
            public Transform BackdropRoot;
            public Transform CharactersRoot;
            public Transform LightingRoot;
        }

        private static ViewerSceneLayout CreateViewerSceneLayout()
        {
            var scene = SceneManager.GetActiveScene();
            var root = new GameObject(ViewerRootObjectName);
            SceneManager.MoveGameObjectToScene(root, scene);
            return new ViewerSceneLayout
            {
                Root = root,
                BackdropRoot = CreateChildGroup(root.transform, "Backdrop"),
                CharactersRoot = CreateChildGroup(root.transform, "Characters"),
                LightingRoot = CreateChildGroup(root.transform, "Lighting"),
            };
        }

        private static Transform CreateChildGroup(Transform parent, string name)
        {
            var group = new GameObject(name);
            group.transform.SetParent(parent, false);
            group.transform.localPosition = Vector3.zero;
            group.transform.localRotation = Quaternion.identity;
            group.transform.localScale = Vector3.one;
            return group.transform;
        }

        [MenuItem("Endfield/Character Recovery Lab/Build Manifest Character Recovery")]
        public static void Build()
        {
            EnsureFolders();

            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var zhuangfy = BuildActor(
                ResolveManifestAssetPath(ZhuangfyManifestAssetPath, LegacyZhuangfyManifestAssetPath),
                "actor_zhuangfy_unity_recovery",
                "Zhuangfy 01 game postmodel",
                Vector3.zero,
                true,
                ZhuangfyPreviewClipPreference);

            string mifuManifestAssetPath = ResolveManifestAssetPath(MifuManifestAssetPath, LegacyMifuManifestAssetPath);
            string mifuManifestPath = Path.Combine(Directory.GetCurrentDirectory(), mifuManifestAssetPath);
            if (File.Exists(mifuManifestPath))
            {
                BuildActor(
                    mifuManifestAssetPath,
                    "actor_mifu_unity_recovery",
                    "Mifu 01 game postmodel",
                    new Vector3(4f, 0f, 0f),
                    false,
                    MifuPreviewClipPreference);
            }

            ConfigureScene(zhuangfy.Root, zhuangfy.MeshObjects);

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            EditorSceneManager.SaveScene(SceneManager.GetActiveScene(), ManifestScenePath);
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ManifestScenePath, true) };
            Debug.Log($"Manifest character recovery scene complete: {zhuangfy.MeshObjects.Count} active Zhuangfy skinned meshes, {zhuangfy.Clips.Count} clips.");
        }

        public static List<GameObject> BuildIntoCurrentScene()
        {
            return BuildIntoCurrentScene(SharedViewerCharacters());
        }

        public static List<GameObject> BuildIntoCurrentScene(IEnumerable<ManifestCharacterSpec> characters)
        {
            EnsureFolders();
            var roots = new List<GameObject>();
            foreach (ManifestCharacterSpec character in characters)
            {
                GameObject root = BuildCharacter(character);
                if (root != null)
                    roots.Add(root);
            }
            return roots;
        }

        public static GameObject BuildCharacter(ManifestCharacterSpec character)
        {
            if (character == null)
                throw new ArgumentNullException(nameof(character));

            string manifestPath = Path.Combine(Directory.GetCurrentDirectory(), character.ManifestAssetPath);
            if (!File.Exists(manifestPath))
                return null;

            return BuildActor(
                character.ManifestAssetPath,
                character.RootName,
                character.DisplayName,
                character.SceneOffset,
                character.Active,
                character.PreviewClipPreference,
                character.IncludeVariants).Root;
        }

        public static void RebuildZhuangfyPrefabForGachaRuntime()
        {
            EnsureFolders();
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            ManifestCharacterSpec zhuangfy = SharedViewerCharacters().Single(character =>
                string.Equals(character.RootName, "Zhuangfy", StringComparison.OrdinalIgnoreCase));
            GameObject root = BuildCharacter(zhuangfy);
            if (root == null)
                throw new InvalidOperationException("Zhuangfy manifest character rebuild returned no root");
            UnityEngine.Object.DestroyImmediate(root);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
        }

        private sealed class ActorBuildResult
        {
            public GameObject Root;
            public string RootName;
            public string DisplayName;
            public string PrefabAssetPath;
            public List<GameObject> MeshObjects;
            public List<AnimationClip> Clips;
        }

        private static void MergeZhuangfyWidget03Manifest(
            Dictionary<string, object> manifest,
            string rootName)
        {
            if (!string.Equals(rootName, "Zhuangfy", StringComparison.OrdinalIgnoreCase))
                return;

            string supplementPath = Path.Combine(
                Directory.GetCurrentDirectory(),
                ZhuangfyWidget03ManifestAssetPath);
            if (!File.Exists(supplementPath))
                return;

            var supplement = Dict(ManifestMiniJson.Deserialize(
                File.ReadAllText(supplementPath, Encoding.UTF8)));
            string actor = Str(supplement.TryGetValue("actor", out object actorObj) ? actorObj : null);
            if (!string.Equals(actor, "zhuangfy", StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException(
                    $"Unexpected widget03 supplemental actor '{actor}' in {supplementPath}.");

            MergeManifestList(
                manifest,
                supplement,
                "scene_transforms",
                item => Str(item.TryGetValue("path", out object value) ? value : null));
            MergeManifestDictionary(manifest, supplement, "materials");
            MergeManifestList(
                manifest,
                supplement,
                "meshes",
                item =>
                    Str(item.TryGetValue("name", out object nameObj) ? nameObj : null) + "|" +
                    Str(item.TryGetValue("path", out object pathObj) ? pathObj : null));
            MergeManifestClipUpgrades(manifest, supplement);
            MergeManifestList(
                manifest,
                supplement,
                "recovered_states",
                RecoveredStateIdentity);
        }

        private static void MergeManifestDictionary(
            Dictionary<string, object> destination,
            Dictionary<string, object> supplement,
            string key)
        {
            var merged = new Dictionary<string, object>(
                Dict(destination.TryGetValue(key, out object destinationObj) ? destinationObj : null),
                StringComparer.OrdinalIgnoreCase);
            foreach (var pair in Dict(
                supplement.TryGetValue(key, out object supplementObj) ? supplementObj : null))
            {
                if (merged.ContainsKey(pair.Key))
                    throw new InvalidOperationException(
                        $"Zhuangfy widget03 supplemental {key} conflict: {pair.Key}");
                merged.Add(pair.Key, pair.Value);
            }
            destination[key] = merged;
        }

        private static void MergeManifestClipUpgrades(
            Dictionary<string, object> destination,
            Dictionary<string, object> supplement)
        {
            var merged = new List<object>();
            var indexByName = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
            foreach (object clipObj in List(
                destination.TryGetValue("clips", out object destinationObj) ? destinationObj : null))
            {
                var clip = Dict(clipObj);
                string name = Str(clip.TryGetValue("name", out object nameObj) ? nameObj : null);
                if (name.Length > 0 && !indexByName.ContainsKey(name))
                    indexByName.Add(name, merged.Count);
                merged.Add(clipObj);
            }

            foreach (object clipObj in List(
                supplement.TryGetValue("clips", out object supplementObj) ? supplementObj : null))
            {
                var clip = Dict(clipObj);
                string name = Str(clip.TryGetValue("name", out object nameObj) ? nameObj : null);
                if (name.Length == 0)
                    throw new InvalidOperationException(
                        "Zhuangfy widget03 supplemental clip has no name.");
                if (!indexByName.TryGetValue(name, out int existingIndex))
                {
                    indexByName.Add(name, merged.Count);
                    merged.Add(clipObj);
                    continue;
                }

                var existing = Dict(merged[existingIndex]);
                int existingMatched = Int(existing.TryGetValue(
                    "matched_transform_count", out object existingMatchedObj)
                        ? existingMatchedObj
                        : null);
                int existingMissing = Int(existing.TryGetValue(
                    "missing_transform_count", out object existingMissingObj)
                        ? existingMissingObj
                        : null);
                int upgradedMatched = Int(clip.TryGetValue(
                    "matched_transform_count", out object upgradedMatchedObj)
                        ? upgradedMatchedObj
                        : null);
                int upgradedMissing = Int(clip.TryGetValue(
                    "missing_transform_count", out object upgradedMissingObj)
                        ? upgradedMissingObj
                        : null);
                if (existingMatched != 1 || existingMissing != 38 ||
                    upgradedMatched != 39 || upgradedMissing != 0)
                {
                    throw new InvalidOperationException(
                        $"Zhuangfy widget03 supplemental clip conflict is not the verified " +
                        $"1/39 -> 39/39 upgrade: {name} existing={existingMatched}/{existingMissing} " +
                        $"supplement={upgradedMatched}/{upgradedMissing}");
                }
                merged[existingIndex] = clipObj;
            }
            destination["clips"] = merged;
        }

        private static void MergeManifestList(
            Dictionary<string, object> destination,
            Dictionary<string, object> supplement,
            string key,
            Func<Dictionary<string, object>, string> identity)
        {
            var merged = new List<object>();
            var identities = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (object itemObj in List(
                destination.TryGetValue(key, out object destinationObj) ? destinationObj : null))
            {
                merged.Add(itemObj);
                string itemIdentity = identity(Dict(itemObj));
                if (itemIdentity.Length > 0)
                    identities.Add(itemIdentity);
            }

            foreach (object itemObj in List(
                supplement.TryGetValue(key, out object supplementObj) ? supplementObj : null))
            {
                string itemIdentity = identity(Dict(itemObj));
                if (itemIdentity.Length == 0)
                    throw new InvalidOperationException(
                        $"Zhuangfy widget03 supplemental {key} entry has no identity.");
                if (!identities.Add(itemIdentity))
                    throw new InvalidOperationException(
                        $"Zhuangfy widget03 supplemental {key} conflict: {itemIdentity}");
                merged.Add(itemObj);
            }
            destination[key] = merged;
        }

        private static string RecoveredStateIdentity(Dictionary<string, object> state)
        {
            string baseClip = Str(
                state.TryGetValue("base_clip", out object baseObj) ? baseObj : null);
            var layerIdentities = new List<string>();
            foreach (object layerObj in List(
                state.TryGetValue("layers", out object layersObj) ? layersObj : null))
            {
                var layer = Dict(layerObj);
                string role = Str(layer.TryGetValue("role", out object roleObj) ? roleObj : null);
                string clip = Str(layer.TryGetValue("clip", out object clipObj) ? clipObj : null);
                if (clip.Length > 0)
                    layerIdentities.Add(role + ":" + clip);
            }
            layerIdentities.Sort(StringComparer.OrdinalIgnoreCase);
            return baseClip + "|" + string.Join(",", layerIdentities.ToArray());
        }

        private static ActorBuildResult BuildActor(
            string manifestAssetPath,
            string rootName,
            string displayName,
            Vector3 sceneOffset,
            bool active,
            string[] previewPreference,
            bool includeVariants = true,
            bool rebuildAnimationAssets = true,
            bool clearGeneratedAssets = true,
            bool rebuildMeshAssets = true,
            bool rebuildMaterialAssets = true,
            bool configureSourceCharacterSemantics = true)
        {
            string manifestPath = Path.Combine(Directory.GetCurrentDirectory(), manifestAssetPath);
            var manifest = Dict(ManifestMiniJson.Deserialize(File.ReadAllText(manifestPath, Encoding.UTF8)));
            string actorPrefix = Str(manifest.TryGetValue("model", out object modelObj) ? modelObj : null, rootName);

            var root = new GameObject(rootName);
            root.transform.position = sceneOffset;
            root.transform.rotation = Quaternion.identity;
            root.transform.localScale = Vector3.one;

            IList transformManifest = manifest.TryGetValue("scene_transforms", out object sceneTransformsObj)
                ? List(sceneTransformsObj)
                : manifest.TryGetValue("transforms", out object transformsObj)
                ? List(transformsObj)
                : List(manifest.TryGetValue("bones", out object bonesObj) ? bonesObj : null);
            transformManifest = HighestQualityTransformManifest(transformManifest);
            var transformsByPath = BuildSkeleton(root.transform, transformManifest);
            var transformsByCrc = new Dictionary<long, Transform>();
            foreach (var transformObj in transformManifest)
            {
                var item = Dict(transformObj);
                string path = Str(item["path"]);
                if (path.Length == 0 || !transformsByPath.TryGetValue(path, out Transform tr))
                    continue;
                transformsByCrc[Long(item["path_crc"])] = tr;
            }

            string actorGeneratedRoot = ActorGeneratedRoot(manifestAssetPath, rootName);
            EnsureActorFolders(actorGeneratedRoot, clearGeneratedAssets);
            var materialCache = BuildMaterials(
                Dict(manifest.TryGetValue("materials", out object materialsObj)
                    ? materialsObj
                    : null),
                actorPrefix,
                actorGeneratedRoot,
                rebuildMaterialAssets);
            var meshObjects = BuildMeshes(
                root.transform,
                List(manifest.TryGetValue("meshes", out object meshesObj)
                    ? meshesObj
                    : null),
                materialCache,
                transformsByPath,
                transformsByCrc,
                actorGeneratedRoot,
                rebuildMeshAssets);
            BuildRecoveredLodGroups(
                root.transform,
                List(manifest.TryGetValue("recovered_lod_groups", out object recoveredLodGroupsObj)
                    ? recoveredLodGroupsObj
                    : null));
            meshObjects.AddRange(BuildStaticProps(
                root.transform,
                List(manifest.TryGetValue("static_props", out object staticPropsObj) ? staticPropsObj : null),
                materialCache,
                actorGeneratedRoot));
            var clips = rebuildAnimationAssets
                ? BuildAnimationClips(
                    List(manifest.TryGetValue("clips", out object clipsObj)
                        ? clipsObj
                        : null),
                    root,
                    actorGeneratedRoot)
                : LoadExistingAnimationClips(actorGeneratedRoot);
            AddOriginalF5FullPoseFixture(root, rootName, actorGeneratedRoot, clips);
            ConfigureAnimation(root, clips, displayName, previewPreference);
            ConfigureRecoveredOverviewPlayback(root, manifest, actorGeneratedRoot);
            if (configureSourceCharacterSemantics)
                ConfigureRecoveredSkeletalMorphBasePose(root, manifest);
            ConfigureClipMetadata(
                root,
                List(manifest.TryGetValue("clips", out object clipMetadataObj)
                    ? clipMetadataObj
                    : null));
            ConfigureRecoveredStates(root, List(manifest.TryGetValue("recovered_states", out object statesObj) ? statesObj : null));
            ConfigureIk(root, transformsByPath, Dict(manifest.TryGetValue("ik", out object ikObj) ? ikObj : null));
            if (includeVariants)
                BuildModelVariants(manifest, transformManifest, materialCache, clips, Dict(manifest.TryGetValue("ik", out object variantIkObj) ? variantIkObj : null), previewPreference, actorGeneratedRoot);
            string prefabAssetPath = $"{actorGeneratedRoot}/Prefabs/{Safe(rootName)}.prefab";
            // A generated prefab is an asset template, not the legacy scene's
            // selected-model state. Keep every playable prefab root active so
            // targeted prefab replacement cannot deactivate a resident viewer
            // instance when Unity regenerates the prefab's local file IDs.
            // Restore the requested scene-object state after saving.
            root.SetActive(true);
            PrefabUtility.SaveAsPrefabAsset(root, prefabAssetPath);
            root.SetActive(active);
            RemoveStaleUnsupportedLastRiteFallbackAssets(rootName, actorGeneratedRoot);
            Debug.Log($"Built {displayName}: {meshObjects.Count} skinned meshes, {transformsByPath.Count} transforms, {clips.Count} clips.");

            return new ActorBuildResult
            {
                Root = root,
                RootName = rootName,
                DisplayName = displayName,
                PrefabAssetPath = prefabAssetPath,
                MeshObjects = meshObjects,
                Clips = clips,
            };
        }

        [MenuItem("Endfield/Character Recovery Lab/Verify Manifest Character Recovery")]
        public static void Verify()
        {
            var scene = EditorSceneManager.OpenScene(ManifestScenePath, OpenSceneMode.Single);
            var root = FindSceneGameObject("actor_zhuangfy_unity_recovery");
            if (root == null)
                throw new InvalidOperationException("Missing actor_zhuangfy_unity_recovery root in generated scene.");
            var mifuRoot = FindSceneGameObject("actor_mifu_unity_recovery");

            string manifestPath = Path.Combine(Directory.GetCurrentDirectory(), ResolveManifestAssetPath(ZhuangfyManifestAssetPath, LegacyZhuangfyManifestAssetPath));
            var manifest = Dict(ManifestMiniJson.Deserialize(File.ReadAllText(manifestPath, Encoding.UTF8)));
            int expectedRendererCount = CountHighestQualityMeshes(List(manifest["meshes"]));
            int expectedClipCount = List(manifest["clips"]).Count;
            int expectedRecoveredStateCount = List(manifest.TryGetValue("recovered_states", out object recoveredStatesObj) ? recoveredStatesObj : null).Count;

            var renderers = root.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            int totalSceneRendererCount = 0;
            int activeSceneRendererCount = 0;
            foreach (var sceneRenderer in UnityEngine.Object.FindObjectsOfType<SkinnedMeshRenderer>(true))
            {
                if (sceneRenderer == null || !sceneRenderer.gameObject.scene.IsValid())
                    continue;
                totalSceneRendererCount++;
                if (sceneRenderer.enabled && sceneRenderer.gameObject.activeInHierarchy)
                    activeSceneRendererCount++;
            }
            var animation = root.GetComponent<Animation>();
            if (animation == null)
                throw new InvalidOperationException("Generated root has no Animation component.");
            var rig = root.GetComponent<CharacterRecoveryRig>();
            var viewer = UnityEngine.Object.FindObjectOfType<CharacterRecoveryViewerUI>(true);
            int recoveredStateCount = rig != null && rig.recoveredStates != null ? rig.recoveredStates.Length : 0;
            int clipMetadataCount = rig != null && rig.clipMetadata != null ? rig.clipMetadata.Length : 0;
            var clipCategories = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            if (rig != null && rig.clipMetadata != null)
            {
                foreach (var metadata in rig.clipMetadata)
                {
                    if (metadata == null || string.IsNullOrEmpty(metadata.clipCategory))
                        continue;
                    clipCategories.Add(metadata.clipCategory);
                }
            }

            var clips = new List<AnimationClip>();
            foreach (AnimationState state in animation)
                clips.Add(state.clip);
            if (viewer != null)
                throw new InvalidOperationException("Generated scene should not include the runtime CharacterRecoveryViewerUI clip selector; use Unity's built-in Animation inspector/window.");
            if (expectedRendererCount > 0 && renderers.Length != expectedRendererCount)
                throw new InvalidOperationException($"Expected {expectedRendererCount} skinned meshes, found {renderers.Length}.");
            if (activeSceneRendererCount != renderers.Length)
                throw new InvalidOperationException($"Expected only the base rig to be visibly active ({renderers.Length}), found {activeSceneRendererCount} active scene skinned meshes.");
            if (clips.Count != expectedClipCount)
                throw new InvalidOperationException($"Expected {expectedClipCount} clips, found {clips.Count}.");
            if (clipMetadataCount != expectedClipCount)
                throw new InvalidOperationException($"Expected {expectedClipCount} clip metadata entries, found {clipMetadataCount}.");
            if (clipCategories.Count < 4)
                throw new InvalidOperationException($"Expected detailed clip category metadata, found only {clipCategories.Count} categories.");
            if (recoveredStateCount != expectedRecoveredStateCount)
                throw new InvalidOperationException($"Expected {expectedRecoveredStateCount} recovered states, found {recoveredStateCount}.");

            Bounds before = CombinedBounds(renderers);
            AnimationClip previewClip = SelectPreviewClip(clips, ZhuangfyPreviewClipPreference);
            int previewCurveCount = previewClip != null ? AnimationUtility.GetCurveBindings(previewClip).Length : 0;
            var poseCorrection = root.GetComponent<CharacterProceduralIk>();
            if (previewClip != null)
            {
                previewClip.SampleAnimation(root, Mathf.Min(previewClip.length * 0.12f, previewClip.length));
                if (poseCorrection != null)
                    poseCorrection.Evaluate();
            }
            Bounds after = CombinedBounds(renderers);
            if (before.size.magnitude < 0.1f || after.size.magnitude < 0.1f)
                throw new InvalidOperationException("Generated renderer bounds are unexpectedly tiny.");

            string repoRoot = Path.GetFullPath(Path.Combine(Application.dataPath, "..", ".."));
            string outDir = Path.Combine(repoRoot, "scratch", "zhuangfy_unity_verify");
            Directory.CreateDirectory(outDir);
            string pngPath = Path.Combine(outDir, "zhuangfy_unity_recovery_preview.png");
            var previewCamera = Camera.main ?? UnityEngine.Object.FindObjectOfType<Camera>();
            if (previewCamera != null)
                FrameCamera(previewCamera, after);
            bool flatGrayBackground = previewCamera != null
                && previewCamera.clearFlags == CameraClearFlags.SolidColor
                && Mathf.Abs(previewCamera.backgroundColor.r - 0.45f) < 0.01f
                && Mathf.Abs(previewCamera.backgroundColor.g - 0.45f) < 0.01f
                && Mathf.Abs(previewCamera.backgroundColor.b - 0.45f) < 0.01f
                && RenderSettings.skybox == null;
            if (!flatGrayBackground)
                throw new InvalidOperationException("Expected a solid flat gray camera background with no skybox.");
            RenderPreview(pngPath);

            int mifuRendererCount = 0;
            int mifuClipCount = 0;
            string mifuPreviewClipName = "";
            string mifuPngPath = "";
            if (mifuRoot != null)
            {
                var mifuRenderers = mifuRoot.GetComponentsInChildren<SkinnedMeshRenderer>(true);
                mifuRendererCount = mifuRenderers.Length;
                var mifuAnimation = mifuRoot.GetComponent<Animation>();
                var mifuClips = new List<AnimationClip>();
                if (mifuAnimation != null)
                {
                    foreach (AnimationState state in mifuAnimation)
                        mifuClips.Add(state.clip);
                }
                mifuClipCount = mifuClips.Count;
                AnimationClip mifuPreviewClip = SelectPreviewClip(mifuClips, MifuPreviewClipPreference);

                bool previousRootActive = root.activeSelf;
                bool previousMifuActive = mifuRoot.activeSelf;
                root.SetActive(false);
                mifuRoot.SetActive(true);
                if (mifuPreviewClip != null)
                {
                    mifuPreviewClipName = mifuPreviewClip.name;
                    mifuPreviewClip.SampleAnimation(mifuRoot, Mathf.Min(mifuPreviewClip.length * 0.35f, mifuPreviewClip.length));
                }
                var camera = Camera.main ?? UnityEngine.Object.FindObjectOfType<Camera>();
                if (camera != null)
                    FrameCamera(camera, CombinedBounds(mifuRenderers));
                mifuPngPath = Path.Combine(outDir, "mifu_unity_recovery_preview.png");
                RenderPreview(mifuPngPath);
                root.SetActive(previousRootActive);
                mifuRoot.SetActive(previousMifuActive);
            }

            string reportPath = Path.Combine(outDir, "zhuangfy_unity_recovery_report.json");
            File.WriteAllText(
                reportPath,
                "{\n" +
                "  \"ok\": true,\n" +
                "  \"scene\": \"" + scene.path.Replace("\\", "\\\\") + "\",\n" +
                "  \"skinned_mesh_renderers\": " + renderers.Length + ",\n" +
                "  \"scene_skinned_mesh_renderers_total\": " + totalSceneRendererCount + ",\n" +
                "  \"scene_skinned_mesh_renderers_active\": " + activeSceneRendererCount + ",\n" +
                "  \"animation_clips\": " + clips.Count + ",\n" +
                "  \"clip_metadata\": " + clipMetadataCount + ",\n" +
                "  \"clip_categories\": " + clipCategories.Count + ",\n" +
                "  \"inspector_animation_component\": " + (animation != null ? "true" : "false") + ",\n" +
                "  \"runtime_clip_selection_ui\": " + (viewer != null ? "true" : "false") + ",\n" +
                "  \"recovered_states\": " + recoveredStateCount + ",\n" +
                "  \"flat_gray_background\": " + (flatGrayBackground ? "true" : "false") + ",\n" +
                "  \"preview_clip\": \"" + (previewClip != null ? previewClip.name : "").Replace("\\", "\\\\").Replace("\"", "\\\"") + "\",\n" +
                "  \"preview_clip_length\": " + (previewClip != null ? previewClip.length.ToString("F4", CultureInfo.InvariantCulture) : "0") + ",\n" +
                "  \"preview_clip_curve_bindings\": " + previewCurveCount + ",\n" +
                "  \"pose_correction_present\": " + (poseCorrection != null ? "true" : "false") + ",\n" +
                "  \"pose_correction_configured\": " + (poseCorrection != null && poseCorrection.HasConfiguredChains ? "true" : "false") + ",\n" +
                "  \"pose_correction_weight\": " + (poseCorrection != null ? poseCorrection.weight.ToString("F2", CultureInfo.InvariantCulture) : "0") + ",\n" +
                "  \"pose_correction_solved_arms\": " + (poseCorrection != null ? poseCorrection.LastSolvedArmCount : 0) + ",\n" +
                "  \"pose_correction_solved_legs\": " + (poseCorrection != null ? poseCorrection.LastSolvedLegCount : 0) + ",\n" +
                "  \"preview_png\": \"" + pngPath.Replace("\\", "\\\\") + "\",\n" +
                "  \"mifu_skinned_mesh_renderers\": " + mifuRendererCount + ",\n" +
                "  \"mifu_animation_clips\": " + mifuClipCount + ",\n" +
                "  \"mifu_preview_clip\": \"" + mifuPreviewClipName.Replace("\\", "\\\\").Replace("\"", "\\\"") + "\",\n" +
                "  \"mifu_preview_png\": \"" + mifuPngPath.Replace("\\", "\\\\") + "\",\n" +
                "  \"preview_resolution\": \"" + PreviewRenderWidth + "x" + PreviewRenderHeight + "\",\n" +
                "  \"before_bounds_size\": \"" + before.size.ToString("F4") + "\",\n" +
                "  \"after_bounds_size\": \"" + after.size.ToString("F4") + "\"\n" +
                "}\n",
                Encoding.UTF8);
            Debug.Log($"Manifest character recovery verification passed. Report: {reportPath}");
        }

        private static string ResolveManifestAssetPath(string primary, string legacy)
        {
            string primaryPath = Path.Combine(Directory.GetCurrentDirectory(), primary);
            if (File.Exists(primaryPath))
                return primary;
            return legacy;
        }

        private static bool AllCharacterManifestsExist(
            IEnumerable<ManifestCharacterSpec> characters)
        {
            if (characters == null)
                return false;
            foreach (ManifestCharacterSpec character in characters)
            {
                if (character == null ||
                    !File.Exists(Path.Combine(
                        Directory.GetCurrentDirectory(),
                        character.ManifestAssetPath)))
                {
                    return false;
                }
            }
            return true;
        }

        [MenuItem("Endfield/Character Recovery Lab/Refresh Manifest Character Presentation")]
        public static void RefreshPresentation()
        {
            EditorSceneManager.OpenScene(ManifestScenePath, OpenSceneMode.Single);
            var root = GameObject.Find("actor_zhuangfy_unity_recovery");
            if (root == null)
                throw new InvalidOperationException("Missing actor_zhuangfy_unity_recovery root in generated scene.");

            var animation = root.GetComponent<Animation>();
            if (animation == null)
                throw new InvalidOperationException("Generated root has no Animation component.");

            var clips = new List<AnimationClip>();
            foreach (AnimationState state in animation)
                clips.Add(state.clip);
            animation.clip = SelectPreviewClip(clips, ZhuangfyPreviewClipPreference);
            animation.playAutomatically = animation.clip != null;
            var camera = Camera.main ?? UnityEngine.Object.FindObjectOfType<Camera>();
            if (camera != null)
                FrameCamera(camera, CombinedBounds(root.GetComponentsInChildren<SkinnedMeshRenderer>(true)));

            EditorUtility.SetDirty(animation);
            if (camera != null)
                EditorUtility.SetDirty(camera);
            string zhuangfyGeneratedRoot = $"{GeneratedRoot}/Playable/Zhuangfy";
            EnsureActorFolders(zhuangfyGeneratedRoot, clearGeneratedAssets: false);
            PrefabUtility.SaveAsPrefabAsset(root, $"{zhuangfyGeneratedRoot}/Prefabs/actor_zhuangfy_unity_recovery.prefab");
            EditorSceneManager.SaveScene(SceneManager.GetActiveScene(), ManifestScenePath);
            Debug.Log($"Manifest character recovery presentation refreshed. Default clip: {(animation.clip != null ? animation.clip.name : "none")}");
        }

        private static void EnsureFolders()
        {
            foreach (string path in new[]
            {
                GeneratedRoot,
                $"{GeneratedRoot}/Scenes",
                $"{GeneratedRoot}/Shared",
                $"{GeneratedRoot}/Shared/Materials",
            })
            {
                Directory.CreateDirectory(path);
            }
            EnsureAssetFolder($"{GeneratedRoot}/Shared");
            EnsureAssetFolder($"{GeneratedRoot}/Shared/Materials");
        }

        private static void EnsureAssetFolder(string assetFolder)
        {
            assetFolder = assetFolder.Replace('\\', '/');
            if (AssetDatabase.IsValidFolder(assetFolder))
                return;

            string parent = Path.GetDirectoryName(assetFolder)?.Replace('\\', '/');
            string name = Path.GetFileName(assetFolder);
            if (string.IsNullOrEmpty(parent) || string.IsNullOrEmpty(name))
                return;
            if (!AssetDatabase.IsValidFolder(parent))
                EnsureAssetFolder(parent);
            if (!AssetDatabase.IsValidFolder(assetFolder))
                AssetDatabase.CreateFolder(parent, name);
        }

        private static void EnsureActorFolders(string actorGeneratedRoot, bool clearGeneratedAssets)
        {
            foreach (string path in new[]
            {
                actorGeneratedRoot,
                $"{actorGeneratedRoot}/Meshes",
                $"{actorGeneratedRoot}/Materials",
                $"{actorGeneratedRoot}/Textures",
                $"{actorGeneratedRoot}/Animations",
                $"{actorGeneratedRoot}/StaticProps",
                $"{actorGeneratedRoot}/Prefabs",
            })
            {
                Directory.CreateDirectory(path);
            }

            if (!clearGeneratedAssets)
                return;

            ClearGeneratedAssets($"{actorGeneratedRoot}/Meshes", ".asset");
            ClearGeneratedAssets($"{actorGeneratedRoot}/Materials", ".mat");
            ClearGeneratedAssets($"{actorGeneratedRoot}/Textures", ".png", ".jpg", ".jpeg", ".tga");
            ClearGeneratedAssets($"{actorGeneratedRoot}/Animations", ".anim");
            ClearGeneratedAssets($"{actorGeneratedRoot}/StaticProps", ".obj", ".fbx");
            ClearGeneratedAssets($"{actorGeneratedRoot}/Prefabs", ".prefab");
            DeleteGeneratedAssetFolder($"{actorGeneratedRoot}/SkinnedMeshes");
        }

        private static string ActorGeneratedRoot(string manifestAssetPath, string rootName)
        {
            string normalized = (manifestAssetPath ?? "").Replace('\\', '/');
            const string generatedPrefix = "Assets/EndfieldGraphShaderLab/Generated/";
            if (normalized.StartsWith(
                    generatedPrefix,
                    StringComparison.OrdinalIgnoreCase))
            {
                int separator = normalized.LastIndexOf('/');
                if (separator > generatedPrefix.Length)
                {
                    string generatedFolder = normalized.Substring(0, separator);
                    string relativeFolder = generatedFolder.Substring(
                        generatedPrefix.Length);
                    string safeFolder = SafeAssetFolderPath(relativeFolder);
                    if (safeFolder.Length > 0 &&
                        string.Equals(
                            safeFolder,
                            relativeFolder,
                            StringComparison.Ordinal))
                    {
                        return generatedPrefix.TrimEnd('/') + "/" + safeFolder;
                    }
                }
            }

            string marker = "/Generated/Characters/";
            int index = normalized.IndexOf(marker, StringComparison.OrdinalIgnoreCase);
            if (index >= 0)
            {
                string remainder = normalized.Substring(index + marker.Length);
                int separator = remainder.LastIndexOf('/');
                string relativeFolder = separator >= 0
                    ? remainder.Substring(0, separator)
                    : "";
                string safeFolder = SafeAssetFolderPath(relativeFolder);
                if (safeFolder.Length > 0)
                    return $"{GeneratedRoot}/{safeFolder}";
            }

            marker = "/Generated/";
            index = normalized.IndexOf(marker, StringComparison.OrdinalIgnoreCase);
            if (index >= 0)
            {
                string remainder = normalized.Substring(index + marker.Length);
                string actorFolder = remainder.Split('/')[0];
                if (actorFolder.Length > 0 && !actorFolder.Equals("Characters", StringComparison.OrdinalIgnoreCase))
                    return $"{GeneratedRoot}/{Safe(actorFolder)}";
            }

            if (rootName.IndexOf("mifu", StringComparison.OrdinalIgnoreCase) >= 0)
                return $"{GeneratedRoot}/Playable/Mifu";
            if (rootName.IndexOf("zhuangfy", StringComparison.OrdinalIgnoreCase) >= 0)
                return $"{GeneratedRoot}/Playable/Zhuangfy";
            return $"{GeneratedRoot}/Playable/{Safe(rootName)}";
        }

        private static string SafeAssetFolderPath(string value)
        {
            var safeSegments = new List<string>();
            foreach (string segment in (value ?? "").Replace('\\', '/').Split('/'))
            {
                string safe = Safe(segment);
                if (safe.Length > 0)
                    safeSegments.Add(safe);
            }
            return string.Join("/", safeSegments.ToArray());
        }

        private static void ClearGeneratedAssets(string folder, params string[] extensions)
        {
            if (!AssetDatabase.IsValidFolder(folder))
                return;
            var wanted = new HashSet<string>(extensions, StringComparer.OrdinalIgnoreCase);
            foreach (string guid in AssetDatabase.FindAssets("", new[] { folder }))
            {
                string assetPath = AssetDatabase.GUIDToAssetPath(guid);
                if (wanted.Contains(Path.GetExtension(assetPath)))
                    AssetDatabase.DeleteAsset(assetPath);
            }
        }

        private static void DeleteGeneratedAssetFolder(string folder)
        {
            if (AssetDatabase.IsValidFolder(folder))
                AssetDatabase.DeleteAsset(folder);
        }

        private static Dictionary<string, Transform> BuildSkeleton(Transform root, IList bones)
        {
            var sorted = new List<Dictionary<string, object>>();
            foreach (object obj in bones)
                sorted.Add(Dict(obj));
            sorted.Sort((a, b) => Str(a["path"]).Split('/').Length.CompareTo(Str(b["path"]).Split('/').Length));

            var byPath = new Dictionary<string, Transform>();
            foreach (var bone in sorted)
            {
                string path = Str(bone["path"]);
                if (path.Length == 0 || byPath.ContainsKey(path))
                    continue;

                string parentPath = ParentPath(path);
                Transform parent = parentPath.Length > 0 && byPath.TryGetValue(parentPath, out Transform parentTr)
                    ? parentTr
                    : root;

                var go = new GameObject(Path.GetFileName(path.Replace('\\', '/')));
                go.transform.SetParent(parent, false);
                object posObj = bone.TryGetValue("local_pos", out object localPosObj) ? localPosObj : (bone.TryGetValue("rest_pos", out object restPosObj) ? restPosObj : null);
                object rotObj = bone.TryGetValue("local_rot", out object localRotObj) ? localRotObj : (bone.TryGetValue("rest_rot", out object restRotObj) ? restRotObj : null);
                object scaleObj = bone.TryGetValue("local_scale", out object localScaleObj) ? localScaleObj : null;
                go.transform.localPosition = Vec3(List(posObj));
                go.transform.localRotation = Quat(List(rotObj));
                IList scaleList = List(scaleObj);
                go.transform.localScale = scaleList.Count >= 3 ? Vec3(scaleList) : Vector3.one;
                byPath[path] = go.transform;
            }
            return byPath;
        }

        private static Dictionary<string, Material> BuildMaterials(
            Dictionary<string, object> materials,
            string assetPrefix,
            string actorGeneratedRoot,
            bool rebuildMaterialAssets = true)
        {
            var cache = new Dictionary<string, Material>();
            foreach (var pair in materials)
            {
                var info = Dict(pair.Value);
                string assetPath = $"{actorGeneratedRoot}/Materials/{Safe(assetPrefix)}_{Safe(pair.Key)}.mat";
                var material = AssetDatabase.LoadAssetAtPath<Material>(assetPath);
                if (!rebuildMaterialAssets)
                {
                    if (material == null)
                        throw new FileNotFoundException(
                            $"Targeted refresh requires the cached material asset: {pair.Key}",
                            assetPath);
                    cache[pair.Key] = material;
                    continue;
                }
                Shader resolvedShader = ResolveShader(info);
                if (material == null)
                {
                    material = new Material(resolvedShader);
                    AssetDatabase.CreateAsset(material, assetPath);
                }
                else if (Bool(
                    info.TryGetValue(
                        "source_serialized_state",
                        out object sourceStateObject)
                        ? sourceStateObject
                        : null))
                {
                    // Exact source-state application must start from the
                    // mapped shader's clean defaults. Otherwise a prior run
                    // can retain a tag, keyword, or disabled pass that the
                    // newly recovered original Material no longer contains.
                    var clean = new Material(resolvedShader);
                    EditorUtility.CopySerialized(clean, material);
                    UnityEngine.Object.DestroyImmediate(clean);
                }
                material.shader = resolvedShader;
                material.name = Str(info["name"], pair.Key);
                ApplyMaterialProperties(material, info, actorGeneratedRoot);

                EditorUtility.SetDirty(material);
                cache[pair.Key] = material;
            }
            return cache;
        }

        private static Shader ResolveShader(Dictionary<string, object> info)
        {
            string shaderName = Str(info.TryGetValue("shader_name", out object shaderNameObj) ? shaderNameObj : null);
            string materialName = Str(info.TryGetValue("name", out object materialNameObj) ? materialNameObj : null);
            Shader shader;
            if (IsOverlayShadow(info))
                shader = Shader.Find("Endfield/Recovered/CharacterOverlayShadow");
            else if (shaderName.Contains("VFXTransparentDepthOnly"))
                shader = Shader.Find("Endfield/Recovered/VFXTransparentDepthOnly");
            else if (IsExactZhuangfyPiaodaiMaterial(info))
            {
                // The source renderer is admitted only by the exact three
                // material PathIDs and its exact VFXBaseV2 shader PathID.  If
                // the compatibility translation is absent, keep the renderer
                // fail-closed instead of falling through to the generic VFX
                // approximation that produced the former white/incorrect prop.
                shader = Shader.Find(ZhuangfyPiaodaiRecoveredShaderName);
                if (shader == null)
                {
                    shader = Shader.Find(
                        "Hidden/Endfield/Recovered/CharInfo/HGRPLitUnavailable");
                }
            }
            else if (
                shaderName == "HGRP/Effect/VFXRefract"
                && materialName == "M_fxui_lizhiyan_relax_sp_01_33"
                && Long(info.TryGetValue("path_id", out object refractPathIdObj) ? refractPathIdObj : null)
                    == 3646701341811672247L)
                shader = Shader.Find("Endfield/Recovered/VFXRefract");
            else if (shaderName.Contains("/Effect/") || shaderName.Contains("VFX"))
                shader = Shader.Find("Endfield/CharacterNPR/VFXGameLike");
            else if (shaderName.Contains("CharacterNPR_Skin"))
                shader = Shader.Find("Endfield/Recovered/CharacterSkin");
            else if (shaderName.Contains("CharacterNPR_Hair"))
                shader = Shader.Find("Endfield/Recovered/CharacterHair");
            else if (shaderName.Contains("CharacterNPR_Eye"))
                shader = Shader.Find("Endfield/Recovered/CharacterEye");
            else if (shaderName.Contains("CharacterNPR"))
                shader = Shader.Find("Endfield/Recovered/CharacterCloth");
            else if (shaderName.Length == 0 ||
                     (shaderName == "HGRP/Lit" && materialName == "DefaultHGMaterial"))
                shader = Shader.Find("Hidden/Endfield/Recovered/CharInfo/HGRPLitUnavailable");
            else
                shader = null;

            if (shader != null)
                return shader;
            if (Bool(
                    info.TryGetValue(
                        "fail_closed_unknown_shader",
                        out object failClosedObject)
                        ? failClosedObject
                        : null))
            {
                shader = Shader.Find(
                    "Hidden/Endfield/Recovered/CharInfo/HGRPLitUnavailable");
                if (shader == null)
                {
                    throw new InvalidOperationException(
                        $"The original shader '{shaderName}' on material " +
                        $"'{materialName}' has no recovered mapping, and the " +
                        "fail-closed diagnostic shader is unavailable.");
                }
                return shader;
            }
            shader = Shader.Find("Standard");
            return shader != null ? shader : Shader.Find("Diffuse");
        }

        private static void ApplyMaterialProperties(Material material, Dictionary<string, object> info, string actorGeneratedRoot)
        {
            if (info.TryGetValue("color", out object colorObj) && colorObj is IList colorList)
                SetColor(material, "_BaseColor", ColorRgba(colorList));
            else
                SetColor(material, "_BaseColor", Color.white);

            var colors = Dict(info.TryGetValue("colors", out object colorsObj) ? colorsObj : null);
            foreach (var colorPair in colors)
            {
                if (colorPair.Value is IList list)
                    SetColor(material, colorPair.Key, ColorRgba(list));
            }

            var floats = Dict(info.TryGetValue("floats", out object floatsObj) ? floatsObj : null);
            foreach (var floatPair in floats)
            {
                string recoveredProperty = RecoveredFloatProperty(floatPair.Key);
                if (!IsMaterialNumericProperty(material, recoveredProperty))
                    continue;
                material.SetFloat(recoveredProperty, Float(floatPair.Value));
            }

            var textures = Dict(info.TryGetValue("textures", out object texturesObj) ? texturesObj : null);
            foreach (var texturePair in textures)
            {
                var textureInfo = Dict(texturePair.Value);
                string sourcePath = Str(textureInfo.TryGetValue("file", out object fileObj) ? fileObj : null);
                if (sourcePath.Length == 0 || !File.Exists(sourcePath))
                    continue;

                Texture2D texture = ImportTexture(sourcePath, texturePair.Key, actorGeneratedRoot);
                if (texture == null)
                    continue;
                if (material.HasProperty(texturePair.Key))
                {
                    material.SetTexture(texturePair.Key, texture);
                    ApplyRecoveredTextureTransform(material, texturePair.Key, textureInfo);
                }
                string recoveredProperty = RecoveredTextureProperty(texturePair.Key);
                if (!string.Equals(recoveredProperty, texturePair.Key, StringComparison.Ordinal)
                    && material.HasProperty(recoveredProperty))
                {
                    material.SetTexture(recoveredProperty, texture);
                    ApplyRecoveredTextureTransform(material, recoveredProperty, textureInfo);
                }
                if (recoveredProperty == "_BaseMap")
                {
                    if (material.HasProperty("_BaseMap"))
                        material.SetTexture("_BaseMap", texture);
                    if (material.HasProperty("_MainTex"))
                        material.SetTexture("_MainTex", texture);
                    material.mainTexture = texture;
                }
            }

            SetFeatureFloat(material, "_UseBumpMap", RecoveredFeatureEnabled(
                floats, "_UseBumpMap", HasAnyTexture(
                    info, "_BumpMap", "_BumpMap1", "_NormalMap", "_NormalMap1", "_NormalTex", "_Normal", "_SplitNormalMap")));
            SetFeatureFloat(material, "_UseSpecBumpMap", RecoveredFeatureEnabled(
                floats, "_UseSpecBumpMap", HasTexture(info, "_SplitNormalMap")));
            SetFeatureFloat(material, "_UseMetallicGlossMap", RecoveredFeatureEnabled(
                floats, "_UseMetallicGlossMap", HasTexture(info, "_MetallicGlossMap") || HasTexture(info, "_MROMap") || HasTexture(info, "_MRAMap")));
            SetFeatureFloat(material, "_UseDiffRampMap", RecoveredFeatureEnabled(
                floats, "_UseDiffRampMap", HasTexture(info, "_DiffRampMap")));
            SetFeatureFloat(material, "_UseSpecRampMap", RecoveredFeatureEnabled(
                floats, "_UseSpecRampMap", HasTexture(info, "_SpecRampMap")));
            SetFeatureFloat(material, "_UseLineMap", RecoveredFeatureEnabled(
                floats, "_UseLineMap", HasTexture(info, "_LineMap")));
            SetFeatureFloat(material, "_UseShadowLutTex", RecoveredFeatureEnabled(
                floats, "_UseShadowLutTex", HasTexture(info, "_ShadowLutTex")));
            SetFeatureFloat(material, "_UseMatcap", RecoveredFeatureEnabled(
                floats, "_UseMatcap", HasTexture(info, "_MatcapTex")));
            SetFeatureFloat(material, "_UseEmotionMap", RecoveredFeatureEnabled(
                floats, "_UseEmotionMap", HasTexture(info, "_EmotionMap")));
            SetFeatureFloat(material, "_UseSDFLightmap", RecoveredFeatureEnabled(
                floats, "_UseSDFLightmap", HasTexture(info, "_SDFLightmap")));
            SetFeatureFloat(material, "_UseEmission", RecoveredFeatureEnabled(
                floats, "_UseEmission", HasAnyTexture(info, "_EmissionMap", "_EmissiveMap", "_EmissionTex", "_GlowMap")));
            SetFeatureFloat(material, "_UseCharacterFur", RecoveredFeatureEnabled(
                floats, "_UseCharacterFur", HasTexture(info, "_FurMap")));
            SetFeatureFloat(material, "_FaceHighlightMap", RecoveredFeatureEnabled(
                floats, "_FaceHighlightMap", HasTexture(info, "_HighlightMap")));
            SetFeatureFloat(material, "_UseMask", RecoveredFeatureEnabled(
                floats, "_UseMask", HasTexture(info, "_MaskTex")));
            SetFeatureFloat(material, "_UseBlend", RecoveredFeatureEnabled(
                floats, "_UseBlend", HasTexture(info, "_BlendTex")));
            SetFeatureFloat(material, "_UseDisturb", RecoveredFeatureEnabled(
                floats, "_UseDisturb", HasTexture(info, "_DisturbTex1")));
            SetFeatureFloat(material, "_UseFresnel", RecoveredFeatureEnabled(
                floats, "_UseFresnel", false));
            SetFeatureFloat(material, "_EnableNormalMap", RecoveredFeatureEnabled(
                floats, "_EnableNormalMap", HasAnyTexture(
                    info, "_NormalMap", "_NormalMap1", "_NormalTex", "_Normal")));

            SetKeyword(
                material,
                "DISABLE_DRAW_UNDER_HAIR",
                FloatProperty(material, "_DisableDrawUnderHair") > 0.5f);

            string shaderName = Str(info.TryGetValue("shader_name", out object shaderNameObj) ? shaderNameObj : null);
            string materialName = Str(info.TryGetValue("name", out object materialNameObj) ? materialNameObj : null).ToLowerInvariant();
            bool overlayShadow = IsOverlayShadow(info);
            bool isHair = !overlayShadow && (shaderName.Contains("Hair") || materialName.Contains("hair"));
            bool isEye = !overlayShadow && (shaderName.Contains("Eye") || materialName.Contains("iris") || materialName.Contains("brow"));
            bool isSkin = !overlayShadow && shaderName.Contains("Skin");
            bool isCloth = !overlayShadow && materialName.Contains("cloth");
            SetFeatureFloat(material, "_IsHair", isHair);
            SetFeatureFloat(material, "_IsEye", isEye);
            SetFeatureFloat(material, "_IsSkin", isSkin);
            SetFeatureFloat(material, "_IsCloth", isCloth);
            // Fail closed for every other Skin material. This hidden selector
            // opens the recovered normal-mapped body ForwardLit branch only
            // after exact original material, shader, feature, and texture PPtr
            // identity checks pass.
            bool exactBodySkinForwardVariant =
                isSkin && IsExactRecoveredSkinBodyForwardVariant(info, floats);
            SetFeatureFloat(
                material,
                "_RecoveredSkinBodyForwardVariant",
                exactBodySkinForwardVariant);
            BindExactRecoveredSkinBodyTexture(
                material,
                "_RecoveredBodyBaseMapPoint",
                "_BaseMap",
                exactBodySkinForwardVariant);
            BindExactRecoveredSkinBodyTexture(
                material,
                "_RecoveredBodyBumpMapPoint",
                "_BumpMap",
                exactBodySkinForwardVariant);
            BindExactRecoveredSkinBodyTexture(
                material,
                "_RecoveredBodyShadowLutPoint",
                "_ShadowLutTex",
                exactBodySkinForwardVariant);
            // The current installed Eye shader has exactly three playable
            // ForwardLit material classes. Resolve them through the pinned
            // 57-material contract so a future lookalike cannot silently enter
            // the source response. The original m_CustomRenderQueue and
            // disabled DepthOnly state do not survive the normal manifest JSON,
            // so restore those two raster controls from the same contract.
            Dictionary<string, object> exactEyeBrowContract = null;
            int exactEyeBrowForwardVariant = isEye
                ? ExactRecoveredEyeBrowForwardVariant(
                    info,
                    floats,
                    out exactEyeBrowContract)
                : 0;
            if (material.HasProperty("_RecoveredEyeForwardVariantClass"))
            {
                material.SetFloat(
                    "_RecoveredEyeForwardVariantClass",
                    exactEyeBrowForwardVariant);
            }
            if (exactEyeBrowForwardVariant > 0)
            {
                bool depthOnlyEnabled = Bool(
                    exactEyeBrowContract.TryGetValue(
                        "depth_only_enabled",
                        out object depthOnlyEnabledObj)
                        ? depthOnlyEnabledObj
                        : null);
                material.SetShaderPassEnabled(
                    "CAMERA_DEPTH_COPY",
                    depthOnlyEnabled);
            }
            // The selected Last Rite cloth-03 material is the only currently
            // recovered roster input that selects CharacterNPR's shipped
            // _SILK_STOCKINGS ForwardLit member. Keep the recovered dry
            // endpoint fail-closed to its exact material/shader/property/PPtr
            // identity; other stockings materials may use the still-open
            // advanced mask and live weather branches.
            bool exactLastRiteSilkStockingsVariant =
                IsExactRecoveredLastRiteSilkStockingsVariant(info, floats);
            SetFeatureFloat(
                material,
                "_RecoveredLastRiteSilkStockingsVariant",
                exactLastRiteSilkStockingsVariant);
            bool originalHgrpProfile = material.HasProperty("_OriginalHGRPProfile");
            if (originalHgrpProfile)
                material.SetFloat("_OriginalHGRPProfile", 1f);
            if (isHair && !originalHgrpProfile)
            {
                if (material.HasProperty("_BumpScale"))
                    material.SetFloat("_BumpScale", Mathf.Min(FloatProperty(material, "_BumpScale"), 0.45f));
                if (material.HasProperty("_SpecBumpScale"))
                    material.SetFloat("_SpecBumpScale", Mathf.Min(FloatProperty(material, "_SpecBumpScale"), 0.40f));
                if (material.HasProperty("_LineIntensity"))
                    material.SetFloat("_LineIntensity", Mathf.Min(FloatProperty(material, "_LineIntensity"), 0.35f));
                if (material.HasProperty("_LineSaturation"))
                    material.SetFloat("_LineSaturation", Mathf.Min(FloatProperty(material, "_LineSaturation"), 1.2f));
            }
            else if (!originalHgrpProfile && material.HasProperty("_BumpScale"))
            {
                material.SetFloat("_BumpScale", Mathf.Min(FloatProperty(material, "_BumpScale"), 0.22f));
            }
            if (isSkin && !originalHgrpProfile)
            {
                if (material.HasProperty("_BumpScale"))
                    material.SetFloat("_BumpScale", 0f);
                if (material.HasProperty("_UseBumpMap"))
                    material.SetFloat("_UseBumpMap", 0f);
                if (material.HasProperty("_EnableNormalMap"))
                    material.SetFloat("_EnableNormalMap", 0f);
                if (material.HasProperty("_UseSDFLightmap"))
                    material.SetFloat("_UseSDFLightmap", 0f);
                if (material.HasProperty("_UseEmotionMap"))
                    material.SetFloat("_UseEmotionMap", 0f);
                if (material.HasProperty("_Specular"))
                    material.SetFloat("_Specular", Mathf.Min(FloatProperty(material, "_Specular"), 0.4f));
            }
            // Original HGRP materials already carry authoritative serialized
            // response values. Preview clamps are valid only for legacy/fallback
            // materials whose source contract is incomplete.
            if (isCloth && !originalHgrpProfile)
                ApplyClothPreviewProfile(material);

            bool vfxMaterial = shaderName.Contains("VFX") || material.shader.name.Contains("VFX");
            if (originalHgrpProfile && !overlayShadow && !vfxMaterial)
            {
                bool hasExplicitOutline = floats.ContainsKey("_EnableOutline");
                bool enableOutline = hasExplicitOutline
                    ? Float(floats["_EnableOutline"]) > 0.5f
                    : HasTexture(info, "_OutlineMask") || Float(floats.TryGetValue("_OutlineWidth", out object outlineWidthObj) ? outlineWidthObj : null) > 0f;
                if (material.HasProperty("_EnableOutline"))
                    material.SetFloat("_EnableOutline", enableOutline ? 1f : 0f);
                if (enableOutline && material.HasProperty("_OutlineWidth") && FloatProperty(material, "_OutlineWidth") <= 0.001f)
                    material.SetFloat("_OutlineWidth", 0.5f);
            }
            else
            {
                if (material.HasProperty("_EnableOutline"))
                    material.SetFloat("_EnableOutline", 0f);
                if (material.HasProperty("_OutlineWidth"))
                    material.SetFloat("_OutlineWidth", 0f);
            }
            if (IsOverlayShadow(info))
            {
                if (material.HasProperty("_ShadowStrength"))
                    material.SetFloat("_ShadowStrength", OverlayShadowStrength(materialName));
                if (material.HasProperty("_ShadowColor"))
                    material.SetColor("_ShadowColor", OverlayShadowColor(materialName));
            }

            bool defaultCharacterShader = IsDefaultCharacterShader(material.shader);
            if (!defaultCharacterShader)
            {
                SetKeyword(material, "_NORMALMAP", FloatProperty(material, "_UseBumpMap") > 0.5f || FloatProperty(material, "_EnableNormalMap") > 0.5f);
                SetKeyword(material, "_SPECULAR_NORMALMAP", FloatProperty(material, "_UseSpecBumpMap") > 0.5f);
                SetKeyword(material, "_METALLICSPECGLOSSMAP", FloatProperty(material, "_UseMetallicGlossMap") > 0.5f);
                SetKeyword(material, "_DIFF_RAMP_ON", FloatProperty(material, "_UseDiffRampMap") > 0.5f);
                SetKeyword(material, "_SPEC_RAMP_ON", FloatProperty(material, "_UseSpecRampMap") > 0.5f);
                SetKeyword(
                    material,
                    "_SPECULAR_LINE",
                    FloatProperty(material, "_IsHair") > 0.5f &&
                    (FloatProperty(material, "_SpecularLine") > 0.5f ||
                     FloatProperty(material, "_UseLineMap") > 0.5f));
                SetKeyword(material, "_SHADOW_LUT_TEX", FloatProperty(material, "_UseShadowLutTex") > 0.5f);
                SetKeyword(material, "_MATCAP_ON", FloatProperty(material, "_UseMatcap") > 0.5f);
                SetKeyword(material, "_EMOTION_MAP", FloatProperty(material, "_UseEmotionMap") > 0.5f);
                SetKeyword(material, "_HIGHLIGHT_MAP", FloatProperty(material, "_FaceHighlightMap") > 0.5f);
                SetKeyword(material, "_SDFLIGHTMAP", FloatProperty(material, "_UseSDFLightmap") > 0.5f);
                SetKeyword(material, "_EMISSION", FloatProperty(material, "_UseEmission") > 0.5f);
                SetKeyword(material, "_CHARACTER_FUR", FloatProperty(material, "_UseCharacterFur") > 0.5f);
                SetKeyword(material, "_CLEARCOAT", FloatProperty(material, "_ClearCoat") > 0.5f);
                SetKeyword(material, "_PARALLAX_MAP", FloatProperty(material, "_UseParallax") > 0.5f);
                SetKeyword(material, "_SILK_STOCKINGS", FloatProperty(material, "_SilkStockings") > 0.5f);
                SetKeyword(
                    material,
                    "_OUTLINE_MASK",
                    FloatProperty(material, "_EnableOutlineMask") > 0.5f ||
                    FloatProperty(material, "_UseOutlineMask") > 0.5f);
                SetKeyword(material, "_DRAW_UNDER_BROW", FloatProperty(material, "_DrawUnderBrow") > 0.5f);
                SetKeyword(material, "_EYE_HIGHLIGHT", FloatProperty(material, "_EyeHighLight") > 0.5f);
            }

            ConfigureMaterialSurface(material, info, floats);
            // ConfigureMaterialSurface applies the general opaque/transparent
            // queue policy. Restore the original Eye-family override after it,
            // including explicit Geometry (2000), because Unity distinguishes
            // that serialized override from the shader-default sentinel (-1).
            if (exactEyeBrowForwardVariant > 0)
            {
                material.renderQueue = Int(
                    exactEyeBrowContract.TryGetValue(
                        "custom_render_queue",
                        out object customRenderQueueObj)
                        ? customRenderQueueObj
                        : null,
                    material.renderQueue);
            }
            ApplyExactZhuangfyPiaodaiMaterialContract(material, info, floats);
            if (defaultCharacterShader)
                ConfigureStandardShaderKeywords(material);
            ApplySourceSerializedMaterialState(material, info);
        }

        private static void ApplySourceSerializedMaterialState(
            Material material,
            Dictionary<string, object> info)
        {
            if (material == null || !Bool(
                    info.TryGetValue(
                        "source_serialized_state",
                        out object sourceStateObject)
                        ? sourceStateObject
                        : null))
            {
                return;
            }

            material.renderQueue = Int(
                info.TryGetValue("custom_render_queue", out object queueObject)
                    ? queueObject
                    : null,
                -1);
            material.enableInstancing = Bool(
                info.TryGetValue(
                    "enable_instancing_variants",
                    out object instancingObject)
                    ? instancingObject
                    : null);
            material.globalIlluminationFlags = (MaterialGlobalIlluminationFlags)Int(
                info.TryGetValue("lightmap_flags", out object lightmapObject)
                    ? lightmapObject
                    : null);

            var serialized = new SerializedObject(material);
            SetSerializedStringArray(
                serialized,
                "m_ValidKeywords",
                List(info.TryGetValue("valid_keywords", out object validObject)
                    ? validObject
                    : null));
            SetSerializedStringArray(
                serialized,
                "m_InvalidKeywords",
                List(info.TryGetValue("invalid_keywords", out object invalidObject)
                    ? invalidObject
                    : null));
            serialized.ApplyModifiedPropertiesWithoutUndo();
            foreach (var tag in Dict(info.TryGetValue(
                "string_tag_map",
                out object tagsObject)
                ? tagsObject
                : null))
            {
                material.SetOverrideTag(tag.Key, Str(tag.Value));
            }
            foreach (object passObject in List(info.TryGetValue(
                "disabled_shader_passes",
                out object disabledObject)
                ? disabledObject
                : null))
            {
                string passName = Str(passObject);
                if (passName.Length > 0)
                    material.SetShaderPassEnabled(passName, false);
            }

            // Applying SerializedObject state can cause Unity to refresh its
            // public Material caches. Reassert these three source scalars last.
            material.renderQueue = Int(
                info.TryGetValue("custom_render_queue", out queueObject)
                    ? queueObject
                    : null,
                -1);
            material.enableInstancing = Bool(
                info.TryGetValue(
                    "enable_instancing_variants",
                    out instancingObject)
                    ? instancingObject
                    : null);
            material.globalIlluminationFlags = (MaterialGlobalIlluminationFlags)Int(
                info.TryGetValue("lightmap_flags", out lightmapObject)
                    ? lightmapObject
                    : null);
        }

        private static void SetSerializedStringArray(
            SerializedObject serialized,
            string propertyName,
            IList values)
        {
            SerializedProperty property = serialized.FindProperty(propertyName);
            if (property == null || !property.isArray)
                throw new InvalidDataException(
                    $"Unity Material no longer exposes serialized {propertyName}.");
            property.arraySize = values.Count;
            for (int index = 0; index < values.Count; index++)
                property.GetArrayElementAtIndex(index).stringValue = Str(values[index]);
        }

        private static bool IsExactZhuangfyPiaodaiMaterial(
            Dictionary<string, object> info)
        {
            if (!string.Equals(
                    Str(info.TryGetValue("shader_name", out object shaderNameObj)
                        ? shaderNameObj
                        : null),
                    "HGRP/Effect/VFXBaseV2",
                    StringComparison.Ordinal) ||
                Long(info.TryGetValue("shader_path_id", out object shaderPathIdObj)
                    ? shaderPathIdObj
                    : null) != ZhuangfyPiaodaiVfxShaderPathId)
            {
                return false;
            }

            long pathId = Long(
                info.TryGetValue("path_id", out object materialPathIdObj)
                    ? materialPathIdObj
                    : null);
            string name = Str(
                info.TryGetValue("name", out object materialNameObj)
                    ? materialNameObj
                    : null);
            return
                (pathId == ZhuangfyPiaodaiMaterial01PathId &&
                 string.Equals(name, "M_fx_ui_zhangfy_piaodai_01", StringComparison.Ordinal)) ||
                (pathId == ZhuangfyPiaodaiMaterial02PathId &&
                 string.Equals(name, "M_fx_ui_zhangfy_piaodai_02", StringComparison.Ordinal)) ||
                (pathId == ZhuangfyPiaodaiMaterial03PathId &&
                 string.Equals(name, "M_fx_ui_zhangfy_piaodai_03", StringComparison.Ordinal));
        }

        private static void ApplyExactZhuangfyPiaodaiMaterialContract(
            Material material,
            Dictionary<string, object> info,
            Dictionary<string, object> floats)
        {
            if (material == null || !IsExactZhuangfyPiaodaiMaterial(info))
                return;

            // ConfigureMaterialSurface deliberately normalizes uncertain VFX
            // inputs.  These three source rows are no longer uncertain: the
            // exporter preserves their queue, tags, disabled passes, keyword
            // set and serialized blend/depth state, so restore those values
            // after the general compatibility policy has run.
            foreach (string property in new[]
            {
                "_SrcBlend",
                "_DstBlend",
                "_AlphaSrcBlend",
                "_AlphaDstBlend",
                "_MVSrcColorBlend",
                "_MVDstColorBlend",
                "_ZWrite",
                "_ZTest",
                "_CullMode",
            })
            {
                if (floats.TryGetValue(property, out object valueObj) &&
                    material.HasProperty(property))
                {
                    material.SetFloat(property, Float(valueObj));
                }
            }

            int queue = Int(
                info.TryGetValue("custom_render_queue", out object queueObj)
                    ? queueObj
                    : null,
                -1);
            if (queue != 3700)
                throw new InvalidOperationException(
                    $"Exact Zhuangfy piaodai material has unexpected render queue {queue}.");
            material.renderQueue = queue;

            var tags = Dict(
                info.TryGetValue("string_tag_map", out object tagsObj)
                    ? tagsObj
                    : null);
            if (tags.Count != 1 ||
                !tags.TryGetValue("RenderType", out object renderTypeObj) ||
                !string.Equals(Str(renderTypeObj), "Transparent", StringComparison.Ordinal))
            {
                throw new InvalidOperationException(
                    "Exact Zhuangfy piaodai material tag map changed.");
            }
            material.SetOverrideTag("RenderType", "Transparent");

            string[] expectedDisabledPasses =
            {
                "ForwardReflection",
                "DepthOnly",
                "GBuffer",
            };
            IList disabledPasses = List(
                info.TryGetValue("disabled_shader_passes", out object disabledObj)
                    ? disabledObj
                    : null);
            if (disabledPasses.Count != expectedDisabledPasses.Length)
                throw new InvalidOperationException(
                    "Exact Zhuangfy piaodai disabled-pass count changed.");
            for (int index = 0; index < expectedDisabledPasses.Length; index++)
            {
                string passName = Str(disabledPasses[index]);
                if (!string.Equals(
                        passName,
                        expectedDisabledPasses[index],
                        StringComparison.Ordinal))
                {
                    throw new InvalidOperationException(
                        "Exact Zhuangfy piaodai disabled-pass order changed.");
                }
                material.SetShaderPassEnabled(passName, false);
            }

            var validKeywords = new List<string>();
            foreach (object keywordObj in List(
                info.TryGetValue("valid_keywords", out object validKeywordsObj)
                    ? validKeywordsObj
                    : null))
            {
                string keyword = Str(keywordObj);
                if (keyword.Length > 0)
                    validKeywords.Add(keyword);
            }
            if (validKeywords.Count != 3 && validKeywords.Count != 4)
                throw new InvalidOperationException(
                    "Exact Zhuangfy piaodai sample-texture keyword count changed.");
            for (int index = 0; index < validKeywords.Count; index++)
            {
                if (!string.Equals(
                        validKeywords[index],
                        "_SAMPLE_TEX" + index.ToString(CultureInfo.InvariantCulture),
                        StringComparison.Ordinal))
                {
                    throw new InvalidOperationException(
                        "Exact Zhuangfy piaodai keyword sequence changed.");
                }
            }
            material.shaderKeywords = validKeywords.ToArray();
            material.enableInstancing = Bool(
                info.TryGetValue("enable_instancing_variants", out object instancingObj)
                    ? instancingObj
                    : null);
            if (material.HasProperty("_RecoveredLODFade"))
            {
                material.SetVector(
                    "_RecoveredLODFade",
                    EndfieldRecoveredLodFadePacking.Disabled);
            }
            material.globalIlluminationFlags = (MaterialGlobalIlluminationFlags)Int(
                info.TryGetValue("lightmap_flags", out object lightmapObj)
                    ? lightmapObj
                    : null);
        }

        private static string RecoveredFloatProperty(string sourceProperty)
        {
            // CharacterNPR serializes _ClearCoatMask in both m_TexEnvs and
            // m_Floats. The recovered shader keeps the texture at the shipped
            // name and exposes the source scalar as the unambiguous Value
            // alias, so neither half of the original property sheet is lost.
            return string.Equals(sourceProperty, "_ClearCoatMask", StringComparison.Ordinal)
                ? "_ClearCoatMaskValue"
                : sourceProperty;
        }

        private static bool IsMaterialNumericProperty(Material material, string propertyName)
        {
            if (material == null || material.shader == null || !material.HasProperty(propertyName))
                return false;
            int count = ShaderUtil.GetPropertyCount(material.shader);
            for (int index = 0; index < count; index++)
            {
                if (!string.Equals(
                        ShaderUtil.GetPropertyName(material.shader, index),
                        propertyName,
                        StringComparison.Ordinal))
                {
                    continue;
                }
                ShaderUtil.ShaderPropertyType propertyType =
                    ShaderUtil.GetPropertyType(material.shader, index);
                return propertyType == ShaderUtil.ShaderPropertyType.Float ||
                    propertyType == ShaderUtil.ShaderPropertyType.Range;
            }
            return false;
        }

        private static void ApplyRecoveredTextureTransform(
            Material material,
            string propertyName,
            Dictionary<string, object> textureInfo)
        {
            IList scale = List(
                textureInfo.TryGetValue("scale", out object scaleObj)
                    ? scaleObj
                    : null);
            IList offset = List(
                textureInfo.TryGetValue("offset", out object offsetObj)
                    ? offsetObj
                    : null);
            if (scale.Count >= 2)
                material.SetTextureScale(
                    propertyName,
                    new Vector2(Float(scale[0]), Float(scale[1])));
            if (offset.Count >= 2)
                material.SetTextureOffset(
                    propertyName,
                    new Vector2(Float(offset[0]), Float(offset[1])));
        }

        private static bool HasTexture(Dictionary<string, object> info, string textureName)
        {
            var textures = Dict(info.TryGetValue("textures", out object texturesObj) ? texturesObj : null);
            if (!textures.TryGetValue(textureName, out object textureObj))
                return false;
            return Str(Dict(textureObj).TryGetValue("file", out object fileObj) ? fileObj : null).Length > 0;
        }

        private static bool HasAnyTexture(Dictionary<string, object> info, params string[] textureNames)
        {
            foreach (string textureName in textureNames)
            {
                if (HasTexture(info, textureName))
                    return true;
            }
            return false;
        }

        private static string RecoveredTextureProperty(string sourceProperty)
        {
            switch (sourceProperty)
            {
                case "_MainTex":
                case "_BaseMap":
                case "_BaseColorMap":
                case "_BaseColorTex":
                case "_Albedo":
                case "_AlbedoMap":
                case "_DiffuseMap":
                case "_Diffuse":
                case "_DiffuseTex":
                case "_ColorTex":
                    return "_BaseMap";
                case "_BumpMap1":
                case "_NormalMap":
                case "_NormalMap1":
                case "_NormalTex":
                case "_Normal":
                    return "_BumpMap";
                case "_EmissiveMap":
                case "_EmissionTex":
                case "_GlowMap":
                    return "_EmissionMap";
                default:
                    return sourceProperty;
            }
        }

        private static int ExactRecoveredEyeBrowForwardVariant(
            Dictionary<string, object> info,
            Dictionary<string, object> floats,
            out Dictionary<string, object> contract)
        {
            contract = null;
            if (!string.Equals(
                    Str(info.TryGetValue("shader_name", out object shaderNameObj)
                        ? shaderNameObj
                        : null),
                    "HGRP/CharacterNPR_Eye",
                    StringComparison.Ordinal) ||
                Long(info.TryGetValue("shader_path_id", out object shaderPathIdObj)
                    ? shaderPathIdObj
                    : null) != CharacterNprEyeShaderPathId)
            {
                return 0;
            }

            long materialPathId = Long(
                info.TryGetValue("path_id", out object materialPathIdObj)
                    ? materialPathIdObj
                    : null);
            Dictionary<long, Dictionary<string, object>> contracts =
                LoadEyeBrowForwardContracts();
            if (!contracts.TryGetValue(materialPathId, out contract))
                return 0;
            if (!string.Equals(
                    Str(info.TryGetValue("name", out object materialNameObj)
                        ? materialNameObj
                        : null),
                    Str(contract.TryGetValue("name", out object contractNameObj)
                        ? contractNameObj
                        : null),
                    StringComparison.Ordinal) ||
                Long(contract.TryGetValue("shader_path_id", out object contractShaderObj)
                    ? contractShaderObj
                    : null) != CharacterNprEyeShaderPathId)
            {
                contract = null;
                return 0;
            }

            int variantClass = Int(
                contract.TryGetValue("variant_class", out object variantClassObj)
                    ? variantClassObj
                    : null);
            if (variantClass < 1 || variantClass > 3)
            {
                contract = null;
                return 0;
            }

            var requiredFloats = Dict(
                contract.TryGetValue("required_float_state", out object requiredFloatsObj)
                    ? requiredFloatsObj
                    : null);
            foreach (var pair in requiredFloats)
            {
                if (!HasExactRecoveredFloat(floats, pair.Key, Float(pair.Value)))
                {
                    contract = null;
                    return 0;
                }
            }

            var textures = Dict(
                info.TryGetValue("textures", out object texturesObj)
                    ? texturesObj
                    : null);
            var requiredTextures = Dict(
                contract.TryGetValue("textures", out object requiredTexturesObj)
                    ? requiredTexturesObj
                    : null);
            if (textures.Count != requiredTextures.Count)
            {
                contract = null;
                return 0;
            }
            foreach (var pair in requiredTextures)
            {
                var expectedTexture = Dict(pair.Value);
                if (!HasExactRecoveredTexture(
                        textures,
                        pair.Key,
                        Str(expectedTexture.TryGetValue("name", out object textureNameObj)
                            ? textureNameObj
                            : null),
                        Long(expectedTexture.TryGetValue("path_id", out object texturePathIdObj)
                            ? texturePathIdObj
                            : null)))
                {
                    contract = null;
                    return 0;
                }
            }
            return variantClass;
        }

        private static Dictionary<long, Dictionary<string, object>>
            LoadEyeBrowForwardContracts()
        {
            if (EyeBrowForwardContracts != null)
                return EyeBrowForwardContracts;

            EyeBrowForwardContracts =
                new Dictionary<long, Dictionary<string, object>>();
            string contractPath = Path.GetFullPath(EyeBrowForwardContractAssetPath);
            if (!File.Exists(contractPath))
                return EyeBrowForwardContracts;

            var root = Dict(ManifestMiniJson.Deserialize(
                File.ReadAllText(contractPath, Encoding.UTF8)));
            var materials = Dict(
                root.TryGetValue("materials", out object materialsObj)
                    ? materialsObj
                    : null);
            foreach (object value in materials.Values)
            {
                var material = Dict(value);
                long pathId = Long(
                    material.TryGetValue("path_id", out object pathIdObj)
                        ? pathIdObj
                        : null);
                if (pathId != 0L)
                    EyeBrowForwardContracts[pathId] = material;
            }
            return EyeBrowForwardContracts;
        }

        private static bool IsExactRecoveredSkinBodyForwardVariant(
            Dictionary<string, object> info,
            Dictionary<string, object> floats)
        {
            if (!string.Equals(
                    Str(info.TryGetValue("shader_name", out object shaderNameObj)
                        ? shaderNameObj
                        : null),
                    "HGRP/CharacterNPR_Skin",
                    StringComparison.Ordinal) ||
                Long(info.TryGetValue("shader_path_id", out object shaderPathIdObj)
                    ? shaderPathIdObj
                    : null) != CharacterNprSkinShaderPathId)
            {
                return false;
            }

            long materialPathId = Long(
                info.TryGetValue("path_id", out object materialPathIdObj)
                    ? materialPathIdObj
                    : null);
            string materialName = Str(
                info.TryGetValue("name", out object materialNameObj)
                    ? materialNameObj
                    : null);
            bool wulfaBody =
                materialPathId == WulfaBodySkinMaterialPathId &&
                string.Equals(
                    materialName,
                    "M_actor_wulfa_body_01",
                    StringComparison.Ordinal);
            bool zhuangfyBody =
                materialPathId == ZhuangfyBodySkinMaterialPathId &&
                string.Equals(
                    materialName,
                    "M_actor_zhuangfy_body_01",
                    StringComparison.Ordinal);
            bool endminfBody =
                materialPathId == EndminfBodySkinMaterialPathId &&
                string.Equals(
                    materialName,
                    "M_actor_endminf_body_01",
                    StringComparison.Ordinal);
            if (!wulfaBody && !zhuangfyBody && !endminfBody)
                return false;

            string[] zeroFeatures =
            {
                "_UseSDFLightmap",
                "_UseSpecRampMap",
                "_Metallic",
                "_SurfaceType",
                "_EnableAlphaTest",
                "_AlphaPremultiply",
                "_DisableRainEffectOnMaterial",
                "_RainEffectIntensity",
                "_WetEffectIntensity",
                "_UseEmission",
                "_FaceHighlightMap",
                "_UseEmotionMap",
            };
            foreach (string feature in zeroFeatures)
            {
                // These legacy controls are absent, rather than serialized as
                // zero, on the pinned Endminf material. Its authoritative
                // disable state is _DisableRainEffectOnMaterial=0 plus the
                // absence of both properties; do not invent float rows.
                if (endminfBody &&
                    (feature == "_RainEffectIntensity" ||
                     feature == "_WetEffectIntensity"))
                {
                    if (floats.ContainsKey(feature))
                        return false;
                    continue;
                }
                if (!HasExactRecoveredFloat(floats, feature, 0f))
                    return false;
            }

            string[] oneFeatures =
            {
                "_UseBumpMap",
                "_UseDiffRampMap",
                "_UseShadowLutTex",
            };
            foreach (string feature in oneFeatures)
            {
                if (!HasExactRecoveredFloat(floats, feature, 1f))
                    return false;
            }
            if (!HasExactRecoveredFloat(
                    floats,
                    "_BumpScale",
                    endminfBody ? 0.6f : 1f))
            {
                return false;
            }

            var textures = Dict(
                info.TryGetValue("textures", out object texturesObj)
                    ? texturesObj
                    : null);
            if (textures.Count != 4)
            {
                return false;
            }

            if (endminfBody)
            {
                return HasExactRecoveredTexture(
                        textures,
                        "_BaseMap",
                        "T_actor_endminf_body_01_D",
                        6666606937086026583L) &&
                    HasExactRecoveredTexture(
                        textures,
                        "_BumpMap",
                        "T_actor_endminf_body_01_N",
                        -7567685407150974306L) &&
                    HasExactRecoveredTexture(
                        textures,
                        "_DiffRampMap",
                        "T_actor_common_face_01_RD",
                        5848563174712869001L) &&
                    HasExactRecoveredTexture(
                        textures,
                        "_ShadowLutTex",
                        "T_actor_common_femaleskincolor02_lut_D",
                        7838960105793206527L);
            }

            if (!HasExactRecoveredTexture(
                    textures,
                    "_DiffRampMap",
                    "T_actor_common_body_01_RD",
                    9015086203897338725L) ||
                !HasExactRecoveredTexture(
                    textures,
                    "_ShadowLutTex",
                    "T_actor_common_femaleskincolor01_lut_D",
                    4951544993205285082L))
            {
                return false;
            }

            return wulfaBody
                ? HasExactRecoveredTexture(
                    textures,
                    "_BaseMap",
                    "T_actor_wulfa_body_01_D",
                    -3226161897161806025L) &&
                  HasExactRecoveredTexture(
                    textures,
                    "_BumpMap",
                    "T_actor_wulfa_body_01_N",
                    1814302978370399985L)
                : HasExactRecoveredTexture(
                    textures,
                    "_BaseMap",
                    "T_actor_zhuangfy_body_01_D",
                    8655472724994348568L) &&
                  HasExactRecoveredTexture(
                    textures,
                    "_BumpMap",
                    "T_actor_zhuangfy_body_01_N",
                    1391104552726659474L);
        }

        private static bool IsExactRecoveredLastRiteSilkStockingsVariant(
            Dictionary<string, object> info,
            Dictionary<string, object> floats)
        {
            if (!string.Equals(
                    Str(info.TryGetValue("shader_name", out object shaderNameObj)
                        ? shaderNameObj
                        : null),
                    "HGRP/CharacterNPR",
                    StringComparison.Ordinal) ||
                Long(info.TryGetValue("shader_path_id", out object shaderPathIdObj)
                    ? shaderPathIdObj
                    : null) != CharacterNprClothShaderPathId ||
                Long(info.TryGetValue("path_id", out object materialPathIdObj)
                    ? materialPathIdObj
                    : null) != LastRiteSilkStockingsMaterialPathId ||
                !string.Equals(
                    Str(info.TryGetValue("name", out object materialNameObj)
                        ? materialNameObj
                        : null),
                    "M_actor_lastrite_cloth_03",
                    StringComparison.Ordinal))
            {
                return false;
            }

            var exactFloats = new Dictionary<string, float>(StringComparer.Ordinal)
            {
                { "_SilkStockings", 1f },
                { "_SilkStockingsAdvance", 0f },
                { "_SilkStockingsMinAffect", 0f },
                { "_SilkStockingsMaxAffect", 0.9f },
                { "_SilkStockingsAnisoDirection", 0.39f },
                { "_SilkStockingsSpecularInt", 0.1756f },
                { "_SilkStockingsSpecularMinAtMinWetness", 1f },
                { "_SilkStockingsSpecularFalloff", 0f },
                { "_SilkStockingsSpecularValue", 0.22f },
                { "_SilkStockingsRainWetMaskScale", 0f },
                { "_SilkStockingsAlbedoAffectType", 0.5f },
            };
            foreach (var pair in exactFloats)
            {
                if (!HasExactRecoveredFloat(floats, pair.Key, pair.Value))
                    return false;
            }

            var textures = Dict(
                info.TryGetValue("textures", out object texturesObj)
                    ? texturesObj
                    : null);
            return textures.Count == 6 &&
                HasExactRecoveredTexture(
                    textures,
                    "_BaseMap",
                    "T_actor_lastrite_body_01_D",
                    -871710608211496919L) &&
                HasExactRecoveredTexture(
                    textures,
                    "_BumpMap",
                    "T_actor_lastrite_body_01_N",
                    6235327319893235715L) &&
                HasExactRecoveredTexture(
                    textures,
                    "_DiffRampMap",
                    "T_actor_lastrite_cloth_03_RD",
                    -5531378566050313161L) &&
                HasExactRecoveredTexture(
                    textures,
                    "_EmissionMap",
                    "T_actor_pelica_cloth_01_E",
                    -4001512737168125190L) &&
                HasExactRecoveredTexture(
                    textures,
                    "_MetallicGlossMap",
                    "T_actor_lastrite_body_01_P",
                    7971436378273533595L) &&
                HasExactRecoveredTexture(
                    textures,
                    "_SpecRampMap",
                    "T_actor_common_cloth_04_RS",
                    4523718382697154697L);
        }

        private static bool HasExactRecoveredFloat(
            Dictionary<string, object> floats,
            string propertyName,
            float expected)
        {
            return floats.TryGetValue(propertyName, out object value) &&
                Mathf.Abs(Float(value) - expected) <= 1e-6f;
        }

        private static bool HasExactRecoveredTexture(
            Dictionary<string, object> textures,
            string propertyName,
            string expectedName,
            long expectedPathId)
        {
            if (!textures.TryGetValue(propertyName, out object textureObj))
                return false;
            Dictionary<string, object> texture = Dict(textureObj);
            return string.Equals(
                    Str(texture.TryGetValue("name", out object nameObj)
                        ? nameObj
                        : null),
                    expectedName,
                    StringComparison.Ordinal) &&
                Long(texture.TryGetValue("path_id", out object pathIdObj)
                    ? pathIdObj
                    : null) == expectedPathId &&
                File.Exists(Str(
                    texture.TryGetValue("file", out object fileObj)
                        ? fileObj
                        : null));
        }

        private static void BindExactRecoveredSkinBodyTexture(
            Material material,
            string targetProperty,
            string sourceProperty,
            bool enabled)
        {
            if (!material.HasProperty(targetProperty))
                return;
            Texture source = enabled && material.HasProperty(sourceProperty)
                ? material.GetTexture(sourceProperty)
                : null;
            // Hidden aliases are black by default and are cleared for every
            // non-target Skin material. Inline samplers on the exact body path
            // make filtering independent of shared texture import settings.
            material.SetTexture(targetProperty, source);
        }

        private static void SetColor(Material material, string propertyName, Color color)
        {
            if (material.HasProperty(propertyName))
                material.SetColor(propertyName, color);
            if (propertyName == "_BaseColor")
            {
                if (material.HasProperty("_Color"))
                    material.SetColor("_Color", color);
                material.color = color;
            }
        }

        private static void SetFeatureFloat(Material material, string propertyName, bool value)
        {
            if (material.HasProperty(propertyName))
                material.SetFloat(propertyName, value ? 1f : 0f);
        }

        private static bool RecoveredFeatureEnabled(
            Dictionary<string, object> serializedFloats,
            string propertyName,
            bool inferredFallback)
        {
            // A texture PPtr can remain serialized while its shader branch is
            // deliberately disabled. Preserve the material's authoritative
            // float whenever it exists and infer from texture presence only for
            // incomplete/legacy manifests that omit that property.
            if (serializedFloats != null &&
                serializedFloats.TryGetValue(propertyName, out object value))
            {
                return Float(value) > 0.5f;
            }
            return inferredFallback;
        }

        private static float FloatProperty(Material material, string propertyName)
        {
            return material.HasProperty(propertyName) ? material.GetFloat(propertyName) : 0f;
        }

        private static void SetKeyword(Material material, string keyword, bool enabled)
        {
            if (enabled)
                material.EnableKeyword(keyword);
            else
                material.DisableKeyword(keyword);
        }

        private static bool IsDefaultCharacterShader(Shader shader)
        {
            return shader != null && shader.name == "Standard";
        }

        private static void ConfigureStandardShaderKeywords(Material material)
        {
            material.shaderKeywords = Array.Empty<string>();
            bool transparent = material.HasProperty("_Mode") && FloatProperty(material, "_Mode") > 0.5f;
            SetKeyword(material, "_ALPHATEST_ON", false);
            SetKeyword(material, "_ALPHABLEND_ON", transparent);
            SetKeyword(material, "_ALPHAPREMULTIPLY_ON", false);
            SetKeyword(material, "_NORMALMAP", material.HasProperty("_BumpMap") && material.GetTexture("_BumpMap") != null);
            SetKeyword(material, "_METALLICGLOSSMAP", material.HasProperty("_MetallicGlossMap") && material.GetTexture("_MetallicGlossMap") != null);
            SetKeyword(material, "_EMISSION", material.HasProperty("_EmissionMap") && material.GetTexture("_EmissionMap") != null);
        }

        private static void ConfigureMaterialSurface(Material material, Dictionary<string, object> info, Dictionary<string, object> floats)
        {
            bool legacyAlphaHint = Bool(info.TryGetValue("alpha", out object alphaObj) ? alphaObj : false);
            float surfaceType = Float(floats.TryGetValue("_SurfaceType", out object surfaceTypeObj) ? surfaceTypeObj : null);
            float blendMode = Float(floats.TryGetValue("_BlendMode", out object blendModeObj) ? blendModeObj : null);
            bool alphaTest = Float(floats.TryGetValue("_EnableAlphaTest", out object enableAlphaTestObj) ? enableAlphaTestObj : null) > 0.5f
                || Float(floats.TryGetValue("_AlphaClip", out object alphaClipObj) ? alphaClipObj : null) > 0.5f;
            string shaderName = Str(info.TryGetValue("shader_name", out object shaderNameObj) ? shaderNameObj : null);
            bool overlayShadow = IsOverlayShadow(info);
            bool vfx = shaderName.Contains("VFX") || material.shader.name.Contains("VFX");
            bool transparent = surfaceType > 0.5f || vfx || overlayShadow || (legacyAlphaHint && blendMode > 0f);
            string materialName = Str(
                info.TryGetValue("name", out object materialNameObj)
                    ? materialNameObj
                    : null);
            bool exactTransparentHairShell =
                transparent &&
                string.Equals(
                    shaderName,
                    "HGRP/CharacterNPR_Hair",
                    StringComparison.Ordinal) &&
                materialName.IndexOf("_hairt_", StringComparison.OrdinalIgnoreCase) >= 0;
            bool exactOpaqueHairQueue =
                !transparent &&
                string.Equals(
                    shaderName,
                    "HGRP/CharacterNPR_Hair",
                    StringComparison.Ordinal) &&
                materialName.IndexOf("_hair_", StringComparison.OrdinalIgnoreCase) >= 0 &&
                materialName.IndexOf("_hairt_", StringComparison.OrdinalIgnoreCase) < 0 &&
                floats.ContainsKey("_characterRenderQueue") &&
                floats.ContainsKey("_QueueOffset");
            float sourceZTest = floats.TryGetValue("_ZTest", out object sourceZTestObj)
                ? Float(sourceZTestObj)
                : (float)CompareFunction.LessEqual;
            // Preserve the installed material's render-state dependency before
            // applying the fail-closed compatibility value. The default-off
            // canonical PreG owner is the only runtime path allowed to restore
            // source Equal, and only after it has written the same Forward depth.
            SetMaterialFloat(material, "_RecoveredSourceZTest", sourceZTest);
            if (transparent)
            {
                ConfigureTransparentBlend(material, blendMode, floats, overlayShadow);
                if (material.HasProperty("_SurfaceType"))
                    material.SetFloat("_SurfaceType", 1f);
                if (material.HasProperty("_ZTest"))
                {
                    float recoveredZTest = exactTransparentHairShell &&
                        floats.TryGetValue("_ZTest", out object zTestObj)
                        ? Float(zTestObj)
                        : (float)CompareFunction.LessEqual;
                    material.SetFloat("_ZTest", recoveredZTest);
                }
                if (exactTransparentHairShell)
                    material.renderQueue = 2985;
                if (vfx && material.HasProperty("_DstBlend") && blendMode <= 0f)
                    material.SetFloat("_DstBlend", (float)BlendMode.One);
                if (overlayShadow)
                {
                    if (material.HasProperty("_Cull"))
                        material.SetFloat("_Cull", (float)CullMode.Back);
                    material.renderQueue = 2900;
                }
            }
            else
            {
                SetMaterialInt(material, "_SrcBlend", (int)BlendMode.One);
                SetMaterialInt(material, "_DstBlend", (int)BlendMode.Zero);
                SetMaterialInt(material, "_ZWrite", 1);
                if (material.HasProperty("_ZTest"))
                    material.SetFloat("_ZTest", (float)CompareFunction.LessEqual);
                if (exactOpaqueHairQueue)
                {
                    // The installed CharacterNPR_Hair materials carry their
                    // exact opaque custom queue as base + offset. Leaving the
                    // recovered shader at its AlphaTest default otherwise
                    // moves opaque hair from 2000/2015 to 2450.
                    int sourceQueue = Mathf.RoundToInt(
                        Float(floats["_characterRenderQueue"]) +
                        Float(floats["_QueueOffset"]));
                    material.renderQueue = sourceQueue;
                }
                else
                {
                    material.renderQueue = alphaTest ? (int)RenderQueue.AlphaTest : -1;
                }
            }

            if (material.HasProperty("_AlphaClip"))
                material.SetFloat("_AlphaClip", alphaTest ? 1f : 0f);
            float alphaThreshold = Float(floats.TryGetValue("_AlphaClipThreshold", out object thresholdObj) ? thresholdObj : null, 0.5f);
            SetMaterialFloat(material, "_AlphaClipThreshold", alphaThreshold);
            SetMaterialFloat(material, "_AlphaCutoff", alphaTest ? alphaThreshold : -1f);
            SetMaterialFloat(material, "_Cutoff", alphaThreshold);
            SetKeyword(material, "_ALPHATEST_ON", alphaTest);
            if (material.HasProperty("_Cull") && Math.Abs(FloatProperty(material, "_Cull")) < 0.001f)
                material.SetFloat("_Cull", (float)CullMode.Off);
        }

        private static void ConfigureTransparentBlend(
            Material material,
            float blendMode,
            Dictionary<string, object> floats,
            bool overlayShadow)
        {
            if (!overlayShadow)
            {
                BlendMode src = BlendMode.SrcAlpha;
                BlendMode dst = BlendMode.OneMinusSrcAlpha;
                if (Mathf.RoundToInt(blendMode) == 1)
                    dst = BlendMode.One;
                else if (Mathf.RoundToInt(blendMode) == 4)
                    src = BlendMode.One;
                SetMaterialInt(material, "_SrcBlend", (int)src);
                SetMaterialInt(material, "_DstBlend", (int)dst);
            }

            bool depthWrite = Float(floats.TryGetValue("_TransparentDepthWrite", out object depthWriteObj) ? depthWriteObj : null) > 0.5f;
            SetMaterialInt(material, "_ZWrite", depthWrite && !overlayShadow ? 1 : 0);
            material.DisableKeyword("_ALPHAPREMULTIPLY_ON");
            material.DisableKeyword("_ALPHABLEND_ON");
            if (!overlayShadow && Mathf.RoundToInt(blendMode) == 4)
                material.EnableKeyword("_ALPHAPREMULTIPLY_ON");
            else if (!overlayShadow)
                material.EnableKeyword("_ALPHABLEND_ON");
            material.renderQueue = overlayShadow ? 2900 : (int)RenderQueue.Transparent;
        }

        private static bool IsOverlayShadow(Dictionary<string, object> info)
        {
            string shaderName = Str(info.TryGetValue("shader_name", out object shaderNameObj) ? shaderNameObj : null);
            string materialName = Str(info.TryGetValue("name", out object nameObj) ? nameObj : null).ToLowerInvariant();
            return shaderName.Contains("OverlayShadow")
                || materialName.Contains("hairshadow")
                || materialName.Contains("eyeshadow")
                || materialName.Contains("eyewhiteshadow");
        }

        private static float OverlayShadowStrength(string materialName)
        {
            string key = (materialName ?? string.Empty).ToLowerInvariant();
            if (key.Contains("hairshadow"))
                return 0.34f;
            if (key.Contains("eyewhiteshadow"))
                return 0.22f;
            if (key.Contains("eyeshadow"))
                return 0.32f;
            return 0.34f;
        }

        private static Color OverlayShadowColor(string materialName)
        {
            string key = (materialName ?? string.Empty).ToLowerInvariant();
            if (key.Contains("hairshadow"))
                return new Color(0.44f, 0.38f, 0.34f, 1f);
            if (key.Contains("eyewhiteshadow"))
                return new Color(0.62f, 0.56f, 0.50f, 1f);
            if (key.Contains("eyeshadow"))
                return new Color(0.48f, 0.40f, 0.36f, 1f);
            return new Color(0.52f, 0.46f, 0.40f, 1f);
        }

        private static IList HighestQualityTransformManifest(IList transformManifest)
        {
            var filtered = new List<object>();
            foreach (object obj in transformManifest)
            {
                var item = Dict(obj);
                string path = Str(item.TryGetValue("path", out object pathObj) ? pathObj : null);
                if (IsLowerQualityMeshLodPath(path) && !PreserveForEntityVfx(item))
                    continue;
                filtered.Add(obj);
            }
            return filtered;
        }

        private static int CountHighestQualityMeshes(IList meshes)
        {
            int count = 0;
            foreach (object obj in meshes)
            {
                Dictionary<string, object> info = Dict(obj);
                if (IsHighestQualityMeshLod(info) || PreserveForEntityVfx(info))
                    count++;
            }
            return count;
        }

        private static bool IsHighestQualityMeshLod(Dictionary<string, object> info)
        {
            string path = Str(info.TryGetValue("path", out object pathObj) ? pathObj : null);
            if (TryGetMeshLodFromPath(path, out int pathLod))
                return pathLod == HighestMeshLod;

            string name = Str(info.TryGetValue("name", out object nameObj) ? nameObj : null);
            return !TryGetMeshLodFromName(name, out int nameLod) || nameLod == HighestMeshLod;
        }

        private static bool PreserveForEntityVfx(Dictionary<string, object> info)
        {
            return Bool(info.TryGetValue("preserve_for_entity_vfx", out object value) ? value : null);
        }

        private static bool IsLowerQualityMeshLodPath(string path)
        {
            return TryGetMeshLodFromPath(path, out int lod) && lod != HighestMeshLod;
        }

        private static bool TryGetMeshLodFromPath(string path, out int lod)
        {
            lod = -1;
            if (string.IsNullOrEmpty(path))
                return false;

            string[] parts = path.Replace('\\', '/').Split('/');
            foreach (string part in parts)
            {
                if (TryGetLodSegment(part, out lod))
                    return true;
            }
            return false;
        }

        private static bool TryGetMeshLodFromName(string name, out int lod)
        {
            lod = -1;
            if (string.IsNullOrEmpty(name))
                return false;

            string lower = name.ToLowerInvariant();
            int start = lower.LastIndexOf("lod", StringComparison.Ordinal);
            if (start < 0)
                return false;
            if (start > 0 && lower[start - 1] != '_' && lower[start - 1] != '-' && lower[start - 1] != '/')
                return false;

            int digitStart = start + 3;
            if (digitStart >= lower.Length || !char.IsDigit(lower[digitStart]))
                return false;

            int digitEnd = digitStart;
            while (digitEnd < lower.Length && char.IsDigit(lower[digitEnd]))
                digitEnd++;
            if (digitEnd < lower.Length && char.IsLetterOrDigit(lower[digitEnd]))
                return false;

            return int.TryParse(lower.Substring(digitStart, digitEnd - digitStart), NumberStyles.Integer, CultureInfo.InvariantCulture, out lod);
        }

        private static bool TryGetLodSegment(string segment, out int lod)
        {
            lod = -1;
            if (string.IsNullOrEmpty(segment) || segment.Length <= 3)
                return false;
            string lower = segment.ToLowerInvariant();
            if (!lower.StartsWith("lod", StringComparison.Ordinal))
                return false;
            for (int i = 3; i < lower.Length; i++)
            {
                if (!char.IsDigit(lower[i]))
                    return false;
            }
            return int.TryParse(lower.Substring(3), NumberStyles.Integer, CultureInfo.InvariantCulture, out lod);
        }

        private static List<GameObject> BuildMeshes(
            Transform root,
            IList meshes,
            Dictionary<string, Material> materialCache,
            Dictionary<string, Transform> transformsByPath,
            Dictionary<long, Transform> bonesByCrc,
            string actorGeneratedRoot,
            bool rebuildMeshAssets = true)
        {
            var created = new List<GameObject>();
            foreach (object obj in meshes)
            {
                var info = Dict(obj);
                string name = Str(info["name"]);
                if (!IsHighestQualityMeshLod(info) && !PreserveForEntityVfx(info))
                    continue;

                string meshJson = Str(
                    info.TryGetValue("mesh_json", out object meshJsonObj)
                        ? meshJsonObj
                        : null);
                bool explicitBuiltinCube = ValidateExplicitBuiltinMeshDeclaration(
                    info,
                    name);
                if (explicitBuiltinCube)
                {
                    string declaredRendererKind = Str(
                        info.TryGetValue("renderer_kind", out object builtinRendererKindObject)
                            ? builtinRendererKindObject
                            : info.TryGetValue("renderer_type", out object builtinRendererTypeObject)
                                ? builtinRendererTypeObject
                                : null).Replace("_", "").Replace("-", "").ToLowerInvariant();
                    bool declaredStatic = declaredRendererKind == "static" ||
                        declaredRendererKind == "meshrenderer" ||
                        Bool(info.TryGetValue("is_static", out object builtinStaticObject)
                            ? builtinStaticObject
                            : false);
                    if (!declaredStatic)
                    {
                        throw new InvalidDataException(
                            $"Unity built-in Cube PathID 10202 must be declared as a static " +
                            $"MeshFilter/MeshRenderer before mesh asset creation: {name}");
                    }
                }
                string meshAssetName = Str(
                    info.TryGetValue("mesh_asset_name", out object meshAssetNameObj)
                        ? meshAssetNameObj
                        : name);
                string meshAssetPath = $"{actorGeneratedRoot}/Meshes/{Safe(meshAssetName)}.asset";
                Dictionary<string, object> meshData = null;
                Mesh mesh = AssetDatabase.LoadAssetAtPath<Mesh>(meshAssetPath);
                bool forceRebuildMesh = Bool(
                    info.TryGetValue("force_rebuild_mesh", out object forceRebuildMeshObj)
                        ? forceRebuildMeshObj
                        : false);
                if ((mesh == null || rebuildMeshAssets || forceRebuildMesh) &&
                    explicitBuiltinCube)
                {
                    Mesh rebuiltMesh = CreateUnityBuiltinCubeMeshCopy(name);
                    mesh = SaveOrUpdateGeneratedMeshAsset(
                        mesh,
                        rebuiltMesh,
                        meshAssetPath,
                        name);
                }
                else if (meshJson.Length > 0 && File.Exists(meshJson) && (mesh == null || rebuildMeshAssets || forceRebuildMesh))
                {
                    meshData = Dict(ManifestMiniJson.Deserialize(File.ReadAllText(meshJson, Encoding.UTF8)));
                    Mesh rebuiltMesh = BuildUnityMesh(name, meshData);
                    mesh = SaveOrUpdateGeneratedMeshAsset(
                        mesh,
                        rebuiltMesh,
                        meshAssetPath,
                        name);
                }
                else
                {
                    if (mesh == null)
                    {
                        Debug.LogWarning($"Skipping mesh without JSON or cached asset: {name} {meshJson}");
                        continue;
                    }
                    Debug.Log($"Reusing cached mesh asset: {meshAssetPath}");
                }

                string path = Str(info.TryGetValue("path", out object pathObj) ? pathObj : null);
                Transform meshTransform = null;
                if (path.Length > 0)
                    transformsByPath.TryGetValue(path, out meshTransform);
                if (meshTransform == null)
                {
                    var fallback = new GameObject(name);
                    fallback.transform.SetParent(root, false);
                    fallback.transform.localPosition = Vector3.zero;
                    fallback.transform.localRotation = Quaternion.identity;
                    fallback.transform.localScale = Vector3.one;
                    meshTransform = fallback.transform;
                }

                var go = meshTransform.gameObject;
                string rendererKind = Str(
                    info.TryGetValue("renderer_kind", out object rendererKindObj)
                        ? rendererKindObj
                        : info.TryGetValue("renderer_type", out object rendererTypeObj)
                            ? rendererTypeObj
                            : null).Replace("_", "").Replace("-", "").ToLowerInvariant();
                if (rendererKind.Contains("particle"))
                {
                    throw new InvalidDataException(
                        $"ParticleSystemRenderer import is not recovered for generic actor mesh {name}; " +
                        "particle geometry and simulation semantics must be serialized before this renderer can be admitted.");
                }
                bool staticRenderer = rendererKind == "static" ||
                    rendererKind == "meshrenderer" ||
                    Bool(info.TryGetValue("is_static", out object isStaticObj)
                        ? isStaticObj
                        : false);
                if (explicitBuiltinCube && !staticRenderer)
                {
                    throw new InvalidDataException(
                        $"Unity built-in Cube PathID 10202 must be recovered as a static " +
                        $"MeshFilter/MeshRenderer: {name}");
                }
                if (rendererKind.Length > 0 &&
                    !staticRenderer &&
                    rendererKind != "skinned" &&
                    rendererKind != "skinnedmeshrenderer")
                {
                    throw new InvalidDataException(
                        $"Unsupported recovered renderer_kind '{rendererKind}' on generic actor mesh {name}.");
                }
                bool defaultVisible = Bool(
                    info.TryGetValue("default_visible", out object defaultVisibleObj)
                        ? defaultVisibleObj
                        : true);
                Renderer renderer;
                if (staticRenderer)
                {
                    SkinnedMeshRenderer staleSkinned = go.GetComponent<SkinnedMeshRenderer>();
                    if (staleSkinned != null)
                        UnityEngine.Object.DestroyImmediate(staleSkinned);
                    MeshFilter filter = EnsureComponent<MeshFilter>(go);
                    MeshRenderer meshRenderer = EnsureComponent<MeshRenderer>(go);
                    filter.sharedMesh = mesh;
                    meshRenderer.enabled = defaultVisible;
                    renderer = meshRenderer;
                }
                else
                {
                    MeshFilter staleFilter = go.GetComponent<MeshFilter>();
                    MeshRenderer staleRenderer = go.GetComponent<MeshRenderer>();
                    if (staleRenderer != null)
                        UnityEngine.Object.DestroyImmediate(staleRenderer);
                    if (staleFilter != null)
                        UnityEngine.Object.DestroyImmediate(staleFilter);
                    var smr = EnsureComponent<SkinnedMeshRenderer>(go);
                    smr.sharedMesh = mesh;
                    smr.enabled = defaultVisible;
                    smr.quality = SkinQuality.Bone4;
                    smr.updateWhenOffscreen = true;
                    Transform rootBone = null;
                    string rootBonePath = Str(info.TryGetValue("root_bone_path", out object rootBonePathObj) ? rootBonePathObj : null);
                    if (rootBonePath.Length > 0)
                        transformsByPath.TryGetValue(rootBonePath, out rootBone);
                    if (meshData != null)
                        BindSkin(
                            smr,
                            mesh,
                            meshData,
                            info,
                            transformsByPath,
                            bonesByCrc,
                            rootBone);
                    else
                        BindCachedMeshSkin(smr, mesh, info, transformsByPath, rootBone);
                    renderer = smr;
                }

                var assignedMaterials = new List<Material>();
                IList materialKeys = info.TryGetValue("material_keys", out object materialKeysObj)
                    ? List(materialKeysObj)
                    : List(Array.Empty<object>());
                if (materialKeys.Count == 0)
                {
                    string materialKey = Str(
                        info.TryGetValue("material_key", out object materialKeyObj)
                            ? materialKeyObj
                            : null);
                    if (materialKey.Length > 0)
                        materialKeys = new object[] { materialKey };
                }
                foreach (object materialKeyObj in materialKeys)
                {
                    string materialKey = Str(materialKeyObj);
                    if (materialCache.TryGetValue(materialKey, out Material material))
                        assignedMaterials.Add(material);
                }
                if (assignedMaterials.Count > 0)
                    renderer.sharedMaterials = assignedMaterials.ToArray();

                if (!staticRenderer &&
                    info.TryGetValue("aabb_center", out object centerObj) &&
                    info.TryGetValue("aabb_extent", out object extentObj))
                {
                    Vector3 extent = Vec3(List(extentObj));
                    if (extent.sqrMagnitude > 0.000001f)
                        ((SkinnedMeshRenderer)renderer).localBounds =
                            new Bounds(Vec3(List(centerObj)), extent * 2f);
                }

                ApplySourceSerializedRendererState(
                    renderer,
                    info,
                    transformsByPath);

                created.Add(go);
            }
            return created;
        }

        private static void ApplySourceSerializedRendererState(
            Renderer renderer,
            Dictionary<string, object> meshInfo,
            Dictionary<string, Transform> transformsByPath)
        {
            Dictionary<string, object> state = Dict(
                meshInfo.TryGetValue("renderer_state", out object stateObject)
                    ? stateObject
                    : null);
            if (renderer == null || !Bool(
                    state.TryGetValue(
                        "source_serialized_state",
                        out object exactObject)
                        ? exactObject
                        : null))
            {
                return;
            }

            var serialized = new SerializedObject(renderer);
            int applied = 0;
            applied += SetSerializedBoolIfPresent(
                serialized, state, "enabled", "m_Enabled");
            applied += SetSerializedIntegerIfPresent(
                serialized, state, "cast_shadows", "m_CastShadows");
            applied += SetSerializedIntegerIfPresent(
                serialized, state, "receive_shadows", "m_ReceiveShadows");
            applied += SetSerializedIntegerIfPresent(
                serialized, state, "dynamic_occludee", "m_DynamicOccludee");
            applied += SetSerializedIntegerIfPresent(
                serialized, state, "static_shadow_caster", "m_StaticShadowCaster");
            applied += SetSerializedIntegerIfPresent(
                serialized, state, "motion_vectors", "m_MotionVectors");
            applied += SetSerializedIntegerIfPresent(
                serialized, state, "light_probe_usage", "m_LightProbeUsage");
            applied += SetSerializedIntegerIfPresent(
                serialized, state, "reflection_probe_usage", "m_ReflectionProbeUsage");
            applied += SetSerializedIntegerIfPresent(
                serialized, state, "ray_tracing_mode", "m_RayTracingMode");
            applied += SetSerializedIntegerIfPresent(
                serialized, state, "ray_trace_procedural", "m_RayTraceProcedural");
            applied += SetSerializedIntegerIfPresent(
                serialized, state, "rendering_layer_mask", "m_RenderingLayerMask");
            applied += SetSerializedIntegerIfPresent(
                serialized, state, "renderer_priority", "m_RendererPriority");
            applied += SetSerializedIntegerIfPresent(
                serialized, state, "sorting_layer_id", "m_SortingLayerID");
            applied += SetSerializedIntegerIfPresent(
                serialized, state, "sorting_layer", "m_SortingLayer");
            applied += SetSerializedIntegerIfPresent(
                serialized, state, "sorting_order", "m_SortingOrder");
            applied += SetSerializedVector4IfPresent(
                serialized, state, "lightmap_tiling_offset", "m_LightmapTilingOffset");
            applied += SetSerializedVector4IfPresent(
                serialized, state, "lightmap_tiling_offset_dynamic", "m_LightmapTilingOffsetDynamic");
            applied += SetSerializedTransformReferenceIfPresent(
                serialized, state, "static_batch_root", "m_StaticBatchRoot",
                transformsByPath, useGameObject: false);
            applied += SetSerializedTransformReferenceIfPresent(
                serialized, state, "probe_anchor", "m_ProbeAnchor",
                transformsByPath, useGameObject: false);
            applied += SetSerializedTransformReferenceIfPresent(
                serialized, state, "light_probe_volume_override", "m_LightProbeVolumeOverride",
                transformsByPath, useGameObject: true);
            applied += SetSerializedStaticBatchInfoIfPresent(serialized, state);
            applied += SetSerializedNullMeshReferenceIfPresent(
                serialized, state, "additional_vertex_streams", "m_AdditionalVertexStreams");
            if (renderer is SkinnedMeshRenderer)
            {
                applied += SetSerializedIntegerIfPresent(
                    serialized, state, "skinned_quality", "m_Quality");
                applied += SetSerializedBoolIfPresent(
                    serialized, state, "update_when_offscreen", "m_UpdateWhenOffscreen");
                applied += SetSerializedFloatArrayIfPresent(
                    serialized, state, "blend_shape_weights", "m_BlendShapeWeights");
                applied += SetSerializedBoolIfPresent(
                    serialized, state, "dirty_aabb", "m_DirtyAABB");
            }
            serialized.ApplyModifiedPropertiesWithoutUndo();
            if (applied == 0)
            {
                throw new InvalidDataException(
                    $"No source Renderer state could be applied to {renderer.name}.");
            }
        }

        private static int SetSerializedBoolIfPresent(
            SerializedObject serialized,
            Dictionary<string, object> state,
            string manifestName,
            string serializedName)
        {
            if (!state.TryGetValue(manifestName, out object value))
                return 0;
            SerializedProperty property = serialized.FindProperty(serializedName);
            if (property == null)
                return 0;
            property.boolValue = Bool(value);
            return 1;
        }

        private static int SetSerializedVector4IfPresent(
            SerializedObject serialized,
            Dictionary<string, object> state,
            string manifestName,
            string serializedName)
        {
            if (!state.TryGetValue(manifestName, out object value))
                return 0;
            SerializedProperty property = serialized.FindProperty(serializedName);
            if (property == null)
                return 0;
            IList values = List(value);
            property.vector4Value = new Vector4(
                Float(values.Count > 0 ? values[0] : null),
                Float(values.Count > 1 ? values[1] : null),
                Float(values.Count > 2 ? values[2] : null),
                Float(values.Count > 3 ? values[3] : null));
            return 1;
        }

        private static int SetSerializedTransformReferenceIfPresent(
            SerializedObject serialized,
            Dictionary<string, object> state,
            string manifestName,
            string serializedName,
            Dictionary<string, Transform> transformsByPath,
            bool useGameObject)
        {
            if (!state.TryGetValue(manifestName, out object value))
                return 0;
            SerializedProperty property = serialized.FindProperty(serializedName);
            if (property == null)
                return 0;
            Dictionary<string, object> reference = Dict(value);
            long pathId = Long(reference.TryGetValue("path_id", out object pathIdObject)
                ? pathIdObject
                : null);
            if (pathId == 0)
            {
                property.objectReferenceValue = null;
                return 1;
            }
            string path = Str(reference.TryGetValue("path", out object pathObject)
                ? pathObject
                : null);
            if (path.Length == 0 || !transformsByPath.TryGetValue(path, out Transform target))
            {
                throw new InvalidDataException(
                    $"Source {manifestName} PathID {pathId} is outside the recovered actor hierarchy.");
            }
            property.objectReferenceValue = useGameObject
                ? (UnityEngine.Object)target.gameObject
                : target;
            return 1;
        }

        private static int SetSerializedStaticBatchInfoIfPresent(
            SerializedObject serialized,
            Dictionary<string, object> state)
        {
            if (!state.TryGetValue("static_batch_info", out object value))
                return 0;
            SerializedProperty property = serialized.FindProperty("m_StaticBatchInfo");
            if (property == null)
                return 0;
            Dictionary<string, object> info = Dict(value);
            SerializedProperty first = property.FindPropertyRelative("firstSubMesh");
            SerializedProperty count = property.FindPropertyRelative("subMeshCount");
            if (first == null || count == null)
                return 0;
            first.longValue = Long(info.TryGetValue("first_sub_mesh", out object firstObject)
                ? firstObject
                : null);
            count.longValue = Long(info.TryGetValue("sub_mesh_count", out object countObject)
                ? countObject
                : null);
            return 1;
        }

        private static int SetSerializedNullMeshReferenceIfPresent(
            SerializedObject serialized,
            Dictionary<string, object> state,
            string manifestName,
            string serializedName)
        {
            if (!state.TryGetValue(manifestName, out object value))
                return 0;
            SerializedProperty property = serialized.FindProperty(serializedName);
            if (property == null)
                return 0;
            Dictionary<string, object> reference = Dict(value);
            long pathId = Long(reference.TryGetValue("path_id", out object pathIdObject)
                ? pathIdObject
                : null);
            if (pathId != 0)
            {
                throw new InvalidDataException(
                    $"Source {manifestName} Mesh PathID {pathId} is not yet recovered.");
            }
            property.objectReferenceValue = null;
            return 1;
        }

        private static int SetSerializedFloatArrayIfPresent(
            SerializedObject serialized,
            Dictionary<string, object> state,
            string manifestName,
            string serializedName)
        {
            if (!state.TryGetValue(manifestName, out object value))
                return 0;
            SerializedProperty property = serialized.FindProperty(serializedName);
            if (property == null || !property.isArray)
                return 0;
            IList values = List(value);
            property.arraySize = values.Count;
            for (int index = 0; index < values.Count; index++)
                property.GetArrayElementAtIndex(index).floatValue = Float(values[index]);
            return 1;
        }

        private static int SetSerializedIntegerIfPresent(
            SerializedObject serialized,
            Dictionary<string, object> state,
            string manifestName,
            string serializedName)
        {
            if (!state.TryGetValue(manifestName, out object value))
                return 0;
            SerializedProperty property = serialized.FindProperty(serializedName);
            if (property == null)
                return 0;
            property.longValue = Long(value);
            return 1;
        }

        private static bool ValidateExplicitBuiltinMeshDeclaration(
            Dictionary<string, object> info,
            string meshName)
        {
            bool hasPathId = info.TryGetValue(
                "builtin_mesh_path_id",
                out object pathIdObject);
            bool hasPrimitive = info.TryGetValue(
                "builtin_primitive",
                out object primitiveObject);
            if (!hasPathId && !hasPrimitive)
                return false;
            long pathId = Long(pathIdObject);
            string primitive = Str(primitiveObject).Trim().ToLowerInvariant();
            if (!hasPathId || !hasPrimitive || pathId != 10202L || primitive != "cube")
            {
                throw new InvalidDataException(
                    $"Unsupported or incomplete Unity built-in Mesh declaration on {meshName}: " +
                    $"builtin_mesh_path_id={pathId} builtin_primitive={primitive}. " +
                    "Only the source-explicit built-in Cube PathID 10202 is recovered.");
            }
            return true;
        }

        private static Mesh CreateUnityBuiltinCubeMeshCopy(string meshName)
        {
            GameObject primitive = null;
            try
            {
                primitive = GameObject.CreatePrimitive(PrimitiveType.Cube);
                MeshFilter filter = primitive.GetComponent<MeshFilter>();
                Mesh source = filter != null ? filter.sharedMesh : null;
                if (source == null || source.vertexCount == 0 || source.subMeshCount == 0)
                {
                    throw new InvalidOperationException(
                        "Unity 2022.3.62f3 did not expose its built-in Cube mesh.");
                }
                Mesh copy = UnityEngine.Object.Instantiate(source);
                copy.name = meshName;
                return copy;
            }
            finally
            {
                if (primitive != null)
                    UnityEngine.Object.DestroyImmediate(primitive);
            }
        }

        private static Mesh SaveOrUpdateGeneratedMeshAsset(
            Mesh existing,
            Mesh rebuilt,
            string meshAssetPath,
            string meshName)
        {
            if (rebuilt == null)
                throw new ArgumentNullException(nameof(rebuilt));
            if (existing == null)
            {
                rebuilt.name = meshName;
                AssetDatabase.CreateAsset(rebuilt, meshAssetPath);
                return rebuilt;
            }

            // Update serialized mesh data in place so an already-imported
            // actor prefab retains the mesh asset GUID and local reference.
            EditorUtility.CopySerialized(rebuilt, existing);
            existing.name = meshName;
            EditorUtility.SetDirty(existing);
            UnityEngine.Object.DestroyImmediate(rebuilt);
            return existing;
        }

        public static void ValidateExplicitBuiltinCubeMeshContract()
        {
            var exact = new Dictionary<string, object>
            {
                { "builtin_mesh_path_id", 10202L },
                { "builtin_primitive", "cube" },
            };
            if (!ValidateExplicitBuiltinMeshDeclaration(exact, "contract_cube"))
                throw new InvalidOperationException("Exact built-in Cube declaration was not admitted.");

            foreach (Dictionary<string, object> invalid in new[]
            {
                new Dictionary<string, object>
                {
                    { "builtin_mesh_path_id", 10203L },
                    { "builtin_primitive", "cube" },
                },
                new Dictionary<string, object>
                {
                    { "builtin_mesh_path_id", 10202L },
                    { "builtin_primitive", "sphere" },
                },
                new Dictionary<string, object>
                {
                    { "builtin_mesh_path_id", 10202L },
                },
            })
            {
                bool rejected = false;
                try
                {
                    ValidateExplicitBuiltinMeshDeclaration(invalid, "invalid_contract");
                }
                catch (InvalidDataException)
                {
                    rejected = true;
                }
                if (!rejected)
                    throw new InvalidOperationException("An unsupported built-in Mesh declaration was admitted.");
            }

            GameObject directPrimitive = null;
            Mesh recovered = null;
            try
            {
                directPrimitive = GameObject.CreatePrimitive(PrimitiveType.Cube);
                Mesh direct = directPrimitive.GetComponent<MeshFilter>().sharedMesh;
                recovered = CreateUnityBuiltinCubeMeshCopy("contract_cube");
                if (direct == null || recovered == null ||
                    direct.vertexCount != recovered.vertexCount ||
                    direct.subMeshCount != recovered.subMeshCount ||
                    direct.bounds != recovered.bounds)
                {
                    throw new InvalidDataException(
                        "Recovered built-in Cube topology/bounds differ from Unity's direct primitive.");
                }
                for (int subMesh = 0; subMesh < direct.subMeshCount; subMesh++)
                {
                    if (direct.GetIndexCount(subMesh) != recovered.GetIndexCount(subMesh) ||
                        direct.GetTopology(subMesh) != recovered.GetTopology(subMesh))
                    {
                        throw new InvalidDataException(
                            $"Recovered built-in Cube submesh {subMesh} differs from Unity's direct primitive.");
                    }
                }
                Debug.Log(
                    $"Unity built-in Cube recovery contract passed: path_id=10202 " +
                    $"vertices={recovered.vertexCount} submeshes={recovered.subMeshCount} " +
                    $"indices={Enumerable.Range(0, recovered.subMeshCount).Sum(i => (long)recovered.GetIndexCount(i))}.");
            }
            finally
            {
                if (recovered != null)
                    UnityEngine.Object.DestroyImmediate(recovered);
                if (directPrimitive != null)
                    UnityEngine.Object.DestroyImmediate(directPrimitive);
            }
        }

        private static void BuildRecoveredLodGroups(Transform root, IList records)
        {
            foreach (object recordObject in records)
            {
                Dictionary<string, object> record = Dict(recordObject);
                string path = Str(record.TryGetValue("path", out object pathObject) ? pathObject : null);
                Transform owner = path.Length == 0 ? root : root.Find(path);
                if (owner == null)
                    throw new InvalidDataException("Recovered LODGroup owner is missing: " + path);

                var lods = new List<LOD>();
                foreach (object lodObject in List(record.TryGetValue("lods", out object lodsObject) ? lodsObject : null))
                {
                    Dictionary<string, object> lodRecord = Dict(lodObject);
                    var renderers = new List<Renderer>();
                    foreach (object rendererPathObject in List(
                        lodRecord.TryGetValue("renderer_paths", out object rendererPathsObject)
                            ? rendererPathsObject
                            : null))
                    {
                        string rendererPath = Str(rendererPathObject);
                        Transform rendererTransform = root.Find(rendererPath);
                        Renderer renderer = rendererTransform != null
                            ? rendererTransform.GetComponent<Renderer>()
                            : null;
                        if (renderer == null)
                            throw new InvalidDataException(
                                "Recovered LODGroup renderer is missing: " + rendererPath);
                        renderers.Add(renderer);
                    }
                    if (renderers.Count == 0)
                        throw new InvalidDataException("Recovered LODGroup contains an empty LOD: " + path);

                    var lod = new LOD(
                        Float(lodRecord.TryGetValue("screen_relative_height", out object heightObject)
                            ? heightObject
                            : null),
                        renderers.ToArray())
                    {
                        fadeTransitionWidth = Float(
                            lodRecord.TryGetValue("fade_transition_width", out object widthObject)
                                ? widthObject
                                : null),
                    };
                    lods.Add(lod);
                }
                if (lods.Count == 0)
                    throw new InvalidDataException("Recovered LODGroup has no serialized LODs: " + path);

                LODGroup group = owner.GetComponent<LODGroup>();
                if (group == null)
                    group = owner.gameObject.AddComponent<LODGroup>();
                group.SetLODs(lods.ToArray());
                group.fadeMode = (LODFadeMode)Int(
                    record.TryGetValue("fade_mode", out object fadeModeObject) ? fadeModeObject : null);
                group.animateCrossFading = Bool(
                    record.TryGetValue("animate_cross_fading", out object animateObject) ? animateObject : null);
                group.localReferencePoint = Vec3(List(
                    record.TryGetValue("local_reference_point", out object referenceObject)
                        ? referenceObject
                        : null));
                group.size = Float(record.TryGetValue("size", out object sizeObject) ? sizeObject : null);
                group.enabled = Bool(
                    record.TryGetValue("enabled", out object enabledObject) ? enabledObject : true);
                EditorUtility.SetDirty(group);
            }
        }

        private static List<GameObject> BuildStaticProps(
            Transform root,
            IList staticProps,
            Dictionary<string, Material> materialCache,
            string actorGeneratedRoot)
        {
            var created = new List<GameObject>();
            foreach (object obj in staticProps)
            {
                var info = Dict(obj);
                string name = Str(info.TryGetValue("name", out object nameObj) ? nameObj : null);
                string sourceObjPath = Str(info.TryGetValue("mesh_obj", out object meshObj) ? meshObj : null);
                string path = Str(info.TryGetValue("path", out object pathObj) ? pathObj : null);
                if (name.Length == 0 || path.Length == 0 || sourceObjPath.Length == 0 || !File.Exists(sourceObjPath))
                {
                    Debug.LogWarning($"Skipping static prop without OBJ: {name}");
                    continue;
                }

                Transform propRoot = EnsurePath(root, path);
                propRoot.localPosition = Vec3(List(info.TryGetValue("local_pos", out object posObj) ? posObj : null));
                propRoot.localRotation = Quat(List(info.TryGetValue("local_rot", out object rotObj) ? rotObj : null));
                IList scaleList = List(info.TryGetValue("local_scale", out object scaleObj) ? scaleObj : null);
                propRoot.localScale = scaleList.Count >= 3 ? Vec3(scaleList) : Vector3.one;

                string objAssetPath = $"{actorGeneratedRoot}/StaticProps/{Safe(name)}.obj";
                if (CopyExternalAssetIntoProject(sourceObjPath, objAssetPath))
                    AssetDatabase.ImportAsset(objAssetPath, ImportAssetOptions.ForceUpdate);
                else if (AssetDatabase.LoadAssetAtPath<GameObject>(objAssetPath) == null)
                    AssetDatabase.ImportAsset(objAssetPath, ImportAssetOptions.ForceUpdate);

                GameObject modelAsset = AssetDatabase.LoadAssetAtPath<GameObject>(objAssetPath);
                GameObject instance = modelAsset != null
                    ? PrefabUtility.InstantiatePrefab(modelAsset) as GameObject
                    : null;
                if (instance == null)
                {
                    instance = GameObject.CreatePrimitive(PrimitiveType.Cube);
                    Collider collider = instance.GetComponent<Collider>();
                    if (collider != null)
                        UnityEngine.Object.DestroyImmediate(collider);
                    instance.transform.localScale = Vector3.one * 0.05f;
                }

                instance.name = name;
                instance.transform.SetParent(propRoot, false);
                instance.transform.localPosition = Vector3.zero;
                instance.transform.localRotation = Quaternion.identity;
                instance.transform.localScale = Vector3.one;

                AssignStaticPropMaterials(instance, List(info.TryGetValue("material_keys", out object keysObj) ? keysObj : null), materialCache);
                bool defaultVisible = Bool(
                    info.TryGetValue("default_visible", out object defaultVisibleObj)
                        ? defaultVisibleObj
                        : false);
                foreach (Renderer renderer in instance.GetComponentsInChildren<Renderer>(true))
                {
                    if (renderer != null)
                        renderer.enabled = defaultVisible;
                }
                created.Add(propRoot.gameObject);
            }
            return created;
        }

        private static void RemoveStaleUnsupportedLastRiteFallbackAssets(
            string rootName,
            string actorGeneratedRoot)
        {
            if (!string.Equals(rootName, "Lastrite", StringComparison.OrdinalIgnoreCase))
                return;

            // The current installed postmodel proves these exact two LOD0
            // renderers are runtime-effect auxiliaries, not ordinary character
            // surfaces. The generated manifest excludes them by actor + source
            // Mesh PPtr + Material PPtr + Shader PPtr. Targeted refreshes retain
            // other actor assets, so remove only the exact stale files after the
            // replacement prefab has been saved and no longer references them.
            foreach (string assetPath in new[]
            {
                $"{actorGeneratedRoot}/Meshes/S_actor_lastrite_skill_01_lod0.asset",
                $"{actorGeneratedRoot}/Meshes/S_actor_lastrite_vfxpart_01_lod0.asset",
                $"{actorGeneratedRoot}/Materials/actor_lastrite_pathid_-2296838609362971186.mat",
                $"{actorGeneratedRoot}/Materials/actor_lastrite_pathid_-7618720439349846356.mat",
            })
            {
                if (AssetDatabase.LoadMainAssetAtPath(assetPath) != null)
                    AssetDatabase.DeleteAsset(assetPath);
            }
        }

        private static Transform EnsurePath(Transform root, string path)
        {
            Transform current = root;
            foreach (string part in path.Split(new[] { '/' }, StringSplitOptions.RemoveEmptyEntries))
            {
                Transform child = current.Find(part);
                if (child == null)
                {
                    var go = new GameObject(part);
                    go.transform.SetParent(current, false);
                    child = go.transform;
                }
                current = child;
            }
            return current;
        }

        private static bool CopyExternalAssetIntoProject(string sourcePath, string assetPath)
        {
            string fullAssetPath = Path.Combine(Directory.GetCurrentDirectory(), assetPath);
            Directory.CreateDirectory(Path.GetDirectoryName(fullAssetPath) ?? ".");
            if (File.Exists(fullAssetPath))
            {
                var sourceInfo = new FileInfo(sourcePath);
                var targetInfo = new FileInfo(fullAssetPath);
                if (sourceInfo.Length == targetInfo.Length && sourceInfo.LastWriteTimeUtc <= targetInfo.LastWriteTimeUtc)
                    return false;
            }
            File.Copy(sourcePath, fullAssetPath, true);
            return true;
        }

        private static void AssignStaticPropMaterials(GameObject instance, IList materialKeys, Dictionary<string, Material> materialCache)
        {
            var materials = new List<Material>();
            foreach (object keyObj in materialKeys)
            {
                string key = Str(keyObj);
                if (key.Length > 0 && materialCache.TryGetValue(key, out Material material) && material != null)
                    materials.Add(material);
            }
            if (materials.Count == 0)
                return;

            foreach (Renderer renderer in instance.GetComponentsInChildren<Renderer>(true))
            {
                int count = Mathf.Max(1, renderer.sharedMaterials.Length);
                var assigned = new Material[count];
                for (int i = 0; i < count; i++)
                    assigned[i] = materials[Mathf.Min(i, materials.Count - 1)];
                renderer.sharedMaterials = assigned;
            }
        }

        private static Mesh BuildUnityMesh(string name, Dictionary<string, object> meshData)
        {
            var mesh = new Mesh();
            mesh.name = name;
            var vertices = FloatList(meshData["m_Vertices"]);
            var outVerts = new Vector3[vertices.Count / 3];
            for (int i = 0; i < outVerts.Length; i++)
                outVerts[i] = new Vector3(vertices[i * 3], vertices[i * 3 + 1], vertices[i * 3 + 2]);
            mesh.vertices = outVerts;

            if (meshData.TryGetValue("m_Normals", out object normalsObj) && normalsObj is IList)
            {
                var normals = FloatList(normalsObj);
                if (normals.Count >= outVerts.Length * 3)
                {
                    var outNormals = new Vector3[outVerts.Length];
                    for (int i = 0; i < outNormals.Length; i++)
                        outNormals[i] = new Vector3(normals[i * 3], normals[i * 3 + 1], normals[i * 3 + 2]);
                    mesh.normals = outNormals;
                }
            }

            if (meshData.TryGetValue("m_UV0", out object uvObj) && uvObj is IList)
            {
                var uvs = FloatList(uvObj);
                if (uvs.Count >= outVerts.Length * 2)
                {
                    var outUvs = new Vector2[outVerts.Length];
                    for (int i = 0; i < outUvs.Length; i++)
                        outUvs[i] = new Vector2(uvs[i * 2], uvs[i * 2 + 1]);
                    mesh.uv = outUvs;
                }
            }

            if (meshData.TryGetValue("m_UV1", out object uv1Obj) && uv1Obj is IList)
            {
                var uvs = FloatList(uv1Obj);
                if (uvs.Count >= outVerts.Length * 2)
                {
                    var outUvs = new Vector2[outVerts.Length];
                    for (int i = 0; i < outUvs.Length; i++)
                        outUvs[i] = new Vector2(uvs[i * 2], uvs[i * 2 + 1]);
                    mesh.uv2 = outUvs;
                }
            }

            if (meshData.TryGetValue("m_Colors", out object colorsObj) && colorsObj is IList)
            {
                var colors = FloatList(colorsObj);
                if (colors.Count >= outVerts.Length * 4)
                {
                    var outColors = new Color[outVerts.Length];
                    for (int i = 0; i < outColors.Length; i++)
                        outColors[i] = new Color(colors[i * 4], colors[i * 4 + 1], colors[i * 4 + 2], colors[i * 4 + 3]);
                    mesh.colors = outColors;
                }
            }

            if (meshData.TryGetValue("m_Tangents", out object tangentsObj) && tangentsObj is IList)
            {
                var tangents = FloatList(tangentsObj);
                if (tangents.Count >= outVerts.Length * 4)
                {
                    var outTangents = new Vector4[outVerts.Length];
                    for (int i = 0; i < outTangents.Length; i++)
                        outTangents[i] = new Vector4(tangents[i * 4], tangents[i * 4 + 1], tangents[i * 4 + 2], tangents[i * 4 + 3]);
                    mesh.tangents = outTangents;
                }
            }

            var indices = IntList(meshData["m_Indices"]);
            IList subMeshes = meshData.TryGetValue("m_SubMeshes", out object subMeshObj) ? List(subMeshObj) : (IList)Array.Empty<object>();
            int sourceIndexSize = InferSourceIndexSize(subMeshes, outVerts.Length);
            mesh.indexFormat = sourceIndexSize == 4 ? IndexFormat.UInt32 : IndexFormat.UInt16;
            if (subMeshes.Count > 0)
            {
                mesh.subMeshCount = subMeshes.Count;
                for (int subMesh = 0; subMesh < subMeshes.Count; subMesh++)
                {
                    var subMeshData = Dict(subMeshes[subMesh]);
                    int start = Int(subMeshData["firstByte"]) / sourceIndexSize;
                    int count = Int(subMeshData["indexCount"]);
                    if (start < 0 || count <= 0 || start + count > indices.Length)
                    {
                        Debug.LogWarning($"Invalid submesh range in {name}: submesh={subMesh} start={start} count={count} indices={indices.Length}");
                        mesh.SetTriangles(indices, subMesh, false);
                        continue;
                    }
                    var subIndices = new int[count];
                    Array.Copy(indices, start, subIndices, 0, count);
                    mesh.SetTriangles(subIndices, subMesh, false, Int(subMeshData["baseVertex"]));
                }
            }
            else
            {
                mesh.SetTriangles(indices, 0, true);
            }
            if (mesh.normals == null || mesh.normals.Length != outVerts.Length)
                mesh.RecalculateNormals();
            if (mesh.tangents == null || mesh.tangents.Length != outVerts.Length)
                mesh.RecalculateTangents();
            mesh.RecalculateBounds();
            return mesh;
        }

        internal static Mesh BuildUnityMeshForRecoveredSource(
            string name,
            Dictionary<string, object> meshData)
        {
            Mesh mesh = BuildUnityMesh(name, meshData);
            var hashes = List(meshData["m_BoneNameHashes"]);
            var bindPoseData = List(meshData["m_BindPose"]);
            var skin = List(meshData["m_Skin"]);
            if (hashes.Count == 0 ||
                bindPoseData.Count != hashes.Count ||
                skin.Count < mesh.vertexCount)
            {
                UnityEngine.Object.DestroyImmediate(mesh);
                throw new InvalidDataException(
                    $"Recovered source mesh skin contract is incomplete: " +
                    $"{name} hashes={hashes.Count} bindposes={bindPoseData.Count} " +
                    $"skin={skin.Count} vertices={mesh.vertexCount}");
            }

            var bindPoses = new Matrix4x4[hashes.Count];
            for (int index = 0; index < bindPoses.Length; index++)
                bindPoses[index] = Matrix(Dict(bindPoseData[index]));
            mesh.bindposes = bindPoses;

            var weights = new BoneWeight[mesh.vertexCount];
            for (int vertex = 0; vertex < weights.Length; vertex++)
            {
                var entry = Dict(skin[vertex]);
                var weightList = FloatList(entry["weight"]);
                var indexList = IntList(entry["boneIndex"]);
                if (weightList.Count != indexList.Length ||
                    indexList.Length > 4)
                {
                    UnityEngine.Object.DestroyImmediate(mesh);
                    throw new InvalidDataException(
                        $"Recovered source mesh vertex skin is malformed: " +
                        $"{name} vertex={vertex} weights={weightList.Count} " +
                        $"indices={indexList.Length}");
                }
                var boneWeight = new BoneWeight();
                if (indexList.Length > 0)
                {
                    boneWeight.boneIndex0 = indexList[0];
                    boneWeight.weight0 = weightList[0];
                }
                if (indexList.Length > 1)
                {
                    boneWeight.boneIndex1 = indexList[1];
                    boneWeight.weight1 = weightList[1];
                }
                if (indexList.Length > 2)
                {
                    boneWeight.boneIndex2 = indexList[2];
                    boneWeight.weight2 = weightList[2];
                }
                if (indexList.Length > 3)
                {
                    boneWeight.boneIndex3 = indexList[3];
                    boneWeight.weight3 = weightList[3];
                }
                weights[vertex] = boneWeight;
            }
            mesh.boneWeights = weights;
            return mesh;
        }

        private static int InferSourceIndexSize(IList subMeshes, int vertexCount)
        {
            int fallback = vertexCount > 65535 ? 4 : 2;
            if (subMeshes == null || subMeshes.Count < 2)
                return fallback;

            foreach (int candidate in new[] { 2, 4 })
            {
                int expectedStart = 0;
                bool sequential = true;
                foreach (object subMeshObj in subMeshes)
                {
                    var subMesh = Dict(subMeshObj);
                    int firstByte = Int(subMesh["firstByte"]);
                    int count = Int(subMesh["indexCount"]);
                    if (firstByte < 0 || firstByte % candidate != 0 ||
                        firstByte / candidate != expectedStart || count < 0)
                    {
                        sequential = false;
                        break;
                    }
                    expectedStart += count;
                }
                if (sequential)
                    return candidate;
            }

            return fallback;
        }

        private static void BindCachedMeshSkin(
            SkinnedMeshRenderer smr,
            Mesh mesh,
            Dictionary<string, object> meshInfo,
            Dictionary<string, Transform> transformsByPath,
            Transform rootBone)
        {
            IList bonePaths = List(meshInfo.TryGetValue("bone_paths", out object bonePathsObj) ? bonePathsObj : null);
            bool recoveredProp = Bool(
                meshInfo.TryGetValue("recovered_prop", out object recoveredPropObj)
                    ? recoveredPropObj
                    : false);
            string propRootPath = Str(
                meshInfo.TryGetValue("prop_root_path", out object propRootPathObj)
                    ? propRootPathObj
                    : null);
            string declaredRootBonePath = Str(
                meshInfo.TryGetValue("root_bone_path", out object declaredRootBonePathObj)
                    ? declaredRootBonePathObj
                    : null);
            var bones = new List<Transform>();
            foreach (object bonePathObj in bonePaths)
            {
                string bonePath = Str(bonePathObj);
                if (recoveredProp &&
                    (propRootPath.Length == 0 ||
                     !bonePath.StartsWith(propRootPath + "/", StringComparison.Ordinal)))
                {
                    throw new InvalidOperationException(
                        $"Recovered prop cached mesh bone escapes its exact owner: " +
                        $"mesh={mesh.name} owner={propRootPath} bone={bonePath}");
                }
                if (bonePath.Length > 0 && transformsByPath.TryGetValue(bonePath, out Transform bone))
                    bones.Add(bone);
                else
                {
                    if (bonePaths.Count > 0)
                        throw new InvalidOperationException(
                            $"Cached mesh explicit bone path is unresolved: " +
                            $"mesh={mesh.name} bone={bonePath}");
                    bones.Add(null);
                }
            }

            if (declaredRootBonePath.Length > 0 && rootBone == null)
            {
                throw new InvalidOperationException(
                    $"Cached mesh explicit root bone path is unresolved: " +
                    $"mesh={mesh.name} root={declaredRootBonePath}");
            }

            if (recoveredProp &&
                (rootBone == null || propRootPath.Length == 0 ||
                 !IsDescendantOfPath(rootBone, transformsByPath, propRootPath)))
            {
                throw new InvalidOperationException(
                    $"Recovered prop cached mesh root bone is unresolved or outside its owner: " +
                    $"mesh={mesh.name} owner={propRootPath}");
            }

            if (bones.Count > 0)
                smr.bones = bones.ToArray();
            smr.rootBone = rootBone != null ? rootBone : (bones.Count > 0 ? bones[0] : null);
            if (mesh != null && mesh.bindposes != null && bones.Count > 0 && mesh.bindposes.Length != bones.Count)
                Debug.LogWarning($"Cached mesh bone count differs from bind pose count: {mesh.name} bones={bones.Count} bindposes={mesh.bindposes.Length}");
        }

        private static void BindSkin(
            SkinnedMeshRenderer smr,
            Mesh mesh,
            Dictionary<string, object> meshData,
            Dictionary<string, object> meshInfo,
            Dictionary<string, Transform> transformsByPath,
            Dictionary<long, Transform> bonesByCrc,
            Transform rootBone)
        {
            var hashes = List(meshData["m_BoneNameHashes"]);
            var bindPoseData = List(meshData["m_BindPose"]);
            IList explicitBonePaths = List(
                meshInfo.TryGetValue("bone_paths", out object bonePathsObj)
                    ? bonePathsObj
                    : null);
            bool hasExplicitBonePaths = explicitBonePaths.Count > 0;
            bool recoveredProp = Bool(
                meshInfo.TryGetValue("recovered_prop", out object recoveredPropObj)
                    ? recoveredPropObj
                    : false);
            string propRootPath = Str(
                meshInfo.TryGetValue("prop_root_path", out object propRootPathObj)
                    ? propRootPathObj
                    : null);
            string declaredRootBonePath = Str(
                meshInfo.TryGetValue("root_bone_path", out object declaredRootBonePathObj)
                    ? declaredRootBonePathObj
                    : null);
            int unresolvedExplicitBonePaths = 0;
            var boneTransforms = new Transform[hashes.Count];
            var bindPoses = new Matrix4x4[hashes.Count];
            for (int i = 0; i < hashes.Count; i++)
            {
                if (i < explicitBonePaths.Count)
                {
                    string bonePath = Str(explicitBonePaths[i]);
                    if (recoveredProp &&
                        (propRootPath.Length == 0 ||
                         !bonePath.StartsWith(propRootPath + "/", StringComparison.Ordinal)))
                    {
                        throw new InvalidOperationException(
                            $"Recovered prop mesh bone escapes its exact owner: " +
                            $"mesh={mesh.name} owner={propRootPath} bone={bonePath}");
                    }
                    if (bonePath.Length == 0 ||
                        !transformsByPath.TryGetValue(bonePath, out boneTransforms[i]))
                    {
                        unresolvedExplicitBonePaths++;
                    }
                }
                else
                {
                    // Older manifests do not carry exact bone paths. Retain the
                    // CRC fallback for them, but never use it in place of an
                    // explicit path: private item-widget rigs commonly repeat
                    // CRCs such as "Root" across several recovered prefabs.
                    if (!hasExplicitBonePaths)
                    {
                        long crc = Long(hashes[i]);
                        bonesByCrc.TryGetValue(crc, out boneTransforms[i]);
                    }
                    else
                    {
                        unresolvedExplicitBonePaths++;
                    }
                }
                bindPoses[i] = i < bindPoseData.Count ? Matrix(Dict(bindPoseData[i])) : Matrix4x4.identity;
            }
            if (hasExplicitBonePaths && explicitBonePaths.Count != hashes.Count)
            {
                throw new InvalidOperationException(
                    $"Explicit mesh bone path count differs from source hash count: " +
                    $"{mesh.name} paths={explicitBonePaths.Count} hashes={hashes.Count}");
            }
            if (unresolvedExplicitBonePaths > 0)
            {
                if (hasExplicitBonePaths)
                    throw new InvalidOperationException(
                        $"Mesh has unresolved explicit bone paths: " +
                        $"mesh={mesh.name} unresolved={unresolvedExplicitBonePaths}");
                Debug.LogWarning(
                    $"Could not resolve {unresolvedExplicitBonePaths} explicit mesh bone paths: " +
                    mesh.name);
            }
            mesh.bindposes = bindPoses;
            smr.bones = boneTransforms;
            if (declaredRootBonePath.Length > 0 && rootBone == null)
            {
                throw new InvalidOperationException(
                    $"Mesh explicit root bone path is unresolved: " +
                    $"mesh={mesh.name} root={declaredRootBonePath}");
            }
            if (recoveredProp &&
                (rootBone == null || propRootPath.Length == 0 ||
                 !IsDescendantOfPath(rootBone, transformsByPath, propRootPath)))
            {
                throw new InvalidOperationException(
                    $"Recovered prop mesh root bone is unresolved or outside its owner: " +
                    $"mesh={mesh.name} owner={propRootPath}");
            }
            smr.rootBone = rootBone != null ? rootBone : (boneTransforms.Length > 0 ? boneTransforms[0] : null);

            var skin = List(meshData["m_Skin"]);
            var weights = new BoneWeight[mesh.vertexCount];
            for (int vertex = 0; vertex < weights.Length && vertex < skin.Count; vertex++)
            {
                var entry = Dict(skin[vertex]);
                var weightList = FloatList(entry["weight"]);
                var indexList = IntList(entry["boneIndex"]);
                var bw = new BoneWeight();
                if (indexList.Length > 0) { bw.boneIndex0 = indexList[0]; bw.weight0 = weightList.Count > 0 ? weightList[0] : 0f; }
                if (indexList.Length > 1) { bw.boneIndex1 = indexList[1]; bw.weight1 = weightList.Count > 1 ? weightList[1] : 0f; }
                if (indexList.Length > 2) { bw.boneIndex2 = indexList[2]; bw.weight2 = weightList.Count > 2 ? weightList[2] : 0f; }
                if (indexList.Length > 3) { bw.boneIndex3 = indexList[3]; bw.weight3 = weightList.Count > 3 ? weightList[3] : 0f; }
                weights[vertex] = bw;
            }
            mesh.boneWeights = weights;
        }

        private static bool IsDescendantOfPath(
            Transform candidate,
            Dictionary<string, Transform> transformsByPath,
            string ownerPath)
        {
            if (candidate == null || string.IsNullOrEmpty(ownerPath))
                return false;
            foreach (var pair in transformsByPath)
            {
                if (pair.Value != candidate)
                    continue;
                return pair.Key.StartsWith(ownerPath + "/", StringComparison.Ordinal);
            }
            return false;
        }

        private static List<AnimationClip> BuildAnimationClips(IList clips, GameObject root, string actorGeneratedRoot)
        {
            var result = new List<AnimationClip>();
            GameObject referenceRoot = root;
            if (referenceRoot == null)
            {
                string prefabFolder = $"{actorGeneratedRoot}/Prefabs";
                string[] prefabGuids = AssetDatabase.FindAssets("t:Prefab", new[] { prefabFolder });
                string prefabGuid = prefabGuids.Length > 0 ? prefabGuids[0] : string.Empty;
                if (!string.IsNullOrEmpty(prefabGuid))
                {
                    referenceRoot = AssetDatabase.LoadAssetAtPath<GameObject>(
                        AssetDatabase.GUIDToAssetPath(prefabGuid));
                }
            }
            var clipInfoByName = new Dictionary<string, Dictionary<string, object>>(StringComparer.Ordinal);
            foreach (object clipObj in clips)
            {
                var info = Dict(clipObj);
                string clipName = Str(info.TryGetValue("name", out object nameObj) ? nameObj : null);
                if (clipName.Length > 0)
                    clipInfoByName[clipName] = info;
            }
            AssetDatabase.StartAssetEditing();
            try
            {
                foreach (object clipObj in clips)
                {
                    var clipInfo = Dict(clipObj);
                    string name = Str(clipInfo["name"]);
                    string sampleJson = Str(clipInfo["sample_json"]);
                    if (name.Length == 0 || sampleJson.Length == 0 || !File.Exists(sampleJson))
                        continue;

                    string assetPath = $"{actorGeneratedRoot}/Animations/{Safe(name)}.anim";
                    AnimationClip existingClip = AssetDatabase.LoadAssetAtPath<AnimationClip>(assetPath);

                    var sampleData = Dict(ManifestMiniJson.Deserialize(File.ReadAllText(sampleJson, Encoding.UTF8)));
                    var frames = List(sampleData["frames"]);
                    bool loop = Bool(clipInfo.TryGetValue("loop", out object loopObj) ? loopObj : false);
                    bool loopBlend = Bool(
                        clipInfo.TryGetValue("loop_blend", out object loopBlendObj) ? loopBlendObj : false);
                    float sourceDuration = Float(
                        clipInfo.TryGetValue("duration", out object durationObj)
                            ? durationObj
                            : sampleData.TryGetValue("duration", out object sampleDurationObj)
                                ? sampleDurationObj
                                : null,
                        0f);
                    var clip = new AnimationClip
                    {
                        name = name,
                        frameRate = Float(clipInfo["sample_rate"], 60f),
                        legacy = true,
                        wrapMode = loop ? WrapMode.Loop : WrapMode.Once,
                    };
                    int previewStride = Mathf.Max(1, Int(clipInfo.TryGetValue("unity_preview_stride", out object strideObj) ? strideObj : null, 1));
                    foreach (object boneObj in List(clipInfo["bones"]))
                    {
                        var bone = Dict(boneObj);
                        string path = Str(bone["path"]);
                        int trackIndex = Int(bone["track_index"], -1);
                        if (path.Length == 0 || trackIndex < 0)
                            continue;
                        bool posAnimated = Bool(bone.TryGetValue("pos_animated", out object posAnimatedObj) ? posAnimatedObj : true);
                        bool rotAnimated = Bool(bone.TryGetValue("rot_animated", out object rotAnimatedObj) ? rotAnimatedObj : true);
                        bool scaleAnimated = Bool(bone.TryGetValue("scale_animated", out object scaleAnimatedObj) ? scaleAnimatedObj : false);
                        if (!posAnimated && !rotAnimated && !scaleAnimated)
                            continue;
                        AddTransformCurves(
                            clip,
                            path,
                            trackIndex,
                            frames,
                            posAnimated,
                            rotAnimated,
                            scaleAnimated,
                            previewStride,
                            loop,
                            sourceDuration);
                    }
                    AddGameObjectActiveCurves(
                        clip,
                        List(
                            clipInfo.TryGetValue(
                                "game_object_active_curves",
                                out object activeCurvesObj)
                                ? activeCurvesObj
                                : null));
                    AddRendererMaterialFloatCurves(
                        clip,
                        List(
                            clipInfo.TryGetValue(
                                "material_float_curves",
                                out object materialCurvesObj)
                                ? materialCurvesObj
                                : null));
                    AddOverviewHandoffReferenceCurves(
                        clip,
                        clipInfo,
                        clipInfoByName,
                        referenceRoot,
                        sourceDuration);
                    clip.EnsureQuaternionContinuity();
                    ApplyClipLoopSettings(clip, loop, loopBlend);

                    if (existingClip == null)
                    {
                        AssetDatabase.CreateAsset(clip, assetPath);
                        result.Add(clip);
                    }
                    else
                    {
                        EditorUtility.CopySerialized(clip, existingClip);
                        existingClip.name = name;
                        EditorUtility.SetDirty(existingClip);
                        result.Add(existingClip);
                        UnityEngine.Object.DestroyImmediate(clip);
                    }
                }
            }
            finally
            {
                AssetDatabase.StopAssetEditing();
            }
            AssetDatabase.SaveAssets();
            bool slimmed = false;
            foreach (AnimationClip saved in result)
                slimmed |= EndfieldAnimationClipSlimmer.StripEditorCurves(saved);
            if (slimmed)
                AssetDatabase.SaveAssets();
            return result;
        }

        private static void AddOverviewHandoffReferenceCurves(
            AnimationClip clip,
            Dictionary<string, object> loopInfo,
            Dictionary<string, Dictionary<string, object>> clipInfoByName,
            GameObject root,
            float sourceDuration)
        {
            if (clip == null || loopInfo == null || root == null)
                return;
            string loopName = Str(loopInfo.TryGetValue("name", out object nameObj) ? nameObj : null);
            const string LoopToken = "_overview_loop_";
            const string TerminalLoopToken = "_overview_loop";
            int loopTokenIndex = loopName.IndexOf(LoopToken, StringComparison.OrdinalIgnoreCase);
            string startName;
            if (loopTokenIndex >= 0)
            {
                startName = loopName.Substring(0, loopTokenIndex) +
                    "_overview_start_" +
                    loopName.Substring(loopTokenIndex + LoopToken.Length);
            }
            else if (loopName.EndsWith(TerminalLoopToken, StringComparison.OrdinalIgnoreCase))
            {
                startName = loopName.Substring(0, loopName.Length - TerminalLoopToken.Length) +
                    "_overview_start";
            }
            else
            {
                return;
            }
            if (!clipInfoByName.TryGetValue(startName, out Dictionary<string, object> startInfo))
                return;

            var loopBones = new Dictionary<string, Dictionary<string, object>>(StringComparer.Ordinal);
            foreach (object boneObj in List(loopInfo.TryGetValue("bones", out object loopBonesObj) ? loopBonesObj : null))
            {
                var bone = Dict(boneObj);
                string path = Str(bone.TryGetValue("path", out object pathObj) ? pathObj : null);
                if (path.Length > 0)
                    loopBones[path] = bone;
            }

            float endTime = Mathf.Max(sourceDuration, 1f / Mathf.Max(1f, clip.frameRate));
            foreach (object boneObj in List(startInfo.TryGetValue("bones", out object startBonesObj) ? startBonesObj : null))
            {
                var startBone = Dict(boneObj);
                string path = Str(startBone.TryGetValue("path", out object pathObj) ? pathObj : null);
                if (path.Length == 0)
                    continue;
                loopBones.TryGetValue(path, out Dictionary<string, object> loopBone);
                Transform transform = root.transform.Find(path);
                if (transform == null)
                    continue;

                bool startPosition = Bool(startBone.TryGetValue("pos_animated", out object startPosObj) ? startPosObj : false);
                bool loopPosition = loopBone != null && Bool(loopBone.TryGetValue("pos_animated", out object loopPosObj) ? loopPosObj : false);
                if (startPosition && !loopPosition)
                {
                    Vector3 value = transform.localPosition;
                    SetConstantCurve(clip, path, "m_LocalPosition.x", value.x, endTime);
                    SetConstantCurve(clip, path, "m_LocalPosition.y", value.y, endTime);
                    SetConstantCurve(clip, path, "m_LocalPosition.z", value.z, endTime);
                }

                bool startRotation = Bool(startBone.TryGetValue("rot_animated", out object startRotObj) ? startRotObj : false);
                bool loopRotation = loopBone != null && Bool(loopBone.TryGetValue("rot_animated", out object loopRotObj) ? loopRotObj : false);
                if (startRotation && !loopRotation)
                {
                    Quaternion value = transform.localRotation;
                    SetConstantCurve(clip, path, "m_LocalRotation.x", value.x, endTime);
                    SetConstantCurve(clip, path, "m_LocalRotation.y", value.y, endTime);
                    SetConstantCurve(clip, path, "m_LocalRotation.z", value.z, endTime);
                    SetConstantCurve(clip, path, "m_LocalRotation.w", value.w, endTime);
                }

                bool startScale = Bool(startBone.TryGetValue("scale_animated", out object startScaleObj) ? startScaleObj : false);
                bool loopScale = loopBone != null && Bool(loopBone.TryGetValue("scale_animated", out object loopScaleObj) ? loopScaleObj : false);
                if (startScale && !loopScale)
                {
                    Vector3 value = transform.localScale;
                    SetConstantCurve(clip, path, "m_LocalScale.x", value.x, endTime);
                    SetConstantCurve(clip, path, "m_LocalScale.y", value.y, endTime);
                    SetConstantCurve(clip, path, "m_LocalScale.z", value.z, endTime);
                }
            }
        }

        private static void SetConstantCurve(
            AnimationClip clip,
            string path,
            string property,
            float value,
            float endTime)
        {
            SetCurve(
                clip,
                path,
                property,
                new AnimationCurve(
                    new Keyframe(0f, value),
                    new Keyframe(endTime, value)));
        }

        private static List<AnimationClip> LoadExistingAnimationClips(string actorGeneratedRoot)
        {
            var clips = new List<AnimationClip>();
            string animationRoot = $"{actorGeneratedRoot}/Animations";
            if (!Directory.Exists(Path.Combine(Directory.GetCurrentDirectory(), animationRoot)))
                return clips;

            foreach (string guid in AssetDatabase.FindAssets("t:AnimationClip", new[] { animationRoot }))
            {
                string assetPath = AssetDatabase.GUIDToAssetPath(guid);
                var clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(assetPath);
                // Animator-ready copies live below Animations/Animator and
                // must never be fed back into the Legacy Animation component
                // on a targeted cached-asset refresh.
                if (clip != null && clip.legacy &&
                    assetPath.IndexOf("/Animations/Animator/", StringComparison.OrdinalIgnoreCase) < 0)
                    clips.Add(clip);
            }
            clips.Sort((a, b) => string.Compare(a.name, b.name, StringComparison.OrdinalIgnoreCase));
            Debug.Log($"Loaded {clips.Count} cached animation clips from {animationRoot}.");
            return clips;
        }

        private static void AddTransformCurves(
            AnimationClip clip,
            string path,
            int trackIndex,
            IList frames,
            bool posAnimated,
            bool rotAnimated,
            bool scaleAnimated,
            int previewStride,
            bool loop,
            float sourceDuration)
        {
            var px = new AnimationCurve();
            var py = new AnimationCurve();
            var pz = new AnimationCurve();
            var qx = new AnimationCurve();
            var qy = new AnimationCurve();
            var qz = new AnimationCurve();
            var qw = new AnimationCurve();
            var sx = new AnimationCurve();
            var sy = new AnimationCurve();
            var sz = new AnimationCurve();

            for (int frameIndex = 0; frameIndex < frames.Count; frameIndex++)
            {
                if (frameIndex % previewStride != 0 && frameIndex != frames.Count - 1)
                    continue;
                object frameObj = frames[frameIndex];
                var frame = Dict(frameObj);
                float time = Float(frame["time"]);
                var tracks = List(frame["tracks"]);
                if (trackIndex >= tracks.Count)
                    continue;
                var track = Dict(tracks[trackIndex]);
                if (posAnimated)
                {
                    Vector3 pos = Vec3(List(track["translation"]));
                    px.AddKey(time, pos.x);
                    py.AddKey(time, pos.y);
                    pz.AddKey(time, pos.z);
                }
                if (rotAnimated)
                {
                    Quaternion rot = Quat(List(track["rotation"]));
                    qx.AddKey(time, rot.x);
                    qy.AddKey(time, rot.y);
                    qz.AddKey(time, rot.z);
                    qw.AddKey(time, rot.w);
                }
                if (scaleAnimated)
                {
                    IList scaleValues = List(track.TryGetValue("scale", out object scaleObj) ? scaleObj : null);
                    Vector3 scale = scaleValues.Count >= 3 ? Vec3(scaleValues) : Vector3.one;
                    sx.AddKey(time, scale.x);
                    sy.AddKey(time, scale.y);
                    sz.AddKey(time, scale.z);
                }
            }

            // ACL clips can encode N distinct loop samples over an N / sample-rate
            // duration without storing a duplicate endpoint. Unity otherwise uses
            // the final key time, (N - 1) / sample-rate, as the clip length and
            // loops one frame early. Runtime capture confirms this distinction for
            // Wulfa's overview loop: 140 samples recur every 140 rendered frames.
            // Add the first sample at the authoritative source duration so Unity
            // preserves both the final-to-first interval and the original period.
            if (loop && sourceDuration > 0f && frames.Count > 0)
            {
                var lastFrame = Dict(frames[frames.Count - 1]);
                float lastTime = Float(lastFrame["time"]);
                if (sourceDuration > lastTime + 0.00001f)
                {
                    var firstFrame = Dict(frames[0]);
                    var firstTracks = List(firstFrame["tracks"]);
                    if (trackIndex < firstTracks.Count)
                    {
                        var firstTrack = Dict(firstTracks[trackIndex]);
                        if (posAnimated)
                        {
                            Vector3 pos = Vec3(List(firstTrack["translation"]));
                            px.AddKey(sourceDuration, pos.x);
                            py.AddKey(sourceDuration, pos.y);
                            pz.AddKey(sourceDuration, pos.z);
                        }
                        if (rotAnimated)
                        {
                            Quaternion rot = Quat(List(firstTrack["rotation"]));
                            qx.AddKey(sourceDuration, rot.x);
                            qy.AddKey(sourceDuration, rot.y);
                            qz.AddKey(sourceDuration, rot.z);
                            qw.AddKey(sourceDuration, rot.w);
                        }
                        if (scaleAnimated)
                        {
                            IList scaleValues = List(firstTrack.TryGetValue("scale", out object scaleObj) ? scaleObj : null);
                            Vector3 scale = scaleValues.Count >= 3 ? Vec3(scaleValues) : Vector3.one;
                            sx.AddKey(sourceDuration, scale.x);
                            sy.AddKey(sourceDuration, scale.y);
                            sz.AddKey(sourceDuration, scale.z);
                        }
                    }
                }
            }

            if (posAnimated)
            {
                SetCurve(clip, path, "m_LocalPosition.x", px);
                SetCurve(clip, path, "m_LocalPosition.y", py);
                SetCurve(clip, path, "m_LocalPosition.z", pz);
            }
            if (rotAnimated)
            {
                SetCurve(clip, path, "m_LocalRotation.x", qx);
                SetCurve(clip, path, "m_LocalRotation.y", qy);
                SetCurve(clip, path, "m_LocalRotation.z", qz);
                SetCurve(clip, path, "m_LocalRotation.w", qw);
            }
            if (scaleAnimated)
            {
                SetCurve(clip, path, "m_LocalScale.x", sx);
                SetCurve(clip, path, "m_LocalScale.y", sy);
                SetCurve(clip, path, "m_LocalScale.z", sz);
            }
        }

        private static void AddGameObjectActiveCurves(AnimationClip clip, IList curves)
        {
            foreach (object curveObj in curves)
            {
                var curveInfo = Dict(curveObj);
                string path = Str(curveInfo.TryGetValue("path", out object pathObj) ? pathObj : null);
                string property = Str(
                    curveInfo.TryGetValue("property", out object propertyObj) ? propertyObj : null);
                if (path.Length == 0 ||
                    !string.Equals(property, "m_IsActive", StringComparison.Ordinal))
                {
                    continue;
                }
                var activeCurve = new AnimationCurve();
                foreach (object keyObj in List(curveInfo["keys"]))
                {
                    var key = Dict(keyObj);
                    activeCurve.AddKey(
                        Float(key.TryGetValue("time", out object timeObj) ? timeObj : null),
                        Float(key.TryGetValue("value", out object valueObj) ? valueObj : null) >= 0.5f
                            ? 1f
                            : 0f);
                }
                if (activeCurve.length == 0)
                    continue;
                for (int index = 0; index < activeCurve.keys.Length; index++)
                {
                    AnimationUtility.SetKeyLeftTangentMode(
                        activeCurve,
                        index,
                        AnimationUtility.TangentMode.Constant);
                    AnimationUtility.SetKeyRightTangentMode(
                        activeCurve,
                        index,
                        AnimationUtility.TangentMode.Constant);
                }
                AnimationUtility.SetEditorCurve(
                    clip,
                    EditorCurveBinding.FloatCurve(
                        path,
                        typeof(GameObject),
                        "m_IsActive"),
                    activeCurve);
            }
        }

        private static void AddRendererMaterialFloatCurves(
            AnimationClip clip,
            IList curves)
        {
            foreach (object curveObj in curves)
            {
                var curveInfo = Dict(curveObj);
                string path = Str(
                    curveInfo.TryGetValue("path", out object pathObj)
                        ? pathObj
                        : null);
                string property = Str(
                    curveInfo.TryGetValue("property", out object propertyObj)
                        ? propertyObj
                        : null);
                if (path.Length == 0 ||
                    !property.StartsWith("material._", StringComparison.Ordinal))
                {
                    continue;
                }

                var materialCurve = new AnimationCurve();
                foreach (object keyObj in List(
                    curveInfo.TryGetValue("keys", out object keysObj)
                        ? keysObj
                        : null))
                {
                    var key = Dict(keyObj);
                    float time = Float(
                        key.TryGetValue("time", out object timeObj)
                            ? timeObj
                            : null);
                    float value = Float(
                        key.TryGetValue("value", out object valueObj)
                            ? valueObj
                            : null);
                    if (!float.IsNaN(time) && !float.IsInfinity(time) &&
                        !float.IsNaN(value) && !float.IsInfinity(value))
                    {
                        materialCurve.AddKey(time, value);
                    }
                }
                if (materialCurve.length == 0)
                    continue;
                for (int index = 0; index < materialCurve.keys.Length; index++)
                {
                    AnimationUtility.SetKeyLeftTangentMode(
                        materialCurve,
                        index,
                        AnimationUtility.TangentMode.Linear);
                    AnimationUtility.SetKeyRightTangentMode(
                        materialCurve,
                        index,
                        AnimationUtility.TangentMode.Linear);
                }
                AnimationUtility.SetEditorCurve(
                    clip,
                    EditorCurveBinding.FloatCurve(
                        path,
                        typeof(SkinnedMeshRenderer),
                        property),
                    materialCurve);
            }
        }

        private static void ConfigureAnimation(GameObject root, List<AnimationClip> clips, string displayName, string[] previewPreference)
        {
            var animation = root.GetComponent<Animation>();
            if (animation == null)
                animation = root.AddComponent<Animation>();
            var layerSync = root.GetComponent<CharacterAnimationLayerSync>();
            if (layerSync == null)
                layerSync = root.AddComponent<CharacterAnimationLayerSync>();
            layerSync.animationSource = animation;
            if (root.GetComponent<CharacterAnimationReferencePose>() == null)
                root.AddComponent<CharacterAnimationReferencePose>();
            foreach (AnimationClip clip in clips)
                animation.AddClip(clip, clip.name);
            if (clips.Count > 0)
            {
                AnimationClip selectedPreviewClip = SelectPreviewClip(clips, previewPreference);
                animation.clip = selectedPreviewClip;
                animation.playAutomatically = selectedPreviewClip != null;
                Debug.Log($"Configured {displayName} preview animation: {selectedPreviewClip?.name ?? "<none>"}");
            }

            var rig = root.GetComponent<CharacterRecoveryRig>();
            if (rig == null)
                rig = root.AddComponent<CharacterRecoveryRig>();
            rig.displayName = displayName;
            rig.animationSource = animation;
            rig.focusTarget = root.transform;
        }

        private static AnimatorController BuildRecoveredOverviewAnimatorController(
            string actorGeneratedRoot,
            AnimationClip legacyStart,
            AnimationClip legacyLoop,
            EndfieldOverviewPlayback playback)
        {
            if (legacyStart == null || legacyLoop == null || playback == null)
                throw new InvalidDataException("Recovered Overview Animator inputs are incomplete.");
            if (playback.transitionDurationFixed ||
                !Mathf.Approximately(playback.entryNormalizedOffset, 0.0058366423f) ||
                !Mathf.Approximately(playback.exitNormalizedTime, 0.75f) ||
                !Mathf.Approximately(playback.normalizedTransitionDuration, 0.25f) ||
                !Mathf.Approximately(playback.destinationNormalizedOffset, 0f) ||
                playback.interruptionSource != 2 || !playback.orderedInterruption ||
                !playback.blendRootMotion)
            {
                throw new InvalidDataException(
                    "Endminf Overview Animator values differ from the recovered controller contract.");
            }

            string animatorFolder = actorGeneratedRoot + "/Animations/Animator";
            EnsureAssetFolder(animatorFolder);
            AnimationClip start = SaveAnimatorClipCopy(
                legacyStart, animatorFolder + "/" + Safe(legacyStart.name) + ".anim", false);
            AnimationClip loop = SaveAnimatorClipCopy(
                legacyLoop, animatorFolder + "/" + Safe(legacyLoop.name) + ".anim", true);
            string controllerPath = animatorFolder + "/EndminfOverview.controller";
            AnimatorController controller = AssetDatabase.LoadAssetAtPath<AnimatorController>(controllerPath);
            if (controller == null)
                controller = AnimatorController.CreateAnimatorControllerAtPath(controllerPath);
            if (controller.layers.Length == 0)
                controller.AddLayer("Base Layer");
            if (controller.layers.Length != 1)
                throw new InvalidDataException(
                    $"Recovered Overview Animator requires exactly one layer; found {controller.layers.Length}.");

            for (int index = controller.parameters.Length - 1; index >= 0; index--)
                controller.RemoveParameter(index);
            controller.AddParameter("FromIndex", AnimatorControllerParameterType.Int);
            controller.AddParameter("ToIndex", AnimatorControllerParameterType.Int);
            controller.AddParameter("EnableSwitch", AnimatorControllerParameterType.Trigger);

            AnimatorStateMachine root = controller.layers[0].stateMachine;
            foreach (ChildAnimatorState child in root.states.ToArray())
                root.RemoveState(child.state);
            foreach (ChildAnimatorStateMachine child in root.stateMachines.ToArray())
                root.RemoveStateMachine(child.stateMachine);
            foreach (AnimatorStateTransition transition in root.anyStateTransitions.ToArray())
                root.RemoveAnyStateTransition(transition);

            AnimatorState waiting = root.AddState("AwaitOverview");
            waiting.writeDefaultValues = true;
            root.defaultState = waiting;
            AnimatorStateMachine overview = root.AddStateMachine("Overview");
            AnimatorState entrance = overview.AddState("FromOveview");
            entrance.motion = start;
            entrance.speed = 1f;
            entrance.mirror = false;
            entrance.iKOnFeet = false;
            entrance.writeDefaultValues = true;
            AnimatorState settled = overview.AddState("OverviewIdle");
            settled.motion = loop;
            settled.speed = 1f;
            settled.mirror = false;
            settled.iKOnFeet = false;
            settled.writeDefaultValues = true;

            AnimatorStateTransition handoff = entrance.AddTransition(settled);
            handoff.hasExitTime = true;
            handoff.exitTime = playback.exitNormalizedTime;
            handoff.hasFixedDuration = false;
            handoff.duration = playback.normalizedTransitionDuration;
            handoff.offset = playback.destinationNormalizedOffset;
            handoff.interruptionSource = TransitionInterruptionSource.SourceThenDestination;
            handoff.orderedInterruption = true;
            handoff.canTransitionToSelf = true;

            AnimatorStateTransition entry = root.AddAnyStateTransition(entrance);
            entry.hasExitTime = false;
            entry.hasFixedDuration = true;
            entry.duration = 0f;
            entry.offset = playback.entryNormalizedOffset;
            entry.canTransitionToSelf = true;
            entry.orderedInterruption = true;
            entry.AddCondition(AnimatorConditionMode.Equals, 0f, "FromIndex");
            entry.AddCondition(AnimatorConditionMode.Equals, 0f, "ToIndex");
            entry.AddCondition(AnimatorConditionMode.If, 0f, "EnableSwitch");

            EditorUtility.SetDirty(controller);
            AssetDatabase.SaveAssets();
            ValidateRecoveredOverviewAnimatorController(controller, start, loop, playback);
            return controller;
        }

        private static AnimationClip SaveAnimatorClipCopy(
            AnimationClip source,
            string assetPath,
            bool loop)
        {
            AnimationClip saved = AssetDatabase.LoadAssetAtPath<AnimationClip>(assetPath);
            AnimationClip rebuilt = new AnimationClip();
            EditorUtility.CopySerialized(source, rebuilt);
            rebuilt.name = source.name;
            rebuilt.legacy = false;
            rebuilt.wrapMode = loop ? WrapMode.Loop : WrapMode.Once;
            ApplyClipLoopSettings(rebuilt, loop, false);
            if (saved == null)
            {
                AssetDatabase.CreateAsset(rebuilt, assetPath);
                return rebuilt;
            }
            EditorUtility.CopySerialized(rebuilt, saved);
            saved.name = source.name;
            saved.legacy = false;
            EditorUtility.SetDirty(saved);
            UnityEngine.Object.DestroyImmediate(rebuilt);
            return saved;
        }

        private static void ValidateRecoveredOverviewAnimatorController(
            AnimatorController controller,
            AnimationClip start,
            AnimationClip loop,
            EndfieldOverviewPlayback playback)
        {
            if (controller == null || start == null || loop == null ||
                start.legacy || loop.legacy || controller.layers.Length != 1)
                throw new InvalidDataException("Generated Overview Animator assets are incomplete.");
            AnimatorStateMachine root = controller.layers[0].stateMachine;
            AnimatorStateMachine overview = root.stateMachines
                .Select(value => value.stateMachine)
                .SingleOrDefault(value => value != null && value.name == "Overview");
            AnimatorState entrance = overview == null ? null : overview.states
                .Select(value => value.state)
                .SingleOrDefault(value => value != null && value.name == "FromOveview");
            AnimatorState settled = overview == null ? null : overview.states
                .Select(value => value.state)
                .SingleOrDefault(value => value != null && value.name == "OverviewIdle");
            AnimatorStateTransition handoff = entrance == null
                ? null
                : entrance.transitions.SingleOrDefault();
            if (entrance == null || settled == null || entrance.motion != start || settled.motion != loop ||
                !entrance.writeDefaultValues || !settled.writeDefaultValues || handoff == null ||
                handoff.destinationState != settled || !handoff.hasExitTime || handoff.hasFixedDuration ||
                !Mathf.Approximately(handoff.exitTime, playback.exitNormalizedTime) ||
                !Mathf.Approximately(handoff.duration, playback.normalizedTransitionDuration) ||
                handoff.interruptionSource != TransitionInterruptionSource.SourceThenDestination ||
                !handoff.orderedInterruption)
            {
                throw new InvalidDataException("Generated Overview Animator state contract drifted.");
            }
            AnimatorStateTransition entry = root.anyStateTransitions.SingleOrDefault();
            if (entry == null || entry.destinationState != entrance || entry.hasExitTime ||
                !entry.hasFixedDuration || !Mathf.Approximately(entry.duration, 0f) ||
                !Mathf.Approximately(entry.offset, playback.entryNormalizedOffset) ||
                entry.conditions.Length != 3)
                throw new InvalidDataException("Generated Overview Animator entry contract drifted.");
        }

        private static void ConfigureRecoveredOverviewPlayback(
            GameObject root,
            Dictionary<string, object> manifest,
            string actorGeneratedRoot)
        {
            if (root == null || manifest == null)
                return;

            var overview = Dict(
                manifest.TryGetValue("overview_playback", out object overviewObj)
                    ? overviewObj
                    : null);
            if (overview.Count == 0)
                return;

            Animation animation = root.GetComponent<Animation>();
            string startClip = Str(
                overview.TryGetValue("start_clip", out object startClipObj)
                    ? startClipObj
                    : null);
            string loopClip = Str(
                overview.TryGetValue("loop_clip", out object loopClipObj)
                    ? loopClipObj
                    : null);
            if (animation == null || startClip.Length == 0 || loopClip.Length == 0 ||
                animation[startClip] == null || animation[loopClip] == null)
            {
                Debug.LogWarning(
                    $"Skipping recovered overview playback with missing body clips on {root.name}: " +
                    $"start={startClip} loop={loopClip}",
                    root);
                return;
            }

            EndfieldOverviewPlayback playback = EnsureComponent<EndfieldOverviewPlayback>(root);
            playback.animationSource = animation;
            playback.startClip = startClip;
            playback.loopClip = loopClip;
            playback.playOnEnable = overview.TryGetValue("play_on_enable", out object playOnEnableObj)
                ? Bool(playOnEnableObj)
                : playback.playOnEnable;
            playback.entryNormalizedOffset = Float(
                overview.TryGetValue("entry_normalized_offset", out object entryOffsetObj)
                    ? entryOffsetObj
                    : null,
                playback.entryNormalizedOffset);
            playback.exitNormalizedTime = Float(
                overview.TryGetValue("exit_normalized_time", out object exitTimeObj)
                    ? exitTimeObj
                    : null,
                playback.exitNormalizedTime);
            playback.normalizedTransitionDuration = Float(
                overview.TryGetValue("normalized_transition_duration", out object transitionDurationObj)
                    ? transitionDurationObj
                    : null,
                playback.normalizedTransitionDuration);
            playback.transitionDurationFixed = Bool(
                overview.TryGetValue("transition_duration_fixed", out object transitionFixedObj)
                    ? transitionFixedObj
                    : false);
            playback.destinationNormalizedOffset = Float(
                overview.TryGetValue("destination_normalized_offset", out object destinationOffsetObj)
                    ? destinationOffsetObj
                    : null,
                0f);
            playback.interruptionSource = Int(
                overview.TryGetValue("interruption_source", out object interruptionSourceObj)
                    ? interruptionSourceObj
                    : null,
                playback.interruptionSource);
            playback.orderedInterruption = overview.TryGetValue(
                "ordered_interruption", out object orderedInterruptionObj)
                    ? Bool(orderedInterruptionObj)
                    : playback.orderedInterruption;
            playback.blendRootMotion = overview.TryGetValue(
                "blend_root_motion", out object blendRootMotionObj)
                    ? Bool(blendRootMotionObj)
                    : playback.blendRootMotion;
            var entryConditions = new List<EndfieldOverviewTransitionCondition>();
            foreach (object conditionObj in List(
                overview.TryGetValue("entry_transition_conditions", out object entryConditionsObj)
                    ? entryConditionsObj
                    : null))
            {
                var condition = Dict(conditionObj);
                entryConditions.Add(new EndfieldOverviewTransitionCondition
                {
                    mode = Int(
                        condition.TryGetValue("mode", out object conditionModeObj)
                            ? conditionModeObj
                            : null),
                    parameter = Str(
                        condition.TryGetValue("parameter", out object conditionParameterObj)
                            ? conditionParameterObj
                            : null),
                    threshold = Float(
                        condition.TryGetValue("threshold", out object conditionThresholdObj)
                            ? conditionThresholdObj
                            : null,
                        0f),
                });
            }
            playback.entryTransitionConditions = entryConditions.ToArray();

            string characterId = Str(
                manifest.TryGetValue("character_id", out object characterIdObj)
                    ? characterIdObj
                    : null);
            if (string.Equals(characterId, "chr_0003_endminf", StringComparison.Ordinal))
            {
                AnimatorController controller = BuildRecoveredOverviewAnimatorController(
                    actorGeneratedRoot,
                    animation[startClip].clip,
                    animation[loopClip].clip,
                    playback);
                Animator animator = EnsureComponent<Animator>(root);
                animator.runtimeAnimatorController = controller;
                // The retail controller records m_EnableBlendRootMotion=true
                // on both transitions. Stock Unity 2022.3 has no serialized
                // per-transition field, so the closest supported execution
                // boundary is the Animator-level root-motion path.
                // This enables AnimatorMove delivery. The runtime component
                // consumes deltaRotation only, matching the pinned native
                // callback, and deliberately ignores deltaPosition.
                animator.applyRootMotion = playback.blendRootMotion;
                animator.cullingMode = AnimatorCullingMode.AlwaysAnimate;
                animator.updateMode = AnimatorUpdateMode.Normal;
                animator.enabled = false;
                playback.animatorSource = animator;
                playback.requireAnimatorContract = true;
                playback.animatorStartStatePath = "Base Layer.Overview.FromOveview";
                playback.animatorLoopStatePath = "Base Layer.Overview.OverviewIdle";
                EditorUtility.SetDirty(animator);
            }
            playback.weaponHide = Float(
                overview.TryGetValue("weapon_hide", out object weaponHideObj)
                    ? weaponHideObj
                    : null,
                playback.weaponHide);
            playback.magicaClothWeight = Float(
                overview.TryGetValue("magica_cloth_weight", out object clothWeightObj)
                    ? clothWeightObj
                    : null,
                playback.magicaClothWeight);
            playback.staticWeaponHide = Float(
                overview.TryGetValue("static_weapon_hide", out object staticWeaponHideObj)
                    ? staticWeaponHideObj
                    : null,
                playback.staticWeaponHide);

            var weaponVisibility = Dict(
                overview.TryGetValue("weapon_visibility", out object weaponVisibilityObj)
                    ? weaponVisibilityObj
                    : null);
            var weaponRenderers = new List<Renderer>();
            foreach (object rendererPathObj in List(
                weaponVisibility.TryGetValue("renderer_paths", out object rendererPathsObj)
                    ? rendererPathsObj
                    : null))
            {
                string rendererPath = Str(rendererPathObj);
                Transform rendererTransform = rendererPath.Length > 0
                    ? root.transform.Find(rendererPath)
                    : null;
                Renderer renderer = rendererTransform != null
                    ? rendererTransform.GetComponent<Renderer>()
                    : null;
                if (renderer == null)
                {
                    Debug.LogWarning(
                        $"Recovered Overview weapon renderer path is missing on {root.name}: {rendererPath}",
                        root);
                    continue;
                }
                weaponRenderers.Add(renderer);
            }
            EndfieldOverviewRendererVisibility rendererVisibility =
                root.GetComponent<EndfieldOverviewRendererVisibility>();
            if (weaponRenderers.Count > 0)
            {
                rendererVisibility = EnsureComponent<EndfieldOverviewRendererVisibility>(root);
                rendererVisibility.weaponRenderers = weaponRenderers.ToArray();
                rendererVisibility.hiddenAtOrAbove = Float(
                    weaponVisibility.TryGetValue("hidden_at_or_above", out object hideThresholdObj)
                        ? hideThresholdObj
                        : null,
                    0.5f);
                EditorUtility.SetDirty(rendererVisibility);
            }
            else if (rendererVisibility != null)
            {
                UnityEngine.Object.DestroyImmediate(rendererVisibility);
            }

            var itemWidgets = new List<EndfieldOverviewItemWidgetBinding>();
            foreach (object widgetObj in List(
                overview.TryGetValue("item_widgets", out object itemWidgetsObj)
                    ? itemWidgetsObj
                    : null))
            {
                var widget = Dict(widgetObj);
                string propPath = Str(
                    widget.TryGetValue("prop_path", out object propPathObj)
                        ? propPathObj
                        : null);
                string widgetStartClip = Str(
                    widget.TryGetValue("start_clip", out object widgetStartClipObj)
                        ? widgetStartClipObj
                        : null);
                string widgetLoopClip = Str(
                    widget.TryGetValue("loop_clip", out object widgetLoopClipObj)
                        ? widgetLoopClipObj
                        : null);
                string widgetPostTransitionClip = Str(
                    widget.TryGetValue("post_transition_clip", out object widgetPostTransitionClipObj)
                        ? widgetPostTransitionClipObj
                        : null);
                if (propPath.Length == 0 && widgetStartClip.Length == 0 && widgetLoopClip.Length == 0 &&
                    widgetPostTransitionClip.Length == 0)
                    continue;

                itemWidgets.Add(new EndfieldOverviewItemWidgetBinding
                {
                    propPath = propPath,
                    startClip = widgetStartClip,
                    loopClip = widgetLoopClip,
                    postTransitionClip = widgetPostTransitionClip,
                    hideAfterTransition = Bool(
                        widget.TryGetValue("hide_after_transition", out object hideWidgetObj)
                            ? hideWidgetObj
                            : false),
                    activationEvidence = Str(
                        widget.TryGetValue("activation_evidence", out object activationEvidenceObj)
                            ? activationEvidenceObj
                            : null),
                });
            }
            playback.itemWidgets = itemWidgets.ToArray();

            // Retain the old single-companion fields as a serialized fallback.
            // The runtime prefers itemWidgets whenever this array is non-empty.
            if (itemWidgets.Count > 0)
            {
                EndfieldOverviewItemWidgetBinding firstWidget = itemWidgets[0];
                playback.entranceCompanionClip = firstWidget.startClip;
                playback.entranceCompanionPropPath = firstWidget.propPath;
                playback.hideEntranceCompanionAfterTransition = firstWidget.hideAfterTransition;
            }
            else
            {
                playback.entranceCompanionClip = "";
                playback.entranceCompanionPropPath = "";
                playback.hideEntranceCompanionAfterTransition = false;
            }

            var entranceEffects = new List<EndfieldOverviewEffectRequest>();
            foreach (object effectObj in List(
                overview.TryGetValue("entrance_effects", out object entranceEffectsObj)
                    ? entranceEffectsObj
                    : null))
            {
                var effect = Dict(effectObj);
                string prefabName = Str(
                    effect.TryGetValue("prefab_name", out object prefabNameObj)
                        ? prefabNameObj
                        : null);
                if (prefabName.Length == 0)
                    continue;
                entranceEffects.Add(new EndfieldOverviewEffectRequest
                {
                    prefabName = prefabName,
                    mountPoint = Str(
                        effect.TryGetValue("mount_point", out object mountPointObj)
                            ? mountPointObj
                            : null),
                    finishWhenExit = effect.TryGetValue("finish_when_exit", out object finishExitObj)
                        ? Bool(finishExitObj)
                        : true,
                    finishWhenTransition = effect.TryGetValue(
                        "finish_when_transition", out object finishTransitionObj)
                            ? Bool(finishTransitionObj)
                            : false,
                });
            }
            playback.entranceEffects = entranceEffects.ToArray();
            EditorUtility.SetDirty(playback);
        }

        private static EndfieldOverviewEffectRequest OverviewEffect(
            string prefabName,
            string mountPoint = "")
        {
            return new EndfieldOverviewEffectRequest
            {
                prefabName = prefabName,
                mountPoint = mountPoint,
                finishWhenExit = true,
                finishWhenTransition = false,
            };
        }

        private static void ConfigureClipMetadata(GameObject root, IList clips)
        {
            var rig = root.GetComponent<CharacterRecoveryRig>();
            if (rig == null)
                return;

            var metadata = new List<CharacterRecoveryClipMetadata>();
            foreach (object clipObj in clips)
            {
                var clipInfo = Dict(clipObj);
                string name = Str(clipInfo.TryGetValue("name", out object nameObj) ? nameObj : null);
                if (name.Length == 0)
                    continue;

                bool helper = false;
                string clipClass = Str(clipInfo.TryGetValue("clip_class", out object clipClassObj) ? clipClassObj : null);
                string clipCategory = Str(clipInfo.TryGetValue("clip_category", out object clipCategoryObj) ? clipCategoryObj : null, clipClass);
                string layerRole = Str(clipInfo.TryGetValue("layer_role", out object layerRoleObj) ? layerRoleObj : null);
                string widgetPropPath = Str(clipInfo.TryGetValue("widget_prop_path", out object widgetPropPathObj) ? widgetPropPathObj : null);
                string autoHelperClip = Str(clipInfo.TryGetValue("auto_helper_clip", out object autoHelperObj) ? autoHelperObj : null);
                string combinationNote = Str(clipInfo.TryGetValue("combination_note", out object comboNoteObj) ? comboNoteObj : null);
                string bindingEvidence = Str(clipInfo.TryGetValue("binding_evidence", out object bindingObj) ? bindingObj : null);
                bool standaloneCandidate = !clipInfo.TryGetValue("standalone_candidate", out object standaloneObj) || Bool(standaloneObj);
                var notes = new List<string>();
                foreach (object item in List(clipInfo.TryGetValue("requires_extra_items", out object extraObj) ? extraObj : null))
                {
                    string note = Str(item);
                    if (note.Length == 0)
                        continue;
                    notes.Add(note);
                    string key = note.ToLowerInvariant();
                    if (key.Contains("additive helper") || key.Contains("not a standalone"))
                        helper = true;
                }
                string clipClassKey = clipClass.ToLowerInvariant();
                string layerRoleKey = layerRole.ToLowerInvariant();
                helper = helper
                    || clipClassKey == "helper"
                    || clipClassKey == "additive"
                    || layerRoleKey == "controller_helper"
                    || layerRoleKey == "additive_overlay";
                string searchText = string.Join(
                    " ",
                    new[]
                    {
                        name,
                        clipClass,
                        clipCategory,
                        layerRole,
                        widgetPropPath,
                        autoHelperClip,
                        combinationNote,
                        bindingEvidence,
                        string.Join(" ", notes.ToArray()),
                    });

                metadata.Add(new CharacterRecoveryClipMetadata
                {
                    name = name,
                    clipClass = clipClass,
                    clipCategory = clipCategory,
                    layerRole = layerRole,
                    standaloneCandidate = standaloneCandidate,
                    helperOrAdditive = helper,
                    widgetPropPath = widgetPropPath,
                    autoHelperClip = autoHelperClip,
                    combinationNote = combinationNote,
                    note = string.Join("; ", notes),
                    searchText = searchText,
                });
            }
            rig.clipMetadata = metadata.ToArray();
            EditorUtility.SetDirty(rig);
        }

        private static void ConfigureRecoveredStates(GameObject root, IList states)
        {
            var rig = root.GetComponent<CharacterRecoveryRig>();
            var animation = root.GetComponent<Animation>();
            if (rig == null || animation == null)
                return;

            var recovered = new List<CharacterRecoveryState>();
            foreach (object stateObj in states)
            {
                var stateInfo = Dict(stateObj);
                string baseClip = Str(stateInfo.TryGetValue("base_clip", out object baseObj) ? baseObj : null);
                if (baseClip.Length == 0 || animation[baseClip] == null)
                    continue;

                var layers = new List<CharacterRecoveryLayer>();
                foreach (object layerObj in List(stateInfo.TryGetValue("layers", out object layersObj) ? layersObj : null))
                {
                    var layerInfo = Dict(layerObj);
                    string clip = Str(layerInfo.TryGetValue("clip", out object clipObj) ? clipObj : null);
                    if (clip.Length == 0 || clip == baseClip || animation[clip] == null)
                        continue;
                    string blendMode = Str(layerInfo.TryGetValue("blend_mode", out object blendObj) ? blendObj : null).ToLowerInvariant();
                    layers.Add(new CharacterRecoveryLayer
                    {
                        clip = clip,
                        layer = Mathf.Max(1, Int(layerInfo.TryGetValue("layer", out object layerIndexObj) ? layerIndexObj : null, layers.Count + 1)),
                        additive = blendMode != "blend",
                        weight = Mathf.Clamp01(Float(layerInfo.TryGetValue("weight", out object weightObj) ? weightObj : null, 1f)),
                        role = Str(layerInfo.TryGetValue("role", out object roleObj) ? roleObj : null),
                        useControllerLoop = layerInfo.ContainsKey("controller_loop"),
                        controllerLoop = Bool(
                            layerInfo.TryGetValue("controller_loop", out object controllerLoopObj)
                                ? controllerLoopObj
                                : false),
                    });
                }
                if (layers.Count == 0)
                    continue;

                var evidence = new List<string>();
                foreach (object item in List(stateInfo.TryGetValue("evidence_clips", out object evidenceObj) ? evidenceObj : null))
                {
                    string clip = Str(item);
                    if (clip.Length > 0)
                        evidence.Add(clip);
                }
                var visibleProps = new List<string>();
                foreach (object item in List(stateInfo.TryGetValue("visible_props", out object visiblePropsObj) ? visiblePropsObj : null))
                {
                    string path = Str(item);
                    if (path.Length > 0)
                        visibleProps.Add(path);
                }

                recovered.Add(new CharacterRecoveryState
                {
                    label = Str(stateInfo.TryGetValue("label", out object labelObj) ? labelObj : null, baseClip),
                    baseClip = baseClip,
                    source = Str(stateInfo.TryGetValue("source", out object sourceObj) ? sourceObj : null),
                    confidence = Str(stateInfo.TryGetValue("confidence", out object confidenceObj) ? confidenceObj : null),
                    note = Str(stateInfo.TryGetValue("note", out object noteObj) ? noteObj : null),
                    evidenceClips = evidence.ToArray(),
                    visibleProps = visibleProps.ToArray(),
                    layers = layers.ToArray(),
                });
            }

            rig.recoveredStates = recovered.ToArray();
            EditorUtility.SetDirty(rig);
        }

        private static List<GameObject> BuildModelVariants(
            Dictionary<string, object> manifest,
            IList transformManifest,
            Dictionary<string, Material> materialCache,
            List<AnimationClip> clips,
            Dictionary<string, object> ik,
            string[] previewPreference,
            string actorGeneratedRoot)
        {
            var roots = new List<GameObject>();
            if (!manifest.TryGetValue("model_variants", out object variantsObj))
                return roots;

            foreach (object variantObj in List(variantsObj))
            {
                var variant = Dict(variantObj);
                string rootName = Str(variant.TryGetValue("root_name", out object rootNameObj) ? rootNameObj : null, "actor_zhuangfy_variant");
                string displayName = Str(variant.TryGetValue("display_name", out object displayNameObj) ? displayNameObj : null, rootName);
                var root = new GameObject(rootName);
                root.transform.position = variant.TryGetValue("scene_offset", out object offsetObj)
                    ? Vec3(List(offsetObj))
                    : Vector3.zero;
                root.transform.rotation = Quaternion.identity;
                root.transform.localScale = Vector3.one;

                IList variantTransformManifest = HighestQualityTransformManifest(transformManifest);
                var transformsByPath = BuildSkeleton(root.transform, variantTransformManifest);
                var transformsByCrc = new Dictionary<long, Transform>();
                foreach (var transformObj in variantTransformManifest)
                {
                    var item = Dict(transformObj);
                    string path = Str(item["path"]);
                    if (path.Length == 0 || !transformsByPath.TryGetValue(path, out Transform tr))
                        continue;
                    transformsByCrc[Long(item["path_crc"])] = tr;
                }

                var meshObjects = BuildMeshes(root.transform, List(variant["meshes"]), materialCache, transformsByPath, transformsByCrc, actorGeneratedRoot);
                ConfigureAnimation(root, clips, displayName, previewPreference);
                ConfigureClipMetadata(root, List(manifest["clips"]));
                ConfigureRecoveredStates(root, List(manifest.TryGetValue("recovered_states", out object statesObj) ? statesObj : null));
                ConfigureIk(root, transformsByPath, ik);
                root.SetActive(false);
                roots.Add(root);
                PrefabUtility.SaveAsPrefabAsset(root, $"{actorGeneratedRoot}/Prefabs/{Safe(rootName)}.prefab");
                Debug.Log($"Built experimental model variant {displayName}: {meshObjects.Count} skinned meshes.");
            }

            return roots;
        }

        private static AnimationClip SelectPreviewClip(List<AnimationClip> clips)
        {
            return SelectPreviewClip(clips, ZhuangfyPreviewClipPreference);
        }

        private static AnimationClip SelectPreviewClip(List<AnimationClip> clips, string[] previewPreference)
        {
            foreach (string wanted in previewPreference ?? Array.Empty<string>())
            {
                foreach (AnimationClip clip in clips)
                {
                    if (clip != null && clip.name == wanted)
                        return clip;
                }
            }

            var normalizedClips = new Dictionary<string, AnimationClip>(StringComparer.Ordinal);
            foreach (AnimationClip clip in clips)
            {
                if (clip == null)
                    continue;
                string key = NormalizeClipNameForMatch(clip.name);
                if (key.Length > 0 && !normalizedClips.ContainsKey(key))
                    normalizedClips.Add(key, clip);
            }

            foreach (string wanted in previewPreference ?? Array.Empty<string>())
            {
                string key = NormalizeClipNameForMatch(wanted);
                if (key.Length > 0 && normalizedClips.TryGetValue(key, out AnimationClip clip))
                    return clip;
            }

            return previewPreference == null || previewPreference.Length == 0
                ? clips.Count > 0 ? clips[0] : null
                : null;
        }

        private static string NormalizeClipNameForMatch(string name)
        {
            if (string.IsNullOrEmpty(name))
                return string.Empty;
            var builder = new StringBuilder(name.Length);
            foreach (char c in name)
            {
                if (c == '_' || c == '-' || char.IsWhiteSpace(c))
                    continue;
                builder.Append(char.ToLowerInvariant(c));
            }
            return builder.ToString();
        }

        private static void ConfigureIk(GameObject root, Dictionary<string, Transform> bonesByPath, Dictionary<string, object> ik)
        {
            if (ik == null || ik.Count == 0)
                return;

            CharacterProceduralIk component = null;
            if (ik.TryGetValue("left", out object leftObj))
            {
                var left = Dict(leftObj);
                if (component == null)
                    component = EnsureComponent<CharacterProceduralIk>(root);
                component.leftUpper = FindPath(bonesByPath, Str(left["upper"]));
                component.leftForearm = FindPath(bonesByPath, Str(left["forearm"]));
                component.leftHand = FindPath(bonesByPath, Str(left["hand"]));
                component.leftTarget = FindPath(bonesByPath, Str(left["target"]));
            }
            if (ik.TryGetValue("right", out object rightObj))
            {
                var right = Dict(rightObj);
                if (component == null)
                    component = EnsureComponent<CharacterProceduralIk>(root);
                component.rightUpper = FindPath(bonesByPath, Str(right["upper"]));
                component.rightForearm = FindPath(bonesByPath, Str(right["forearm"]));
                component.rightHand = FindPath(bonesByPath, Str(right["hand"]));
                component.rightTarget = FindPath(bonesByPath, Str(right["target"]));
            }
            if (ik.TryGetValue("left_leg", out object leftLegObj))
            {
                var leftLeg = Dict(leftLegObj);
                if (component == null)
                    component = EnsureComponent<CharacterProceduralIk>(root);
                component.leftThigh = FindPath(bonesByPath, Str(leftLeg["upper"]));
                component.leftCalf = FindPath(bonesByPath, Str(leftLeg["forearm"]));
                component.leftFoot = FindPath(bonesByPath, Str(leftLeg["hand"]));
                component.leftFootTarget = FindPath(bonesByPath, Str(leftLeg["target"]));
                component.leftKneeTarget = leftLeg.TryGetValue("pole", out object poleObj) ? FindPath(bonesByPath, Str(poleObj)) : null;
            }
            if (ik.TryGetValue("right_leg", out object rightLegObj))
            {
                var rightLeg = Dict(rightLegObj);
                if (component == null)
                    component = EnsureComponent<CharacterProceduralIk>(root);
                component.rightThigh = FindPath(bonesByPath, Str(rightLeg["upper"]));
                component.rightCalf = FindPath(bonesByPath, Str(rightLeg["forearm"]));
                component.rightFoot = FindPath(bonesByPath, Str(rightLeg["hand"]));
                component.rightFootTarget = FindPath(bonesByPath, Str(rightLeg["target"]));
                component.rightKneeTarget = rightLeg.TryGetValue("pole", out object poleObj) ? FindPath(bonesByPath, Str(poleObj)) : null;
            }
            if (component == null || !component.HasConfiguredChains)
                return;

            // Original postmodels prove that IK_Foot markers are Grounding
            // references, and native code proves their three animation-
            // blackboard weight curves. Retail hands instead take external
            // interaction targets; knee/weapon consumers and the complete
            // terrain, pelvis, pole, and solve policies remain unproven. Older
            // generated prefabs silently ran the
            // lab's guessed 0.65/0.35/0.15 two-bone solve.  Regeneration must
            // migrate those guesses to a fail-closed diagnostic component.
            Dictionary<string, object> runtimeSolver = Dict(
                ik.TryGetValue("runtime_solver", out object runtimeSolverObj)
                    ? runtimeSolverObj
                    : null);
            component.enableLabSolver = runtimeSolver.TryGetValue("default_enabled", out object enabledObj)
                && Bool(enabledObj);
            component.weight = 0f;
            component.handRotationWeight = 0f;
            component.footRotationWeight = 0f;
            component.previewInEditMode = true;
            var rig = root.GetComponent<CharacterRecoveryRig>();
            if (rig != null)
                rig.poseCorrection = component;
        }

        private static void ConfigureScene(GameObject root, List<GameObject> meshes, ViewerSceneLayout layout = null)
        {
            var scene = SceneManager.GetActiveScene();
            if (layout == null)
                SceneManager.MoveGameObjectToScene(root, scene);

            Bounds bounds = new Bounds(Vector3.up, Vector3.one);
            bool hasBounds = false;
            foreach (GameObject go in meshes)
            {
                var renderer = go.GetComponent<Renderer>();
                if (renderer == null)
                    continue;
                if (!hasBounds)
                {
                    bounds = renderer.bounds;
                    hasBounds = true;
                }
                else
                {
                    bounds.Encapsulate(renderer.bounds);
                }
            }

            ConfigurePreviewLighting(scene, layout != null ? layout.LightingRoot : null);

            var cameraObject = CreateSceneObject("MainCamera", layout != null ? layout.Root.transform : null, scene);
            cameraObject.tag = "MainCamera";
            var camera = cameraObject.AddComponent<Camera>();
            FrameCamera(camera, bounds);
            ConfigureReferenceBackdrop(scene, layout != null ? layout.BackdropRoot : null, camera, bounds);
            var controller = cameraObject.AddComponent<CharacterRecoveryCameraController>();
            ConfigureCameraController(controller);
            controller.SetFocus(root.transform, bounds);
            controller.FrameTarget();
            var keyLightObject = FindSceneGameObject("KeyLight");
            ConfigureRecoveredCharacterLighting(
                camera,
                keyLightObject != null ? keyLightObject.GetComponent<Light>() : null);
            ConfigureReferenceBackdrop(scene, layout != null ? layout.BackdropRoot : null, camera, bounds);
            // Saved ordinary viewer scenes carry the source resources for a
            // later explicit selector, but this inert marker does not alter
            // the default SolidColor/backdrop path.
            ConfigureRecoveredCharInfoSky(camera);
        }

        private static void ConfigurePreviewLighting(Scene scene, Transform lightingRoot)
        {
            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = PreviewAmbientColor;
            RenderSettings.skybox = null;
            RenderSettings.defaultReflectionMode = UnityEngine.Rendering.DefaultReflectionMode.Custom;
            RenderSettings.customReflectionTexture = null;

            var fillObject = FindSceneGameObject("FillLight");
            if (fillObject != null)
                UnityEngine.Object.DestroyImmediate(fillObject);

            var keyObject = FindSceneGameObject("KeyLight");
            if (keyObject == null)
                keyObject = CreateSceneObject("KeyLight", lightingRoot, scene);
            else if (lightingRoot != null)
                keyObject.transform.SetParent(lightingRoot, false);

            var key = EnsureComponent<Light>(keyObject);
            key.type = LightType.Directional;
            key.intensity = PreviewKeyIntensity;
            key.color = Color.white;
            key.shadows = LightShadows.Soft;
            key.shadowStrength = 0.9f;
            key.shadowBias = 0.04f;
            key.shadowNormalBias = 0.35f;
            key.shadowNearPlane = 0.1f;
            keyObject.transform.rotation = Quaternion.LookRotation(-PreviewKeyDirectionToLight, Vector3.up);

            var camera = Camera.main ?? UnityEngine.Object.FindObjectOfType<Camera>();
            if (camera != null)
                ConfigureRecoveredCharacterLighting(camera, key);
        }

        internal static void ConfigureOperatorReferenceLighting(
            Scene scene,
            Transform lightingRoot,
            Camera camera,
            string actorName,
            Transform actorRoot)
        {
            ConfigurePreviewLighting(scene, lightingRoot);

            var keyObject = FindSceneGameObject("KeyLight");
            Light key = keyObject != null ? keyObject.GetComponent<Light>() : null;
            if (key != null)
            {
                if (!EndfieldOriginalRenderParameterImporter.TryReadEnvironmentLight(
                        out Vector2 directPitchYaw,
                        out Color directColor,
                        out float directColorTemperature,
                        out float directEv100,
                        out float directIntensityDividePi,
                        out string environmentProvenance))
                {
                    throw new InvalidDataException(
                        "Could not load the generated original CharInfo_Env parameter payload.");
                }

                // Unity's non-HGRP Light intensity is not physically equivalent
                // to the original EV100 carrier. Keep that unresolved bridge
                // neutral instead of inserting the serialized EV as lux.
                key.intensity = 1.0f;
                key.color = directColor;
                key.useColorTemperature = true;
                key.colorTemperature = directColorTemperature;
                key.shadows = LightShadows.None;
                float pitch = directPitchYaw.x * Mathf.Deg2Rad;
                float yaw = directPitchYaw.y * Mathf.Deg2Rad;
                float cosPitch = Mathf.Cos(pitch);
                Vector3 directionToLight = new Vector3(
                    -Mathf.Sin(yaw) * cosPitch,
                    Mathf.Sin(pitch),
                    -Mathf.Cos(yaw) * cosPitch).normalized;
                keyObject.transform.rotation = Quaternion.LookRotation(-directionToLight, Vector3.up);
                EditorUtility.SetDirty(key);
                EditorUtility.SetDirty(keyObject);
                Debug.Log(
                    $"Loaded original CharInfo environment parameters ({environmentProvenance}); " +
                    $"direct EV100 {directEv100:0.###}; character-main directIntensityDividePi " +
                    $"{directIntensityDividePi:0.#######} is recovered through the native live-exposure descriptor.");
            }

            if (camera == null)
                camera = Camera.main ?? UnityEngine.Object.FindObjectOfType<Camera>();
            if (camera == null)
                return;

            EndfieldHGRPCharacterLightingVolume volume =
                EnsureComponent<EndfieldHGRPCharacterLightingVolume>(camera.gameObject);
            volume.sceneMainLight = key;
            volume.targetCamera = camera;
            volume.characterReflectionCubemap =
                LoadRecoveredCharacterReflectionCubemap();
            volume.environmentReflectionCubemap =
                LoadRecoveredEnvironmentReflectionCubemap();
            volume.compatibilityShaderInfluence = 1.0f;
            string lightingActorName = Environment.GetEnvironmentVariable(
                ComparisonLightingActorEnvironmentVariable);
            if (string.IsNullOrWhiteSpace(lightingActorName))
                lightingActorName = actorName;
            else
                lightingActorName = lightingActorName.Trim();
            if (!EndfieldOriginalRenderParameterImporter.TryApplyCharacterLighting(
                    volume,
                    lightingActorName,
                    out string characterParameterProvenance))
            {
                throw new InvalidDataException(
                    $"Could not load generated original CharInfo parameters for {lightingActorName}.");
            }
            // CharInfo selects Manual mode at zero EV. A reused physical camera
            // can carry a prior current multiplier briefly, but the source-exact
            // target and the new-camera/settled value are neutral.
            volume.postExposureEV = 0.0f;
            EditorUtility.SetDirty(volume);
            Debug.Log(
                $"Loaded original character render parameters for {lightingActorName} " +
                $"(capture actor={actorName}, {characterParameterProvenance}).");

            EndfieldHGOperatorPresentation presentation =
                EnsureComponent<EndfieldHGOperatorPresentation>(camera.gameObject);
            // Publish the original Manual zero-EV target. The existing
            // environment override remains an explicit diagnostic only.
            presentation.fixedPostExposureEV = 0.0f;
            string recoveredExposureOverride = Environment.GetEnvironmentVariable(
                "ENDFIELD_RECOVERED_POST_EXPOSURE_EV");
            if (!string.IsNullOrWhiteSpace(recoveredExposureOverride))
            {
                if (float.TryParse(
                        recoveredExposureOverride.Trim(),
                        NumberStyles.Float,
                        CultureInfo.InvariantCulture,
                        out float recoveredExposureEV) &&
                    !float.IsNaN(recoveredExposureEV) &&
                    !float.IsInfinity(recoveredExposureEV))
                {
                    presentation.fixedPostExposureEV = Mathf.Clamp(
                        recoveredExposureEV,
                        -4.0f,
                        4.0f);
                    Debug.Log(
                        "Recovered-post fixed exposure override: " +
                        $"{presentation.fixedPostExposureEV:+0.###;-0.###;0} EV");
                }
                else
                {
                    Debug.LogWarning(
                        "Ignoring invalid ENDFIELD_RECOVERED_POST_EXPOSURE_EV=" +
                        recoveredExposureOverride.Trim());
                }
            }
            presentation.saturation = 1.08f;
            presentation.characterBloomThreshold = 0.75f;
            presentation.characterBloomIntensity = 0.45f;
            presentation.characterBloomSoftness = 0.8f;
            presentation.useRecoveredGachaRoomPostProfile = false;
            presentation.vignetteIntensity = 0.3f;
            presentation.vignetteSmoothness = 0.41f;
            presentation.vignetteRoundness = 0.94f;
            EditorUtility.SetDirty(presentation);

            EndfieldHGOperatorLightRig operatorLights =
                EnsureComponent<EndfieldHGOperatorLightRig>(camera.gameObject);
            bool approximateOperatorLighting =
                IsEnvironmentFlagEnabled(ApproximateOperatorLightingEnvironmentVariable);
            operatorLights.normalLightCompatibilityScale =
                approximateOperatorLighting ? 0.45f : 0.0f;
            operatorLights.rimLightCompatibilityScale =
                approximateOperatorLighting ? 0.05f : 0.0f;
            operatorLights.sourceBackedClusteredNprLightLoop =
                IsEnvironmentFlagEnabled(
                    RecoveredClusteredNprLightLoopEnvironmentVariable);
            operatorLights.sourceBackedLightBinningMembership =
                operatorLights.sourceBackedClusteredNprLightLoop &&
                IsEnvironmentFlagEnabled(
                    RecoveredLightBinningMembershipEnvironmentVariable);
            operatorLights.sourceBackedIsolatedPunctualSoftShadowProducer =
                operatorLights.sourceBackedClusteredNprLightLoop &&
                IsEnvironmentFlagEnabled(
                    RecoveredIsolatedPunctualSoftShadowsEnvironmentVariable);
            operatorLights.sourceBackedPunctualShadowTileResolution =
                operatorLights.sourceBackedIsolatedPunctualSoftShadowProducer
                    ? ReadRecoveredPunctualShadowTileResolution()
                    : 1024;
            if (!EndfieldOriginalOperatorLightImporter.TryRead(
                    lightingActorName,
                    out EndfieldHGOperatorLightData[] originalOperatorLights,
                    out string operatorLightProvenance))
            {
                throw new InvalidDataException(
                    $"Could not load generated original operator-light parameters for " +
                    $"{lightingActorName}.");
            }
            operatorLights.lights = originalOperatorLights;
            string followerBinding = operatorLights.BindActorRootAndDescribe(actorRoot);
            operatorLights.ApplyGlobals();
            EditorUtility.SetDirty(operatorLights);
            Debug.Log(
                $"Loaded original operator-light parameters for {lightingActorName} " +
                $"(capture actor={actorName}, {operatorLightProvenance}); " +
                $"{followerBinding}; clustered follower evaluation " +
                $"enabled={operatorLights.sourceBackedClusteredNprLightLoop}; " +
                $"exact isolated-rig XY/Z membership " +
                $"enabled={operatorLights.sourceBackedLightBinningMembership}; " +
                $"isolated punctual soft shadows " +
                $"enabled={operatorLights.sourceBackedIsolatedPunctualSoftShadowProducer}, " +
                $"B={operatorLights.sourceBackedPunctualShadowTileResolution}.");

            ConfigureRecoveredCharInfoSky(camera);
        }

        private static void ConfigureRecoveredCharacterLighting(Camera camera, Light keyLight)
        {
            if (camera == null)
                return;

            var volume = EnsureComponent<EndfieldHGRPCharacterLightingVolume>(camera.gameObject);
            volume.sceneMainLight = keyLight;
            volume.targetCamera = camera;
            volume.characterReflectionCubemap =
                LoadRecoveredCharacterReflectionCubemap();
            volume.environmentReflectionCubemap =
                LoadRecoveredEnvironmentReflectionCubemap();
            volume.compatibilityShaderInfluence = 0.35f;

            // These are the serialized values in the original C28M3 Wulfa
            // cutscene/dialog HGCharacterVolume assets, not viewer tuning guesses.
            volume.manualCharacterLightControl = true;
            volume.mainLightMode = EndfieldHGRPCharacterLightingVolume.CharacterLightMode.Scene;
            volume.mainLightMultiplier = 1.0f;
            volume.environmentLightMultiplier = 0.7f;
            volume.environmentShadowMultiplier = 1.0f;
            volume.mainLightSpecularMultiplier = 1.0f;
            volume.ambientDirection = Vector3.up;
            volume.ambientBaseIntensity = 1.0f;
            volume.ambientDirectionalIntensity = 0.6f;
            volume.ambientDirectionalBias = 0.15f;
            volume.ignoreMainLightShadow = false;
            volume.shadowTintMode = EndfieldHGRPCharacterLightingVolume.CharacterShadowTintMode.Auto;
            volume.dialogueLightingMode = false;
            volume.enableCharacterRim = false;
            volume.enableFaceRim = false;
            volume.eyeBaseLightMultiplier = 0.0f;
            volume.eyeHighlightMultiplier = 0.0f;
            volume.eyeScatteringMultiplier = 0.0f;
            volume.enableCharacterOutline = true;
            volume.outlineWidthMultiplier = 1.0f;
            volume.outlineIntensity = 1.0f;
            volume.postExposureEV = 0.0f;
            EditorUtility.SetDirty(volume);
        }

        private static Cubemap LoadRecoveredCharacterReflectionCubemap()
        {
            return AssetDatabase.LoadAssetAtPath<Cubemap>(
                EndfieldRecoveredCharCubemapImporter.CubemapAssetPath);
        }

        private static Cubemap LoadRecoveredEnvironmentReflectionCubemap()
        {
            return AssetDatabase.LoadAssetAtPath<Cubemap>(
                EndfieldRecoveredCharCubemapImporter
                    .EnvironmentReflectionCubemapAssetPath);
        }

        internal static void ConfigureRecoveredCharInfoSky(
            Camera camera,
            bool requireSourceAssets = false)
        {
            if (camera == null)
                throw new ArgumentNullException(nameof(camera));

            Cubemap skyCubemap = AssetDatabase.LoadAssetAtPath<Cubemap>(
                EndfieldRecoveredCharCubemapImporter.SkyCubemapAssetPath);
            if (skyCubemap == null &&
                (requireSourceAssets ||
                 Shader.IsKeywordEnabled(
                     EndfieldRecoveredSourceEnergyCoreProbe.Keyword)))
            {
                throw new FileNotFoundException(
                    "The source/operator physical-HDR path requires the exact " +
                    "T_hdri_006 Cubemap. Run recover_charinfo_cubemap.bat first.",
                    EndfieldRecoveredCharCubemapImporter.SkyCubemapAssetPath);
            }

            Material skyMaterial = EnsureRecoveredCharInfoSkyMaterial(skyCubemap);
            EndfieldRecoveredCharInfoSky sourceSky =
                EnsureComponent<EndfieldRecoveredCharInfoSky>(camera.gameObject);
            sourceSky.operatorPhysicalHdrSource = true;
            sourceSky.sourceCubemap = skyCubemap;
            sourceSky.sourceSkyMaterial = skyMaterial;

            GameObject backdrop = FindSceneGameObject(ReferenceBackdropObjectName);
            sourceSky.presentationBackdropRenderer =
                backdrop != null ? backdrop.GetComponent<Renderer>() : null;
            EditorUtility.SetDirty(sourceSky);
        }

        private static Material EnsureRecoveredCharInfoSkyMaterial(Cubemap cubemap)
        {
            EnsureAssetFolder($"{GeneratedRoot}/Shared/Materials");
            Shader shader = Shader.Find(EndfieldRecoveredCharInfoSky.ShaderName);
            if (shader == null)
            {
                throw new InvalidOperationException(
                    $"Recovered CharInfo sky shader is unavailable: " +
                    EndfieldRecoveredCharInfoSky.ShaderName);
            }

            Material material = AssetDatabase.LoadAssetAtPath<Material>(
                RecoveredCharInfoSkyMaterialPath);
            if (material == null)
            {
                material = new Material(shader)
                {
                    name = "M_RecoveredCharInfoSky",
                };
                AssetDatabase.CreateAsset(
                    material,
                    RecoveredCharInfoSkyMaterialPath);
            }
            else if (material.shader != shader)
            {
                material.shader = shader;
            }

            material.SetTexture("_Tex", cubemap);
            material.SetColor(
                "_Tint",
                EndfieldRecoveredCharInfoSky.SourceTint);
            material.SetFloat(
                "_Exposure",
                EndfieldRecoveredCharInfoSky.SourceExposure);
            material.SetFloat(
                "_Rotation",
                EndfieldRecoveredCharInfoSky.SourceRotationDegrees);
            EditorUtility.SetDirty(material);
            return material;
        }

        private static void FrameReferencePreviewScene(Scene scene)
        {
            var camera = Camera.main ?? UnityEngine.Object.FindObjectOfType<Camera>();
            Transform activeRoot = FindActiveCharacterRoot();
            var renderers = UnityEngine.Object.FindObjectsOfType<SkinnedMeshRenderer>();
            if (camera == null || renderers.Length == 0)
                return;

            Bounds bounds = CombinedBounds(renderers);
            FrameCamera(camera, bounds);
            ConfigureReferenceBackdrop(scene, FindBackdropRoot(), camera, bounds);

            var controller = camera.GetComponent<CharacterRecoveryCameraController>();
            if (controller != null)
            {
                ConfigureCameraController(controller);
                if (activeRoot != null)
                    controller.SetFocus(activeRoot, bounds);
                EditorUtility.SetDirty(controller);
            }
            EditorUtility.SetDirty(camera);
        }

        private static void ConfigureCameraController(CharacterRecoveryCameraController controller)
        {
            controller.defaultFieldOfView = PreviewFieldOfView;
            controller.nearClip = PreviewNearClip;
            controller.useReferenceFraming = true;
            controller.referenceVerticalCoverage = PreviewReferenceVerticalCoverage;
            controller.referenceTopBias = PreviewReferenceTopBias;
            controller.referenceDistanceScale = 1f;
        }

        private static Transform FindActiveCharacterRoot()
        {
            var charactersRoot = FindSceneGameObject("Characters")?.transform;
            if (charactersRoot == null)
                return null;

            foreach (Transform child in charactersRoot)
            {
                if (child != null && child.gameObject.activeInHierarchy)
                    return child;
            }
            return null;
        }

        private static Transform FindBackdropRoot()
        {
            var viewerRoot = FindSceneGameObject(ViewerRootObjectName);
            if (viewerRoot == null)
                return null;

            Transform backdropRoot = FindDirectChild(viewerRoot.transform, "Backdrop");
            if (backdropRoot == null)
                backdropRoot = CreateChildGroup(viewerRoot.transform, "Backdrop");
            return backdropRoot;
        }

        private static Transform FindDirectChild(Transform parent, string name)
        {
            if (parent == null)
                return null;

            foreach (Transform child in parent)
            {
                if (child != null && child.name == name)
                    return child;
            }
            return null;
        }

        private static void ConfigureReferenceBackdrop(
            Scene scene,
            Transform backdropRoot,
            Camera camera,
            Bounds bounds,
            float outputAspect = 0f)
        {
            if (camera == null)
                return;

            if (backdropRoot == null)
                backdropRoot = FindBackdropRoot();

            GameObject backdrop = null;
            if (backdropRoot != null)
                backdrop = FindDirectChild(backdropRoot, ReferenceBackdropObjectName)?.gameObject;
            if (backdrop == null)
                backdrop = FindSceneGameObject(ReferenceBackdropObjectName);
            if (backdrop == null)
                backdrop = CreateSceneObject(ReferenceBackdropObjectName, backdropRoot, scene);
            else if (backdropRoot != null && backdrop.transform.parent != backdropRoot)
                backdrop.transform.SetParent(backdropRoot, true);

            var filter = EnsureComponent<MeshFilter>(backdrop);
            if (filter.sharedMesh == null || filter.sharedMesh.name != "ReferenceBackdropQuad")
                filter.sharedMesh = CreateReferenceBackdropMesh();

            var renderer = EnsureComponent<MeshRenderer>(backdrop);
            renderer.sharedMaterial = EnsureReferenceBackdropMaterial();
            // This remains a separate presentation/UI background. The
            // recovered CharInfo sky component disables it before source-path
            // culling so it cannot contaminate raw HDR or histogram input.
            renderer.enabled = true;
            renderer.shadowCastingMode = ShadowCastingMode.Off;
            renderer.receiveShadows = false;
            renderer.lightProbeUsage = LightProbeUsage.Off;
            renderer.reflectionProbeUsage = ReflectionProbeUsage.Off;

            foreach (Collider collider in backdrop.GetComponents<Collider>())
                UnityEngine.Object.DestroyImmediate(collider);

            Vector3 target = ReferenceFrameTarget(bounds);
            float targetDistance = Mathf.Max(1f, Vector3.Distance(camera.transform.position, target));
            float planeDistance = targetDistance + Mathf.Max(0.8f, bounds.size.y * 0.20f + bounds.extents.z);
            // Leave enough overscan for the operator UI compositor's off-axis
            // projection. The earlier 1.12 margin exposed the camera clear
            // color at the edge of capture-calibrated 4K renders.
            float planeHeight = 2f * planeDistance * Mathf.Tan(camera.fieldOfView * 0.5f * Mathf.Deg2Rad) * 1.35f;
            float aspect = outputAspect > 0f
                ? outputAspect
                : (float)PreviewRenderWidth / PreviewRenderHeight;
            float planeWidth = planeHeight * aspect * 1.18f;

            backdrop.transform.position = camera.transform.position + camera.transform.forward * planeDistance;
            backdrop.transform.rotation = camera.transform.rotation;
            backdrop.transform.localScale = new Vector3(planeWidth, planeHeight, 1f);

            EndfieldRecoveredCharInfoSky sourceSky =
                camera.GetComponent<EndfieldRecoveredCharInfoSky>();
            if (sourceSky != null)
            {
                sourceSky.presentationBackdropRenderer = renderer;
                EditorUtility.SetDirty(sourceSky);
            }
            EditorUtility.SetDirty(backdrop);
        }

        /// <summary>
        /// Switches the viewer camera to a uniform white presentation
        /// background shared by every selected character: solid-white camera
        /// clear, a flat-white backdrop quad, the recovered CharInfo HDR sky
        /// released (it is presentation-only here; character shading keeps the
        /// source-energy path), and the dark CharInfo room subset hidden.
        /// </summary>
        private static void ApplyNeutralWhiteViewerBackground(Camera camera)
        {
            if (camera == null)
                throw new ArgumentNullException(nameof(camera));

            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = Color.white;
            EditorUtility.SetDirty(camera);

            EndfieldRecoveredCharInfoSky sourceSky =
                camera.GetComponent<EndfieldRecoveredCharInfoSky>();
            Renderer backdropRenderer = sourceSky != null
                ? sourceSky.presentationBackdropRenderer
                : null;
            if (sourceSky != null)
            {
                sourceSky.operatorPhysicalHdrSource = false;
                EditorUtility.SetDirty(sourceSky);
            }
            if (backdropRenderer == null)
            {
                GameObject backdrop = FindSceneGameObject(ReferenceBackdropObjectName);
                backdropRenderer = backdrop != null
                    ? backdrop.GetComponent<MeshRenderer>()
                    : null;
            }
            if (backdropRenderer != null)
            {
                backdropRenderer.enabled = true;
                backdropRenderer.sharedMaterial = EnsureWhiteReferenceBackdropMaterial();
                EditorUtility.SetDirty(backdropRenderer);
            }

            var presentationController =
                camera.GetComponent<CharacterRecoveryPresentationController>();
            if (presentationController != null)
            {
                presentationController.enableRecoveredReadyPresentationSubset = false;
                EditorUtility.SetDirty(presentationController);
            }

            // The recovered CharInfo vignette multiplies the frame after the
            // tonemap, so it would leave the corners grey no matter how bright
            // the backdrop is. A uniform background requires it off.
            var operatorPresentation =
                camera.GetComponent<EndfieldHGOperatorPresentation>();
            if (operatorPresentation != null)
            {
                operatorPresentation.vignetteIntensity = 0f;
                EditorUtility.SetDirty(operatorPresentation);
            }

            EndfieldRecoveredCharInfoPresentation physicalPresentation =
                UnityEngine.Object.FindObjectOfType<EndfieldRecoveredCharInfoPresentation>(true);
            if (physicalPresentation != null)
            {
                physicalPresentation.enableRecoveredPresentation = false;
                physicalPresentation.enableReadySubsetDiagnostic = false;
                physicalPresentation.RefreshSelection();
                EditorUtility.SetDirty(physicalPresentation);
            }
        }

        private static Material EnsureWhiteReferenceBackdropMaterial()
        {
            EnsureAssetFolder($"{GeneratedRoot}/Shared/Materials");
            Shader shader =
                Shader.Find("Endfield/CharacterRecovery/ReferenceBackdrop") ??
                Shader.Find("Unlit/Color") ??
                Shader.Find("Standard");
            var material = AssetDatabase.LoadAssetAtPath<Material>(
                WhiteReferenceBackdropMaterialPath);
            if (material == null)
            {
                material = new Material(shader);
                AssetDatabase.CreateAsset(material, WhiteReferenceBackdropMaterialPath);
            }
            else if (shader != null && material.shader != shader)
            {
                material.shader = shader;
            }

            material.color = Color.white;
            SetMaterialColor(material, "_Color", Color.white);
            SetMaterialColor(material, "_TopColor", Color.white);
            SetMaterialColor(material, "_BottomColor", Color.white);
            SetMaterialColor(material, "_GridColor", Color.white);
            SetMaterialColor(material, "_SilhouetteColor", Color.white);
            SetMaterialFloat(material, "_GridOpacity", 0f);
            SetMaterialFloat(material, "_DiagonalOpacity", 0f);
            SetMaterialFloat(material, "_SilhouetteOpacity", 0f);
            SetMaterialFloat(material, "_BottomVignette", 0f);
            // Keeps the neutral backdrop above the recovered ACES_modified
            // highlight-compression knee after the CharInfo grade/vignette, so
            // post outputs exact display white for every character selection.
            // 32 left the vignetted frame corners below the knee (sRGB 219);
            // 128 clears it across the whole frame.
            SetMaterialFloat(material, "_HdrBoost", 128f);
            EditorUtility.SetDirty(material);
            return material;
        }

        private static Mesh CreateReferenceBackdropMesh()
        {
            var mesh = new Mesh
            {
                name = "ReferenceBackdropQuad",
                vertices = new[]
                {
                    new Vector3(-0.5f, -0.5f, 0f),
                    new Vector3(0.5f, -0.5f, 0f),
                    new Vector3(0.5f, 0.5f, 0f),
                    new Vector3(-0.5f, 0.5f, 0f),
                },
                uv = new[]
                {
                    new Vector2(0f, 0f),
                    new Vector2(1f, 0f),
                    new Vector2(1f, 1f),
                    new Vector2(0f, 1f),
                },
                triangles = new[] { 0, 2, 1, 0, 3, 2 },
            };
            mesh.RecalculateBounds();
            return mesh;
        }

        private static Material EnsureReferenceBackdropMaterial()
        {
            EnsureAssetFolder($"{GeneratedRoot}/Shared/Materials");
            string fullPath = Path.Combine(Directory.GetCurrentDirectory(), ReferenceBackdropMaterialPath);
            Directory.CreateDirectory(Path.GetDirectoryName(fullPath) ?? ".");

            Shader shader =
                Shader.Find("Endfield/CharacterRecovery/ReferenceBackdrop") ??
                Shader.Find("Unlit/Color") ??
                Shader.Find("Standard");
            var material = AssetDatabase.LoadAssetAtPath<Material>(ReferenceBackdropMaterialPath);
            if (material == null)
            {
                material = new Material(shader);
                AssetDatabase.CreateAsset(material, ReferenceBackdropMaterialPath);
            }
            else if (shader != null && material.shader != shader)
            {
                material.shader = shader;
            }

            material.color = PreviewBackgroundColor;
            SetMaterialColor(material, "_Color", PreviewBackgroundColor);
            SetMaterialColor(material, "_TopColor", new Color(0.78f, 0.79f, 0.78f, 1f));
            SetMaterialColor(material, "_BottomColor", new Color(0.55f, 0.56f, 0.55f, 1f));
            SetMaterialColor(material, "_GridColor", new Color(0.34f, 0.35f, 0.34f, 1f));
            SetMaterialColor(material, "_SilhouetteColor", new Color(0.42f, 0.43f, 0.42f, 1f));
            SetMaterialFloat(material, "_GridOpacity", 0.18f);
            SetMaterialFloat(material, "_DiagonalOpacity", 0.12f);
            SetMaterialFloat(material, "_SilhouetteOpacity", 0.22f);
            SetMaterialFloat(material, "_BottomVignette", 0.22f);
            EditorUtility.SetDirty(material);
            return material;
        }

        private static void SetMaterialColor(Material material, string propertyName, Color color)
        {
            if (material != null && material.HasProperty(propertyName))
                material.SetColor(propertyName, color);
        }

        private static void SetMaterialFloat(Material material, string propertyName, float value)
        {
            if (material != null && material.HasProperty(propertyName))
                material.SetFloat(propertyName, value);
        }

        private static void SetMaterialInt(Material material, string propertyName, int value)
        {
            if (material != null && material.HasProperty(propertyName))
                material.SetInt(propertyName, value);
        }

        private static void ApplyGeneratedMaterialProfileFlags()
        {
            foreach (string guid in AssetDatabase.FindAssets("t:Material", new[] { GeneratedRoot }))
            {
                string assetPath = AssetDatabase.GUIDToAssetPath(guid);
                var material = AssetDatabase.LoadAssetAtPath<Material>(assetPath);
                if (material == null)
                    continue;

                string materialName = material.name.ToLowerInvariant();
                bool isCloth = materialName.Contains("cloth");
                bool originalHgrpProfile =
                    material.HasProperty("_OriginalHGRPProfile") &&
                    material.GetFloat("_OriginalHGRPProfile") > 0.5f;
                if (material.HasProperty("_IsCloth"))
                    material.SetFloat("_IsCloth", isCloth ? 1f : 0f);
                if (isCloth && !originalHgrpProfile)
                    ApplyClothPreviewProfile(material);
                if (material.HasProperty("_ShadowStrength"))
                    material.SetFloat("_ShadowStrength", OverlayShadowStrength(materialName));
                if (material.HasProperty("_ShadowColor"))
                    material.SetColor("_ShadowColor", OverlayShadowColor(materialName));
                EditorUtility.SetDirty(material);
            }
            AssetDatabase.SaveAssets();
        }

        private static void SampleActivePreviewAnimations(
            Scene scene,
            CharacterRecoveryRig selectedRig = null)
        {
            foreach (GameObject root in scene.GetRootGameObjects())
            {
                if (root == null || !root.activeInHierarchy)
                    continue;

                foreach (Animation animation in root.GetComponentsInChildren<Animation>(true))
                {
                    if (animation == null || !animation.gameObject.activeInHierarchy || animation.clip == null)
                        continue;
                    if (selectedRig != null &&
                        animation.GetComponentInParent<CharacterRecoveryRig>() != selectedRig)
                        continue;

                    AnimationClip clip = animation.clip;
                    CharacterRecoveryRig rig = animation.GetComponent<CharacterRecoveryRig>();
                    SetRecoveredPropVisibility(animation.gameObject, Array.Empty<string>());
                    float sampleTime = Mathf.Clamp(clip.length * PreviewAnimationSampleNormalizedTime, 0f, Mathf.Max(clip.length, 0f));
                    clip.SampleAnimation(animation.gameObject, sampleTime);
                    CharacterRecoveryState companionState = FindUiPropCompanionState(rig, clip.name);
                    int companionLayerCount = 0;
                    if (companionState != null)
                    {
                        SetRecoveredPropVisibility(animation.gameObject, companionState.visibleProps);
                        foreach (CharacterRecoveryLayer layer in companionState.layers ?? Array.Empty<CharacterRecoveryLayer>())
                        {
                            if (layer == null
                                || !IsRecoveredUiItemWidgetRole(layer.role)
                                || string.IsNullOrEmpty(layer.clip))
                                continue;
                            AnimationState layerState = animation[layer.clip];
                            AnimationClip layerClip = layerState != null ? layerState.clip : null;
                            if (layerClip == null)
                                continue;
                            float layerTime = Mathf.Clamp(
                                layerClip.length * PreviewAnimationSampleNormalizedTime,
                                0f,
                                Mathf.Max(layerClip.length, 0f));
                            layerClip.SampleAnimation(animation.gameObject, layerTime);
                            companionLayerCount++;
                        }
                    }
                    EditorUtility.SetDirty(animation.gameObject);
                    Debug.Log(
                        $"Sampled {animation.gameObject.name} preview animation {clip.name} at {sampleTime:0.###}s " +
                        $"with {companionLayerCount} recovered UI-prop companion layer(s).");
                }
            }
        }

        private static CharacterRecoveryState FindUiPropCompanionState(CharacterRecoveryRig rig, string baseClip)
        {
            if (rig == null || rig.recoveredStates == null || string.IsNullOrEmpty(baseClip))
                return null;
            foreach (CharacterRecoveryState state in rig.recoveredStates)
            {
                if (state == null || !string.Equals(state.baseClip, baseClip, StringComparison.OrdinalIgnoreCase))
                    continue;
                foreach (CharacterRecoveryLayer layer in state.layers ?? Array.Empty<CharacterRecoveryLayer>())
                {
                    if (layer != null && IsRecoveredUiItemWidgetRole(layer.role))
                        return state;
                }
            }
            return null;
        }

        private static bool IsRecoveredUiItemWidgetRole(string role)
        {
            return string.Equals(role, "ui_prop", StringComparison.OrdinalIgnoreCase) ||
                   string.Equals(role, "ui_item_widget", StringComparison.OrdinalIgnoreCase);
        }

        private static void SetRecoveredPropVisibility(GameObject actorRoot, IEnumerable<string> visibleProps)
        {
            if (actorRoot == null)
                return;
            Transform propRoot = actorRoot.transform.Find("RecoveredProps");
            if (propRoot == null)
                return;
            foreach (Renderer renderer in propRoot.GetComponentsInChildren<Renderer>(true))
            {
                if (renderer != null)
                    renderer.enabled = false;
            }

            var enabledPaths = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (string path in visibleProps ?? Array.Empty<string>())
            {
                if (string.IsNullOrEmpty(path) || !enabledPaths.Add(path))
                    continue;
                Transform prop = actorRoot.transform.Find(path);
                if (prop == null)
                    continue;
                foreach (Renderer renderer in prop.GetComponentsInChildren<Renderer>(true))
                {
                    if (renderer != null)
                        renderer.enabled = true;
                }
            }
        }

        private static void ApplyClothPreviewProfile(Material material)
        {
            if (material.HasProperty("_Metallic"))
                material.SetFloat("_Metallic", 0f);
            if (material.HasProperty("_Specular"))
                material.SetFloat("_Specular", Mathf.Clamp(FloatProperty(material, "_Specular"), 0.22f, 0.42f));
            if (material.HasProperty("_Smoothness"))
                material.SetFloat("_Smoothness", Mathf.Clamp(FloatProperty(material, "_Smoothness"), 0.44f, 0.60f));
            if (material.HasProperty("_BumpScale"))
                material.SetFloat("_BumpScale", Mathf.Min(FloatProperty(material, "_BumpScale"), 0.72f));
            if (material.HasProperty("_SpecBumpScale"))
                material.SetFloat("_SpecBumpScale", Mathf.Min(FloatProperty(material, "_SpecBumpScale"), 0.68f));
            if (material.HasProperty("_EmissionBrightness"))
                material.SetFloat("_EmissionBrightness", Mathf.Min(FloatProperty(material, "_EmissionBrightness"), 1.5f));
            if (material.HasProperty("_OutlineWidth"))
                material.SetFloat("_OutlineWidth", Mathf.Min(FloatProperty(material, "_OutlineWidth"), 0.28f));
            if (material.HasProperty("_OutlineOffsetZ"))
                material.SetFloat("_OutlineOffsetZ", Mathf.Min(FloatProperty(material, "_OutlineOffsetZ"), 0.05f));
        }

        private static void ApplyGeneratedTextureImportProfiles(
            params string[] searchRoots)
        {
            bool changedAny = false;
            string[] effectiveSearchRoots =
                searchRoots != null && searchRoots.Length > 0
                    ? searchRoots
                    : new[] { GeneratedRoot };
            foreach (string guid in AssetDatabase.FindAssets(
                         "t:Texture2D",
                         effectiveSearchRoots))
            {
                string assetPath = AssetDatabase.GUIDToAssetPath(guid);
                var importer = AssetImporter.GetAtPath(assetPath) as TextureImporter;
                if (importer == null)
                    continue;

                string textureName = Path.GetFileName(assetPath);
                // The two exact installed OverlayShadow masks are `_BaseMap`
                // inputs even though their `_M` filenames resemble generic
                // packed maps. Preserve that property identity in this
                // filename-only repair pass; the source descriptor contract
                // independently applies their Linear=0 color-space value.
                string materialProperty = IsOriginalEyeShadowBaseMap(
                        "_BaseMap",
                        textureName)
                    ? "_BaseMap"
                    : GuessMaterialPropertyFromTextureName(textureName);
                if (ConfigureTextureImporter(importer, materialProperty, textureName))
                {
                    importer.SaveAndReimport();
                    changedAny = true;
                }
            }

            if (changedAny)
                AssetDatabase.Refresh();
        }

        private static void PruneLowerQualityMeshLodsFromOpenScene()
        {
            int removed = 0;
            var groups = new List<GameObject>();
            foreach (Transform transform in UnityEngine.Object.FindObjectsOfType<Transform>(true))
            {
                if (transform == null || !transform.gameObject.scene.IsValid())
                    continue;
                if (IsLowerQualityMeshLodGroup(transform) && !IsPreservedEntityVfxLod(transform))
                    groups.Add(transform.gameObject);
            }

            foreach (GameObject group in groups)
            {
                if (group == null)
                    continue;
                UnityEngine.Object.DestroyImmediate(group);
                removed++;
            }

            var meshObjects = new List<GameObject>();
            foreach (SkinnedMeshRenderer renderer in UnityEngine.Object.FindObjectsOfType<SkinnedMeshRenderer>(true))
            {
                if (renderer == null || !renderer.gameObject.scene.IsValid())
                    continue;
                string path = ScenePath(renderer.transform);
                bool lowerPathLod = TryGetMeshLodFromPath(path, out int pathLod) && pathLod != HighestMeshLod;
                bool lowerNameLod = TryGetMeshLodFromName(renderer.name, out int nameLod) && nameLod != HighestMeshLod;
                if ((lowerPathLod || lowerNameLod) && !IsPreservedEntityVfxLod(renderer.transform))
                    meshObjects.Add(renderer.gameObject);
            }

            foreach (GameObject meshObject in meshObjects)
            {
                if (meshObject == null)
                    continue;
                UnityEngine.Object.DestroyImmediate(meshObject);
                removed++;
            }

            if (removed > 0)
                Debug.Log($"Pruned {removed} lower-quality mesh LOD scene objects; viewer now uses lod{HighestMeshLod} renderers only.");
        }

        private static bool IsLowerQualityMeshLodGroup(Transform transform)
        {
            return transform.parent != null
                && transform.parent.name.Equals("Mesh_all", StringComparison.OrdinalIgnoreCase)
                && TryGetLodSegment(transform.name, out int lod)
                && lod != HighestMeshLod;
        }

        private static bool IsPreservedEntityVfxLod(Transform transform)
        {
            for (Transform cursor = transform; cursor != null; cursor = cursor.parent)
            {
                if (!cursor.name.Equals("chr_0030_zhuangfy_deco_1", StringComparison.Ordinal) ||
                    cursor.parent == null ||
                    !cursor.parent.name.Equals("RecoveredProps", StringComparison.Ordinal))
                    continue;

                LODGroup group = cursor.GetComponent<LODGroup>();
                if (group == null)
                    return false;
                LOD[] lods = group.GetLODs();
                return lods.Length == 4 && lods.All(lod =>
                    lod.renderers != null && lod.renderers.Length == 1 && lod.renderers[0] != null);
            }
            return false;
        }

        private static string ScenePath(Transform transform)
        {
            var names = new List<string>();
            for (Transform cursor = transform; cursor != null; cursor = cursor.parent)
                names.Add(cursor.name);
            names.Reverse();
            return string.Join("/", names.ToArray());
        }

        private static GameObject CreateSceneObject(string name, Transform parent, Scene scene)
        {
            var go = new GameObject(name);
            if (parent != null)
                go.transform.SetParent(parent, false);
            else
                SceneManager.MoveGameObjectToScene(go, scene);
            return go;
        }

        private static T EnsureComponent<T>(GameObject go) where T : Component
        {
            T component = go.GetComponent<T>();
            if (component == null)
                component = go.AddComponent<T>();
            return component;
        }

        private static void EnsureCharacterRecoveryActorCatalog(
            ViewerSceneLayout layout,
            List<ActorBuildResult> actors,
            Dictionary<string, CharacterRecoveryPresentationProfile>
                presentationProfiles = null,
            bool allowMissingPresentationProfiles = false)
        {
            if (layout == null || layout.CharactersRoot == null || actors == null)
                return;

            GameObject catalogObject = layout.CharactersRoot.gameObject;
            foreach (CharacterRecoveryActorCatalog stale in
                     catalogObject.GetComponents<CharacterRecoveryActorCatalog>())
            {
                if (stale != null)
                    UnityEngine.Object.DestroyImmediate(stale);
            }
            GameObjectUtility.RemoveMonoBehavioursWithMissingScript(catalogObject);
            var catalog = catalogObject.AddComponent<CharacterRecoveryActorCatalog>();
            catalog.spawnParent = layout.CharactersRoot;
            // The shared viewer is a selector, not a resident gallery. Keeping
            // all 31 prefab references and instances resident makes opening the
            // scene import every mesh, texture, material, and animation before
            // the first frame. Runtime selection resolves prefabAssetPath in
            // the editor and keeps only the selected actor alive.
            catalog.keepAllModelsResident = false;
            catalog.horizontalSpacing = CharacterLineupHorizontalSpacing;
            var entries = new List<CharacterRecoveryActorCatalogEntry>();
            foreach (ActorBuildResult actor in actors)
            {
                if (actor == null || string.IsNullOrEmpty(actor.PrefabAssetPath))
                    continue;
                GameObject prefab =
                    AssetDatabase.LoadAssetAtPath<GameObject>(
                        actor.PrefabAssetPath);
                if (prefab == null)
                {
                    throw new FileNotFoundException(
                        $"Character viewer catalog prefab is missing: {actor.RootName}",
                        actor.PrefabAssetPath);
                }
                CharacterRecoveryPresentationProfile presentationProfile = null;
                if (presentationProfiles != null &&
                    !presentationProfiles.TryGetValue(
                        actor.RootName,
                        out presentationProfile))
                {
                    if (!allowMissingPresentationProfiles)
                    {
                        throw new InvalidDataException(
                            $"Character viewer catalog profile is missing: {actor.RootName}.");
                    }
                    Debug.Log(
                        $"Character viewer catalog keeps {actor.RootName} source-profile-null; " +
                        "camera selection will use model bounds because no original CharInfo profile was recovered.");
                }
                entries.Add(new CharacterRecoveryActorCatalogEntry
                {
                    displayName = actor.DisplayName,
                    rootName = actor.RootName,
                    prefabAssetPath = actor.PrefabAssetPath,
                    prefab = null,
                    presentationProfile = presentationProfile,
                });
            }
            catalog.entries = entries.ToArray();
            EditorUtility.SetDirty(catalog);
        }

        private static EndfieldRecoveredCharInfoPresentation
            EnsureOriginalStylePresentationScene(Scene scene)
        {
            return EndfieldRecoveredCharInfoPresentationBuilder
                .EnsureBoundIntoScene(
                    scene,
                    enableReadySubsetDiagnostic: true);
        }

        private static void EnsureCharacterRecoveryPresentation(
            Camera camera,
            EndfieldRecoveredCharInfoBackgroundPortrait portrait,
            ActorBuildResult activeActor,
            Dictionary<string, CharacterRecoveryPresentationProfile>
                presentationProfiles)
        {
            if (camera == null || activeActor == null || activeActor.Root == null)
                throw new ArgumentNullException(
                    camera == null ? nameof(camera) : nameof(activeActor));
            CharacterRecoveryPresentationProfile activeProfile = null;
            if (presentationProfiles != null)
            {
                presentationProfiles.TryGetValue(
                    activeActor.RootName,
                    out activeProfile);
            }
            // The legacy two-actor portrait importer may synchronously refresh
            // assets while upgrading an older scene. Reload the persistent
            // profile rather than treating an invalidated Unity object handle
            // as missing original data.
            if (activeProfile == null)
            {
                activeProfile =
                    EndfieldPlayableCharInfoProfileBuilder.LoadProfile(
                        activeActor.RootName);
            }
            if (activeProfile == null)
            {
                throw new InvalidDataException(
                    $"No source-recovered presentation profile for {activeActor.RootName}.");
            }

            CharacterRecoveryPresentationController presentation =
                EnsureComponent<CharacterRecoveryPresentationController>(
                    camera.gameObject);
            presentation.viewerCamera = camera;
            presentation.cameraController =
                camera.GetComponent<CharacterRecoveryCameraController>();
            presentation.backgroundPortrait = portrait;
            presentation.characterLighting =
                camera.GetComponent<EndfieldHGRPCharacterLightingVolume>();
            presentation.operatorLightRig =
                camera.GetComponent<EndfieldHGOperatorLightRig>();
            presentation.physicalPresentation =
                UnityEngine.Object.FindObjectOfType<
                    EndfieldRecoveredCharInfoPresentation>(true);
            EndfieldRecoveredCharInfoSky sourceSky =
                camera.GetComponent<EndfieldRecoveredCharInfoSky>();
            presentation.presentationBackdropRenderer =
                sourceSky != null
                    ? sourceSky.presentationBackdropRenderer
                    : null;
            // Keep the optional source UIImage portrait out of the resident
            // horizontal model lineup. Selection still applies the original
            // camera/light profile without loading or replacing actor roots.
            presentation.enableRecoveredPortrait = false;
            presentation.enableRecoveredSourceEnergyCore = false;
            presentation.enableRecoveredEyeResponse = true;
            presentation.enableRecoveredFaceHighlight = true;
            presentation.enableRecoveredPostSemantics = true;
            presentation.enableRecoveredReadyPresentationSubset = true;
            presentation.enableSourceBackedClusteredNprLights = true;
            presentation.enableSourceBackedLightBinning = true;
            presentation.enableIsolatedPunctualSoftShadows = false;

            CharacterRecoveryRig rig =
                activeActor.Root.GetComponent<CharacterRecoveryRig>();
            if (rig == null || !presentation.ApplyProfile(activeProfile, rig))
            {
                throw new InvalidOperationException(
                    $"Could not apply source-recovered presentation for {activeActor.RootName}.");
            }
            EditorUtility.SetDirty(presentation);
            EditorUtility.SetDirty(camera);
        }

        private static ActorBuildResult EnsureHorizontalCharacterLineup(
            Scene scene,
            ViewerSceneLayout layout,
            List<ActorBuildResult> actors,
            string preferredActiveRootName)
        {
            if (layout == null || layout.CharactersRoot == null || actors == null)
                throw new ArgumentNullException(nameof(actors));

            List<ActorBuildResult> ordered = actors
                .Where(actor => actor != null && !string.IsNullOrEmpty(actor.RootName))
                .OrderBy(
                    actor => string.IsNullOrEmpty(actor.DisplayName)
                        ? actor.RootName
                        : actor.DisplayName,
                    StringComparer.Ordinal)
                .ToList();
            if (ordered.Count == 0)
                throw new InvalidOperationException(
                    "Character viewer resident lineup contains no actors.");

            ActorBuildResult activeActor = ordered.FirstOrDefault(
                actor => string.Equals(
                    actor.RootName,
                    preferredActiveRootName,
                    StringComparison.OrdinalIgnoreCase)) ?? ordered[0];

            // Keep one scene instance. The catalog retains paths for every
            // other actor, which CharacterRecoveryViewerUI loads on demand.
            for (int childIndex = layout.CharactersRoot.childCount - 1;
                 childIndex >= 0;
                 childIndex--)
            {
                Transform child = layout.CharactersRoot.GetChild(childIndex);
                if (child == null ||
                    child.GetComponent<CharacterRecoveryRig>() == null ||
                    string.Equals(
                        child.name,
                        activeActor.RootName,
                        StringComparison.OrdinalIgnoreCase))
                    continue;
                UnityEngine.Object.DestroyImmediate(child.gameObject);
            }

            for (int index = 0; index < ordered.Count; index++)
            {
                ActorBuildResult actor = ordered[index];
                if (actor != activeActor)
                {
                    actor.Root = null;
                    continue;
                }
                GameObject root = actor.Root;
                if (root == null || root.scene != scene)
                {
                    Transform existing = FindDirectChild(
                        layout.CharactersRoot,
                        actor.RootName);
                    root = existing != null ? existing.gameObject : null;
                }
                if (root == null)
                {
                    GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(
                        actor.PrefabAssetPath);
                    if (prefab == null)
                    {
                        throw new FileNotFoundException(
                            $"Resident character lineup prefab is missing: {actor.RootName}",
                            actor.PrefabAssetPath);
                    }
                    root = PrefabUtility.InstantiatePrefab(prefab, scene) as GameObject;
                    if (root == null)
                    {
                        throw new InvalidOperationException(
                            $"Could not instantiate resident character: {actor.RootName}");
                    }
                    root.name = actor.RootName;
                }

                root.transform.SetParent(layout.CharactersRoot, false);
                root.transform.localPosition = Vector3.zero;
                root.transform.localRotation = Quaternion.identity;
                root.transform.SetSiblingIndex(0);
                root.SetActive(true);
                CharacterRecoveryRig rig = root.GetComponent<CharacterRecoveryRig>();
                if (rig == null)
                {
                    throw new InvalidDataException(
                        $"Resident character lineup prefab has no rig: {actor.RootName}");
                }
                if (!string.IsNullOrEmpty(actor.DisplayName))
                    rig.displayName = actor.DisplayName;
                if (PrefabUtility.IsPartOfPrefabInstance(root))
                {
                    PrefabUtility.RecordPrefabInstancePropertyModifications(root);
                    PrefabUtility.RecordPrefabInstancePropertyModifications(root.transform);
                    PrefabUtility.RecordPrefabInstancePropertyModifications(rig);
                }
                actor.Root = root;
                EditorUtility.SetDirty(root);
                EditorUtility.SetDirty(rig);
            }

            return activeActor;
        }

        private static void EnsureCharacterRecoveryViewerUi(ViewerSceneLayout layout = null)
        {
            var existing = UnityEngine.Object.FindObjectOfType<CharacterRecoveryViewerUI>(true);
            if (existing != null)
            {
                existing.gameObject.name = "ViewerUI";
                if (layout != null)
                    existing.transform.SetParent(layout.Root.transform, true);
                return;
            }

            var uiRoot = CreateSceneObject(
                "ViewerUI",
                layout != null ? layout.Root.transform : null,
                SceneManager.GetActiveScene());
            uiRoot.AddComponent<CharacterRecoveryViewerUI>();
        }

        private static Bounds CombinedBounds(SkinnedMeshRenderer[] renderers)
        {
            var bounds = new Bounds(Vector3.zero, Vector3.zero);
            bool hasBounds = false;
            foreach (var renderer in renderers)
            {
                if (renderer == null
                    || !renderer.enabled
                    || !renderer.gameObject.activeInHierarchy
                    || IsRecoveredPropRenderer(renderer))
                    continue;
                if (!hasBounds)
                {
                    bounds = renderer.bounds;
                    hasBounds = true;
                }
                else
                {
                    bounds.Encapsulate(renderer.bounds);
                }
            }
            return bounds;
        }

        private static bool IsRecoveredPropRenderer(Renderer renderer)
        {
            Transform current = renderer != null ? renderer.transform : null;
            while (current != null)
            {
                if (string.Equals(current.name, "RecoveredProps", StringComparison.OrdinalIgnoreCase))
                    return true;
                current = current.parent;
            }
            return false;
        }

        private static GameObject FindSceneGameObject(string name)
        {
            foreach (GameObject go in Resources.FindObjectsOfTypeAll<GameObject>())
            {
                if (go == null || go.name != name || !go.scene.IsValid())
                    continue;
                return go;
            }
            return null;
        }

        private static void RenderPreview(string path)
        {
            RenderPreview(path, PreviewRenderWidth, PreviewRenderHeight);
        }

        private static void RenderPreview(string path, int width, int height)
        {
            Camera camera = Camera.main ?? UnityEngine.Object.FindObjectOfType<Camera>();
            if (camera == null)
                throw new InvalidOperationException("Generated scene has no camera.");
            RenderPreview(path, camera, width, height);
        }

        private static void RenderPreview(
            string path,
            Camera camera,
            int width,
            int height)
        {
            if (camera == null)
                throw new ArgumentNullException(nameof(camera));
            if (width <= 0 || height <= 0)
                throw new ArgumentOutOfRangeException(
                    nameof(width),
                    $"Render dimensions must be positive: {width}x{height}.");

            RenderTexture previousTarget = camera.targetTexture;
            RenderTexture previousActive = RenderTexture.active;
            bool useRecoveredLinearUnormFinalTarget =
                HDRenderPipeline.IsRecoveredLinearUnormFinalTargetRequested() &&
                Shader.GetGlobalFloat("_EndfieldRecoveredPostSemantics") > 0.5f;
            RenderTexture renderTexture;
            Texture2D texture;
            if (useRecoveredLinearUnormFinalTarget)
            {
                var descriptor = new RenderTextureDescriptor(
                    width,
                    height,
                    RenderTextureFormat.ARGB32,
                    24)
                {
                    msaaSamples = 1,
                    sRGB = false,
                    useMipMap = false,
                    autoGenerateMips = false
                };
                descriptor.graphicsFormat = GraphicsFormat.R8G8B8A8_UNorm;
                renderTexture = new RenderTexture(descriptor)
                {
                    name = "Endfield Recovered Linear UNorm Capture Target"
                };
                if (!renderTexture.Create() ||
                    renderTexture.graphicsFormat != GraphicsFormat.R8G8B8A8_UNorm ||
                    renderTexture.sRGB)
                {
                    UnityEngine.Object.DestroyImmediate(renderTexture);
                    throw new InvalidOperationException(
                        "Could not create the exact linear R8G8B8A8_UNorm capture target " +
                        "required by the recovered final-display selector.");
                }
                // ReadPixels and PNG encoding must preserve the already OETF-encoded
                // channel bytes; a linear Texture2D prevents an additional transfer.
                texture = new Texture2D(
                    renderTexture.width,
                    renderTexture.height,
                    TextureFormat.RGBA32,
                    false,
                    true);
            }
            else
            {
                renderTexture = new RenderTexture(width, height, 24, RenderTextureFormat.ARGB32);
                texture = new Texture2D(
                    renderTexture.width,
                    renderTexture.height,
                    TextureFormat.RGBA32,
                    false);
            }
            try
            {
                if (IsEnvironmentFlagEnabled(
                        CumulativeCharInfoDiagnosticEnvironmentVariable))
                {
                    // PARTIAL/NON-ORIGINAL diagnostic only. Three small
                    // same-camera renders let the focused screen-shadow
                    // producer perform its two identical GPU readbacks before
                    // the final 4K beauty render. Changing dimensions then
                    // rebuilds its private sidecar resources for the final
                    // consumer without enabling the generic screen/direct
                    // audit or changing ordinary preview behavior.
                    RunCumulativeCharInfoDiagnosticValidation(camera);
                }
                camera.targetTexture = renderTexture;
                RenderTexture.active = renderTexture;
                camera.Render();
                texture.ReadPixels(new Rect(0, 0, renderTexture.width, renderTexture.height), 0, 0);
                texture.Apply();
                File.WriteAllBytes(path, texture.EncodeToPNG());
            }
            finally
            {
                camera.targetTexture = previousTarget;
                RenderTexture.active = previousActive;
                UnityEngine.Object.DestroyImmediate(texture);
                UnityEngine.Object.DestroyImmediate(renderTexture);
            }
        }

        private static void RunCumulativeCharInfoDiagnosticValidation(
            Camera camera)
        {
            RenderTexture previousTarget = camera.targetTexture;
            var descriptor = new RenderTextureDescriptor(
                CumulativeDiagnosticValidationWidth,
                CumulativeDiagnosticValidationHeight,
                RenderTextureFormat.ARGB32,
                24)
            {
                msaaSamples = 1,
                sRGB = false,
                useMipMap = false,
                autoGenerateMips = false
            };
            var validationTarget = new RenderTexture(descriptor)
            {
                name = "PARTIAL NON-ORIGINAL CharInfo cumulative validation target",
                hideFlags = HideFlags.HideAndDontSave
            };
            try
            {
                if (!validationTarget.Create())
                {
                    throw new InvalidOperationException(
                        "Could not create the explicit cumulative CharInfo " +
                        "screen-shadow validation target.");
                }
                camera.targetTexture = validationTarget;
                for (int frame = 0; frame < 3; frame++)
                {
                    camera.Render();
                    AsyncGPUReadback.WaitAllRequests();
                }
            }
            finally
            {
                camera.targetTexture = previousTarget;
                validationTarget.Release();
                UnityEngine.Object.DestroyImmediate(validationTarget);
            }
        }

        private static void FrameCameraToRuntimeReferenceEyes(
            Camera camera,
            Transform actorRoot,
            Vector2 referenceEyeMidpointFromTop,
            float referenceEyeSpanFraction,
            float fieldOfView)
        {
            Transform leftEye = FindDescendantByName(actorRoot, "faceLfIrisJoint")
                ?? FindDescendantByName(actorRoot, "eyeLf03IrissdJoint");
            Transform rightEye = FindDescendantByName(actorRoot, "faceRtIrisJoint")
                ?? FindDescendantByName(actorRoot, "eyeRt03IrissdJoint");
            if (leftEye == null || rightEye == null)
                throw new InvalidOperationException($"Runtime-reference eye anchors are missing under {actorRoot.name}.");

            camera.orthographic = false;
            camera.fieldOfView = fieldOfView;
            float aspect = (float)RuntimeReferenceRenderWidth / RuntimeReferenceRenderHeight;
            camera.aspect = aspect;
            float tangentVertical = Mathf.Tan(camera.fieldOfView * 0.5f * Mathf.Deg2Rad);
            Vector3 eyeMidpoint = (leftEye.position + rightEye.position) * 0.5f;
            float eyeSpanWorld = Mathf.Abs(rightEye.position.x - leftEye.position.x);
            float distance = eyeSpanWorld /
                Mathf.Max(0.0001f, 2f * referenceEyeSpanFraction * tangentVertical * aspect);
            float desiredScreenY = 1f - referenceEyeMidpointFromTop.y;
            float eyeOffsetX = (referenceEyeMidpointFromTop.x - 0.5f) * 2f * distance * tangentVertical * aspect;
            float eyeOffsetY = (desiredScreenY - 0.5f) * 2f * distance * tangentVertical;

            camera.transform.position = new Vector3(
                eyeMidpoint.x - eyeOffsetX,
                eyeMidpoint.y - eyeOffsetY,
                eyeMidpoint.z + distance);
            camera.transform.rotation = Quaternion.LookRotation(Vector3.back, Vector3.up);
            camera.nearClipPlane = PreviewNearClip;
            camera.farClipPlane = Mathf.Max(100f, distance * 8f);
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = PreviewBackgroundColor;
            EditorUtility.SetDirty(camera);
        }

        internal static void FrameCameraToRecoveredOperatorCamera(
            Camera camera,
            string actorName)
        {
            // Authored Overview vcam endpoint plus its centered, zero-damping
            // Composer LookAt target, read from
            // charinfo_overview_camera_contract.json. That contract is built
            // from the track_chr_<template>.prefab Cinemachine rigs and covers
            // 31 characters; it reproduces the two values that were previously
            // hard-coded here. Cinemachine Composer owns the settled physical
            // orientation, so the serialized vcam quaternion is recorded in the
            // contract but not applied directly.
            //
            // Field of view, near and far come from the same Cinemachine lens
            // rather than from the call site. Field of view varies per
            // character across five distinct values just above 20 degrees, so
            // the single constant the callers used was wrong for 13 of 31.
            EndfieldRecoveredOverviewCameraContract.Entry cameraEntry =
                EndfieldRecoveredOverviewCameraContract.Resolve(actorName);

            camera.orthographic = false;
            camera.fieldOfView = cameraEntry.FieldOfView;
            camera.aspect = (float)RuntimeReferenceRenderWidth / RuntimeReferenceRenderHeight;
            Vector3 cameraPosition = cameraEntry.CameraPosition;
            Vector3 lookAtPosition = cameraEntry.LookAtPosition;
            camera.transform.position = cameraPosition;
            camera.transform.rotation = Quaternion.LookRotation(
                lookAtPosition - cameraPosition,
                Vector3.up);
            EndfieldRecoveredCharInfoGyroscopeCameraState.TryApplyOverview(
                camera,
                actorName,
                lookAtPosition);
            camera.nearClipPlane = cameraEntry.NearClipPlane;
            camera.farClipPlane = cameraEntry.FarClipPlane;
            EndfieldRecoveredCharInfoSky sourceSky =
                camera.GetComponent<EndfieldRecoveredCharInfoSky>();
            camera.clearFlags =
                sourceSky != null && sourceSky.SourcePhysicalHdrRequested
                    ? CameraClearFlags.Skybox
                    : CameraClearFlags.SolidColor;
            camera.backgroundColor = PreviewBackgroundColor;
            EditorUtility.SetDirty(camera);
        }

        private static void ApplyRuntimeReferenceCompositorTranslation(
            Camera camera,
            string actorName)
        {
            // These are image-space translations measured directly from the
            // supplied 3840x2160 front_full captures after using the recovered
            // raw virtual-camera transform. They model the still-unrecovered
            // Cinemachine/actor-root/render-texture composition stage without
            // altering the authoritative camera position, rotation, or FOV.
            Vector2 pixelOffset = string.Equals(
                actorName,
                "Wulfa",
                StringComparison.OrdinalIgnoreCase)
                ? new Vector2(-445.54f, 222.35f)
                : new Vector2(184.0f, 184.0f);

            Matrix4x4 projection = camera.projectionMatrix;
            projection.m02 += -2.0f * pixelOffset.x / RuntimeReferenceRenderWidth;
            projection.m12 += 2.0f * pixelOffset.y / RuntimeReferenceRenderHeight;
            camera.projectionMatrix = projection;
            EditorUtility.SetDirty(camera);
        }

        private static bool IsEnvironmentFlagEnabled(string variableName)
        {
            string value = Environment.GetEnvironmentVariable(variableName);
            if (string.IsNullOrWhiteSpace(value))
                return false;

            value = value.Trim();
            return string.Equals(value, "1", StringComparison.OrdinalIgnoreCase) ||
                   string.Equals(value, "true", StringComparison.OrdinalIgnoreCase) ||
                   string.Equals(value, "yes", StringComparison.OrdinalIgnoreCase) ||
                   string.Equals(value, "on", StringComparison.OrdinalIgnoreCase);
        }

        [Serializable]
        private sealed class ComparisonCameraOverride
        {
            public string cameraId = string.Empty;
            public float[] position = Array.Empty<float>();
            public float[] rotation = Array.Empty<float>();
            public float fieldOfView;
            public float nearClipPlane;
            public float farClipPlane;
        }

        private static void ApplyComparisonCameraOverrideIfRequested(Camera camera)
        {
            string payload = Environment.GetEnvironmentVariable(
                ComparisonCameraEnvironmentVariable);
            if (string.IsNullOrWhiteSpace(payload))
                return;

            ComparisonCameraOverride contract;
            try
            {
                contract = JsonUtility.FromJson<ComparisonCameraOverride>(payload);
            }
            catch (Exception exception)
            {
                throw new InvalidDataException(
                    $"Could not parse {ComparisonCameraEnvironmentVariable}: " +
                    exception.Message,
                    exception);
            }
            if (contract == null ||
                contract.position == null || contract.position.Length != 3 ||
                contract.rotation == null || contract.rotation.Length != 4 ||
                string.IsNullOrWhiteSpace(contract.cameraId) ||
                contract.fieldOfView <= 0f ||
                contract.nearClipPlane <= 0f ||
                contract.farClipPlane <= contract.nearClipPlane)
            {
                throw new InvalidDataException(
                    $"{ComparisonCameraEnvironmentVariable} is incomplete or invalid.");
            }
            foreach (float value in contract.position)
            {
                if (float.IsNaN(value) || float.IsInfinity(value))
                    throw new InvalidDataException(
                        "Comparison camera position is non-finite.");
            }
            foreach (float value in contract.rotation)
            {
                if (float.IsNaN(value) || float.IsInfinity(value))
                    throw new InvalidDataException(
                        "Comparison camera rotation is non-finite.");
            }

            camera.orthographic = false;
            camera.transform.position = new Vector3(
                contract.position[0],
                contract.position[1],
                contract.position[2]);
            camera.transform.rotation = new Quaternion(
                contract.rotation[0],
                contract.rotation[1],
                contract.rotation[2],
                contract.rotation[3]);
            camera.fieldOfView = contract.fieldOfView;
            camera.aspect = (float)RuntimeReferenceRenderWidth /
                RuntimeReferenceRenderHeight;
            camera.nearClipPlane = contract.nearClipPlane;
            camera.farClipPlane = contract.farClipPlane;
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = PreviewBackgroundColor;
            camera.ResetProjectionMatrix();
            EditorUtility.SetDirty(camera);
            Debug.Log(
                $"Applied common comparison camera '{contract.cameraId}' " +
                $"at {camera.transform.position} fov={camera.fieldOfView:0.###}.");
        }

        private static int ReadRecoveredPunctualShadowTileResolution()
        {
            string value = Environment.GetEnvironmentVariable(
                RecoveredPunctualShadowTileResolutionEnvironmentVariable);
            if (string.IsNullOrWhiteSpace(value))
            {
                // Installed RTX 5080 device-default HGRP tier 5000 resolves to
                // the recovered desktop B=1024 profile. B=512 remains an exact
                // source-backed lower quality profile, not a fitted option.
                return 1024;
            }

            int resolution;
            if (int.TryParse(
                    value.Trim(),
                    NumberStyles.Integer,
                    CultureInfo.InvariantCulture,
                    out resolution) &&
                (resolution == 512 || resolution == 1024))
            {
                return resolution;
            }
            throw new InvalidDataException(
                $"{RecoveredPunctualShadowTileResolutionEnvironmentVariable} must be " +
                "512 or 1024.");
        }

        private static Transform FindDescendantByName(Transform root, string name)
        {
            if (root == null)
                return null;
            foreach (Transform descendant in root.GetComponentsInChildren<Transform>(true))
            {
                if (descendant != null && string.Equals(descendant.name, name, StringComparison.OrdinalIgnoreCase))
                    return descendant;
            }
            return null;
        }

        private static Vector3 ReferenceFrameTarget(Bounds bounds)
        {
            float span = ReferenceVerticalSpan(bounds);
            float y = bounds.max.y - span * PreviewReferenceTopBias;
            return new Vector3(bounds.center.x, y, bounds.center.z);
        }

        private static float ReferenceVerticalSpan(Bounds bounds)
        {
            return Mathf.Max(0.9f, bounds.size.y * PreviewReferenceVerticalCoverage);
        }

        private static void FrameCamera(Camera camera, Bounds bounds)
        {
            camera.orthographic = false;
            camera.fieldOfView = PreviewFieldOfView;
            Vector3 target = ReferenceFrameTarget(bounds);
            float span = ReferenceVerticalSpan(bounds);
            float distance = span / (2f * Mathf.Tan(camera.fieldOfView * 0.5f * Mathf.Deg2Rad));
            distance = Mathf.Max(distance, bounds.extents.z + 0.8f);
            camera.transform.position = target + new Vector3(0f, span * 0.015f, distance);
            camera.transform.rotation = Quaternion.LookRotation(target - camera.transform.position, Vector3.up);
            camera.nearClipPlane = PreviewNearClip;
            camera.farClipPlane = Mathf.Max(100f, distance * 8f);
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = PreviewBackgroundColor;
        }

        private static void FrameMultiCharacterShadowAuditCamera(
            Camera camera,
            Bounds bounds,
            float outputAspect)
        {
            camera.orthographic = false;
            camera.fieldOfView = PreviewFieldOfView;
            float verticalHalfAngle =
                camera.fieldOfView * 0.5f * Mathf.Deg2Rad;
            float horizontalHalfAngle = Mathf.Atan(
                Mathf.Tan(verticalHalfAngle) *
                Mathf.Max(outputAspect, 0.01f));
            float verticalDistance =
                bounds.extents.y / Mathf.Tan(verticalHalfAngle);
            float horizontalDistance =
                bounds.extents.x / Mathf.Tan(horizontalHalfAngle);
            float distance =
                Mathf.Max(verticalDistance, horizontalDistance) +
                bounds.extents.z +
                0.45f;
            camera.transform.position =
                bounds.center + new Vector3(0f, 0f, distance);
            camera.transform.rotation = Quaternion.LookRotation(
                bounds.center - camera.transform.position,
                Vector3.up);
            camera.nearClipPlane = PreviewNearClip;
            camera.farClipPlane = Mathf.Max(100f, distance * 8f);
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = PreviewBackgroundColor;
        }

        private static void FrameFarCamera(Camera camera, Bounds bounds)
        {
            camera.orthographic = false;
            camera.fieldOfView = PreviewFieldOfView;
            float radius = Mathf.Max(0.6f, bounds.extents.magnitude);
            camera.transform.position = bounds.center + new Vector3(0f, radius * 0.75f, radius * 5.8f);
            camera.transform.rotation = Quaternion.LookRotation(bounds.center - camera.transform.position, Vector3.up);
            camera.nearClipPlane = PreviewNearClip;
            camera.farClipPlane = Mathf.Max(100f, radius * 12f);
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = PreviewBackgroundColor;
        }

        private static Texture2D ImportTexture(string sourcePath, string materialProperty, string actorGeneratedRoot)
        {
            if (string.IsNullOrEmpty(sourcePath) || !File.Exists(sourcePath))
                return null;
            string textureName = Path.GetFileName(sourcePath);
            string assetPath = $"{actorGeneratedRoot}/Textures/{Safe(textureName)}";
            if (TextureImportCache.TryGetValue(assetPath, out Texture2D cachedTexture) && cachedTexture != null)
                return cachedTexture;

            string fullAssetPath = Path.Combine(Directory.GetCurrentDirectory(), assetPath);
            Directory.CreateDirectory(Path.GetDirectoryName(fullAssetPath) ?? ".");
            bool copied = !File.Exists(fullAssetPath) || new FileInfo(fullAssetPath).Length != new FileInfo(sourcePath).Length;
            if (copied)
                File.Copy(sourcePath, fullAssetPath, true);

            Texture2D texture = AssetDatabase.LoadAssetAtPath<Texture2D>(assetPath);
            if (texture == null || copied)
                AssetDatabase.ImportAsset(assetPath, ImportAssetOptions.ForceUpdate);

            var importer = AssetImporter.GetAtPath(assetPath) as TextureImporter;
            if (importer != null)
            {
                if (ConfigureTextureImporter(importer, materialProperty, textureName))
                    importer.SaveAndReimport();
            }
            texture = AssetDatabase.LoadAssetAtPath<Texture2D>(assetPath);
            if (texture != null)
                TextureImportCache[assetPath] = texture;
            return texture;
        }

        private static bool ConfigureTextureImporter(TextureImporter importer, string materialProperty, string textureName)
        {
            bool changed = false;
            string recoveredProperty = RecoveredTextureProperty(materialProperty);
            string key = TextureKey(recoveredProperty, textureName);
            // This heuristic is only a pre-contract fallback. Exact roster
            // textures are overridden below by their installed Texture2D
            // descriptors, whose TextureColorSpace enum is Linear=0, sRGB=1.
            bool linear = IsLinearTexture(recoveredProperty, textureName);
            changed |= SetTextureImporterValue(importer.sRGBTexture, !linear, value => importer.sRGBTexture = value);

            bool colorTexture = IsColorTexture(recoveredProperty, textureName);
            bool clothColorTexture = colorTexture && TextureKey(recoveredProperty, textureName).Contains("cloth");
            bool skinHighlightTexture = recoveredProperty == "_HighlightMap";
            bool parallaxTexture = recoveredProperty == "_ParallaxTex";
            bool overlayShadowMaskTexture = key.Contains("eyeshadow") || key.Contains("hairshadow");
            bool lookupTexture = key.Contains("lut")
                || key.Contains("ramp")
                || recoveredProperty == "_DiffRampMap"
                || recoveredProperty == "_SpecRampMap"
                || recoveredProperty == "_ShadowLutTex";
            bool packedDataTexture = linear && (key.Contains("normal")
                || key.Contains("bump")
                || key.Contains("_hn.")
                || key.Contains("metallic")
                || key.Contains("gloss")
                || key.Contains("outline")
                || key.Contains("mask")
                || key.Contains("line")
                || key.Contains("stroke")
                || key.Contains("parallax")
                || key.Contains("height"));

            // Recovered shaders decode packed RG/BA normals themselves. Unity's
            // NormalMap importer swizzles/reconstructs those channels and must
            // never be used for these source textures.
            if (packedDataTexture)
                changed |= SetTextureImporterValue(importer.textureType, TextureImporterType.Default, value => importer.textureType = value);

            changed |= SetTextureImporterValue(importer.mipmapEnabled, !lookupTexture, value => importer.mipmapEnabled = value);
            changed |= SetTextureImporterValue(
                importer.wrapMode,
                skinHighlightTexture
                    ? TextureWrapMode.MirrorOnce
                    : parallaxTexture ? TextureWrapMode.Repeat : TextureWrapMode.Clamp,
                value => importer.wrapMode = value);
            changed |= SetTextureImporterValue(
                importer.filterMode,
                skinHighlightTexture
                    ? FilterMode.Point
                    : lookupTexture || parallaxTexture || overlayShadowMaskTexture
                        ? FilterMode.Bilinear
                        : FilterMode.Trilinear,
                value => importer.filterMode = value);
            changed |= SetTextureImporterValue(
                importer.anisoLevel,
                skinHighlightTexture || lookupTexture || parallaxTexture || overlayShadowMaskTexture
                    ? 1
                    : clothColorTexture ? 8 : 2,
                value => importer.anisoLevel = value);

            if (colorTexture && !overlayShadowMaskTexture)
                changed |= SetTextureImporterValue(importer.alphaIsTransparency, true, value => importer.alphaIsTransparency = value);
            else
                changed |= SetTextureImporterValue(importer.alphaIsTransparency, false, value => importer.alphaIsTransparency = value);
            if (clothColorTexture || lookupTexture || packedDataTexture)
                changed |= SetTextureImporterValue(importer.textureCompression, TextureImporterCompression.Uncompressed, value => importer.textureCompression = value);

            // Exact installed Texture2D descriptors override filename/property
            // heuristics whenever the current source contract contains the
            // full PathID-bearing filename. This covers all 853 distinct
            // source objects used by the 31-character generated roster.
            changed |= ApplyOriginalTextureImportProfile(importer, textureName);

            return changed;
        }

        private static bool IsOriginalEyeShadowBaseMap(
            string materialProperty,
            string textureName)
        {
            if (materialProperty != "_BaseMap")
                return false;

            // Exact AssetMap PathIDs, encoded by AnimeStudio in the converted
            // filename. Do not widen this to generic `eyeshadow`/`_M` names:
            // the exception is backed only by these two installed objects and
            // the pinned eye_shadow_original_data_contract.json source hashes.
            string fileName = Path.GetFileName(textureName ?? string.Empty);
            return string.Equals(
                    fileName,
                    "T_actor_common_eyeshadow_01_M_p1AF9F6EE6B0D822A.png",
                    StringComparison.OrdinalIgnoreCase) ||
                string.Equals(
                    fileName,
                    "T_actor_common_eyeshadow_02_M_p214F5F1A8FB49548.png",
                    StringComparison.OrdinalIgnoreCase);
        }

        private static bool SetTextureImporterValue<T>(T current, T wanted, Action<T> assign)
        {
            if (EqualityComparer<T>.Default.Equals(current, wanted))
                return false;
            assign(wanted);
            return true;
        }

        private static string GuessMaterialPropertyFromTextureName(string textureName)
        {
            string lower = CanonicalTextureNameForClassification(textureName)
                .ToLowerInvariant();
            if (lower.Contains("lut"))
                return "_ShadowLutTex";
            if (lower.EndsWith("_rd.png") || lower.Contains("difframp"))
                return "_DiffRampMap";
            if (lower.EndsWith("_rs.png") || lower.Contains("specramp"))
                return "_SpecRampMap";
            if (lower.EndsWith("_hl.png") || lower.Contains("_hl_"))
                return "_HighlightMap";
            if (lower.EndsWith("_hn.png"))
                return "_SplitNormalMap";
            if (lower.EndsWith("_d.png"))
                return "_BaseMap";
            if (lower.EndsWith("_n.png") || lower.EndsWith("_hn.png"))
                return "_BumpMap";
            if (lower.EndsWith("_p.png") || lower.EndsWith("_m.png"))
                return "_MetallicGlossMap";
            if (lower.EndsWith("_st.png"))
                return "_OutlineMask";
            return "";
        }

        private static bool IsColorTexture(string materialProperty, string textureName)
        {
            string key = TextureKey(materialProperty, textureName);
            if (key.Contains("lut")
                || key.Contains("ramp")
                || materialProperty == "_DiffRampMap"
                || materialProperty == "_SpecRampMap"
                || materialProperty == "_ShadowLutTex")
            {
                return false;
            }
            if (key.EndsWith("_m.png")
                || key.EndsWith("_n.png")
                || key.EndsWith("_hn.png")
                || key.EndsWith("_p.png")
                || key.EndsWith("_st.png"))
            {
                return false;
            }
            return materialProperty == "_BaseMap"
                || materialProperty == "_MainTex"
                || key.EndsWith("_d.png")
                || key.EndsWith("_rd.png");
        }

        private static bool IsLinearTexture(string materialProperty, string textureName)
        {
            string key = TextureKey(materialProperty, textureName);
            return key.Contains("normal")
                || key.Contains("bump")
                || key.Contains("mask")
                || key.Contains("metallic")
                || key.Contains("gloss")
                || key.Contains("mro")
                || key.Contains("mra")
                || key.Contains("sdf")
                || key.Contains("line")
                || key.Contains("stroke")
                || key.Contains("parallax")
                || key.Contains("height")
                || key.EndsWith("_m.png")
                || key.EndsWith("_n.png")
                || key.EndsWith("_hn.png")
                || key.EndsWith("_p.png")
                || key.EndsWith("_st.png");
        }

        private static string TextureKey(string materialProperty, string textureName)
        {
            return (materialProperty + " " +
                    CanonicalTextureNameForClassification(textureName))
                .ToLowerInvariant();
        }

        private static string CanonicalTextureNameForClassification(string textureName)
        {
            string fileName = Path.GetFileName(textureName ?? "");
            string extension = Path.GetExtension(fileName);
            string stem = Path.GetFileNameWithoutExtension(fileName);
            int hashMarker = stem.LastIndexOf("_p", StringComparison.OrdinalIgnoreCase);
            if (hashMarker < 0)
                return fileName;

            int hashStart = hashMarker + 2;
            int hashLength = stem.Length - hashStart;
            if (hashLength < 8)
                return fileName;

            for (int index = hashStart; index < stem.Length; index++)
            {
                char value = stem[index];
                bool isHex = (value >= '0' && value <= '9')
                    || (value >= 'a' && value <= 'f')
                    || (value >= 'A' && value <= 'F');
                if (!isHex)
                    return fileName;
            }

            return stem.Substring(0, hashMarker) + extension;
        }

        private static void SetCurve(AnimationClip clip, string path, string property, AnimationCurve curve)
        {
            for (int i = 0; i < curve.keys.Length; i++)
            {
                AnimationUtility.SetKeyLeftTangentMode(curve, i, AnimationUtility.TangentMode.Linear);
                AnimationUtility.SetKeyRightTangentMode(curve, i, AnimationUtility.TangentMode.Linear);
            }
            AnimationUtility.SetEditorCurve(clip, EditorCurveBinding.FloatCurve(path, typeof(Transform), property), curve);
        }

        private static void ApplyClipLoopSettings(AnimationClip clip, bool loop, bool loopBlend)
        {
            if (clip == null)
                return;
            clip.wrapMode = loop ? WrapMode.Loop : WrapMode.Once;
            AnimationClipSettings settings = AnimationUtility.GetAnimationClipSettings(clip);
            settings.loopTime = loop;
            settings.loopBlend = loop && loopBlend;
            AnimationUtility.SetAnimationClipSettings(clip, settings);
        }

        private static Transform FindPath(Dictionary<string, Transform> bonesByPath, string path)
        {
            bonesByPath.TryGetValue(path, out Transform tr);
            return tr;
        }

        private static string ParentPath(string path)
        {
            int slash = path.LastIndexOf('/');
            return slash > 0 ? path.Substring(0, slash) : "";
        }

        private static string Safe(string value)
        {
            foreach (char c in Path.GetInvalidFileNameChars())
                value = value.Replace(c, '_');
            return value.Replace('/', '_').Replace('\\', '_');
        }

        private static Dictionary<string, object> Dict(object value) => value as Dictionary<string, object> ?? new Dictionary<string, object>();
        private static IList List(object value) => value as IList ?? Array.Empty<object>();
        private static string Str(object value, string fallback = "") => value == null ? fallback : Convert.ToString(value, CultureInfo.InvariantCulture) ?? fallback;
        private static bool Bool(object value) => value is bool b ? b : Str(value).Equals("true", StringComparison.OrdinalIgnoreCase);
        private static int Int(object value, int fallback = 0) => value == null ? fallback : Convert.ToInt32(value, CultureInfo.InvariantCulture);
        private static long Long(object value) => value == null ? 0L : Convert.ToInt64(value, CultureInfo.InvariantCulture);
        private static float Float(object value, float fallback = 0f) => value == null ? fallback : Convert.ToSingle(value, CultureInfo.InvariantCulture);
        private static Vector3 Vec3(IList list) => new Vector3(Float(list.Count > 0 ? list[0] : null), Float(list.Count > 1 ? list[1] : null), Float(list.Count > 2 ? list[2] : null));
        private static Quaternion Quat(IList list) => new Quaternion(Float(list.Count > 0 ? list[0] : null), Float(list.Count > 1 ? list[1] : null), Float(list.Count > 2 ? list[2] : null), Float(list.Count > 3 ? list[3] : 1f));
        private static Color ColorRgba(IList list) => new Color(Float(list.Count > 0 ? list[0] : null, 1f), Float(list.Count > 1 ? list[1] : null, 1f), Float(list.Count > 2 ? list[2] : null, 1f), Float(list.Count > 3 ? list[3] : null, 1f));

        private static List<float> FloatList(object value)
        {
            var outList = new List<float>();
            foreach (object item in List(value))
                outList.Add(Float(item));
            return outList;
        }

        private static int[] IntList(object value)
        {
            var list = List(value);
            var outList = new int[list.Count];
            for (int i = 0; i < list.Count; i++)
                outList[i] = Int(list[i]);
            return outList;
        }

        private static Matrix4x4 Matrix(Dictionary<string, object> data)
        {
            var m = new Matrix4x4();
            // The dumped Matrix4x4 uses row-vector layout, with translation in
            // M30/M31/M32. Unity's Matrix4x4 uses column-vector layout.
            m.m00 = Float(data["M00"], 1f); m.m01 = Float(data["M10"]); m.m02 = Float(data["M20"]); m.m03 = Float(data["M30"]);
            m.m10 = Float(data["M01"]); m.m11 = Float(data["M11"], 1f); m.m12 = Float(data["M21"]); m.m13 = Float(data["M31"]);
            m.m20 = Float(data["M02"]); m.m21 = Float(data["M12"]); m.m22 = Float(data["M22"], 1f); m.m23 = Float(data["M32"]);
            m.m30 = Float(data["M03"]); m.m31 = Float(data["M13"]); m.m32 = Float(data["M23"]); m.m33 = Float(data["M33"], 1f);
            return m;
        }
    }

    internal static class ManifestMiniJson
    {
        public static object Deserialize(string json)
        {
            return Parser.Parse(json);
        }

        private sealed class Parser
        {
            private readonly string json;
            private int index;

            private Parser(string json)
            {
                this.json = json;
            }

            public static object Parse(string json)
            {
                return new Parser(json).ParseValue();
            }

            private object ParseValue()
            {
                SkipWhitespace();
                if (index >= json.Length)
                    return null;
                char c = json[index];
                if (c == '{') return ParseObject();
                if (c == '[') return ParseArray();
                if (c == '"') return ParseString();
                if (c == '-' || char.IsDigit(c)) return ParseNumber();
                if (Match("true")) return true;
                if (Match("false")) return false;
                if (Match("null")) return null;
                throw new FormatException($"Unexpected JSON token at {index}: {c}");
            }

            private Dictionary<string, object> ParseObject()
            {
                var table = new Dictionary<string, object>();
                index++;
                while (true)
                {
                    SkipWhitespace();
                    if (json[index] == '}')
                    {
                        index++;
                        return table;
                    }
                    string key = ParseString();
                    SkipWhitespace();
                    Expect(':');
                    table[key] = ParseValue();
                    SkipWhitespace();
                    if (json[index] == ',')
                    {
                        index++;
                        continue;
                    }
                    Expect('}');
                    return table;
                }
            }

            private List<object> ParseArray()
            {
                var array = new List<object>();
                index++;
                while (true)
                {
                    SkipWhitespace();
                    if (json[index] == ']')
                    {
                        index++;
                        return array;
                    }
                    array.Add(ParseValue());
                    SkipWhitespace();
                    if (json[index] == ',')
                    {
                        index++;
                        continue;
                    }
                    Expect(']');
                    return array;
                }
            }

            private string ParseString()
            {
                Expect('"');
                var builder = new StringBuilder();
                while (index < json.Length)
                {
                    char c = json[index++];
                    if (c == '"')
                        return builder.ToString();
                    if (c != '\\')
                    {
                        builder.Append(c);
                        continue;
                    }
                    char esc = json[index++];
                    switch (esc)
                    {
                        case '"': builder.Append('"'); break;
                        case '\\': builder.Append('\\'); break;
                        case '/': builder.Append('/'); break;
                        case 'b': builder.Append('\b'); break;
                        case 'f': builder.Append('\f'); break;
                        case 'n': builder.Append('\n'); break;
                        case 'r': builder.Append('\r'); break;
                        case 't': builder.Append('\t'); break;
                        case 'u':
                            string hex = json.Substring(index, 4);
                            builder.Append((char)Convert.ToInt32(hex, 16));
                            index += 4;
                            break;
                    }
                }
                throw new FormatException("Unterminated JSON string");
            }

            private object ParseNumber()
            {
                int start = index;
                if (json[index] == '-')
                    index++;
                while (index < json.Length && char.IsDigit(json[index]))
                    index++;
                bool isFloat = false;
                if (index < json.Length && json[index] == '.')
                {
                    isFloat = true;
                    index++;
                    while (index < json.Length && char.IsDigit(json[index]))
                        index++;
                }
                if (index < json.Length && (json[index] == 'e' || json[index] == 'E'))
                {
                    isFloat = true;
                    index++;
                    if (json[index] == '+' || json[index] == '-')
                        index++;
                    while (index < json.Length && char.IsDigit(json[index]))
                        index++;
                }
                string text = json.Substring(start, index - start);
                if (isFloat)
                    return double.Parse(text, CultureInfo.InvariantCulture);
                if (long.TryParse(text, NumberStyles.Integer, CultureInfo.InvariantCulture, out long l))
                    return l;
                return double.Parse(text, CultureInfo.InvariantCulture);
            }

            private bool Match(string token)
            {
                if (string.CompareOrdinal(json, index, token, 0, token.Length) != 0)
                    return false;
                index += token.Length;
                return true;
            }

            private void Expect(char expected)
            {
                SkipWhitespace();
                if (index >= json.Length || json[index] != expected)
                    throw new FormatException($"Expected '{expected}' at {index}");
                index++;
            }

            private void SkipWhitespace()
            {
                while (index < json.Length && char.IsWhiteSpace(json[index]))
                    index++;
            }
        }
    }
}

using System;
using System.IO;
using System.Text;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Builds a disposable D3D11 player whose source target remains a real
    /// ParticleSystemRenderer. The runtime also creates one same-scene positive
    /// control with the known-good compatibility material. The generated scene
    /// is a probe artifact; the authored prefab is never modified.
    /// </summary>
    public static class EndfieldLiZhiyanM23ParticleRendererCaptureBuilder
    {
        private const string PrefabPath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Lizhiyan/" +
            "Effects/OverviewPeakParticles/P_fxui_lizhiyan_overview_start_04_2.prefab";
        private const string GeneratedRoot =
            "Assets/EndfieldGraphShaderLab/Generated/Diagnostics/LiZhiyanM23ParticleRendererCapture";
        private const string ScenePath = GeneratedRoot + "/LiZhiyanM23ParticleRendererCapture.unity";
        private const string CompatibilityMaterialPath =
            GeneratedRoot + "/M23ParticleSubmissionCompatibility.mat";
        private const string OutputRoot = "scratch/reverse_engineering/lizhiyan_m23_particle_renderer_capture";
        private const string TargetHierarchy = "P_fxui_lizhiyan_overview_start_04_2/xuanzhuan03";
        private const long TargetMaterialPathId = -430604955415889784L;
        private const string ActivationArgument =
            EndfieldLiZhiyanM23ParticleRendererCaptureRuntime.ActivationArgument;

        [MenuItem("Endfield/Character Recovery Lab/Build Li Zhiyan M23 Source Particle Renderer Capture")]
        public static void BuildAndValidate()
        {
            Build();
        }

        /// <summary>
        /// Batch entry point for Unity -executeMethod.  The resulting player is
        /// launched separately through DXCap with ActivationArgument.
        /// </summary>
        public static void BuildPlayerCommandLine()
        {
            Build();
        }

        private static void Build()
        {
            EndfieldLiZhiyanOverviewPeakParticleEffectImporter.ValidateBatch();
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
            if (prefab == null)
                throw new FileNotFoundException("Missing generated M23 prefab.", PrefabPath);

            EnsureAssetFolder(GeneratedRoot);
            if (AssetDatabase.LoadAssetAtPath<SceneAsset>(ScenePath) != null)
                AssetDatabase.DeleteAsset(ScenePath);

            Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            GameObject instance = PrefabUtility.InstantiatePrefab(prefab, scene) as GameObject;
            if (instance == null)
                throw new InvalidOperationException("Could not instantiate generated M23 prefab.");
            instance.name = "P_fxui_lizhiyan_overview_start_04_2";
            instance.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
            instance.transform.localScale = Vector3.one;

            EndfieldRecoveredParticleEffectSource marker =
                instance.GetComponent<EndfieldRecoveredParticleEffectSource>();
            Require(marker != null && marker.contractSchema ==
                "endfield.lizhiyan-overview-peak-particle-effects.v1",
                "M23 source marker contract is missing or drifted.");
            EndfieldRecoveredParticleNodeSource node = FindNode(marker, TargetHierarchy);
            Require(node != null && node.materialPathIds.Length == 1 &&
                node.materialPathIds[0] == TargetMaterialPathId,
                "M23 target identity does not match the source contract.");

            Transform target = instance.transform.Find("xuanzhuan03");
            Require(target != null, "M23 target hierarchy is missing: " + TargetHierarchy);
            ParticleSystemRenderer targetRenderer = target.GetComponent<ParticleSystemRenderer>();
            Require(targetRenderer != null, "M23 target ParticleSystemRenderer is missing.");
            Material diagnostic = LoadDiagnosticMaterial(targetRenderer, TargetMaterialPathId);
            if (diagnostic != null)
                targetRenderer.sharedMaterials = new[] { diagnostic };

            var runtime = instance.AddComponent<EndfieldLiZhiyanM23ParticleRendererCaptureRuntime>();
            runtime.ConfigureCompatibilityMaterial(BuildCompatibilityMaterial());
            runtime.enabled = true;
            SetLayerRecursively(instance.transform, 30);

            GameObject cameraObject = new GameObject("LiZhiyanM23ParticleRendererCaptureCamera");
            SceneManager.MoveGameObjectToScene(cameraObject, scene);
            cameraObject.tag = "MainCamera";
            cameraObject.layer = 30;
            cameraObject.transform.SetPositionAndRotation(
                new Vector3(0.0f, 0.0f, -10.0f), Quaternion.identity);
            Camera camera = cameraObject.AddComponent<Camera>();
            camera.enabled = true;
            camera.cullingMask = 1 << 30;
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = Color.black;
            camera.nearClipPlane = 0.01f;
            camera.farClipPlane = 1000.0f;
            camera.fieldOfView = 60.0f;

            if (!EditorSceneManager.SaveScene(scene, ScenePath, false))
                throw new IOException("Could not save M23 source-renderer capture scene.");
            AssetDatabase.SaveAssets();

            string projectRoot = Directory.GetParent(Application.dataPath).FullName;
            string outputRoot = Path.Combine(projectRoot, OutputRoot);
            Directory.CreateDirectory(outputRoot);
            string buildRoot = Path.Combine(projectRoot, "Builds", "LiZhiyanM23ParticleRendererCapture");
            Directory.CreateDirectory(buildRoot);
            string playerPath = Path.Combine(buildRoot, "EndfieldLiZhiyanM23ParticleRendererCapture.exe");

            GraphicsDeviceType[] previousApis = PlayerSettings.GetGraphicsAPIs(BuildTarget.StandaloneWindows64);
            bool previousDefault = PlayerSettings.GetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64);
            try
            {
                PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64, false);
                PlayerSettings.SetGraphicsAPIs(
                    BuildTarget.StandaloneWindows64,
                    new[] { GraphicsDeviceType.Direct3D11 });
                BuildReport report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
                {
                    scenes = new[] { ScenePath },
                    locationPathName = playerPath,
                    target = BuildTarget.StandaloneWindows64,
                    options = BuildOptions.Development | BuildOptions.CleanBuildCache,
                });
                if (report.summary.result != BuildResult.Succeeded)
                    throw new InvalidOperationException(
                        "M23 source-renderer standalone build failed: result=" +
                        report.summary.result + ", errors=" + report.summary.totalErrors + ".");
                File.WriteAllText(
                    Path.Combine(outputRoot, "standalone_build.json"),
                    RenderManifest(playerPath, ScenePath, diagnostic != null),
                    new UTF8Encoding(false));
            }
            finally
            {
                PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64, previousDefault);
                if (!previousDefault && previousApis != null && previousApis.Length != 0)
                    PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneWindows64, previousApis);
            }
            Debug.Log("Built Li Zhiyan M23 source ParticleSystemRenderer capture: " + playerPath);
        }

        private static Material LoadDiagnosticMaterial(
            ParticleSystemRenderer renderer, long materialPathId)
        {
            Material source = renderer.sharedMaterials != null && renderer.sharedMaterials.Length == 1
                ? renderer.sharedMaterials[0]
                : null;
            if (source == null)
                return null;
            string path = EndfieldLiZhiyanOverviewPeakParticleEffectImporter.DiagnosticMaterialPath(
                source.name, materialPathId);
            return AssetDatabase.LoadAssetAtPath<Material>(path);
        }

        private static Material BuildCompatibilityMaterial()
        {
            Shader shader = Shader.Find("Endfield/CharacterRecovery/ReferenceBackdrop");
            Require(shader != null && shader.isSupported,
                "The SRPDefaultUnlit compatibility shader is missing or unsupported.");
            Material material = AssetDatabase.LoadAssetAtPath<Material>(
                CompatibilityMaterialPath);
            if (material == null)
            {
                material = new Material(shader)
                {
                    name = "M23ParticleSubmissionCompatibility"
                };
                AssetDatabase.CreateAsset(material, CompatibilityMaterialPath);
            }
            else
            {
                material.shader = shader;
            }
            material.renderQueue = 3000;
            material.SetColor("_TopColor", Color.white);
            material.SetColor("_BottomColor", Color.white);
            EditorUtility.SetDirty(material);
            return material;
        }

        private static EndfieldRecoveredParticleNodeSource FindNode(
            EndfieldRecoveredParticleEffectSource marker, string hierarchy)
        {
            foreach (EndfieldRecoveredParticleNodeSource node in marker.particleNodes)
                if (node.hierarchy == hierarchy)
                    return node;
            return null;
        }

        private static void SetLayerRecursively(Transform root, int layer)
        {
            root.gameObject.layer = layer;
            for (int index = 0; index < root.childCount; index++)
                SetLayerRecursively(root.GetChild(index), layer);
        }

        private static void EnsureAssetFolder(string path)
        {
            string[] parts = path.Split('/');
            string current = parts[0];
            for (int index = 1; index < parts.Length; index++)
            {
                string next = current + "/" + parts[index];
                if (!AssetDatabase.IsValidFolder(next))
                    AssetDatabase.CreateFolder(current, parts[index]);
                current = next;
            }
        }

        private static string RenderManifest(string playerPath, string scenePath, bool diagnosticMaterial)
        {
            return "{\n" +
                "  \"schema\": \"endfield.lizhiyan-m23-particle-renderer-build.v1\",\n" +
                "  \"player\": \"" + Escape(playerPath) + "\",\n" +
                "  \"scene\": \"" + Escape(scenePath) + "\",\n" +
                "  \"graphics_api\": \"Direct3D11\",\n" +
                "  \"activation_argument\": \"" + ActivationArgument + "\",\n" +
                "  \"target_hierarchy\": \"" + TargetHierarchy + "\",\n" +
                "  \"target_particle_system_path_id\": 2171212438583907872,\n" +
                "  \"target_particle_renderer_path_id\": 37981486576571936,\n" +
                "  \"target_mesh_path_id\": 5776537116290261507,\n" +
                "  \"target_material_path_id\": -430604955415889784,\n" +
                "  \"diagnostic_material_assigned\": " + (diagnosticMaterial ? "true" : "false") + ",\n" +
                "  \"positive_control\": \"runtime ParticleSystemRenderer with one emitted particle and the known-good compatibility material\",\n" +
                "  \"no_bake_mesh\": true,\n" +
                "  \"no_mesh_renderer_proxy\": true,\n" +
                "  \"dxcap_command\": \"DXCap.exe -file <capture.vsglog> -frame 0+1 -terminateonsave -c <player.exe> -endfield-m23-particle-renderer-capture -endfield-m23-particle-renderer-mode=positive -endfield-m23-particle-renderer-output=<report.json> -endfield-m23-particle-renderer-quit\"\n" +
                "}\n";
        }

        private static string Escape(string value)
        {
            return (value ?? string.Empty).Replace("\\", "\\\\").Replace("\"", "\\\"");
        }

        private static void Require(bool condition, string message)
        {
            if (!condition)
                throw new InvalidOperationException(message);
        }
    }
}

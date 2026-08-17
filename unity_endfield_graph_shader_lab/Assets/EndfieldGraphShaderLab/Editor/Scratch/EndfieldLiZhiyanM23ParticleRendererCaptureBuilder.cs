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
        private const string BuiltinCompatibilityMaterialPath =
            GeneratedRoot + "/M23ParticleBuiltinCompatibility.mat";
        private const string OutputRoot = "scratch/reverse_engineering/lizhiyan_m23_particle_renderer_capture";
        private const string TargetHierarchy = "P_fxui_lizhiyan_overview_start_04_2/xuanzhuan03";
        private const long TargetMaterialPathId = -430604955415889784L;
        private const string ActivationArgument =
            EndfieldLiZhiyanM23ParticleRendererCaptureRuntime.ActivationArgument;
        private const string ForegroundWindowArgument =
            EndfieldLiZhiyanM23ParticleRendererCaptureRuntime.ForegroundWindowArgument;

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
            Material compatibilityMaterial = BuildCompatibilityMaterial();
            runtime.ConfigureCompatibilityMaterial(compatibilityMaterial);
            runtime.ConfigureBuiltinCompatibilityMaterial(BuildBuiltinCompatibilityMaterial());
            ParticleSystem serializedControlSystem;
            ParticleSystemRenderer serializedControlRenderer;
            BuildSerializedControl(
                instance,
                compatibilityMaterial,
                out serializedControlSystem,
                out serializedControlRenderer);
            runtime.ConfigureSerializedControl(
                serializedControlSystem, serializedControlRenderer);
            MeshFilter sentinelFilter;
            MeshRenderer sentinelRenderer;
            BuildSerializedSentinel(
                instance,
                compatibilityMaterial,
                out sentinelFilter,
                out sentinelRenderer);
            runtime.ConfigureSerializedSentinel(sentinelFilter, sentinelRenderer);
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

        private static Material BuildBuiltinCompatibilityMaterial()
        {
            Shader shader = Shader.Find("Unlit/Color");
            Require(shader != null && shader.isSupported,
                "The built-in Unlit/Color compatibility shader is missing or unsupported.");
            Material material = AssetDatabase.LoadAssetAtPath<Material>(
                BuiltinCompatibilityMaterialPath);
            if (material == null)
            {
                material = new Material(shader)
                {
                    name = "M23ParticleBuiltinCompatibility"
                };
                AssetDatabase.CreateAsset(material, BuiltinCompatibilityMaterialPath);
            }
            else
            {
                material.shader = shader;
            }
            material.renderQueue = 3000;
            material.color = Color.white;
            EditorUtility.SetDirty(material);
            return material;
        }

        private static void BuildSerializedControl(
            GameObject sourceInstance,
            Material compatibilityMaterial,
            out ParticleSystem system,
            out ParticleSystemRenderer renderer)
        {
            GameObject controlObject = new GameObject(
                "M23ParticleRendererSerializedAdmissionControl");
            SceneManager.MoveGameObjectToScene(controlObject, sourceInstance.scene);
            controlObject.layer = 30;
            controlObject.transform.SetPositionAndRotation(
                new Vector3(-0.086f, 1.064f, 0.5f), Quaternion.identity);
            system = controlObject.AddComponent<ParticleSystem>();
            renderer = controlObject.GetComponent<ParticleSystemRenderer>();
            Require(renderer != null, "Could not create serialized control renderer.");

            ParticleSystem.MainModule main = system.main;
            main.playOnAwake = false;
            main.loop = false;
            main.startDelay = 0.0f;
            main.startLifetime = 10.0f;
            main.startSpeed = 0.0f;
            main.startSize = 1.0f;
            main.maxParticles = 1;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            ParticleSystem.EmissionModule emission = system.emission;
            emission.enabled = false;
            renderer.renderMode = ParticleSystemRenderMode.Billboard;
            renderer.sharedMaterial = compatibilityMaterial;
            renderer.enableGPUInstancing = false;
            renderer.allowOcclusionWhenDynamic = false;
            renderer.sortingFudge = 0.0f;
            renderer.enabled = true;
        }

        private static void BuildSerializedSentinel(
            GameObject sourceInstance,
            Material compatibilityMaterial,
            out MeshFilter filter,
            out MeshRenderer renderer)
        {
            GameObject sentinel = GameObject.CreatePrimitive(PrimitiveType.Quad);
            sentinel.name = "M23ParticleRendererCameraCullingSentinel";
            SceneManager.MoveGameObjectToScene(sentinel, sourceInstance.scene);
            sentinel.layer = 30;
            sentinel.transform.SetPositionAndRotation(
                new Vector3(-0.086f, 1.064f, 0.5f), Quaternion.identity);
            sentinel.transform.localScale = Vector3.one * 0.75f;
            filter = sentinel.GetComponent<MeshFilter>();
            renderer = sentinel.GetComponent<MeshRenderer>();
            Require(filter != null && renderer != null,
                "Could not create serialized MeshRenderer camera/culling sentinel.");
            renderer.sharedMaterial = compatibilityMaterial;
            renderer.enabled = true;
            renderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            renderer.receiveShadows = false;
            renderer.allowOcclusionWhenDynamic = false;
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
                "  \"builtin_differential_mode\": \"clears GraphicsSettings and QualitySettings render pipelines; uses Unlit/Color control only; shader parity not claimed\",\n" +
                "  \"no_bake_mesh\": true,\n" +
                "  \"no_mesh_renderer_proxy\": true,\n" +
                "  \"dxcap_command\": \"DXCap.exe -file <capture.vsglog> -frame 0+1 -terminateonsave -c <player.exe> -endfield-m23-particle-renderer-capture -endfield-m23-particle-renderer-mode=positive -endfield-m23-particle-renderer-output=<report.json> -endfield-m23-particle-renderer-quit\",\n" +
                "  \"foreground_window_command\": \"DXCap.exe -file <foreground-window.vsglog> -frame 0+1 -terminateonsave -c <player.exe> -endfield-m23-particle-renderer-capture -endfield-m23-particle-renderer-mode=positive " + ForegroundWindowArgument + " -endfield-m23-particle-renderer-output=<foreground-window.json> -endfield-m23-particle-renderer-quit\",\n" +
                "  \"builtin_differential_command\": \"<player.exe> -force-d3d11 -endfield-m23-particle-renderer-capture -endfield-m23-particle-renderer-mode=builtin-pipeline -endfield-m23-particle-renderer-output=<report.json> -endfield-m23-particle-renderer-quit\",\n" +
                "  \"control_disabled_command\": \"DXCap.exe -file <control-disabled.vsglog> -frame 0+1 -terminateonsave -c <player.exe> -endfield-m23-particle-renderer-capture -endfield-m23-particle-renderer-mode=control-disabled -endfield-m23-particle-renderer-output=<control-disabled.json> -endfield-m23-particle-renderer-quit\",\n" +
                "  \"serialized_control_command\": \"DXCap.exe -file <serialized-control.vsglog> -frame 0+1 -terminateonsave -c <player.exe> -endfield-m23-particle-renderer-capture -endfield-m23-particle-renderer-mode=serialized-control -endfield-m23-particle-renderer-output=<serialized-control.json> -endfield-m23-particle-renderer-quit\",\n" +
                "  \"serialized_control_disabled_command\": \"DXCap.exe -file <serialized-control-disabled.vsglog> -frame 0+1 -terminateonsave -c <player.exe> -endfield-m23-particle-renderer-capture -endfield-m23-particle-renderer-mode=serialized-control-disabled -endfield-m23-particle-renderer-output=<serialized-control-disabled.json> -endfield-m23-particle-renderer-quit\",\n" +
                "  \"sentinel_enabled_command\": \"DXCap.exe -file <sentinel-enabled.vsglog> -frame 0+1 -terminateonsave -c <player.exe> -endfield-m23-particle-renderer-capture -endfield-m23-particle-renderer-mode=sentinel-enabled -endfield-m23-particle-renderer-output=<sentinel-enabled.json> -endfield-m23-particle-renderer-quit\",\n" +
                "  \"sentinel_disabled_command\": \"DXCap.exe -file <sentinel-disabled.vsglog> -frame 0+1 -terminateonsave -c <player.exe> -endfield-m23-particle-renderer-capture -endfield-m23-particle-renderer-mode=sentinel-disabled -endfield-m23-particle-renderer-output=<sentinel-disabled.json> -endfield-m23-particle-renderer-quit\",\n" +
                "  \"mesh_control_command\": \"DXCap.exe -file <mesh-control.vsglog> -frame 0+1 -terminateonsave -c <player.exe> -endfield-m23-particle-renderer-capture -endfield-m23-particle-renderer-mode=mesh-control -endfield-m23-particle-renderer-frames=2 " + ForegroundWindowArgument + " -endfield-m23-particle-renderer-output=<mesh-control.json> -endfield-m23-particle-renderer-quit\",\n" +
                "  \"mesh_control_time_guidance\": \"This is a time-based player-loop diagnostic: use the foreground flag, allow the player to advance two setup frames, and compare the resulting DXCap frame against the disabled/control baseline; do not claim source shader parity.\",\n" +
                "  \"source_manual_particle_command\": \"DXCap.exe -file <source-manual-particle.vsglog> -frame 0+1 -terminateonsave -c <player.exe> -endfield-m23-particle-renderer-capture -endfield-m23-particle-renderer-mode=source-manual-particle -endfield-m23-particle-renderer-frames=2 " + ForegroundWindowArgument + " -endfield-m23-particle-renderer-output=<source-manual-particle.json> -endfield-m23-particle-renderer-quit\",\n" +
                "  \"source_manual_particle_time_guidance\": \"Use a time-based player-loop capture: foreground the standalone player, advance two setup frames, then inspect the captured frame and report together; this tests component admission only, not source visual parity.\",\n" +
                "  \"source_field_matrix_guidance\": \"Run each source-field-* mode separately from the same build with the foreground flag, 30 setup frames, and DXCap -frame 7s; pair the XML with its runtime report, which fails closed if an unrelated family changes.\",\n" +
                "  \"source_field_lifetime_command\": \"DXCap.exe -file <source-field-lifetime.vsglog> -frame 7s -terminateonsave -c <player.exe> -endfield-m23-particle-renderer-capture -endfield-m23-particle-renderer-mode=source-field-lifetime -endfield-m23-particle-renderer-frames=30 " + ForegroundWindowArgument + " -endfield-m23-particle-renderer-output=<source-field-lifetime.json>\",\n" +
                "  \"source_field_size_command\": \"DXCap.exe -file <source-field-size.vsglog> -frame 7s -terminateonsave -c <player.exe> -endfield-m23-particle-renderer-capture -endfield-m23-particle-renderer-mode=source-field-size -endfield-m23-particle-renderer-frames=30 " + ForegroundWindowArgument + " -endfield-m23-particle-renderer-output=<source-field-size.json>\",\n" +
                "  \"source_field_color_command\": \"DXCap.exe -file <source-field-color.vsglog> -frame 7s -terminateonsave -c <player.exe> -endfield-m23-particle-renderer-capture -endfield-m23-particle-renderer-mode=source-field-color -endfield-m23-particle-renderer-frames=30 " + ForegroundWindowArgument + " -endfield-m23-particle-renderer-output=<source-field-color.json>\",\n" +
                "  \"source_field_rotation_command\": \"DXCap.exe -file <source-field-rotation.vsglog> -frame 7s -terminateonsave -c <player.exe> -endfield-m23-particle-renderer-capture -endfield-m23-particle-renderer-mode=source-field-rotation -endfield-m23-particle-renderer-frames=30 " + ForegroundWindowArgument + " -endfield-m23-particle-renderer-output=<source-field-rotation.json>\",\n" +
                "  \"source_field_velocity_command\": \"DXCap.exe -file <source-field-velocity.vsglog> -frame 7s -terminateonsave -c <player.exe> -endfield-m23-particle-renderer-capture -endfield-m23-particle-renderer-mode=source-field-velocity -endfield-m23-particle-renderer-frames=30 " + ForegroundWindowArgument + " -endfield-m23-particle-renderer-output=<source-field-velocity.json>\",\n" +
                "  \"source_field_custom1_command\": \"DXCap.exe -file <source-field-custom1.vsglog> -frame 7s -terminateonsave -c <player.exe> -endfield-m23-particle-renderer-capture -endfield-m23-particle-renderer-mode=source-field-custom1 -endfield-m23-particle-renderer-frames=30 " + ForegroundWindowArgument + " -endfield-m23-particle-renderer-output=<source-field-custom1.json>\",\n" +
                "  \"source_republish_identical_command\": \"DXCap.exe -file <source-republish-identical.vsglog> -frame 7s -terminateonsave -c <player.exe> -endfield-m23-particle-renderer-capture -endfield-m23-particle-renderer-mode=source-republish-identical -endfield-m23-particle-renderer-frames=30 " + ForegroundWindowArgument + " -endfield-m23-particle-renderer-output=<source-republish-identical.json>\",\n" +
                "  \"source_republish_identical_guidance\": \"Capture the original simulated rows, Clear, SetParticles and SetCustomParticleData with the same values, then require strict before/after value equality; this is a component-admission differential, not source visual parity.\",\n" +
                "  \"explicit_camera_render_command\": \"DXCap.exe -file <explicit-camera-render.vsglog> -frame 0+1 -terminateonsave -c <player.exe> -endfield-m23-particle-renderer-capture -endfield-m23-particle-renderer-mode=explicit-camera-render -endfield-m23-particle-renderer-output=<explicit-camera-render.json> -endfield-m23-particle-renderer-quit\"\n" +
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

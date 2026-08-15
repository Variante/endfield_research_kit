using System;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
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
    /// Builds an isolated D3D12 player from a disposable copy of the fast HG
    /// compatibility scene. The generated gacha prefab and source scene are read-only.
    /// </summary>
    public static class EndfieldZhuangfyGachaPresentationCaptureBuilder
    {
        private const string FastScenePath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/" +
            "CharacterRenderStyleFast.unity";
        private const string GachaPrefabPath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Zhuangfy/Effects/" +
            "GachaRuntime/Zhuangfy_Gacha_Recovered.prefab";
        private const string GeneratedRoot =
            "Assets/EndfieldGraphShaderLab/Generated/Diagnostics/" +
            "ZhuangfyGachaPresentationCapture";
        private const string CaptureScenePath =
            GeneratedRoot + "/ZhuangfyGachaPresentationCapture.unity";
        private const string PlayerOutputArgument =
            "-endfield-zhuangfy-gacha-player-output";
        private const string ReferenceRelativePath =
            "ReferenceCaptures/Zhuangfy/public_3d_demo_BV1M7D1BKEbQ_25fps.mp4";
        private const string ExpectedReferenceSha256 =
            "18389E9658E524FBAF03E3605402EA8A5B9FF4C608AB4FFF97F256023D3A11C9";

        [MenuItem(
            "Endfield/Character Recovery Lab/Build Zhuangfy Gacha Presentation Capture")]
        public static void BuildFromMenu()
        {
            BuildPlayer();
        }

        public static void BuildPlayer()
        {
            if (AssetDatabase.LoadAssetAtPath<SceneAsset>(FastScenePath) == null)
                EndfieldManifestCharacterSetup.BuildFastRenderStyleViewer();
            ValidateInputs();
            EnsureAssetFolder(GeneratedRoot);
            if (AssetDatabase.LoadAssetAtPath<SceneAsset>(CaptureScenePath) != null &&
                !AssetDatabase.DeleteAsset(CaptureScenePath))
            {
                throw new IOException(
                    "Could not replace disposable capture scene: " + CaptureScenePath);
            }

            Scene scene = EditorSceneManager.OpenScene(FastScenePath, OpenSceneMode.Single);
            if (!EditorSceneManager.SaveScene(scene, CaptureScenePath, false))
            {
                throw new IOException(
                    "Could not create disposable capture scene: " + CaptureScenePath);
            }

            GameObject viewerRoot = GameObject.Find("CharacterRecoveryViewerRoot");
            if (viewerRoot == null)
            {
                throw new InvalidOperationException(
                    "Fast scene has no CharacterRecoveryViewerRoot.");
            }
            DestroyChildIfPresent(viewerRoot.transform, "ViewerUI");
            DestroyChildIfPresent(viewerRoot.transform, "Characters");
            foreach (EndfieldRecoveredCharInfoBackgroundPortrait portrait in
                UnityEngine.Object.FindObjectsOfType<
                    EndfieldRecoveredCharInfoBackgroundPortrait>(true))
            {
                UnityEngine.Object.DestroyImmediate(portrait.gameObject);
            }

            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(GachaPrefabPath);
            GameObject gacha = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
            gacha.name = "Zhuangfy_Gacha_Recovered_CaptureInstance";
            gacha.transform.SetParent(viewerRoot.transform, false);
            gacha.transform.localPosition = Vector3.zero;
            gacha.transform.localRotation = Quaternion.identity;
            gacha.transform.localScale = Vector3.one;

            EndfieldRecoveredZhuangfyGachaRuntime runtime =
                gacha.GetComponent<EndfieldRecoveredZhuangfyGachaRuntime>();
            EndfieldRecoveredEnvironmentPhaseSnapshot environmentPhase =
                gacha.GetComponent<EndfieldRecoveredEnvironmentPhaseSnapshot>();
            Transform actor = gacha.transform.Find("Actor");
            EndfieldRecoveredZhuangfyExternalCameraPlayback playback =
                gacha.GetComponentInChildren<
                    EndfieldRecoveredZhuangfyExternalCameraPlayback>(true);
            if (runtime == null || environmentPhase == null ||
                !environmentPhase.IsGachaRoomSourceClosed ||
                actor == null || playback == null ||
                playback.sourceCamera == null || playback.sourceCamera.enabled ||
                !playback.keepSourceCameraDisabled ||
                playback.sourceClip == null || !playback.sourceClip.IsSourceClosed)
            {
                throw new InvalidDataException(
                    "Generated Zhuangfy gacha prefab changed its exact runtime/camera contract.");
            }
            runtime.autoStartRecoveredEffect = false;
            SetLayerRecursively(
                gacha.transform,
                EndfieldZhuangfyGachaPresentationCapture.SourceGachaLayer);

            Camera presentationCamera =
                Camera.main ?? UnityEngine.Object.FindObjectOfType<Camera>(true);
            if (presentationCamera == null ||
                ReferenceEquals(presentationCamera, playback.sourceCamera))
            {
                throw new InvalidOperationException(
                    "Disposable fast scene has no separate presentation Camera.");
            }
            presentationCamera.gameObject.SetActive(true);
            presentationCamera.enabled = true;
            presentationCamera.cullingMask =
                EndfieldZhuangfyGachaPresentationCapture.SourceGachaCullingMask;
            presentationCamera.useOcclusionCulling = false;
            string presentationCameraComponents = string.Join(
                ",",
                Array.ConvertAll(
                    presentationCamera.GetComponents<Component>(),
                    component => component.GetType().Name));
            Debug.Log(
                "Zhuangfy gacha capture presentation Camera selected: " +
                $"name='{presentationCamera.name}', tag='{presentationCamera.tag}', " +
                $"scene='{presentationCamera.gameObject.scene.name}', " +
                $"cullingMask=0x{presentationCamera.cullingMask:X8}, " +
                $"useOcclusionCulling={presentationCamera.useOcclusionCulling}, " +
                $"captureScopeLayer={EndfieldZhuangfyGachaPresentationCapture.SourceGachaLayer}, " +
                $"rect={presentationCamera.rect}, depth={presentationCamera.depth}, " +
                $"display={presentationCamera.targetDisplay}, clear={presentationCamera.clearFlags}, " +
                $"components=[{presentationCameraComponents}].");
            Transform lighting = viewerRoot.transform.Find("Lighting");
            EndfieldManifestCharacterSetup.ConfigureOperatorReferenceLighting(
                scene,
                lighting,
                presentationCamera,
                "Zhuangfy",
                actor);
            EndfieldHGOperatorPresentation presentation =
                presentationCamera.GetComponent<EndfieldHGOperatorPresentation>();
            if (presentation == null)
            {
                throw new InvalidDataException(
                    "Gacha presentation Camera is missing its recovered post profile.");
            }
            presentation.useRecoveredGachaRoomPostProfile = true;
            presentation.environmentPhaseSnapshot = environmentPhase;

            GameObject keyObject = GameObject.Find("KeyLight");
            Light keyLight = keyObject != null
                ? keyObject.GetComponent<Light>()
                : null;
            EndfieldHGRPCharacterLightingVolume characterLighting =
                presentationCamera.GetComponent<EndfieldHGRPCharacterLightingVolume>();
            EndfieldRecoveredEnvironmentPhaseConsumer environmentConsumer =
                presentationCamera.GetComponent<EndfieldRecoveredEnvironmentPhaseConsumer>();
            if (environmentConsumer == null)
            {
                environmentConsumer = presentationCamera.gameObject.AddComponent<
                    EndfieldRecoveredEnvironmentPhaseConsumer>();
            }
            environmentConsumer.snapshot = environmentPhase;
            environmentConsumer.sceneMainLight = keyLight;
            environmentConsumer.characterLighting = characterLighting;
            if (!environmentConsumer.TryApplySourceClosedDirectLight(
                    out string environmentFailure))
            {
                throw new InvalidDataException(
                    "Could not apply source-closed Gacha environment phase: " +
                    environmentFailure);
            }
            AddPostShaderKeepalive(viewerRoot.transform);

            var captureObject = new GameObject("ZhuangfyGachaPresentationCapture");
            captureObject.transform.SetParent(viewerRoot.transform, false);
            var capture =
                captureObject.AddComponent<EndfieldZhuangfyGachaPresentationCapture>();
            capture.runtime = runtime;
            capture.sourceCameraPlayback = playback;
            capture.presentationCamera = presentationCamera;
            capture.captureScopeRoot = gacha.transform;

            EditorUtility.SetDirty(runtime);
            EditorUtility.SetDirty(presentationCamera);
            EditorUtility.SetDirty(presentation);
            EditorUtility.SetDirty(environmentConsumer);
            EditorUtility.SetDirty(capture);
            if (!EditorSceneManager.SaveScene(scene, CaptureScenePath, false))
            {
                throw new IOException(
                    "Could not save disposable capture scene: " + CaptureScenePath);
            }
            AssetDatabase.SaveAssets();

            string playerPath = ReadArgument(
                Environment.GetCommandLineArgs(),
                PlayerOutputArgument);
            if (string.IsNullOrWhiteSpace(playerPath))
            {
                playerPath = Path.Combine(
                    Directory.GetParent(Application.dataPath).FullName,
                    "Builds",
                    "ZhuangfyGachaPresentationCapture",
                    "EndfieldZhuangfyGachaPresentationCapture.exe");
            }
            playerPath = Path.GetFullPath(playerPath);
            Directory.CreateDirectory(Path.GetDirectoryName(playerPath));

            GraphicsDeviceType[] previousGraphicsApis =
                PlayerSettings.GetGraphicsAPIs(BuildTarget.StandaloneWindows64);
            bool previousDefaultGraphicsApis =
                PlayerSettings.GetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64);
            bool previousRunInBackground = PlayerSettings.runInBackground;
            try
            {
                PlayerSettings.SetUseDefaultGraphicsAPIs(
                    BuildTarget.StandaloneWindows64,
                    false);
                PlayerSettings.SetGraphicsAPIs(
                    BuildTarget.StandaloneWindows64,
                    new[] { GraphicsDeviceType.Direct3D12 });
                PlayerSettings.runInBackground = true;
                var options = new BuildPlayerOptions
                {
                    scenes = new[] { CaptureScenePath },
                    locationPathName = playerPath,
                    target = BuildTarget.StandaloneWindows64,
                    options = BuildOptions.Development,
                };
                BuildReport report = BuildPipeline.BuildPlayer(options);
                if (report.summary.result != BuildResult.Succeeded)
                {
                    throw new InvalidOperationException(
                        "Zhuangfy gacha presentation player build failed: " +
                        $"result={report.summary.result}, " +
                        $"errors={report.summary.totalErrors}, " +
                        $"warnings={report.summary.totalWarnings}.");
                }
                Debug.Log(
                    "Zhuangfy gacha presentation player built: " +
                    $"path={playerPath}, size={report.summary.totalSize} bytes, " +
                    $"seconds={report.summary.totalTime.TotalSeconds:0.0}, api=D3D12, " +
                    $"referenceSha256={ExpectedReferenceSha256}.");
            }
            finally
            {
                PlayerSettings.runInBackground = previousRunInBackground;
                PlayerSettings.SetUseDefaultGraphicsAPIs(
                    BuildTarget.StandaloneWindows64,
                    previousDefaultGraphicsApis);
                if (!previousDefaultGraphicsApis &&
                    previousGraphicsApis != null &&
                    previousGraphicsApis.Length > 0)
                {
                    PlayerSettings.SetGraphicsAPIs(
                        BuildTarget.StandaloneWindows64,
                        previousGraphicsApis);
                }
            }
        }

        private static void SetLayerRecursively(Transform root, int layer)
        {
            root.gameObject.layer = layer;
            for (int index = 0; index < root.childCount; index++)
                SetLayerRecursively(root.GetChild(index), layer);
        }

        private static void ValidateInputs()
        {
            if (AssetDatabase.LoadAssetAtPath<SceneAsset>(FastScenePath) == null)
            {
                throw new FileNotFoundException(
                    "Build the fast render-style scene first.",
                    FastScenePath);
            }
            if (AssetDatabase.LoadAssetAtPath<GameObject>(GachaPrefabPath) == null)
                throw new FileNotFoundException("Missing recovered gacha prefab.", GachaPrefabPath);

            string projectRoot = Directory.GetParent(Application.dataPath).FullName;
            string referencePath = Path.Combine(
                projectRoot,
                ReferenceRelativePath.Replace('/', Path.DirectorySeparatorChar));
            if (!File.Exists(referencePath))
            {
                throw new FileNotFoundException(
                    "Missing preserved public retail entrance reference.",
                    referencePath);
            }
            string actualSha256 = ComputeSha256(referencePath);
            if (!string.Equals(
                    actualSha256,
                    ExpectedReferenceSha256,
                    StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidDataException(
                    "Public reference hash changed: " + actualSha256);
            }
        }

        private static void AddPostShaderKeepalive(Transform viewerRoot)
        {
            string[] shaderNames =
            {
                "Hidden/Endfield/HGRPCompat/ExposureTonemap",
                "Hidden/Endfield/HGRPCompat/RecoveredCharInfoLutBuilder2D",
            };
            string[] assetNames =
            {
                "HGCompatPostShaderKeepalive",
                "RecoveredCharInfoLutBuilderKeepalive",
            };
            for (int index = 0; index < shaderNames.Length; index++)
            {
                Shader shader = Shader.Find(shaderNames[index]);
                if (shader == null)
                {
                    throw new InvalidOperationException(
                        "Could not find compatibility post shader: " + shaderNames[index]);
                }
                string materialPath =
                    GeneratedRoot + "/" + assetNames[index] + ".mat";
                if (AssetDatabase.LoadAssetAtPath<Material>(materialPath) != null &&
                    !AssetDatabase.DeleteAsset(materialPath))
                {
                    throw new IOException(
                        "Could not replace keepalive material: " + materialPath);
                }
                var material = new Material(shader) { name = assetNames[index] };
                AssetDatabase.CreateAsset(material, materialPath);
                var keepalive = new GameObject(assetNames[index]);
                keepalive.transform.SetParent(viewerRoot, false);
                MeshRenderer renderer = keepalive.AddComponent<MeshRenderer>();
                renderer.sharedMaterial = material;
                renderer.enabled = false;
            }
        }

        private static void DestroyChildIfPresent(Transform parent, string name)
        {
            Transform child = parent.Find(name);
            if (child != null)
                UnityEngine.Object.DestroyImmediate(child.gameObject);
        }

        private static void EnsureAssetFolder(string assetPath)
        {
            string[] segments = assetPath.Split('/');
            string current = segments[0];
            for (int index = 1; index < segments.Length; index++)
            {
                string next = current + "/" + segments[index];
                if (!AssetDatabase.IsValidFolder(next))
                    AssetDatabase.CreateFolder(current, segments[index]);
                current = next;
            }
        }

        private static string ComputeSha256(string path)
        {
            using (FileStream stream = File.OpenRead(path))
            using (SHA256 sha256 = SHA256.Create())
                return ToHex(sha256.ComputeHash(stream));
        }

        private static string ToHex(byte[] bytes)
        {
            var builder = new StringBuilder(bytes.Length * 2);
            foreach (byte value in bytes)
                builder.Append(value.ToString("X2", CultureInfo.InvariantCulture));
            return builder.ToString();
        }

        private static string ReadArgument(string[] arguments, string name)
        {
            string prefix = name + "=";
            for (int index = 0; index < arguments.Length; index++)
            {
                string argument = arguments[index];
                if (argument.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                    return argument.Substring(prefix.Length);
                if (string.Equals(argument, name, StringComparison.OrdinalIgnoreCase) &&
                    index + 1 < arguments.Length)
                {
                    return arguments[index + 1];
                }
            }
            return null;
        }
    }
}

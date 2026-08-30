using System;
using System.IO;
using System.Linq;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLabEditor
{
    public static class EndfieldEndminfOverviewEffectBindingBuilder
    {
        private const string Actor = "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Prefabs/Endminf.prefab";
        private const string Effects = "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Effects/Overview/";
        private static readonly string[] Names = { "P_fxui_endminm003_overview_01", "P_fxui_endminm003_overview_02", "P_fxui_endminm003_overview_03", "P_fxui_endminm003_overview_04" };
        private static readonly float[] Durations = { 9f, 10f, 9f, 9f };
        private const string ViewerScene =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/CharacterRecoveryViewer.unity";
        private const string OverviewAudio =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Audio/925835917.flac";

        public static void OpenVisualReproductionInPlayMode()
        {
            PrepareVisualReproductionScene();
            EditorApplication.EnterPlaymode();
        }

        public static void BuildD3D11CapturePlayer()
        {
            PrepareVisualReproductionScene();
            EnsureEndminfSceneInstanceForStandalone();
            EditorSceneManager.SaveScene(
                UnityEngine.SceneManagement.SceneManager.GetActiveScene(),
                ViewerScene);
            string playerPath = Path.GetFullPath(Path.Combine(
                Directory.GetCurrentDirectory(),
                "Builds/EndminfOverviewCapture/EndminfOverviewCapture.exe"));
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
                    new[] { GraphicsDeviceType.Direct3D11 });
                var options = new BuildPlayerOptions
                {
                    scenes = new[] { ViewerScene },
                    locationPathName = playerPath,
                    target = BuildTarget.StandaloneWindows64,
                    options = BuildOptions.Development,
                };
                BuildReport report = BuildPipeline.BuildPlayer(options);
                if (report.summary.result != BuildResult.Succeeded)
                {
                    throw new InvalidOperationException(
                        "Endminf D3D11 capture-player build failed: " +
                        $"result={report.summary.result}, " +
                        $"errors={report.summary.totalErrors}, " +
                        $"warnings={report.summary.totalWarnings}.");
                }
                Debug.Log(
                    "Endminf D3D11 capture player built: " +
                    $"path={playerPath}, size={report.summary.totalSize} bytes, " +
                    $"time={report.summary.totalTime.TotalSeconds:0.0}s.");
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

        private static void EnsureEndminfSceneInstanceForStandalone()
        {
            CharacterRecoveryRig existing = UnityEngine.Object
                .FindObjectsOfType<CharacterRecoveryRig>(true)
                .FirstOrDefault(value => value != null &&
                    value.name.Equals("Endminf", StringComparison.OrdinalIgnoreCase));
            if (existing != null)
                return;

            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(Actor);
            if (prefab == null)
                throw new FileNotFoundException(
                    "Endminf standalone capture prefab is missing.", Actor);
            GameObject instance = PrefabUtility.InstantiatePrefab(
                prefab,
                UnityEngine.SceneManagement.SceneManager.GetActiveScene()) as GameObject;
            if (instance == null)
                throw new InvalidOperationException(
                    "Could not serialize Endminf into the standalone capture scene.");
            instance.name = "Endminf";
            instance.SetActive(false);
            EditorUtility.SetDirty(instance);
            Debug.Log(
                "Serialized Endminf directly into the standalone capture scene; " +
                "runtime selection no longer depends on editor-only AssetDatabase loading.");
        }

        private static void PrepareVisualReproductionScene()
        {
            Environment.SetEnvironmentVariable(
                EndfieldEndminfVisualCompatibilityClock.EnvironmentVariable,
                "1");
            Environment.SetEnvironmentVariable(
                EndfieldEndminfOverviewEffectImporter.LitEffectCompatibilityEnvironment,
                "1");
            Environment.SetEnvironmentVariable(
                EndfieldRecoveredSourceEnergyCoreProbe.Keyword,
                "1");
            Environment.SetEnvironmentVariable(
                HGCompatRenderPipeline.LinearUnormFinalTargetEnvironmentVariable,
                "1");
            Environment.SetEnvironmentVariable(
                EndfieldRecoveredCharInfoPresentation.EndminfBackdropVisualCompatibilityEnvironmentVariable,
                "1");
            Environment.SetEnvironmentVariable(
                EndfieldRecoveredCharInfoBackgroundPortrait.EnvironmentVariable,
                "1");
            // A comparison render must never inherit possibly stale generated
            // prefabs. Rebuild all four roots from the validated source stage,
            // or fail before serializing the visual-reproduction scene.
            EndfieldEndminfOverviewEffectImporter.BuildAndValidate();
            EndfieldEndminfLitEffectCompatibilityBindingBuilder.BuildAndValidate();
            BuildAndValidate();
            EditorSceneManager.OpenScene(ViewerScene, OpenSceneMode.Single);
            GameObject sceneActor = UnityEngine.Object
                .FindObjectsOfType<CharacterRecoveryRig>(true)
                .Where(value => value != null &&
                    value.name.Equals("Endminf", StringComparison.OrdinalIgnoreCase))
                .Select(value => value.gameObject)
                .FirstOrDefault();
            if (sceneActor == null)
            {
                CharacterRecoveryViewerUI viewer = UnityEngine.Object
                    .FindObjectOfType<CharacterRecoveryViewerUI>(true);
                sceneActor = viewer != null ? viewer.gameObject : null;
            }
            if (sceneActor == null)
                throw new InvalidOperationException(
                    "The character viewer has no room-background owner.");
            Camera camera = Camera.main ?? UnityEngine.Object.FindObjectOfType<Camera>(true);
            CharacterRecoveryPresentationController presentation = camera != null
                ? camera.GetComponent<CharacterRecoveryPresentationController>()
                : null;
            if (presentation != null)
            {
                Renderer referenceBackdrop = UnityEngine.Object.FindObjectsOfType<Renderer>(true)
                    .FirstOrDefault(value => value != null && value.gameObject.name == "ReferenceBackdrop");
                if (referenceBackdrop != null)
                {
                    referenceBackdrop.enabled = true;
                    presentation.presentationBackdropRenderer = referenceBackdrop;
                }
                presentation.enableRecoveredReadyPresentationSubset = false;
                presentation.enableSourceBackedClusteredNprLights = true;
                presentation.enableSourceBackedLightBinning = true;
                presentation.enableIsolatedPunctualSoftShadows = true;
                // The reference uses the exact source CharInfo portrait behind
                // Endminf. Keep this explicit in the saved viewer scene so the
                // result does not depend on an inherited editor environment.
                presentation.enableRecoveredPortrait = true;
                if (presentation.physicalPresentation != null)
                {
                    presentation.physicalPresentation.enableRecoveredPresentation = false;
                    presentation.physicalPresentation.enableReadySubsetDiagnostic = false;
                    presentation.physicalPresentation.RefreshSelection();
                }
                EditorUtility.SetDirty(presentation);
            }
            if (camera != null)
            {
                if (camera.GetComponent<AudioListener>() == null)
                    camera.gameObject.AddComponent<AudioListener>();
                camera.clearFlags = CameraClearFlags.SolidColor;
                camera.backgroundColor = new Color(0.735f, 0.755f, 0.765f, 1f);
                // The reference and all comparison renders are 1920x1080.
                // Override Free Aspect so wide crystal flashes and rock arcs
                // use the same horizontal frustum in the interactive Game view.
                camera.aspect = 16f / 9f;
                EditorUtility.SetDirty(camera);
            }
            EditorSceneManager.SaveScene(
                UnityEngine.SceneManagement.SceneManager.GetActiveScene(), ViewerScene);
        }

        [MenuItem("Endfield/Character Recovery Lab/Bind Endminf Overview Effects")]
        public static void BuildAndValidate()
        {
            // The disposable broad importer stage may be absent between
            // recovery batches, but the pinned suikuai (1) source material,
            // BlendTex, four-mesh palette, and retained prefab are versioned.
            // Re-establish that independently validated renderer before the
            // actor stores its four direct effect-prefab references. Otherwise
            // a focused character rebuild can preserve overview_02 while
            // silently leaving this exact refract branch disabled and empty.
            EndfieldEndminfOverviewEffectImporter
                .RebuildAndValidateSuikuai1Material();

            GameObject actor = PrefabUtility.LoadPrefabContents(Actor);
            if (actor == null) throw new InvalidOperationException("Endminf actor is missing");
            try
            {
                EndfieldOverviewPlayback playback = actor.GetComponentInChildren<EndfieldOverviewPlayback>(true);
                if (playback == null) throw new InvalidOperationException("Endminf Overview playback is missing");
                playback.entranceEffects = Names.Select(name => new EndfieldOverviewEffectRequest {
                    prefabName = name, mountPoint = "", finishWhenExit = true,
                    finishWhenTransition = false
                }).ToArray();
                playback.overviewStartAudio = AssetDatabase.LoadAssetAtPath<AudioClip>(OverviewAudio);
                playback.overviewStartAudioEventTime = 0.058666665f;
                playback.overviewAudioSource = playback.GetComponent<AudioSource>();
                if (playback.overviewAudioSource == null)
                    playback.overviewAudioSource = playback.gameObject.AddComponent<AudioSource>();
                playback.overviewAudioSource.playOnAwake = false;
                playback.overviewAudioSource.loop = false;
                playback.overviewAudioSource.spatialBlend = 0f;
                EndfieldRecoveredCharEffectSpawner spawner = playback.GetComponent<EndfieldRecoveredCharEffectSpawner>();
                if (spawner == null) spawner = playback.gameObject.AddComponent<EndfieldRecoveredCharEffectSpawner>();
                spawner.ReplaceBindings(Names.Select((name, index) => new EndfieldRecoveredCharEffectSpawner.Binding {
                    requestPrefabName = name, prefab = AssetDatabase.LoadAssetAtPath<GameObject>(Effects + name + ".prefab"),
                    requiredMountPoint = "", expectedEffectRoot = name, expectedDelay = 0f,
                    expectedDuration = Durations[index], stationaryPosition = true,
                    shouldFollowScale = false, shouldFollowRotation = true,
                    shouldFollowMainObjRotation = false }).ToArray());
                spawner.RejectUnboundRequests = true;
                EditorUtility.SetDirty(playback); EditorUtility.SetDirty(spawner);
                PrefabUtility.SaveAsPrefabAsset(actor, Actor);
            }
            finally { PrefabUtility.UnloadPrefabContents(actor); }
            AssetDatabase.SaveAssets(); AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            GameObject saved = AssetDatabase.LoadAssetAtPath<GameObject>(Actor);
            EndfieldOverviewPlayback check = saved.GetComponentInChildren<EndfieldOverviewPlayback>(true);
            EndfieldRecoveredCharEffectSpawner source = check.GetComponent<EndfieldRecoveredCharEffectSpawner>();
            if (check.entranceEffects.Length != 4 || source.Bindings.Length != 4 ||
                check.overviewStartAudio == null ||
                !Mathf.Approximately(check.overviewStartAudioEventTime, 0.058666665f) ||
                check.entranceEffects.Any(row => row.prefabName == "A_actor_endminf_ui_overview_02") ||
                check.entranceEffects.Any(row => !row.finishWhenExit || row.finishWhenTransition) ||
                source.Bindings.Any(row => row.prefab == null || !row.stationaryPosition ||
                    row.shouldFollowScale || !row.shouldFollowRotation ||
                    row.shouldFollowMainObjRotation))
                throw new InvalidOperationException("Endminf exact entrance-effect binding drifted");
        }

    }
}

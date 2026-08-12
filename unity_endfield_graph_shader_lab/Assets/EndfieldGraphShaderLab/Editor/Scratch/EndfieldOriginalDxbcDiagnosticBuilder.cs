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
    /// Builds and validates only the disposable original-DXBC diagnostic.
    /// No compatibility room scene or runtime renderer is opened or modified.
    /// </summary>
    public static class EndfieldOriginalDxbcDiagnosticBuilder
    {
        private const string PluginPath =
            "Assets/EndfieldGraphShaderLab/Plugins/x86_64/" +
            "OriginalDxbcSwapPlugin.dll";
        private const string ShaderPath =
            "Assets/EndfieldGraphShaderLab/Shaders/Diagnostics/" +
            "EndfieldOriginalDxbcResolverDiagnostic.shader";
        private const string GeneratedRoot =
            "Assets/EndfieldGraphShaderLab/Generated/Diagnostics/" +
            "OriginalDxbcExact";
        private const string ScenePath =
            GeneratedRoot + "/OriginalDxbcExactDiagnostic.unity";
        private const string MaterialPath =
            GeneratedRoot + "/OriginalDxbcExactDiagnosticMaterial.mat";

        [MenuItem(
            "Endfield/Character Recovery Lab/" +
            "Build Original DXBC Exact Diagnostic")]
        public static void BuildAndValidate()
        {
            if (!HasArgument(
                EndfieldOriginalDxbcDiagnosticRuntime.ActivationArgument))
            {
                throw new InvalidOperationException(
                    "Explicit original-DXBC diagnostic token is required.");
            }
            if (!Application.isBatchMode)
            {
                throw new InvalidOperationException(
                    "Original-DXBC validation is batch-mode only.");
            }
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
            {
                throw new InvalidOperationException(
                    "Editor validation requires Direct3D11; actual=" +
                    SystemInfo.graphicsDeviceType + ".");
            }

            ConfigurePluginImporter();
            Shader shader = AssetDatabase.LoadAssetAtPath<Shader>(ShaderPath);
            if (shader == null)
                throw new FileNotFoundException(
                    "Original-DXBC diagnostic shader was not imported.",
                    ShaderPath);

            string projectRoot =
                Directory.GetParent(Application.dataPath).FullName;
            string outputRoot = Path.Combine(
                projectRoot,
                "scratch",
                "reverse_engineering",
                "original_dxbc_exact_diagnostic");
            Directory.CreateDirectory(outputRoot);
            string editorReport = Path.Combine(
                outputRoot,
                "editor_validation.json");

            bool editorPassed =
                EndfieldOriginalDxbcDiagnosticRuntime.RunAndWrite(
                    shader,
                    editorReport,
                    "unity-editor");
            if (!editorPassed)
            {
                Debug.LogWarning(
                    "Editor original-DXBC frame remained fail-closed; " +
                    "building the isolated standalone to test its separately " +
                    "proven loader path. Report: " + editorReport);
            }

            EnsureAssetFolder(GeneratedRoot);
            if (AssetDatabase.LoadAssetAtPath<SceneAsset>(ScenePath) != null)
                AssetDatabase.DeleteAsset(ScenePath);
            if (AssetDatabase.LoadAssetAtPath<Material>(MaterialPath) != null)
                AssetDatabase.DeleteAsset(MaterialPath);

            var exactMaterial = new Material(shader)
            {
                name = "Original DXBC Exact Diagnostic Material",
            };
            var exactKeyword = new LocalKeyword(
                shader,
                EndfieldOriginalDxbcDiagnosticRuntime.KeywordName);
            if (!exactKeyword.isValid)
                throw new InvalidOperationException(
                    "The exact diagnostic shader keywords are unavailable.");
            exactMaterial.SetKeyword(exactKeyword, true);
            AssetDatabase.CreateAsset(exactMaterial, MaterialPath);
            AssetDatabase.SaveAssets();

            Scene scene = EditorSceneManager.NewScene(
                NewSceneSetup.EmptyScene,
                NewSceneMode.Single);
            var root = new GameObject("OriginalDxbcExactDiagnosticRoot");
            var runtime =
                root.AddComponent<EndfieldOriginalDxbcDiagnosticRuntime>();
            runtime.Configure(shader, exactMaterial);
            if (!EditorSceneManager.SaveScene(scene, ScenePath, false))
                throw new IOException(
                    "Could not save isolated diagnostic scene: " + ScenePath);
            AssetDatabase.SaveAssets();

            string buildRoot = Path.Combine(
                projectRoot,
                "Builds",
                "OriginalDxbcExactDiagnostic");
            Directory.CreateDirectory(buildRoot);
            string playerPath = Path.Combine(
                buildRoot,
                "EndfieldOriginalDxbcExactDiagnostic.exe");

            GraphicsDeviceType[] previousGraphicsApis =
                PlayerSettings.GetGraphicsAPIs(BuildTarget.StandaloneWindows64);
            bool previousUseDefaultGraphicsApis =
                PlayerSettings.GetUseDefaultGraphicsAPIs(
                    BuildTarget.StandaloneWindows64);
            try
            {
                PlayerSettings.SetUseDefaultGraphicsAPIs(
                    BuildTarget.StandaloneWindows64,
                    false);
                PlayerSettings.SetGraphicsAPIs(
                    BuildTarget.StandaloneWindows64,
                    new[] { GraphicsDeviceType.Direct3D11 });

                bool buildArmed =
                    EndfieldOriginalDxbcDiagnosticRuntime.ArmForStandaloneBuild();
                if (!buildArmed)
                    throw new InvalidOperationException(
                        "Could not arm the exact DXBC compiler hook for the " +
                        "standalone build.");

                try
                {
                    // Force the shader importer to request the exact local
                    // keyword variant while the native replacement hook is
                    // armed. BuildPipeline may otherwise accept a cached
                    // shell binary without invoking the compiler extension.
                    AssetDatabase.ImportAsset(
                        ShaderPath,
                        ImportAssetOptions.ForceUpdate);
                    var options = new BuildPlayerOptions
                    {
                        scenes = new[] { ScenePath },
                        locationPathName = playerPath,
                        target = BuildTarget.StandaloneWindows64,
                        options =
                            BuildOptions.Development |
                            BuildOptions.CleanBuildCache,
                    };
                    BuildReport report = BuildPipeline.BuildPlayer(options);
                    if (report.summary.result != BuildResult.Succeeded)
                    {
                        throw new InvalidOperationException(
                            "Original-DXBC standalone build failed: result=" +
                            report.summary.result +
                            ", errors=" + report.summary.totalErrors +
                            ", warnings=" + report.summary.totalWarnings + ".");
                    }

                    Debug.Log(
                        "Original DXBC exact build compiler counters: " +
                        EndfieldOriginalDxbcDiagnosticRuntime.StandaloneBuildCounters());

                    string buildManifest = Path.Combine(
                        outputRoot,
                        "standalone_build.json");
                    File.WriteAllText(
                        buildManifest,
                        RenderBuildManifest(playerPath, report),
                        new UTF8Encoding(false));
                    Debug.Log(
                        "Original DXBC diagnostic editor status=" +
                        (editorPassed ? "pass" : "no_activation") + "; " +
                        "D3D11-only standalone built: " + playerPath);
                }
                finally
                {
                    EndfieldOriginalDxbcDiagnosticRuntime.DisarmAfterStandaloneBuild();
                }
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

        private static void ConfigurePluginImporter()
        {
            var importer = AssetImporter.GetAtPath(PluginPath) as PluginImporter;
            if (importer == null)
            {
                throw new FileNotFoundException(
                    "Native original-DXBC plugin was not imported.",
                    PluginPath);
            }

            bool changed =
                importer.GetCompatibleWithAnyPlatform() ||
                !importer.GetCompatibleWithEditor() ||
                importer.GetEditorData("OS") != "Windows" ||
                importer.GetEditorData("CPU") != "x86_64" ||
                !importer.GetCompatibleWithPlatform(
                    BuildTarget.StandaloneWindows64) ||
                importer.GetPlatformData(
                    BuildTarget.StandaloneWindows64,
                    "CPU") != "x86_64" ||
                importer.GetCompatibleWithPlatform(
                    BuildTarget.StandaloneWindows) ||
                importer.GetCompatibleWithPlatform(
                    BuildTarget.StandaloneOSX) ||
                importer.GetCompatibleWithPlatform(
                    BuildTarget.StandaloneLinux64) ||
                importer.GetCompatibleWithPlatform(BuildTarget.Android) ||
                importer.GetCompatibleWithPlatform(BuildTarget.iOS) ||
                importer.GetCompatibleWithPlatform(BuildTarget.WebGL) ||
                !importer.isPreloaded;
            if (!changed)
                return;

            importer.SetCompatibleWithAnyPlatform(false);
            importer.SetCompatibleWithEditor(true);
            importer.SetEditorData("OS", "Windows");
            importer.SetEditorData("CPU", "x86_64");
            importer.SetCompatibleWithPlatform(
                BuildTarget.StandaloneWindows64,
                true);
            importer.SetPlatformData(
                BuildTarget.StandaloneWindows64,
                "CPU",
                "x86_64");
            importer.SetCompatibleWithPlatform(
                BuildTarget.StandaloneWindows,
                false);
            importer.SetCompatibleWithPlatform(
                BuildTarget.StandaloneOSX,
                false);
            importer.SetCompatibleWithPlatform(
                BuildTarget.StandaloneLinux64,
                false);
            importer.SetCompatibleWithPlatform(BuildTarget.Android, false);
            importer.SetCompatibleWithPlatform(BuildTarget.iOS, false);
            importer.SetCompatibleWithPlatform(BuildTarget.WebGL, false);
            importer.isPreloaded = true;
            importer.SaveAndReimport();
        }

        private static string RenderBuildManifest(
            string playerPath,
            BuildReport report)
        {
            return
                "{\n" +
                "  \"schema\": " +
                "\"endfield.original-dxbc-exact-standalone-build.v1\",\n" +
                "  \"status\": \"pass\",\n" +
                "  \"graphics_apis\": [\"Direct3D11\"],\n" +
                "  \"development_build\": true,\n" +
                "  \"scene\": \"" + Escape(ScenePath) + "\",\n" +
                "  \"player\": \"" + Escape(playerPath) + "\",\n" +
                "  \"build_result\": \"" + report.summary.result + "\",\n" +
                "  \"total_errors\": " + report.summary.totalErrors + ",\n" +
                "  \"total_warnings\": " + report.summary.totalWarnings + ",\n" +
                "  \"total_size\": " + report.summary.totalSize + "\n" +
                "}\n";
        }

        private static void EnsureAssetFolder(string path)
        {
            string[] pieces = path.Split('/');
            string current = pieces[0];
            for (int index = 1; index < pieces.Length; index++)
            {
                string next = current + "/" + pieces[index];
                if (!AssetDatabase.IsValidFolder(next))
                    AssetDatabase.CreateFolder(current, pieces[index]);
                current = next;
            }
        }

        private static bool HasArgument(string argument)
        {
            foreach (string value in Environment.GetCommandLineArgs())
            {
                if (string.Equals(value, argument, StringComparison.Ordinal))
                    return true;
            }
            return false;
        }

        private static string Escape(string value)
        {
            return (value ?? string.Empty)
                .Replace("\\", "\\\\")
                .Replace("\"", "\\\"");
        }
    }
}

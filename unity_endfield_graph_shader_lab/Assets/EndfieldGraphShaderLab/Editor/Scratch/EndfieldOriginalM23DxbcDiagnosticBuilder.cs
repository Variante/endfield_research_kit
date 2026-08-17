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
    /// Builds only the opt-in M23 native-bridge diagnostic scene/player.
    /// </summary>
    public static class EndfieldOriginalM23DxbcDiagnosticBuilder
    {
        private const string PluginPath =
            "Assets/EndfieldGraphShaderLab/Plugins/x86_64/OriginalM23DxbcExactPlugin.dll";
        private const string ShaderPath =
            "Assets/EndfieldGraphShaderLab/Shaders/Diagnostics/EndfieldOriginalM23DxbcDiagnostic.shader";
        private const string GeneratedRoot =
            "Assets/EndfieldGraphShaderLab/Generated/Diagnostics/OriginalM23DxbcExact";
        private const string ScenePath = GeneratedRoot + "/OriginalM23DxbcExactDiagnostic.unity";

        [MenuItem("Endfield/Character Recovery Lab/Build Original M23 DXBC Bridge Diagnostic")]
        public static void BuildAndValidate()
        {
            RequireTokenAndBatch();
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
                throw new InvalidOperationException("M23 bridge requires Direct3D11; actual=" + SystemInfo.graphicsDeviceType + ".");
            ConfigurePluginImporter();
            Shader shader = AssetDatabase.LoadAssetAtPath<Shader>(ShaderPath);
            if (shader == null)
                throw new FileNotFoundException("M23 bridge diagnostic shader was not imported.", ShaderPath);

            string projectRoot = Directory.GetParent(Application.dataPath).FullName;
            string outputRoot = Path.Combine(projectRoot, "scratch", "reverse_engineering", "original_m23_dxbc_exact_diagnostic");
            Directory.CreateDirectory(outputRoot);
            EnsureAssetFolder(GeneratedRoot);
            if (AssetDatabase.LoadAssetAtPath<SceneAsset>(ScenePath) != null)
                AssetDatabase.DeleteAsset(ScenePath);
            Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            GameObject root = new GameObject("OriginalM23DxbcExactDiagnosticRoot");
            var runtime = root.AddComponent<EndfieldOriginalM23DxbcDiagnosticRuntime>();
            runtime.Configure(shader);
            if (!EditorSceneManager.SaveScene(scene, ScenePath, false))
                throw new IOException("Could not save M23 diagnostic scene: " + ScenePath);
            AssetDatabase.SaveAssets();

            string buildRoot = Path.Combine(projectRoot, "Builds", "OriginalM23DxbcExactDiagnostic");
            Directory.CreateDirectory(buildRoot);
            string playerPath = Path.Combine(buildRoot, "EndfieldOriginalM23DxbcExactDiagnostic.exe");
            GraphicsDeviceType[] previousApis = PlayerSettings.GetGraphicsAPIs(BuildTarget.StandaloneWindows64);
            bool previousDefault = PlayerSettings.GetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64);
            try
            {
                PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64, false);
                PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneWindows64, new[] { GraphicsDeviceType.Direct3D11 });
                var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
                {
                    scenes = new[] { ScenePath },
                    locationPathName = playerPath,
                    target = BuildTarget.StandaloneWindows64,
                    options = BuildOptions.Development | BuildOptions.CleanBuildCache,
                });
                if (report.summary.result != BuildResult.Succeeded)
                    throw new InvalidOperationException("M23 standalone build failed: result=" + report.summary.result + ", errors=" + report.summary.totalErrors + ".");
                File.WriteAllText(Path.Combine(outputRoot, "standalone_build.json"), RenderBuildManifest(playerPath, report), new UTF8Encoding(false));
            }
            finally
            {
                PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64, previousDefault);
                if (!previousDefault && previousApis != null && previousApis.Length != 0)
                    PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneWindows64, previousApis);
            }
        }

        public static void ValidateD3D12NonActivation()
        {
            RequireTokenAndBatch();
            ConfigurePluginImporter();
            string projectRoot = Directory.GetParent(Application.dataPath).FullName;
            string output = ReadArgument(Environment.GetCommandLineArgs(), EndfieldOriginalM23DxbcDiagnosticRuntime.OutputArgument);
            if (string.IsNullOrWhiteSpace(output))
                output = Path.Combine(projectRoot, "scratch", "reverse_engineering", "original_m23_dxbc_exact_diagnostic", "d3d12_non_activation.json");
            if (!EndfieldOriginalM23DxbcDiagnosticRuntime.WriteD3D12NonActivationReport(output))
                throw new InvalidOperationException("M23 D3D12 non-activation gate failed; report=" + output);
        }

        private static void ConfigurePluginImporter()
        {
            var importer = AssetImporter.GetAtPath(PluginPath) as PluginImporter;
            if (importer == null) throw new FileNotFoundException("M23 native bridge plugin was not imported.", PluginPath);
            importer.SetCompatibleWithAnyPlatform(false);
            importer.SetCompatibleWithEditor(true);
            importer.SetEditorData("OS", "Windows");
            importer.SetEditorData("CPU", "x86_64");
            importer.SetCompatibleWithPlatform(BuildTarget.StandaloneWindows64, true);
            importer.SetPlatformData(BuildTarget.StandaloneWindows64, "CPU", "x86_64");
            importer.SetCompatibleWithPlatform(BuildTarget.StandaloneWindows, false);
            importer.SetCompatibleWithPlatform(BuildTarget.StandaloneOSX, false);
            importer.SetCompatibleWithPlatform(BuildTarget.StandaloneLinux64, false);
            importer.SetCompatibleWithPlatform(BuildTarget.Android, false);
            importer.SetCompatibleWithPlatform(BuildTarget.iOS, false);
            importer.SetCompatibleWithPlatform(BuildTarget.WebGL, false);
            importer.isPreloaded = true;
            importer.SaveAndReimport();
        }

        private static void RequireTokenAndBatch()
        {
            if (!HasArgument(EndfieldOriginalM23DxbcDiagnosticRuntime.ActivationArgument))
                throw new InvalidOperationException("Explicit M23 diagnostic token is required.");
            if (!Application.isBatchMode)
                throw new InvalidOperationException("M23 diagnostic is batch-mode only.");
        }

        private static void EnsureAssetFolder(string path)
        {
            string[] pieces = path.Split('/');
            string current = pieces[0];
            for (int index = 1; index < pieces.Length; index++)
            {
                string next = current + "/" + pieces[index];
                if (!AssetDatabase.IsValidFolder(next)) AssetDatabase.CreateFolder(current, pieces[index]);
                current = next;
            }
        }

        private static bool HasArgument(string argument)
        {
            foreach (string value in Environment.GetCommandLineArgs())
                if (string.Equals(value, argument, StringComparison.Ordinal)) return true;
            return false;
        }

        private static string ReadArgument(string[] args, string name)
        {
            for (int index = 0; index + 1 < args.Length; index++)
                if (string.Equals(args[index], name, StringComparison.Ordinal)) return args[index + 1];
            return null;
        }

        private static string RenderBuildManifest(string playerPath, BuildReport report)
        {
            return "{\n" +
                "  \"schema\": \"endfield.original-m23-dxbc-exact-build.v1\",\n" +
                "  \"status\": \"pass\",\n" +
                "  \"standalone_only\": true,\n" +
                "  \"production_submission\": false,\n" +
                "  \"graphics_apis\": [\"Direct3D11\"],\n" +
                "  \"visual_fidelity_claim\": false,\n" +
                "  \"scene\": \"" + Escape(ScenePath) + "\",\n" +
                "  \"player\": \"" + Escape(playerPath) + "\",\n" +
                "  \"build_result\": \"" + report.summary.result + "\",\n" +
                "  \"total_errors\": " + report.summary.totalErrors + ",\n" +
                "  \"total_warnings\": " + report.summary.totalWarnings + "\n}\n";
        }

        private static string Escape(string value) => (value ?? string.Empty).Replace("\\", "\\\\").Replace("\"", "\\\"");
    }
}

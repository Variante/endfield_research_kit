using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLabEditor
{
    public static class EndfieldOriginalUberPostBundleProbe
    {
        private const string ShaderName = "HGRP/PostProcessing/UberPost";

        [Serializable]
        private sealed class ProbeReport
        {
            public string schema = "endfield.original-uberpost-bundle-probe.v1";
            public string status;
            public string unityVersion;
            public string graphicsDeviceType;
            public string bundlePath;
            public string[] assetNames;
            public string shaderName;
            public bool shaderIsSupported;
            public int passCount;
            public string[] passNames;
            public string failure;
        }

        public static void RunBatch()
        {
            var report = new ProbeReport
            {
                status = "failed_closed",
                unityVersion = Application.unityVersion,
                graphicsDeviceType = SystemInfo.graphicsDeviceType.ToString(),
                bundlePath = Environment.GetEnvironmentVariable(
                    "ENDFIELD_ORIGINAL_UBERPOST_BUNDLE"),
                assetNames = Array.Empty<string>(),
                passNames = Array.Empty<string>(),
            };
            int exitCode = 1;
            AssetBundle bundle = null;
            try
            {
                if (string.IsNullOrWhiteSpace(report.bundlePath))
                    throw new InvalidOperationException(
                        "ENDFIELD_ORIGINAL_UBERPOST_BUNDLE is required.");
                report.bundlePath = Path.GetFullPath(report.bundlePath);
                if (!File.Exists(report.bundlePath))
                    throw new FileNotFoundException(
                        "Original UberPost bundle does not exist.", report.bundlePath);

                bundle = AssetBundle.LoadFromFile(report.bundlePath);
                if (bundle == null)
                    throw new InvalidDataException(
                        "AssetBundle.LoadFromFile returned null for the exact repacked bundle.");
                report.assetNames = bundle.GetAllAssetNames();
                Shader shader = bundle.LoadAllAssets<Shader>()
                    .FirstOrDefault(candidate => candidate != null &&
                        candidate.name == ShaderName);
                if (shader == null)
                {
                    string loaded = string.Join(", ", bundle.LoadAllAssets<Shader>()
                        .Where(candidate => candidate != null)
                        .Select(candidate => candidate.name));
                    throw new InvalidDataException(
                        "Exact UberPost Shader was not loadable. Loaded Shader names: " + loaded);
                }

                report.shaderName = shader.name;
                report.shaderIsSupported = shader.isSupported;
                var material = new Material(shader);
                try
                {
                    report.passCount = material.passCount;
                    report.passNames = Enumerable.Range(0, material.passCount)
                        .Select(material.GetPassName)
                        .ToArray();
                }
                finally
                {
                    UnityEngine.Object.DestroyImmediate(material);
                }
                if (!shader.isSupported)
                    throw new InvalidOperationException(
                        "Exact UberPost Shader loaded but is unsupported on " +
                        report.graphicsDeviceType + ".");
                if (shader.passCount <= 0)
                    throw new InvalidOperationException(
                        "Exact UberPost Shader loaded without a usable pass.");

                report.status = "exact_shader_loaded_supported";
                exitCode = 0;
            }
            catch (Exception exception)
            {
                report.failure = exception.ToString();
                Debug.LogError(report.failure);
            }
            finally
            {
                if (bundle != null)
                    bundle.Unload(false);
                string output = Environment.GetEnvironmentVariable(
                    "ENDFIELD_ORIGINAL_UBERPOST_REPORT");
                if (string.IsNullOrWhiteSpace(output))
                    output = Path.Combine("scratch", "character_recovery",
                        "endminf_original_uberpost_bundle", "report.json");
                output = Path.GetFullPath(output);
                Directory.CreateDirectory(Path.GetDirectoryName(output));
                File.WriteAllText(output, JsonUtility.ToJson(report, true));
                Debug.Log("Original UberPost bundle probe report: " + output);
                EditorApplication.Exit(exitCode);
            }
        }
    }
}

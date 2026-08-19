using System;
using System.Reflection;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Batch-only publisher and render entry point for the recovered cloth GGX/DFG
    /// probes. The optional cubemap path must be a project-relative Cubemap asset;
    /// an absent or invalid path is deliberately represented by a black cube.
    /// </summary>
    [InitializeOnLoad]
    public static class EndfieldRecoveredClothSpecularBatchPublisher
    {
        public const string CubemapAssetEnvironmentVariable =
            "ENDFIELD_RECOVERED_CLOTH_CUBEMAP_ASSET";

        private static readonly MethodInfo RenderRuntimeReferenceActorPreview =
            typeof(EndfieldManifestCharacterSetup).GetMethod(
                "RenderRuntimeReferenceActorPreview",
                BindingFlags.NonPublic | BindingFlags.Static);

        static EndfieldRecoveredClothSpecularBatchPublisher()
        {
            PublishFromEnvironment();
        }

        public static EndfieldRecoveredClothSpecularProbe.ResponseMode
            PublishFromEnvironment()
        {
            string rawMode = Environment.GetEnvironmentVariable(
                EndfieldRecoveredClothSpecularProbe.EnvironmentVariable);
            EndfieldRecoveredClothSpecularProbe.ResponseMode mode =
                EndfieldRecoveredClothSpecularProbe.ParseMode(rawMode);
            string cubemapPath = Environment.GetEnvironmentVariable(
                CubemapAssetEnvironmentVariable);
            Cubemap cubemap = null;
            if (!string.IsNullOrWhiteSpace(cubemapPath))
            {
                cubemapPath = cubemapPath.Trim().Replace('\\', '/');
                cubemap = AssetDatabase.LoadAssetAtPath<Cubemap>(cubemapPath);
                if (cubemap == null)
                {
                    Debug.LogWarning(
                        $"Recovered cloth cubemap path is not a Cubemap asset: " +
                        $"{cubemapPath}. Using explicit black fallback.");
                }
            }

            EndfieldRecoveredClothSpecularProbe.PublishGlobals(mode, cubemap);
            Debug.Log(
                $"Recovered cloth specular selector: mode={(int)mode} ({mode}); " +
                $"cubemap={(cubemap != null ? cubemapPath : "<black/unbound>")}");
            return mode;
        }

        public static void RenderWulfaRuntimeReferenceProbe()
        {
            EndfieldRecoveredClothSpecularProbe.ResponseMode mode =
                PublishFromEnvironment();
            InvokeRuntimeReferenceRender(
                "Wulfa",
                "A_actor_wulfa_ui_overview_loop_01",
                0.95f,
                $"cloth_specular_recovery_wulfa_{ModeFileToken(mode)}.png");
        }

        public static void RenderZhuangfyRuntimeReferenceProbe()
        {
            EndfieldRecoveredClothSpecularProbe.ResponseMode mode =
                PublishFromEnvironment();
            InvokeRuntimeReferenceRender(
                "Zhuangfy",
                "A_actor_zhuangfy_ui_overview_loop_01",
                0.275f,
                $"cloth_specular_recovery_zhuangfy_{ModeFileToken(mode)}.png");
        }

        public static void RenderBothRuntimeReferenceProbes()
        {
            RenderWulfaRuntimeReferenceProbe();
            RenderZhuangfyRuntimeReferenceProbe();
        }

        private static string ModeFileToken(
            EndfieldRecoveredClothSpecularProbe.ResponseMode mode)
        {
            switch (mode)
            {
                case EndfieldRecoveredClothSpecularProbe.ResponseMode.RecoveredDirectGgx:
                    return "mode1_recovered_direct_ggx";
                case EndfieldRecoveredClothSpecularProbe.ResponseMode.RecoveredDirectGgxAndCubemap:
                    return "mode2_recovered_direct_ggx_cubemap";
                case EndfieldRecoveredClothSpecularProbe.ResponseMode.CanonicalDirectAndRecoveredCubemap:
                    return "mode3_canonical_direct_cubemap";
                default:
                    return "mode0_canonical";
            }
        }

        private static void InvokeRuntimeReferenceRender(
            string actorName,
            string clipName,
            float sampleTime,
            string outputFileName)
        {
            if (RenderRuntimeReferenceActorPreview == null)
            {
                throw new MissingMethodException(
                    typeof(EndfieldManifestCharacterSetup).FullName,
                    "RenderRuntimeReferenceActorPreview");
            }

            try
            {
                RenderRuntimeReferenceActorPreview.Invoke(
                    null,
                    new object[]
                    {
                        actorName,
                        clipName,
                        sampleTime,
                        outputFileName,
                    });
            }
            catch (TargetInvocationException exception)
            {
                throw exception.InnerException ?? exception;
            }
        }
    }
}

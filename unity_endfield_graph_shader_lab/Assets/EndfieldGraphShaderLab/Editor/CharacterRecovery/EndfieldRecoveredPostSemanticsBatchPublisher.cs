using System;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Publishes the offline-recovered CharInfo post selector for editor batch jobs.
    /// The selector is disabled unless the environment explicitly opts in.
    /// </summary>
    [InitializeOnLoad]
    public static class EndfieldRecoveredPostSemanticsBatchPublisher
    {
        public const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_POST_SEMANTICS";

        private const string SelectorProperty =
            "_EndfieldRecoveredPostSemantics";

        private static readonly int SelectorId =
            Shader.PropertyToID(SelectorProperty);

        private static readonly MethodInfo RenderRuntimeReferenceActorPreview =
            typeof(EndfieldManifestCharacterSetup).GetMethod(
                "RenderRuntimeReferenceActorPreview",
                BindingFlags.NonPublic | BindingFlags.Static);

        static EndfieldRecoveredPostSemanticsBatchPublisher()
        {
            PublishFromEnvironment();
        }

        /// <summary>
        /// Re-publishes the selector and returns the resolved value. Accepted enabled
        /// values are 1, true, yes, and on (case-insensitive); every other value is 0.
        /// </summary>
        public static float PublishFromEnvironment()
        {
            string raw = Environment.GetEnvironmentVariable(EnvironmentVariable);
            float value = IsExplicitlyEnabled(raw) ? 1.0f : 0.0f;
            Shader.SetGlobalFloat(SelectorId, value);
            Debug.Log(
                $"Recovered CharInfo post selector: {SelectorProperty}={value:0} " +
                $"({EnvironmentVariable}={FormatForLog(raw)})");
            return value;
        }

        public static void RenderWulfaRuntimeReferenceProbe()
        {
            PublishFromEnvironment();
            InvokeRuntimeReferenceRender(
                "Wulfa",
                "A_actor_wulfa_ui_overview_loop_01",
                0.95f,
                "charinfo_post_recovery/wulfa_recovered_post_semantics.png");
        }

        public static void RenderZhuangfyRuntimeReferenceProbe()
        {
            PublishFromEnvironment();
            InvokeRuntimeReferenceRender(
                "Zhuangfy",
                "A_actor_zhuangfy_ui_overview_loop_01",
                0.275f,
                "charinfo_post_recovery/zhuangfy_recovered_post_semantics.png");
        }

        public static void RenderWulfaRuntimeReferenceBloomPyramidProbe()
        {
            PublishFromEnvironment();
            InvokeRuntimeReferenceRender(
                "Wulfa",
                "A_actor_wulfa_ui_overview_loop_01",
                0.95f,
                "charinfo_post_recovery_mip_pyramid/wulfa_recovered_scene_bloom.png");
        }

        public static void RenderWulfaRuntimeReferenceBloomPyramidSelectorZeroControl()
        {
            PublishFromEnvironment();
            InvokeRuntimeReferenceRender(
                "Wulfa",
                "A_actor_wulfa_ui_overview_loop_01",
                0.95f,
                "charinfo_post_recovery_mip_pyramid/wulfa_selector0_control.png");
        }

        public static void RenderZhuangfyRuntimeReferenceBloomPyramidProbe()
        {
            PublishFromEnvironment();
            InvokeRuntimeReferenceRender(
                "Zhuangfy",
                "A_actor_zhuangfy_ui_overview_loop_01",
                0.275f,
                "charinfo_post_recovery_mip_pyramid/zhuangfy_recovered_scene_bloom.png");
        }

        public static void RenderWulfaAnalyticLutFallbackProbe()
        {
            PublishFromEnvironment();
            InvokeRuntimeReferenceRender(
                "Wulfa",
                "A_actor_wulfa_ui_overview_loop_01",
                0.95f,
                "charinfo_post_lut_fallback/wulfa_analytic_fallback.png");
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

        private static bool IsExplicitlyEnabled(string raw)
        {
            if (string.IsNullOrWhiteSpace(raw))
                return false;

            switch (raw.Trim().ToLowerInvariant())
            {
                case "1":
                case "true":
                case "yes":
                case "on":
                    return true;
                default:
                    return false;
            }
        }

        private static string FormatForLog(string raw)
        {
            return string.IsNullOrWhiteSpace(raw) ? "<unset>" : raw.Trim();
        }
    }
}

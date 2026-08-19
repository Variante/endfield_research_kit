using System;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Batch-only selector and fixed-pose publisher for the recovered
    /// CharacterNPR hair material response. It is disabled unless explicitly
    /// enabled by the environment.
    /// </summary>
    [InitializeOnLoad]
    public static class EndfieldRecoveredHairResponseBatchPublisher
    {
        public const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_HAIR_RESPONSE_SEMANTICS";

        private const string RecoveredKeyword =
            "ENDFIELD_RECOVERED_HAIR_RESPONSE";

        private static readonly MethodInfo RenderRuntimeReferenceActorPreview =
            typeof(EndfieldManifestCharacterSetup).GetMethod(
                "RenderRuntimeReferenceActorPreview",
                BindingFlags.NonPublic | BindingFlags.Static);

        static EndfieldRecoveredHairResponseBatchPublisher()
        {
            PublishFromEnvironment();
        }

        public static float PublishFromEnvironment()
        {
            string raw = Environment.GetEnvironmentVariable(EnvironmentVariable);
            float value = IsExplicitlyEnabled(raw) ? 1.0f : 0.0f;
            if (value > 0.5f)
                Shader.EnableKeyword(RecoveredKeyword);
            else
                Shader.DisableKeyword(RecoveredKeyword);
            Debug.Log(
                $"Recovered hair-response keyword: {RecoveredKeyword}={value:0} " +
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
                "hair_response_recovery/wulfa_recovered_hair_response.png");
        }

        public static void RenderZhuangfyRuntimeReferenceProbe()
        {
            PublishFromEnvironment();
            InvokeRuntimeReferenceRender(
                "Zhuangfy",
                "A_actor_zhuangfy_ui_overview_loop_01",
                0.275f,
                "hair_response_recovery/zhuangfy_recovered_hair_response.png");
        }

        public static void RenderBothRuntimeReferenceProbes()
        {
            RenderWulfaRuntimeReferenceProbe();
            RenderZhuangfyRuntimeReferenceProbe();
        }

        public static void RenderWulfaSelectorZeroControl()
        {
            PublishFromEnvironment();
            InvokeRuntimeReferenceRender(
                "Wulfa",
                "A_actor_wulfa_ui_overview_loop_01",
                0.95f,
                "hair_response_recovery/wulfa_selector0_control.png");
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

using System;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Batch-only selector for comparing the recovered CharacterNPR_Skin
    /// highlight-map addressing contract without changing generated materials.
    /// </summary>
    [InitializeOnLoad]
    public static class EndfieldRecoveredFaceHighlightBatchPublisher
    {
        public const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_FACE_HIGHLIGHT_SEMANTICS";

        private const string SelectorProperty =
            "_EndfieldRecoveredFaceHighlightSemantics";

        private static readonly int SelectorId =
            Shader.PropertyToID(SelectorProperty);

        private static readonly MethodInfo RenderRuntimeReferenceActorPreview =
            typeof(EndfieldManifestCharacterSetup).GetMethod(
                "RenderRuntimeReferenceActorPreview",
                BindingFlags.NonPublic | BindingFlags.Static);

        static EndfieldRecoveredFaceHighlightBatchPublisher()
        {
            PublishFromEnvironment();
        }

        public static float PublishFromEnvironment()
        {
            string raw = Environment.GetEnvironmentVariable(EnvironmentVariable);
            float value = IsExplicitlyEnabled(raw) ? 1.0f : 0.0f;
            Shader.SetGlobalFloat(SelectorId, value);
            Debug.Log(
                $"Recovered face-highlight selector: {SelectorProperty}={value:0} " +
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
                "material_response_audit/wulfa_face_highlight_semantics.png");
        }

        public static void RenderZhuangfyRuntimeReferenceProbe()
        {
            PublishFromEnvironment();
            InvokeRuntimeReferenceRender(
                "Zhuangfy",
                "A_actor_zhuangfy_ui_overview_loop_01",
                0.275f,
                "material_response_audit/zhuangfy_face_highlight_semantics.png");
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

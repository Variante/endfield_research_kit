using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Reflection;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Renders opt-in fixed-exposure probes for the recovered CharInfo post path.
    /// This is a perceptual calibration aid: an SDR reference cannot identify the
    /// original frame's HDR histogram or temporal exposure history.
    /// </summary>
    public static class EndfieldRecoveredPostExposureSweepBatch
    {
        public const string ExposureEnvironmentVariable =
            "ENDFIELD_RECOVERED_POST_EXPOSURE_EV";

        public const string SweepEnvironmentVariable =
            "ENDFIELD_RECOVERED_POST_EXPOSURE_SWEEP";

        private const string RecoveredPostEnvironmentVariable =
            "ENDFIELD_RECOVERED_POST_SEMANTICS";

        private const int RuntimeReferenceWidth = 3840;
        private const int RuntimeReferenceHeight = 2160;

        private static readonly float[] DefaultExposureValues =
        {
            0.0f,
            0.5f,
            1.0f,
            1.5f,
            2.0f,
        };

        private static readonly MethodInfo RenderRuntimeReferenceActorPreview =
            typeof(EndfieldManifestCharacterSetup).GetMethod(
                "RenderRuntimeReferenceActorPreview",
                BindingFlags.NonPublic | BindingFlags.Static);

        private static readonly MethodInfo RenderPreparedPreview =
            typeof(EndfieldManifestCharacterSetup).GetMethod(
                "RenderPreview",
                BindingFlags.NonPublic | BindingFlags.Static,
                null,
                new[] { typeof(string), typeof(int), typeof(int) },
                null);

        [MenuItem("Endfield/Character Recovery Lab/Render Recovered Post Exposure Sweep/Wulfa")]
        public static void RenderWulfaExposureSweep()
        {
            RenderActorExposureSweep(
                "Wulfa",
                "A_actor_wulfa_ui_overview_loop_01",
                0.95f,
                "wulfa");
        }

        [MenuItem("Endfield/Character Recovery Lab/Render Recovered Post Exposure Sweep/Zhuangfy")]
        public static void RenderZhuangfyExposureSweep()
        {
            RenderActorExposureSweep(
                "Zhuangfy",
                "A_actor_zhuangfy_ui_overview_loop_01",
                0.275f,
                "zhuangfy");
        }

        public static void RenderBothExposureSweeps()
        {
            RenderWulfaExposureSweep();
            RenderZhuangfyExposureSweep();
        }

        private static void RenderActorExposureSweep(
            string actorName,
            string clipName,
            float sampleTime,
            string outputStem)
        {
            if (RenderRuntimeReferenceActorPreview == null)
            {
                throw new MissingMethodException(
                    typeof(EndfieldManifestCharacterSetup).FullName,
                    "RenderRuntimeReferenceActorPreview");
            }

            IReadOnlyList<float> exposureValues = ResolveExposureValues();
            string previousExposure = Environment.GetEnvironmentVariable(
                ExposureEnvironmentVariable);
            string previousRecoveredPost = Environment.GetEnvironmentVariable(
                RecoveredPostEnvironmentVariable);

            try
            {
                Environment.SetEnvironmentVariable(
                    RecoveredPostEnvironmentVariable,
                    "1");
                EndfieldRecoveredPostSemanticsBatchPublisher.PublishFromEnvironment();

                for (int index = 0; index < exposureValues.Count; index++)
                {
                    float exposureEV = exposureValues[index];
                    string serializedExposure = exposureEV.ToString(
                        "0.######",
                        CultureInfo.InvariantCulture);
                    Environment.SetEnvironmentVariable(
                        ExposureEnvironmentVariable,
                        serializedExposure);

                    string outputFileName =
                        "charinfo_post_exposure_sweep/" +
                        outputStem + "_ev_" + FormatExposureForFileName(exposureEV) +
                        ".png";
                    Debug.Log(
                        $"Rendering recovered-post exposure sweep: {actorName}, " +
                        $"EV {exposureEV:+0.###;-0.###;0}, {outputFileName}");

                    if (index == 0)
                    {
                        InvokeRuntimeReferenceRender(
                            actorName,
                            clipName,
                            sampleTime,
                            outputFileName);
                    }
                    else
                    {
                        RenderPreparedActorAtExposure(
                            actorName,
                            exposureEV,
                            outputFileName);
                    }
                }
            }
            finally
            {
                Environment.SetEnvironmentVariable(
                    ExposureEnvironmentVariable,
                    previousExposure);
                Environment.SetEnvironmentVariable(
                    RecoveredPostEnvironmentVariable,
                    previousRecoveredPost);
                EndfieldRecoveredPostSemanticsBatchPublisher.PublishFromEnvironment();
            }
        }

        private static void RenderPreparedActorAtExposure(
            string actorName,
            float exposureEV,
            string outputFileName)
        {
            if (RenderPreparedPreview == null)
            {
                throw new MissingMethodException(
                    typeof(EndfieldManifestCharacterSetup).FullName,
                    "RenderPreview(string,int,int)");
            }

            Camera camera = Camera.main ?? UnityEngine.Object.FindObjectOfType<Camera>();
            if (camera == null)
                throw new InvalidOperationException("Prepared exposure sweep has no camera.");

            EndfieldHGOperatorPresentation presentation =
                camera.GetComponent<EndfieldHGOperatorPresentation>();
            if (presentation == null)
            {
                throw new InvalidOperationException(
                    $"Prepared {actorName} exposure sweep has no operator presentation.");
            }

            presentation.fixedPostExposureEV = exposureEV;
            EditorUtility.SetDirty(presentation);

            string outputPath = Path.GetFullPath(Path.Combine(
                Application.dataPath,
                "../../scratch",
                outputFileName));
            Directory.CreateDirectory(Path.GetDirectoryName(outputPath) ?? ".");

            try
            {
                RenderPreparedPreview.Invoke(
                    null,
                    new object[]
                    {
                        outputPath,
                        RuntimeReferenceWidth,
                        RuntimeReferenceHeight,
                    });
            }
            catch (TargetInvocationException exception)
            {
                throw exception.InnerException ?? exception;
            }

            Debug.Log(
                $"Rendered prepared {actorName} exposure sweep at " +
                $"{exposureEV:+0.###;-0.###;0} EV: {outputPath}");
        }

        private static void InvokeRuntimeReferenceRender(
            string actorName,
            string clipName,
            float sampleTime,
            string outputFileName)
        {
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

        private static IReadOnlyList<float> ResolveExposureValues()
        {
            string raw = Environment.GetEnvironmentVariable(
                SweepEnvironmentVariable);
            if (string.IsNullOrWhiteSpace(raw))
                return DefaultExposureValues;

            var resolved = new List<float>();
            var unique = new HashSet<float>();
            foreach (string token in raw.Split(','))
            {
                if (!float.TryParse(
                        token.Trim(),
                        NumberStyles.Float,
                        CultureInfo.InvariantCulture,
                        out float value) ||
                    float.IsNaN(value) ||
                    float.IsInfinity(value))
                {
                    Debug.LogWarning(
                        $"Ignoring invalid exposure sweep value: {token.Trim()}");
                    continue;
                }

                value = Mathf.Clamp(value, -4.0f, 4.0f);
                if (unique.Add(value))
                    resolved.Add(value);
            }

            if (resolved.Count > 0)
                return resolved;

            Debug.LogWarning(
                $"{SweepEnvironmentVariable} contained no valid values; " +
                "using the default exposure sweep.");
            return DefaultExposureValues;
        }

        private static string FormatExposureForFileName(float exposureEV)
        {
            string sign = exposureEV < 0.0f ? "m" : "p";
            return sign + Mathf.Abs(exposureEV).ToString(
                "0.00",
                CultureInfo.InvariantCulture).Replace('.', '_');
        }
    }
}

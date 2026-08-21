using System;
using System.Collections.Generic;
using System.Globalization;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Renders one actor at several animation phases in a single editor
    /// session, so a computed phase can be checked against a recorded
    /// reference frame.
    ///
    /// The recorded roster walkthrough catches every character inside its
    /// ui_overview_start clip rather than the idle loop, and
    /// video_segment_boundaries.json pins the selection instant to a frame.
    /// What that leaves is a residual of roughly +/- 0.7 s, because the
    /// character-model swap leads the panel settle by a variable amount. This
    /// sweeps that residual instead of sweeping an unknown phase across a whole
    /// loop.
    ///
    /// Driven by environment variables so a batch run can vary them without
    /// editing code:
    ///
    ///   ENDFIELD_PHASE_SWEEP_ACTOR   actor directory name, e.g. Wulfa
    ///   ENDFIELD_PHASE_SWEEP_CLIP    clip name without extension
    ///   ENDFIELD_PHASE_SWEEP_TIMES   comma-separated sample times in seconds
    ///   ENDFIELD_PHASE_SWEEP_STEM    output stem under scratch/
    ///   ENDFIELD_PHASE_SWEEP_OUTPUT_DIRECTORY  relative scratch directory
    ///   ENDFIELD_PHASE_SWEEP_REUSE_SCENE  keep one scene for all samples
    /// </summary>
    internal static class EndfieldRecoveredOverviewPhaseSweep
    {
        private const string ActorVariable = "ENDFIELD_PHASE_SWEEP_ACTOR";
        private const string ClipVariable = "ENDFIELD_PHASE_SWEEP_CLIP";
        private const string TimesVariable = "ENDFIELD_PHASE_SWEEP_TIMES";
        private const string StemVariable = "ENDFIELD_PHASE_SWEEP_STEM";
        private const string OutputDirectoryVariable =
            "ENDFIELD_PHASE_SWEEP_OUTPUT_DIRECTORY";
        private const string ReuseSceneVariable =
            "ENDFIELD_PHASE_SWEEP_REUSE_SCENE";

        private static readonly MethodInfo RenderRuntimeReferenceActorPreview =
            typeof(EndfieldManifestCharacterSetup).GetMethod(
                "RenderRuntimeReferenceActorPreview",
                BindingFlags.NonPublic | BindingFlags.Static);
        private static readonly MethodInfo RenderRuntimeReferenceActorSweep =
            typeof(EndfieldManifestCharacterSetup).GetMethod(
                "RenderRuntimeReferenceActorSweep",
                BindingFlags.NonPublic | BindingFlags.Static);

        public static void RenderFromEnvironment()
        {
            if (RenderRuntimeReferenceActorPreview == null)
            {
                throw new MissingMethodException(
                    typeof(EndfieldManifestCharacterSetup).FullName,
                    "RenderRuntimeReferenceActorPreview");
            }

            string actor = Read(ActorVariable);
            string clip = Read(ClipVariable);
            string stem = Read(StemVariable);
            string outputDirectory = ReadOutputDirectory();
            IReadOnlyList<float> times = ReadTimes(TimesVariable);

            if (IsEnvironmentFlagEnabled(ReuseSceneVariable))
            {
                if (RenderRuntimeReferenceActorSweep == null)
                {
                    throw new MissingMethodException(
                        typeof(EndfieldManifestCharacterSetup).FullName,
                        "RenderRuntimeReferenceActorSweep");
                }
                try
                {
                    RenderRuntimeReferenceActorSweep.Invoke(
                        null,
                        new object[]
                        {
                            actor,
                            clip,
                            new List<float>(times).ToArray(),
                            outputDirectory,
                            stem,
                        });
                }
                catch (TargetInvocationException exception)
                {
                    throw exception.InnerException ?? exception;
                }
                return;
            }

            Debug.Log(
                $"Overview phase sweep: actor={actor}, clip={clip}, " +
                $"{times.Count} samples, stem={stem}");

            for (int index = 0; index < times.Count; index++)
            {
                float sampleTime = times[index];
                string outputFileName =
                    outputDirectory + "/" + stem + "_t" +
                    sampleTime.ToString("0.000", CultureInfo.InvariantCulture)
                        .Replace('.', 'p') +
                    ".png";
                Debug.Log(
                    $"Overview phase sweep sample {index + 1}/{times.Count}: " +
                    $"t={sampleTime.ToString("0.000", CultureInfo.InvariantCulture)}s " +
                    $"-> {outputFileName}");
                try
                {
                    RenderRuntimeReferenceActorPreview.Invoke(
                        null,
                        new object[] { actor, clip, sampleTime, outputFileName });
                }
                catch (TargetInvocationException exception)
                {
                    throw exception.InnerException ?? exception;
                }
            }

            Debug.Log($"Overview phase sweep complete: {times.Count} frames.");
        }

        private static string ReadOutputDirectory()
        {
            string value = Environment.GetEnvironmentVariable(OutputDirectoryVariable);
            if (string.IsNullOrWhiteSpace(value))
                return "charinfo_phase_sweep";

            string normalized = value.Trim().Replace('\\', '/').Trim('/');
            if (normalized.Length == 0 ||
                normalized.StartsWith("/", StringComparison.Ordinal) ||
                normalized.Contains("..", StringComparison.Ordinal))
            {
                throw new InvalidOperationException(
                    $"{OutputDirectoryVariable} must be a non-empty relative directory.");
            }
            return normalized;
        }

        private static bool IsEnvironmentFlagEnabled(string variable)
        {
            string value = Environment.GetEnvironmentVariable(variable);
            if (string.IsNullOrWhiteSpace(value))
                return false;
            value = value.Trim();
            return string.Equals(value, "1", StringComparison.OrdinalIgnoreCase) ||
                   string.Equals(value, "true", StringComparison.OrdinalIgnoreCase) ||
                   string.Equals(value, "yes", StringComparison.OrdinalIgnoreCase) ||
                   string.Equals(value, "on", StringComparison.OrdinalIgnoreCase);
        }

        private static string Read(string variable)
        {
            string value = Environment.GetEnvironmentVariable(variable);
            if (string.IsNullOrWhiteSpace(value))
            {
                throw new InvalidOperationException(
                    $"Overview phase sweep requires {variable}.");
            }
            return value.Trim();
        }

        private static IReadOnlyList<float> ReadTimes(string variable)
        {
            string value = Read(variable);
            var times = new List<float>();
            foreach (string token in value.Split(','))
            {
                string trimmed = token.Trim();
                if (trimmed.Length == 0)
                    continue;
                if (!float.TryParse(
                        trimmed,
                        NumberStyles.Float,
                        CultureInfo.InvariantCulture,
                        out float parsed))
                {
                    throw new InvalidOperationException(
                        $"Overview phase sweep could not parse a sample time: '{trimmed}'.");
                }
                if (parsed < 0.0f)
                {
                    throw new InvalidOperationException(
                        $"Overview phase sweep sample time is negative: {parsed}.");
                }
                times.Add(parsed);
            }
            if (times.Count == 0)
            {
                throw new InvalidOperationException(
                    $"Overview phase sweep found no sample times in {variable}.");
            }
            return times;
        }
    }
}

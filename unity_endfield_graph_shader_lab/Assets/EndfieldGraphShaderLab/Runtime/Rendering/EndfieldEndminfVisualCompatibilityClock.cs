using System;
using System.Globalization;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Opt-in timing bridge for Endminf's recovered `_02` post components.
    /// It is anchored to source effect creation, never level load.
    /// </summary>
    public static class EndfieldEndminfVisualCompatibilityClock
    {
        public struct RecoveredPostState
        {
            public float elapsed;
            public float radialIntensity;
            public float chromaticIntensity;
            public float effectivePower;
            public int mode;
            public Vector2 centerViewport;
        }

        public struct RecoveredOpeningStripState
        {
            public float elapsed;
            public float intensity;
            public float displacementPixels;
            public float chromaticEdgePixels;
        }

        public const string EnvironmentVariable =
            "ENDFIELD_ENDMINF_VISUAL_COMPATIBILITY";
        public const string PreRollSecondsEnvironmentVariable =
            "ENDFIELD_ENDMINF_VISUAL_COMPATIBILITY_PREROLL_SECONDS";
        public const float OpeningStripStartSeconds = 0.03333334f;
        public const float OpeningStripPeakSeconds = 0.06666667f;
        public const float OpeningStripEndSeconds = 0.35f;
        private static float startTime = float.NaN;
        private static float configuredPreRollSeconds;
        private static Transform overview02Root;
        private static readonly Vector3 RecoveredPostCenterLocal =
            new Vector3(0.0f, 1.266f, 0.0f);

        public static bool Requested
        {
            get
            {
                string value = Environment.GetEnvironmentVariable(EnvironmentVariable);
                return string.Equals(value, "1", StringComparison.Ordinal) ||
                    string.Equals(value, "true", StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(value, "on", StringComparison.OrdinalIgnoreCase);
            }
        }

        public static void MarkOverview02Start(Transform effectRoot)
        {
            if (Requested)
            {
                configuredPreRollSeconds = ResolvePreRollSeconds();
                startTime = Time.time - configuredPreRollSeconds;
                overview02Root = effectRoot;
            }
        }

        public static float ConfiguredPreRollSeconds => configuredPreRollSeconds;

        public static void ClearOverview02(Transform effectRoot)
        {
            if (overview02Root != effectRoot)
                return;
            startTime = float.NaN;
            configuredPreRollSeconds = 0.0f;
            overview02Root = null;
        }

        private static float ResolvePreRollSeconds()
        {
            string text = Environment.GetEnvironmentVariable(
                PreRollSecondsEnvironmentVariable);
            if (string.IsNullOrWhiteSpace(text))
                return 0.0f;
            if (float.TryParse(
                    text,
                    NumberStyles.Float,
                    CultureInfo.InvariantCulture,
                    out float seconds) &&
                !float.IsNaN(seconds) &&
                !float.IsInfinity(seconds) &&
                seconds >= 0.0f &&
                seconds <= 1.0f)
            {
                return seconds;
            }
            Debug.LogWarning(
                "Recovered Endminf visual compatibility pre-roll failed closed: " +
                $"{PreRollSecondsEnvironmentVariable} must be a finite value in [0,1].");
            return 0.0f;
        }

        public static bool TryGetElapsed(out float elapsed)
        {
            if (Requested && overview02Root != null && !float.IsNaN(startTime))
            {
                elapsed = Mathf.Max(0.0f, Time.time - startTime);
                return true;
            }
            elapsed = 0.0f;
            return false;
        }

        public static bool TryEvaluateRecoveredPost(
            Camera camera,
            out RecoveredPostState state)
        {
            state = default;
            if (camera == null || !TryGetElapsed(out float elapsed))
                return false;

            float chromatic = EvaluateSourceCurve(elapsed, 0.127f, 0.101f);
            float radial = EvaluateSourceCurve(elapsed, 0.152f, 0.109f);
            bool chromaticActive = chromatic > 0.0f;
            bool radialActive = radial > 0.0f;
            // The pinned native producer selects the nine-tap combined mode
            // when both effects are active and radial intensity exceeds 0.01.
            int mode = chromaticActive || radialActive
                ? (chromaticActive && radial > 0.01f ? 6 : 3)
                : 0;

            // A_fx_endminf_ui_overview_02 animates radial power to exactly
            // 1.0. The pinned Uber parameter producer blends from 1.0 when
            // both effects are active. Its separate no-radial default is 1.2.
            const float animatedRadialPower = 1.0f;
            float effectivePower = animatedRadialPower;
            if (chromaticActive && radialActive)
            {
                effectivePower = Mathf.Lerp(
                    1.0f,
                    animatedRadialPower,
                    Mathf.Clamp01(radial / chromatic));
            }

            state = new RecoveredPostState {
                elapsed = elapsed,
                radialIntensity = radial,
                chromaticIntensity = chromatic,
                effectivePower = effectivePower,
                mode = mode,
                centerViewport = GetRecoveredPostCenterViewport(camera)
            };
            return true;
        }

        public static bool TryEvaluateOpeningStrip(
            out RecoveredOpeningStripState state)
        {
            state = default;
            if (!TryGetElapsed(out float elapsed))
                return false;

            float intensity = EvaluateOpeningStripEnvelope(elapsed);
            if (intensity <= 0.0f)
                return false;

            state = new RecoveredOpeningStripState {
                elapsed = elapsed,
                intensity = intensity,
                displacementPixels = 34.0f * intensity,
                chromaticEdgePixels = 1.35f * intensity
            };
            return true;
        }

        public static float EvaluateOpeningStripEnvelope(float elapsed)
        {
            if (float.IsNaN(elapsed) || float.IsInfinity(elapsed) ||
                elapsed < OpeningStripStartSeconds ||
                elapsed >= OpeningStripEndSeconds)
            {
                return 0.0f;
            }

            if (elapsed < OpeningStripPeakSeconds)
            {
                return Mathf.SmoothStep(
                    0.0f,
                    1.0f,
                    (elapsed - OpeningStripStartSeconds) /
                        (OpeningStripPeakSeconds - OpeningStripStartSeconds));
            }

            return Mathf.SmoothStep(
                1.0f,
                0.0f,
                (elapsed - OpeningStripPeakSeconds) /
                    (OpeningStripEndSeconds - OpeningStripPeakSeconds));
        }

        private static float EvaluateSourceCurve(
            float time,
            float initialPeak,
            float latePeak)
        {
            if (time <= 0.16666667f)
                return Mathf.SmoothStep(initialPeak, 0.0f, time / 0.16666667f);
            if (time < 4.4f)
                return 0.0f;
            if (time <= 4.4333334f)
                return Mathf.SmoothStep(
                    0.0f,
                    latePeak,
                    (time - 4.4f) / 0.0333333f);
            if (time <= 4.6f)
                return Mathf.SmoothStep(
                    latePeak,
                    0.0f,
                    (time - 4.4333334f) / 0.1666665f);
            return 0.0f;
        }

        public static Vector2 GetRecoveredPostCenterViewport(Camera camera)
        {
            if (!Requested || overview02Root == null || camera == null)
                return new Vector2(0.5f, 0.5f);

            Vector3 viewport = camera.WorldToViewportPoint(
                overview02Root.TransformPoint(RecoveredPostCenterLocal));
            if (viewport.z <= 0.0f)
                return new Vector2(0.5f, 0.5f);

            // The native producer uses signed viewport space only to test and
            // normalize a far-offscreen center. An ordinary on-screen center
            // keeps the original 0..1 viewport coordinates. The previous
            // translation returned the signed test vector itself, moving the
            // captured (0.50998, 0.53291) hand center to the lower-left and
            // magnifying the whole-frame radial/chromatic pull.
            Vector2 center = new Vector2(viewport.x, viewport.y);
            Vector2 signedCenter = new Vector2(
                viewport.x * 2.0f - 1.0f,
                viewport.y * 2.0f - 1.0f);
            if (signedCenter.magnitude > 1.414f)
                center = (signedCenter.normalized + Vector2.one) * 0.5f;
            return new Vector2(
                Mathf.Clamp01(center.x),
                Mathf.Clamp01(center.y));
        }
    }
}

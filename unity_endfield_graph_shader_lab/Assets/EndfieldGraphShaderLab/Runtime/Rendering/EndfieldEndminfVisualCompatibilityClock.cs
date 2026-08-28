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
        public const float OpeningStripStartSeconds = 0.06666667f;
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
            if (float.IsNaN(elapsed) || float.IsInfinity(elapsed) ||
                elapsed < OpeningStripStartSeconds ||
                elapsed >= OpeningStripEndSeconds)
            {
                return false;
            }

            int frame = Mathf.FloorToInt(elapsed * 60.0f + 0.5f);
            if (!IsMeasuredOpeningStripFrame(frame))
                return false;

            state = new RecoveredOpeningStripState {
                elapsed = elapsed,
                intensity = 1.0f,
                displacementPixels = 274.0f,
                chromaticEdgePixels = 3.0f
            };
            return true;
        }

        public static bool IsMeasuredOpeningStripFrame(int frame)
        {
            switch (frame)
            {
                case 4:
                case 6:
                case 7:
                case 8:
                case 9:
                case 10:
                case 11:
                case 12:
                case 18:
                case 19:
                case 20:
                    return true;
                default:
                    return false;
            }
        }

        private static float EvaluateSourceCurve(
            float time,
            float initialPeak,
            float latePeak)
        {
            if (time <= 0.1f)
            {
                // Clean-reference frames 91-94 lose the broad camera pull in
                // roughly three 60-Hz samples while the character-owned
                // horizontal slices persist. The compatibility Uber magnifies
                // the native scalar, so retain 45% of the authored peak and
                // finish this broad response at 0.1 s. The separately measured
                // late crystal pulse below keeps its captured magnitude.
                return Mathf.SmoothStep(
                    initialPeak * 0.45f,
                    0.0f,
                    time / 0.1f);
            }
            // Retail frame 1818 registers the late Uber pulse peak at clean
            // frame 264 / overview phase 4.350000 s. The former curve was
            // five 60-Hz samples late. Preserve its captured rise/fall shape
            // and move only this pulse to the measured source phase.
            const float lateStartSeconds = 4.3166667f;
            const float latePeakSeconds = 4.35f;
            const float lateEndSeconds = 4.5166667f;
            if (time < lateStartSeconds)
                return 0.0f;
            if (time <= latePeakSeconds)
                return Mathf.SmoothStep(
                    0.0f,
                    latePeak,
                    (time - lateStartSeconds) /
                        (latePeakSeconds - lateStartSeconds));
            if (time <= lateEndSeconds)
                return Mathf.SmoothStep(
                    latePeak,
                    0.0f,
                    (time - latePeakSeconds) /
                        (lateEndSeconds - latePeakSeconds));
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

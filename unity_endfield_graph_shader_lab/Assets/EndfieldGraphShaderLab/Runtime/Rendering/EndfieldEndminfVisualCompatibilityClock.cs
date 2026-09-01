using System;
using System.Globalization;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Opt-in timing bridge for Endminf's recovered `_02` post components.
    /// Exact post evaluation follows the authenticated FromOveview
    /// AnimatorStateInfo clock. The separate measured-strip diagnostic retains
    /// a compatibility wall clock and cannot authorize source post output.
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
        public const string SourcePostEnvironmentVariable =
            "ENDFIELD_RECOVERED_ENDMINF_SOURCE_POST";
        public const string PreRollSecondsEnvironmentVariable =
            "ENDFIELD_ENDMINF_VISUAL_COMPATIBILITY_PREROLL_SECONDS";
        public const string MeasuredOpeningStripDiagnosticEnvironmentVariable =
            "ENDFIELD_ENDMINF_MEASURED_OPENING_STRIP_DIAGNOSTIC";
        public const float OpeningStripStartSeconds = 0.06666667f;
        public const float OpeningStripEndSeconds = 0.35f;
        private static float compatibilityStartTime = float.NaN;
        private static float configuredPreRollSeconds;
        private static Transform compatibilityOverview02Root;
        private static int compatibilityOverview02RootInstanceId;
        private static Transform sourcePostRoot;
        private static int sourcePostRootInstanceId;
        private static uint sourcePostGeneration;
        private static uint boundSourcePostGeneration;
        private static float sourcePostSeedSeconds = float.NaN;
        private static double sourcePostBindTime = double.NaN;
        private static EndfieldOverviewPlayback overview02SourceOwner;
        private static int overview02SourcePlaybackGeneration;
        private static bool sourcePostFailureLogged;
        private static readonly Vector3 RecoveredPostCenterLocal =
            new Vector3(0.0f, 1.266f, 0.0f);
        private const string RecoveredPostRuntimeRootName =
            "P_fxui_endminm003_overview_01__OverviewRuntime";
        private const string RecoveredPostRequestName =
            "P_fxui_endminm003_overview_01";
        private const string CompatibilityRuntimeRootName =
            "P_fxui_endminm003_overview_02__OverviewRuntime";

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

        public static bool MeasuredOpeningStripDiagnosticRequested =>
            string.Equals(
                Environment.GetEnvironmentVariable(
                    MeasuredOpeningStripDiagnosticEnvironmentVariable),
                "1",
                StringComparison.Ordinal);

        public static bool SourcePostRequested
        {
            get
            {
                string value = Environment.GetEnvironmentVariable(
                    SourcePostEnvironmentVariable);
                return string.Equals(value, "1", StringComparison.Ordinal) ||
                    string.Equals(value, "true", StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(value, "on", StringComparison.OrdinalIgnoreCase);
            }
        }

        public static bool BindOverview02SourceClock(
            Transform effectRoot,
            string requestPrefabName,
            float expectedDelay,
            EndfieldOverviewEffectSourceClock sourceClock,
            out string failure)
        {
            failure = string.Empty;
            if (!SourcePostRequested)
            {
                ClearSourcePost();
                failure = "source-post selector is disabled";
                return false;
            }
            if (effectRoot == null ||
                !string.Equals(effectRoot.name, RecoveredPostRuntimeRootName,
                    StringComparison.Ordinal))
            {
                ClearSourcePost();
                failure = "runtime root identity is not exact";
                return false;
            }
            if (!string.Equals(requestPrefabName, RecoveredPostRequestName,
                    StringComparison.Ordinal) || expectedDelay != 0.0f)
            {
                ClearSourcePost();
                failure = "request identity or zero-delay contract drifted";
                return false;
            }
            if (!effectRoot.gameObject.activeInHierarchy ||
                !sourceClock.valid || sourceClock.owner == null ||
                !IsSourceOwnerLive(sourceClock.owner,
                    sourceClock.playbackGeneration) ||
                sourceClock.stateFullPathHash !=
                    EndfieldOverviewPlayback.SourceOverviewStartFullPathHash ||
                float.IsNaN(sourceClock.elapsedSeconds) ||
                float.IsInfinity(sourceClock.elapsedSeconds) ||
                sourceClock.elapsedSeconds < 0.0f ||
                double.IsNaN(Time.timeAsDouble) ||
                double.IsInfinity(Time.timeAsDouble))
            {
                ClearSourcePost();
                failure = "source-state transaction is invalid or stale";
                return false;
            }

            // Stationary recovered effect roots are instantiated outside the
            // actor hierarchy. In that exact binding, validate the actor owner
            // through the transaction token rather than a parent relation.
            float sourceElapsed = sourceClock.elapsedSeconds;

            AdvanceSourcePostGeneration();
            sourcePostRoot = effectRoot;
            sourcePostRootInstanceId = effectRoot.GetInstanceID();
            boundSourcePostGeneration = sourcePostGeneration;
            sourcePostSeedSeconds = sourceElapsed;
            sourcePostBindTime = Time.timeAsDouble;
            overview02SourceOwner = sourceClock.owner;
            overview02SourcePlaybackGeneration = sourceClock.playbackGeneration;
            sourcePostFailureLogged = false;
            return true;
        }

        public static void MarkOverview02CompatibilityStart(Transform effectRoot)
        {
            if (!Requested || effectRoot == null ||
                !effectRoot.gameObject.activeInHierarchy ||
                !string.Equals(effectRoot.name, CompatibilityRuntimeRootName,
                    StringComparison.Ordinal))
                return;

            configuredPreRollSeconds = ResolvePreRollSeconds();
            compatibilityStartTime = Time.time - configuredPreRollSeconds;
            compatibilityOverview02Root = effectRoot;
            compatibilityOverview02RootInstanceId = effectRoot.GetInstanceID();
        }

        public static float ConfiguredPreRollSeconds => configuredPreRollSeconds;

        public static bool SourcePostSeedAuthenticated =>
            TryGetAuthenticatedSourcePostElapsed(out _);

        // The pinned native path proves the one-shot seed and ordering. The
        // lab advances that seed with public Unity scaled time because the
        // retail EffectInstance tick implementation is not source-closed.
        public static bool RetailEffectTickDomainExact => false;

        public static void ClearOverview02(Transform effectRoot)
        {
            if (sourcePostRoot == effectRoot &&
                (effectRoot == null ||
                    sourcePostRootInstanceId == effectRoot.GetInstanceID()))
                ClearSourcePost();

            if (compatibilityOverview02Root == effectRoot &&
                (effectRoot == null ||
                    compatibilityOverview02RootInstanceId ==
                        effectRoot.GetInstanceID()))
                ClearCompatibilityClock();
        }

        private static void ClearSourcePost()
        {
            if (sourcePostRoot != null || sourcePostRootInstanceId != 0 ||
                boundSourcePostGeneration != 0 ||
                overview02SourceOwner != null)
                AdvanceSourcePostGeneration();
            sourcePostRoot = null;
            sourcePostRootInstanceId = 0;
            boundSourcePostGeneration = 0;
            sourcePostSeedSeconds = float.NaN;
            sourcePostBindTime = double.NaN;
            overview02SourceOwner = null;
            overview02SourcePlaybackGeneration = 0;
        }

        private static void ClearCompatibilityClock()
        {
            compatibilityStartTime = float.NaN;
            configuredPreRollSeconds = 0.0f;
            compatibilityOverview02Root = null;
            compatibilityOverview02RootInstanceId = 0;
        }

        private static void AdvanceSourcePostGeneration()
        {
            unchecked
            {
                sourcePostGeneration++;
            }
            if (sourcePostGeneration == 0)
                sourcePostGeneration = 1;
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
            if (Requested && compatibilityOverview02Root != null &&
                compatibilityOverview02Root.gameObject.activeInHierarchy &&
                compatibilityOverview02RootInstanceId ==
                    compatibilityOverview02Root.GetInstanceID() &&
                !float.IsNaN(compatibilityStartTime))
            {
                elapsed = Mathf.Max(0.0f, Time.time - compatibilityStartTime);
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
            if (camera == null ||
                !TryGetAuthenticatedSourcePostElapsed(out float elapsed))
                return false;

            if (!EndfieldRecoveredEndminfSourcePostCurves.TryEvaluate(
                    elapsed,
                    out float chromatic,
                    out float radial,
                    out float animatedRadialPower,
                    out string sourcePostFailure))
            {
                if (!sourcePostFailureLogged)
                {
                    sourcePostFailureLogged = true;
                    Debug.LogWarning(
                        "Recovered Endminf source post failed closed: " +
                        sourcePostFailure);
                }
                return false;
            }
            bool chromaticActive = chromatic > 0.0f;
            bool radialActive = radial > 0.0f;
            // The pinned native producer selects the nine-tap combined mode
            // when both effects are active and radial intensity exceeds 0.01.
            int mode = chromaticActive || radialActive
                ? (chromaticActive && radial > 0.01f ? 6 : 3)
                : 0;

            // The serialized clip owns radial power. The pinned Uber parameter
            // producer blends from 1.0 when both effects are active. Its
            // separate no-radial default is 1.2.
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

        private static bool TryGetAuthenticatedSourcePostElapsed(
            out float elapsed)
        {
            if (!SourcePostRequested)
            {
                ClearSourcePost();
                elapsed = 0.0f;
                return false;
            }
            if (sourcePostRoot != null &&
                sourcePostRoot.gameObject.activeInHierarchy &&
                sourcePostRootInstanceId == sourcePostRoot.GetInstanceID() &&
                boundSourcePostGeneration != 0 &&
                boundSourcePostGeneration == sourcePostGeneration &&
                overview02SourceOwner != null &&
                IsSourceOwnerLive(overview02SourceOwner,
                    overview02SourcePlaybackGeneration) &&
                !float.IsNaN(sourcePostSeedSeconds) &&
                !float.IsInfinity(sourcePostSeedSeconds) &&
                !double.IsNaN(sourcePostBindTime) &&
                !double.IsInfinity(sourcePostBindTime))
            {
                // AnimatorBehaviourPlayEffect._SyncEffectTime samples
                // length*normalizedTime once after the EffectInstance has
                // started. The effect then owns progression. Preserve that
                // one-shot source seed and advance it with Unity's scaled
                // engine clock; never re-poll the body Animator here.
                double delta = Time.timeAsDouble - sourcePostBindTime;
                elapsed = sourcePostSeedSeconds + (float)delta;
                if (!double.IsNaN(delta) && !double.IsInfinity(delta) &&
                    delta >= 0.0 && !float.IsNaN(elapsed) &&
                    !float.IsInfinity(elapsed) && elapsed >= 0.0f)
                    return true;
            }
            // Inactive/destroyed roots, stale playback owners, invalid
            // Animators, and invalid engine-time deltas permanently revoke
            // this transaction. Reactivation must obtain a fresh source seed.
            ClearSourcePost();
            elapsed = 0.0f;
            return false;
        }

        private static bool IsSourceOwnerLive(
            EndfieldOverviewPlayback owner,
            int playbackGeneration)
        {
            Animator animator = owner == null ? null : owner.animatorSource;
            return owner != null && owner.isActiveAndEnabled &&
                owner.gameObject.activeInHierarchy &&
                owner.AnimatorContractActive &&
                owner.PlaybackGeneration == playbackGeneration &&
                animator != null && animator.enabled &&
                animator.runtimeAnimatorController != null;
        }

        public static bool TryEvaluateOpeningStrip(
            out RecoveredOpeningStripState state)
        {
            state = default;
            // This evaluator reconstructs bounded rectangles measured from the
            // clean reference rather than the missing retail producer. Keep it
            // available for A/B diagnostics, but never admit it implicitly in
            // the canonical or interactive presentation.
            if (!MeasuredOpeningStripDiagnosticRequested ||
                !TryGetElapsed(out float elapsed))
                return false;
            if (float.IsNaN(elapsed) || float.IsInfinity(elapsed) ||
                elapsed < OpeningStripStartSeconds ||
                elapsed >= OpeningStripEndSeconds)
            {
                return false;
            }

            // The maintained clean-reference registration maps rendered Unity
            // frame N to extracted retail frame N+1 (bounded to +/-1 by the
            // decode anchor). The measured rectangles are retail-frame keyed.
            int frame = Mathf.FloorToInt(elapsed * 60.0f + 0.5f) + 1;
            if (!IsMeasuredOpeningStripFrame(frame))
                return false;

            state = new RecoveredOpeningStripState {
                elapsed = elapsed + 1.0f / 60.0f,
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

        public static Vector2 GetRecoveredPostCenterViewport(Camera camera)
        {
            if (!SourcePostRequested || sourcePostRoot == null || camera == null)
                return new Vector2(0.5f, 0.5f);

            Vector3 viewport = camera.WorldToViewportPoint(
                sourcePostRoot.TransformPoint(RecoveredPostCenterLocal));
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

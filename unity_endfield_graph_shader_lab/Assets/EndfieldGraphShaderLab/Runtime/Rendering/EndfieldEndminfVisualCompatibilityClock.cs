using System;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Opt-in timing bridge for Endminf's recovered `_02` post components.
    /// It is anchored to source effect creation, never level load.
    /// </summary>
    public static class EndfieldEndminfVisualCompatibilityClock
    {
        public const string EnvironmentVariable =
            "ENDFIELD_ENDMINF_VISUAL_COMPATIBILITY";
        private static float startTime = float.NaN;
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
                startTime = Time.time;
                overview02Root = effectRoot;
            }
        }

        public static bool TryGetElapsed(out float elapsed)
        {
            if (Requested && !float.IsNaN(startTime))
            {
                elapsed = Mathf.Max(0.0f, Time.time - startTime);
                return true;
            }
            elapsed = 0.0f;
            return false;
        }

        public static Vector2 GetRecoveredPostCenterViewport(Camera camera)
        {
            if (!Requested || overview02Root == null || camera == null)
                return new Vector2(0.5f, 0.5f);

            Vector3 viewport = camera.WorldToViewportPoint(
                overview02Root.TransformPoint(RecoveredPostCenterLocal));
            return viewport.z > 0.0f
                ? new Vector2(viewport.x, viewport.y)
                : new Vector2(0.5f, 0.5f);
        }
    }
}

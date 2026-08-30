using UnityEngine;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Camera-local consumer for the source-closed subset of one recovered
    /// environment phase. Unresolved EV-to-Unity intensity and broad global
    /// environment publication deliberately remain outside this component.
    /// </summary>
    [ExecuteAlways]
    [DisallowMultipleComponent]
    [AddComponentMenu("Endfield/Recovered/Environment Phase Consumer")]
    public sealed class EndfieldRecoveredEnvironmentPhaseConsumer : MonoBehaviour
    {
        public EndfieldRecoveredEnvironmentPhaseSnapshot snapshot;
        public Light sceneMainLight;
        public EndfieldHGRPCharacterLightingVolume characterLighting;

        public bool TryApplySourceClosedDirectLight(out string failure)
        {
            failure = null;
            if (snapshot == null ||
                (!snapshot.IsGachaRoomSourceClosed &&
                 !snapshot.IsCharacterInfoSourceClosed))
            {
                failure = "environment phase snapshot is absent or not source-closed";
                return false;
            }
            if (sceneMainLight == null || sceneMainLight.type != LightType.Directional)
            {
                failure = "scene main light is absent or not directional";
                return false;
            }

            sceneMainLight.color = snapshot.directColorMode == 1
                ? snapshot.directCustomColor
                : snapshot.directColor;
            sceneMainLight.useColorTemperature = true;
            sceneMainLight.colorTemperature = Mathf.Clamp(
                snapshot.directColorTemperature,
                1000f,
                20000f);

            if (!TryBuildSourceDirectionalRotation(
                    snapshot.directPitchYaw,
                    out Quaternion directRotation,
                    out _,
                    out failure))
            {
                return false;
            }
            sceneMainLight.transform.rotation = directRotation;

            // The source EV100 carrier is not equivalent to built-in Unity
            // Light intensity. Preserve the existing neutral intensity and
            // only select the already recovered native descriptor boundary.
            if (characterLighting != null)
            {
                characterLighting.sourceDirectIntensityDividePi =
                    snapshot.directIntensityDividePi;
                characterLighting.useRecoveredSourceMainLightDescriptor =
                    snapshot.directIntensityDividePi > 0f;
            }
            return true;
        }

        /// <summary>
        /// Replays the recovered HGLightConfig pitch/yaw consumer. Returning
        /// rotation-matrix column 2 is intentional: VisibleLight stores that
        /// local-to-world column, and LightCulling copies it without a second
        /// normalization.
        /// </summary>
        public static bool TryBuildSourceDirectionalRotation(
            Vector2 directPitchYaw,
            out Quaternion rotation,
            out Vector3 forward,
            out string failure)
        {
            rotation = Quaternion.identity;
            forward = Vector3.zero;
            failure = null;
            if (!IsFinite(directPitchYaw))
            {
                failure = "direct pitch/yaw is non-finite";
                return false;
            }

            // HGLightConfig.UpdateDirectFinalDirection builds the authored
            // rotation first, then its TRS/local-to-world matrix. Replacing
            // that route with a trig vector followed by LookRotation changes
            // the resulting binary32 matrix column.
            rotation = Quaternion.Euler(
                directPitchYaw.x,
                directPitchYaw.y,
                0.0f);
            forward = EndfieldRecoveredNativeLightMath.RotationMatrixColumn2(rotation);
            if (!IsFinite(forward))
            {
                failure = "direct pitch/yaw produced a non-finite light transform";
                return false;
            }
            return true;
        }

        private static bool IsFinite(Vector2 value) =>
            IsFinite(value.x) && IsFinite(value.y);

        private static bool IsFinite(Vector3 value) =>
            IsFinite(value.x) && IsFinite(value.y) && IsFinite(value.z);

        private static bool IsFinite(float value) =>
            !float.IsNaN(value) && !float.IsInfinity(value);
    }
}

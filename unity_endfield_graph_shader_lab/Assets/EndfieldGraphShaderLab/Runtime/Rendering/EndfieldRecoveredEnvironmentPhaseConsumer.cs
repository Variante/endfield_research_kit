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

            float pitch = snapshot.directPitchYaw.x * Mathf.Deg2Rad;
            float yaw = snapshot.directPitchYaw.y * Mathf.Deg2Rad;
            float cosPitch = Mathf.Cos(pitch);
            Vector3 directionToLight = new Vector3(
                -Mathf.Sin(yaw) * cosPitch,
                Mathf.Sin(pitch),
                -Mathf.Cos(yaw) * cosPitch).normalized;
            sceneMainLight.transform.rotation =
                Quaternion.LookRotation(-directionToLight, Vector3.up);

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
    }
}

using UnityEngine;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Camera-local post overrides recovered from the CharInfo operator screen.
    /// The original uses histogram auto exposure; fixedPostExposureEV remains an
    /// explicit compatibility approximation until exposure history is restored.
    /// </summary>
    [ExecuteAlways]
    [DisallowMultipleComponent]
    [RequireComponent(typeof(Camera))]
    public sealed class EndfieldHGOperatorPresentation : MonoBehaviour
    {
        [Range(-4.0f, 4.0f)] public float fixedPostExposureEV;
        [Range(0.0f, 2.0f)] public float saturation = 1.08f;

        [Header("Recovered CharInfo bloom")]
        [Range(0.0f, 4.0f)] public float characterBloomIntensity = 0.45f;
        [Range(0.0f, 4.0f)] public float characterBloomThreshold = 0.75f;
        [Range(0.0f, 1.0f)] public float characterBloomSoftness = 0.8f;

        [Header("Recovered scene profile")]
        [Tooltip(
            "Selects the source-closed GachaRoom_Volume general Bloom values " +
            "(threshold 0.95, intensity 0.5, raw scatter 0.4).")]
        public bool useRecoveredGachaRoomPostProfile;
        [Tooltip(
            "Camera-local source/hash gate for recovered environment consumers. " +
            "No phase is inferred when this reference is absent.")]
        public EndfieldRecoveredEnvironmentPhaseSnapshot environmentPhaseSnapshot;

        [Header("Recovered CharInfo vignette")]
        [Range(0.0f, 1.0f)] public float vignetteIntensity = 0.3f;
        [Range(0.0f, 1.0f)] public float vignetteSmoothness = 0.41f;
        [Range(0.0f, 1.0f)] public float vignetteRoundness = 0.94f;
    }
}

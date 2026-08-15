using UnityEngine;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Source-backed selection of one priority-600 HGEnvironmentPhase.
    /// This is a scene/camera data carrier: consumers must opt into individual
    /// fields and may not publish the whole snapshot as shader globals.
    /// </summary>
    [DisallowMultipleComponent]
    [AddComponentMenu("Endfield/Recovered/Environment Phase Snapshot")]
    public sealed class EndfieldRecoveredEnvironmentPhaseSnapshot : MonoBehaviour
    {
        public string sceneId;
        public string phaseName;
        public long phasePathId;
        public string phaseRawDataSha256;
        public int priority;
        public float manualBlendFactor;
        public float blendDistance;
        public float fadeInDuration;
        public float fadeOutDuration;

        [Header("Light config")]
        public Color directColor = Color.white;
        public int directColorMode;
        public Color directCustomColor = Color.white;
        public float directColorTemperature;
        public Vector2 directPitchYaw;
        public float directEV100;
        public float directIntensityDividePi;
        public float indirectDiffuseFactor;
        public float indirectSpecularFactor;
        public int indirectSpecularFactorType;

        [Header("Exposure config")]
        public bool autoExposureActive;
        public int autoExposureMode;
        public float manualEvCompensationManual;
        public float lerpUpSpeed;
        public float lerpDownSpeed;
        public float derivedTargetMultiplier;

        [TextArea] public string publicationBoundary =
            "Identity/light/exposure carrier only. Sky/SH, fog, volumetrics, " +
            "CSM and punctual-shadow publication remain fail closed.";

        public bool IsSourceClosed =>
            !string.IsNullOrEmpty(sceneId) &&
            !string.IsNullOrEmpty(phaseName) &&
            phasePathId != 0L &&
            !string.IsNullOrEmpty(phaseRawDataSha256) &&
            priority == 600 &&
            Mathf.Approximately(manualBlendFactor, 1f) &&
            Mathf.Approximately(blendDistance, 0f) &&
            Mathf.Approximately(fadeInDuration, 0f) &&
            Mathf.Approximately(fadeOutDuration, 0f);

        public void ConfigureGachaRoom()
        {
            sceneId = "GachaRoom";
            phaseName = "Env_gachaRoom_01";
            phasePathId = 6627355437943792087L;
            phaseRawDataSha256 =
                "cc84bc63c3f0c8da08559282f04df1cb2a2056a6427848dd35a3e5f4624d5bb7";
            priority = 600;
            manualBlendFactor = 1f;
            blendDistance = 0f;
            fadeInDuration = 0f;
            fadeOutDuration = 0f;
            directColor = new Color(1f, 0.82839394f, 0.6482222f, 1f);
            directColorMode = 0;
            directCustomColor = Color.white;
            directColorTemperature = 4000f;
            directPitchYaw = new Vector2(23.2f, 137.4f);
            directEV100 = 14.1f;
            directIntensityDividePi = 0f;
            indirectDiffuseFactor = 1f;
            indirectSpecularFactor = 1f;
            indirectSpecularFactorType = 1;
            autoExposureActive = true;
            autoExposureMode = 1;
            manualEvCompensationManual = 0f;
            lerpUpSpeed = 0.6f;
            lerpDownSpeed = 0.6f;
            derivedTargetMultiplier = 1f;
        }

        public void ConfigureCharacterInfo()
        {
            sceneId = "CharacterInfo";
            phaseName = "CharInfo_Env";
            phasePathId = 1201129019072041203L;
            phaseRawDataSha256 =
                "f9d1384c29f1e54599cd55e5f9c5c6d7eb9bd6f678d9fd104c7c329e6f1a66f9";
            priority = 600;
            manualBlendFactor = 1f;
            blendDistance = 0f;
            fadeInDuration = 0f;
            fadeOutDuration = 0f;
            directColor = Color.white;
            directColorMode = 1;
            directCustomColor = Color.white;
            directColorTemperature = 7000f;
            directPitchYaw = new Vector2(40f, -181.6f);
            directEV100 = 13.5f;
            directIntensityDividePi = 2.7475471f;
            indirectDiffuseFactor = 0.28772247f;
            indirectSpecularFactor = 0.28772247f;
            indirectSpecularFactorType = 0;
            autoExposureActive = false;
            autoExposureMode = 0;
            manualEvCompensationManual = 0f;
            lerpUpSpeed = 0.6f;
            lerpDownSpeed = 0.6f;
            derivedTargetMultiplier = 1f;
        }
    }
}

using System;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    [Serializable]
    public struct EndfieldRecoveredEffectLodRow
    {
        public Transform target;
        public int settingLodLevel;
        public int targetLayer;
        public bool distanceActive;
        public bool authoredInitialActive;
    }

    /// <summary>Build-locked EffectLodCfg._RefreshLod activation contract.</summary>
    public sealed class EndfieldRecoveredEffectLodActivation : MonoBehaviour
    {
        // Exact pinned normal-creation runtime values. The serialized row masks
        // (typically 15/3) are operands, not the EffectLodCfg show masks.
        public const int NormalCreationQualitySettingLodLevel = 8;
        public const int NormalCreationTargetLayers = 1;

        [SerializeField]
        private int qualitySettingLodLevel = NormalCreationQualitySettingLodLevel;
        public bool useDistanceLod;
        public bool cullDisabled;
        public bool cameraDistanceResolved;
        public EndfieldRecoveredEffectLodRow[] rows = Array.Empty<EndfieldRecoveredEffectLodRow>();
        private bool applying;

        public int QualitySettingLodLevel => qualitySettingLodLevel;

        public void UseNormalCreationDefaults()
        {
            qualitySettingLodLevel = NormalCreationQualitySettingLodLevel;
        }

        public void SetQualitySettingLodLevel(int requestedLevel)
        {
            // EffectManager._NormalizeSingleSettingLodLevel admits one quality
            // bit and falls back to the pinned normal-creation default.
            qualitySettingLodLevel = requestedLevel == 1 || requestedLevel == 2 ||
                requestedLevel == 4 || requestedLevel == 8
                ? requestedLevel
                : NormalCreationQualitySettingLodLevel;
        }

        private void OnEnable()
        {
            ApplyBeforePlay();
        }

        public void ApplyBeforePlay()
        {
            if (applying)
                return;
            if ((useDistanceLod && !cameraDistanceResolved) || !cullDisabled)
                throw new InvalidOperationException("Recovered EffectLod activation requires unresolved camera/distance inputs.");
            if (qualitySettingLodLevel != 1 && qualitySettingLodLevel != 2 &&
                qualitySettingLodLevel != 4 && qualitySettingLodLevel != 8)
                throw new InvalidOperationException("Recovered EffectLod quality is not a normalized single-bit level.");
            if (rows == null || rows.Length == 0)
                throw new InvalidOperationException("Recovered EffectLod rows are missing.");

            var activeStates = new bool[rows.Length];
            for (int index = 0; index < rows.Length; index++)
            {
                EndfieldRecoveredEffectLodRow row = rows[index];
                if (row.target == null)
                    throw new InvalidOperationException("Recovered EffectLod row target is missing.");
                activeStates[index] = row.authoredInitialActive &&
                    (row.settingLodLevel & qualitySettingLodLevel) != 0 &&
                    (row.targetLayer & NormalCreationTargetLayers) != 0 &&
                    row.distanceActive;
            }

            // Compute first, then mutate. Activating the component owner can
            // synchronously invoke OnEnable; the guard keeps that lifecycle
            // edge from observing a partially applied hierarchy.
            applying = true;
            try
            {
                for (int index = 0; index < rows.Length; index++)
                {
                    if (rows[index].target.gameObject != gameObject)
                        rows[index].target.gameObject.SetActive(activeStates[index]);
                }
                for (int index = 0; index < rows.Length; index++)
                {
                    if (rows[index].target.gameObject == gameObject)
                        rows[index].target.gameObject.SetActive(activeStates[index]);
                }
            }
            finally
            {
                applying = false;
            }
        }
    }
}

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
    }

    /// <summary>Build-locked EffectLodCfg._RefreshLod activation contract.</summary>
    public sealed class EndfieldRecoveredEffectLodActivation : MonoBehaviour
    {
        public int showSettingLodLevel = 15;
        public int showTargetLayers = 3;
        public bool useDistanceLod;
        public bool cullDisabled;
        public bool cameraDistanceResolved;
        public EndfieldRecoveredEffectLodRow[] rows = Array.Empty<EndfieldRecoveredEffectLodRow>();

        private void OnEnable()
        {
            ApplyBeforePlay();
        }

        public void ApplyBeforePlay()
        {
            if ((useDistanceLod && !cameraDistanceResolved) || !cullDisabled)
                throw new InvalidOperationException("Recovered EffectLod activation requires unresolved camera/distance inputs.");
            foreach (EndfieldRecoveredEffectLodRow row in rows)
            {
                if (row.target == null)
                    throw new InvalidOperationException("Recovered EffectLod row target is missing.");
                bool active = (row.settingLodLevel & showSettingLodLevel) != 0 &&
                    (row.targetLayer & showTargetLayers) != 0 && row.distanceActive;
                row.target.gameObject.SetActive(active);
            }
        }
    }
}

using System;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    public static class EndfieldLiZhiyanOverviewStaticMeshBindingValidator
    {
        private const string EffectName = "P_fxui_lizhiyan_overview_start_01";

        [MenuItem("Endfield/Character Recovery Lab/Validate Li Zhiyan Static Mesh Binding Gate")]
        public static void ValidateMenu()
        {
            var root = new GameObject(EffectName);
            try
            {
                var marker = root.AddComponent<EndfieldRecoveredStaticMeshEffectSource>();
                marker.contractSchema =
                    EndfieldRecoveredStaticMeshEffectSource.LiZhiyanStart01ContractSchema;
                marker.effectRoot = EffectName;
                marker.sourceGameObjectPathId = 1314393592276219621L;
                marker.sourceTransformPathId = 4995983695754262245L;
                marker.sourceEffectSettingPathId = 2305038813790631653L;
                marker.sourceEffectDuration = 2.2f;
                marker.sourceAnimatorPathId = -7686199192497981723L;
                marker.sourceAnimationHelperPathId = -8633596874860955931L;
                marker.sourceStartAnimationClipPathId = 7360398354216100382L;
                marker.sourcePayloadApplied = false;
                marker.sourceEffectSettingPayloadApplied = false;
                marker.sourceAnimationPayloadApplied = false;
                marker.sourceAggregateSha256 =
                    "5B83D031736E9CE864F1D2BE021C0E1A04BCA29D11291A506AD9740ADC047511";
                marker.visibleAdmission = false;
                marker.blockedBy = new[] { "source payloads are not imported" };

                var binding = new EndfieldRecoveredCharEffectSpawner.Binding
                {
                    bindingKind = EndfieldRecoveredCharEffectSpawner.BindingKind.StaticMesh,
                    requestPrefabName = EffectName,
                    prefab = root,
                    expectedEffectRoot = EffectName,
                    expectedDuration = 2.2f,
                };
                var request = new EndfieldOverviewEffectRequest
                {
                    prefabName = EffectName,
                    mountPoint = string.Empty,
                };
                bool admitted = EndfieldRecoveredCharEffectSpawner
                    .TryValidateBindingForRecoveryAudit(binding, request, out string reason);
                if (admitted || reason !=
                    "Static-mesh source contract has not admitted runtime visibility.")
                {
                    throw new InvalidOperationException(
                        "Li Zhiyan static-mesh binding did not fail closed: " + reason);
                }
                Debug.Log("[Endfield Li Zhiyan] start_01 static-mesh binding kind validated; " +
                    "source application and visible admission remain false.");
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }
    }
}

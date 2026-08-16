using System;
using System.Linq;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Validates the generated start_02 sibling diagnostic prefab without
    /// treating converted geometry or the managed shader as native admission.
    /// </summary>
    public static class EndfieldLiZhiyanStart02DiagnosticPrefabValidator
    {
        private const string EffectName = "P_fxui_lizhiyan_overview_start_02";
        private const string ContractSchema =
            "endfield.lizhiyan-overview-static-sibling-effects.v1";
        private const long RootGameObjectPathId = 2896713466425102497L;
        private const long RootTransformPathId = -210178290990919519L;
        private const long EffectSettingPathId = 3940221264379367585L;
        private const long AnimatorPathId = 9077272783571767457L;
        private const long HelperPathId = 8739770745933123745L;
        private const long ClipPathId = 7360398354216100382L;

        [MenuItem("Endfield/Character Recovery Lab/Validate Li Zhiyan start_02 Diagnostic Prefab")]
        public static void ValidateCommandLine()
        {
            ValidateGenerated(
                EndfieldLiZhiyanStart02DiagnosticPrefabImporter.PrefabPath, -1, -1);
        }

        public static void ValidateGenerated(
            string prefabPath, int unsupportedProperties, int appliedProperties)
        {
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
            Require(prefab != null, "Generated Li Zhiyan start_02 diagnostic prefab is missing");

            EndfieldRecoveredStaticMeshEffectSource marker =
                prefab.GetComponent<EndfieldRecoveredStaticMeshEffectSource>();
            Require(marker != null, "Generated Li Zhiyan start_02 marker is missing");
            Require(marker.contractSchema == ContractSchema &&
                marker.effectRoot == EffectName &&
                marker.sourceGameObjectPathId == RootGameObjectPathId &&
                marker.sourceTransformPathId == RootTransformPathId &&
                marker.sourceEffectSettingPathId == EffectSettingPathId &&
                marker.sourceAnimatorPathId == AnimatorPathId &&
                marker.sourceAnimationHelperPathId == HelperPathId,
                "Generated Li Zhiyan start_02 source identity drifted");
            Require(!marker.sourcePayloadApplied &&
                !marker.sourceEffectSettingPayloadApplied &&
                !marker.sourceAnimationPayloadApplied &&
                !marker.visibleAdmission &&
                !marker.sourceAnimationBindingsResolved &&
                Mathf.Abs(marker.sourceEffectDuration - 5f) < 0.0001f &&
                marker.sourceStartAnimationClip != null &&
                marker.sourceStartAnimationClipPathId == ClipPathId &&
                marker.blockedBy != null && marker.blockedBy.Length >= 4 &&
                marker.blockedBy.Any(value => value != null && value.Contains("provisional")),
                "Generated Li Zhiyan start_02 admission did not remain fail-closed");
            Require(marker.materialExecutionBoundary != null &&
                marker.materialExecutionBoundary.Contains("M12/M13=_LiMaterialMode 9") &&
                marker.materialExecutionBoundary.Contains("M14=_LiMaterialMode 11") &&
                marker.materialExecutionBoundary.Contains("15/53_partial"),
                "Generated Li Zhiyan start_02 material/animation boundary drifted");

            long[] expectedGameObjects =
            {
                RootGameObjectPathId,
                7723516932710912161L,
                -4584248681830690655L,
                -5197900411038412639L,
            };
            long[] expectedTransforms =
            {
                RootTransformPathId,
                -6379787651090296671L,
                -7289802502760050527L,
                -5897389556348170079L,
            };
            string[] expectedPaths =
            {
                EffectName,
                EffectName + "/S_fx_lzy_fenweiqiliu_02",
                EffectName + "/S_fx_lzy_fenweiqiliu_02 (1)",
                EffectName + "/S_fx_lzy_fenweiqiliu_02 (3)",
            };
            Require(marker.hierarchyNodes != null && marker.hierarchyNodes.Length == 4,
                "Generated start_02 hierarchy census drifted");
            for (int i = 0; i < expectedGameObjects.Length; i++)
            {
                EndfieldRecoveredStaticMeshHierarchyNodeSource node = marker.hierarchyNodes[i];
                Require(node != null && node.generatedTransform != null &&
                    node.gameObjectPathId == expectedGameObjects[i] &&
                    node.transformPathId == expectedTransforms[i] &&
                    node.hierarchy == expectedPaths[i],
                    "Generated start_02 hierarchy identity drifted at index " + i);
            }

            MeshFilter[] filters = prefab.GetComponentsInChildren<MeshFilter>(true);
            MeshRenderer[] renderers = prefab.GetComponentsInChildren<MeshRenderer>(true);
            ParticleSystem[] particles = prefab.GetComponentsInChildren<ParticleSystem>(true);
            Require(filters.Length == 3 && renderers.Length == 3 && particles.Length == 0,
                "Generated start_02 component census drifted");
            Require(filters.All(value => value.sharedMesh != null) &&
                renderers.All(value => value.sharedMaterials.Length == 1 &&
                    value.sharedMaterials[0] != null && value.sharedMaterials[0].shader != null &&
                    value.sharedMaterials[0].shader.name ==
                    "Endfield/Recovered/LiZhiyanStart01Diagnostic"),
                "Generated start_02 provisional mesh/material import is missing");

            Require(marker.staticMeshNodes != null && marker.staticMeshNodes.Length == 3,
                "Generated start_02 static mesh marker census drifted");
            float[] expectedModes = { 9f, 9f, 11f };
            long[] expectedMeshes = { 7032717393607757449L, 7032717393607757449L,
                7032717393607757449L };
            long[] expectedMaterials = { -481371258366057841L,
                2540816063756981481L, -2434886401441015548L };
            for (int i = 0; i < marker.staticMeshNodes.Length; i++)
            {
                EndfieldRecoveredStaticMeshNodeSource node = marker.staticMeshNodes[i];
                Require(node != null && node.generatedMeshFilter != null &&
                    node.generatedMeshRenderer != null && node.meshPathId == expectedMeshes[i] &&
                    node.materialPathIds.Length == 1 &&
                    node.materialPathIds[0] == expectedMaterials[i] &&
                    !node.nativeMeshPayloadApplied && !node.nativeRendererPayloadApplied &&
                    !node.nativeTexturePayloadsApplied && !node.exactShaderVariantsApplied &&
                    node.rendererFailClosedForUnrecoveredShader &&
                    Mathf.Abs(node.generatedMeshRenderer.sharedMaterials[0]
                        .GetFloat("_LiMaterialMode") - expectedModes[i]) < 0.001f,
                    "Generated start_02 mesh/material gate drifted at index " + i);
            }

            EndfieldLiZhiyanBehavioralAnimationSimulation simulation =
                prefab.GetComponent<EndfieldLiZhiyanBehavioralAnimationSimulation>();
            Require(simulation != null && simulation.SourceEffectRoot == EffectName &&
                simulation.SourceEffectSettingPathId == EffectSettingPathId &&
                simulation.SourceStartAnimationClipPathId == ClipPathId &&
                Mathf.Abs(simulation.EffectSettingLifetime - 5f) < 0.0001f &&
                !simulation.VisibleAdmission && !simulation.RetailAbiEquivalent,
                "Generated start_02 behavioral simulation identity/admission drifted");

            string report = unsupportedProperties >= 0
                ? "; shader-supported properties applied=" + appliedProperties +
                  ", unsupported serialized properties=" + unsupportedProperties
                : string.Empty;
            Debug.Log("[Endfield Li Zhiyan] start_02 diagnostic prefab validation passed" +
                report + "; Plane009=provisional; sourcePayloadApplied=false; " +
                "exactShaderVariantsApplied=false; visibleAdmission=false.");
        }

        private static void Require(bool condition, string message)
        {
            if (!condition)
                throw new InvalidOperationException(message);
        }
    }
}

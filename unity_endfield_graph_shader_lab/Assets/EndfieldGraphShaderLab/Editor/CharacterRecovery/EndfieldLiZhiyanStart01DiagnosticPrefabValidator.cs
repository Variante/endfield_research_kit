using System;
using System.Linq;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Validator for the generated Li start_01 diagnostic prefab.  The
    /// validator checks source identity and the intentional admission gates;
    /// it never registers an actor binding or treats a valid Unity prefab as
    /// proof of the retail native renderer path.
    /// </summary>
    public static class EndfieldLiZhiyanStart01DiagnosticPrefabValidator
    {
        [MenuItem(
            "Endfield/Character Recovery Lab/Validate Li Zhiyan start_01 Diagnostic Prefab")]
        public static void ValidateCommandLine()
        {
            ValidateGenerated(
                EndfieldLiZhiyanStart01DiagnosticPrefabImporter.GeneratedPrefabPath,
                -1, -1);
        }

        public static void ValidateGenerated(
            string prefabPath, int unsupportedProperties, int appliedProperties)
        {
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
            Require(prefab != null, "Generated Li Zhiyan diagnostic prefab is missing");
            EndfieldRecoveredStaticMeshEffectSource marker =
                prefab.GetComponent<EndfieldRecoveredStaticMeshEffectSource>();
            Require(marker != null, "Generated Li Zhiyan diagnostic marker is missing");
            Require(marker.contractSchema ==
                    EndfieldRecoveredStaticMeshEffectSource.LiZhiyanStart01ContractSchema &&
                marker.effectRoot == "P_fxui_lizhiyan_overview_start_01" &&
                marker.sourceGameObjectPathId == 1314393592276219621L &&
                marker.sourceTransformPathId == 4995983695754262245L &&
                marker.sourceEffectSettingPathId == 2305038813790631653L,
                "Generated Li Zhiyan root source identity drifted");
            Require(!marker.sourcePayloadApplied &&
                !marker.sourceEffectSettingPayloadApplied &&
                !marker.sourceAnimationPayloadApplied &&
                !marker.visibleAdmission &&
                marker.blockedBy != null && marker.blockedBy.Length > 0,
                "Generated Li Zhiyan diagnostic admission did not remain fail-closed");
            Require(marker.sourceStartAnimationClip != null &&
                marker.sourceStartAnimationClipPathId == 7360398354216100382L &&
                marker.sourceStartAnimationClipName ==
                    "A_fxui__lizhiyan_overview_start_01" &&
                Mathf.Abs(marker.sourceStartAnimationSampleRate - 30f) < 0.0001f &&
                Mathf.Abs(marker.sourceStartAnimationStopTime - 6.366667f) < 0.0001f,
                "Generated Li Zhiyan animation source identity drifted");
            Require(marker.hierarchyNodes != null && marker.hierarchyNodes.Length == 5 &&
                marker.staticMeshNodes != null && marker.staticMeshNodes.Length == 4,
                "Generated Li Zhiyan hierarchy census drifted");
            long[] expectedGameObjects =
            {
                1314393592276219621L, -3035674024450951451L,
                -8894984188664187163L, -4762788037748558107L,
                -5633037065891318043L,
            };
            long[] expectedTransforms =
            {
                4995983695754262245L, 5043134150308755173L,
                4605173516639106789L, -1254243568809380123L,
                -3446281828114336027L,
            };
            string[] expectedHierarchies =
            {
                "P_fxui_lizhiyan_overview_start_01",
                "P_fxui_lizhiyan_overview_start_01/S_fx_lzy_tiaodaifenwei_01 (4)",
                "P_fxui_lizhiyan_overview_start_01/S_fx_lzy_tiaodaifenwei_01 (5)",
                "P_fxui_lizhiyan_overview_start_01/S_fx_lzy_tiaodaifenwei_01 (6)",
                "P_fxui_lizhiyan_overview_start_01/S_fx_lzy_tiaodaifenwei_01 (7)",
            };
            for (int index = 0; index < expectedGameObjects.Length; index++)
            {
                EndfieldRecoveredStaticMeshHierarchyNodeSource node =
                    marker.hierarchyNodes[index];
                Require(node != null && node.gameObjectPathId == expectedGameObjects[index] &&
                    node.transformPathId == expectedTransforms[index] &&
                    node.hierarchy == expectedHierarchies[index] &&
                    node.generatedTransform != null,
                    "Generated Li Zhiyan hierarchy identity drifted at index " + index);
            }
            for (int index = 1; index < marker.hierarchyNodes.Length; index++)
            {
                Transform child = marker.hierarchyNodes[index].generatedTransform;
                Require(Vector3.Distance(child.localPosition,
                        new Vector3(0.40779486f, 1.0111285f, 0.50908583f)) < 0.00001f &&
                    Quaternion.Angle(child.localRotation,
                        new Quaternion(-0.7071068f, 0f, 0f, 0.7071068f)) < 0.001f,
                    "Generated Li Zhiyan child transform drifted at index " + index);
                Vector3 expectedScale = index == 4
                    ? new Vector3(2.54f, 2.5399997f, 2.5399997f)
                    : new Vector3(2.54f, 2.54f, 2.54f);
                Require(Vector3.Distance(child.localScale, expectedScale) < 0.00001f,
                    "Generated Li Zhiyan child scale drifted at index " + index);
            }

            MeshFilter[] filters = prefab.GetComponentsInChildren<MeshFilter>(true);
            MeshRenderer[] renderers = prefab.GetComponentsInChildren<MeshRenderer>(true);
            ParticleSystem[] particles = prefab.GetComponentsInChildren<ParticleSystem>(true);
            Require(filters.Length == 4 && renderers.Length == 4 && particles.Length == 0,
                "Generated Li Zhiyan diagnostic component census drifted");
            Require(filters.All(filter => filter.sharedMesh != null),
                "Generated Li Zhiyan diagnostic mesh import is missing");
            Require(renderers.All(renderer => renderer.sharedMaterials.Length == 1 &&
                renderer.sharedMaterials[0] != null &&
                renderer.sharedMaterials[0].shader != null &&
                renderer.sharedMaterials[0].shader.name ==
                    "Endfield/Recovered/VFXBaseV2SampleStack"),
                "Generated Li Zhiyan diagnostic material/shader identity drifted");
            Require(marker.staticMeshNodes.All(node =>
                node != null && node.generatedMeshFilter != null &&
                node.generatedMeshRenderer != null &&
                !node.nativeMeshPayloadApplied && !node.nativeRendererPayloadApplied &&
                !node.nativeTexturePayloadsApplied && !node.exactShaderVariantsApplied),
                "Generated Li Zhiyan native admission flags drifted");

            EndfieldLiZhiyanBehavioralAnimationSimulation simulation =
                prefab.GetComponent<EndfieldLiZhiyanBehavioralAnimationSimulation>();
            Require(simulation != null && simulation.SourceEffectRoot ==
                "P_fxui_lizhiyan_overview_start_01" &&
                simulation.SourceEffectSettingPathId == 2305038813790631653L &&
                simulation.SourceStartAnimationClipPathId == 7360398354216100382L &&
                !simulation.VisibleAdmission && !simulation.RetailAbiEquivalent,
                "Generated Li Zhiyan behavioral simulator identity/admission drifted");

            string report = unsupportedProperties >= 0
                ? "; shader-supported properties applied=" + appliedProperties +
                  ", unsupported serialized properties=" + unsupportedProperties
                : string.Empty;
            Debug.Log("[Endfield Li Zhiyan] start_01 diagnostic prefab validation passed" +
                report + "; sourcePayloadApplied=false; exactShaderVariantsApplied=false; " +
                "visibleAdmission=false; actor binding unchanged.");
        }

        private static void Require(bool condition, string message)
        {
            if (!condition)
                throw new InvalidOperationException(message);
        }
    }
}

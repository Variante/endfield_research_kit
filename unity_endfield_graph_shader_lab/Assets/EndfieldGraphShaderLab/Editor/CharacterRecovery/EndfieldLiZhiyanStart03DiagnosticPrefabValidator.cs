using System;
using System.Linq;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>Fail-closed validator for the isolated start_03 prefab.</summary>
    public static class EndfieldLiZhiyanStart03DiagnosticPrefabValidator
    {
        private const string Effect = "P_fxui_lizhiyan_overview_start_03";
        private const string Shader = "Endfield/Recovered/LiZhiyanStart01Diagnostic";
        private const long RootGameObject = -4762735294709058244L;
        private const long RootTransform = -1899328819351145156L;
        private const long EffectSetting = 8184202388571141436L;
        private const long Clip = 7360398354216100382L;
        [MenuItem("Endfield/Character Recovery Lab/Validate Li Zhiyan start_03 Diagnostic Prefab")]
        public static void ValidateCommandLine() { ValidateGenerated(EndfieldLiZhiyanStart03DiagnosticPrefabImporter.GeneratedPrefabPath, -1, -1); }

        public static void ValidateGenerated(string path, int unsupportedProperties, int appliedProperties)
        {
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            Require(prefab != null, "Generated start_03 prefab is missing");
            EndfieldRecoveredStaticMeshEffectSource marker = prefab.GetComponent<EndfieldRecoveredStaticMeshEffectSource>();
            Require(marker != null && marker.effectRoot == Effect && marker.sourceGameObjectPathId == RootGameObject && marker.sourceTransformPathId == RootTransform && marker.sourceEffectSettingPathId == EffectSetting, "start_03 source identity drifted");
            Require(marker.contractSchema == "endfield.lizhiyan-overview-static-sibling-effects.v1" && marker.sourceAggregateSha256 == "AB587FDA1E0AEC1761A10F334959541FA0217347E595D18415850791AE33545B", "start_03 contract identity drifted");
            Require(!marker.sourcePayloadApplied && !marker.sourceEffectSettingPayloadApplied && !marker.sourceAnimationPayloadApplied && !marker.visibleAdmission && !marker.sourceAnimationBindingsResolved, "start_03 admission is not fail-closed");
            Require(marker.sourceStartAnimationClip != null && marker.sourceStartAnimationClipPathId == Clip && Mathf.Abs(marker.sourceEffectDuration - 7f) < .0001f && Mathf.Abs(marker.sourceStartAnimationSampleRate - 30f) < .0001f && Mathf.Abs(marker.sourceStartAnimationStopTime - 6.366667f) < .0001f, "start_03 shared clip identity drifted");
            Require(marker.blockedBy != null && marker.blockedBy.Any(value => value != null && value.Contains("converted OBJ geometry is source-exact")) && marker.materialExecutionBoundary.Contains("visibleAdmission=false"), "start_03 exact/provisional geometry boundary drifted");
            Require(marker.hierarchyNodes != null && marker.hierarchyNodes.Length == 4 && marker.staticMeshNodes != null && marker.staticMeshNodes.Length == 3, "start_03 hierarchy census drifted");
            MeshFilter[] filters = prefab.GetComponentsInChildren<MeshFilter>(true); MeshRenderer[] renderers = prefab.GetComponentsInChildren<MeshRenderer>(true);
            Require(filters.Length == 3 && renderers.Length == 3 && filters.All(v => v.sharedMesh != null) && renderers.All(v => v.enabled && v.sharedMaterials.Length == 1 && v.sharedMaterials[0] != null && v.sharedMaterials[0].shader != null && v.sharedMaterials[0].shader.name == Shader), "start_03 renderer/material census drifted");
            long[] expectedMeshes = { -4003364140602261775L, -4003364140602261775L, 3893791131891476371L }; long[] expectedMaterials = { -7438264461631060117L, 9120706159938786131L, -6772801081383272744L };
            for (int i = 0; i < marker.staticMeshNodes.Length; i++) { EndfieldRecoveredStaticMeshNodeSource node = marker.staticMeshNodes[i]; Require(node != null && node.meshPathId == expectedMeshes[i] && node.materialPathIds.Length == 1 && node.materialPathIds[0] == expectedMaterials[i] && node.generatedMeshFilter != null && node.generatedMeshRenderer != null && !node.nativeMeshPayloadApplied && !node.nativeRendererPayloadApplied && !node.nativeTexturePayloadsApplied && !node.exactShaderVariantsApplied && node.rendererFailClosedForUnrecoveredShader, "start_03 static mesh source drifted at index " + i); Require(Mathf.Abs(node.generatedMeshRenderer.sharedMaterials[0].GetFloat("_LiMaterialMode") - 9f) < .001f, "start_03 material mode drifted at index " + i); }
            EndfieldLiZhiyanBehavioralAnimationSimulation simulation = prefab.GetComponent<EndfieldLiZhiyanBehavioralAnimationSimulation>(); Require(simulation != null && simulation.SourceEffectRoot == Effect && simulation.SourceEffectSettingPathId == EffectSetting && simulation.SourceStartAnimationClipPathId == Clip && !simulation.VisibleAdmission && !simulation.RetailAbiEquivalent, "start_03 behavioral simulation identity drifted");
            string report = unsupportedProperties >= 0 ? "; shader-supported properties applied=" + appliedProperties + ", unsupported serialized properties=" + unsupportedProperties : string.Empty;
            Debug.Log("[Endfield Li Zhiyan] start_03 diagnostic prefab validation passed" + report + "; native payload=false; exactShaderVariantsApplied=false; visibleAdmission=false.");
        }
        private static void Require(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
    }
}

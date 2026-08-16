using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;
using L = EndfieldGraphShaderLabEditor.EndfieldLastRiteOverviewHeadEffectImporter;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Validates exact material-to-DXBC evidence without admitting a visible shader.
    /// Live descriptor tables, PSO overrides, attachments, and draw ownership are
    /// deliberately outside this offline contract.
    /// </summary>
    public static class EndfieldLiZhiyanOverviewShaderEvidenceValidator
    {
        private const string ContractPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/ShaderEvidence/" +
            "LiZhiyanOverviewFinger/lizhiyan_overview_vfxbasev2_variants.json";
        private const string NativeContractPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/ShaderEvidence/" +
            "LiZhiyanOverviewFinger/lizhiyan_after_dof_native_abi.json";
        private const string Schema = "endfield.lizhiyan-overview-vfxbasev2-variants.v1";
        private const long ShaderPathId = -1430105248647086886L;

        [MenuItem("Endfield/Character Recovery Lab/Validate Li Zhiyan Overview Shader Evidence")]
        public static void ValidateMenu()
        {
            Dictionary<string, object> effect = L.Dict(
                ManifestMiniJson.Deserialize(File.ReadAllText(
                    L.ProjectAbsolute(
                        "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/" +
                        "lizhiyan_overview_finger_effect.json"), Encoding.UTF8)));
            Validate(effect);
            Debug.Log("Li Zhiyan shader evidence validated: 6 materials, 3 exact DXBC pairs, visible admission=false.");
        }

        public static void Validate(Dictionary<string, object> effect)
        {
            Dictionary<string, object> contract = L.Dict(
                ManifestMiniJson.Deserialize(File.ReadAllText(
                    L.ProjectAbsolute(ContractPath), Encoding.UTF8)));
            L.Require(L.Str(contract, "schema") == Schema &&
                L.Str(contract, "status") ==
                    "material_to_compiled_variant_closed_live_draw_and_descriptor_table_pending",
                "Li Zhiyan shader-evidence identity drifted");
            Dictionary<string, object> shader = L.Dict(contract["shader"]);
            L.Require(L.Str(shader, "name") == "HGRP/Effect/VFXBaseV2" &&
                L.Long(shader, "pathID") == ShaderPathId &&
                L.Str(shader, "pass") == "ForwardOnly" &&
                L.Long(shader, "gpuProgramID") == 59433,
                "Li Zhiyan shader identity drifted");
            Dictionary<string, object> summary = L.Dict(contract["summary"]);
            L.Require(L.Long(summary, "materials") == 6 &&
                L.Long(summary, "compiledKeywordSignatures") == 1360 &&
                L.Long(summary, "materialKeywordSignatures") == 3 &&
                L.Long(summary, "exactNonInstancedDxbcPairs") == 3 &&
                L.Long(summary, "verifiedInstancedDxbcPairs") == 3,
                "Li Zhiyan compiled-shader census drifted");
            Dictionary<string, object> scheduling = L.Dict(contract["renderScheduling"]);
            Dictionary<string, object> queueRange = L.Dict(scheduling["queueRange"]);
            Dictionary<string, object> attachments = L.Dict(scheduling["attachments"]);
            L.Require(L.Long(scheduling, "materialQueue") == 3700 &&
                L.Long(queueRange, "first") == 3660 &&
                L.Long(queueRange, "last") == 3740 &&
                L.Str(scheduling, "pass") == "ForwardOnly in Forward Transparent After DOF" &&
                L.Str(attachments, "color0") == "new sceneColor clone, store" &&
                L.Str(attachments, "color1") == "incoming sceneMV when valid, load/store" &&
                L.Str(attachments, "depth") == "incoming sceneDepth, read" &&
                L.List(scheduling["sourceArtifacts"]).Count == 3,
                "Li Zhiyan after-DOF scheduling contract drifted");

            Dictionary<string, object> selectedGates =
                L.Dict(contract["selectedMaterialGates"]);
            Dictionary<string, object> selectedGateValues =
                L.Dict(selectedGates["values"]);
            L.Require(!L.Bool(selectedGates, "vfxParams1Required") &&
                !L.Bool(selectedGates, "transformHistoryRequired") &&
                L.Float(selectedGateValues, "_RenderTransparentAfterDOF") == 1.0f &&
                L.Float(selectedGateValues, "_EnableTransparentMV") == 0.0f &&
                L.Float(selectedGateValues, "_IsSceneEffect") == 0.0f,
                "Li Zhiyan selected-material global/history gate drifted");

            var expectedMaterials = L.List(effect["materials"]).Cast<object>()
                .Select(L.Dict).ToDictionary(
                    row => L.Str(row, "name"),
                    row => new
                    {
                        PathId = L.Long(row, "pathID"),
                        Signature = Signature(L.List(row["validKeywords"]) .Cast<object>()
                            .Select(value => Convert.ToString(value))),
                        Floats = L.Dict(L.Dict(L.Dict(row["payload"])["m_SavedProperties"])["m_Floats"])
                    });
            L.Require(expectedMaterials.Count == 6, "Li Zhiyan source material census drifted");
            foreach (var expected in expectedMaterials.Values)
            {
                L.Require(L.Float(expected.Floats, "_RenderTransparentAfterDOF") == 1.0f &&
                    L.Float(expected.Floats, "_EnableTransparentMV") == 0.0f &&
                    L.Float(expected.Floats, "_IsSceneEffect") == 0.0f &&
                    L.Float(expected.Floats, "_IgnorePostExposure") == 1.0f &&
                    L.Float(expected.Floats, "_Responsive") == 1.0f &&
                    L.Float(expected.Floats, "_InParticle") == 1.0f,
                    "Li Zhiyan selected material escaped the fail-closed global/history gate");
            }

            var seen = new HashSet<string>(StringComparer.Ordinal);
            IList variants = L.List(contract["variants"]);
            L.Require(variants.Count == 3, "Li Zhiyan compiled-variant census drifted");
            foreach (object item in variants)
            {
                Dictionary<string, object> variant = L.Dict(item);
                string signature = Signature(L.List(variant["materialKeywords"]).Cast<object>()
                    .Select(value => Convert.ToString(value)));
                IList runtimeKeywords = L.List(variant["nonInstancedCompiledKeywords"]);
                L.Require(runtimeKeywords.Cast<object>().Any(value =>
                    Convert.ToString(value) == "HG_ENABLE_MV"),
                    "Li Zhiyan runtime variant lost HG_ENABLE_MV");
                foreach (object materialItem in L.List(variant["materials"]))
                {
                    Dictionary<string, object> material = L.Dict(materialItem);
                    string name = L.Str(material, "name");
                    L.Require(expectedMaterials.TryGetValue(name, out var expected) &&
                        expected.PathId == L.Long(material, "pathID") &&
                        expected.Signature == signature && seen.Add(name),
                        "Li Zhiyan material-to-DXBC mapping drifted: " + name);
                }
                Dictionary<string, object> stages = L.Dict(variant["stages"]);
                ValidateStage(L.Dict(stages["vertex"]), "vertex", false, signature);
                ValidateStage(L.Dict(stages["fragment"]), "fragment", true, signature);
            }
            L.Require(seen.SetEquals(expectedMaterials.Keys),
                "Li Zhiyan shader evidence does not cover all six materials");
            ValidateNativeAbi();
        }

        private static void ValidateNativeAbi()
        {
            Dictionary<string, object> native = L.Dict(
                ManifestMiniJson.Deserialize(File.ReadAllText(
                    L.ProjectAbsolute(NativeContractPath), Encoding.UTF8)));
            L.Require(L.Str(native, "schema") ==
                    "endfield.lizhiyan-after-dof-native-abi.v1" &&
                L.Str(native, "status") ==
                    "current_build_native_schedule_and_static_shader_abi_closed_live_draw_pending" &&
                L.List(native["methods"]).Count == 6 &&
                L.List(native["decisiveCalls"]).Count == 10,
                "Li Zhiyan native after-DOF contract identity drifted");
            var expectedMethods = new Dictionary<long, string>
            {
                { 287274, "319799A95260B1717084D16AA8C2E0CCAD668CEDF3E52E9465B99A31EC44A5E0" },
                { 287316, "D54DCF38AC17E6062573C476BF988FF8CBEE70E89F2B02FB341E5588DA3612CC" },
                { 287324, "D49C4DE691A7B65184532D8C9E46E1209F35AF2A76C0E23FA82B8E35593011CC" },
                { 288225, "76DC5D1B4730F4A5BB937F3776A776DE2A8E960B4BB4A47B983BA5F264555879" },
                { 288226, "BBA699B59C1081CDF6870E95B3B17469DD0D8791234E166D1D403D85786E6F42" },
                { 288241, "08E90A05982967C1F0AA45950FDF24F069FA6B639238EE3F6429FEF2DE697163" },
            };
            foreach (object item in L.List(native["methods"]))
            {
                Dictionary<string, object> method = L.Dict(item);
                long index = L.Long(method, "methodIndex");
                L.Require(expectedMethods.TryGetValue(index, out string bodyHash) &&
                    L.Str(method, "functionSha256") == bodyHash,
                    "Li Zhiyan native method body identity drifted: " + index);
            }
            Dictionary<string, object> boundary = L.Dict(native["nativeBoundary"]);
            Dictionary<string, object> decision = L.Dict(native["unityDecision"]);
            Dictionary<string, object> rendererList = L.Dict(native["rendererList"]);
            Dictionary<string, object> stateBlock = L.Dict(rendererList["stateBlock"]);
            Dictionary<string, object> consumers = L.Dict(native["rendererConsumers"]);
            L.Require(L.Str(boundary, "callbackConstantBufferPublication") == "not_present" &&
                L.Str(boundary, "callbackGlobalVectorAndTexturePublication") == "present" &&
                !L.Bool(boundary, "serializedBindingsAreD3D12RootParameters") &&
                L.Long(rendererList, "sortingCriteria") == 87 &&
                L.Str(rendererList, "sortingSemantic") ==
                    "CommonTransparent | OptimizeStateChanges | RendererPriority" &&
                L.Str(rendererList, "layerMask") ==
                    "RemoveWorldUILayer(camera.cullingMask)" &&
                !L.Bool(stateBlock, "hasValue") &&
                rendererList["overrideMaterial"] == null &&
                !L.Bool(rendererList, "excludeObjectMotionVectors") &&
                !L.Bool(consumers, "opaqueArgument") &&
                L.Str(consumers, "frameSettingsGate") == "TransparentObjects" &&
                L.Str(consumers, "survivorIdentity") ==
                    "runtime renderer-list and ECS handles pending" &&
                !L.Bool(decision, "visibleAdmission") &&
                !L.Bool(decision, "vfxParams1PublicationRequiredForSelectedMaterials") &&
                !L.Bool(decision, "transformHistoryRequiredForSelectedMaterials"),
                "Li Zhiyan native-to-Unity fail-closed decision drifted");
        }

        private static void ValidateStage(
            Dictionary<string, object> stage,
            string expectedStage,
            bool fragment,
            string materialSignature)
        {
            L.Require(L.Str(stage, "decodedProgramStage") == expectedStage &&
                L.Str(stage, "sourcePass") == "ForwardOnly",
                "Li Zhiyan DXBC stage/pass drifted");
            ValidateArtifact(L.Dict(stage["dxbc"]));
            ValidateArtifact(L.Dict(stage["metadata"]));
            Dictionary<string, object> assembly = L.Dict(stage["exactAssembly"]);
            ValidateArtifact(L.Dict(assembly["artifact"]));
            if (!fragment)
                return;
            ValidateArtifact(L.Dict(stage["ruriHlsl"]));
            Dictionary<string, object> registers = L.Dict(stage["registerSignature"]);
            var outputs = new HashSet<string>(
                L.List(registers["outputs"]).Cast<object>()
                    .Select(value => Convert.ToString(value)), StringComparer.Ordinal);
            L.Require(outputs.SetEquals(new[] { "SV_Target", "SV_Target_1" }) &&
                L.List(registers["resources"]).Count >= 2 &&
                L.List(registers["constantBuffers"]).Count >= 3,
                "Li Zhiyan fragment register/MRT signature drifted");
            Dictionary<string, object> lengths =
                L.Dict(assembly["constantBufferFloat4Lengths"]);
            long expectedMaterialLength = materialSignature == "" ? 21 :
                materialSignature == "_USE_SOFTBLEND" ? 22 : 28;
            L.Require(L.Str(assembly, "shaderModel") == "ps_5_0" &&
                L.Long(lengths, "0") == 28 && L.Long(lengths, "1") == 105 &&
                L.Long(lengths, "2") == 5 && L.Long(lengths, "3") == expectedMaterialLength,
                "Li Zhiyan exact DXBC constant-buffer ABI drifted");
            Dictionary<string, object> semantics =
                L.Dict(stage["staticResourceSemantics"]);
            int expectedPairs = materialSignature == "" ? 1 :
                materialSignature == "_USE_SOFTBLEND" ? 2 : 3;
            L.Require(L.Str(semantics, "status") ==
                    "variant_delta_and_coordinate_use_closed_live_descriptor_identity_pending" &&
                L.List(semantics["texturesAndSamplers"]).Count == expectedPairs &&
                L.List(assembly["textureSamplerPairs"]).Count == expectedPairs,
                "Li Zhiyan texture/sampler ABI drifted");
        }

        private static void ValidateArtifact(Dictionary<string, object> artifact)
        {
            const string projectPrefix = "unity_endfield_graph_shader_lab/";
            string relative = L.Str(artifact, "path").Replace('\\', '/');
            L.Require(relative.StartsWith(projectPrefix, StringComparison.Ordinal),
                "Li Zhiyan shader artifact escaped the Unity project");
            string path = L.ProjectAbsolute(relative.Substring(projectPrefix.Length));
            L.Require(File.Exists(path) && new FileInfo(path).Length == L.Long(artifact, "bytes") &&
                Sha256(path) == L.Str(artifact, "sha256").ToUpperInvariant(),
                "Li Zhiyan shader artifact drifted: " + path);
        }

        private static string Signature(IEnumerable<string> values)
        {
            return string.Join("+", values.Where(value => !string.IsNullOrEmpty(value))
                .OrderBy(value => value, StringComparer.Ordinal));
        }

        private static string Sha256(string path)
        {
            using (SHA256 hash = SHA256.Create())
            using (FileStream stream = File.OpenRead(path))
                return BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", string.Empty);
        }
    }
}

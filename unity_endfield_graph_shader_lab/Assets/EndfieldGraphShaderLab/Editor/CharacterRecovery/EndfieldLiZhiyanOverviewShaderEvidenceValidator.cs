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
            L.Require(L.Long(scheduling, "materialQueue") == 3700 &&
                L.Long(queueRange, "first") == 3660 &&
                L.Long(queueRange, "last") == 3740 &&
                L.Str(scheduling, "pass") == "ForwardOnly in Forward Transparent After DOF" &&
                L.List(scheduling["sourceArtifacts"]).Count == 3,
                "Li Zhiyan after-DOF scheduling contract drifted");

            var expectedMaterials = L.List(effect["materials"]).Cast<object>()
                .Select(L.Dict).ToDictionary(
                    row => L.Str(row, "name"),
                    row => new
                    {
                        PathId = L.Long(row, "pathID"),
                        Signature = Signature(L.List(row["validKeywords"]) .Cast<object>()
                            .Select(value => Convert.ToString(value)))
                    });
            L.Require(expectedMaterials.Count == 6, "Li Zhiyan source material census drifted");

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

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Tests Unity's public path/property hash functions against the hashes
    /// retained by AnimeStudio when original AnimationClip binding strings are
    /// absent. This is an evidence probe; it does not rewrite the clip.
    /// </summary>
    public static class EndfieldLiZhiyanOverviewAnimationHashProbe
    {
        private static readonly uint[] TargetPathHashes = {
            100733734u, 1182372393u, 1485209883u, 1600299880u, 1834271210u,
            1951396011u, 2367030625u, 2832407953u, 3206572003u, 524802392u,
        };

        private static readonly uint[] MaterialPropertyHashes = {
            109495689u, 2250381253u, 2292127880u, 2316997392u,
            377931145u, 646366601u, 914802057u,
        };

        private static readonly string[] ChildNames = {
            "S_fx_lzy_tiaodaifenwei_01 (4)",
            "S_fx_lzy_tiaodaifenwei_01 (5)",
            "S_fx_lzy_tiaodaifenwei_01 (6)",
            "S_fx_lzy_tiaodaifenwei_01 (7)",
        };

        [MenuItem("Endfield/Character Recovery Lab/Probe Li Zhiyan start_01 Animation Hashes")]
        public static void ProbeMenu()
        {
            const string root = "P_fxui_lizhiyan_overview_start_01";
            var pathCandidates = new HashSet<string>(StringComparer.Ordinal) { string.Empty, root };
            foreach (string child in ChildNames)
            {
                pathCandidates.Add(child);
                pathCandidates.Add(root + "/" + child);
                pathCandidates.Add("/" + child);
                pathCandidates.Add("/" + root + "/" + child);
            }

            string repo = Directory.GetParent(Application.dataPath).Parent.FullName;
            string candidateGameObjectRoot = Path.Combine(
                repo,
                "scratch/character_recovery/next_effect_candidates/prefabs/GameObject");
            var namePattern = new Regex("\\\"m_Name\\\"\\s*:\\s*\\\"([^\\\"]+)\\\"");
            foreach (string file in Directory.GetFiles(candidateGameObjectRoot, "*.json"))
            {
                Match name = namePattern.Match(File.ReadAllText(file));
                if (!name.Success)
                    continue;
                string candidate = name.Groups[1].Value;
                pathCandidates.Add(candidate);
                pathCandidates.Add(root + "/" + candidate);
            }

            Dictionary<uint, string> pathMatches = Match(
                TargetPathHashes,
                pathCandidates,
                value => unchecked((uint)Animator.StringToHash(value)));

            string materialRoot = Path.Combine(
                repo,
                "export_full/recovered/AnimeStudio-cli/StreamingAssets/json_by_type/Material");
            string[] materialFiles = {
                "M_fxui__lizhiyan_overview_09_p298ADB1F028DBD8D.json",
                "M_fxui__lizhiyan_overview_10_p2D8D3114D6B992A1.json",
                "M_fxui__lizhiyan_overview_11_pA01017DC01A5AC37.json",
            };
            var propertyCandidates = new HashSet<string>(StringComparer.Ordinal);
            var propertyPattern = new Regex("\\\"(_[^\\\"]+)\\\"\\s*:");
            foreach (string file in materialFiles)
            {
                string text = File.ReadAllText(Path.Combine(materialRoot, file));
                foreach (Match match in propertyPattern.Matches(text))
                {
                    string property = match.Groups[1].Value;
                    propertyCandidates.Add(property);
                    propertyCandidates.Add(property + "_ST");
                    propertyCandidates.Add(property + "_HDR");
                    propertyCandidates.Add(property + "_TexelSize");
                }
            }
            Dictionary<uint, string> propertyMatches = Match(
                MaterialPropertyHashes,
                ExpandMaterialBindingCandidates(propertyCandidates),
                value => unchecked((uint)Animator.StringToHash(value)));
            Dictionary<uint, string> shaderPropertyMatches = Match(
                MaterialPropertyHashes,
                propertyCandidates,
                value => unchecked((uint)Shader.PropertyToID(value)));
            Dictionary<uint, string> crc28PropertyMatches = MatchCrc28(
                MaterialPropertyHashes, propertyCandidates);

            var expectedProperties = new Dictionary<uint, string> {
                { 109495689u, "_MainTex_ST" },
                { 377931145u, "_MainTex_ST" },
                { 646366601u, "_MainTex_ST" },
                { 914802057u, "_MainTex_ST" },
                { 2250381253u, "_DisturbUIntensity1" },
                { 2292127880u, "_TintColorAlpha" },
                { 2316997392u, "_DissolveScheduleOffset" },
            };
            if (pathMatches.Count != TargetPathHashes.Length ||
                crc28PropertyMatches.Count != MaterialPropertyHashes.Length ||
                expectedProperties.Any(row => !crc28PropertyMatches.TryGetValue(
                    row.Key, out string value) || value != row.Value))
            {
                throw new InvalidOperationException(
                    "Li Zhiyan start_01 path or CRC28 property mapping is incomplete.");
            }

            Debug.Log(
                "[Endfield Li Zhiyan] start_01 hash probe: pathMatches=" +
                Format(pathMatches) + "; animatorPropertyMatches=" + Format(propertyMatches) +
                "; shaderPropertyMatches=" + Format(shaderPropertyMatches) +
                "; crc28PropertyMatches=" + Format(crc28PropertyMatches) +
                "; pathCandidates=" + pathCandidates.Count +
                "; propertyCandidates=" + propertyCandidates.Count + ".");
        }

        private static Dictionary<uint, string> MatchCrc28(
            IEnumerable<uint> targets,
            IEnumerable<string> candidates)
        {
            var result = new Dictionary<uint, string>();
            foreach (uint target in targets)
            {
                uint expected = target & 0x0FFFFFFFu;
                foreach (string candidate in candidates.OrderBy(value => value, StringComparer.Ordinal))
                {
                    if ((Crc32(candidate) & 0x0FFFFFFFu) != expected)
                        continue;
                    if (result.ContainsKey(target) && result[target] != candidate)
                        throw new InvalidOperationException("Ambiguous CRC28 material property mapping.");
                    result[target] = candidate;
                }
            }
            return result;
        }

        private static uint Crc32(string value)
        {
            uint crc = 0xFFFFFFFFu;
            foreach (byte item in System.Text.Encoding.UTF8.GetBytes(value))
            {
                crc ^= item;
                for (int bit = 0; bit < 8; bit++)
                    crc = (crc & 1u) != 0 ? (crc >> 1) ^ 0xEDB88320u : crc >> 1;
            }
            return crc ^ 0xFFFFFFFFu;
        }

        private static IEnumerable<string> ExpandMaterialBindingCandidates(
            IEnumerable<string> propertyNames)
        {
            foreach (string propertyName in propertyNames)
            {
                yield return propertyName;
                yield return "material." + propertyName;
                foreach (string channel in new[] { ".r", ".g", ".b", ".a", ".x", ".y", ".z", ".w" })
                    yield return "material." + propertyName + channel;
            }
        }

        private static Dictionary<uint, string> Match(
            IEnumerable<uint> targets,
            IEnumerable<string> candidates,
            Func<string, uint> hash)
        {
            var targetSet = new HashSet<uint>(targets);
            var result = new Dictionary<uint, string>();
            foreach (string candidate in candidates.OrderBy(value => value, StringComparer.Ordinal))
            {
                uint value = hash(candidate);
                if (targetSet.Contains(value) && !result.ContainsKey(value))
                    result.Add(value, candidate);
            }
            return result;
        }

        private static string Format(Dictionary<uint, string> values)
        {
            return values.Count == 0
                ? "none"
                : string.Join(",", values.OrderBy(row => row.Key)
                    .Select(row => row.Key + "=" + row.Value));
        }
    }
}

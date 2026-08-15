using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Verifies the source-backed property-bound render state of the Character
    /// Info VFXRefract Distortion pass. The converted ShaderLab's Zero/Off
    /// values are lossy parser defaults and must not replace the material
    /// properties named by the original parsed m_State.
    /// </summary>
    public static class EndfieldCharInfoVFXRefractStateVerifier
    {
        private const string ShaderAssetPath =
            "Assets/EndfieldGraphShaderLab/Shaders/Recovered/EndfieldZhuangfyVFXRefractMRT.shader";
        private const string MaterialAssetPath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/CharInfo/Effects/CharEffect/Materials/M_UI_charChoose_12.mat";
        private const string ShaderName =
            "Hidden/Endfield/Recovered/Zhuangfy/VFXRefractMRT";

        [MenuItem("Endfield/Character Recovery Lab/Verify CharInfo VFXRefract State")]
        public static void Verify()
        {
            string shaderSource = ReadShaderSource();
            Require(shaderSource.Contains("\"LightMode\"=\"Distortion\""),
                "VFXRefract pass lost its Distortion LightMode tag");
            Require(shaderSource.Contains(
                    "Blend 0 [_SrcBlend] [_DstBlend], Zero One"),
                "VFXRefract Target0 property-bound blend state drifted");
            Require(shaderSource.Contains(
                    "Blend 1 [_MVSrcColorBlend] [_MVDstColorBlend], One One"),
                "VFXRefract SceneMV property-bound blend state drifted");
            Require(shaderSource.Contains("ZTest [_ZTest]"),
                "VFXRefract property-bound ZTest state drifted");
            Require(shaderSource.Contains("ZWrite [_ZWrite]"),
                "VFXRefract property-bound ZWrite state drifted");
            Require(shaderSource.Contains("Cull [_CullMode]"),
                "VFXRefract property-bound cull state drifted");

            Material material = AssetDatabase.LoadAssetAtPath<Material>(MaterialAssetPath);
            Require(material != null, "CharInfo VFXRefract material is missing");
            Require(material.shader != null && material.shader.name == ShaderName,
                "CharInfo material shader identity drifted");
            Require(material.renderQueue == 3000,
                "CharInfo VFXRefract material queue drifted");
            Require(material.shaderKeywords.SequenceEqual(
                    new[] { "_USE_RBOFFSET" }, StringComparer.Ordinal),
                "CharInfo VFXRefract keyword gate drifted");
            Require(Mathf.Approximately(material.GetFloat("_CullMode"), 2f) &&
                    Mathf.Approximately(material.GetFloat("_ZTest"), 4f) &&
                    Mathf.Approximately(material.GetFloat("_ZWrite"), 0f) &&
                    Mathf.Approximately(material.GetFloat("_SrcBlend"), 5f) &&
                    Mathf.Approximately(material.GetFloat("_DstBlend"), 10f) &&
                    Mathf.Approximately(material.GetFloat("_MVSrcColorBlend"), 3f) &&
                    Mathf.Approximately(material.GetFloat("_MVDstColorBlend"), 6f),
                "serialized property-bound render state changed");

            Debug.Log(
                "[Endfield CharInfo] VFXRefract property-bound state verification " +
                "passed: Blend0=5/10, Blend1=3/6, ZTest=4, ZWrite=0, Cull=2");
        }

        private static string ReadShaderSource()
        {
            string projectRoot = Path.GetFullPath(Path.Combine(
                Application.dataPath, ".."));
            string sourcePath = Path.Combine(
                projectRoot,
                ShaderAssetPath.Replace('/', Path.DirectorySeparatorChar));
            Require(File.Exists(sourcePath), "VFXRefract shader source is missing");
            return File.ReadAllText(sourcePath);
        }

        private static void Require(bool condition, string message)
        {
            if (!condition)
                throw new InvalidOperationException(message);
        }
    }
}

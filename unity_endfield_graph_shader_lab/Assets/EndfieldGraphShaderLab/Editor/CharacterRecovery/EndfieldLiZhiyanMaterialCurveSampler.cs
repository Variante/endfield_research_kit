using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Evaluates the serialized classID 23 `material.*` curves from the shared
    /// Li Zhiyan start clip and mirrors Unity's SampleAnimation property-block
    /// result into the diagnostic material instance.  Unity's stock sampler
    /// writes these bindings to a renderer MaterialPropertyBlock (and leaves
    /// the cloned Material unchanged); the diagnostic pipeline needs the same
    /// values on its cloned material because its recovered shader consumes the
    /// material instance directly in the custom render route.  This helper is
    /// editor-only, source-path bound, and never changes the generated asset or
    /// the normal viewer prefab.
    /// </summary>
    internal sealed class EndfieldLiZhiyanMaterialCurveSampler
    {
        private const string MaterialPrefix = "material.";
        private const string MainTexStPrefix = "_MainTex_ST.";

        private readonly GameObject root;
        private readonly Binding[] bindings;
        private readonly MaterialCurveValue[] values;

        private EndfieldLiZhiyanMaterialCurveSampler(
            GameObject root,
            Binding[] bindings)
        {
            this.root = root;
            this.bindings = bindings;
            values = new MaterialCurveValue[bindings.Length];
        }

        public int BindingCount => bindings.Length;

        public IReadOnlyList<MaterialCurveValue> LastValues => values;

        public static EndfieldLiZhiyanMaterialCurveSampler Build(
            GameObject root,
            AnimationClip clip)
        {
            Require(root != null, "Li Zhiyan material curve root is missing");
            Require(clip != null, "Li Zhiyan material curve clip is missing");

            var rows = new List<Binding>();
            foreach (EditorCurveBinding binding in AnimationUtility.GetCurveBindings(clip))
            {
                if (binding.type != typeof(MeshRenderer) ||
                    !binding.propertyName.StartsWith(MaterialPrefix,
                        StringComparison.Ordinal))
                    continue;

                Transform target = string.IsNullOrEmpty(binding.path)
                    ? root.transform
                    : root.transform.Find(binding.path);
                if (target == null)
                    continue; // shared clip binding for another effect root

                MeshRenderer renderer = target.GetComponent<MeshRenderer>();
                Require(renderer != null,
                    "Material curve target is not a MeshRenderer: " + binding.path);
                Material[] materials = renderer.sharedMaterials;
                Require(materials != null && materials.Length == 1 && materials[0] != null,
                    "Li Zhiyan material curve target must have exactly one material: " +
                    binding.path);

                string property = binding.propertyName.Substring(MaterialPrefix.Length);
                ValidateProperty(materials[0], property, binding.path);
                AnimationCurve curve = AnimationUtility.GetEditorCurve(clip, binding);
                Require(curve != null,
                    "Li Zhiyan material curve payload is missing: " + binding.path +
                    "/" + binding.propertyName);
                rows.Add(new Binding(binding.path, property, renderer, materials[0], curve));
            }

            rows.Sort((left, right) =>
            {
                int path = string.CompareOrdinal(left.path, right.path);
                return path != 0 ? path : string.CompareOrdinal(left.property, right.property);
            });
            Require(rows.Count > 0,
                "No source-bound material curves resolve on " + root.name);
            return new EndfieldLiZhiyanMaterialCurveSampler(root, rows.ToArray());
        }

        public MaterialCurveSample Apply(float sampleTime)
        {
            Require(!float.IsNaN(sampleTime) && !float.IsInfinity(sampleTime) &&
                sampleTime >= 0f, "Li Zhiyan material curve sample time is invalid");

            // Build vectors from the cloned material defaults, then overwrite
            // every source-authored component before publishing one full
            // vector.  This avoids the zero-default behavior of an empty MPB.
            var vectorValues = new Dictionary<Material, Vector4>();
            var blockValues = new Dictionary<Material, MaterialPropertyBlock>();
            for (int index = 0; index < bindings.Length; index++)
            {
                Binding binding = bindings[index];
                float value = binding.curve.Evaluate(sampleTime);
                values[index] = new MaterialCurveValue(
                    binding.path, binding.property, value, binding.material.GetInstanceID());
                Material material = binding.material;
                if (!blockValues.TryGetValue(material, out MaterialPropertyBlock block))
                {
                    block = new MaterialPropertyBlock();
                    binding.renderer.GetPropertyBlock(block, 0);
                    blockValues.Add(material, block);
                }

                if (binding.property.StartsWith(MainTexStPrefix,
                    StringComparison.Ordinal))
                {
                    if (!vectorValues.TryGetValue(material, out Vector4 vector))
                        vector = material.GetVector("_MainTex_ST");
                    int component = "xyzw".IndexOf(
                        binding.property[binding.property.Length - 1]);
                    Require(component >= 0,
                        "Unknown _MainTex_ST component: " + binding.property);
                    vector[component] = value;
                    vectorValues[material] = vector;
                    block.SetVector("_MainTex_ST", vector);
                }
                else
                {
                    material.SetFloat(binding.property, value);
                    block.SetFloat(binding.property, value);
                }
            }

            foreach (KeyValuePair<Material, Vector4> row in vectorValues)
            {
                row.Key.SetVector("_MainTex_ST", row.Value);
                Binding owner = bindings.First(value => value.material == row.Key);
                owner.renderer.SetPropertyBlock(blockValues[row.Key], 0);
            }
            foreach (KeyValuePair<Material, MaterialPropertyBlock> row in blockValues)
            {
                if (vectorValues.ContainsKey(row.Key))
                    continue;
                Binding owner = bindings.First(value => value.material == row.Key);
                owner.renderer.SetPropertyBlock(row.Value, 0);
            }

            string stateHash = StateHash(values);
            return new MaterialCurveSample(
                bindings.Length, values.Length, stateHash,
                values.ToArray());
        }

        private static void ValidateProperty(
            Material material, string property, string path)
        {
            string shaderProperty = property.StartsWith(MainTexStPrefix,
                StringComparison.Ordinal) ? "_MainTex_ST" : property;
            Require(material.HasProperty(shaderProperty),
                "Source material curve property is absent from diagnostic shader: " +
                path + "/" + property);
        }

        private static string StateHash(MaterialCurveValue[] rows)
        {
            var text = new StringBuilder();
            foreach (MaterialCurveValue row in rows)
                text.Append(row.path).Append('|').Append(row.property).Append('|')
                    .Append(row.value.ToString("R", CultureInfo.InvariantCulture)).Append('\n');
            using (SHA256 sha = SHA256.Create())
            {
                byte[] bytes = sha.ComputeHash(Encoding.UTF8.GetBytes(text.ToString()));
                return BitConverter.ToString(bytes).Replace("-", string.Empty)
                    .ToUpperInvariant();
            }
        }

        private static void Require(bool condition, string message)
        {
            if (!condition)
                throw new InvalidOperationException(message);
        }

        private sealed class Binding
        {
            internal readonly string path;
            internal readonly string property;
            internal readonly MeshRenderer renderer;
            internal readonly Material material;
            internal readonly AnimationCurve curve;

            internal Binding(
                string path,
                string property,
                MeshRenderer renderer,
                Material material,
                AnimationCurve curve)
            {
                this.path = path;
                this.property = property;
                this.renderer = renderer;
                this.material = material;
                this.curve = curve;
            }
        }
    }

    [Serializable]
    internal sealed class MaterialCurveValue
    {
        public string path;
        public string property;
        public float value;
        public int materialInstanceId;

        internal MaterialCurveValue(
            string path, string property, float value, int materialInstanceId)
        {
            this.path = path;
            this.property = property;
            this.value = value;
            this.materialInstanceId = materialInstanceId;
        }
    }

    [Serializable]
    internal sealed class MaterialCurveSample
    {
        public int sourceBindingCount;
        public int appliedBindingCount;
        public string stateSha256;
        public MaterialCurveValue[] values;

        internal MaterialCurveSample(
            int sourceBindingCount,
            int appliedBindingCount,
            string stateSha256,
            MaterialCurveValue[] values)
        {
            this.sourceBindingCount = sourceBindingCount;
            this.appliedBindingCount = appliedBindingCount;
            this.stateSha256 = stateSha256;
            this.values = values;
        }

        internal static MaterialCurveSample Inactive(int sourceBindingCount)
        {
            return new MaterialCurveSample(
                sourceBindingCount, 0, "inactive", Array.Empty<MaterialCurveValue>());
        }
    }
}

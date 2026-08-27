using System;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Opt-in binding for source-identified Endminf overview rock and hand-
    /// crystal renderers whose retained prefabs remain fail-closed. Direct
    /// references are published by the editor validator; runtime path/name
    /// searches are deliberately forbidden.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class EndfieldEndminfLitEffectCompatibilityBinding : MonoBehaviour
    {
        public const string EnvironmentVariable =
            "ENDFIELD_ENDMINF_LITEFFECT_VISUAL_COMPAT";
        public const string ContractSchema =
            "endfield.endminf-liteffect-runtime-binding.v1";
        private const string ExactM27EnvironmentVariable =
            "ENDFIELD_RECOVERED_ENDMINF_M27_HGBUFFER";
        private const long M27RendererPathId = 59284134265994738L;
        internal const int ExactM27Layer = 31;

        [Serializable]
        public sealed class Row
        {
            public long particleRendererPathId;
            public long materialPathId;
            public long meshPathId;
            public ParticleSystemRenderer renderer;
            public Material material;
            public Mesh mesh;
        }

        public string contractSchema = ContractSchema;
        public Row[] rows = Array.Empty<Row>();

        private void OnEnable()
        {
            bool compatibility = Requested;
            bool exactM27 = string.Equals(
                Environment.GetEnvironmentVariable(
                    ExactM27EnvironmentVariable),
                "1",
                StringComparison.Ordinal);
            if (!compatibility && !exactM27)
                return;

            foreach (Row row in rows)
            {
                if (row == null || row.renderer == null ||
                    row.material == null || row.mesh == null)
                {
                    Debug.LogError(
                        "Recovered Endminf LitEffect compatibility binding " +
                        "failed closed because a direct reference is missing.", this);
                    continue;
                }

                bool isM27 = row.particleRendererPathId == M27RendererPathId;
                if (!isM27 && !compatibility)
                    continue;

                row.renderer.renderMode = ParticleSystemRenderMode.Mesh;
                row.renderer.SetMeshes(new[] { row.mesh }, 1);
                row.renderer.sharedMaterials = new[] { row.material };
                if (exactM27 && isM27)
                    row.renderer.gameObject.layer = ExactM27Layer;
                row.renderer.enabled = true;
            }
        }

        public static bool Requested
        {
            get
            {
                string value = Environment.GetEnvironmentVariable(EnvironmentVariable);
                return string.Equals(value, "1", StringComparison.Ordinal) ||
                    string.Equals(value, "true", StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(value, "on", StringComparison.OrdinalIgnoreCase);
            }
        }
    }
}

using System;
using System.Collections.Generic;
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
        public const string LiveHGBufferEnvironmentVariable =
            "ENDFIELD_RECOVERED_ENDMINF_LITEFFECT_HGBUFFER";
        public const string ContractSchema =
            "endfield.endminf-liteffect-runtime-binding.v1";
        private const string ExactM27EnvironmentVariable =
            "ENDFIELD_RECOVERED_ENDMINF_M27_HGBUFFER";
        private const string GenerativeExactM27EnvironmentVariable =
            "ENDFIELD_RECOVERED_ENDMINF_M27_GENERATIVE_EXACT_DXBC";
        private const long M27RendererPathId = 59284134265994738L;
        private const long Material01PathId = 0x5A6341E8A834E421L;
        private const long Material38PathId =
            unchecked((long)0xAFCE491DD7BC5724UL);
        private const long Material27PathId =
            unchecked((long)0xA531A88850690EB8UL);
        private const long RockMeshPathId =
            unchecked((long)0x8EC9950E5461C8D9UL);
        private const string Overview01 = "P_fxui_endminm003_overview_01";
        private const string Overview02 = "P_fxui_endminm003_overview_02";
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
            bool liveHGBuffer = IsEnabled(
                Environment.GetEnvironmentVariable(
                    LiveHGBufferEnvironmentVariable));
            bool generativeExactM27 = IsEnabled(
                Environment.GetEnvironmentVariable(
                    GenerativeExactM27EnvironmentVariable));
            if (!compatibility && !exactM27 && !liveHGBuffer &&
                !generativeExactM27)
                return;

            if (!TryValidateForRecoveryAudit(out string validationFailure))
            {
                Debug.LogError(
                    "Recovered Endminf LitEffect binding failed closed: " +
                    validationFailure,
                    this);
                return;
            }

            foreach (Row row in rows)
            {
                bool isM27 = row.particleRendererPathId == M27RendererPathId;
                if (!isM27 && !compatibility && !liveHGBuffer)
                    continue;

                row.renderer.renderMode = ParticleSystemRenderMode.Mesh;
                row.renderer.SetMeshes(new[] { row.mesh }, 1);
                row.renderer.sharedMaterials = new[] { row.material };
                // The live HGBuffer route remains a non-presented diagnostic
                // until the original deferred output proves non-empty source
                // content. Keep the ordinary source renderer visible while
                // that proof is incomplete; otherwise a black diagnostic
                // resolve replaces an already useful compatibility result.
                if (exactM27 && isM27)
                    row.renderer.gameObject.layer = ExactM27Layer;
                row.renderer.enabled = true;
            }
        }

        /// <summary>
        /// Rejoins every serialized compatibility row to the exact v2 source
        /// marker before runtime visibility can change. This deliberately
        /// validates identities and direct references rather than trusting the
        /// serialized Row integers on their own.
        /// </summary>
        public bool TryValidateForRecoveryAudit(out string reason)
        {
            reason = string.Empty;
            if (!string.Equals(
                    contractSchema,
                    ContractSchema,
                    StringComparison.Ordinal))
            {
                reason = "binding schema is absent or stale";
                return false;
            }

            EndfieldRecoveredParticleEffectSource marker =
                GetComponent<EndfieldRecoveredParticleEffectSource>();
            if (marker == null || !string.Equals(
                    marker.contractSchema,
                    EndfieldRecoveredCharEffectSpawner.EndminfOverviewContractSchema,
                    StringComparison.Ordinal))
            {
                reason = "v2 source marker is missing or stale";
                return false;
            }
            if (!EndfieldRecoveredCharEffectSpawner
                    .TryValidateEndminfV2MarkerForRecoveryAudit(
                        gameObject,
                        out string markerFailure))
            {
                reason = "v2 source marker is invalid: " + markerFailure;
                return false;
            }

            int expectedRowCount;
            if (string.Equals(marker.effectRoot, Overview01, StringComparison.Ordinal))
                expectedRowCount = 10;
            else if (string.Equals(
                         marker.effectRoot,
                         Overview02,
                         StringComparison.Ordinal))
                expectedRowCount = 1;
            else
            {
                reason = "binding is attached to an unsupported effect root";
                return false;
            }
            if (rows == null || rows.Length != expectedRowCount ||
                marker.particleNodes == null)
            {
                reason = "binding row census drifted";
                return false;
            }

            var sourceByRendererPathId =
                new Dictionary<long, EndfieldRecoveredParticleNodeSource>();
            foreach (EndfieldRecoveredParticleNodeSource node in marker.particleNodes)
            {
                if (node == null || node.particleRendererPathId == 0 ||
                    !sourceByRendererPathId.TryAdd(
                        node.particleRendererPathId,
                        node))
                {
                    reason = "source renderer identities are null or ambiguous";
                    return false;
                }
            }

            var admittedRendererIds = new HashSet<long>();
            var admittedRenderers = new HashSet<ParticleSystemRenderer>();
            int material01Count = 0;
            int material38Count = 0;
            int material27Count = 0;
            foreach (Row row in rows)
            {
                if (row == null || row.particleRendererPathId == 0 ||
                    row.renderer == null || row.material == null || row.mesh == null ||
                    !admittedRendererIds.Add(row.particleRendererPathId) ||
                    !admittedRenderers.Add(row.renderer) ||
                    !sourceByRendererPathId.TryGetValue(
                        row.particleRendererPathId,
                        out EndfieldRecoveredParticleNodeSource node) ||
                    node.generatedRenderer != row.renderer ||
                    node.generatedParticleSystem == null ||
                    node.generatedParticleSystem.GetComponent<ParticleSystemRenderer>() !=
                        row.renderer ||
                    !node.sourceRendererEnabled ||
                    !node.rendererFailClosedForUnrecoveredShader ||
                    row.renderer.enabled ||
                    row.renderer.sharedMaterials == null ||
                    row.renderer.sharedMaterials.Length != 0 ||
                    node.materialPathIds == null ||
                    node.materialPathIds.Length != 1 ||
                    node.materialPathIds[0] != row.materialPathId ||
                    node.meshPathIds == null || node.meshPathIds.Length != 1 ||
                    node.meshPathIds[0] != row.meshPathId ||
                    row.meshPathId != RockMeshPathId ||
                    node.resolvedSourceMaterials == null ||
                    node.resolvedSourceMaterials.Length != 1 ||
                    node.resolvedSourceMaterials[0] != row.material ||
                    node.resolvedSourceMeshes == null ||
                    node.resolvedSourceMeshes.Length != 1 ||
                    node.resolvedSourceMeshes[0] != row.mesh)
                {
                    reason = "a row does not match its exact source owner/references";
                    return false;
                }

                if (row.materialPathId == Material01PathId) material01Count++;
                else if (row.materialPathId == Material38PathId) material38Count++;
                else if (row.materialPathId == Material27PathId) material27Count++;
                else
                {
                    reason = "a row contains an unsupported material identity";
                    return false;
                }
            }

            if (string.Equals(marker.effectRoot, Overview01, StringComparison.Ordinal))
            {
                if (material01Count != 7 || material38Count != 3 ||
                    material27Count != 0 || admittedRendererIds.Contains(M27RendererPathId))
                {
                    reason = "overview_01 material/renderer census drifted";
                    return false;
                }
            }
            else if (material01Count != 0 || material38Count != 0 ||
                     material27Count != 1 ||
                     !admittedRendererIds.Contains(M27RendererPathId))
            {
                reason = "overview_02 M27 owner census drifted";
                return false;
            }
            return true;
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

        private static bool IsEnabled(string value)
        {
            return string.Equals(value, "1", StringComparison.Ordinal) ||
                string.Equals(value, "true", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(value, "yes", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(value, "on", StringComparison.OrdinalIgnoreCase);
        }
    }
}

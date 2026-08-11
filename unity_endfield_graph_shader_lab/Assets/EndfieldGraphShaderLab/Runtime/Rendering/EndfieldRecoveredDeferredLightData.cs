using System;
using Unity.Collections;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Default-off same-frame transport for the selected original deferred
    /// resolver's b31 reads. This closes only the explicitly audited
    /// SphereOutside/isolated-CharInfo consumer path and does not activate the
    /// original pass.
    /// </summary>
    public sealed class EndfieldRecoveredDeferredLightData : IDisposable
    {
        public const string Selector =
            "ENDFIELD_RECOVERED_DEFERRED_LIGHT_DATA";

        private static readonly int ConstantsId =
            Shader.PropertyToID("_LightDataBuffer");
        private static readonly int ExactDxbcBridgeConstantsId =
            Shader.PropertyToID("EndfieldCB4");
        private static readonly int ReadyId = Shader.PropertyToID(
            "_EndfieldRecoveredDeferredLightDataReady");
        private static readonly int Pass0SubsetReadyId = Shader.PropertyToID(
            "_EndfieldRecoveredDeferredPass0InputSubsetReady");

        private readonly Vector4[] vectors = new Vector4[
            EndfieldRecoveredDeferredLightDataContract.VectorCount];
        private ComputeBuffer buffer;
        private bool disposed;

        public static bool IsRequested
        {
            get
            {
                string value = Environment.GetEnvironmentVariable(Selector);
                return string.Equals(value, "1", StringComparison.Ordinal) ||
                    string.Equals(value, "true", StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(value, "on", StringComparison.OrdinalIgnoreCase) ||
                    EndfieldRecoveredDeferredResolverBindingPolicy.IsRequested;
            }
        }

        public bool PrepareAndPublish(
            Camera camera,
            CullingResults cullingResults,
            Light directionalLight,
            EndfieldHGOperatorLightRig rig,
            bool canonicalFrameResourcesReady,
            bool deferredTransformsReady,
            CommandBuffer commandBuffer,
            out string failure)
        {
            failure = null;
            if (disposed)
            {
                throw new ObjectDisposedException(
                    nameof(EndfieldRecoveredDeferredLightData));
            }
            if (commandBuffer == null)
                throw new ArgumentNullException(nameof(commandBuffer));

            ResetPublication(commandBuffer);
            if (!IsRequested)
            {
                failure = "explicit deferred LightData selector is disabled";
                return false;
            }
            if (!canonicalFrameResourcesReady)
            {
                failure =
                    "canonical binning/reflection/VisibilitySHConstData prerequisites are not ready";
                return false;
            }
            if (!deferredTransformsReady)
            {
                failure = "selected deferred TransformVariables prerequisite is not ready";
                return false;
            }
            if (camera == null)
            {
                failure = "physical camera is required";
                return false;
            }
            if (!MatchesRecoveredDirectionalFixture(
                    cullingResults,
                    directionalLight,
                    out VisibleLight visibleDirectional,
                    out failure))
            {
                return false;
            }
            if (rig == null ||
                !TryValidateSelectedRigSubset(
                    rig,
                    out int punctualLightCount,
                    out failure))
            {
                if (rig == null)
                    failure = "source-backed operator-light rig is required";
                return false;
            }

            // The selected SphereOutside program reads record[5].w and then
            // record[3].z for these rows. CharacterOnly is one, so it exits
            // before any shadow-slot word is consumed. A same-frame shadow
            // atlas is therefore not a b31 publication prerequisite.

            Vector4 forward4 = visibleDirectional.localToWorldMatrix.GetColumn(2);
            if (!EndfieldRecoveredDeferredLightDataContract
                    .TryBuildSelectedConsumerSubset(
                        new Vector3(forward4.x, forward4.y, forward4.z),
                        visibleDirectional.finalColor,
                        punctualLightCount,
                        vectors,
                        out failure))
            {
                return false;
            }

            try
            {
                EnsureBuffer();
                buffer.SetData(vectors);
                commandBuffer.SetGlobalConstantBuffer(
                    buffer,
                    ConstantsId,
                    0,
                    EndfieldRecoveredDeferredLightDataContract.SizeBytes);
                commandBuffer.SetGlobalConstantBuffer(
                    buffer,
                    ExactDxbcBridgeConstantsId,
                    0,
                    EndfieldRecoveredDeferredLightDataContract.SizeBytes);
                commandBuffer.SetGlobalFloat(ReadyId, 1.0f);
                // The combined subset gate is raised only after the matching
                // b34 ShadowData/atlas publication succeeds later this frame.
                return true;
            }
            catch (Exception exception)
            {
                failure = "deferred LightData publication failed: " +
                    exception.Message;
                ResetPublication(commandBuffer);
                return false;
            }
        }

        public void ResetPublication(CommandBuffer commandBuffer)
        {
            if (commandBuffer == null)
                throw new ArgumentNullException(nameof(commandBuffer));
            commandBuffer.SetGlobalFloat(ReadyId, 0.0f);
            commandBuffer.SetGlobalFloat(Pass0SubsetReadyId, 0.0f);
        }

        public void Dispose()
        {
            if (disposed)
                return;
            disposed = true;
            if (buffer != null)
            {
                buffer.Release();
                buffer = null;
            }
            Shader.SetGlobalFloat(ReadyId, 0.0f);
            Shader.SetGlobalFloat(Pass0SubsetReadyId, 0.0f);
        }

        private static bool MatchesRecoveredDirectionalFixture(
            CullingResults cullingResults,
            Light directionalLight,
            out VisibleLight visibleDirectional,
            out string failure)
        {
            visibleDirectional = default;
            failure = null;
            if (directionalLight == null ||
                directionalLight.type != LightType.Directional ||
                !directionalLight.enabled ||
                !directionalLight.gameObject.activeInHierarchy)
            {
                failure =
                    "the source-backed sceneMainLight is not an active directional light";
                return false;
            }
            if (Mathf.Abs(directionalLight.intensity - 1.0f) > 1.0e-6f ||
                !Approximately(directionalLight.color, Color.white) ||
                !directionalLight.useColorTemperature ||
                Mathf.Abs(directionalLight.colorTemperature - 7000.0f) > 1.0e-3f)
            {
                failure =
                    "sceneMainLight no longer matches the neutral carrier for CharInfo_Env direct lighting";
                return false;
            }

            NativeArray<VisibleLight> visibleLights = cullingResults.visibleLights;
            int matchCount = 0;
            for (int index = 0; index < visibleLights.Length; index++)
            {
                VisibleLight candidate = visibleLights[index];
                if (candidate.light != directionalLight)
                    continue;
                visibleDirectional = candidate;
                matchCount++;
            }
            if (matchCount != 1)
            {
                failure =
                    "sceneMainLight must appear exactly once in CullingResults.visibleLights";
                return false;
            }
            return true;
        }

        private static bool TryValidateSelectedRigSubset(
            EndfieldHGOperatorLightRig rig,
            out int punctualLightCount,
            out string failure)
        {
            punctualLightCount = 0;
            failure = null;
            if (!rig.sourceBackedClusteredNprLightLoop ||
                !rig.sourceBackedLightBinningMembership)
            {
                failure =
                    "clustered NPR and canonical binning must both be enabled";
                return false;
            }
            if (rig.actorRoot == null)
            {
                failure = "no recovered actor root is bound";
                return false;
            }

            int expectedLightCount;
            if (string.Equals(
                    rig.actorRoot.name,
                    "Wulfa",
                    StringComparison.OrdinalIgnoreCase))
            {
                expectedLightCount = 8;
            }
            else if (string.Equals(
                         rig.actorRoot.name,
                         "Zhuangfy",
                         StringComparison.OrdinalIgnoreCase))
            {
                expectedLightCount = 6;
            }
            else
            {
                failure =
                    "actor identity '" + rig.actorRoot.name +
                    "' is outside the selected Wulfa/Zhuangfy deferred fixture";
                return false;
            }
            if (rig.lights == null ||
                rig.lights.Length != expectedLightCount)
            {
                failure =
                    "selected deferred source list must contain exactly " +
                    expectedLightCount + " rows";
                return false;
            }

            int shadowedRowCount = 0;
            for (int sourceIndex = 0;
                 sourceIndex < rig.lights.Length;
                 sourceIndex++)
            {
                EndfieldHGOperatorLightData row = rig.lights[sourceIndex];
                if (!row.enabled || !row.characterOnly ||
                    row.enableObbCullingBox || row.hasCookie ||
                    row.flickerEnabled || row.useColorTemperature ||
                    row.useCullingDistance ||
                    row.useShadowCullingMatrixOverride)
                {
                    failure =
                        "light row " + sourceIndex +
                        " no longer matches the selected CharacterOnly/" +
                        "no-OBB/no-cookie/no-flicker/no-culling contract";
                    return false;
                }
                if (row.shadowType == 0)
                    continue;
                shadowedRowCount++;
                if (sourceIndex != 4 ||
                    !string.Equals(
                        row.sourceName,
                        "RimLight_2 (5)",
                        StringComparison.Ordinal) ||
                    row.shadowType != 2)
                {
                    failure =
                        "unexpected shadowed light row " + sourceIndex +
                        " (" + row.sourceName + ")";
                    return false;
                }
            }
            if (shadowedRowCount != 1)
            {
                failure =
                    "expected exactly one isolated shadowed overview row, found " +
                    shadowedRowCount;
                return false;
            }

            punctualLightCount = expectedLightCount;
            return true;
        }

        private static bool Approximately(Color left, Color right)
        {
            return Mathf.Abs(left.r - right.r) <= 1.0e-6f &&
                Mathf.Abs(left.g - right.g) <= 1.0e-6f &&
                Mathf.Abs(left.b - right.b) <= 1.0e-6f &&
                Mathf.Abs(left.a - right.a) <= 1.0e-6f;
        }

        private void EnsureBuffer()
        {
            if (buffer != null)
                return;
            buffer = new ComputeBuffer(
                EndfieldRecoveredDeferredLightDataContract.VectorCount,
                sizeof(float) * 4,
                ComputeBufferType.Constant)
            {
                name = "Recovered selected deferred _LightDataBuffer b31"
            };
        }
    }
}

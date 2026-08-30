using System;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Same-frame owner for the complete Endminf retail b31 payload. This is a
    /// distinct scope from the older SphereOutside-selected zero subset.
    /// </summary>
    internal sealed class EndfieldRecoveredEndminfFullDeferredLightData : IDisposable
    {
        internal const string Selector =
            "ENDFIELD_RECOVERED_ENDMINF_FULL_LIGHT_DATA";
        private static readonly int ConstantsId = Shader.PropertyToID("_LightDataBuffer");
        private static readonly int ExactDxbcBridgeConstantsId =
            Shader.PropertyToID("EndfieldCB4");
        private static readonly int ReadyId = Shader.PropertyToID(
            "_EndfieldRecoveredEndminfFullLightDataReady");

        private readonly Vector4[] vectors = new Vector4[
            EndfieldRecoveredEndminfFullLightDataContract.VectorCount];
        private readonly EndfieldHGPreparedOperatorLight[] preparedLights =
            new EndfieldHGPreparedOperatorLight[
                EndfieldRecoveredEndminfFullLightDataContract.EndminfPunctualLightCount];
        private readonly EndfieldHGPreparedShadowAssignment[] shadowAssignments =
            new EndfieldHGPreparedShadowAssignment[2];
        private ComputeBuffer buffer;
        private Camera publicationCamera;
        private uint publicationPreparedSerial;
        private bool publicationReady;
        private bool disposed;

        internal static bool IsRequested
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

        internal bool PrepareAndPublish(
            Camera camera,
            CullingResults cullingResults,
            Light directionalLight,
            EndfieldHGRPCharacterLightingVolume characterVolume,
            bool currentCameraExposureReady,
            float exposureAdaptation,
            EndfieldHGOperatorLightRig rig,
            EndfieldRecoveredPunctualShadowProducer shadowProducer,
            bool canonicalFrameResourcesReady,
            bool deferredTransformsReady,
            bool punctualShadowReady,
            CommandBuffer commandBuffer,
            out uint publishedPreparedSerial,
            out string failure)
        {
            publishedPreparedSerial = 0;
            failure = string.Empty;
            if (disposed)
                throw new ObjectDisposedException(nameof(EndfieldRecoveredEndminfFullDeferredLightData));
            if (commandBuffer == null)
                throw new ArgumentNullException(nameof(commandBuffer));

            ResetPublication(commandBuffer);
            if (!IsRequested)
            {
                failure = "explicit deferred LightData selector is disabled";
                return false;
            }
            if (!canonicalFrameResourcesReady || !deferredTransformsReady)
            {
                failure = "canonical frame and transform prerequisites are not ready";
                return false;
            }
            if (!punctualShadowReady || shadowProducer == null)
            {
                failure = "same-frame punctual-shadow publication is required";
                return false;
            }
            if (camera == null || rig == null || rig.actorRoot == null ||
                !string.Equals(
                    rig.actorRoot.name,
                    "Endminf",
                    StringComparison.OrdinalIgnoreCase))
            {
                failure = "the full retail LightData scope is limited to the Endminf fixture";
                return false;
            }
            if (characterVolume == null ||
                !characterVolume.useRecoveredSourceMainLightDescriptor)
            {
                failure = "the source-backed CharInfo_Env directional descriptor is required";
                return false;
            }
            if (!EndfieldRecoveredDeferredLightData.MatchesRecoveredDirectionalFixture(
                    cullingResults,
                    directionalLight,
                    out VisibleLight visibleDirectional,
                    out failure))
            {
                return false;
            }
            if (!rig.TryCopyPreparedSourceBackedFrame(
                    camera,
                    preparedLights,
                    out int preparedLightCount,
                    out uint preparedSerial,
                    out failure))
            {
                return false;
            }
            if (!shadowProducer.TryCopyCurrentLightShadowAssignments(
                    camera,
                    preparedSerial,
                    shadowAssignments,
                    out int shadowAssignmentCount,
                    out failure))
            {
                return false;
            }

            if (!currentCameraExposureReady)
            {
                failure = "the current camera has no provenance-valid exposure publication";
                return false;
            }
            if (float.IsNaN(exposureAdaptation) ||
                float.IsInfinity(exposureAdaptation) ||
                exposureAdaptation <= 0.0f)
            {
                failure = "the recovered camera exposure adaptation is invalid";
                return false;
            }
            float sourceIntensity = characterVolume.sourceDirectIntensityDividePi;
            float expectedIntensity =
                EndfieldRecoveredDeferredLightDataContract.SourceDirectIntensityDividePi;
            if (Mathf.Abs(sourceIntensity - expectedIntensity) > 1.0e-6f)
            {
                failure = "the CharInfo_Env direct intensity no longer matches source data";
                return false;
            }
            if (!EndfieldRecoveredEndminfFullLightDataContract
                    .MatchesRecoveredSourceDirectColor(
                        characterVolume.sourceDirectColor))
            {
                failure = "the CharInfo_Env direct color no longer matches exact white RGBA source data";
                return false;
            }

            Vector4 forward4 = visibleDirectional.localToWorldMatrix.GetColumn(2);
            if (!EndfieldRecoveredEndminfFullLightDataContract.TryBuild(
                    new Vector3(forward4.x, forward4.y, forward4.z),
                    visibleDirectional.finalColor,
                    characterVolume.sourceDirectColor,
                    sourceIntensity,
                    exposureAdaptation,
                    characterVolume.dialogueLightingMode,
                    preparedLights,
                    preparedLightCount,
                    shadowAssignments,
                    shadowAssignmentCount,
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
                    EndfieldRecoveredEndminfFullLightDataContract.SizeBytes);
                commandBuffer.SetGlobalConstantBuffer(
                    buffer,
                    ExactDxbcBridgeConstantsId,
                    0,
                    EndfieldRecoveredEndminfFullLightDataContract.SizeBytes);
                commandBuffer.SetGlobalFloat(ReadyId, 1.0f);
                publicationCamera = camera;
                publicationPreparedSerial = preparedSerial;
                publicationReady = true;
                publishedPreparedSerial = preparedSerial;
                return true;
            }
            catch (Exception exception)
            {
                failure = "full Endminf LightData publication failed: " + exception.Message;
                ResetPublication(commandBuffer);
                return false;
            }
        }

        internal bool TryGetCurrentPublication(
            Camera expectedCamera,
            out ComputeBuffer publishedBuffer,
            out uint preparedSerial,
            out string failure)
        {
            publishedBuffer = null;
            preparedSerial = 0;
            failure = string.Empty;
            if (!publicationReady || publicationCamera != expectedCamera ||
                publicationPreparedSerial == 0 || buffer == null || !buffer.IsValid())
            {
                failure = "the full Endminf LightData publication is absent or stale";
                return false;
            }
            publishedBuffer = buffer;
            preparedSerial = publicationPreparedSerial;
            return true;
        }

        internal void ResetPublication(CommandBuffer commandBuffer)
        {
            if (commandBuffer == null)
                throw new ArgumentNullException(nameof(commandBuffer));
            publicationReady = false;
            publicationCamera = null;
            publicationPreparedSerial = 0;
            commandBuffer.SetGlobalFloat(ReadyId, 0.0f);
        }

        public void Dispose()
        {
            if (disposed)
                return;
            disposed = true;
            publicationReady = false;
            publicationCamera = null;
            publicationPreparedSerial = 0;
            if (buffer != null)
            {
                buffer.Release();
                buffer = null;
            }
            Shader.SetGlobalFloat(ReadyId, 0.0f);
        }

        private void EnsureBuffer()
        {
            if (buffer != null)
                return;
            buffer = new ComputeBuffer(
                EndfieldRecoveredEndminfFullLightDataContract.VectorCount,
                sizeof(float) * 4,
                ComputeBufferType.Constant)
            {
                name = "Recovered full Endminf retail _LightDataBuffer b31"
            };
        }
    }
}

using System;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Default-off same-frame transport for the selected resolver's b34
    /// punctual ShadowData section and its matching recovered D16 atlas.
    /// Other ShadowData sections remain zero and pass 0 remains disabled.
    /// </summary>
    public sealed class EndfieldRecoveredDeferredShadowData : IDisposable
    {
        public const string Selector =
            "ENDFIELD_RECOVERED_DEFERRED_SHADOW_DATA";

        private static readonly int ConstantsId =
            Shader.PropertyToID("_ShadowData");
        private static readonly int ExactDxbcBridgeConstantsId =
            Shader.PropertyToID("EndfieldCB5");
        private static readonly int PunctualShadowTextureId =
            Shader.PropertyToID("_PunctualLightShadowTexV2");
        private static readonly int ReadyId = Shader.PropertyToID(
            "_EndfieldRecoveredDeferredShadowDataReady");
        private static readonly int Pass0SubsetReadyId = Shader.PropertyToID(
            "_EndfieldRecoveredDeferredPass0InputSubsetReady");

        private readonly Vector4[] vectors = new Vector4[
            EndfieldRecoveredDeferredShadowDataContract.VectorCount];
        private ComputeBuffer buffer;
        private bool disposed;

        public static bool IsRequested
        {
            get
            {
                string value = Environment.GetEnvironmentVariable(Selector);
                return string.Equals(value, "1", StringComparison.Ordinal) ||
                    string.Equals(
                        value,
                        "true",
                        StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(
                        value,
                        "on",
                        StringComparison.OrdinalIgnoreCase);
            }
        }

        internal bool PrepareAndPublish(
            Camera camera,
            EndfieldHGOperatorLightRig rig,
            EndfieldRecoveredPunctualShadowProducer punctualShadowProducer,
            bool deferredLightDataReady,
            bool punctualShadowReady,
            CommandBuffer commandBuffer,
            out string failure)
        {
            failure = null;
            if (disposed)
            {
                throw new ObjectDisposedException(
                    nameof(EndfieldRecoveredDeferredShadowData));
            }
            if (commandBuffer == null)
                throw new ArgumentNullException(nameof(commandBuffer));

            ResetPublication(commandBuffer);
            if (!IsRequested)
            {
                failure = "explicit deferred ShadowData selector is disabled";
                return false;
            }
            if (!deferredLightDataReady)
            {
                failure =
                    "selected deferred LightData prerequisite is not ready";
                return false;
            }
            if (!punctualShadowReady)
            {
                failure =
                    "isolated punctual-shadow producer prerequisite is not ready";
                return false;
            }
            if (camera == null || rig == null ||
                punctualShadowProducer == null)
            {
                failure =
                    "physical camera, source-backed light rig, and punctual-shadow owner are required";
                return false;
            }
            if (!rig.TryGetIsolatedPunctualSoftShadowTarget(
                    camera,
                    out EndfieldHGIsolatedPunctualShadowTarget target,
                    out failure))
            {
                return false;
            }
            if (target.sourceIndex != 4 ||
                !string.Equals(
                    target.light.sourceName,
                    "RimLight_2 (5)",
                    StringComparison.Ordinal) ||
                target.light.shadowType != 2)
            {
                failure =
                    "isolated shadow target no longer matches source row 4 RimLight_2 (5)";
                return false;
            }

            if (!punctualShadowProducer.TryGetCurrentPublication(
                    out Matrix4x4[] worldToShadow,
                    out Vector4[] shadowParams,
                    out Vector4[] shadowRects,
                    out Vector4 texelSize,
                    out RenderTexture atlas,
                    out failure))
            {
                return false;
            }
            int tileResolution = rig.sourceBackedPunctualShadowTileResolution;
            int expectedWidth = 6 * tileResolution;
            int expectedHeight = 4 * tileResolution;
            if (atlas == null || !atlas.IsCreated() ||
                atlas.width != expectedWidth ||
                atlas.height != expectedHeight ||
                atlas.dimension != TextureDimension.Tex2D ||
                atlas.depthStencilFormat != GraphicsFormat.D16_UNorm)
            {
                failure =
                    "matching recovered 6T x 4T D16 punctual atlas is unavailable";
                return false;
            }

            int faceCount = target.light.spot ? 1 : 6;
            if (!EndfieldRecoveredDeferredShadowDataContract
                    .TryBuildSelectedPunctualSubset(
                        worldToShadow,
                        shadowParams,
                        shadowRects,
                        texelSize,
                        tileResolution,
                        faceCount,
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
                    EndfieldRecoveredDeferredShadowDataContract.SizeBytes);
                commandBuffer.SetGlobalConstantBuffer(
                    buffer,
                    ExactDxbcBridgeConstantsId,
                    0,
                    EndfieldRecoveredDeferredShadowDataContract
                        .D3D11SelectedSizeBytes);
                commandBuffer.SetGlobalTexture(
                    PunctualShadowTextureId,
                    atlas);
                commandBuffer.SetGlobalFloat(ReadyId, 1.0f);
                commandBuffer.SetGlobalFloat(Pass0SubsetReadyId, 1.0f);
                return true;
            }
            catch (Exception exception)
            {
                failure =
                    "deferred ShadowData publication failed: " +
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

        private void EnsureBuffer()
        {
            if (buffer != null)
                return;
            buffer = new ComputeBuffer(
                EndfieldRecoveredDeferredShadowDataContract.VectorCount,
                sizeof(float) * 4,
                ComputeBufferType.Constant)
            {
                name = "Recovered selected deferred ShadowData b34"
            };
        }
    }
}

using System;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Publishes the exact installed VisibilitySHConstData rows alongside the
    /// default-off canonical CharInfo frame. This does not publish or invent a
    /// retail VisibilitySH texture.
    /// </summary>
    public sealed class EndfieldRecoveredVisibilitySHConstants : IDisposable
    {
        private static readonly int ConstantsId =
            Shader.PropertyToID("VisibilitySHConstData");
        // The selected original D3D11 resolver reads this same source
        // payload through register b8.  Keep the exact bridge separate from
        // the semantic name so the canonical VisibilitySH producer remains
        // usable by the ordinary lab shaders.
        private static readonly int ExactDxbcBridgeConstantsId =
            Shader.PropertyToID("EndfieldCB8");
        private static readonly int ReadyId =
            Shader.PropertyToID("_EndfieldRecoveredVisibilitySHConstDataReady");

        private readonly Vector4[] vectors =
            new Vector4[EndfieldRecoveredVisibilitySHConstantsContract.VectorCount];
        private ComputeBuffer buffer;
        private bool disposed;

        public bool PrepareAndPublish(
            int cameraWidth,
            int cameraHeight,
            CommandBuffer commandBuffer,
            out string failure)
        {
            failure = null;
            if (disposed)
                throw new ObjectDisposedException(
                    nameof(EndfieldRecoveredVisibilitySHConstants));
            if (commandBuffer == null)
                throw new ArgumentNullException(nameof(commandBuffer));
            commandBuffer.SetGlobalFloat(ReadyId, 0.0f);
            if (!EndfieldRecoveredVisibilitySHConstantsContract.TryBuild(
                    cameraWidth,
                    cameraHeight,
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
                    EndfieldRecoveredVisibilitySHConstantsContract.SizeBytes);
                commandBuffer.SetGlobalConstantBuffer(
                    buffer,
                    ExactDxbcBridgeConstantsId,
                    0,
                    EndfieldRecoveredVisibilitySHConstantsContract.SizeBytes);
                commandBuffer.SetGlobalFloat(ReadyId, 1.0f);
                return true;
            }
            catch (Exception exception)
            {
                failure = "VisibilitySHConstData publication failed: " +
                    exception.Message;
                return false;
            }
        }

        public void ResetPublication(CommandBuffer commandBuffer)
        {
            if (commandBuffer == null)
                throw new ArgumentNullException(nameof(commandBuffer));
            commandBuffer.SetGlobalFloat(ReadyId, 0.0f);
            // Do not leave a previous frame's SH rows reachable through the
            // exact b8 bridge after a failed or disabled publication.  The
            // buffer is reused to avoid allocating a second zero fixture.
            if (buffer != null)
            {
                Array.Clear(vectors, 0, vectors.Length);
                buffer.SetData(vectors);
                commandBuffer.SetGlobalConstantBuffer(
                    buffer,
                    ConstantsId,
                    0,
                    EndfieldRecoveredVisibilitySHConstantsContract.SizeBytes);
                commandBuffer.SetGlobalConstantBuffer(
                    buffer,
                    ExactDxbcBridgeConstantsId,
                    0,
                    EndfieldRecoveredVisibilitySHConstantsContract.SizeBytes);
            }
        }

        internal ComputeBuffer CurrentBuffer => buffer;

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
        }

        private void EnsureBuffer()
        {
            if (buffer != null)
                return;
            buffer = new ComputeBuffer(
                EndfieldRecoveredVisibilitySHConstantsContract.VectorCount,
                sizeof(float) * 4,
                ComputeBufferType.Constant)
            {
                name = "Recovered exact VisibilitySHConstData fixture"
            };
        }
    }
}

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

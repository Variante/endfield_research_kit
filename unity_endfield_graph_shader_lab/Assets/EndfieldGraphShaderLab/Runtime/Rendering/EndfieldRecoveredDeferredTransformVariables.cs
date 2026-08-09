using System;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Default-off same-camera transport for the selected original deferred
    /// resolver's b30 reads. This is an input producer, not pass-0 activation.
    /// </summary>
    public sealed class EndfieldRecoveredDeferredTransformVariables : IDisposable
    {
        public const string Selector =
            "ENDFIELD_RECOVERED_DEFERRED_TRANSFORM_VARIABLES";

        private static readonly int ConstantsId =
            Shader.PropertyToID("_TransformVariables");
        private static readonly int ExactDxbcBridgeConstantsId =
            Shader.PropertyToID("EndfieldCB0");
        private static readonly int ReadyId = Shader.PropertyToID(
            "_EndfieldRecoveredDeferredTransformVariablesReady");
        private static readonly int Pass0SubsetReadyId = Shader.PropertyToID(
            "_EndfieldRecoveredDeferredPass0InputSubsetReady");

        private readonly Vector4[] vectors = new Vector4[
            EndfieldRecoveredDeferredTransformVariablesContract.VectorCount];
        private ComputeBuffer buffer;
        private bool disposed;

        public static bool IsRequested
        {
            get
            {
                string value = Environment.GetEnvironmentVariable(Selector);
                return string.Equals(value, "1", StringComparison.Ordinal) ||
                    string.Equals(value, "true", StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(value, "on", StringComparison.OrdinalIgnoreCase);
            }
        }

        public bool PrepareAndPublish(
            Camera camera,
            bool renderIntoTexture,
            CommandBuffer commandBuffer,
            out string failure)
        {
            failure = null;
            if (disposed)
            {
                throw new ObjectDisposedException(
                    nameof(EndfieldRecoveredDeferredTransformVariables));
            }
            if (commandBuffer == null)
                throw new ArgumentNullException(nameof(commandBuffer));

            ResetPublication(commandBuffer);
            if (!IsRequested)
            {
                failure = "explicit deferred TransformVariables selector is disabled";
                return false;
            }
            if (!EndfieldRecoveredDeferredTransformVariablesContract.TryBuild(
                    camera,
                    renderIntoTexture,
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
                    EndfieldRecoveredDeferredTransformVariablesContract.SizeBytes);
                commandBuffer.SetGlobalConstantBuffer(
                    buffer,
                    ExactDxbcBridgeConstantsId,
                    0,
                    EndfieldRecoveredDeferredTransformVariablesContract
                        .D3D11SelectedSizeBytes);
                commandBuffer.SetGlobalFloat(ReadyId, 1.0f);
                commandBuffer.SetGlobalFloat(Pass0SubsetReadyId, 1.0f);
                return true;
            }
            catch (Exception exception)
            {
                failure = "deferred TransformVariables publication failed: " +
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
                EndfieldRecoveredDeferredTransformVariablesContract.VectorCount,
                sizeof(float) * 4,
                ComputeBufferType.Constant)
            {
                name = "Recovered selected deferred _TransformVariables b30"
            };
        }
    }
}

using System;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Default-off same-camera transport for the selected original deferred
    /// resolver's b35 reads. This publishes inputs only and never enables pass 0.
    /// </summary>
    public sealed class EndfieldRecoveredShaderVariablesGlobal : IDisposable
    {
        public const string Selector =
            "ENDFIELD_RECOVERED_SHADER_VARIABLES_GLOBAL";

        private static readonly int ConstantsId =
            Shader.PropertyToID("ShaderVariablesGlobal");
        private static readonly int ExactDxbcBridgeConstantsId =
            Shader.PropertyToID("EndfieldCB1");
        private static readonly int ReadyId = Shader.PropertyToID(
            "_EndfieldRecoveredShaderVariablesGlobalReady");

        private readonly Vector4[] vectors = new Vector4[
            EndfieldRecoveredShaderVariablesGlobalContract.VectorCount];
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
            int width,
            int height,
            Vector4 environmentParams,
            bool prerequisitesReady,
            CommandBuffer commandBuffer,
            out string failure)
        {
            failure = null;
            if (disposed)
            {
                throw new ObjectDisposedException(
                    nameof(EndfieldRecoveredShaderVariablesGlobal));
            }
            if (commandBuffer == null)
                throw new ArgumentNullException(nameof(commandBuffer));

            ResetPublication(commandBuffer);
            if (!IsRequested)
            {
                failure =
                    "explicit ShaderVariablesGlobal selector is disabled";
                return false;
            }
            if (!EndfieldRecoveredShaderVariablesGlobalContract.TryBuild(
                    camera,
                    width,
                    height,
                    environmentParams,
                    prerequisitesReady,
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
                    EndfieldRecoveredShaderVariablesGlobalContract.SizeBytes);
                commandBuffer.SetGlobalConstantBuffer(
                    buffer,
                    ExactDxbcBridgeConstantsId,
                    0,
                    EndfieldRecoveredShaderVariablesGlobalContract
                        .D3D11SelectedSizeBytes);
                commandBuffer.SetGlobalFloat(ReadyId, 1.0f);
                return true;
            }
            catch (Exception exception)
            {
                failure =
                    "ShaderVariablesGlobal publication failed: " +
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
                EndfieldRecoveredShaderVariablesGlobalContract.VectorCount,
                sizeof(float) * 4,
                ComputeBufferType.Constant)
            {
                name = "Recovered selected ShaderVariablesGlobal b35"
            };
        }
    }
}

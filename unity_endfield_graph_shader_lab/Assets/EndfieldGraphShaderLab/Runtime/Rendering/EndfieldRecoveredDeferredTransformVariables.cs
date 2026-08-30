using System;
using System.Collections.Generic;
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
        private readonly Dictionary<int,
            EndfieldRecoveredDeferredTransformVariablesContract.CameraHistoryState>
            cameraHistory = new Dictionary<int,
                EndfieldRecoveredDeferredTransformVariablesContract
                    .CameraHistoryState>();
        private ComputeBuffer buffer;
        private bool disposed;
        private bool currentM27SourceReady;

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
            bool renderIntoTexture,
            int width,
            int height,
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
            if (camera == null)
            {
                failure = "physical camera is required";
                return false;
            }
            if (width <= 0 || height <= 0)
            {
                failure = "render dimensions must be positive";
                return false;
            }
            int cameraId = camera.GetInstanceID();
            cameraHistory.TryGetValue(
                cameraId,
                out EndfieldRecoveredDeferredTransformVariablesContract
                    .CameraHistoryState history);
            if (!EndfieldRecoveredDeferredTransformVariablesContract
                    .TryEvaluateHistory(
                        history,
                        Time.frameCount,
                        width,
                        height,
                        renderIntoTexture,
                        out bool previousFrameHistoryReady,
                        out failure))
            {
                return false;
            }
            if (!EndfieldRecoveredDeferredTransformVariablesContract.TryBuild(
                    camera,
                    renderIntoTexture,
                    history != null
                        ? history.nonJitteredViewNoTranslationProjection
                        : Matrix4x4.identity,
                    history != null
                        ? history.cameraPosition
                        : Vector3.zero,
                    previousFrameHistoryReady,
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
                var currentProjection = Matrix4x4.zero;
                for (int column = 0; column < 4; column++)
                {
                    currentProjection.SetColumn(
                        column,
                        vectors[
                            EndfieldRecoveredDeferredTransformVariablesContract
                                .NonJitteredViewNoTranslationProjectionFirstVector +
                            column]);
                }
                if (history == null)
                {
                    history = new EndfieldRecoveredDeferredTransformVariablesContract
                        .CameraHistoryState();
                    cameraHistory.Add(cameraId, history);
                }
                EndfieldRecoveredDeferredTransformVariablesContract.CommitHistory(
                    history,
                    currentProjection,
                    camera.transform.position,
                    Time.frameCount,
                    width,
                    height,
                    renderIntoTexture);
                currentM27SourceReady = true;
                // The combined pass-0 subset gate is raised only after b31
                // _LightDataBuffer also succeeds later in the same frame.
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
            currentM27SourceReady = false;
        }

        internal ComputeBuffer CurrentBuffer => buffer;
        public bool CurrentM27SourceReady => currentM27SourceReady;

        public void Dispose()
        {
            if (disposed)
                return;
            disposed = true;
            cameraHistory.Clear();
            currentM27SourceReady = false;
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

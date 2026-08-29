using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Exact producer-side reconstruction of retail DLSSVelocityCombineCS.
    /// This publishes the Streamline motion-vector input but does not select or
    /// emulate a DLSS/DLAA consumer, so it cannot alter the current beauty path.
    /// </summary>
    internal sealed class EndfieldRecoveredCombinedVelocityProducer
    {
        internal const GraphicsFormat OutputFormat =
            GraphicsFormat.R16G16_SFloat;

        private const string ComputeResourceName =
            "EndfieldRecoveredDLSSVelocityCombine";
        private const string KernelName = "CombineVelocity";
        private const int ThreadGroupSize = 8;

        private static readonly int VelocityId =
            Shader.PropertyToID("_Velocity");
        private static readonly int CombinedVelocityId =
            Shader.PropertyToID("_CombinedVelocity");
        private static readonly int InputExtentId =
            Shader.PropertyToID("_InputExtent");

        private readonly ComputeShader compute;
        private readonly int kernel = -1;
        private readonly int[] inputExtent = new int[2];
        private bool loggedActive;
        private string lastFailure = string.Empty;

        internal EndfieldRecoveredCombinedVelocityProducer()
        {
            compute = Resources.Load<ComputeShader>(ComputeResourceName);
            if (compute == null)
                return;
            try
            {
                kernel = compute.FindKernel(KernelName);
            }
            catch (System.Exception exception)
            {
                lastFailure = exception.Message;
            }
        }

        internal bool TryEnqueue(
            CommandBuffer commandBuffer,
            RenderTexture packedSceneMV,
            int width,
            int height,
            int destinationId,
            out string failure)
        {
            failure = string.Empty;
            if (commandBuffer == null)
            {
                failure = "command buffer is missing";
                return false;
            }
            if (compute == null || kernel < 0)
            {
                failure = string.IsNullOrEmpty(lastFailure)
                    ? "velocity-combine compute resource is unavailable"
                    : "velocity-combine kernel lookup failed: " + lastFailure;
                return false;
            }
            if (!SystemInfo.supportsComputeShaders)
            {
                failure = "compute shaders are unsupported";
                return false;
            }
            if (!SystemInfo.IsFormatSupported(
                    OutputFormat,
                    FormatUsage.LoadStore))
            {
                failure = OutputFormat + " does not support UAV load/store";
                return false;
            }
            if (packedSceneMV == null || !packedSceneMV.IsCreated())
            {
                failure = "packed SceneMV is unavailable";
                return false;
            }
            if (packedSceneMV.graphicsFormat !=
                EndfieldRecoveredSceneMVCompositor.SceneMVFormat)
            {
                failure =
                    "packed SceneMV format is " + packedSceneMV.graphicsFormat +
                    ", expected " +
                    EndfieldRecoveredSceneMVCompositor.SceneMVFormat;
                return false;
            }
            if (width <= 0 || height <= 0 ||
                packedSceneMV.width != width || packedSceneMV.height != height)
            {
                failure =
                    $"packed SceneMV extent {packedSceneMV.width}x" +
                    $"{packedSceneMV.height} does not match requested " +
                    $"{width}x{height}";
                return false;
            }

            var descriptor = new RenderTextureDescriptor(width, height)
            {
                graphicsFormat = OutputFormat,
                depthStencilFormat = GraphicsFormat.None,
                msaaSamples = 1,
                volumeDepth = 1,
                dimension = TextureDimension.Tex2D,
                sRGB = false,
                useMipMap = false,
                autoGenerateMips = false,
                enableRandomWrite = true
            };
            commandBuffer.GetTemporaryRT(
                destinationId,
                descriptor,
                FilterMode.Point);
            commandBuffer.SetComputeTextureParam(
                compute,
                kernel,
                VelocityId,
                packedSceneMV);
            commandBuffer.SetComputeTextureParam(
                compute,
                kernel,
                CombinedVelocityId,
                new RenderTargetIdentifier(destinationId));
            inputExtent[0] = width;
            inputExtent[1] = height;
            commandBuffer.SetComputeIntParams(
                compute,
                InputExtentId,
                inputExtent);
            commandBuffer.DispatchCompute(
                compute,
                kernel,
                Mathf.CeilToInt(width / (float)ThreadGroupSize),
                Mathf.CeilToInt(height / (float)ThreadGroupSize),
                1);
            commandBuffer.SetGlobalTexture(
                CombinedVelocityId,
                new RenderTargetIdentifier(destinationId));

            if (!loggedActive)
            {
                Debug.Log(
                    "Recovered DLSSVelocityCombineCS producer active: " +
                    $"{width}x{height} packed " +
                    EndfieldRecoveredSceneMVCompositor.SceneMVFormat +
                    " -> " + OutputFormat +
                    $", dispatch {Mathf.CeilToInt(width / 8.0f)}x" +
                    $"{Mathf.CeilToInt(height / 8.0f)}; no DLSS/DLAA " +
                    "consumer is enabled.");
                loggedActive = true;
            }
            return true;
        }

        internal bool TryEnqueue(
            CommandBuffer commandBuffer,
            RenderTexture packedSceneMV,
            int width,
            int height,
            RenderTexture destination,
            out string failure)
        {
            failure = string.Empty;
            if (!ValidateSource(
                    commandBuffer,
                    packedSceneMV,
                    width,
                    height,
                    out failure))
            {
                return false;
            }
            if (destination == null || !destination.IsCreated())
            {
                failure = "persistent combined-velocity destination is unavailable";
                return false;
            }
            if (destination.width != width || destination.height != height ||
                destination.graphicsFormat != OutputFormat ||
                !destination.enableRandomWrite)
            {
                failure =
                    $"persistent combined-velocity destination is " +
                    $"{destination.width}x{destination.height} " +
                    $"{destination.graphicsFormat}, randomWrite=" +
                    destination.enableRandomWrite + "; expected " +
                    $"{width}x{height} {OutputFormat}, randomWrite=true";
                return false;
            }

            commandBuffer.SetComputeTextureParam(
                compute,
                kernel,
                VelocityId,
                packedSceneMV);
            commandBuffer.SetComputeTextureParam(
                compute,
                kernel,
                CombinedVelocityId,
                destination);
            inputExtent[0] = width;
            inputExtent[1] = height;
            commandBuffer.SetComputeIntParams(
                compute,
                InputExtentId,
                inputExtent);
            commandBuffer.DispatchCompute(
                compute,
                kernel,
                Mathf.CeilToInt(width / (float)ThreadGroupSize),
                Mathf.CeilToInt(height / (float)ThreadGroupSize),
                1);
            commandBuffer.SetGlobalTexture(CombinedVelocityId, destination);
            return true;
        }

        private bool ValidateSource(
            CommandBuffer commandBuffer,
            RenderTexture packedSceneMV,
            int width,
            int height,
            out string failure)
        {
            failure = string.Empty;
            if (commandBuffer == null)
            {
                failure = "command buffer is missing";
                return false;
            }
            if (compute == null || kernel < 0)
            {
                failure = string.IsNullOrEmpty(lastFailure)
                    ? "velocity-combine compute resource is unavailable"
                    : "velocity-combine kernel lookup failed: " + lastFailure;
                return false;
            }
            if (!SystemInfo.supportsComputeShaders)
            {
                failure = "compute shaders are unsupported";
                return false;
            }
            if (!SystemInfo.IsFormatSupported(
                    OutputFormat,
                    FormatUsage.LoadStore))
            {
                failure = OutputFormat + " does not support UAV load/store";
                return false;
            }
            if (packedSceneMV == null || !packedSceneMV.IsCreated())
            {
                failure = "packed SceneMV is unavailable";
                return false;
            }
            if (packedSceneMV.graphicsFormat !=
                EndfieldRecoveredSceneMVCompositor.SceneMVFormat)
            {
                failure =
                    "packed SceneMV format is " + packedSceneMV.graphicsFormat +
                    ", expected " +
                    EndfieldRecoveredSceneMVCompositor.SceneMVFormat;
                return false;
            }
            if (width <= 0 || height <= 0 ||
                packedSceneMV.width != width || packedSceneMV.height != height)
            {
                failure =
                    $"packed SceneMV extent {packedSceneMV.width}x" +
                    $"{packedSceneMV.height} does not match requested " +
                    $"{width}x{height}";
                return false;
            }
            return true;
        }
    }
}

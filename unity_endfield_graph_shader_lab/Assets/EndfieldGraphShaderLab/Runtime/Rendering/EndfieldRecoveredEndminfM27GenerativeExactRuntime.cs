using System;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Default-off binding contract for a compiler-substituted M27 exact draw
    /// submitted by the retained ParticleSystemRenderer. This path owns no
    /// captured geometry or constant-buffer packet data and never presents its
    /// five diagnostic targets.
    /// </summary>
    internal sealed class EndfieldRecoveredEndminfM27GenerativeExactRuntime :
        IDisposable
    {
        internal const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_ENDMINF_M27_GENERATIVE_EXACT_DXBC";

        private static readonly int TransformVariablesId =
            Shader.PropertyToID("_TransformVariables");
        private static readonly int ShaderVariablesGlobalId =
            Shader.PropertyToID("ShaderVariablesGlobal");
        private static readonly TextureContract[] TextureContracts =
        {
            new TextureContract(
                "_BaseColorMap", 1024, 1024,
                GraphicsFormat.RGBA_BC7_SRGB, 11),
            new TextureContract(
                "_NormalMap", 1024, 1024,
                GraphicsFormat.RG_BC5_UNorm, 11),
            new TextureContract(
                "_MROMap", 1024, 1024,
                GraphicsFormat.RG_BC5_UNorm, 11),
            new TextureContract(
                "_ParallaxMap", 128, 128,
                GraphicsFormat.RGBA_BC7_SRGB, 8),
        };
        private static readonly string[] SerializedNullTextureProperties =
        {
            "_ParallaxMaskMap",
            "_ParallaxNoiseMap",
        };

        private static readonly string[] FloatProperties =
        {
            "_NormalScale",
            "_RoughnessMin",
            "_RoughnessMax",
            "_OcclusionStrength",
            "_TwoSidedNormal",
            "_BaseUVSet",
            "_BasePbrMapUVSet",
            "_TAAUNormalBiasReverse",
            "_BaseTextureMapCount",
            "_BaseColorTintCover",
            "_Metallic",
            "_BaseColorBrighterScale",
            "_AntiFlicker",
            "_TaauMaskModeValue",
            "_ParallaxStrength",
            "_ParallaxTilling",
            "_ParallaxAnimSpeed",
            "_ParallaxAnimRandom",
            "_ParallaxMinBrightness",
            "_ParallaxFresnelStrength",
            "_ParallaxIgnorePostExposure",
            "_ParallaxMaskChannel",
            "_ParallaxMapUVType",
            "_ParallaxMaskByLayerBlend",
            "_ParallaxNoiseMapTilling",
            "_ParallaxCharPos",
            "_ParallaxBrightOuterRadius",
            "_ParallaxBrightInnerRadius",
            "_ParallaxBrightStrength",
            "_UseParallaxMask",
            "_ParallaxIntensity",
        };

        private static readonly string[] ColorProperties =
        {
            "_BaseColor",
            "_ParallaxColor",
            "_ParallaxColorDark",
        };

        private bool disposed;

        internal static bool Requested => IsEnabled(
            Environment.GetEnvironmentVariable(EnvironmentVariable));

        internal bool TryConfigureMaterial(
            Material source,
            Material destination,
            out string failure)
        {
            failure = string.Empty;
            if (source == null || destination == null)
            {
                failure = "source and exact-shell materials are required";
                return false;
            }

            foreach (TextureContract contract in TextureContracts)
            {
                if (!source.HasProperty(contract.id) ||
                    !destination.HasProperty(contract.id))
                {
                    failure = contract.name + " is absent from the source or shell";
                    return false;
                }
                Texture2D texture = source.GetTexture(contract.id) as Texture2D;
                if (texture == null ||
                    texture.width != contract.width ||
                    texture.height != contract.height ||
                    texture.mipmapCount != contract.mipCount ||
                    texture.graphicsFormat != contract.format)
                {
                    failure = contract.name + " native full-mip contract drifted";
                    return false;
                }
                destination.SetTexture(contract.id, texture);
                destination.SetTextureScale(
                    contract.name,
                    source.GetTextureScale(contract.name));
                destination.SetTextureOffset(
                    contract.name,
                    source.GetTextureOffset(contract.name));
            }
            foreach (string property in SerializedNullTextureProperties)
            {
                if (!source.HasProperty(property) ||
                    !destination.HasProperty(property))
                {
                    failure = property +
                        " is absent from the source or exact shell";
                    return false;
                }
                if (source.GetTexture(property) != null)
                {
                    failure = property +
                        " no longer matches the serialized-null M27 source";
                    return false;
                }
                // Leave the destination's recovered black ShaderLab default
                // intact. The exact retail draw binds one shared null/default
                // resource at both physical slots.
            }

            foreach (string property in FloatProperties)
            {
                if (source.HasProperty(property) &&
                    destination.HasProperty(property))
                {
                    destination.SetFloat(property, source.GetFloat(property));
                }
            }
            foreach (string property in ColorProperties)
            {
                if (source.HasProperty(property) &&
                    destination.HasProperty(property))
                {
                    destination.SetColor(property, source.GetColor(property));
                }
            }
            if (!destination.HasProperty("_ParallaxMarchNum"))
            {
                failure = "the exact shell lost _ParallaxMarchNum b3 identity";
                return false;
            }
            int marchCount = source.HasProperty("_ParallaxMarchNum")
                ? Mathf.RoundToInt(source.GetFloat("_ParallaxMarchNum"))
                : destination.GetInteger("_ParallaxMarchNum");
            destination.SetInteger("_ParallaxMarchNum", marchCount);
            destination.EnableKeyword("ENDFIELD_ORIGINAL_DXBC_M27_EXACT");
            return true;
        }

        internal bool TryBindDraw(
            Material material,
            bool compilerSubstitutionReady,
            ComputeBuffer transformVariables,
            bool transformVariablesReady,
            ComputeBuffer shaderVariablesGlobal,
            bool shaderVariablesGlobalReady,
            EndfieldRecoveredTerrainSubsurfaceConstants.PublisherState
                terrainSubsurfaceConstants,
            CommandBuffer command,
            out string failure)
        {
            failure = string.Empty;
            if (disposed)
            {
                failure = "the generative exact M27 runtime is disposed";
                return false;
            }
            if (material == null || command == null)
            {
                failure = "the exact material and command buffer are required";
                return false;
            }
            if (!compilerSubstitutionReady)
            {
                failure =
                    "the generative M27 shell has not been independently " +
                    "hash-pinned and compiler-substituted";
                return false;
            }
            bool transformSourceReady =
                EndfieldRecoveredDeferredTransformVariablesContract
                    .TryValidateCurrentPublisherForM27(
                        out string transformSourceFailure);
            bool globalSourceReady =
                EndfieldRecoveredShaderVariablesGlobalContract
                    .TryValidateCurrentPublisherForM27(
                        out string globalSourceFailure);
            if (!transformSourceReady || !globalSourceReady)
            {
                failure = "M27 generative constant-buffer source closure failed: ";
                if (!transformSourceReady)
                    failure += transformSourceFailure;
                if (!transformSourceReady && !globalSourceReady)
                    failure += "; ";
                if (!globalSourceReady)
                    failure += globalSourceFailure;
                return false;
            }
            if (!transformVariablesReady || transformVariables == null ||
                transformVariables.count * transformVariables.stride !=
                    EndfieldRecoveredDeferredTransformVariablesContract.SizeBytes)
            {
                failure = "full _TransformVariables b0 publisher is not ready";
                return false;
            }
            if (!shaderVariablesGlobalReady || shaderVariablesGlobal == null ||
                shaderVariablesGlobal.count * shaderVariablesGlobal.stride !=
                    EndfieldRecoveredShaderVariablesGlobalContract.SizeBytes)
            {
                failure = "full ShaderVariablesGlobal b1 publisher is not ready";
                return false;
            }
            if (!terrainSubsurfaceConstants.ready ||
                !string.Equals(
                    terrainSubsurfaceConstants.nativeContractSchema,
                    EndfieldRecoveredTerrainSubsurfaceConstants
                        .NativeContractSchema,
                    StringComparison.Ordinal) ||
                !string.Equals(
                    terrainSubsurfaceConstants.selectedFrameProvenanceSchema,
                    EndfieldRecoveredTerrainSubsurfaceConstants
                        .RequiredSelectedFrameProvenanceSchema,
                    StringComparison.Ordinal) ||
                string.IsNullOrWhiteSpace(
                    terrainSubsurfaceConstants.selectedFrameProvenance))
            {
                failure =
                    "the named _TerrainSubsurfaceProfileInt b4 publisher lacks " +
                    "fresh selected-frame value provenance";
                return false;
            }

            command.SetGlobalConstantBuffer(
                transformVariables,
                TransformVariablesId,
                0,
                EndfieldRecoveredDeferredTransformVariablesContract.SizeBytes);
            command.SetGlobalConstantBuffer(
                shaderVariablesGlobal,
                ShaderVariablesGlobalId,
                0,
                EndfieldRecoveredShaderVariablesGlobalContract.SizeBytes);
            return true;
        }

        public void Dispose()
        {
            if (disposed)
                return;
            disposed = true;
        }

        private static bool IsEnabled(string value)
        {
            return string.Equals(value, "1", StringComparison.Ordinal) ||
                string.Equals(value, "true", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(value, "yes", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(value, "on", StringComparison.OrdinalIgnoreCase);
        }

        private readonly struct TextureContract
        {
            internal readonly string name;
            internal readonly int id;
            internal readonly int width;
            internal readonly int height;
            internal readonly GraphicsFormat format;
            internal readonly int mipCount;

            internal TextureContract(
                string name,
                int width,
                int height,
                GraphicsFormat format,
                int mipCount)
            {
                this.name = name;
                id = Shader.PropertyToID(name);
                this.width = width;
                this.height = height;
                this.format = format;
                this.mipCount = mipCount;
            }
        }
    }
}

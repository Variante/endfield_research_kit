using System;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Selected-consumer subset of the original deferred pass-0 b35
    /// ShaderVariablesGlobal constant buffer. Every non-selected row remains
    /// zero until its producer is independently recovered.
    /// </summary>
    public static class EndfieldRecoveredShaderVariablesGlobalContract
    {
        public const int SizeBytes = 3200;
        public const int VectorCount = 200;
        public const int D3D11SelectedSizeBytes = 2512;
        public const int D3D11SelectedVectorCount = 157;

        public const int ScreenSizeVector = 0;
        public const int ProjectionParamsVector = 3;
        public const int OrthoParamsVector = 4;
        public const int TaaJitterStrengthVector = 19;
        public const int GlobalMipBiasVector = 26;
        public const int ExposureWithMiscParamsVector = 27;
        public const int BinningOffsetsVector = 28;
        public const int EnvironmentParamsVector = 29;
        public const int GraphicsFeatures0Vector = 30;
        public const int GraphicsFeatures1Vector = 31;
        public const int AtmosphereFogFirstVector = 71;
        public const int HeightFogFirstVector = 77;
        public const int VolumetricFogFirstVector = 83;
        public const int IrradianceParamsFirstVector = 132;
        public const int DefaultSHRedVector = 135;
        public const int DefaultSHGreenVector = 136;
        public const int DefaultSHBlueVector = 137;
        public const int WetnessVector = 156;
        public const int VFXParams0Vector = 103;
        public const int VFXParams2Vector = 105;

        public static readonly int[] M27ReadVectors =
        {
            0, 4, 19, 26, 27, 103, 105,
        };

        /// <summary>
        /// Authoritative live inputs for the M27-read b1 rows. Readiness bits
        /// distinguish a valid zero from absent state, so clearing the buffer
        /// can never be promoted to source evidence.
        /// </summary>
        public readonly struct M27SourceInputs
        {
            public readonly bool targetDimensionsReady;
            public readonly bool perspectiveCameraReady;
            public readonly Vector4 taaJitterStrength;
            public readonly bool taaJitterReady;
            public readonly float physicalCameraGlobalMipBias;
            public readonly bool physicalCameraGlobalMipBiasReady;
            public readonly float exposureAdaptation;
            public readonly bool exposureReady;
            public readonly Vector3 vfxPlayerPosition;
            public readonly float vfxClockSeconds;
            public readonly bool vfxParams0Ready;
            public readonly Vector4 vfxParams2;
            public readonly bool vfxParams2Ready;

            public M27SourceInputs(
                bool targetDimensionsReady,
                bool perspectiveCameraReady,
                Vector4 taaJitterStrength,
                bool taaJitterReady,
                float physicalCameraGlobalMipBias,
                bool physicalCameraGlobalMipBiasReady,
                float exposureAdaptation,
                bool exposureReady,
                Vector3 vfxPlayerPosition,
                float vfxClockSeconds,
                bool vfxParams0Ready,
                Vector4 vfxParams2,
                bool vfxParams2Ready)
            {
                this.targetDimensionsReady = targetDimensionsReady;
                this.perspectiveCameraReady = perspectiveCameraReady;
                this.taaJitterStrength = taaJitterStrength;
                this.taaJitterReady = taaJitterReady;
                this.physicalCameraGlobalMipBias =
                    physicalCameraGlobalMipBias;
                this.physicalCameraGlobalMipBiasReady =
                    physicalCameraGlobalMipBiasReady;
                this.exposureAdaptation = exposureAdaptation;
                this.exposureReady = exposureReady;
                this.vfxPlayerPosition = vfxPlayerPosition;
                this.vfxClockSeconds = vfxClockSeconds;
                this.vfxParams0Ready = vfxParams0Ready;
                this.vfxParams2 = vfxParams2;
                this.vfxParams2Ready = vfxParams2Ready;
            }

            /// <summary>
            /// The default publisher owns only the current render target and
            /// perspective Camera arguments. Zero-valued fields below are
            /// placeholders guarded by false readiness bits, not recovered
            /// runtime values.
            /// </summary>
            public static M27SourceInputs CurrentTargetAndPerspectiveCameraOnly
            {
                get
                {
                    return new M27SourceInputs(
                        true,
                        true,
                        Vector4.zero,
                        false,
                        0.0f,
                        false,
                        0.0f,
                        false,
                        Vector3.zero,
                        0.0f,
                        false,
                        Vector4.zero,
                        false);
                }
            }

            /// <summary>
            /// Joins the independently recovered source-closed Manual exposure
            /// and live lab actor-root/time carrier to the target/camera lanes.
            /// The carrier is not proof of retail selected-frame HGVFX player
            /// identity. TAA, the physical-camera material mip-bias assignment,
            /// and the HGVFX anchor owner deliberately remain absent. These
            /// partial live sources can populate their selected registers but
            /// can never admit the M27 draw by themselves.
            /// </summary>
            public static M27SourceInputs
                CurrentTargetPerspectiveExposureAndVFXPlayer(
                    float exposureAdaptation,
                    bool exposureReady,
                    Vector3 vfxPlayerPosition,
                    float vfxClockSeconds,
                    bool vfxParams0Ready)
            {
                return new M27SourceInputs(
                    true,
                    true,
                    Vector4.zero,
                    false,
                    0.0f,
                    false,
                    exposureAdaptation,
                    exposureReady,
                    vfxPlayerPosition,
                    vfxClockSeconds,
                    vfxParams0Ready,
                    Vector4.zero,
                    false);
            }

            /// <summary>
            /// Overlays only the authenticated post-dynamic HGCamera.globalMipBias
            /// producer. A missing owner preserves the prior readiness/value.
            /// </summary>
            public M27SourceInputs WithPhysicalCameraGlobalMipBias(
                float value,
                bool ready)
            {
                if (!ready)
                    return this;
                return new M27SourceInputs(
                    targetDimensionsReady,
                    perspectiveCameraReady,
                    taaJitterStrength,
                    taaJitterReady,
                    value,
                    true,
                    exposureAdaptation,
                    exposureReady,
                    vfxPlayerPosition,
                    vfxClockSeconds,
                    vfxParams0Ready,
                    vfxParams2,
                    vfxParams2Ready);
            }
        }

        public static readonly Vector4 SelectedEnvironmentParams = new Vector4(
            0.28772247f,
            0.28772247f,
            1.0f,
            0.0f);

        public static readonly Vector4 SelectedDefaultSH = new Vector4(
            -0.007550761f,
            0.47223732f,
            0.012170809f,
            1.0963056f);

        public static readonly int[] SelectedUsedVectors =
        {
            0, 3, 4, 19, 26, 27, 28, 29, 30, 31,
            71, 72, 73, 74, 75, 76,
            77, 78, 79, 80, 81, 82,
            83, 84, 85, 86, 87,
            103, 105,
            132, 133, 134, 135, 136, 137,
            156,
        };

        public static bool TryBuild(
            Camera camera,
            int width,
            int height,
            Vector4 environmentParams,
            bool prerequisitesReady,
            Vector4[] destination,
            out string failure)
        {
            return TryBuild(
                camera,
                width,
                height,
                environmentParams,
                prerequisitesReady,
                M27SourceInputs.CurrentTargetAndPerspectiveCameraOnly,
                destination,
                out failure);
        }

        public static bool TryBuild(
            Camera camera,
            int width,
            int height,
            Vector4 environmentParams,
            bool prerequisitesReady,
            M27SourceInputs m27Inputs,
            Vector4[] destination,
            out string failure)
        {
            failure = null;
            if (!prerequisitesReady)
            {
                failure =
                    "canonical binning/reflection/VisibilitySH and deferred " +
                    "TransformVariables prerequisites are required";
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
            if (camera.orthographic)
            {
                failure = "selected CharInfo camera must be perspective";
                return false;
            }
            if (FloatBits(camera.nearClipPlane) != FloatBits(0.1f))
            {
                failure =
                    "selected CharInfo near clip must be exact float32 0.1";
                return false;
            }
            if (FloatBits(environmentParams.x) !=
                    FloatBits(SelectedEnvironmentParams.x) ||
                FloatBits(environmentParams.y) !=
                    FloatBits(SelectedEnvironmentParams.y))
            {
                failure =
                    "selected CharInfo environment diffuse/specular factors " +
                    "must match the serialized phase";
                return false;
            }
            if (destination == null || destination.Length != VectorCount)
            {
                failure =
                    "destination must contain exactly 200 float4 vectors";
                return false;
            }
            if (m27Inputs.taaJitterReady &&
                !IsFinite(m27Inputs.taaJitterStrength))
            {
                failure = "M27 b1 c19 Halton TAA jitter must be finite";
                return false;
            }
            if (m27Inputs.physicalCameraGlobalMipBiasReady &&
                !IsFinite(m27Inputs.physicalCameraGlobalMipBias))
            {
                failure =
                    "M27 b1 c26 physical-camera global mip bias must be finite";
                return false;
            }
            if (m27Inputs.exposureReady &&
                (!IsFinite(m27Inputs.exposureAdaptation) ||
                 m27Inputs.exposureAdaptation <= 0.0f))
            {
                failure =
                    "M27 b1 c27.y exposure adaptation must be finite and positive";
                return false;
            }
            if (m27Inputs.vfxParams0Ready &&
                (!IsFinite(m27Inputs.vfxPlayerPosition) ||
                 !IsFinite(m27Inputs.vfxClockSeconds) ||
                 m27Inputs.vfxClockSeconds < 0.0f))
            {
                failure =
                    "M27 b1 c103 VFX player position/time must be finite and nonnegative";
                return false;
            }
            if (m27Inputs.vfxParams2Ready && !IsFinite(m27Inputs.vfxParams2))
            {
                failure = "M27 b1 c105 VFX anchor parameters must be finite";
                return false;
            }
            if (!EndfieldRecoveredCanonicalBinningLayoutContract.TryBuild(
                    width,
                    height,
                    out EndfieldRecoveredCanonicalBinningLayoutContract.Layout
                        layout,
                    out failure))
            {
                return false;
            }

            Array.Clear(destination, 0, destination.Length);
            destination[ScreenSizeVector] = new Vector4(
                width,
                height,
                1.0f / width,
                1.0f / height);
            destination[ProjectionParamsVector] = new Vector4(
                0.0f,
                camera.nearClipPlane,
                0.0f,
                0.0f);
            // c4.w is derived from the current camera mode. The selected M27
            // path rejects orthographic cameras above, so its value is zero.
            destination[OrthoParamsVector] = new Vector4(
                0.0f,
                0.0f,
                0.0f,
                camera.orthographic ? 1.0f : 0.0f);
            if (m27Inputs.taaJitterReady)
            {
                destination[TaaJitterStrengthVector] =
                    m27Inputs.taaJitterStrength;
            }
            if (m27Inputs.physicalCameraGlobalMipBiasReady)
            {
                float globalMipBiasPow2 = Mathf.Pow(
                    2.0f,
                    m27Inputs.physicalCameraGlobalMipBias);
                if (!IsFinite(globalMipBiasPow2))
                {
                    failure = "M27 b1 c26.y mip-bias pow2 overflowed";
                    return false;
                }
                // Retail publishes c26.y=pow(2,c26.x). c26.w remains
                // branch-dead behind the source-backed disabled-volumetric
                // c83.z=0.
                destination[GlobalMipBiasVector] = new Vector4(
                    m27Inputs.physicalCameraGlobalMipBias,
                    globalMipBiasPow2,
                    0.0f,
                    0.0f);
            }
            if (m27Inputs.exposureReady)
            {
                destination[ExposureWithMiscParamsVector] = new Vector4(
                    m27Inputs.exposureAdaptation,
                    1.0f / m27Inputs.exposureAdaptation,
                    width / (float)height,
                    0.0f);
            }
            destination[BinningOffsetsVector] = new Vector4(
                IntBits(layout.lightXYOffset),
                IntBits(layout.lightZOffset),
                IntBits(layout.reflectionXYOffset),
                IntBits(layout.reflectionZOffset));
            destination[EnvironmentParamsVector] = new Vector4(
                SelectedEnvironmentParams.x,
                SelectedEnvironmentParams.y,
                0.0f,
                0.0f);
            destination[GraphicsFeatures0Vector] = new Vector4(
                0.0f,
                0.0f,
                1.0f,
                1.0f);
            destination[GraphicsFeatures1Vector] = new Vector4(
                7.0f,
                0.0f,
                0.0f,
                0.0f);

            destination[71] = Vector4.zero;
            destination[72] = new Vector4(0.0f, 0.0f, 1.0f, 0.001f);
            destination[73] = new Vector4(0.00001f, 0.00001f, 0.00001f, 0.0f);
            destination[74] = new Vector4(0.0f, 0.0f, 0.0f, -1.0f);
            destination[75] = Vector4.zero;
            destination[76] = new Vector4(0.0f, 0.0f, 0.0f, -65535.0f);

            destination[77] = Vector4.zero;
            destination[78] = Vector4.zero;
            destination[79] = new Vector4(0.0f, 0.0f, 0.0f, 1.0f);
            destination[80] = Vector4.zero;
            destination[81] = new Vector4(0.0f, 1.0f, 0.0f, 0.0f);
            destination[82] = new Vector4(0.0f, 0.0f, 0.0f, 1.0f);

            // c83.z disables every downstream volumetric read. c83..c87 and
            // inactive V2 irradiance c132..c134 remain exact zero vectors.
            for (int vector = 83; vector <= 87; vector++)
                destination[vector] = Vector4.zero;
            for (int vector = 132; vector <= 134; vector++)
                destination[vector] = Vector4.zero;

            destination[DefaultSHRedVector] = SelectedDefaultSH;
            destination[DefaultSHGreenVector] = SelectedDefaultSH;
            destination[DefaultSHBlueVector] = SelectedDefaultSH;
            destination[WetnessVector] = Vector4.zero;
            if (m27Inputs.vfxParams0Ready)
            {
                destination[VFXParams0Vector] = new Vector4(
                    m27Inputs.vfxPlayerPosition.x,
                    m27Inputs.vfxPlayerPosition.y,
                    m27Inputs.vfxPlayerPosition.z,
                    m27Inputs.vfxClockSeconds % 1024.0f);
            }
            if (m27Inputs.vfxParams2Ready)
                destination[VFXParams2Vector] = m27Inputs.vfxParams2;
            return true;
        }

        public static bool TryValidateM27SourceReadiness(
            M27SourceInputs m27Inputs,
            out string failure)
        {
            if (!m27Inputs.targetDimensionsReady)
            {
                failure =
                    "M27 b1 c0.zw requires current target dimensions and reciprocals";
                return false;
            }
            if (!m27Inputs.perspectiveCameraReady)
            {
                failure =
                    "M27 b1 c4.w requires the current physical-camera perspective flag";
                return false;
            }
            if (!m27Inputs.taaJitterReady)
            {
                failure =
                    "M27 b1 c19.zw requires authoritative live HGCamera Halton jitter";
                return false;
            }
            if (!m27Inputs.physicalCameraGlobalMipBiasReady)
            {
                failure =
                    "M27 b1 c26.xy requires authoritative physical-camera global mip bias";
                return false;
            }
            if (!m27Inputs.exposureReady)
            {
                failure =
                    "M27 b1 c27.y (_ExposureWithMiscParams reciprocal exposure) " +
                    "requires authoritative live camera exposure history";
                return false;
            }
            if (!m27Inputs.vfxParams0Ready)
            {
                failure =
                    "M27 b1 c103.xyzw (_VFXParams0) requires the unique live " +
                    "lab actor-root carrier and Time.time modulo 1024; retail " +
                    "selected-frame HGVFX player identity remains unproven";
                return false;
            }
            if (!m27Inputs.vfxParams2Ready)
            {
                failure =
                    "M27 b1 c105.xyzw (_VFXParams2) requires authoritative " +
                    "live HGVFXManager anchor position/radius/brightness state";
                return false;
            }
            failure = null;
            return true;
        }

        public static bool TryValidateCurrentPublisherForM27(
            out string failure)
        {
            return TryValidateM27SourceReadiness(
                M27SourceInputs.CurrentTargetAndPerspectiveCameraOnly,
                out failure);
        }

        public static uint[] BuildExpectedWords(Vector4[] vectors)
        {
            if (vectors == null || vectors.Length != VectorCount)
            {
                throw new ArgumentException(
                    "Expected exactly 200 vectors.",
                    nameof(vectors));
            }
            var words = new uint[VectorCount * 4];
            for (int vectorIndex = 0; vectorIndex < vectors.Length; vectorIndex++)
            {
                Vector4 value = vectors[vectorIndex];
                int word = vectorIndex * 4;
                words[word + 0] = FloatBits(value.x);
                words[word + 1] = FloatBits(value.y);
                words[word + 2] = FloatBits(value.z);
                words[word + 3] = FloatBits(value.w);
            }
            return words;
        }

        private static float IntBits(int value)
        {
            return BitConverter.Int32BitsToSingle(value);
        }

        private static bool IsFinite(Vector3 value)
        {
            return IsFinite(value.x) &&
                IsFinite(value.y) &&
                IsFinite(value.z);
        }

        private static bool IsFinite(Vector4 value)
        {
            return IsFinite(value.x) &&
                IsFinite(value.y) &&
                IsFinite(value.z) &&
                IsFinite(value.w);
        }

        private static bool IsFinite(float value)
        {
            return !float.IsNaN(value) && !float.IsInfinity(value);
        }

        private static uint FloatBits(float value)
        {
            return unchecked((uint)BitConverter.SingleToInt32Bits(value));
        }
    }
}

using System;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Selected-consumer subset of the original pass-0 b31 _LightDataBuffer.
    /// The retail allocation is six header vectors followed by 256 records of
    /// eight vectors. The selected SphereOutside program consumes the three
    /// directional fields below. For the isolated CharInfo overview rigs, each
    /// punctual row is source-authored CharacterOnly with no OBB, so the same
    /// program reads record[5].w, then record[3].z, and exits before consuming
    /// the unresolved general-scene punctual payload.
    /// </summary>
    public static class EndfieldRecoveredDeferredLightDataContract
    {
        public const int HeaderVectorCount = 6;
        public const int MaxPunctualLightCount = 256;
        public const int VectorsPerPunctualLight = 8;
        public const int VectorCount = HeaderVectorCount +
            MaxPunctualLightCount * VectorsPerPunctualLight;
        public const int SizeBytes = VectorCount * sizeof(float) * 4;

        public const int DirectionalDirectionVector = 0;
        public const int DirectionalColorVector = 1;
        public const int DirectionalCustomData2Vector = 4;
        public const int PunctualCharacterOnlyVectorInRecord = 3;
        public const int PunctualObbFlagsVectorInRecord = 5;

        // CharInfo_Env PathID 1201129019072041203, raw-data SHA-256
        // f9d1384c29f1e54599cd55e5f9c5c6d7eb9bd6f678d9fd104c7c329e6f1a66f9.
        public const float SourceDirectIntensity = 8.631674f;
        public const float SourceDirectIntensityDividePi =
            SourceDirectIntensity / Mathf.PI;
        public const float SourceDirectSpecularIntensity = 1.0f;
        public const float SourceDirectSoftRadiusDegrees = 0.0f;
        public static readonly Vector3 SourceDirectionalForward = new Vector3(
            0.021389274f,
            -0.64278764f,
            -0.76574594f);

        public static bool TryBuildSelectedConsumerSubset(
            Vector3 directionalForward,
            Color unitIntensityFinalColor,
            int punctualLightCount,
            Vector4[] destination,
            out string failure)
        {
            failure = null;
            if (destination == null || destination.Length != VectorCount)
            {
                failure = "destination must contain exactly 2054 float4 vectors";
                return false;
            }
            if (punctualLightCount < 0 ||
                punctualLightCount > MaxPunctualLightCount)
            {
                failure = "punctual light count must be within [0, 256]";
                return false;
            }
            if (!IsFinite(directionalForward) ||
                directionalForward.sqrMagnitude <= 1.0e-8f)
            {
                failure = "directional forward must be finite and nonzero";
                return false;
            }
            if (!IsFinite(unitIntensityFinalColor))
            {
                failure = "directional unit-intensity final color must be finite";
                return false;
            }

            Vector3 normalizedForward = directionalForward.normalized;
            if ((normalizedForward - SourceDirectionalForward).sqrMagnitude >
                1.0e-8f)
            {
                failure =
                    "directional forward does not match the recovered CharInfo_Env source";
                return false;
            }

            Array.Clear(destination, 0, destination.Length);
            destination[DirectionalDirectionVector] = new Vector4(
                normalizedForward.x,
                normalizedForward.y,
                normalizedForward.z,
                0.0f);
            destination[DirectionalColorVector] = new Vector4(
                unitIntensityFinalColor.r * SourceDirectIntensityDividePi,
                unitIntensityFinalColor.g * SourceDirectIntensityDividePi,
                unitIntensityFinalColor.b * SourceDirectIntensityDividePi,
                unitIntensityFinalColor.a * SourceDirectIntensityDividePi);

            float softRadiusRadians =
                SourceDirectSoftRadiusDegrees * Mathf.Deg2Rad;
            destination[DirectionalCustomData2Vector] = new Vector4(
                SourceDirectSpecularIntensity,
                Mathf.Sin(softRadiusRadians),
                Mathf.Cos(softRadiusRadians),
                0.0f);

            for (int lightIndex = 0;
                 lightIndex < punctualLightCount;
                 lightIndex++)
            {
                int record = HeaderVectorCount +
                    lightIndex * VectorsPerPunctualLight;
                // Native selected-consumer order: record[5].w == 0 disables
                // the OBB matrix path; record[3].z == 1 then rejects this
                // CharacterOnly light from the SphereOutside resolver.
                destination[
                    record + PunctualObbFlagsVectorInRecord].w = 0.0f;
                destination[
                    record + PunctualCharacterOnlyVectorInRecord].z = 1.0f;
            }
            return true;
        }

        public static uint[] BuildExpectedWords(Vector4[] vectors)
        {
            if (vectors == null || vectors.Length != VectorCount)
            {
                throw new ArgumentException(
                    "Expected exactly 2054 vectors.",
                    nameof(vectors));
            }
            var words = new uint[VectorCount * 4];
            for (int vectorIndex = 0;
                 vectorIndex < vectors.Length;
                 vectorIndex++)
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

        private static bool IsFinite(Vector3 value)
        {
            return IsFinite(value.x) && IsFinite(value.y) && IsFinite(value.z);
        }

        private static bool IsFinite(Color value)
        {
            return IsFinite(value.r) && IsFinite(value.g) &&
                IsFinite(value.b) && IsFinite(value.a);
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

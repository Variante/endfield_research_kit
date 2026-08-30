using System;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Complete native LightCulling.PrepareCPUData layout for the isolated
    /// Endminf CharInfo fixture: six directional vectors followed by twelve
    /// live, source-backed punctual records and a deliberately cleared tail.
    /// Captured transforms and cache slots are never runtime inputs.
    /// </summary>
    public static class EndfieldRecoveredEndminfFullLightDataContract
    {
        public const int HeaderVectorCount = 6;
        public const int MaxPunctualLightCount = 256;
        public const int VectorsPerPunctualLight = 8;
        public const int EndminfPunctualLightCount = 12;
        public const int VectorCount = HeaderVectorCount +
            MaxPunctualLightCount * VectorsPerPunctualLight;
        public const int SizeBytes = VectorCount * sizeof(float) * 4;

        public static bool TryBuild(
            Vector3 directionalForward,
            Color unitIntensityFinalColor,
            Color sourceDirectColor,
            float sourceDirectIntensityDividePi,
            float exposureAdaptation,
            bool dialogueLightingMode,
            EndfieldHGPreparedOperatorLight[] preparedLights,
            int preparedLightCount,
            EndfieldHGPreparedShadowAssignment[] shadowAssignments,
            int shadowAssignmentCount,
            Vector4[] destination,
            out string failure)
        {
            failure = string.Empty;
            if (destination == null || destination.Length != VectorCount)
            {
                failure = "destination must contain exactly 2054 float4 vectors";
                return false;
            }
            if (preparedLights == null ||
                preparedLightCount != EndminfPunctualLightCount ||
                preparedLights.Length < preparedLightCount)
            {
                failure = "the full Endminf contract requires exactly 12 prepared lights";
                return false;
            }
            if (shadowAssignments == null ||
                shadowAssignmentCount != 2 ||
                shadowAssignments.Length < shadowAssignmentCount)
            {
                failure = "the full Endminf contract requires two same-frame shadow assignments";
                return false;
            }
            if (!TryNormalize(directionalForward, out directionalForward) ||
                !IsFinite(unitIntensityFinalColor) ||
                !IsFinite(sourceDirectColor) ||
                !IsFinite(sourceDirectIntensityDividePi) ||
                sourceDirectIntensityDividePi < 0.0f ||
                !IsFinite(exposureAdaptation) || exposureAdaptation < 0.0f)
            {
                failure = "the recovered directional-light descriptor is invalid";
                return false;
            }
            if ((directionalForward -
                 EndfieldRecoveredDeferredLightDataContract.SourceDirectionalForward)
                .sqrMagnitude > 1.0e-8f)
            {
                failure = "directional forward does not match CharInfo_Env source";
                return false;
            }

            var assignmentByPackedIndex = new int[EndminfPunctualLightCount];
            for (int index = 0; index < assignmentByPackedIndex.Length; index++)
                assignmentByPackedIndex[index] = -1;
            int nextShadowBaseIndex =
                EndfieldRecoveredPunctualShadowProducer.DynamicCacheBase;
            int previousPackedIndex = -1;
            for (int index = 0; index < shadowAssignmentCount; index++)
            {
                EndfieldHGPreparedShadowAssignment assignment = shadowAssignments[index];
                if (assignment.sourceIndex < 0 ||
                    assignment.sourceIndex >= EndminfPunctualLightCount ||
                    assignment.packedIndex < 0 ||
                    assignment.packedIndex >= EndminfPunctualLightCount ||
                    assignment.shadowBaseIndex <
                        EndfieldRecoveredPunctualShadowProducer.DynamicCacheBase ||
                    assignment.shadowBaseIndex >=
                        EndfieldRecoveredPunctualShadowProducer.CacheSlotCount ||
                    (assignment.faceCount != 1 && assignment.faceCount != 6) ||
                    assignment.packedIndex <= previousPackedIndex ||
                    assignment.shadowBaseIndex != nextShadowBaseIndex ||
                    assignment.shadowBaseIndex + assignment.faceCount >
                        EndfieldRecoveredPunctualShadowProducer.CacheSlotCount ||
                    assignmentByPackedIndex[assignment.packedIndex] >= 0)
                {
                    failure = "a shadow assignment has an invalid or duplicate identity";
                    return false;
                }
                assignmentByPackedIndex[assignment.packedIndex] = index;
                previousPackedIndex = assignment.packedIndex;
                nextShadowBaseIndex += assignment.faceCount;
            }

            Array.Clear(destination, 0, destination.Length);
            destination[0] = new Vector4(
                directionalForward.x,
                directionalForward.y,
                directionalForward.z,
                0.0f);
            destination[1] = new Vector4(
                unitIntensityFinalColor.r * sourceDirectIntensityDividePi,
                unitIntensityFinalColor.g * sourceDirectIntensityDividePi,
                unitIntensityFinalColor.b * sourceDirectIntensityDividePi,
                unitIntensityFinalColor.a * sourceDirectIntensityDividePi);

            Color sourceLinear = sourceDirectColor.linear;
            destination[2] = new Vector4(
                sourceLinear.r,
                sourceLinear.g,
                sourceLinear.b,
                sourceDirectIntensityDividePi);
            destination[3] = BuildCharacterLightHeader(
                sourceLinear,
                sourceDirectIntensityDividePi,
                exposureAdaptation,
                dialogueLightingMode);
            float softRadiusRadians =
                EndfieldRecoveredDeferredLightDataContract
                    .SourceDirectSoftRadiusDegrees * Mathf.Deg2Rad;
            destination[4] = new Vector4(
                EndfieldRecoveredDeferredLightDataContract
                    .SourceDirectSpecularIntensity,
                Mathf.Sin(softRadiusRadians),
                Mathf.Cos(softRadiusRadians),
                0.0f);
            // PrepareCPUData copies its uint4 lightMasks argument bitwise into
            // H5. The admitted isolated CharInfo producer supplies uint4(0).
            destination[5] = Vector4.zero;

            var seenSourceIndices = new bool[EndminfPunctualLightCount];
            int consumedAssignments = 0;
            for (int packedIndex = 0;
                 packedIndex < preparedLightCount;
                 packedIndex++)
            {
                EndfieldHGPreparedOperatorLight prepared = preparedLights[packedIndex];
                EndfieldHGOperatorLightData light = prepared.light;
                if (prepared.packedIndex != packedIndex ||
                    prepared.sourceIndex < 0 ||
                    prepared.sourceIndex >= EndminfPunctualLightCount ||
                    seenSourceIndices[prepared.sourceIndex])
                {
                    failure = "the prepared Endminf order contains a duplicate or invalid row";
                    return false;
                }
                seenSourceIndices[prepared.sourceIndex] = true;
                if (!ValidateIsolatedEndminfRow(
                        prepared,
                        out failure))
                {
                    return false;
                }

                int assignmentIndex = assignmentByPackedIndex[packedIndex];
                EndfieldHGPreparedShadowAssignment assignment =
                    assignmentIndex >= 0
                        ? shadowAssignments[assignmentIndex]
                        : default;
                bool hasAssignment = assignmentIndex >= 0;
                if (hasAssignment)
                {
                    if (assignment.sourceIndex != prepared.sourceIndex ||
                        light.shadowType != 2)
                    {
                        failure = "a shadow assignment does not match its prepared source row";
                        return false;
                    }
                    consumedAssignments++;
                }
                else if (light.shadowType != 0)
                {
                    failure = $"shadow-producing row {prepared.sourceIndex} has no same-frame cache assignment";
                    return false;
                }

                int record = HeaderVectorCount +
                    packedIndex * VectorsPerPunctualLight;
                Color finalColor = light.color.linear * light.intensity;
                destination[record + 0] = new Vector4(
                    finalColor.r,
                    finalColor.g,
                    finalColor.b,
                    light.spot
                        ? (light.shadowOnly ? 2.0f : 0.0f)
                        : (light.shadowOnly ? 3.0f : 1.0f));
                destination[record + 1] = new Vector4(
                    prepared.worldPosition.x,
                    prepared.worldPosition.y,
                    prepared.worldPosition.z,
                    1.0f / light.range);

                Vector2 octForward = PackNormalOctRectEncode(prepared.worldForward);
                if (light.spot)
                {
                    float outerCos = Mathf.Cos(
                        0.5f * light.outerSpotAngle * Mathf.Deg2Rad);
                    float innerCos = Mathf.Cos(
                        0.5f * light.innerSpotAngle * Mathf.Deg2Rad);
                    float coneDenominator = innerCos - outerCos;
                    if (!(coneDenominator > 0.0f) || !IsFinite(coneDenominator))
                    {
                        failure = $"spot row {prepared.sourceIndex} has an invalid cone";
                        return false;
                    }
                    if (hasAssignment && assignment.faceCount != 1)
                    {
                        failure = "a spot-light shadow assignment must contain exactly one face";
                        return false;
                    }
                    destination[record + 2] = new Vector4(
                        octForward.x,
                        octForward.y,
                        outerCos,
                        1.0f / coneDenominator);
                    destination[record + 3] = new Vector4(
                        hasAssignment ? assignment.shadowBaseIndex : -1.0f,
                        light.volumetricScatteringIntensity,
                        1.0f,
                        UIntBitsAsFloat(unchecked((uint)light.nprType)));
                }
                else
                {
                    if (hasAssignment && assignment.faceCount != 6)
                    {
                        failure = "a point-light shadow assignment must contain exactly six faces";
                        return false;
                    }
                    uint packed0123 = 0xffffffffu;
                    uint packed45 = 0x0000ffffu;
                    if (hasAssignment)
                    {
                        int baseSlot = assignment.shadowBaseIndex;
                        if (baseSlot + 5 >=
                            EndfieldRecoveredPunctualShadowProducer.CacheSlotCount)
                        {
                            failure = "a point-light shadow assignment exceeds the cache";
                            return false;
                        }
                        packed0123 =
                            ((uint)(baseSlot + 0) << 24) |
                            ((uint)(baseSlot + 1) << 16) |
                            ((uint)(baseSlot + 2) << 8) |
                            (uint)(baseSlot + 3);
                        packed45 =
                            ((uint)(baseSlot + 4) << 8) |
                            (uint)(baseSlot + 5);
                    }
                    destination[record + 2] = new Vector4(
                        octForward.x,
                        octForward.y,
                        light.linearLightLength,
                        UIntBitsAsFloat(packed0123));
                    destination[record + 3] = new Vector4(
                        UIntBitsAsFloat(packed45),
                        light.volumetricScatteringIntensity,
                        1.0f,
                        UIntBitsAsFloat(unchecked((uint)light.nprType)));
                }

                destination[record + 4] = light.nprData;
                destination[record + 5] = Vector4.zero;
                destination[record + 6] = new Vector4(
                    0.0f,
                    0.0f,
                    0.0f,
                    light.falloffExponent);
                destination[record + 7] = new Vector4(
                    light.cullingBoxFalloffThreshold,
                    light.softSourceRadius,
                    light.specularIntensity,
                    -1.0f);
            }

            if (consumedAssignments != shadowAssignmentCount)
            {
                failure = "not every same-frame shadow assignment was consumed";
                return false;
            }
            return true;
        }

        internal static Vector2 PackNormalOctRectEncode(Vector3 value)
        {
            float denominator =
                Mathf.Abs(value.x) + Mathf.Abs(value.y) + Mathf.Abs(value.z);
            Vector3 projected = value / denominator;
            float folded = Mathf.Clamp01(
                0.5f * (1.0f - projected.x + projected.y));
            return new Vector2(
                projected.z < 0.0f ? -Mathf.Abs(folded) : Mathf.Abs(folded),
                projected.x + projected.y);
        }

        internal static Vector4 BuildCharacterLightHeader(
            Color linearColor,
            float originalIntensity,
            float exposureAdaptation,
            bool dialogueLightingMode)
        {
            Color.RGBToHSV(linearColor, out float hue, out float saturation, out _);
            float transition = Mathf.Clamp01(
                (0.45f - Mathf.Abs(hue - 0.5f)) / 0.1f);
            float saturationLimit = 0.7f - 0.35f *
                ((3.0f - 2.0f * transition) * transition * transition);
            float correctedSaturation = Mathf.Min(saturation, saturationLimit);
            Color normalized = Color.HSVToRGB(
                hue,
                correctedSaturation,
                1.0f,
                true);
            float chromaScale =
                (2.0f - saturation) / (2.0f - correctedSaturation);
            float exposedIntensity = originalIntensity * exposureAdaptation;
            float slope = dialogueLightingMode ? 0.05f : 0.25f;
            float intensity =
                Mathf.Clamp(exposedIntensity, 0.75f, 1.25f) +
                slope * Mathf.Max(exposedIntensity - 1.25f, 0.0f) -
                slope * Mathf.Max(0.75f - exposedIntensity, 0.0f);
            return new Vector4(
                normalized.r,
                normalized.g,
                normalized.b,
                chromaScale * intensity);
        }

        private static bool ValidateIsolatedEndminfRow(
            EndfieldHGPreparedOperatorLight prepared,
            out string failure)
        {
            EndfieldHGOperatorLightData light = prepared.light;
            failure = string.Empty;
            if (!light.enabled || !light.characterOnly || light.shadowOnly ||
                !EndfieldHGOperatorLightSemanticFingerprint.Matches(light) ||
                light.enableObbCullingBox || light.enableOverrideShadowLight ||
                light.hasCookie || light.flickerEnabled || light.useColorTemperature ||
                light.useCullingDistance || light.useFarDistanceShow ||
                light.useShadowCullingMatrixOverride ||
                !IsFinite(light.range) || !(light.range > 0.0f) ||
                !IsFinite(light.intensity) || light.intensity < 0.0f ||
                !IsFinite(light.cullingBoxFalloffThreshold) ||
                Mathf.Abs(light.cullingBoxFalloffThreshold - 0.8f) > 1.0e-6f ||
                !IsFinite(light.color) ||
                !IsFinite(light.softSourceRadius) ||
                !IsFinite(light.specularIntensity) ||
                !IsFinite(light.falloffExponent) ||
                !IsFinite(light.volumetricScatteringIntensity) ||
                !IsFinite(light.linearLightLength) ||
                !IsFinite(light.innerSpotAngle) ||
                !IsFinite(light.outerSpotAngle) ||
                !IsFinite(light.nprData) ||
                !TryNormalize(prepared.worldForward, out _) ||
                !IsFinite(prepared.worldPosition) ||
                !IsNormalized(prepared.worldRotation))
            {
                failure = $"Endminf row {prepared.sourceIndex} is outside the isolated native contract";
                return false;
            }
            if (light.shadowType != 0 && light.shadowType != 2)
            {
                failure = $"Endminf row {prepared.sourceIndex} has unsupported shadow type {light.shadowType}";
                return false;
            }
            return true;
        }

        private static bool TryNormalize(Vector3 value, out Vector3 normalized)
        {
            float magnitudeSquared = value.sqrMagnitude;
            if (!(magnitudeSquared > 1.0e-12f) || !IsFinite(magnitudeSquared))
            {
                normalized = Vector3.zero;
                return false;
            }
            normalized = value / Mathf.Sqrt(magnitudeSquared);
            return true;
        }

        private static bool IsNormalized(Quaternion value)
        {
            float magnitudeSquared =
                value.x * value.x + value.y * value.y +
                value.z * value.z + value.w * value.w;
            return IsFinite(magnitudeSquared) &&
                Mathf.Abs(magnitudeSquared - 1.0f) <= 1.0e-4f;
        }

        private static float UIntBitsAsFloat(uint value) =>
            BitConverter.Int32BitsToSingle(unchecked((int)value));

        private static bool IsFinite(Color value) =>
            IsFinite(value.r) && IsFinite(value.g) &&
            IsFinite(value.b) && IsFinite(value.a);

        private static bool IsFinite(Vector3 value) =>
            IsFinite(value.x) && IsFinite(value.y) && IsFinite(value.z);

        private static bool IsFinite(Vector4 value) =>
            IsFinite(value.x) && IsFinite(value.y) &&
            IsFinite(value.z) && IsFinite(value.w);

        private static bool IsFinite(float value) =>
            !float.IsNaN(value) && !float.IsInfinity(value);
    }
}

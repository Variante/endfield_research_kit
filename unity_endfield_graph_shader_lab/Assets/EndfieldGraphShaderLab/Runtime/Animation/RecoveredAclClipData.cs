using System;
using System.Collections.Generic;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    public enum RecoveredAclLoopingPolicy
    {
        Clamp = 0,
        Wrap = 1,
    }

    [Flags]
    public enum RecoveredAclTransformComponentMask
    {
        None = 0,
        Translation = 1,
        Rotation = 2,
        Scale = 4,
    }

    [Serializable]
    public struct RecoveredAclTransformBinding
    {
        public string transformPath;
        public int trackIndex;
        public RecoveredAclTransformComponentMask components;
    }

    /// <summary>
    /// Build-generated, frame-major QVV samples decoded from one validated ACL
    /// transform buffer. This asset is inert: it contains no Animator or
    /// Transform mutation behavior.
    /// </summary>
    [CreateAssetMenu(
        fileName = "RecoveredAclClipData",
        menuName = "Endfield/Character Recovery/Recovered ACL Clip Data")]
    public sealed class RecoveredAclClipData : ScriptableObject
    {
        public const int CurrentSchemaVersion = 1;

        public int schemaVersion = CurrentSchemaVersion;
        public string sourceClipName;
        public string sourceClipJsonSha256;
        public string sourceAclSha256;
        public string decodedSamplesSha256;
        public float sampleRate;
        public float duration;
        public int sampleCount;
        public int trackCount;
        public RecoveredAclLoopingPolicy loopingPolicy;
        public RecoveredAclTransformBinding[] bindings =
            Array.Empty<RecoveredAclTransformBinding>();

        // Frame-major layout: sampleIndex * trackCount + trackIndex.
        public Vector3[] translations = Array.Empty<Vector3>();
        public Quaternion[] rotations = Array.Empty<Quaternion>();
        public Vector3[] scales = Array.Empty<Vector3>();

        public int FlatSampleCount => checked(sampleCount * trackCount);

        public bool TryValidate(out string failure)
        {
            failure = string.Empty;
            if (schemaVersion != CurrentSchemaVersion)
                return Fail("schema version is not supported", out failure);
            if (string.IsNullOrEmpty(sourceClipName))
                return Fail("source clip name is empty", out failure);
            if (!IsSha256(sourceClipJsonSha256) || !IsSha256(sourceAclSha256) ||
                !IsSha256(decodedSamplesSha256))
                return Fail("source clip, ACL, or decoded-sample SHA-256 is malformed", out failure);
            if (!Finite(sampleRate) || sampleRate <= 0f)
                return Fail("sample rate is not positive and finite", out failure);
            if (!Finite(duration) || duration < 0f)
                return Fail("duration is negative or non-finite", out failure);
            if (sampleCount <= 0 || trackCount <= 0)
                return Fail("sample or track count is not positive", out failure);
            if (loopingPolicy != RecoveredAclLoopingPolicy.Clamp &&
                loopingPolicy != RecoveredAclLoopingPolicy.Wrap)
                return Fail("looping policy is not recognized", out failure);

            int expected;
            try
            {
                expected = checked(sampleCount * trackCount);
            }
            catch (OverflowException)
            {
                return Fail("flat sample count overflows Int32", out failure);
            }
            if (translations == null || rotations == null || scales == null ||
                translations.Length != expected || rotations.Length != expected ||
                scales.Length != expected)
                return Fail("QVV arrays do not match sampleCount * trackCount", out failure);

            float lastSampleTime = (sampleCount - 1) / sampleRate;
            float onePastLastSampleTime = sampleCount / sampleRate;
            float timingTolerance = Mathf.Max(1e-5f, 1e-5f * onePastLastSampleTime);
            if (duration + timingTolerance < lastSampleTime ||
                duration > onePastLastSampleTime + timingTolerance)
                return Fail("duration is outside the uniform ACL sample interval", out failure);
            if (loopingPolicy == RecoveredAclLoopingPolicy.Clamp &&
                Mathf.Abs(duration - lastSampleTime) > timingTolerance)
                return Fail("clamped duration does not end on the final ACL sample", out failure);
            if (loopingPolicy == RecoveredAclLoopingPolicy.Wrap && duration <= 0f)
                return Fail("wrapped duration is not positive", out failure);

            var paths = new HashSet<string>(StringComparer.Ordinal);
            var boundTracks = new HashSet<int>();
            if (bindings == null)
                return Fail("bindings are null", out failure);
            foreach (RecoveredAclTransformBinding binding in bindings)
            {
                if (binding.transformPath == null || !paths.Add(binding.transformPath))
                    return Fail("binding path is null or duplicated", out failure);
                if (binding.trackIndex < 0 || binding.trackIndex >= trackCount ||
                    !boundTracks.Add(binding.trackIndex))
                    return Fail("binding track index is outside the payload or duplicated", out failure);
                if (binding.components == RecoveredAclTransformComponentMask.None ||
                    (binding.components & ~(
                        RecoveredAclTransformComponentMask.Translation |
                        RecoveredAclTransformComponentMask.Rotation |
                        RecoveredAclTransformComponentMask.Scale)) != 0)
                    return Fail("binding component mask is empty or malformed", out failure);
            }

            for (int index = 0; index < expected; index++)
            {
                Vector3 translation = translations[index];
                Quaternion rotation = rotations[index];
                Vector3 scale = scales[index];
                if (!Finite(translation.x) || !Finite(translation.y) || !Finite(translation.z) ||
                    !Finite(rotation.x) || !Finite(rotation.y) ||
                    !Finite(rotation.z) || !Finite(rotation.w) ||
                    !Finite(scale.x) || !Finite(scale.y) || !Finite(scale.z))
                    return Fail("QVV payload contains a non-finite component", out failure);
                float rotationLengthSquared = rotation.x * rotation.x +
                    rotation.y * rotation.y + rotation.z * rotation.z +
                    rotation.w * rotation.w;
                if (!Finite(rotationLengthSquared) || rotationLengthSquared <= 0f)
                    return Fail("QVV payload contains a zero quaternion", out failure);
            }
            return true;
        }

        private static bool IsSha256(string value)
        {
            if (value == null || value.Length != 64)
                return false;
            foreach (char character in value)
            {
                bool digit = character >= '0' && character <= '9';
                bool lower = character >= 'a' && character <= 'f';
                bool upper = character >= 'A' && character <= 'F';
                if (!digit && !lower && !upper)
                    return false;
            }
            return true;
        }

        private static bool Finite(float value) =>
            !float.IsNaN(value) && !float.IsInfinity(value);

        private static bool Fail(string message, out string failure)
        {
            failure = message;
            return false;
        }
    }
}

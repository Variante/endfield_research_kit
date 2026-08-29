using UnityEngine;

namespace EndfieldGraphShaderLab
{
    public struct RecoveredAclSampleWindow
    {
        public int lowerIndex;
        public int upperIndex;
        public float alpha;
    }

    public struct RecoveredAclQvvSample
    {
        public Vector3 translation;
        public Quaternion rotation;
        public Vector3 scale;
    }

    /// <summary>
    /// Deterministic sampling primitives for decoded, uniformly sampled ACL
    /// QVV tracks. This evaluator does not read or write scene Transforms.
    /// </summary>
    public static class RecoveredAclPoseEvaluator
    {
        public static bool TryResolveSampleWindow(
            float time,
            float sampleRate,
            float duration,
            int sampleCount,
            RecoveredAclLoopingPolicy loopingPolicy,
            out RecoveredAclSampleWindow window,
            out string failure)
        {
            window = default;
            failure = string.Empty;
            if (!Finite(time) || !Finite(sampleRate) || sampleRate <= 0f ||
                !Finite(duration) || duration < 0f || sampleCount <= 0)
                return Fail("sample-window inputs are malformed", out failure);
            if (loopingPolicy != RecoveredAclLoopingPolicy.Clamp &&
                loopingPolicy != RecoveredAclLoopingPolicy.Wrap)
                return Fail("sample-window looping policy is not recognized", out failure);

            // The pinned runtime only floors a non-negative sample index.
            float effectiveTime = Mathf.Max(0f, time);
            if (loopingPolicy == RecoveredAclLoopingPolicy.Wrap)
            {
                if (duration <= 0f)
                    return Fail("wrapped sample window requires a positive duration", out failure);
                effectiveTime %= duration;
            }
            else
            {
                effectiveTime = Mathf.Min(effectiveTime, duration);
            }

            // Preserve the native operation order: float time * float rate,
            // floor for non-negative input, then clamp or context wrap.
            float sampleIndex = effectiveTime * sampleRate;
            if (!Finite(sampleIndex) || sampleIndex > int.MaxValue)
                return Fail("sample index is outside the supported Int32 range", out failure);
            if (loopingPolicy == RecoveredAclLoopingPolicy.Clamp &&
                sampleIndex >= sampleCount - 1)
            {
                int last = sampleCount - 1;
                window.lowerIndex = last;
                window.upperIndex = last;
                window.alpha = 0f;
                return true;
            }
            int lower = Mathf.FloorToInt(sampleIndex);
            float alpha = sampleIndex - lower;
            if (loopingPolicy == RecoveredAclLoopingPolicy.Wrap)
            {
                lower %= sampleCount;
                window.lowerIndex = lower;
                window.upperIndex = (lower + 1) % sampleCount;
                window.alpha = alpha;
            }
            else
            {
                int last = sampleCount - 1;
                if (lower >= last)
                {
                    window.lowerIndex = last;
                    window.upperIndex = last;
                    window.alpha = 0f;
                }
                else
                {
                    window.lowerIndex = lower;
                    window.upperIndex = lower + 1;
                    window.alpha = alpha;
                }
            }
            return true;
        }

        public static bool TrySampleTrack(
            RecoveredAclClipData clip,
            float time,
            int trackIndex,
            out RecoveredAclQvvSample sample,
            out string failure)
        {
            sample = default;
            failure = string.Empty;
            if (clip == null)
                return Fail("ACL clip data is null", out failure);
            if (trackIndex < 0 || trackIndex >= clip.trackCount)
                return Fail("ACL track index is outside the clip payload", out failure);
            int expected;
            try
            {
                expected = checked(clip.sampleCount * clip.trackCount);
            }
            catch (System.OverflowException)
            {
                return Fail("ACL flat sample count overflows Int32", out failure);
            }
            if (clip.translations == null || clip.rotations == null || clip.scales == null ||
                clip.translations.Length != expected || clip.rotations.Length != expected ||
                clip.scales.Length != expected)
                return Fail("ACL QVV arrays do not match the clip dimensions", out failure);
            if (!TryResolveSampleWindow(
                    time, clip.sampleRate, clip.duration, clip.sampleCount,
                    clip.loopingPolicy, out RecoveredAclSampleWindow window,
                    out failure))
                return false;

            int lower = checked(window.lowerIndex * clip.trackCount + trackIndex);
            int upper = checked(window.upperIndex * clip.trackCount + trackIndex);
            sample.translation = StableVectorLerp(
                clip.translations[lower], clip.translations[upper], window.alpha);
            sample.scale = StableVectorLerp(
                clip.scales[lower], clip.scales[upper], window.alpha);
            if (!Finite(sample.translation) || !Finite(sample.scale))
                return Fail("ACL vector interpolation produced an invalid value", out failure);
            if (!TryStableQuaternionLerp(
                    clip.rotations[lower], clip.rotations[upper], window.alpha,
                    out sample.rotation))
                return Fail("ACL quaternion interpolation produced an invalid value", out failure);
            return true;
        }

        public static Vector3 StableVectorLerp(Vector3 start, Vector3 end, float alpha)
        {
            return new Vector3(
                (start.x - alpha * start.x) + alpha * end.x,
                (start.y - alpha * start.y) + alpha * end.y,
                (start.z - alpha * start.z) + alpha * end.z);
        }

        public static bool TryStableQuaternionLerp(
            Quaternion start,
            Quaternion end,
            float alpha,
            out Quaternion result)
        {
            result = default;
            if (!Finite(start.x) || !Finite(start.y) ||
                !Finite(start.z) || !Finite(start.w) ||
                !Finite(end.x) || !Finite(end.y) ||
                !Finite(end.z) || !Finite(end.w) || !Finite(alpha))
                return false;

            float dot = start.x * end.x + start.y * end.y +
                start.z * end.z + start.w * end.w;
            float bias = dot >= 0f ? 1f : -1f;
            float x = (start.x - alpha * start.x) + alpha * (bias * end.x);
            float y = (start.y - alpha * start.y) + alpha * (bias * end.y);
            float z = (start.z - alpha * start.z) + alpha * (bias * end.z);
            float w = (start.w - alpha * start.w) + alpha * (bias * end.w);
            float lengthSquared = x * x + y * y + z * z + w * w;
            if (!Finite(lengthSquared) || lengthSquared <= 0f)
                return false;
            float inverseLength = 1f / Mathf.Sqrt(lengthSquared);
            result = new Quaternion(
                x * inverseLength,
                y * inverseLength,
                z * inverseLength,
                w * inverseLength);
            return Finite(result.x) && Finite(result.y) &&
                Finite(result.z) && Finite(result.w);
        }

        private static bool Finite(float value) =>
            !float.IsNaN(value) && !float.IsInfinity(value);

        private static bool Finite(Vector3 value) =>
            Finite(value.x) && Finite(value.y) && Finite(value.z);

        private static bool Fail(string message, out string failure)
        {
            failure = message;
            return false;
        }
    }
}

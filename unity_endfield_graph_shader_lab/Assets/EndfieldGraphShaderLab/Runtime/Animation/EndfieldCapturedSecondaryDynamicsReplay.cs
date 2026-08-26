using System;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Replays the bounded, captured Endminf hair/cape trajectory after the
    /// Animator has evaluated. It does not extrapolate or pretend to recover
    /// uncaptured solver state.
    /// </summary>
    [DisallowMultipleComponent]
    [DefaultExecutionOrder(32000)]
    public sealed class EndfieldCapturedSecondaryDynamicsReplay : MonoBehaviour
    {
        public EndfieldCapturedSecondaryDynamicsReplayData data;

        [Tooltip("Source-backed Endminf-only opt-in. Invalid or absent captured data performs no writes.")]
        public bool useCapturedReplay = true;

        public bool BindingValid { get; private set; }
        public string BindingFailure { get; private set; } = "not validated";
        public float PlaybackSeconds { get; private set; }
        public int LowerSampleIndex { get; private set; }
        public int UpperSampleIndex { get; private set; }
        public float SampleBlend { get; private set; }

        private Transform[] bones = Array.Empty<Transform>();
        private EndfieldOverviewPlayback overview;
        private int observedPlaybackGeneration = int.MinValue;
        private bool warned;

        private void OnEnable()
        {
            BindingValid = false;
            BindingFailure = "not validated";
            PlaybackSeconds = 0f;
            observedPlaybackGeneration = int.MinValue;
            warned = false;
        }

        private void LateUpdate()
        {
            if (!useCapturedReplay)
                return;
            if (!BindingValid && !TryBind())
                return;
            if (!overview.AutomaticOverviewPlaybackActive)
                return;

            int generation = overview.PlaybackGeneration;
            if (generation != observedPlaybackGeneration)
            {
                observedPlaybackGeneration = generation;
                PlaybackSeconds = 0f;
            }
            else
            {
                PlaybackSeconds += Mathf.Max(0f, Time.deltaTime);
            }

            ApplyAtSeconds(PlaybackSeconds);
        }

        public bool TryBind()
        {
            BindingValid = false;
            if (!useCapturedReplay)
                return Fail("captured replay is not opted in");
            string failure = "captured replay data is absent";
            if (data == null || !data.Validate(out failure))
                return Fail(failure);

            overview = GetComponent<EndfieldOverviewPlayback>();
            if (overview == null)
                return Fail("EndfieldOverviewPlayback is missing");

            EndfieldSecondaryDynamicsRuntime solver =
                GetComponent<EndfieldSecondaryDynamicsRuntime>();
            if (solver != null && solver.enableUnverifiedSolverWriteback)
                return Fail("captured replay and solver writeback cannot own the same bones");

            bones = new Transform[data.BoneCount];
            for (int index = 0; index < bones.Length; index++)
            {
                bones[index] = transform.Find(data.bonePaths[index]);
                if (bones[index] == null)
                    return Fail("captured replay bone is missing: " + data.bonePaths[index]);
            }

            BindingValid = true;
            BindingFailure = string.Empty;
            return true;
        }

        public void ApplyAtSeconds(float seconds)
        {
            if (!BindingValid && !TryBind())
                return;
            ResolveSample(data.sampleTimes, seconds, out int lower, out int upper, out float blend);
            LowerSampleIndex = lower;
            UpperSampleIndex = upper;
            SampleBlend = blend;

            Matrix4x4 rootToWorld = transform.localToWorldMatrix;
            Quaternion rootRotation = transform.rotation;
            int boneCount = data.BoneCount;
            int lowerOffset = lower * boneCount;
            int upperOffset = upper * boneCount;
            for (int bone = 0; bone < boneCount; bone++)
            {
                Vector3 rootPosition = Vector3.LerpUnclamped(
                    data.rootSpacePositions[lowerOffset + bone],
                    data.rootSpacePositions[upperOffset + bone], blend);
                Quaternion rootBoneRotation = Quaternion.SlerpUnclamped(
                    data.rootSpaceRotations[lowerOffset + bone],
                    data.rootSpaceRotations[upperOffset + bone], blend);
                bones[bone].SetPositionAndRotation(
                    rootToWorld.MultiplyPoint3x4(rootPosition),
                    rootRotation * rootBoneRotation);
            }
        }

        public static void ResolveSample(
            float[] times,
            float seconds,
            out int lower,
            out int upper,
            out float blend)
        {
            if (times == null || times.Length == 0)
                throw new ArgumentException("Replay sample times are empty.", nameof(times));
            if (seconds <= times[0])
            {
                lower = upper = 0;
                blend = 0f;
                return;
            }
            int last = times.Length - 1;
            if (seconds >= times[last])
            {
                lower = upper = last;
                blend = 0f;
                return;
            }

            int left = 0;
            int right = last;
            while (right - left > 1)
            {
                int middle = left + ((right - left) >> 1);
                if (times[middle] <= seconds)
                    left = middle;
                else
                    right = middle;
            }
            lower = left;
            upper = right;
            blend = Mathf.InverseLerp(times[left], times[right], seconds);
        }

        private bool Fail(string failure)
        {
            BindingFailure = failure;
            bones = Array.Empty<Transform>();
            if (!warned)
            {
                warned = true;
                Debug.LogError("Captured secondary-dynamics replay failed closed on " +
                    name + ": " + failure, this);
            }
            return false;
        }
    }
}

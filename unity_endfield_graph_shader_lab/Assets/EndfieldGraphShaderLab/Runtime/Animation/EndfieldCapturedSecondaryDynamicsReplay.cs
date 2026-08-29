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
        public bool PoseAppliedThisFrame { get; private set; }

        private Transform[] bones = Array.Empty<Transform>();
        private Transform[] applicationAnchors = Array.Empty<Transform>();
        private int[] applicationOrder = Array.Empty<int>();
        private EndfieldOverviewPlayback overview;
        private int observedPlaybackGeneration = int.MinValue;
        private float sequenceElapsedSeconds;
        private bool warned;

        private void OnEnable()
        {
            BindingValid = false;
            BindingFailure = "not validated";
            PlaybackSeconds = 0f;
            observedPlaybackGeneration = int.MinValue;
            sequenceElapsedSeconds = 0f;
            warned = false;
            PoseAppliedThisFrame = false;
        }

        private void LateUpdate()
        {
            PoseAppliedThisFrame = false;
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
                sequenceElapsedSeconds = 0f;
            }
            else if (overview.TryGetAutomaticOverviewStartSeconds(
                         out float bodyClipSeconds))
            {
                float bodyClipStartSeconds =
                    data.entranceBodyClipAnchorSeconds -
                    data.entranceSequenceAnchorSeconds;
                sequenceElapsedSeconds = Mathf.Max(
                    0f,
                    bodyClipSeconds - bodyClipStartSeconds);
            }
            else
            {
                // The retained trajectory is a finite retail start-to-loop
                // sequence, so continue its measured timeline across Animator
                // transitions and loop wraps. Do not synthesize a periodic
                // replay after the captured endpoint.
                sequenceElapsedSeconds += Mathf.Max(0f, Time.deltaTime);
            }

            PlaybackSeconds = Mathf.Max(
                0f,
                sequenceElapsedSeconds - data.entranceSequenceAnchorSeconds);
            ApplyAtSeconds(PlaybackSeconds);
            PoseAppliedThisFrame = true;
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
            applicationAnchors = new Transform[data.BoneCount];
            applicationOrder = new int[data.BoneCount];
            for (int index = 0; index < bones.Length; index++)
            {
                bones[index] = transform.Find(data.bonePaths[index]);
                if (bones[index] == null)
                    return Fail("captured replay bone is missing: " + data.bonePaths[index]);
                applicationAnchors[index] = transform.Find(data.applicationAnchorPaths[index]);
                if (applicationAnchors[index] == null)
                    return Fail("captured replay anchor is missing: " +
                        data.applicationAnchorPaths[index]);
                applicationOrder[index] = index;
            }
            Array.Sort(applicationOrder, (left, right) =>
                PathDepth(data.bonePaths[left]).CompareTo(PathDepth(data.bonePaths[right])));

            BindingValid = true;
            BindingFailure = string.Empty;
            return true;
        }

        public void ApplyAtSeconds(float seconds)
        {
            if (!BindingValid && !TryBind())
                return;
            ResolveSample(data.sampleTimes, seconds, out int lower, out int upper, out float blend);
            RejectUncapturedGap(
                data.sampleTimes,
                data.sourceFps,
                seconds,
                ref lower,
                ref upper,
                ref blend);
            LowerSampleIndex = lower;
            UpperSampleIndex = upper;
            SampleBlend = blend;

            int boneCount = data.BoneCount;
            int lowerOffset = lower * boneCount;
            int upperOffset = upper * boneCount;
            for (int order = 0; order < applicationOrder.Length; order++)
            {
                int bone = applicationOrder[order];
                Vector3 anchorPosition = Vector3.LerpUnclamped(
                    data.anchorSpacePositions[lowerOffset + bone],
                    data.anchorSpacePositions[upperOffset + bone], blend);
                Quaternion anchorBoneRotation = Quaternion.SlerpUnclamped(
                    data.anchorSpaceRotations[lowerOffset + bone],
                    data.anchorSpaceRotations[upperOffset + bone], blend);
                Transform anchor = applicationAnchors[bone];
                bones[bone].SetPositionAndRotation(
                    anchor.localToWorldMatrix.MultiplyPoint3x4(anchorPosition),
                    anchor.rotation * anchorBoneRotation);
            }
        }

        public static void RejectUncapturedGap(
            float[] times,
            float sourceFps,
            float seconds,
            ref int lower,
            ref int upper,
            ref float blend)
        {
            if (lower == upper ||
                (times[upper] - times[lower]) * sourceFps <= 1.5f)
                return;

            // Each package contains a measured previous/current pair. A longer
            // interval is an unobserved retail gap, not permission to blend two
            // unrelated absolute poses. Select the nearest measured endpoint.
            if (seconds - times[lower] <= times[upper] - seconds)
                upper = lower;
            else
                lower = upper;
            blend = 0f;
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
            applicationAnchors = Array.Empty<Transform>();
            applicationOrder = Array.Empty<int>();
            if (!warned)
            {
                warned = true;
                Debug.LogError("Captured secondary-dynamics replay failed closed on " +
                    name + ": " + failure, this);
            }
            return false;
        }

        private static int PathDepth(string path)
        {
            int depth = 0;
            for (int index = 0; index < path.Length; index++)
            {
                if (path[index] == '/')
                    depth++;
            }
            return depth;
        }
    }
}

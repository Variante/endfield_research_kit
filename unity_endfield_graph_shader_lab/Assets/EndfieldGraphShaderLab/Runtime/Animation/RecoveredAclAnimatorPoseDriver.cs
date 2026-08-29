using System;
using System.Collections.Generic;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    [Serializable]
    public struct RecoveredAclAnimatorState
    {
        public string fullStatePath;
        public RecoveredAclClipData clip;
    }

    /// <summary>
    /// Publishes source-decoded ACL QVV samples after Animator evaluation and
    /// before the recovered secondary-dynamics PlayerLoop boundary. It contains
    /// no actor-specific paths, poses, positions, or authored smoothing curves.
    /// </summary>
    [DisallowMultipleComponent]
    [DefaultExecutionOrder(-70)]
    public sealed class RecoveredAclAnimatorPoseDriver : MonoBehaviour
    {
        private struct TrackBinding
        {
            public int trackIndex;
            public RecoveredAclTransformComponentMask components;
        }

        private sealed class BoundPath
        {
            public string path;
            public Transform transform;
            public Vector3 referencePosition;
            public Quaternion referenceRotation;
            public Vector3 referenceScale;
            public TrackBinding[] stateTracks;
        }

        public Animator animatorSource;
        [Tooltip("Root used to resolve the source Transform binding paths.")]
        public Transform poseRoot;
        public RecoveredAclAnimatorState[] states =
            Array.Empty<RecoveredAclAnimatorState>();

        public bool BindingValid { get; private set; }
        public string BindingFailure { get; private set; } = "not validated";
        public int AppliedFrameCount { get; private set; }
        public int AppliedTransformCount { get; private set; }
        public int CurrentStateHash { get; private set; }
        public int NextStateHash { get; private set; }
        public float TransitionWeight { get; private set; }

        private readonly Dictionary<int, int> stateIndexByHash =
            new Dictionary<int, int>();
        private BoundPath[] boundPaths = Array.Empty<BoundPath>();

        private void Awake()
        {
            if (animatorSource == null)
                animatorSource = GetComponent<Animator>();
            if (poseRoot == null)
                poseRoot = transform;
            Rebind();
        }

        private void OnEnable()
        {
            if (!BindingValid)
                Rebind();
        }

        public bool Rebind()
        {
            BindingValid = false;
            BindingFailure = string.Empty;
            AppliedFrameCount = 0;
            AppliedTransformCount = 0;
            CurrentStateHash = 0;
            NextStateHash = 0;
            TransitionWeight = 0f;
            stateIndexByHash.Clear();
            boundPaths = Array.Empty<BoundPath>();

            if (animatorSource == null)
                return Fail("Animator source is missing");
            if (poseRoot == null)
                return Fail("pose root is missing");
            if (states == null || states.Length == 0)
                return Fail("no ACL Animator states are configured");

            var paths = new Dictionary<string, BoundPath>(StringComparer.Ordinal);
            for (int stateIndex = 0; stateIndex < states.Length; stateIndex++)
            {
                RecoveredAclAnimatorState state = states[stateIndex];
                if (string.IsNullOrEmpty(state.fullStatePath))
                    return Fail("ACL Animator state path is empty");
                string failure = "clip is missing";
                if (state.clip == null || !state.clip.TryValidate(out failure))
                    return Fail(
                        "ACL clip is missing or invalid for " + state.fullStatePath +
                        ": " + failure);
                if (state.clip.bindings == null || state.clip.bindings.Length == 0)
                    return Fail("ACL clip has no Transform bindings: " + state.clip.name);

                int stateHash = Animator.StringToHash(state.fullStatePath);
                if (stateHash == 0 || stateIndexByHash.ContainsKey(stateHash))
                    return Fail("ACL Animator state hash is zero or duplicated: " +
                        state.fullStatePath);
                stateIndexByHash.Add(stateHash, stateIndex);

                foreach (RecoveredAclTransformBinding binding in state.clip.bindings)
                {
                    if (!paths.TryGetValue(binding.transformPath, out BoundPath path))
                    {
                        Transform target = poseRoot.Find(binding.transformPath);
                        if (target == null)
                            return Fail("ACL Transform binding is unresolved: " +
                                binding.transformPath);
                        path = new BoundPath
                        {
                            path = binding.transformPath,
                            transform = target,
                            referencePosition = target.localPosition,
                            referenceRotation = target.localRotation,
                            referenceScale = target.localScale,
                            stateTracks = new TrackBinding[states.Length],
                        };
                        for (int index = 0; index < path.stateTracks.Length; index++)
                            path.stateTracks[index].trackIndex = -1;
                        paths.Add(binding.transformPath, path);
                    }
                    if (path.stateTracks[stateIndex].trackIndex >= 0)
                        return Fail("ACL Transform path is duplicated within a state: " +
                            binding.transformPath);
                    path.stateTracks[stateIndex] = new TrackBinding
                    {
                        trackIndex = binding.trackIndex,
                        components = binding.components,
                    };
                }
            }

            var ordered = new List<BoundPath>(paths.Values);
            ordered.Sort((left, right) =>
                string.Compare(left.path, right.path, StringComparison.Ordinal));
            boundPaths = ordered.ToArray();
            BindingValid = true;
            BindingFailure = "ok";
            return true;
        }

        private void LateUpdate()
        {
            if (!BindingValid || animatorSource == null ||
                !animatorSource.enabled ||
                animatorSource.runtimeAnimatorController == null)
                return;

            AnimatorStateInfo current = animatorSource.GetCurrentAnimatorStateInfo(0);
            CurrentStateHash = current.fullPathHash;
            if (!stateIndexByHash.TryGetValue(CurrentStateHash, out int currentIndex))
                return;

            bool transitioning = animatorSource.IsInTransition(0);
            if (!transitioning)
            {
                NextStateHash = 0;
                TransitionWeight = 0f;
                ApplySingleState(currentIndex, current.normalizedTime);
                return;
            }

            AnimatorStateInfo next = animatorSource.GetNextAnimatorStateInfo(0);
            NextStateHash = next.fullPathHash;
            if (!stateIndexByHash.TryGetValue(NextStateHash, out int nextIndex))
                return;
            float weight = Mathf.Clamp01(
                animatorSource.GetAnimatorTransitionInfo(0).normalizedTime);
            TransitionWeight = weight;
            ApplyTransition(
                currentIndex, current.normalizedTime,
                nextIndex, next.normalizedTime,
                weight);
        }

        private void ApplySingleState(int stateIndex, float normalizedTime)
        {
            RecoveredAclClipData clip = states[stateIndex].clip;
            float time = ResolveStateTime(clip, normalizedTime);
            int writes = 0;
            foreach (BoundPath path in boundPaths)
            {
                TrackBinding binding = path.stateTracks[stateIndex];
                if (binding.trackIndex < 0)
                    continue;
                if (!RecoveredAclPoseEvaluator.TrySampleTrack(
                        clip, time, binding.trackIndex,
                        out RecoveredAclQvvSample sample, out string failure))
                {
                    FailRuntime(clip, path.path, failure);
                    return;
                }
                ApplyComponents(path.transform, binding.components, sample);
                writes++;
            }
            AppliedTransformCount = writes;
            AppliedFrameCount++;
        }

        private void ApplyTransition(
            int currentIndex,
            float currentNormalizedTime,
            int nextIndex,
            float nextNormalizedTime,
            float weight)
        {
            RecoveredAclClipData currentClip = states[currentIndex].clip;
            RecoveredAclClipData nextClip = states[nextIndex].clip;
            float currentTime = ResolveStateTime(currentClip, currentNormalizedTime);
            float nextTime = ResolveStateTime(nextClip, nextNormalizedTime);
            int writes = 0;

            foreach (BoundPath path in boundPaths)
            {
                TrackBinding currentBinding = path.stateTracks[currentIndex];
                TrackBinding nextBinding = path.stateTracks[nextIndex];
                RecoveredAclTransformComponentMask components =
                    currentBinding.components | nextBinding.components;
                if (components == RecoveredAclTransformComponentMask.None)
                    continue;

                RecoveredAclQvvSample currentSample = ReferenceSample(path);
                RecoveredAclQvvSample nextSample = ReferenceSample(path);
                if (currentBinding.trackIndex >= 0 &&
                    !RecoveredAclPoseEvaluator.TrySampleTrack(
                        currentClip, currentTime, currentBinding.trackIndex,
                        out currentSample, out string currentFailure))
                {
                    FailRuntime(currentClip, path.path, currentFailure);
                    return;
                }
                if (nextBinding.trackIndex >= 0 &&
                    !RecoveredAclPoseEvaluator.TrySampleTrack(
                        nextClip, nextTime, nextBinding.trackIndex,
                        out nextSample, out string nextFailure))
                {
                    FailRuntime(nextClip, path.path, nextFailure);
                    return;
                }

                var blended = new RecoveredAclQvvSample
                {
                    translation = RecoveredAclPoseEvaluator.StableVectorLerp(
                        ComponentValue(
                            currentSample.translation, path.referencePosition,
                            currentBinding.components,
                            RecoveredAclTransformComponentMask.Translation),
                        ComponentValue(
                            nextSample.translation, path.referencePosition,
                            nextBinding.components,
                            RecoveredAclTransformComponentMask.Translation),
                        weight),
                    scale = RecoveredAclPoseEvaluator.StableVectorLerp(
                        ComponentValue(
                            currentSample.scale, path.referenceScale,
                            currentBinding.components,
                            RecoveredAclTransformComponentMask.Scale),
                        ComponentValue(
                            nextSample.scale, path.referenceScale,
                            nextBinding.components,
                            RecoveredAclTransformComponentMask.Scale),
                        weight),
                    rotation = path.referenceRotation,
                };
                Quaternion currentRotation = ComponentValue(
                    currentSample.rotation, path.referenceRotation,
                    currentBinding.components,
                    RecoveredAclTransformComponentMask.Rotation);
                Quaternion nextRotation = ComponentValue(
                    nextSample.rotation, path.referenceRotation,
                    nextBinding.components,
                    RecoveredAclTransformComponentMask.Rotation);
                if (!RecoveredAclPoseEvaluator.TryStableQuaternionLerp(
                        currentRotation, nextRotation, weight,
                        out blended.rotation))
                {
                    FailRuntime(currentClip, path.path,
                        "transition quaternion blend is invalid");
                    return;
                }
                ApplyComponents(path.transform, components, blended);
                writes++;
            }

            AppliedTransformCount = writes;
            AppliedFrameCount++;
        }

        private static float ResolveStateTime(
            RecoveredAclClipData clip,
            float normalizedTime)
        {
            if (clip == null || float.IsNaN(normalizedTime) ||
                float.IsInfinity(normalizedTime))
                return 0f;
            float normalized = clip.loopingPolicy == RecoveredAclLoopingPolicy.Wrap
                ? Mathf.Repeat(normalizedTime, 1f)
                : Mathf.Clamp01(normalizedTime);
            return normalized * clip.duration;
        }

        private static RecoveredAclQvvSample ReferenceSample(BoundPath path)
        {
            return new RecoveredAclQvvSample
            {
                translation = path.referencePosition,
                rotation = path.referenceRotation,
                scale = path.referenceScale,
            };
        }

        private static Vector3 ComponentValue(
            Vector3 sample,
            Vector3 reference,
            RecoveredAclTransformComponentMask components,
            RecoveredAclTransformComponentMask requested)
        {
            return (components & requested) != 0 ? sample : reference;
        }

        private static Quaternion ComponentValue(
            Quaternion sample,
            Quaternion reference,
            RecoveredAclTransformComponentMask components,
            RecoveredAclTransformComponentMask requested)
        {
            return (components & requested) != 0 ? sample : reference;
        }

        private static void ApplyComponents(
            Transform target,
            RecoveredAclTransformComponentMask components,
            RecoveredAclQvvSample sample)
        {
            if ((components & RecoveredAclTransformComponentMask.Translation) != 0)
                target.localPosition = sample.translation;
            if ((components & RecoveredAclTransformComponentMask.Rotation) != 0)
                target.localRotation = sample.rotation;
            if ((components & RecoveredAclTransformComponentMask.Scale) != 0)
                target.localScale = sample.scale;
        }

        private bool Fail(string failure)
        {
            BindingFailure = failure;
            return false;
        }

        private void FailRuntime(
            RecoveredAclClipData clip,
            string path,
            string failure)
        {
            BindingValid = false;
            BindingFailure = "ACL runtime sampling failed: clip=" +
                (clip != null ? clip.sourceClipName : "<null>") +
                " path=" + path + " detail=" + failure;
            Debug.LogError(BindingFailure, this);
        }
    }
}

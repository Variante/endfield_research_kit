using System;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    [CreateAssetMenu(
        fileName = "EndfieldCapturedSecondaryDynamicsReplayData",
        menuName = "Endfield/Character Recovery/Captured Secondary Dynamics Replay Data")]
    public sealed class EndfieldCapturedSecondaryDynamicsReplayData : ScriptableObject
    {
        public const string ExpectedSchema =
            "endfield.charinfo.endminf-dense-captured-secondary-dynamics-oracle.v5";

        public string sourceSchema;
        public string sourceSha256;
        public float sourceFps;
        public int firstReferenceSourceFrame;
        public int playbackReferenceSourceFrame;
        public float entranceBodyClipAnchorSeconds;
        public float entranceSequenceAnchorSeconds;
        public string[] bonePaths = Array.Empty<string>();
        public float[] sampleTimes = Array.Empty<float>();
        public Vector3[] rootSpacePositions = Array.Empty<Vector3>();
        public Quaternion[] rootSpaceRotations = Array.Empty<Quaternion>();
        public bool transparentCapeExtensionObserved;
        public bool transparentCapeExtensionRuntimeEligible;
        public string transparentCapeCaptureSession;
        public string[] transparentCapeAdmissionFailures = Array.Empty<string>();
        public string[] transparentCapeBonePaths = Array.Empty<string>();
        public string[] transparentCapeParentPaths = Array.Empty<string>();
        public int transparentCapeSampleCount;
        public int transparentCapeMaximumSampleGapFrames;
        public int primaryMaximumSampleGapFrames;
        public bool transparentCapeSameSessionPrimaryReplay;

        public int BoneCount => bonePaths == null ? 0 : bonePaths.Length;
        public int SampleCount => sampleTimes == null ? 0 : sampleTimes.Length;

        public bool Validate(out string failure)
        {
            if (!string.Equals(sourceSchema, ExpectedSchema, StringComparison.Ordinal))
            {
                failure = "captured oracle schema is missing or stale";
                return false;
            }
            if (string.IsNullOrEmpty(sourceSha256) || sourceSha256.Length != 64)
            {
                failure = "captured oracle SHA-256 is missing";
                return false;
            }
            if (!IsFinite(sourceFps) || sourceFps <= 0f)
            {
                failure = "captured oracle source FPS is invalid";
                return false;
            }
            if (!IsFinite(entranceBodyClipAnchorSeconds) ||
                entranceBodyClipAnchorSeconds < 0f ||
                !IsFinite(entranceSequenceAnchorSeconds) ||
                entranceSequenceAnchorSeconds < 0f ||
                entranceSequenceAnchorSeconds > entranceBodyClipAnchorSeconds)
            {
                failure = "captured oracle entrance body anchor is invalid";
                return false;
            }
            if (BoneCount == 0 || SampleCount < 2)
            {
                failure = "captured oracle has no replayable bones or samples";
                return false;
            }
            int poseCount = BoneCount * SampleCount;
            if (rootSpacePositions == null || rootSpacePositions.Length != poseCount ||
                rootSpaceRotations == null || rootSpaceRotations.Length != poseCount)
            {
                failure = "captured oracle pose arrays differ from its declared dimensions";
                return false;
            }

            for (int bone = 0; bone < BoneCount; bone++)
            {
                if (string.IsNullOrEmpty(bonePaths[bone]))
                {
                    failure = "captured oracle contains an empty bone path";
                    return false;
                }
                for (int other = 0; other < bone; other++)
                {
                    if (string.Equals(bonePaths[bone], bonePaths[other], StringComparison.Ordinal))
                    {
                        failure = "captured oracle contains duplicate bone paths";
                        return false;
                    }
                }
            }

            for (int sample = 0; sample < SampleCount; sample++)
            {
                float time = sampleTimes[sample];
                if (!IsFinite(time) || (sample > 0 && time <= sampleTimes[sample - 1]))
                {
                    failure = "captured oracle sample times are not finite and strictly increasing";
                    return false;
                }
            }
            for (int pose = 0; pose < poseCount; pose++)
            {
                Vector3 position = rootSpacePositions[pose];
                Quaternion rotation = rootSpaceRotations[pose];
                if (!IsFinite(position.x) || !IsFinite(position.y) || !IsFinite(position.z) ||
                    !IsFinite(rotation.x) || !IsFinite(rotation.y) ||
                    !IsFinite(rotation.z) || !IsFinite(rotation.w) ||
                    Mathf.Abs(1f - Quaternion.Dot(rotation, rotation)) > 1e-3f)
                {
                    failure = "captured oracle contains a non-finite or non-unit pose";
                    return false;
                }
            }

            if (!transparentCapeExtensionObserved ||
                string.IsNullOrEmpty(transparentCapeCaptureSession) ||
                transparentCapeBonePaths == null ||
                transparentCapeParentPaths == null ||
                transparentCapeBonePaths.Length != 6 ||
                transparentCapeParentPaths.Length != 6 ||
                transparentCapeSampleCount < 2 ||
                transparentCapeMaximumSampleGapFrames <= 0 ||
                primaryMaximumSampleGapFrames <= 0)
            {
                failure = "transparent cape extension evidence is missing or malformed";
                return false;
            }
            for (int bone = 0; bone < transparentCapeBonePaths.Length; bone++)
            {
                string path = transparentCapeBonePaths[bone];
                string parent = transparentCapeParentPaths[bone];
                if (string.IsNullOrEmpty(path) || string.IsNullOrEmpty(parent) ||
                    !path.StartsWith(parent + "/", StringComparison.Ordinal) ||
                    Array.IndexOf(bonePaths, path) >= 0)
                {
                    failure = "transparent cape extension ownership is invalid";
                    return false;
                }
            }
            if (transparentCapeExtensionRuntimeEligible ||
                transparentCapeSameSessionPrimaryReplay ||
                transparentCapeAdmissionFailures == null ||
                transparentCapeAdmissionFailures.Length == 0)
            {
                failure = "sparse transparent cape extension was not kept fail-closed";
                return false;
            }

            failure = string.Empty;
            return true;
        }

        private static bool IsFinite(float value) =>
            !float.IsNaN(value) && !float.IsInfinity(value);
    }
}

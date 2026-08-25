using System;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    [CreateAssetMenu(
        fileName = "EndfieldSecondaryDynamicsData",
        menuName = "Endfield/Character Recovery/Secondary Dynamics Data")]
    public sealed class EndfieldSecondaryDynamicsData : ScriptableObject
    {
        [Serializable]
        public struct Owner
        {
            public string ownerPath;
            public string centerTransformPath;
            public string[] proxyTransformPaths;
            public int selectionSampleCount;
            public int proxyVertexCount;
            public int lineCount;
            public int baselineCount;
            public int centerFixedCount;
            public int colliderCount;

            // Source-order proxy-mesh and prebuilt constraint data. These arrays are
            // inert until a separately verified runtime elects to consume them.
            public int[] referenceIndices;
            public byte[] attributes;
            public float[] vertexDepths;
            public int[] vertexRootIndices;
            public int[] vertexParentIndices;
            public Vector3[] vertexLocalPositions;
            public Quaternion[] vertexLocalRotations;
            public Quaternion[] vertexToTransformRotations;
            public byte[] baseLineFlags;
            public ushort[] baseLineStartDataIndices;
            public ushort[] baseLineDataCounts;
            public ushort[] baseLineData;
            public ushort[] centerFixedList;
            public int[] distanceConstraintIndexArray;
            public ushort[] distanceConstraintDataArray;
            public float[] distanceConstraintRestLengths;

            public SolverInputs solverInputs;
        }

        [Serializable]
        public struct SolverInputs
        {
            public bool authoredScalarsRecovered;
            public bool compiledCurveSamplesRecovered;
            public string compiledCurveSamplesBoundary;

            public int normalAxis;
            public float gravity;
            public Vector3 gravityDirection;
            public float gravityFalloff;
            public float animationPoseRatio;

            public float dampingValue;
            public bool dampingUsesCurve;
            public float radiusValue;
            public bool radiusUsesCurve;

            public float inertiaDepth;
            public bool particleSpeedLimitEnabled;
            public float particleSpeedLimit;
            public float centrifugalAcceleration;

            public float tetherDistanceCompression;
            public float distanceStiffnessValue;
            public bool distanceStiffnessUsesCurve;

            public bool angleRestorationEnabled;
            public float angleRestorationStiffnessValue;
            public bool angleRestorationStiffnessUsesCurve;
            public float angleRestorationVelocityAttenuation;
            public float angleRestorationGravityFalloff;
            public bool angleLimitEnabled;
            public float angleLimitValue;
            public bool angleLimitUsesCurve;
            public float angleLimitStiffness;

            public float colliderDynamicFriction;
            public bool springEnabled;
            public float springPower;
            public float springLimitDistance;
            public float springNormalLimitRatio;
            public float springNoise;
        }

        public bool sourceRecovered;
        public string actorKey;
        public TextAsset solverInputs;
        public string solverInputsSha256;
        public TextAsset payloadDecode;
        public string payloadDecodeSha256;
        public Owner[] owners = Array.Empty<Owner>();
        public int expectedBindingCount;
        public int expectedUniqueBindingCount;
        public int expectedOverlappingBindingCount;
    }
}

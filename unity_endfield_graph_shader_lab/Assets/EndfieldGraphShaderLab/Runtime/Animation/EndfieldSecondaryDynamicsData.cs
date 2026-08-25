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

using System;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    [Serializable]
    public struct EndfieldHGOperatorLightData
    {
        public string sourceName;
        public Vector3 position;
        public Quaternion rotation;
        public Vector3 forward;
        public Color color;
        public int priority;
        public bool useColorTemperature;
        public float intensity;
        public bool enabled;
        public float range;
        public bool spot;
        public float outerSpotAngle;
        public float innerSpotAngle;
        public int nprType;
        public Vector4 nprData;
        public bool characterOnly;
        public float volumetricScatteringIntensity;
        public float falloffExponent;
        public float linearLightLength;
        public float softSourceRadius;
        public float specularIntensity;
        public bool useCullingDistance;
        public float cullingDistance;
        public float falloffDistance;
        public float cullingBoxFalloffThreshold;
        public bool useFarDistanceShow;
        public bool enableOverrideShadowLight;
        public int shadowType;
        public float shadowNearPlane;
        public float shadowFarPlane;
        public float shadowBias;
        public float shadowNormalBias;
        public float shadowStrength;
        public float shadowGuardAngle;
        public int shadowCasterProperties;
        public int pointLightShadowCasterFaces;
        public int shadowCustomResolution;
        public int shadowResolution;
        public int shadowPlatformDefault;
        public bool useShadowCullingMatrixOverride;
        public bool shadowOnly;
        public bool enableObbCullingBox;
        public bool hasCookie;
        public bool flickerEnabled;
        public float rimWidth;
        public float rimAlpha;
        public bool hasFollower;
        public bool followerEnabled;
        public int followerMode;
        public int followerBoneType;
        public string followerBoneKey;
        public Vector3 followerPositionOffset;
        public Vector3 followerLocalPosition;
        public Vector3 followerLocalEulerDegrees;
        public long followerSourcePathId;
        public string followerSourcePath;
        public string followerSourceJsonSha256;
        public string followerSourceRawDataSha256;
        public string sourceSemanticSha256;
    }

    public static class EndfieldHGOperatorLightSemanticFingerprint
    {
        public static string Compute(EndfieldHGOperatorLightData value)
        {
            var semantic = new StringBuilder(1024);
            AppendString(semantic, "endfield.operator-light.semantic.v1");
            AppendString(semantic, value.sourceName);
            Append(semantic, value.position);
            Append(semantic, value.rotation);
            Append(semantic, value.forward);
            Append(semantic, value.color);
            Append(semantic, value.priority);
            Append(semantic, value.useColorTemperature);
            Append(semantic, value.intensity);
            Append(semantic, value.enabled);
            Append(semantic, value.range);
            Append(semantic, value.spot);
            Append(semantic, value.outerSpotAngle);
            Append(semantic, value.innerSpotAngle);
            Append(semantic, value.nprType);
            Append(semantic, value.nprData);
            Append(semantic, value.characterOnly);
            Append(semantic, value.volumetricScatteringIntensity);
            Append(semantic, value.falloffExponent);
            Append(semantic, value.linearLightLength);
            Append(semantic, value.softSourceRadius);
            Append(semantic, value.specularIntensity);
            Append(semantic, value.useCullingDistance);
            Append(semantic, value.cullingDistance);
            Append(semantic, value.falloffDistance);
            Append(semantic, value.cullingBoxFalloffThreshold);
            Append(semantic, value.useFarDistanceShow);
            Append(semantic, value.enableOverrideShadowLight);
            Append(semantic, value.shadowType);
            Append(semantic, value.useShadowCullingMatrixOverride);
            Append(semantic, value.shadowOnly);
            Append(semantic, value.enableObbCullingBox);
            Append(semantic, value.hasCookie);
            Append(semantic, value.flickerEnabled);
            Append(semantic, value.hasFollower);
            Append(semantic, value.followerEnabled);
            Append(semantic, value.followerMode);
            Append(semantic, value.followerBoneType);
            AppendString(semantic, value.followerBoneKey);
            Append(semantic, value.followerPositionOffset);
            Append(semantic, value.followerLocalPosition);
            Append(semantic, value.followerLocalEulerDegrees);
            Append(semantic, value.followerSourcePathId);
            AppendString(semantic, value.followerSourceJsonSha256);
            AppendString(semantic, value.followerSourceRawDataSha256);
            byte[] payload = Encoding.UTF8.GetBytes(semantic.ToString());
            using (SHA256 sha = SHA256.Create())
            {
                byte[] digest = sha.ComputeHash(payload);
                var result = new StringBuilder(digest.Length * 2);
                for (int index = 0; index < digest.Length; index++)
                    result.Append(digest[index].ToString("x2"));
                return result.ToString();
            }
        }

        public static bool Matches(EndfieldHGOperatorLightData value) =>
            !string.IsNullOrEmpty(value.sourceSemanticSha256) &&
            string.Equals(
                value.sourceSemanticSha256,
                Compute(value),
                StringComparison.Ordinal);

        private static void Append(StringBuilder destination, bool value) =>
            destination.Append(value ? '1' : '0').Append('|');

        private static void Append(StringBuilder destination, int value) =>
            destination.Append(value.ToString(CultureInfo.InvariantCulture)).Append('|');

        private static void Append(StringBuilder destination, long value) =>
            destination.Append(value.ToString(CultureInfo.InvariantCulture)).Append('|');

        private static void Append(StringBuilder destination, float value) =>
            destination.Append(
                unchecked((uint)BitConverter.SingleToInt32Bits(value)).ToString("x8"))
                .Append('|');

        private static void Append(StringBuilder destination, Vector3 value)
        {
            Append(destination, value.x);
            Append(destination, value.y);
            Append(destination, value.z);
        }

        private static void Append(StringBuilder destination, Vector4 value)
        {
            Append(destination, value.x);
            Append(destination, value.y);
            Append(destination, value.z);
            Append(destination, value.w);
        }

        private static void Append(StringBuilder destination, Quaternion value)
        {
            Append(destination, value.x);
            Append(destination, value.y);
            Append(destination, value.z);
            Append(destination, value.w);
        }

        private static void Append(StringBuilder destination, Color value)
        {
            Append(destination, value.r);
            Append(destination, value.g);
            Append(destination, value.b);
            Append(destination, value.a);
        }

        private static void AppendString(StringBuilder destination, string value)
        {
            string encoded = Convert.ToBase64String(
                Encoding.UTF8.GetBytes(value ?? string.Empty));
            destination.Append(encoded).Append('|');
        }
    }

    internal struct EndfieldHGIsolatedPunctualShadowTarget
    {
        internal string actorKey;
        internal Transform actorRoot;
        internal int sourceIndex;
        internal int packedIndex;
        internal Vector3 worldPosition;
        internal Quaternion worldRotation;
        internal EndfieldHGOperatorLightData light;
    }

    public struct EndfieldHGPreparedOperatorLight
    {
        public int sourceIndex;
        public int packedIndex;
        public EndfieldHGOperatorLightData light;
        public Vector3 worldPosition;
        public Vector3 worldForward;
        public Quaternion worldRotation;
    }

    /// <summary>
    /// Publishes the exact serialized CharInfo light rig through a compact lab
    /// contract. The legacy compatibility scales remain explicit approximations;
    /// the separately gated clustered-NPR subset consumes only source-backed data.
    /// </summary>
    [ExecuteAlways]
    [DisallowMultipleComponent]
    [RequireComponent(typeof(Camera))]
    public sealed class EndfieldHGOperatorLightRig : MonoBehaviour
    {
        // The complete playable roster has up to 13 serialized overview
        // lights (Aglina). Keep a small aligned capacity above that recovered
        // maximum so no source row is truncated when the viewer switches.
        private const int MaxLights = 16;
        internal const int MaxBinnedLights = 256;
        internal const int DescriptorVectorsPerLight = 3;
        internal const int DescriptorVectorCount =
            MaxBinnedLights * DescriptorVectorsPerLight;
        private static readonly int CountId = Shader.PropertyToID("_EndfieldOperatorLightCount");
        private static readonly int PositionRangeId = Shader.PropertyToID("_EndfieldOperatorLightPositionRange");
        private static readonly int ColorIntensityId = Shader.PropertyToID("_EndfieldOperatorLightColorIntensity");
        private static readonly int DirectionTypeId = Shader.PropertyToID("_EndfieldOperatorLightDirectionType");
        private static readonly int SpotNprId = Shader.PropertyToID("_EndfieldOperatorLightSpotNpr");
        private static readonly int NprDataId = Shader.PropertyToID("_EndfieldOperatorLightNprData");
        private static readonly int AdditionalDataId = Shader.PropertyToID("_EndfieldOperatorLightAdditionalData");
        private static readonly int SurfaceDataId = Shader.PropertyToID("_EndfieldOperatorLightSurfaceData");
        private static readonly int SourceFlagsId = Shader.PropertyToID("_EndfieldOperatorLightSourceFlags");
        private static readonly int ContributionScaleId = Shader.PropertyToID("_EndfieldOperatorLightContributionScale");
        private static readonly int RecoveredClusteredNprLightLoopId =
            Shader.PropertyToID("_EndfieldRecoveredClusteredNprLightLoop");
        private static readonly int RecoveredLightBinningAvailableId =
            Shader.PropertyToID("_EndfieldRecoveredLightBinningAvailable");

        [Tooltip("Unrecovered punctual-light equation scale. Keep zero outside explicit diagnostics.")]
        [Range(0.0f, 2.0f)] public float normalLightCompatibilityScale;
        [Tooltip("Unrecovered NPR-rim equation scale. Keep zero outside explicit diagnostics.")]
        [Range(0.0f, 1.0f)] public float rimLightCompatibilityScale;
        [Tooltip("Default-off source-backed punctual CharacterNPR subset. Unsupported terms contribute exactly zero.")]
        public bool sourceBackedClusteredNprLightLoop;
        [Tooltip("Default-off exact 32-pixel XY/2048-slice Z membership for the isolated original overview rig. When disabled, the source-backed shading loop keeps its direct-loop fallback.")]
        public bool sourceBackedLightBinningMembership;
        [Tooltip("Default-off isolated overview producer for Wulfa/Zhuangfy RimLight_2 (5) and Endminf RimLight_2/RimLight_2 (1). It requires the source-backed clustered NPR loop and fails closed if the exact actor, light, atlas, or caster contract is unavailable.")]
        public bool sourceBackedIsolatedPunctualSoftShadowProducer;
        [Tooltip("Source-backed original punctual-shadow quality profile. Only 512 and 1024 are valid recovered base tile sizes; the captured RTX 5080 device default selects 1024.")]
        public int sourceBackedPunctualShadowTileResolution = 1024;
        [Tooltip("Sampled/live recovered actor whose exact Bip001 and Head_Local transforms drive original CharInfoLightFollower rows.")]
        public Transform actorRoot;
        public EndfieldHGOperatorLightData[] lights = Array.Empty<EndfieldHGOperatorLightData>();

        private readonly Vector4[] positionRange = new Vector4[MaxLights];
        private readonly Vector4[] colorIntensity = new Vector4[MaxLights];
        private readonly Vector4[] directionType = new Vector4[MaxLights];
        private readonly Vector4[] spotNpr = new Vector4[MaxLights];
        private readonly Vector4[] nprData = new Vector4[MaxLights];
        private readonly Vector4[] additionalData = new Vector4[MaxLights];
        private readonly Vector4[] surfaceData = new Vector4[MaxLights];
        private readonly Vector4[] sourceFlags = new Vector4[MaxLights];
        private readonly Transform[] resolvedFollowerBones = new Transform[MaxLights];
        private readonly Vector3[] resolvedWorldPositions = new Vector3[MaxLights];
        private readonly Vector3[] resolvedWorldForwards = new Vector3[MaxLights];
        private readonly Quaternion[] resolvedWorldRotations = new Quaternion[MaxLights];
        private readonly int[] packedSourceIndices = new int[MaxLights];
        private Transform resolvedActorRoot;
        private EndfieldHGOperatorLightData[] resolvedLightRows;
        private Camera preparedCamera;
        private int preparedLightCount;
        private uint preparedSerial;

        public void SetRecoveredGachaPublicationState(
            bool clusteredNpr,
            bool binnedMembership,
            bool isolatedSoftShadow)
        {
            sourceBackedClusteredNprLightLoop = clusteredNpr;
            sourceBackedLightBinningMembership =
                clusteredNpr && binnedMembership;
            sourceBackedIsolatedPunctualSoftShadowProducer =
                clusteredNpr && isolatedSoftShadow;
            if (clusteredNpr)
                return;

            preparedCamera = null;
            preparedLightCount = 0;
            preparedSerial = 0;
            PublishGlobalsImmediate(0);
            Shader.SetGlobalFloat(RecoveredLightBinningAvailableId, 0.0f);
        }

        private void InvalidateFollowerBones()
        {
            resolvedActorRoot = null;
            resolvedLightRows = null;
            Array.Clear(resolvedFollowerBones, 0, resolvedFollowerBones.Length);
        }

        private void EnsureFollowerBonesResolved(int count)
        {
            bool cacheIsCurrent =
                resolvedActorRoot == actorRoot && ReferenceEquals(resolvedLightRows, lights);
            if (cacheIsCurrent)
            {
                for (int index = 0; index < count; index++)
                {
                    EndfieldHGOperatorLightData row = lights[index];
                    if (row.hasFollower && row.followerEnabled && resolvedFollowerBones[index] == null)
                    {
                        cacheIsCurrent = false;
                        break;
                    }
                }
            }
            if (cacheIsCurrent)
                return;

            InvalidateFollowerBones();
            if (actorRoot == null)
            {
                throw new InvalidOperationException(
                    "Original CharInfoLightFollower recovery is enabled, but no actor root was bound.");
            }

            Transform[] descendants = actorRoot.GetComponentsInChildren<Transform>(true);
            SkinnedMeshRenderer[] skinnedRenderers =
                actorRoot.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            for (int index = 0; index < count; index++)
            {
                EndfieldHGOperatorLightData row = lights[index];
                if (!row.hasFollower || !row.followerEnabled)
                    continue;

                string expectedBoneKey;
                switch (row.followerBoneType)
                {
                    case 0:
                        expectedBoneKey = "BIP001";
                        break;
                    case 1:
                        expectedBoneKey = "HEAD_LOCAL";
                        break;
                    default:
                        throw new InvalidOperationException(
                            $"Unsupported original follower bone type {row.followerBoneType} " +
                            $"for light row {index} (PathID {row.followerSourcePathId}).");
                }
                if (!string.Equals(
                        row.followerBoneKey,
                        expectedBoneKey,
                        StringComparison.Ordinal))
                {
                    throw new InvalidOperationException(
                        $"Original follower bone provenance mismatch for light row {index}: " +
                        $"type {row.followerBoneType} requires {expectedBoneKey}, " +
                        $"payload supplied {row.followerBoneKey ?? "<null>"}.");
                }

                Transform match = null;
                int matchCount = 0;
                int bestRendererReferences = -1;
                int bestDepth = int.MaxValue;
                int bestCount = 0;
                for (int candidateIndex = 0; candidateIndex < descendants.Length; candidateIndex++)
                {
                    Transform candidate = descendants[candidateIndex];
                    if (candidate != null && string.Equals(
                            candidate.name,
                            row.followerBoneKey,
                            StringComparison.OrdinalIgnoreCase))
                    {
                        matchCount++;
                        int rendererReferences = CountRendererBoneReferences(
                            candidate,
                            skinnedRenderers);
                        int depth = HierarchyDepth(actorRoot, candidate);
                        bool better =
                            rendererReferences > bestRendererReferences ||
                            (rendererReferences == bestRendererReferences &&
                             depth < bestDepth);
                        if (better)
                        {
                            match = candidate;
                            bestRendererReferences = rendererReferences;
                            bestDepth = depth;
                            bestCount = 1;
                        }
                        else if (rendererReferences == bestRendererReferences &&
                                 depth == bestDepth)
                        {
                            bestCount++;
                        }
                    }
                }
                if (match == null || bestCount != 1)
                {
                    throw new InvalidOperationException(
                        $"Could not deterministically resolve original follower bone " +
                        $"{row.followerBoneKey} below actor {actorRoot.name}: " +
                        $"found {matchCount} name matches; best source-skeleton score " +
                        $"references={bestRendererReferences}, depth={bestDepth}, ties={bestCount}. " +
                        $"Light row {index}, follower PathID {row.followerSourcePathId}.");
                }
                resolvedFollowerBones[index] = match;
            }

            resolvedActorRoot = actorRoot;
            resolvedLightRows = lights;
        }

        private static int CountRendererBoneReferences(
            Transform candidate,
            SkinnedMeshRenderer[] renderers)
        {
            int count = 0;
            for (int rendererIndex = 0; rendererIndex < renderers.Length; rendererIndex++)
            {
                SkinnedMeshRenderer renderer = renderers[rendererIndex];
                if (renderer == null)
                    continue;
                if (renderer.rootBone == candidate)
                {
                    count++;
                    continue;
                }
                Transform[] bones = renderer.bones;
                for (int boneIndex = 0; boneIndex < bones.Length; boneIndex++)
                {
                    if (bones[boneIndex] != candidate)
                        continue;
                    count++;
                    break;
                }
            }
            return count;
        }

        private static int HierarchyDepth(Transform root, Transform value)
        {
            int depth = 0;
            Transform current = value;
            while (current != null && current != root)
            {
                depth++;
                current = current.parent;
            }
            return current == root ? depth : int.MaxValue;
        }

        public string BindActorRootAndDescribe(Transform recoveredActorRoot)
        {
            actorRoot = recoveredActorRoot;
            InvalidateFollowerBones();
            int count = Mathf.Min(lights != null ? lights.Length : 0, MaxLights);
            EnsureFollowerBonesResolved(count);

            int followerCount = 0;
            int fixedOffsetCount = 0;
            int parentSpaceCount = 0;
            Transform bip001 = null;
            Transform headLocal = null;
            for (int index = 0; index < count; index++)
            {
                EndfieldHGOperatorLightData row = lights[index];
                if (!row.hasFollower || !row.followerEnabled)
                    continue;
                followerCount++;
                if (row.followerMode == 0)
                    fixedOffsetCount++;
                else if (row.followerMode == 1)
                    parentSpaceCount++;
                if (row.followerBoneType == 0)
                    bip001 = resolvedFollowerBones[index];
                else if (row.followerBoneType == 1)
                    headLocal = resolvedFollowerBones[index];
            }

            return
                $"actor={actorRoot.name}; followers={followerCount} " +
                $"(fixed={fixedOffsetCount}, parent={parentSpaceCount}); " +
                $"BIP001={HierarchyPath(actorRoot, bip001)}; " +
                $"HEAD_LOCAL={HierarchyPath(actorRoot, headLocal)}";
        }

        private static string HierarchyPath(Transform root, Transform value)
        {
            if (value == null)
                return "<unused>";
            string result = value.name;
            Transform current = value.parent;
            while (current != null && current != root)
            {
                result = current.name + "/" + result;
                current = current.parent;
            }
            if (current != root)
                throw new InvalidOperationException(
                    $"Resolved follower bone {value.name} is not below actor root {root.name}.");
            return root.name + "/" + result;
        }

        public void ApplyGlobals()
        {
            Camera camera = GetComponent<Camera>();
            int count = EvaluateAndPack(camera);
            PublishGlobalsImmediate(count);
            preparedCamera = null;
            preparedLightCount = 0;

            // The exact membership buffer is owned and dispatched by the active
            // render pipeline. Immediate/editor publication deliberately keeps
            // the old direct-loop behavior until that per-camera dispatch runs.
            Shader.SetGlobalFloat(RecoveredLightBinningAvailableId, 0.0f);
        }

        internal int PrepareSourceBackedFrame(
            Camera camera,
            CommandBuffer commandBuffer,
            Vector4[] descriptorDestination)
        {
            if (camera == null)
                throw new ArgumentNullException(nameof(camera));
            if (commandBuffer == null)
                throw new ArgumentNullException(nameof(commandBuffer));

            // Invalidate the current publication before any evaluation work so
            // an exception cannot leave an older frame looking current.
            preparedCamera = null;
            preparedLightCount = 0;
            int count = EvaluateAndPack(camera);
            if (descriptorDestination != null)
                BuildBinningDescriptors(camera, count, descriptorDestination);
            PublishGlobals(commandBuffer, count);
            preparedCamera = camera;
            preparedLightCount = count;
            unchecked
            {
                preparedSerial++;
                if (preparedSerial == 0)
                    preparedSerial = 1;
            }
            return count;
        }

        internal bool TryCopyPreparedSourceBackedFrame(
            Camera camera,
            EndfieldHGPreparedOperatorLight[] destination,
            out int count,
            out uint serial,
            out string failure)
        {
            if (!TryGetPreparedFrameIdentity(
                    camera,
                    out count,
                    out serial,
                    out failure))
                return false;
            if (destination == null || destination.Length < preparedLightCount)
            {
                failure = $"destination must hold at least {preparedLightCount} prepared lights";
                return false;
            }

            var seen = new bool[MaxLights];
            for (int packedIndex = 0; packedIndex < preparedLightCount; packedIndex++)
            {
                int sourceIndex = packedSourceIndices[packedIndex];
                if (sourceIndex < 0 || sourceIndex >= lights.Length || seen[sourceIndex])
                {
                    failure = "the prepared light order contains a duplicate or invalid source index";
                    return false;
                }
                seen[sourceIndex] = true;

                Vector3 worldPosition = resolvedWorldPositions[sourceIndex];
                Vector3 worldForward = resolvedWorldForwards[sourceIndex];
                Quaternion worldRotation = resolvedWorldRotations[sourceIndex];
                if (!IsFinite(worldPosition) || !IsFinite(worldForward) ||
                    worldForward.sqrMagnitude <= 1.0e-12f ||
                    !TryNormalizeQuaternion(worldRotation, out worldRotation))
                {
                    failure = $"prepared light row {sourceIndex} has a non-finite transform";
                    return false;
                }

                destination[packedIndex] = new EndfieldHGPreparedOperatorLight
                {
                    sourceIndex = sourceIndex,
                    packedIndex = packedIndex,
                    light = lights[sourceIndex],
                    worldPosition = worldPosition,
                    worldForward = worldForward.normalized,
                    worldRotation = worldRotation
                };
            }

            count = preparedLightCount;
            serial = preparedSerial;
            return true;
        }

        internal bool TryGetPreparedFrameIdentity(
            Camera camera,
            out int count,
            out uint serial,
            out string failure)
        {
            count = 0;
            serial = 0;
            failure = string.Empty;
            if (!sourceBackedClusteredNprLightLoop)
            {
                failure = "the source-backed clustered NPR light loop must be enabled";
                return false;
            }
            if (camera == null || preparedCamera != camera || preparedSerial == 0)
            {
                failure = "the source-backed light frame was not prepared for this camera";
                return false;
            }
            if (actorRoot == null || lights == null ||
                preparedLightCount <= 0 || preparedLightCount != lights.Length ||
                preparedLightCount > MaxLights)
            {
                failure = "the prepared source-backed light identity is incomplete";
                return false;
            }
            count = preparedLightCount;
            serial = preparedSerial;
            return true;
        }

        internal bool TryGetIsolatedPunctualSoftShadowTarget(
            Camera camera,
            out EndfieldHGIsolatedPunctualShadowTarget target,
            out string failure,
            int endminfSourceIndex = 11)
        {
            target = default;
            failure = string.Empty;
            if (!sourceBackedIsolatedPunctualSoftShadowProducer)
            {
                failure = "the isolated punctual soft-shadow selector is disabled";
                return false;
            }
            if (!sourceBackedClusteredNprLightLoop)
            {
                failure = "the required source-backed clustered NPR light loop is disabled";
                return false;
            }
            if (camera == null || preparedCamera != camera)
            {
                failure = "the source-backed light frame was not prepared for this camera";
                return false;
            }
            if (sourceBackedPunctualShadowTileResolution != 512 &&
                sourceBackedPunctualShadowTileResolution != 1024)
            {
                failure =
                    $"unsupported punctual-shadow base tile resolution " +
                    $"{sourceBackedPunctualShadowTileResolution}; expected 512 or 1024";
                return false;
            }
            if (actorRoot == null)
            {
                failure = "no recovered actor root is bound";
                return false;
            }

            string actorKey;
            int expectedLightCount;
            int sourceIndex;
            if (string.Equals(actorRoot.name, "Wulfa", StringComparison.OrdinalIgnoreCase))
            {
                actorKey = "wulfa";
                expectedLightCount = 8;
                sourceIndex = 4;
            }
            else if (string.Equals(
                         actorRoot.name,
                         "Zhuangfy",
                         StringComparison.OrdinalIgnoreCase))
            {
                actorKey = "zhuangfy";
                expectedLightCount = 6;
                sourceIndex = 4;
            }
            else if (string.Equals(
                         actorRoot.name,
                         "Endminf",
                         StringComparison.OrdinalIgnoreCase))
            {
                actorKey = "endminf";
                expectedLightCount = 12;
                if (endminfSourceIndex != 3 && endminfSourceIndex != 11)
                {
                    failure = $"unsupported Endminf soft-rim source row {endminfSourceIndex}";
                    return false;
                }
                sourceIndex = endminfSourceIndex;
            }
            else
            {
                failure =
                    $"actor identity '{actorRoot.name}' is not an isolated punctual-shadow contract";
                return false;
            }

            if (lights == null || lights.Length != expectedLightCount ||
                preparedLightCount != expectedLightCount)
            {
                failure =
                    $"{actorKey} light-list identity mismatch: expected {expectedLightCount} " +
                    $"prepared rows, found {preparedLightCount}";
                return false;
            }

            EndfieldHGOperatorLightData row = lights[sourceIndex];
            if (!MatchesIsolatedPunctualSoftShadowContract(
                    actorKey,
                    sourceIndex,
                    row,
                    out failure))
                return false;

            int packedIndex = -1;
            for (int index = 0; index < preparedLightCount; index++)
            {
                if (packedSourceIndices[index] == sourceIndex)
                {
                    packedIndex = index;
                    break;
                }
            }
            if (packedIndex < 0)
            {
                failure = $"{actorKey} {row.sourceName} is absent from the prepared light order";
                return false;
            }

            Vector3 worldPosition = resolvedWorldPositions[sourceIndex];
            Quaternion worldRotation = resolvedWorldRotations[sourceIndex];
            if (!IsFinite(worldPosition) || !TryNormalizeQuaternion(worldRotation, out worldRotation))
            {
                failure = $"{actorKey} {row.sourceName} resolved to a non-finite transform";
                return false;
            }

            target = new EndfieldHGIsolatedPunctualShadowTarget
            {
                actorKey = actorKey,
                actorRoot = actorRoot,
                sourceIndex = sourceIndex,
                packedIndex = packedIndex,
                worldPosition = worldPosition,
                worldRotation = worldRotation,
                light = row
            };
            return true;
        }

        private static bool MatchesIsolatedPunctualSoftShadowContract(
            string actorKey,
            int sourceIndex,
            EndfieldHGOperatorLightData row,
            out string failure)
        {
            failure = string.Empty;
            string expectedName = actorKey == "endminf"
                ? sourceIndex == 3 ? "RimLight_2" : "RimLight_2 (1)"
                : "RimLight_2 (5)";
            float expectedFarPlane = actorKey == "endminf"
                ? sourceIndex == 3 ? 0.7f : 0.55f
                : 0.76f;
            bool common =
                string.Equals(row.sourceName, expectedName, StringComparison.Ordinal) &&
                row.enabled && row.characterOnly && row.nprType == 3 && row.shadowType == 2 &&
                !row.shadowOnly && !row.enableObbCullingBox && !row.hasCookie &&
                !row.flickerEnabled && !row.useColorTemperature && !row.useCullingDistance &&
                SameFloat(row.linearLightLength, -1.0f) &&
                SameFloat(row.softSourceRadius, 0.0f) &&
                SameFloat(row.shadowNearPlane, 0.2f) &&
                SameFloat(row.shadowFarPlane, expectedFarPlane) &&
                SameFloat(row.shadowBias, 0.05f) &&
                SameFloat(row.shadowNormalBias, 0.4f) &&
                SameFloat(row.shadowStrength, 1.0f) &&
                SameFloat(row.shadowGuardAngle, 0.0f) &&
                row.shadowCasterProperties == 6 &&
                row.pointLightShadowCasterFaces == -1 &&
                row.shadowCustomResolution == -1 && row.shadowResolution == -1 &&
                row.shadowPlatformDefault == 2 && !row.useShadowCullingMatrixOverride &&
                SameFloat(row.nprData.z, 0.0f) && SameFloat(row.nprData.w, 0.0f);
            if (!common)
            {
                failure = $"{actorKey} rim row no longer matches the serialized soft Rim contract";
                return false;
            }

            if (actorKey == "wulfa")
            {
                bool wulfa =
                    row.spot && SameFloat(row.range, 0.76f) &&
                    SameFloat(row.outerSpotAngle, 108.36655f) &&
                    SameVector4(row.nprData, new Vector4(0.3f, 0.9f, 0.0f, 0.0f)) &&
                    SameQuaternion(
                        row.rotation,
                        new Quaternion(-0.021831237f, 0.7911832f, -0.56646883f, 0.2294901f)) &&
                    row.hasFollower && row.followerEnabled && row.followerMode == 0 &&
                    row.followerBoneType == 0 &&
                    string.Equals(row.followerBoneKey, "BIP001", StringComparison.Ordinal) &&
                    SameVector3(
                        row.followerPositionOffset,
                        new Vector3(-0.2643397f, 0.9243164f, -0.040226698f));
                if (!wulfa)
                {
                    failure = "Wulfa row 4 light/follower identity no longer matches installed data";
                    return false;
                }
            }
            else if (actorKey == "zhuangfy")
            {
                bool zhuangfy =
                    !row.spot && SameFloat(row.range, 0.5296414f) &&
                    SameVector4(row.nprData, new Vector4(0.5f, 0.8f, 0.0f, 0.0f)) &&
                    SameVector3(row.position, new Vector3(-0.397f, 1.8294373f, 0.242f)) &&
                    SameQuaternion(
                        row.rotation,
                        new Quaternion(-0.2570091f, 0.76333225f, -0.44640762f, 0.38985953f)) &&
                    !row.hasFollower;
                if (!zhuangfy)
                {
                    failure = "Zhuangfy row 4 point-light identity no longer matches installed data";
                    return false;
                }
            }
            else
            {
                bool endminf = sourceIndex == 3
                    ? row.spot && SameFloat(row.range, 0.7f) &&
                      SameFloat(row.outerSpotAngle, 85.20261f) &&
                      SameVector4(row.nprData, new Vector4(0.3f, 0.4f, 0.0f, 0.0f)) &&
                      SameVector3(row.position, new Vector3(-0.593f, 0.943f, 0.422f)) &&
                      SameQuaternion(
                          row.rotation,
                          new Quaternion(0.0f, 0.76840407f, 0.0f, 0.63996506f)) &&
                      !row.hasFollower
                    : row.spot && SameFloat(row.range, 0.55f) &&
                      SameFloat(row.outerSpotAngle, 166.96637f) &&
                      SameVector4(row.nprData, new Vector4(0.569f, 0.5f, 0.0f, 0.0f)) &&
                      SameVector3(row.position, new Vector3(-0.424f, 1.684f, -0.136f)) &&
                      SameQuaternion(
                          row.rotation,
                          new Quaternion(0.10568979f, 0.67250973f, -0.17864475f, 0.7103847f)) &&
                      !row.hasFollower;
                if (!endminf)
                {
                    failure = $"Endminf row {sourceIndex} light identity no longer matches installed data";
                    return false;
                }
            }

            return true;
        }

        private int EvaluateAndPack(Camera camera)
        {
            int count = Mathf.Min(lights != null ? lights.Length : 0, MaxLights);
            if (sourceBackedClusteredNprLightLoop)
                EnsureFollowerBonesResolved(count);
            Vector3 cameraPosition = camera != null ? camera.transform.position : transform.position;
            bool requireExactSourceRotation =
                sourceBackedClusteredNprLightLoop && sourceBackedLightBinningMembership;
            for (int sourceIndex = 0; sourceIndex < count; sourceIndex++)
            {
                EndfieldHGOperatorLightData sourceLight = lights[sourceIndex];
                Vector3 worldPosition = sourceLight.position;
                Vector3 worldForward = sourceLight.forward;
                Quaternion worldRotation;
                bool hasSourceRotation = TryNormalizeQuaternion(
                    sourceLight.rotation,
                    out worldRotation);
                bool usesSourceRotation =
                    !sourceLight.hasFollower ||
                    !sourceLight.followerEnabled ||
                    sourceLight.followerMode == 0;
                if (!hasSourceRotation)
                {
                    if (requireExactSourceRotation && usesSourceRotation)
                    {
                        throw new InvalidOperationException(
                            $"Original light row {sourceIndex} has no valid source rotation. " +
                            "Exact Spot membership must consume rotation_xyzw; it cannot invent roll from forward.");
                    }
                    worldRotation = Quaternion.identity;
                }
                else
                {
                    worldForward = worldRotation * Vector3.forward;
                }
                if (
                    sourceBackedClusteredNprLightLoop &&
                    sourceLight.hasFollower &&
                    sourceLight.followerEnabled)
                {
                    Transform bone = resolvedFollowerBones[sourceIndex];
                    switch (sourceLight.followerMode)
                    {
                        case 0:
                            worldPosition = bone.position + sourceLight.followerPositionOffset;
                            break;
                        case 1:
                            worldRotation =
                                bone.rotation * Quaternion.Euler(sourceLight.followerLocalEulerDegrees);
                            if (!TryNormalizeQuaternion(worldRotation, out worldRotation))
                            {
                                throw new InvalidOperationException(
                                    $"Original follower mode 1 produced an invalid rotation for " +
                                    $"light row {sourceIndex} (PathID {sourceLight.followerSourcePathId}).");
                            }
                            worldPosition =
                                bone.position + bone.rotation * sourceLight.followerLocalPosition;
                            worldForward = worldRotation * Vector3.forward;
                            break;
                        default:
                            throw new InvalidOperationException(
                                $"Unsupported original follower mode {sourceLight.followerMode} " +
                                $"for light row {sourceIndex} (PathID {sourceLight.followerSourcePathId}).");
                    }
                }
                resolvedWorldPositions[sourceIndex] = worldPosition;
                resolvedWorldForwards[sourceIndex] = worldForward;
                resolvedWorldRotations[sourceIndex] = worldRotation;
                packedSourceIndices[sourceIndex] = sourceIndex;
            }

            if (sourceBackedClusteredNprLightLoop)
            {
                // Native HGRP compares priority descending, then camera distance^2
                // ascending. It defines no tie-break, so equal rows compare equal.
                for (int destination = 1; destination < count; destination++)
                {
                    int sourceIndex = packedSourceIndices[destination];
                    int insert = destination;
                    while (insert > 0 && ComesBefore(
                               sourceIndex,
                               packedSourceIndices[insert - 1],
                               cameraPosition))
                    {
                        packedSourceIndices[insert] = packedSourceIndices[insert - 1];
                        insert--;
                    }
                    packedSourceIndices[insert] = sourceIndex;
                }
            }
            for (int index = 0; index < MaxLights; index++)
            {
                if (index >= count)
                {
                    positionRange[index] = Vector4.zero;
                    colorIntensity[index] = Vector4.zero;
                    directionType[index] = Vector4.zero;
                    spotNpr[index] = Vector4.zero;
                    nprData[index] = Vector4.zero;
                    additionalData[index] = Vector4.zero;
                    surfaceData[index] = Vector4.zero;
                    sourceFlags[index] = Vector4.zero;
                    continue;
                }

                int sourceIndex = sourceBackedClusteredNprLightLoop
                    ? packedSourceIndices[index]
                    : index;
                EndfieldHGOperatorLightData light = lights[sourceIndex];
                Vector3 worldPosition = resolvedWorldPositions[sourceIndex];
                Vector3 worldForward = resolvedWorldForwards[sourceIndex];
                Vector3 forward = worldForward.sqrMagnitude > 1e-6f
                    ? worldForward.normalized
                    : Vector3.forward;
                positionRange[index] = new Vector4(
                    worldPosition.x,
                    worldPosition.y,
                    worldPosition.z,
                    Mathf.Max(light.range, 1e-4f));
                colorIntensity[index] = new Vector4(
                    light.color.r,
                    light.color.g,
                    light.color.b,
                    light.enabled ? Mathf.Max(light.intensity, 0.0f) : 0.0f);
                directionType[index] = new Vector4(
                    forward.x,
                    forward.y,
                    forward.z,
                    light.spot ? 1.0f : 0.0f);
                spotNpr[index] = new Vector4(
                    Mathf.Cos(light.outerSpotAngle * 0.5f * Mathf.Deg2Rad),
                    Mathf.Cos(light.innerSpotAngle * 0.5f * Mathf.Deg2Rad),
                    light.nprType,
                    light.rimWidth * light.rimAlpha);
                nprData[index] = light.nprData;
                additionalData[index] = new Vector4(
                    light.characterOnly ? 1.0f : 0.0f,
                    light.volumetricScatteringIntensity,
                    light.falloffExponent,
                    !light.enabled || light.useCullingDistance ? 1.0f : 0.0f);
                surfaceData[index] = new Vector4(
                    light.linearLightLength,
                    light.softSourceRadius,
                    light.specularIntensity,
                    light.shadowType);
                sourceFlags[index] = new Vector4(
                    light.shadowOnly ? 1.0f : 0.0f,
                    light.enableObbCullingBox ? 1.0f : 0.0f,
                    light.hasCookie ? 1.0f : 0.0f,
                    light.flickerEnabled || light.useColorTemperature ? 1.0f : 0.0f);
            }

            return count;
        }

        private void BuildBinningDescriptors(
            Camera camera,
            int count,
            Vector4[] destination)
        {
            if (!sourceBackedClusteredNprLightLoop ||
                !sourceBackedLightBinningMembership)
            {
                throw new InvalidOperationException(
                    "Binning descriptors were requested while exact isolated-rig membership was disabled.");
            }
            if (destination.Length < DescriptorVectorCount)
            {
                throw new ArgumentException(
                    $"Expected at least {DescriptorVectorCount} descriptor vectors.",
                    nameof(destination));
            }

            Array.Clear(destination, 0, destination.Length);
            Matrix4x4 worldToView = camera.worldToCameraMatrix;
            for (int packedIndex = 0; packedIndex < count; packedIndex++)
            {
                int sourceIndex = packedSourceIndices[packedIndex];
                EndfieldHGOperatorLightData light = lights[sourceIndex];
                if (light.enableObbCullingBox)
                {
                    throw new InvalidOperationException(
                        $"Light row {sourceIndex} enables an authored OBB, whose serialized " +
                        "center/extents are outside the isolated overview payload. Refusing to substitute " +
                        "the implicit Spot proxy.");
                }

                Vector3 worldPosition = resolvedWorldPositions[sourceIndex];
                Vector3 worldForward = NormalizeVectorOrThrow(
                    resolvedWorldForwards[sourceIndex],
                    $"light row {sourceIndex} forward");
                float range = light.range;
                Vector3 sphereCenter = worldPosition;
                float sphereRadius = range;

                int descriptorBase = packedIndex * DescriptorVectorsPerLight;
                if (!light.spot)
                {
                    Vector3 pointCenterView = worldToView.MultiplyPoint(worldPosition);
                    destination[descriptorBase] = new Vector4(
                        pointCenterView.x,
                        pointCenterView.y,
                        pointCenterView.z,
                        sphereRadius);
                    continue;
                }

                float coneTangent = Mathf.Tan(
                    light.outerSpotAngle * 0.5f * Mathf.Deg2Rad);
                if (light.outerSpotAngle > 90.0f)
                {
                    sphereRadius = coneTangent * range;
                    sphereCenter = worldPosition + worldForward * range;
                }
                else
                {
                    sphereRadius = 0.5f * range * (1.0f + coneTangent * coneTangent);
                    sphereCenter = worldPosition + worldForward * sphereRadius;
                }

                Vector3 sphereCenterView = worldToView.MultiplyPoint(sphereCenter);
                destination[descriptorBase] = new Vector4(
                    sphereCenterView.x,
                    sphereCenterView.y,
                    sphereCenterView.z,
                    sphereRadius);

                Quaternion worldRotation = resolvedWorldRotations[sourceIndex];
                Vector3 axis0 = NormalizeVectorOrThrow(
                    worldToView.MultiplyVector(worldRotation * Vector3.right),
                    $"light row {sourceIndex} view right");
                Vector3 axis1 = NormalizeVectorOrThrow(
                    worldToView.MultiplyVector(worldRotation * Vector3.up),
                    $"light row {sourceIndex} view up");
                Vector3 obbCenterView = worldToView.MultiplyPoint(
                    worldPosition + worldForward * (range * 0.5f));
                float halfWidth = coneTangent * range;
                Vector3 halfExtents = new Vector3(
                    halfWidth,
                    halfWidth,
                    range * 0.5f);

                destination[descriptorBase + 1] = new Vector4(
                    PackHalf2(1.0f, axis0.x),
                    PackHalf2(axis0.y, axis0.z),
                    PackHalf2(axis1.x, axis1.y),
                    PackHalf2(axis1.z, halfExtents.x));
                destination[descriptorBase + 2] = new Vector4(
                    obbCenterView.x,
                    obbCenterView.y,
                    obbCenterView.z,
                    PackHalf2(halfExtents.y, halfExtents.z));
            }
        }

        private void PublishGlobalsImmediate(int count)
        {

            Shader.SetGlobalInt(CountId, count);
            Shader.SetGlobalVectorArray(PositionRangeId, positionRange);
            Shader.SetGlobalVectorArray(ColorIntensityId, colorIntensity);
            Shader.SetGlobalVectorArray(DirectionTypeId, directionType);
            Shader.SetGlobalVectorArray(SpotNprId, spotNpr);
            Shader.SetGlobalVectorArray(NprDataId, nprData);
            Shader.SetGlobalVectorArray(AdditionalDataId, additionalData);
            Shader.SetGlobalVectorArray(SurfaceDataId, surfaceData);
            Shader.SetGlobalVectorArray(SourceFlagsId, sourceFlags);
            Shader.SetGlobalVector(
                ContributionScaleId,
                new Vector4(normalLightCompatibilityScale, rimLightCompatibilityScale, 0.0f, 0.0f));
            Shader.SetGlobalFloat(
                RecoveredClusteredNprLightLoopId,
                sourceBackedClusteredNprLightLoop ? 1.0f : 0.0f);
        }

        private void PublishGlobals(CommandBuffer commandBuffer, int count)
        {
            commandBuffer.SetGlobalInt(CountId, count);
            commandBuffer.SetGlobalVectorArray(PositionRangeId, positionRange);
            commandBuffer.SetGlobalVectorArray(ColorIntensityId, colorIntensity);
            commandBuffer.SetGlobalVectorArray(DirectionTypeId, directionType);
            commandBuffer.SetGlobalVectorArray(SpotNprId, spotNpr);
            commandBuffer.SetGlobalVectorArray(NprDataId, nprData);
            commandBuffer.SetGlobalVectorArray(AdditionalDataId, additionalData);
            commandBuffer.SetGlobalVectorArray(SurfaceDataId, surfaceData);
            commandBuffer.SetGlobalVectorArray(SourceFlagsId, sourceFlags);
            commandBuffer.SetGlobalVector(
                ContributionScaleId,
                new Vector4(
                    normalLightCompatibilityScale,
                    rimLightCompatibilityScale,
                    0.0f,
                    0.0f));
            commandBuffer.SetGlobalFloat(
                RecoveredClusteredNprLightLoopId,
                sourceBackedClusteredNprLightLoop ? 1.0f : 0.0f);
        }

        private static Vector3 NormalizeVectorOrThrow(Vector3 value, string label)
        {
            float magnitudeSquared = value.sqrMagnitude;
            if (!(magnitudeSquared > 1e-12f) ||
                float.IsNaN(magnitudeSquared) ||
                float.IsInfinity(magnitudeSquared))
            {
                throw new InvalidOperationException(
                    $"Exact recovered light binning received an invalid {label}.");
            }
            return value / Mathf.Sqrt(magnitudeSquared);
        }

        private static bool SameFloat(float value, float expected)
        {
            float tolerance = Mathf.Max(1e-7f, Mathf.Abs(expected) * 1e-6f);
            return !float.IsNaN(value) && !float.IsInfinity(value) &&
                   Mathf.Abs(value - expected) <= tolerance;
        }

        private static bool SameVector3(Vector3 value, Vector3 expected) =>
            SameFloat(value.x, expected.x) &&
            SameFloat(value.y, expected.y) &&
            SameFloat(value.z, expected.z);

        private static bool SameVector4(Vector4 value, Vector4 expected) =>
            SameFloat(value.x, expected.x) &&
            SameFloat(value.y, expected.y) &&
            SameFloat(value.z, expected.z) &&
            SameFloat(value.w, expected.w);

        private static bool SameQuaternion(Quaternion value, Quaternion expected) =>
            SameFloat(value.x, expected.x) &&
            SameFloat(value.y, expected.y) &&
            SameFloat(value.z, expected.z) &&
            SameFloat(value.w, expected.w);

        private static bool IsFinite(Vector3 value) =>
            !float.IsNaN(value.x) && !float.IsInfinity(value.x) &&
            !float.IsNaN(value.y) && !float.IsInfinity(value.y) &&
            !float.IsNaN(value.z) && !float.IsInfinity(value.z);

        private static bool TryNormalizeQuaternion(
            Quaternion value,
            out Quaternion normalized)
        {
            float magnitudeSquared =
                value.x * value.x + value.y * value.y +
                value.z * value.z + value.w * value.w;
            if (!(magnitudeSquared > 1e-12f) ||
                float.IsNaN(magnitudeSquared) ||
                float.IsInfinity(magnitudeSquared))
            {
                normalized = Quaternion.identity;
                return false;
            }

            float inverseMagnitude = 1.0f / Mathf.Sqrt(magnitudeSquared);
            normalized = new Quaternion(
                value.x * inverseMagnitude,
                value.y * inverseMagnitude,
                value.z * inverseMagnitude,
                value.w * inverseMagnitude);
            return true;
        }

        [StructLayout(LayoutKind.Explicit)]
        private struct FloatUIntBits
        {
            [FieldOffset(0)] public float floatValue;
            [FieldOffset(0)] public uint uintValue;
        }

        private static float PackHalf2(float low, float high)
        {
            uint packed = FloatToHalfBits(low) | ((uint)FloatToHalfBits(high) << 16);
            var bits = new FloatUIntBits { uintValue = packed };
            return bits.floatValue;
        }

        private static ushort FloatToHalfBits(float value)
        {
            var bits = new FloatUIntBits { floatValue = value };
            uint source = bits.uintValue;
            uint sign = (source >> 16) & 0x8000u;
            uint exponent = (source >> 23) & 0xffu;
            uint mantissa = source & 0x7fffffu;

            if (exponent == 0xffu)
            {
                if (mantissa == 0u)
                    return (ushort)(sign | 0x7c00u);
                uint payload = mantissa >> 13;
                return (ushort)(sign | 0x7c00u | payload | (payload == 0u ? 1u : 0u));
            }

            int halfExponent = (int)exponent - 127 + 15;
            if (halfExponent >= 31)
                return (ushort)(sign | 0x7c00u);

            if (halfExponent <= 0)
            {
                if (halfExponent < -10)
                    return (ushort)sign;

                mantissa |= 0x800000u;
                int shift = 14 - halfExponent;
                uint halfMantissa = mantissa >> shift;
                uint remainderMask = (1u << shift) - 1u;
                uint remainder = mantissa & remainderMask;
                uint halfway = 1u << (shift - 1);
                if (remainder > halfway ||
                    (remainder == halfway && (halfMantissa & 1u) != 0u))
                {
                    halfMantissa++;
                }
                return (ushort)(sign | halfMantissa);
            }

            uint result = sign | ((uint)halfExponent << 10) | (mantissa >> 13);
            uint normalRemainder = mantissa & 0x1fffu;
            if (normalRemainder > 0x1000u ||
                (normalRemainder == 0x1000u && (result & 1u) != 0u))
            {
                result++;
            }
            return (ushort)result;
        }

        private bool ComesBefore(int candidateIndex, int previousIndex, Vector3 cameraPosition)
        {
            EndfieldHGOperatorLightData candidate = lights[candidateIndex];
            EndfieldHGOperatorLightData previous = lights[previousIndex];
            if (candidate.priority != previous.priority)
                return candidate.priority > previous.priority;

            float candidateDistance =
                (resolvedWorldPositions[candidateIndex] - cameraPosition).sqrMagnitude;
            float previousDistance =
                (resolvedWorldPositions[previousIndex] - cameraPosition).sqrMagnitude;
            return candidateDistance < previousDistance;
        }

        private void OnEnable()
        {
            InvalidateFollowerBones();
            RenderPipelineManager.beginCameraRendering += OnBeginCameraRendering;
            ApplyGlobals();
        }

        private void OnDisable()
        {
            RenderPipelineManager.beginCameraRendering -= OnBeginCameraRendering;
            preparedCamera = null;
            preparedLightCount = 0;
            preparedSerial = 0;
            Shader.SetGlobalInt(CountId, 0);
            Shader.SetGlobalFloat(RecoveredClusteredNprLightLoopId, 0.0f);
            Shader.SetGlobalFloat(RecoveredLightBinningAvailableId, 0.0f);
        }

        private void LateUpdate()
        {
            ApplyGlobals();
        }

        private void OnValidate()
        {
            InvalidateFollowerBones();
            ApplyGlobals();
        }

        private void OnBeginCameraRendering(ScriptableRenderContext context, Camera camera)
        {
            if (camera == GetComponent<Camera>())
                ApplyGlobals();
        }
    }
}

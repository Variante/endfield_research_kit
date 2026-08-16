using System;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Provenance and admission gates for a recovered EffectSetting root made
    /// from animated MeshFilter/MeshRenderer pairs rather than ParticleSystems.
    /// This component does not emulate EffectSetting or guess an Animator state.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class EndfieldRecoveredStaticMeshEffectSource : MonoBehaviour
    {
        public const string LiZhiyanStart01ContractSchema =
            "endfield.lizhiyan-overview-start01-effect.v1";

        public string contractSchema;
        public string effectRoot;
        public string sourceHierarchy;
        public long sourceGameObjectPathId;
        public long sourceTransformPathId;
        public long sourceEffectSettingPathId;
        public bool sourcePayloadApplied;
        public bool sourceEffectSettingPayloadApplied;
        public bool sourceEffectLoops;
        public float sourceEffectDuration;
        public float sourceEffectDelay;
        public float sourceEffectRandomDelay;
        public long sourceAnimatorPathId;
        public long sourceAnimationHelperPathId;
        public long sourceStartAnimationClipPathId;
        public AnimationClip sourceStartAnimationClip;
        public string sourceStartAnimationClipName;
        public float sourceStartAnimationSampleRate;
        public float sourceStartAnimationStopTime;
        public long[] sourceAnimationTargetPathHashes = Array.Empty<long>();
        public string[] sourceAnimationTargetPaths = Array.Empty<string>();
        public long[] sourceAnimationMaterialPropertyHashes = Array.Empty<long>();
        public string[] sourceAnimationMaterialProperties = Array.Empty<string>();
        public bool sourceAnimationBindingsResolved;
        public bool sourceAnimationPayloadApplied;
        public string sourceAggregateSha256;
        public bool visibleAdmission;
        public string[] blockedBy = Array.Empty<string>();
        public string materialExecutionBoundary;
        public EndfieldRecoveredStaticMeshHierarchyNodeSource[] hierarchyNodes =
            Array.Empty<EndfieldRecoveredStaticMeshHierarchyNodeSource>();
        public EndfieldRecoveredStaticMeshNodeSource[] staticMeshNodes =
            Array.Empty<EndfieldRecoveredStaticMeshNodeSource>();
    }

    [Serializable]
    public sealed class EndfieldRecoveredStaticMeshHierarchyNodeSource
    {
        public string hierarchy;
        public long gameObjectPathId;
        public long transformPathId;
        public Transform generatedTransform;
    }

    [Serializable]
    public sealed class EndfieldRecoveredStaticMeshNodeSource
    {
        public string hierarchy;
        public long gameObjectPathId;
        public long transformPathId;
        public long meshFilterPathId;
        public long meshRendererPathId;
        public long meshPathId;
        public long[] materialPathIds = Array.Empty<long>();
        public long[] shaderPathIds = Array.Empty<long>();
        public MeshFilter generatedMeshFilter;
        public MeshRenderer generatedMeshRenderer;
        public bool sourceRendererEnabled;
        public bool nativeMeshPayloadApplied;
        public bool nativeRendererPayloadApplied;
        public bool nativeTexturePayloadsApplied;
        public bool exactShaderVariantsApplied;
        public bool rendererFailClosedForUnrecoveredShader;
    }
}

using System;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    [DisallowMultipleComponent]
    public sealed class EndfieldRecoveredZhuangfyGachaSource : MonoBehaviour
    {
        public string schema;
        public string timelineContractSha256;
        public string particleContractSha256;
        public string nativeContractSha256;
        public string startOrderContractSha256;
        public string runtimePayloadSha256;
        public string originalTimelineName;
        public int originalTrackCount;
        public double originalTimelineEnd;
        public string boundEntityVFXSourceHierarchy;
        public string generatedEntityVFXScopeRoot;
        public string[] exactEligibleRendererPaths = Array.Empty<string>();
        public int[] failClosedAnimationBindingCRCs = Array.Empty<int>();
        public string sourceOuterParentHierarchy;
        public long sourceOuterParentGameObjectPathId;
        public long sourceOuterParentTransformPathId;
        public bool sourceOuterParentSerializedActive;
        public string sourceOuterParentLocalTransform;
        public bool sourceInstantiateInWorldSpace;
        public string[] sourceDirectChildOrder = Array.Empty<string>();
        public string[] sourceHelperDirectorOrder = Array.Empty<string>();
        public string recoveredActorCameraSchema;
        public long recoveredActorDirectorSourcePathId;
        public long recoveredActorCameraTrackSourcePathId;
        public long recoveredActorCameraClipSourcePathId;
        public string recoveredActorCameraClipName;
        public string recoveredActorCameraReportSha256;
        public string recoveredActorCameraFixtureSha256;
        public string recoveredActorCameraClipSourceSha256;
        public string recoveredActorTimelineSha256;
        public string recoveredActorLoopTrackSha256;
        public int recoveredActorAnimationTrackCount;
        public int recoveredActorAnimationClipCount;
        public string[] recoveredActorAnimationTrackBindings =
            Array.Empty<string>();
        public string[] recoveredActorAnimationClipSourceSha256 =
            Array.Empty<string>();
        public string actorLoopBoundary;
        public string[] partiallyRecoveredHelperDirectors =
            Array.Empty<string>();
        public string recoveredDirectorRole;
        public int recoveredDirectorSourceOrdinal;
        public long recoveredDirectorSourcePathId;
        public long recoveredAudioTimelinePathId;
        public string recoveredAudioSerializedFile;
        public string[] recoveredAudioEventNames = Array.Empty<string>();
        public uint[] recoveredAudioEventHashes = Array.Empty<uint>();
        public uint[] recoveredAudioMediaIds = Array.Empty<uint>();
        public double[] recoveredAudioStarts = Array.Empty<double>();
        public double[] recoveredAudioDurations = Array.Empty<double>();
        public string[] recoveredAudioMediaSha256 = Array.Empty<string>();
        public string[] unimplementedHelperDirectors = Array.Empty<string>();
        public float scaledPlayDelaySeconds;
        public string startOrderExecutionBoundary;
        public int sourceBaofaControlTrackOrder;
        public bool sourceBaofaUpdateParticle;
        public uint sourceBaofaParticleRandomSeed;
        public bool sourceBaofaForceRuntimeSimulate;
        public bool sourceBaofaUpdateITimeControl;
        public bool sourceBaofaSearchHierarchy;
        public bool recoveredBaofaUpdateParticle;
        public int recoveredBaofaControllableRootCount;
        public string baofaTimelineOwnershipBoundary;
        public int sourceFingerLightningControlTrackOrder;
        public bool sourceFingerLightningUpdateParticle;
        public uint sourceFingerLightningParticleRandomSeed;
        public bool sourceFingerLightningUpdateITimeControl;
        public bool sourceFingerLightningSearchHierarchy;
        public bool recoveredFingerLightningUpdateParticle;
        public int recoveredFingerLightningControllableRootCount;
        public string timelineParticleHostAuditSha256;
        public string dian901AutomaticRuntimeAuditSha256;
        public string dian901Order4AutomaticOwnerAuditSha256;
        public string dian901DynamicCarrierOracleSha256;
        public string lightning902RetailRuntimeAuditSha256;
        public string fingerLightningTimelineOwnershipBoundary;
        public string effectFollowAuditSha256;
        public int recoveredVFXFollowBoneCarrierCount;
        public string vfxFollowBoneExecutionBoundary;
        public string rendererSelectionBoundary;
        public string animationBindingBoundary;
        public string shaderExecutionBoundary;
    }
}

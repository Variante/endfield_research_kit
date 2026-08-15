using System;
using System.Linq;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Replays the scene-owned Character Info CharEffect after the selected
    /// actor's Overview Animator has been force-started. The original height
    /// bucket remains table-owned; all four serialized buckets have identity
    /// local transforms, so this runtime preserves the proven spatial result
    /// without inventing a character height classification.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class EndfieldRecoveredCharInfoSharedEffect : MonoBehaviour
    {
        private const string ResourcePath = "EndfieldCharInfo/CharEffect";
        private const string ContractSchema =
            "endfield.charinfo-char-effect-particle.v1";
        private const string RecoveredShaderName =
            "Hidden/Endfield/Recovered/Zhuangfy/VFXRefractMRT";
        private const long RootGameObjectPathId = 803616490075416323L;
        private const long RootTransformPathId = 6247092020272195331L;
        private const long TrailGameObjectPathId = 3013782730707986179L;
        private const long TrailParticleSystemPathId = 8113670769548486403L;
        private const long TrailRendererPathId = 5757248678484338435L;
        private const long MaterialPathId = 4388811075012960551L;

        private static readonly Vector3 SingleEffectsPosition =
            new Vector3(-0.3f, 0f, 0.05f);
        private static readonly Vector3 SingleEffectsScale =
            new Vector3(0.5f, 1f, 0.5f);

        private GameObject sourcePrefab;
        private Transform sceneParent;
        private GameObject stage;
        private GameObject instance;
        private bool loggedFailure;

        public bool IsSourceClosedAndPlaying => instance != null;

        public void ClearSharedEffect()
        {
            DestroyStage();
        }

        public void PlayAfterOverviewAnimator(Transform actorRoot)
        {
            if (actorRoot == null || actorRoot.parent == null)
            {
                FailClosed("selected actor has no shared stage parent");
                return;
            }

            if (!TryLoadAndValidatePrefab(out string failure))
            {
                FailClosed(failure);
                return;
            }

            EnsureStage(actorRoot.parent);
            if (stage == null)
                return;

            if (instance == null)
            {
                instance = Instantiate(sourcePrefab, stage.transform, false);
                instance.name = "CharEffect__CharacterInfoRuntime";
            }

            instance.transform.localPosition = Vector3.zero;
            instance.transform.localRotation = Quaternion.identity;
            instance.transform.localScale = Vector3.one;
            instance.SetActive(false);
            foreach (ParticleSystem system in
                     instance.GetComponentsInChildren<ParticleSystem>(true))
            {
                system.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            }
            instance.SetActive(true);
            foreach (ParticleSystem system in
                     instance.GetComponentsInChildren<ParticleSystem>(true))
            {
                system.Play(true);
            }
        }

        private void EnsureStage(Transform requiredParent)
        {
            if (stage != null && sceneParent == requiredParent)
                return;

            DestroyStage();
            sceneParent = requiredParent;
            stage = new GameObject(
                "SingleEffects__RecoveredCharacterInfoSharedStage");
            stage.transform.SetParent(sceneParent, false);
            stage.transform.localPosition = SingleEffectsPosition;
            stage.transform.localRotation = Quaternion.identity;
            stage.transform.localScale = SingleEffectsScale;
        }

        private bool TryLoadAndValidatePrefab(out string failure)
        {
            failure = string.Empty;
            if (sourcePrefab == null)
                sourcePrefab = Resources.Load<GameObject>(ResourcePath);
            if (sourcePrefab == null)
            {
                failure = "source-closed CharEffect resource is missing";
                return false;
            }

            EndfieldRecoveredParticleEffectSource marker =
                sourcePrefab.GetComponent<EndfieldRecoveredParticleEffectSource>();
            if (marker == null ||
                marker.contractSchema != ContractSchema ||
                marker.effectRoot != "CharEffect" ||
                marker.sourceGameObjectPathId != RootGameObjectPathId ||
                marker.sourceTransformPathId != RootTransformPathId ||
                marker.hierarchyNodes == null ||
                marker.hierarchyNodes.Length != 2 ||
                marker.particleNodes == null ||
                marker.particleNodes.Length != 2)
            {
                failure = "CharEffect source marker identity drifted";
                return false;
            }

            EndfieldRecoveredParticleNodeSource trail =
                marker.particleNodes.FirstOrDefault(node =>
                    node != null &&
                    node.gameObjectPathId == TrailGameObjectPathId &&
                    node.particleSystemPathId == TrailParticleSystemPathId &&
                    node.particleRendererPathId == TrailRendererPathId);
            if (trail == null ||
                !trail.sourceRendererEnabled ||
                !trail.nativeParticlePayloadApplied ||
                !trail.nativeRendererPayloadApplied ||
                trail.rendererFailClosedForUnrecoveredShader ||
                trail.materialPathIds == null ||
                trail.materialPathIds.Length != 1 ||
                trail.materialPathIds[0] != MaterialPathId)
            {
                failure = "CharEffect/trail particle identity is incomplete";
                return false;
            }

            ParticleSystemRenderer[] renderers =
                sourcePrefab.GetComponentsInChildren<ParticleSystemRenderer>(true);
            ParticleSystemRenderer visible = renderers.FirstOrDefault(value =>
                value != null && value.enabled);
            if (renderers.Length != 2 || visible == null ||
                visible.sharedMaterials.Length != 1)
            {
                failure = "CharEffect renderer topology drifted";
                return false;
            }

            Material material = visible.sharedMaterials[0];
            if (material == null || material.shader == null ||
                material.shader.name != RecoveredShaderName ||
                material.renderQueue != 3000 ||
                !material.shaderKeywords.SequenceEqual(
                    new[] { "_USE_RBOFFSET" },
                    StringComparer.Ordinal) ||
                !material.HasProperty("_RefractTex") ||
                material.GetTexture("_RefractTex") == null ||
                material.GetTexture("_RefractTex").name != "T_fx_mask_01_M")
            {
                failure = "CharEffect exact VFXRefract material gate failed";
                return false;
            }
            return true;
        }

        private void FailClosed(string reason)
        {
            if (loggedFailure)
                return;
            loggedFailure = true;
            Debug.LogWarning(
                "[Endfield CharInfo] shared CharEffect failed closed: " + reason,
                this);
        }

        private void OnDisable()
        {
            ClearSharedEffect();
        }

        private void OnDestroy()
        {
            ClearSharedEffect();
        }

        private void DestroyStage()
        {
            instance = null;
            if (stage != null)
            {
                if (Application.isPlaying)
                    Destroy(stage);
                else
                    DestroyImmediate(stage);
            }
            stage = null;
            sceneParent = null;
        }
    }
}

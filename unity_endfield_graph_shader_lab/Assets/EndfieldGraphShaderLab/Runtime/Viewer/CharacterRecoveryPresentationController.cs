using System;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    [DisallowMultipleComponent]
    [RequireComponent(typeof(Camera))]
    public sealed class CharacterRecoveryPresentationController : MonoBehaviour
    {
        public Camera viewerCamera;
        public CharacterRecoveryCameraController cameraController;
        public EndfieldRecoveredCharInfoBackgroundPortrait backgroundPortrait;
        public EndfieldHGRPCharacterLightingVolume characterLighting;
        public EndfieldHGOperatorLightRig operatorLightRig;
        public Renderer presentationBackdropRenderer;
        public EndfieldRecoveredCharInfoPresentation physicalPresentation;

        [Header("Recovered Overview behavior")]
        [Tooltip("Optional source CharInfo UIImage backdrop. Keep this off in the resident model lineup; dedicated CharInfo feature captures can enable it explicitly.")]
        public bool enableRecoveredPortrait;
        public bool enableRecoveredSourceEnergyCore;
        public bool enableRecoveredEyeResponse = true;
        public bool enableRecoveredFaceHighlight = true;
        public bool enableRecoveredPostSemantics = true;
        public bool enableRecoveredReadyPresentationSubset = true;
        public bool enableSourceBackedClusteredNprLights = true;
        public bool enableSourceBackedLightBinning = true;
        public bool enableIsolatedPunctualSoftShadows;

        private static readonly int RecoveredFaceHighlightSemanticsId =
            Shader.PropertyToID("_EndfieldRecoveredFaceHighlightSemantics");
        private static readonly int RecoveredPostSemanticsId =
            Shader.PropertyToID("_EndfieldRecoveredPostSemantics");
        private const string RecoveredSourceEnergyCoreEnvironmentVariable =
            "ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE";

        public CharacterRecoveryPresentationProfile ActiveProfile { get; private set; }
        public CharacterRecoveryRig ActiveRig { get; private set; }

        private void Awake()
        {
            ResolveComponents();
        }

        private void OnEnable()
        {
            ResolveComponents();
            PublishRecoveredStyleSelectors();
        }

        private void OnPreCull()
        {
            // These selectors are global because the recovered shaders mirror
            // the source pipeline's global feature switches. Re-publish on the
            // owning camera so editor Camera.Render and normal Play Mode use
            // the same source-profile path.
            PublishRecoveredStyleSelectors();
        }

        private void OnDisable()
        {
            Shader.DisableKeyword(
                EndfieldRecoveredSourceEnergyCoreProbe.Keyword);
            EndfieldRecoveredEyeResponseProbe.Publish(false);
            Shader.SetGlobalFloat(RecoveredFaceHighlightSemanticsId, 0.0f);
            Shader.SetGlobalFloat(RecoveredPostSemanticsId, 0.0f);
            if (physicalPresentation != null)
            {
                physicalPresentation.enableReadySubsetDiagnostic = false;
                physicalPresentation.RefreshSelection();
            }
        }

        public bool ApplyProfile(
            CharacterRecoveryPresentationProfile profile,
            CharacterRecoveryRig rig)
        {
            if (profile == null || rig == null)
                return false;
            if (!profile.sourceRecovered)
            {
                Debug.LogWarning(
                    $"Character presentation profile failed closed because it is not source-recovered: {profile.name}");
                return false;
            }

            ResolveComponents();
            if (viewerCamera == null)
                return false;

            PublishRecoveredStyleSelectors();
            viewerCamera.orthographic = false;
            viewerCamera.aspect = profile.referenceAspect > 0.0f
                ? profile.referenceAspect
                : 16.0f / 9.0f;
            viewerCamera.ResetProjectionMatrix();

            ActiveProfile = profile;
            ActiveRig = rig;
            Transform actorRoot = rig.transform;
            Bounds bounds = rig.CalculateBounds();

            if (cameraController != null)
            {
                cameraController.SetFocus(rig.FocusTarget, bounds);
                cameraController.ApplyRecoveredView(
                    actorRoot.TransformPoint(profile.cameraPosition),
                    actorRoot.TransformPoint(profile.lookAtPosition),
                    profile.fieldOfView,
                    profile.nearClip,
                    profile.farClip);
            }
            else
            {
                Vector3 position = actorRoot.TransformPoint(profile.cameraPosition);
                Vector3 lookAt = actorRoot.TransformPoint(profile.lookAtPosition);
                viewerCamera.transform.SetPositionAndRotation(
                    position,
                    Quaternion.LookRotation(lookAt - position, actorRoot.up));
                viewerCamera.fieldOfView = profile.fieldOfView;
                viewerCamera.nearClipPlane = profile.nearClip;
                viewerCamera.farClipPlane = profile.farClip;
            }

            ApplyCharacterLighting(profile);
            ApplyOperatorLights(profile, actorRoot);
            ApplyPortrait(profile, actorRoot);
            AlignPresentationBackdrop(profile, bounds, actorRoot);

            Debug.Log(
                $"Applied source-recovered CharInfo presentation: {profile.displayName} " +
                $"({profile.characterId}), FOV={profile.fieldOfView:R}, " +
                $"operatorLights={(profile.operatorLights != null ? profile.operatorLights.Length : 0)}.");
            return true;
        }

        public bool ReapplyActiveProfile()
        {
            return ApplyProfile(ActiveProfile, ActiveRig);
        }

        private void ResolveComponents()
        {
            if (viewerCamera == null)
                viewerCamera = GetComponent<Camera>();
            if (cameraController == null)
                cameraController = GetComponent<CharacterRecoveryCameraController>();
            if (characterLighting == null)
                characterLighting = GetComponent<EndfieldHGRPCharacterLightingVolume>();
            if (operatorLightRig == null)
                operatorLightRig = GetComponent<EndfieldHGOperatorLightRig>();
            if (backgroundPortrait == null)
                backgroundPortrait = FindObjectOfType<EndfieldRecoveredCharInfoBackgroundPortrait>(true);
            if (physicalPresentation == null)
                physicalPresentation =
                    FindObjectOfType<EndfieldRecoveredCharInfoPresentation>(true);
            if (presentationBackdropRenderer == null)
            {
                EndfieldRecoveredCharInfoSky sourceSky =
                    GetComponent<EndfieldRecoveredCharInfoSky>();
                if (sourceSky != null)
                    presentationBackdropRenderer = sourceSky.presentationBackdropRenderer;
            }
        }

        private void PublishRecoveredStyleSelectors()
        {
            if (SourceEnergyCoreRequested())
                Shader.EnableKeyword(
                    EndfieldRecoveredSourceEnergyCoreProbe.Keyword);
            else
                Shader.DisableKeyword(
                    EndfieldRecoveredSourceEnergyCoreProbe.Keyword);

            EndfieldRecoveredEyeResponseProbe.Publish(
                enableRecoveredEyeResponse);
            Shader.SetGlobalFloat(
                RecoveredFaceHighlightSemanticsId,
                enableRecoveredFaceHighlight ? 1.0f : 0.0f);
            Shader.SetGlobalFloat(
                RecoveredPostSemanticsId,
                enableRecoveredPostSemantics ? 1.0f : 0.0f);

            if (physicalPresentation == null)
                physicalPresentation =
                    FindObjectOfType<EndfieldRecoveredCharInfoPresentation>(true);
            if (physicalPresentation != null)
            {
                // The complete physical hierarchy is still source-incomplete.
                // Select only the recovered floor/wall/far-grid allow-list.
                physicalPresentation.enableRecoveredPresentation = false;
                physicalPresentation.enableReadySubsetDiagnostic =
                    enableRecoveredReadyPresentationSubset;
                physicalPresentation.RefreshSelection();
            }
        }

        private bool SourceEnergyCoreRequested()
        {
            if (enableRecoveredSourceEnergyCore)
                return true;

            string raw = Environment.GetEnvironmentVariable(
                RecoveredSourceEnergyCoreEnvironmentVariable);
            if (!string.IsNullOrWhiteSpace(raw))
            {
                switch (raw.Trim().ToLowerInvariant())
                {
                    case "1":
                    case "true":
                    case "yes":
                    case "on":
                        return true;
                }
            }

            string[] arguments = Environment.GetCommandLineArgs();
            for (int i = 0; i < arguments.Length; i++)
            {
                if (string.Equals(
                        arguments[i],
                        EndfieldRecoveredSourceEnergyCoreProbe.CommandLineArgument,
                        StringComparison.OrdinalIgnoreCase))
                    return true;
            }
            return false;
        }

        private void ApplyCharacterLighting(CharacterRecoveryPresentationProfile profile)
        {
            if (characterLighting == null || profile.characterLighting == null)
                return;

            Light sceneMainLight = characterLighting.sceneMainLight;
            Cubemap reflectionCubemap = characterLighting.characterReflectionCubemap;
            Cubemap environmentReflectionCubemap =
                characterLighting.environmentReflectionCubemap;
            profile.characterLighting.ApplyTo(characterLighting);
            characterLighting.sceneMainLight = sceneMainLight;
            characterLighting.targetCamera = viewerCamera;
            characterLighting.characterReflectionCubemap = reflectionCubemap;
            characterLighting.environmentReflectionCubemap =
                environmentReflectionCubemap;
            characterLighting.ApplyGlobals(viewerCamera);
        }

        private void ApplyOperatorLights(
            CharacterRecoveryPresentationProfile profile,
            Transform actorRoot)
        {
            if (operatorLightRig == null)
                return;

            operatorLightRig.normalLightCompatibilityScale = 0.0f;
            // The exact selected cloth/hair/skin type-3 equations and both
            // Endminf type-2 punctual-shadow rows are now live. Keep the old
            // generic silhouette carrier disabled so it cannot double-light
            // the recovered clustered response.
            operatorLightRig.rimLightCompatibilityScale = 0.0f;
            operatorLightRig.sourceBackedClusteredNprLightLoop =
                enableSourceBackedClusteredNprLights;
            operatorLightRig.sourceBackedLightBinningMembership =
                enableSourceBackedClusteredNprLights &&
                enableSourceBackedLightBinning;
            operatorLightRig.sourceBackedIsolatedPunctualSoftShadowProducer =
                enableSourceBackedClusteredNprLights &&
                enableIsolatedPunctualSoftShadows &&
                (string.Equals(profile.rootName, "Wulfa", StringComparison.OrdinalIgnoreCase) ||
                 string.Equals(profile.rootName, "Zhuangfy", StringComparison.OrdinalIgnoreCase) ||
                 string.Equals(profile.rootName, "Endminf", StringComparison.OrdinalIgnoreCase));
            operatorLightRig.lights = profile.operatorLights ??
                Array.Empty<EndfieldHGOperatorLightData>();
            operatorLightRig.BindActorRootAndDescribe(actorRoot);
            operatorLightRig.ApplyGlobals();
        }

        private void ApplyPortrait(
            CharacterRecoveryPresentationProfile profile,
            Transform actorRoot)
        {
            if (backgroundPortrait == null)
                return;
            backgroundPortrait.enableRecoveredPortrait = enableRecoveredPortrait;
            backgroundPortrait.ConfigureActor(actorRoot, profile);
        }

        private void AlignPresentationBackdrop(
            CharacterRecoveryPresentationProfile profile,
            Bounds bounds,
            Transform actorRoot)
        {
            if (presentationBackdropRenderer == null || viewerCamera == null)
                return;

            Vector3 target = actorRoot.TransformPoint(profile.lookAtPosition);
            float targetDistance = Mathf.Max(
                1.0f,
                Vector3.Distance(viewerCamera.transform.position, target));
            float planeDistance = targetDistance +
                Mathf.Max(0.8f, bounds.size.y * 0.20f + bounds.extents.z);
            float planeHeight = 2.0f * planeDistance *
                Mathf.Tan(viewerCamera.fieldOfView * 0.5f * Mathf.Deg2Rad) * 1.35f;
            float aspect = profile.referenceAspect > 0.0f
                ? profile.referenceAspect
                : Mathf.Max(0.1f, viewerCamera.aspect);
            float planeWidth = planeHeight * aspect * 1.18f;
            Transform backdrop = presentationBackdropRenderer.transform;
            backdrop.position = viewerCamera.transform.position +
                viewerCamera.transform.forward * planeDistance;
            backdrop.rotation = viewerCamera.transform.rotation;
            backdrop.localScale = new Vector3(planeWidth, planeHeight, 1.0f);
        }
    }
}

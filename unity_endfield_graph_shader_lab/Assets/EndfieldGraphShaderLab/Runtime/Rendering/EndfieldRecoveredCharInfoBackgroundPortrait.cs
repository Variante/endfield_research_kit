using System;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Source-authored CharInfo overview portrait attachment. The retail Lua
    /// route loads bg_charinfo_&lt;templateId&gt; into a world-space UIImage,
    /// aligns the attachment with the authored overview camera/look-at pair,
    /// and applies CharacterDisplayData.overviewImgOffset only to OffsetRoot.
    /// The legacy Wulfa/Zhuangfy fields remain for older diagnostic scenes;
    /// the shared viewer binds a source-recovered roster profile instead.
    /// </summary>
    [ExecuteAlways]
    [DisallowMultipleComponent]
    [AddComponentMenu("Endfield/HGRP Compatibility/Recovered CharInfo Background Portrait")]
    public sealed class EndfieldRecoveredCharInfoBackgroundPortrait : MonoBehaviour
    {
        public const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_CHARINFO_BACKGROUND_PORTRAIT";
        public const string CommandLineArgument =
            "-endfield-recovered-charinfo-background-portrait";
        public const string ShaderName =
            "Endfield/Recovered/CharInfo/BackgroundPortrait";

        public const int SourceUiLayer = 16;
        public const float SettledAnimationAlpha = 90.0f / 255.0f;
        public const float SerializedPrefabAlpha = 120.0f / 255.0f;
        public const float SourceCanvasScale = 0.0016f;
        public const float SourceCardSize = 900.0f;
        public const float SourceCardWorldSize = SourceCanvasScale * SourceCardSize;
        public const float SourceDepthOffset = 0.011f;

        private static readonly Vector3 CanvasLocalPosition =
            new Vector3(0.0f, 0.0f, 0.8f);
        private static readonly Vector3 SettledCardAnchoredPosition =
            new Vector3(-300.0f, 50.0f, 0.0f);
        private static readonly AnimationCurve CardAnchoredXCurve =
            BuildCardAnchoredXCurve();
        private static readonly AnimationCurve CardAlphaCurve =
            BuildCardAlphaCurve();

        private static readonly Vector3 WulfaLookAt =
            new Vector3(0.022f, 1.19f, 0.0f);
        private static readonly Quaternion WulfaOverviewRotation =
            new Quaternion(
                -0.00036646938f,
                0.9991945f,
                0.009385596f,
                0.03901448f);

        private static readonly Vector3 ZhuangfyLookAt =
            new Vector3(0.002f, 1.346f, -0.21826088f);
        private static readonly Quaternion ZhuangfyOverviewRotation =
            new Quaternion(
                -0.00001367486f,
                0.99982595f,
                -0.0007334001f,
                -0.018642593f);

        [Tooltip("Explicit editor/debug selector. Normal use reads the default-off environment or command-line selector.")]
        public bool enableRecoveredPortrait;

        [Tooltip("MeshRenderer carrying the recovered world-space UIImage equivalent.")]
        public Renderer portraitRenderer;

        [Tooltip("MeshFilter switched with the actor-specific GenerateSimpleSprite-equivalent quad.")]
        public MeshFilter portraitMeshFilter;

        [Tooltip("Wulfa UIImage simple-sprite quad recovered from the original tight textureRect and logical 1022-square rect.")]
        public Mesh wulfaMesh;

        [Tooltip("Zhuangfy UIImage simple-sprite quad recovered from the original tight textureRect and logical 1022-square rect.")]
        public Mesh zhuangfyMesh;

        [Tooltip("Exact decoded 1024-square Texture2D for bg_charinfo_chr_0028_wulfa.")]
        public Texture2D wulfaTexture;

        [Tooltip("Exact decoded 1024-square Texture2D for bg_charinfo_chr_0030_zhuangfy.")]
        public Texture2D zhuangfyTexture;

        [Tooltip("Original-data source manifest retained as a player-build dependency.")]
        public TextAsset sourceManifest;

        [Tooltip("Source-recovered camera, portrait, offset, and light profile for the selected playable character.")]
        public CharacterRecoveryPresentationProfile presentationProfile;

        [Tooltip("Currently selected actor root. The component resolves an active Wulfa/Zhuangfy root after viewer switches.")]
        public Transform actorRoot;

        [Tooltip("Wulfa or Zhuangfy. This selects the original texture, look-at point, and raw overview-camera rotation.")]
        public string actorName = "Wulfa";

        private MaterialPropertyBlock propertyBlock;
        private EndfieldOverviewPlayback overviewPlayback;
        private int observedPlaybackGeneration = int.MinValue;
        private float portraitAnimationSeconds;
        private bool loggedActivation;
        private bool loggedFailure;

        public bool RecoveredPortraitRequested =>
            StandaloneRequest() ?? enableRecoveredPortrait;

        public void ConfigureActor(Transform root, string configuredActorName)
        {
            bool actorChanged = actorRoot != root ||
                                !string.Equals(
                                    actorName,
                                    configuredActorName,
                                    StringComparison.OrdinalIgnoreCase);
            actorRoot = root;
            actorName = configuredActorName;
            if (actorChanged)
            {
                ResetAnimationClock();
                loggedActivation = false;
                loggedFailure = false;
            }
            ApplyRecoveredState();
        }

        public void ConfigureActor(
            Transform root,
            CharacterRecoveryPresentationProfile profile)
        {
            bool actorChanged = actorRoot != root || presentationProfile != profile;
            actorRoot = root;
            presentationProfile = profile;
            if (profile != null)
            {
                actorName = string.IsNullOrEmpty(profile.rootName)
                    ? root != null ? root.name : actorName
                    : profile.rootName;
                if (profile.sourceManifest != null)
                    sourceManifest = profile.sourceManifest;
            }
            if (actorChanged)
            {
                ResetAnimationClock();
                loggedActivation = false;
                loggedFailure = false;
            }
            ApplyRecoveredState();
        }

        public void ApplyRecoveredState()
        {
            if (portraitRenderer == null)
                portraitRenderer = GetComponent<Renderer>();
            if (portraitMeshFilter == null)
                portraitMeshFilter = GetComponent<MeshFilter>();

            if (!RecoveredPortraitRequested)
            {
                if (portraitRenderer != null)
                    portraitRenderer.enabled = false;
                loggedActivation = false;
                loggedFailure = false;
                return;
            }

            Transform resolvedActor = ResolveActiveActor();
            bool hasProfile = presentationProfile != null &&
                              presentationProfile.sourceRecovered;
            bool isWulfa = string.Equals(
                actorName,
                "Wulfa",
                StringComparison.OrdinalIgnoreCase);
            bool isZhuangfy = string.Equals(
                actorName,
                "Zhuangfy",
                StringComparison.OrdinalIgnoreCase);
            Texture2D texture = hasProfile
                ? presentationProfile.portraitTexture
                : isWulfa
                    ? wulfaTexture
                    : isZhuangfy
                        ? zhuangfyTexture
                        : null;
            Mesh mesh = hasProfile
                ? presentationProfile.portraitMesh
                : isWulfa
                    ? wulfaMesh
                    : isZhuangfy
                        ? zhuangfyMesh
                        : null;

            if (portraitRenderer == null ||
                portraitMeshFilter == null ||
                resolvedActor == null ||
                texture == null ||
                mesh == null)
            {
                if (portraitRenderer != null)
                    portraitRenderer.enabled = false;
                if (!loggedFailure)
                {
                    Debug.LogWarning(
                        "Recovered CharInfo background portrait failed closed: " +
                        $"actor={actorName}, actorRoot={(resolvedActor != null)}, " +
                        $"renderer={(portraitRenderer != null)}, " +
                        $"meshFilter={(portraitMeshFilter != null)}, " +
                        $"texture={(texture != null)}, mesh={(mesh != null)}.");
                    loggedFailure = true;
                }
                return;
            }

            Vector3 lookAt = hasProfile
                ? presentationProfile.lookAtPosition
                : isWulfa ? WulfaLookAt : ZhuangfyLookAt;
            Quaternion overviewRotation = hasProfile
                ? presentationProfile.authoredOverviewRotation
                : isWulfa
                    ? WulfaOverviewRotation
                    : ZhuangfyOverviewRotation;
            overviewRotation.Normalize();
            Vector3 overviewImageOffset = hasProfile
                ? presentationProfile.overviewImageOffset
                : Vector3.zero;
            float animationSeconds = ResolveAnimationSeconds(resolvedActor);
            Vector3 cardAnchoredPosition = new Vector3(
                CardAnchoredXCurve.Evaluate(animationSeconds),
                SettledCardAnchoredPosition.y,
                0.0f);
            float animationAlpha = CardAlphaCurve.Evaluate(animationSeconds);

            // CharInfoCamAttachment is aligned with lookat_overview, assigned
            // the raw vcam_overview local rotation, and reparented under the
            // identity CharContainer. CharinfoBGDeco then contributes local
            // z=0.8 and scale=.0016; the settled CharTexture contributes
            // anchoredPosition=(-300,50), size=900x900.
            Vector3 localCardCenter = lookAt + overviewRotation *
                (overviewImageOffset + CanvasLocalPosition +
                 cardAnchoredPosition * SourceCanvasScale);
            transform.position = resolvedActor.TransformPoint(localCardCenter);
            transform.rotation = resolvedActor.rotation * overviewRotation;
            transform.localScale = Vector3.Scale(
                resolvedActor.lossyScale,
                new Vector3(SourceCardWorldSize, SourceCardWorldSize, 1.0f));
            if (portraitMeshFilter.sharedMesh != mesh)
                portraitMeshFilter.sharedMesh = mesh;

            if (propertyBlock == null)
                propertyBlock = new MaterialPropertyBlock();
            portraitRenderer.GetPropertyBlock(propertyBlock);
            propertyBlock.SetTexture("_MainTex", texture);
            propertyBlock.SetColor(
                "_TintColor",
                new Color(1.0f, 1.0f, 1.0f, animationAlpha));
            propertyBlock.SetFloat("_DepthOffset", SourceDepthOffset);
            portraitRenderer.SetPropertyBlock(propertyBlock);
            portraitRenderer.enabled = true;
            loggedFailure = false;

            if (!loggedActivation)
            {
                Debug.Log(
                    "Recovered CharInfo background portrait active: " +
                    $"actor={actorName}, sprite=bg_charinfo_" +
                    $"{(hasProfile ? presentationProfile.characterId : isWulfa ? "chr_0028_wulfa" : "chr_0030_zhuangfy")}, " +
                    $"overviewImgOffset=({overviewImageOffset.x:R},{overviewImageOffset.y:R},{overviewImageOffset.z:R}), " +
                    "card=900x900, canvasScale=0.0016, " +
                    "simpleSpriteTightQuad=actor-specific, " +
                    "sourceAutoplay=charinfobgdeco_in, " +
                    "anchoredX=-200..-300/3.5s, alpha=0..90/255/1s, " +
                    "depthOffset=0.011, " +
                    "blend=One/OneMinusSrcAlpha, " +
                    "sceneDepthClip=primary-full-scene-post-Uber. " +
                    "The distinct retail paired output-depth attachment remains omitted; " +
                    "this selected pass is ZTest Always/ZWrite Off.");
                loggedActivation = true;
            }
        }

        private Transform ResolveActiveActor()
        {
            if (actorRoot != null && actorRoot.gameObject.activeInHierarchy)
            {
                actorName = CanonicalActorName(actorRoot.name, actorName);
                return actorRoot;
            }

            Transform fallback = FindActiveRecoveryRigTransform();
            if (fallback == null)
            {
                fallback = FindActiveSceneTransform("Wulfa");
                if (fallback == null)
                    fallback = FindActiveSceneTransform("Zhuangfy");
            }
            if (fallback != null)
            {
                actorRoot = fallback;
                actorName = CanonicalActorName(fallback.name, actorName);
            }
            return fallback;
        }

        private float ResolveAnimationSeconds(Transform resolvedActor)
        {
            if (!Application.isPlaying)
                return 3.5f;

            EndfieldOverviewPlayback resolvedOverview = resolvedActor == null
                ? null
                : resolvedActor.GetComponentInChildren<EndfieldOverviewPlayback>(true);
            if (resolvedOverview != overviewPlayback)
            {
                overviewPlayback = resolvedOverview;
                observedPlaybackGeneration = int.MinValue;
                portraitAnimationSeconds = 0.0f;
            }
            if (overviewPlayback == null ||
                !overviewPlayback.AutomaticOverviewPlaybackActive)
            {
                return 3.5f;
            }

            int generation = overviewPlayback.PlaybackGeneration;
            bool startState = overviewPlayback.TryGetAutomaticOverviewStartSeconds(
                out float bodyClipSeconds);
            if (generation != observedPlaybackGeneration)
            {
                observedPlaybackGeneration = generation;
                portraitAnimationSeconds = startState
                    ? Mathf.Max(0.0f, bodyClipSeconds)
                    : 0.0f;
            }
            else if (startState)
            {
                portraitAnimationSeconds = Mathf.Max(0.0f, bodyClipSeconds);
            }
            else
            {
                portraitAnimationSeconds += Mathf.Max(0.0f, Time.deltaTime);
            }
            return portraitAnimationSeconds;
        }

        private void ResetAnimationClock()
        {
            overviewPlayback = null;
            observedPlaybackGeneration = int.MinValue;
            portraitAnimationSeconds = 0.0f;
        }

        private static AnimationCurve BuildCardAnchoredXCurve()
        {
            Keyframe start = new Keyframe(
                0.0f,
                -200.0f,
                2.2694368f,
                2.2694368f,
                1.0f / 3.0f,
                0.04842146f)
            {
                weightedMode = WeightedMode.Both
            };
            Keyframe end = new Keyframe(
                3.5f,
                -300.0f,
                0.0f,
                0.0f,
                1.0f,
                1.0f / 3.0f)
            {
                weightedMode = WeightedMode.Both
            };
            return new AnimationCurve(start, end)
            {
                preWrapMode = WrapMode.ClampForever,
                postWrapMode = WrapMode.ClampForever
            };
        }

        private static AnimationCurve BuildCardAlphaCurve()
        {
            return new AnimationCurve(
                new Keyframe(0.0f, 0.0f, 0.0f, 0.0f),
                new Keyframe(1.0f, SettledAnimationAlpha, 0.0f, 0.0f))
            {
                preWrapMode = WrapMode.ClampForever,
                postWrapMode = WrapMode.ClampForever
            };
        }

        private static Transform FindActiveRecoveryRigTransform()
        {
            CharacterRecoveryRig[] rigs =
                Resources.FindObjectsOfTypeAll<CharacterRecoveryRig>();
            for (int i = 0; i < rigs.Length; i++)
            {
                CharacterRecoveryRig rig = rigs[i];
                if (rig != null &&
                    rig.gameObject.activeInHierarchy &&
                    rig.gameObject.scene.IsValid())
                {
                    return rig.transform;
                }
            }
            return null;
        }

        private static Transform FindActiveSceneTransform(string targetName)
        {
            Transform[] transforms = Resources.FindObjectsOfTypeAll<Transform>();
            for (int i = 0; i < transforms.Length; i++)
            {
                Transform candidate = transforms[i];
                if (candidate == null ||
                    !candidate.gameObject.activeInHierarchy ||
                    !candidate.gameObject.scene.IsValid() ||
                    !string.Equals(candidate.name, targetName, StringComparison.OrdinalIgnoreCase))
                {
                    continue;
                }
                return candidate;
            }
            return null;
        }

        private static string CanonicalActorName(string candidate, string fallback)
        {
            if (string.Equals(candidate, "Wulfa", StringComparison.OrdinalIgnoreCase))
                return "Wulfa";
            if (string.Equals(candidate, "Zhuangfy", StringComparison.OrdinalIgnoreCase))
                return "Zhuangfy";
            return fallback;
        }

        /// <summary>
        /// Explicit standalone request, or null when neither the selector nor
        /// the command line names one. A falsey selector forces the recovered
        /// portrait off even when the scene serialized it on.
        /// </summary>
        private static bool? StandaloneRequest()
        {
            bool? request = EndfieldRecoveredSelector.Explicit(EnvironmentVariable);
            string[] arguments = Environment.GetCommandLineArgs();
            for (int i = 0; i < arguments.Length; i++)
            {
                string argument = arguments[i];
                if (string.Equals(
                    argument,
                    CommandLineArgument,
                    StringComparison.OrdinalIgnoreCase))
                {
                    request = true;
                    continue;
                }

                string prefix = CommandLineArgument + "=";
                if (argument.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                    request = IsEnabledSelectorValue(argument.Substring(prefix.Length));
            }
            return request;
        }

        private static bool? IsEnabledSelectorValue(string value)
        {
            if (string.IsNullOrWhiteSpace(value))
                return null;
            value = value.Trim();
            if (string.Equals(value, "1", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(value, "true", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(value, "yes", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(value, "on", StringComparison.OrdinalIgnoreCase))
                return true;
            if (string.Equals(value, "0", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(value, "false", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(value, "no", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(value, "off", StringComparison.OrdinalIgnoreCase))
                return false;
            return null;
        }

        private void OnEnable()
        {
            ResetAnimationClock();
            ApplyRecoveredState();
        }

        private void LateUpdate()
        {
            ApplyRecoveredState();
        }

        private void OnValidate()
        {
            ApplyRecoveredState();
        }

        private void OnDisable()
        {
            if (portraitRenderer != null)
                portraitRenderer.enabled = false;
        }
    }
}

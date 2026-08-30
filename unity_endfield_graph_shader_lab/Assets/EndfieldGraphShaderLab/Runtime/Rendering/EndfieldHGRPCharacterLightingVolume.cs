using System;
using System.Collections.Generic;
using System.Globalization;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Serialization;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Built-in/SRP-independent publisher for Endfield's recovered HGRP character-light contract.
    ///
    /// The original HGCharacterVolume is packed by HGRenderPipeline into _CharacterParams0..15.
    /// This component preserves that packing so recovered shaders can consume the same controls
    /// without depending on the unavailable HGRP runtime.
    /// </summary>
    [ExecuteAlways]
    [DisallowMultipleComponent]
    [DefaultExecutionOrder(-10000)]
    [AddComponentMenu("Endfield/HGRP Compatibility/Character Lighting Volume")]
    public sealed class EndfieldHGRPCharacterLightingVolume : MonoBehaviour
    {
        public enum CharacterLightMode
        {
            Scene = 0,
            CameraFollow = 1,
            Custom = 2
        }

        public enum CharacterShadowTintMode
        {
            Auto = 0,
            CustomTintColor = 1
        }

        private static readonly List<EndfieldHGRPCharacterLightingVolume> Instances =
            new List<EndfieldHGRPCharacterLightingVolume>();

        private static readonly int[] CharacterParameterIds =
        {
            Shader.PropertyToID("_CharacterParams0"),
            Shader.PropertyToID("_CharacterParams1"),
            Shader.PropertyToID("_CharacterParams2"),
            Shader.PropertyToID("_CharacterParams3"),
            Shader.PropertyToID("_CharacterParams4"),
            Shader.PropertyToID("_CharacterParams5"),
            Shader.PropertyToID("_CharacterParams6"),
            Shader.PropertyToID("_CharacterParams7"),
            Shader.PropertyToID("_CharacterParams8"),
            Shader.PropertyToID("_CharacterParams9"),
            Shader.PropertyToID("_CharacterParams10"),
            Shader.PropertyToID("_CharacterParams11"),
            Shader.PropertyToID("_CharacterParams12"),
            Shader.PropertyToID("_CharacterParams13"),
            Shader.PropertyToID("_CharacterParams14"),
            Shader.PropertyToID("_CharacterParams15")
        };

        private static readonly int EnvironmentGlobalParams0Id = Shader.PropertyToID("_EnvironmentGlobalParams0");
        private static readonly int ExposureParamsId = Shader.PropertyToID("_ExposureParams");
        private static readonly int CharacterMainLightIntensityId =
            Shader.PropertyToID("_EndfieldCharMainLightIntensity");
        private static readonly int CharacterMaxCubemapId = Shader.PropertyToID("_CharMaxCubemap");
        private static readonly int RecoveredCharacterCubemapBoundId =
            Shader.PropertyToID("_EndfieldRecoveredCharCubemapBound");
        private static readonly int CompatibilityActiveId = Shader.PropertyToID("_EndfieldHGRPCompatActive");
        private static readonly int CompatibilityInfluenceId = Shader.PropertyToID("_EndfieldHGRPCompatInfluence");
        private static readonly int RecoveredDiffuseAuditModeId =
            Shader.PropertyToID("_EndfieldRecoveredDiffuseAuditMode");
        private static readonly int RecoveredShadowBlendOverrideId =
            Shader.PropertyToID("_EndfieldRecoveredShadowBlendOverride");
        private const string RecoveredDiffuseAuditModeEnvironmentVariable =
            "ENDFIELD_RECOVERED_DIFFUSE_AUDIT_MODE";
        private const string RecoveredShadowBlendOverrideEnvironmentVariable =
            "ENDFIELD_RECOVERED_SHADOW_BLEND_OVERRIDE";

        [Header("Volume Selection")]
        [Tooltip("If multiple compatibility volumes are enabled, only the highest-priority volume publishes globals.")]
        public int priority;

        [Tooltip("Blends simplified lab shaders toward the exact HGRP global contract. Keep below one until irradiance volumes and the original post stack are recovered.")]
        [Range(0.0f, 1.0f)] public float compatibilityShaderInfluence = 0.35f;

        [Header("Scene Sources")]
        [Tooltip("Optional. RenderSettings.sun, then the first active directional light, are used when this is empty.")]
        public Light sceneMainLight;

        [Tooltip("Optional camera used for Camera Follow light mode. The currently rendering camera is used when empty.")]
        public Camera targetCamera;

        [Header("Main Character Light")]
        [Tooltip("Original charMainLightControl flag. It tells compatible shaders that the character volume owns the light controls.")]
        public bool manualCharacterLightControl = true;

        public CharacterLightMode mainLightMode = CharacterLightMode.Scene;

        [Tooltip("Pitch/yaw in degrees. The recovered game default is (30, 150).")]
        public Vector2 customMainLightAngles = new Vector2(30.0f, 150.0f);

        [Tooltip("Minimum pitch and yaw offset in degrees. The recovered game default is (30, 10).")]
        public Vector2 cameraFollowLightBias = new Vector2(30.0f, 10.0f);

        [Range(0.0f, 5.0f)] public float mainLightMultiplier = 1.0f;
        [Range(0.0f, 3.0f)] public float environmentLightMultiplier = 0.7f;
        [Range(0.0f, 2.0f)] public float environmentShadowMultiplier = 1.0f;
        [Range(0.0f, 2.0f)] public float mainLightSpecularMultiplier = 1.0f;

        [Tooltip("Moves the NPR light/shadow boundary. The original valid range is -1..1.")]
        [Range(-1.0f, 1.0f)] public float mainLightRangeBias;
        public bool overrideMainLightRangeBias;

        public bool overrideMainLightColor;
        [ColorUsage(true, true)] public Color mainLightOverrideColor = Color.white;
        public bool overrideSkinMainLightColor;
        [ColorUsage(true, true)] public Color skinMainLightOverrideColor = Color.white;

        [Header("Ambient / Environment")]
        [Tooltip("World-space direction used by the character-only directional ambient lobe.")]
        public Vector3 ambientDirection = Vector3.up;

        [Range(0.0f, 5.0f)] public float ambientBaseIntensity = 1.0f;
        [Range(0.0f, 5.0f)] public float ambientDirectionalIntensity = 0.6f;
        [Range(-0.5f, 0.5f)] public float ambientDirectionalBias = 0.15f;
        public bool ignoreSceneEnvironment;
        public bool ignoreSceneAdditionalLights;
        public Cubemap characterReflectionCubemap;
        [Tooltip(
            "Exact T_hdri_env_char_01 source for the recovered reflection-probe " +
            "oct/global resources. It is consumed only by the default-off " +
            "canonical CharInfo frame path.")]
        public Cubemap environmentReflectionCubemap;

        [Tooltip("Recovered default is (1.67, 1.5, 1, 0). Its exact scene-volume semantics remain partially unresolved.")]
        public Vector4 environmentGlobalParams0 = new Vector4(1.67f, 1.5f, 1.0f, 0.0f);

        [Header("Shadow Composition")]
        public bool ignoreMainLightShadow;
        public CharacterShadowTintMode shadowTintMode = CharacterShadowTintMode.Auto;
        [ColorUsage(true, true)] public Color shadowTintColor = Color.white;
        [ColorUsage(true, true)] public Color skinShadowTintColor = Color.white;
        [Range(0.0f, 1.0f)] public float selfShadowStrength = 1.0f;

        [Header("Dialogue Presentation")]
        [Tooltip("Recovered charLightDialogMode. It deliberately separates attractive close-up lighting from scene integration.")]
        public bool dialogueLightingMode;

        [Header("Character Rim")]
        public bool enableCharacterRim;
        [ColorUsage(true, true)] public Color characterRimColor = Color.white;
        [Range(0.0f, 1.0f)] public float characterRimDirection;
        [Range(0.0f, 10.0f)] public float characterRimIntensity = 1.0f;
        [Range(0.0f, 1.0f)] public float characterRimWidth = 0.4f;
        [Range(0.0f, 1.0f)] public float characterRimAlbedoInfluence;
        public bool useNewCharacterRimMode;

        [Header("Face Rim")]
        public bool enableFaceRim;
        [ColorUsage(true, true)] public Color faceRimColor = Color.white;
        [Range(0.0f, 1.0f)] public float faceRimDirection;
        [Range(0.0f, 10.0f)] public float faceRimIntensity = 1.0f;

        [Header("Eye Light")]
        [Range(0.0f, 3.0f)] public float eyeBaseLightMultiplier;
        [Range(0.0f, 3.0f)] public float eyeHighlightMultiplier;
        [Range(0.0f, 3.0f)] public float eyeScatteringMultiplier;

        [Header("Outline Compatibility")]
        [Tooltip("The original volume quality tier controls whether the outline pass runs; material masks still control local width.")]
        public bool enableCharacterOutline = true;
        [Range(0.0f, 4.0f)] public float outlineWidthMultiplier = 1.0f;
        [Range(0.0f, 4.0f)] public float outlineIntensity = 1.0f;
        [ColorUsage(true, true)] public Color outlineTint = Color.white;

        [Header("Character Environment Override")]
        [FormerlySerializedAs("hairDarkenOverride")]
        [Tooltip("Recovered _CharacterParams10 override. X > 0.5 selects it; Y stores the bit-packed rain/wet/wet-global/snow UNorm8 lanes; W overrides wet world-space height. Z is unresolved and should remain zero. A zero vector leaves the static lab's per-draw environment state inactive.")]
        public Vector4 characterEnvironmentEffectOverride;

        [Header("Exposure Contract")]
        [Tooltip("Uses the original LightExtensions character-main descriptor. The source intensity is the serialized HGLightConfig directIntensityDividePi; its live input is _ExposureParams.x.")]
        public bool useRecoveredSourceMainLightDescriptor;
        [ColorUsage(true, true)] public Color sourceDirectColor = Color.white;
        [Min(0.0f)] public float sourceDirectIntensityDividePi = 1.0f;

        [Tooltip("Publishes the recovered HGRP _ExposureParams contract: x is the exposure multiplier and y/z/w are zero. Zero EV is neutral and is the safe default.")]
        public bool publishExposureGlobals = true;
        [Range(-8.0f, 8.0f)] public float postExposureEV;

        private readonly Vector4[] packedCharacterParameters = new Vector4[16];
        private Light cachedAutomaticMainLight;

        public Vector4 GetPackedCharacterParameter(int index)
        {
            if (index < 0 || index >= packedCharacterParameters.Length)
                return Vector4.zero;

            PackCharacterParameters(ResolveCamera(null), ResolveMainLight());
            return packedCharacterParameters[index];
        }

        public void ApplyGlobals(Camera renderingCamera = null)
        {
            if (!isActiveAndEnabled || ActiveVolume != this)
                return;

            Camera camera = ResolveCamera(renderingCamera);
            Light mainLight = ResolveMainLight();
            PackCharacterParameters(camera, mainLight);

            Shader.SetGlobalFloat(CompatibilityActiveId, 1.0f);
            Shader.SetGlobalFloat(CompatibilityInfluenceId, compatibilityShaderInfluence);
            Shader.SetGlobalFloat(RecoveredDiffuseAuditModeId, ResolveRecoveredDiffuseAuditMode());
            Shader.SetGlobalFloat(
                RecoveredShadowBlendOverrideId,
                ResolveRecoveredShadowBlendOverride());
            for (int i = 0; i < packedCharacterParameters.Length; i++)
                Shader.SetGlobalVector(CharacterParameterIds[i], packedCharacterParameters[i]);

            Shader.SetGlobalVector(EnvironmentGlobalParams0Id, environmentGlobalParams0);
            float exposure = Mathf.Max(Shader.GetGlobalVector(ExposureParamsId).x, 1e-5f);
            if (publishExposureGlobals)
            {
                exposure = Mathf.Pow(2.0f, postExposureEV);
                Shader.SetGlobalVector(ExposureParamsId, new Vector4(exposure, 0.0f, 0.0f, 0.0f));
            }

            bool characterCubemapBound = characterReflectionCubemap != null;
            Shader.SetGlobalFloat(
                RecoveredCharacterCubemapBoundId,
                characterCubemapBound ? 1.0f : 0.0f);
            if (characterCubemapBound)
                Shader.SetGlobalTexture(CharacterMaxCubemapId, characterReflectionCubemap);

            PublishSemanticAliases(mainLight, exposure);
        }

        internal void ApplyRecoveredExposureDependentGlobals(
            CommandBuffer commandBuffer,
            float exposure)
        {
            if (commandBuffer == null)
                return;
            commandBuffer.SetGlobalFloat(
                CharacterMainLightIntensityId,
                ResolveCharacterMainLightIntensity(exposure));
        }

        private void OnEnable()
        {
            if (!Instances.Contains(this))
                Instances.Add(this);

            Camera.onPreCull += OnCameraPreCull;
            RenderPipelineManager.beginCameraRendering += OnBeginCameraRendering;
            ApplyGlobals();
        }

        private void OnDisable()
        {
            Camera.onPreCull -= OnCameraPreCull;
            RenderPipelineManager.beginCameraRendering -= OnBeginCameraRendering;
            Instances.Remove(this);

            EndfieldHGRPCharacterLightingVolume active = ActiveVolume;
            if (active != null)
                active.ApplyGlobals();
            else
            {
                Shader.SetGlobalFloat(CompatibilityActiveId, 0.0f);
                Shader.SetGlobalFloat(CompatibilityInfluenceId, 0.0f);
                Shader.SetGlobalFloat(RecoveredCharacterCubemapBoundId, 0.0f);
                Shader.SetGlobalFloat(RecoveredDiffuseAuditModeId, 0.0f);
                Shader.SetGlobalFloat(RecoveredShadowBlendOverrideId, -1.0f);
                Shader.SetGlobalFloat(CharacterMainLightIntensityId, 1.0f);
                for (int i = 0; i < CharacterParameterIds.Length; i++)
                    Shader.SetGlobalVector(CharacterParameterIds[i], Vector4.zero);
            }
        }

        private void LateUpdate()
        {
            ApplyGlobals();
        }

        private void OnValidate()
        {
            if (ambientDirection.sqrMagnitude < 1e-6f)
                ambientDirection = Vector3.up;

            if (isActiveAndEnabled)
                ApplyGlobals();
        }

        private void OnCameraPreCull(Camera camera)
        {
            ApplyGlobals(camera);
        }

        private void OnBeginCameraRendering(ScriptableRenderContext context, Camera camera)
        {
            ApplyGlobals(camera);
        }

        private static int ResolveRecoveredDiffuseAuditMode()
        {
            string rawValue = Environment.GetEnvironmentVariable(
                RecoveredDiffuseAuditModeEnvironmentVariable);
            return int.TryParse(rawValue, out int mode)
                ? Mathf.Clamp(mode, 0, 6)
                : 0;
        }

        private static float ResolveRecoveredShadowBlendOverride()
        {
            string rawValue = Environment.GetEnvironmentVariable(
                RecoveredShadowBlendOverrideEnvironmentVariable);
            if (!float.TryParse(
                    rawValue,
                    NumberStyles.Float,
                    CultureInfo.InvariantCulture,
                    out float blend))
            {
                return -1.0f;
            }

            return blend < 0.0f ? -1.0f : Mathf.Clamp01(blend);
        }

        private static EndfieldHGRPCharacterLightingVolume ActiveVolume
        {
            get
            {
                EndfieldHGRPCharacterLightingVolume best = null;
                for (int i = Instances.Count - 1; i >= 0; i--)
                {
                    EndfieldHGRPCharacterLightingVolume candidate = Instances[i];
                    if (candidate == null)
                    {
                        Instances.RemoveAt(i);
                        continue;
                    }

                    if (!candidate.isActiveAndEnabled)
                        continue;

                    if (best == null || candidate.priority > best.priority ||
                        (candidate.priority == best.priority && candidate.GetInstanceID() < best.GetInstanceID()))
                    {
                        best = candidate;
                    }
                }

                return best;
            }
        }

        private Camera ResolveCamera(Camera renderingCamera)
        {
            if (targetCamera != null)
                return targetCamera;
            if (renderingCamera != null)
                return renderingCamera;
            return Camera.main;
        }

        private Light ResolveMainLight()
        {
            if (IsUsableDirectionalLight(sceneMainLight))
                return sceneMainLight;
            if (IsUsableDirectionalLight(RenderSettings.sun))
                return RenderSettings.sun;
            if (IsUsableDirectionalLight(cachedAutomaticMainLight))
                return cachedAutomaticMainLight;

            Light[] lights = FindObjectsOfType<Light>();
            for (int i = 0; i < lights.Length; i++)
            {
                if (!IsUsableDirectionalLight(lights[i]))
                    continue;
                cachedAutomaticMainLight = lights[i];
                return cachedAutomaticMainLight;
            }

            return null;
        }

        private static bool IsUsableDirectionalLight(Light light)
        {
            return light != null && light.type == LightType.Directional && light.enabled &&
                   light.gameObject.activeInHierarchy;
        }

        private void PackCharacterParameters(Camera camera, Light mainLight)
        {
            Vector3 characterLightDirection = ResolveCharacterLightDirection(camera, mainLight);
            Vector3 normalizedAmbientDirection = ambientDirection.normalized;
            Vector3 autoRimVector = ResolveAutoRimVector(characterRimDirection);
            Vector3 faceRimVector = ResolveFaceRimVector(faceRimDirection);

            Color resolvedShadowTint = shadowTintMode == CharacterShadowTintMode.CustomTintColor
                ? AutoTintColor(shadowTintColor)
                : Color.white;
            Color resolvedSkinShadowTint = shadowTintMode == CharacterShadowTintMode.CustomTintColor
                ? AutoTintColor(skinShadowTintColor)
                : Color.white;

            Color skinLightColor = overrideSkinMainLightColor
                ? skinMainLightOverrideColor
                : mainLightOverrideColor;

            // This layout is recovered directly from HGRenderPipeline's writes into
            // ShaderVariablesGlobal. Preserve it even where a compatibility shader uses
            // only a subset of the vectors.
            packedCharacterParameters[0] = new Vector4(
                BoolFloat(manualCharacterLightControl),
                mainLightMultiplier,
                environmentLightMultiplier,
                environmentShadowMultiplier);
            packedCharacterParameters[1] = new Vector4(
                BoolFloat(dialogueLightingMode),
                (float)shadowTintMode,
                BoolFloat(ignoreMainLightShadow),
                mainLightMode == CharacterLightMode.Scene ? 0.0f : 1.0f);
            packedCharacterParameters[2] = ColorVector(resolvedShadowTint);
            packedCharacterParameters[3] = ColorVector(resolvedSkinShadowTint);
            packedCharacterParameters[4] = ColorVector(skinLightColor);
            packedCharacterParameters[5] = ColorVector(mainLightOverrideColor);
            packedCharacterParameters[6] = new Vector4(
                normalizedAmbientDirection.x,
                normalizedAmbientDirection.y,
                normalizedAmbientDirection.z,
                0.0f);
            packedCharacterParameters[7] = new Vector4(
                ambientDirectionalBias,
                ambientDirectionalIntensity,
                ambientBaseIntensity,
                0.0f);
            packedCharacterParameters[8] = new Vector4(
                enableCharacterRim ? characterRimColor.r : 0.0f,
                enableCharacterRim ? characterRimColor.g : 0.0f,
                enableCharacterRim ? characterRimColor.b : 0.0f,
                characterRimIntensity);
            packedCharacterParameters[9] = new Vector4(
                autoRimVector.x,
                autoRimVector.y,
                characterRimAlbedoInfluence,
                characterRimWidth);
            packedCharacterParameters[10] = characterEnvironmentEffectOverride;
            packedCharacterParameters[11] = new Vector4(
                characterLightDirection.x,
                characterLightDirection.y,
                characterLightDirection.z,
                mainLightRangeBias);
            packedCharacterParameters[12] = new Vector4(
                BoolFloat(overrideMainLightRangeBias),
                BoolFloat(overrideMainLightColor),
                ignoreSceneAdditionalLights ? 0.0f : 1.0f,
                BoolFloat(ignoreSceneEnvironment));
            packedCharacterParameters[13] = new Vector4(
                eyeBaseLightMultiplier,
                eyeHighlightMultiplier,
                eyeScatteringMultiplier,
                mainLightSpecularMultiplier);
            packedCharacterParameters[14] = new Vector4(
                enableFaceRim ? faceRimColor.r : 0.0f,
                enableFaceRim ? faceRimColor.g : 0.0f,
                enableFaceRim ? faceRimColor.b : 0.0f,
                faceRimIntensity);
            packedCharacterParameters[15] = new Vector4(
                faceRimVector.x,
                faceRimVector.y,
                faceRimVector.z,
                BoolFloat(useNewCharacterRimMode));
        }

        private Vector3 ResolveCharacterLightDirection(Camera camera, Light mainLight)
        {
            if (mainLightMode == CharacterLightMode.Scene)
            {
                return mainLight != null
                    ? (-mainLight.transform.forward).normalized
                    : new Vector3(-0.433f, 0.5f, 0.75f).normalized;
            }

            if (mainLightMode == CharacterLightMode.CameraFollow && camera != null)
            {
                Vector3 euler = camera.transform.rotation.eulerAngles;
                float signedPitch = euler.x > 180.0f ? euler.x - 360.0f : euler.x;
                float pitch = Mathf.Max(cameraFollowLightBias.x, signedPitch);
                float yaw = euler.y + cameraFollowLightBias.y;
                return DirectionFromPitchYaw(pitch, yaw);
            }

            return DirectionFromPitchYaw(customMainLightAngles.x, customMainLightAngles.y);
        }

        private static Vector3 DirectionFromPitchYaw(float pitchDegrees, float yawDegrees)
        {
            // Matches the recovered GetCharLightVector equation:
            // (-sin(yaw)*cos(pitch), sin(pitch), -cos(yaw)*cos(pitch)).
            float pitch = pitchDegrees * Mathf.Deg2Rad;
            float yaw = yawDegrees * Mathf.Deg2Rad;
            float cosPitch = Mathf.Cos(pitch);
            return new Vector3(
                -Mathf.Sin(yaw) * cosPitch,
                Mathf.Sin(pitch),
                -Mathf.Cos(yaw) * cosPitch).normalized;
        }

        private static Vector3 ResolveAutoRimVector(float direction)
        {
            // The recovered unpatched method passes this 0..1 value directly to sin/cos.
            return new Vector3(Mathf.Sin(direction), Mathf.Cos(direction), 0.0f);
        }

        private static Vector3 ResolveFaceRimVector(float direction)
        {
            return new Vector3(-Mathf.Sin(direction), 0.001f, -Mathf.Cos(direction));
        }

        private static Color AutoTintColor(Color color)
        {
            // Exact recovered HGCharacterVolume behavior for custom shadow tint:
            // preserve hue/saturation and normalize value to 2/(2-saturation).
            Color.RGBToHSV(color, out float hue, out float saturation, out _);
            Color result = Color.HSVToRGB(hue, saturation, 2.0f / Mathf.Max(2.0f - saturation, 1e-5f), true);
            result.a = color.a;
            return result;
        }

        private void PublishSemanticAliases(Light mainLight, float exposure)
        {
            Vector3 sceneDirection = mainLight != null
                ? (-mainLight.transform.forward).normalized
                : new Vector3(-0.433f, 0.5f, 0.75f).normalized;
            Color sceneColor = mainLight != null ? mainLight.color * mainLight.intensity : Color.white;
            Color resolvedMainColor = overrideMainLightColor ? mainLightOverrideColor : sceneColor;
            Color resolvedSkinColor = overrideSkinMainLightColor ? skinMainLightOverrideColor : resolvedMainColor;

            Shader.SetGlobalVector("_EndfieldCharSceneLightDirection",
                new Vector4(sceneDirection.x, sceneDirection.y, sceneDirection.z, 0.0f));
            Shader.SetGlobalColor("_EndfieldCharMainLightColor", resolvedMainColor);
            Shader.SetGlobalColor("_EndfieldCharSkinMainLightColor", resolvedSkinColor);
            Shader.SetGlobalFloat(
                CharacterMainLightIntensityId,
                ResolveCharacterMainLightIntensity(exposure));
            Shader.SetGlobalVector("_EndfieldCharLightingFactors",
                new Vector4(mainLightMultiplier, environmentLightMultiplier,
                    environmentShadowMultiplier, mainLightSpecularMultiplier));
            Shader.SetGlobalVector("_EndfieldCharAmbientFactors",
                new Vector4(ambientBaseIntensity, ambientDirectionalIntensity,
                    ambientDirectionalBias, ignoreSceneEnvironment ? 0.0f : 1.0f));
            Shader.SetGlobalVector("_EndfieldCharShadowFactors",
                new Vector4(ignoreMainLightShadow ? 0.0f : selfShadowStrength,
                    mainLightRangeBias, BoolFloat(dialogueLightingMode), 0.0f));
            Shader.SetGlobalVector("_EndfieldCharOutlineFactors",
                new Vector4(BoolFloat(enableCharacterOutline), outlineWidthMultiplier, outlineIntensity, 0.0f));
            Shader.SetGlobalColor("_EndfieldCharOutlineTint", outlineTint);
        }

        private float ResolveCharacterMainLightIntensity(float exposure)
        {
            if (!useRecoveredSourceMainLightDescriptor)
                return 1.0f;

            // Exact native LightExtensions.GetCharacterLightColorAndIntensity
            // scalar path. CharInfo's serialized direct RGB is white, so its
            // HSV normalization/correction is exactly one for this source.
            float intensity = Mathf.Max(sourceDirectIntensityDividePi, 0.0f) *
                              Mathf.Max(exposure, 0.0f);
            float clamped = Mathf.Clamp(intensity, 0.75f, 1.25f);
            float extensionScale = dialogueLightingMode ? 0.05f : 0.25f;
            return clamped +
                   Mathf.Max(intensity - 1.25f, 0.0f) * extensionScale -
                   Mathf.Max(0.75f - intensity, 0.0f) * extensionScale;
        }

        private static float BoolFloat(bool value)
        {
            return value ? 1.0f : 0.0f;
        }

        private static Vector4 ColorVector(Color color)
        {
            return new Vector4(color.r, color.g, color.b, color.a);
        }
    }
}

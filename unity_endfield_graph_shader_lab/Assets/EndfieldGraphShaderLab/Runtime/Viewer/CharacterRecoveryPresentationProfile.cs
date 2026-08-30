using System;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    [Serializable]
    public sealed class CharacterRecoveryLightingProfile
    {
        public int priority;
        public float compatibilityShaderInfluence = 1.0f;
        public bool manualCharacterLightControl = true;
        public EndfieldHGRPCharacterLightingVolume.CharacterLightMode mainLightMode;
        public Vector2 customMainLightAngles;
        public Vector2 cameraFollowLightBias;
        public float mainLightMultiplier;
        public float environmentLightMultiplier;
        public float environmentShadowMultiplier;
        public float mainLightSpecularMultiplier;
        public float mainLightRangeBias;
        public bool overrideMainLightRangeBias;
        public bool overrideMainLightColor;
        public Color mainLightOverrideColor = Color.white;
        public bool overrideSkinMainLightColor;
        public Color skinMainLightOverrideColor = Color.white;
        public Vector3 ambientDirection = Vector3.up;
        public float ambientBaseIntensity;
        public float ambientDirectionalIntensity;
        public float ambientDirectionalBias;
        public bool ignoreSceneEnvironment;
        public bool ignoreSceneAdditionalLights;
        public Vector4 environmentGlobalParams0;
        public bool ignoreMainLightShadow;
        public EndfieldHGRPCharacterLightingVolume.CharacterShadowTintMode shadowTintMode;
        public Color shadowTintColor = Color.white;
        public Color skinShadowTintColor = Color.white;
        public float selfShadowStrength = 1.0f;
        public bool dialogueLightingMode;
        public bool enableCharacterRim;
        public Color characterRimColor = Color.white;
        public float characterRimDirection;
        public float characterRimIntensity;
        public float characterRimWidth;
        public float characterRimAlbedoInfluence;
        public bool useNewCharacterRimMode;
        public bool enableFaceRim;
        public Color faceRimColor = Color.white;
        public float faceRimDirection;
        public float faceRimIntensity;
        public float eyeBaseLightMultiplier;
        public float eyeHighlightMultiplier;
        public float eyeScatteringMultiplier;
        public bool enableCharacterOutline = true;
        public float outlineWidthMultiplier = 1.0f;
        public float outlineIntensity = 1.0f;
        public Color outlineTint = Color.white;
        public Vector4 characterEnvironmentEffectOverride;
        public bool useRecoveredSourceMainLightDescriptor;
        public Color sourceDirectColor = Color.white;
        public float sourceDirectIntensityDividePi = 1.0f;
        public bool publishExposureGlobals = true;
        public float postExposureEV;

        public void CaptureFrom(EndfieldHGRPCharacterLightingVolume source)
        {
            if (source == null)
                throw new ArgumentNullException(nameof(source));

            priority = source.priority;
            compatibilityShaderInfluence = source.compatibilityShaderInfluence;
            manualCharacterLightControl = source.manualCharacterLightControl;
            mainLightMode = source.mainLightMode;
            customMainLightAngles = source.customMainLightAngles;
            cameraFollowLightBias = source.cameraFollowLightBias;
            mainLightMultiplier = source.mainLightMultiplier;
            environmentLightMultiplier = source.environmentLightMultiplier;
            environmentShadowMultiplier = source.environmentShadowMultiplier;
            mainLightSpecularMultiplier = source.mainLightSpecularMultiplier;
            mainLightRangeBias = source.mainLightRangeBias;
            overrideMainLightRangeBias = source.overrideMainLightRangeBias;
            overrideMainLightColor = source.overrideMainLightColor;
            mainLightOverrideColor = source.mainLightOverrideColor;
            overrideSkinMainLightColor = source.overrideSkinMainLightColor;
            skinMainLightOverrideColor = source.skinMainLightOverrideColor;
            ambientDirection = source.ambientDirection;
            ambientBaseIntensity = source.ambientBaseIntensity;
            ambientDirectionalIntensity = source.ambientDirectionalIntensity;
            ambientDirectionalBias = source.ambientDirectionalBias;
            ignoreSceneEnvironment = source.ignoreSceneEnvironment;
            ignoreSceneAdditionalLights = source.ignoreSceneAdditionalLights;
            environmentGlobalParams0 = source.environmentGlobalParams0;
            ignoreMainLightShadow = source.ignoreMainLightShadow;
            shadowTintMode = source.shadowTintMode;
            shadowTintColor = source.shadowTintColor;
            skinShadowTintColor = source.skinShadowTintColor;
            selfShadowStrength = source.selfShadowStrength;
            dialogueLightingMode = source.dialogueLightingMode;
            enableCharacterRim = source.enableCharacterRim;
            characterRimColor = source.characterRimColor;
            characterRimDirection = source.characterRimDirection;
            characterRimIntensity = source.characterRimIntensity;
            characterRimWidth = source.characterRimWidth;
            characterRimAlbedoInfluence = source.characterRimAlbedoInfluence;
            useNewCharacterRimMode = source.useNewCharacterRimMode;
            enableFaceRim = source.enableFaceRim;
            faceRimColor = source.faceRimColor;
            faceRimDirection = source.faceRimDirection;
            faceRimIntensity = source.faceRimIntensity;
            eyeBaseLightMultiplier = source.eyeBaseLightMultiplier;
            eyeHighlightMultiplier = source.eyeHighlightMultiplier;
            eyeScatteringMultiplier = source.eyeScatteringMultiplier;
            enableCharacterOutline = source.enableCharacterOutline;
            outlineWidthMultiplier = source.outlineWidthMultiplier;
            outlineIntensity = source.outlineIntensity;
            outlineTint = source.outlineTint;
            characterEnvironmentEffectOverride = source.characterEnvironmentEffectOverride;
            useRecoveredSourceMainLightDescriptor = source.useRecoveredSourceMainLightDescriptor;
            sourceDirectColor = source.sourceDirectColor;
            sourceDirectIntensityDividePi = source.sourceDirectIntensityDividePi;
            publishExposureGlobals = source.publishExposureGlobals;
            postExposureEV = source.postExposureEV;
        }

        public void ApplyTo(EndfieldHGRPCharacterLightingVolume target)
        {
            if (target == null)
                throw new ArgumentNullException(nameof(target));

            target.priority = priority;
            target.compatibilityShaderInfluence = compatibilityShaderInfluence;
            target.manualCharacterLightControl = manualCharacterLightControl;
            target.mainLightMode = mainLightMode;
            target.customMainLightAngles = customMainLightAngles;
            target.cameraFollowLightBias = cameraFollowLightBias;
            target.mainLightMultiplier = mainLightMultiplier;
            target.environmentLightMultiplier = environmentLightMultiplier;
            target.environmentShadowMultiplier = environmentShadowMultiplier;
            target.mainLightSpecularMultiplier = mainLightSpecularMultiplier;
            target.mainLightRangeBias = mainLightRangeBias;
            target.overrideMainLightRangeBias = overrideMainLightRangeBias;
            target.overrideMainLightColor = overrideMainLightColor;
            target.mainLightOverrideColor = mainLightOverrideColor;
            target.overrideSkinMainLightColor = overrideSkinMainLightColor;
            target.skinMainLightOverrideColor = skinMainLightOverrideColor;
            target.ambientDirection = ambientDirection;
            target.ambientBaseIntensity = ambientBaseIntensity;
            target.ambientDirectionalIntensity = ambientDirectionalIntensity;
            target.ambientDirectionalBias = ambientDirectionalBias;
            target.ignoreSceneEnvironment = ignoreSceneEnvironment;
            target.ignoreSceneAdditionalLights = ignoreSceneAdditionalLights;
            target.environmentGlobalParams0 = environmentGlobalParams0;
            target.ignoreMainLightShadow = ignoreMainLightShadow;
            target.shadowTintMode = shadowTintMode;
            target.shadowTintColor = shadowTintColor;
            target.skinShadowTintColor = skinShadowTintColor;
            target.selfShadowStrength = selfShadowStrength;
            target.dialogueLightingMode = dialogueLightingMode;
            target.enableCharacterRim = enableCharacterRim;
            target.characterRimColor = characterRimColor;
            target.characterRimDirection = characterRimDirection;
            target.characterRimIntensity = characterRimIntensity;
            target.characterRimWidth = characterRimWidth;
            target.characterRimAlbedoInfluence = characterRimAlbedoInfluence;
            target.useNewCharacterRimMode = useNewCharacterRimMode;
            target.enableFaceRim = enableFaceRim;
            target.faceRimColor = faceRimColor;
            target.faceRimDirection = faceRimDirection;
            target.faceRimIntensity = faceRimIntensity;
            target.eyeBaseLightMultiplier = eyeBaseLightMultiplier;
            target.eyeHighlightMultiplier = eyeHighlightMultiplier;
            target.eyeScatteringMultiplier = eyeScatteringMultiplier;
            target.enableCharacterOutline = enableCharacterOutline;
            target.outlineWidthMultiplier = outlineWidthMultiplier;
            target.outlineIntensity = outlineIntensity;
            target.outlineTint = outlineTint;
            target.characterEnvironmentEffectOverride = characterEnvironmentEffectOverride;
            target.useRecoveredSourceMainLightDescriptor = useRecoveredSourceMainLightDescriptor;
            target.sourceDirectColor = sourceDirectColor;
            target.sourceDirectIntensityDividePi = sourceDirectIntensityDividePi;
            target.publishExposureGlobals = publishExposureGlobals;
            target.postExposureEV = postExposureEV;
        }
    }

    [CreateAssetMenu(
        fileName = "CharacterRecoveryPresentationProfile",
        menuName = "Endfield/Character Recovery Presentation Profile")]
    public sealed class CharacterRecoveryPresentationProfile : ScriptableObject
    {
        [Header("Source identity")]
        public string schema = "endfield.playable-charinfo-presentation-profile.v1";
        public bool sourceRecovered;
        public string characterId = "";
        public string actorToken = "";
        public string rootName = "";
        public string displayName = "";
        public string cameraGroup = "";
        public string lightGroup = "";
        public TextAsset sourceManifest;

        [Header("Recovered Overview camera")]
        public Vector3 cameraPosition;
        public Vector3 lookAtPosition;
        public Quaternion authoredOverviewRotation = Quaternion.identity;
        public float fieldOfView = 20.0f;
        public float nearClip = 0.1f;
        public float farClip = 50.0f;
        public float referenceAspect = 16.0f / 9.0f;
        public Vector2 gyroscopeEntryOffsets;

        [Header("Recovered Overview portrait")]
        public Vector3 overviewImageOffset;
        public Texture2D portraitTexture;
        public Mesh portraitMesh;

        [Header("Recovered Overview lighting")]
        public CharacterRecoveryLightingProfile characterLighting =
            new CharacterRecoveryLightingProfile();
        public EndfieldHGOperatorLightData[] operatorLights =
            Array.Empty<EndfieldHGOperatorLightData>();
        [TextArea(2, 5)] public string characterLightingProvenance = "";
        [TextArea(2, 5)] public string operatorLightProvenance = "";
    }
}

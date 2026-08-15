using System;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Exact value/overrideState payload copied by HGCharacterVolume.SetCharLightVolumeData.
    /// The pinned body copies these 30 parameters once; it does not retain the source.
    /// </summary>
    [DisallowMultipleComponent]
    [AddComponentMenu("Endfield/Recovered/Character Light Volume Snapshot")]
    public sealed class EndfieldRecoveredCharLightVolumeSnapshot : MonoBehaviour
    {
        public const long GachaRoomCharacterVolumePathId = -6994529406646053790L;
        public const string GachaRoomCharacterVolumeRawSha256 =
            "d5e8137d2efe5619582c28baad7c776d1bc866564ac33ff4d8d43aac9189866f";

        [Serializable] public sealed class BoolParameter
        {
            public bool value;
            public bool overrideState;
        }

        [Serializable] public sealed class FloatParameter
        {
            public float value;
            public bool overrideState;
        }

        [Serializable] public sealed class IntParameter
        {
            public int value;
            public bool overrideState;
        }

        [Serializable] public sealed class Vector2Parameter
        {
            public Vector2 value;
            public bool overrideState;
        }

        [Serializable] public sealed class ColorParameter
        {
            public Color value = Color.white;
            public bool overrideState;
        }

        public BoolParameter charMainLightControl = new BoolParameter();
        public FloatParameter charMainLightMultiplier = new FloatParameter();
        public FloatParameter charEnvLightMultiplier = new FloatParameter();
        public FloatParameter charEnvShadowMultiplier = new FloatParameter();
        public FloatParameter charMainLightSpecularMultiplier = new FloatParameter();
        public FloatParameter charEyeBaseLightMultiplier = new FloatParameter();
        public FloatParameter charEyeHighlightMultiplier = new FloatParameter();
        public FloatParameter charEyeScatteringMultiplier = new FloatParameter();
        public FloatParameter charMainLightRangeBias = new FloatParameter();
        public BoolParameter charIgnoreMainLightShadow = new BoolParameter();
        public IntParameter charMainLightMode = new IntParameter();
        public Vector2Parameter charCameraFollowMainLightBias = new Vector2Parameter();
        public Vector2Parameter charCustomMainLightDir = new Vector2Parameter();
        public ColorParameter charMainLightOverrideColor = new ColorParameter();
        public ColorParameter charSkinMainLightOverrideColor = new ColorParameter();
        public BoolParameter charLightDialogMode = new BoolParameter();
        public IntParameter charShadowTintControl = new IntParameter();
        public ColorParameter charShadowTintColor = new ColorParameter();
        public ColorParameter charSkinShadowTintColor = new ColorParameter();
        public BoolParameter charAutoRimEnable = new BoolParameter();
        public ColorParameter charAutoRimColor = new ColorParameter();
        public FloatParameter charAutoRimDir = new FloatParameter();
        public FloatParameter charAutoRimIntensity = new FloatParameter();
        public FloatParameter charAutoRimWidth = new FloatParameter();
        public BoolParameter charFaceRimEnable = new BoolParameter();
        public FloatParameter charFaceRimIntensity = new FloatParameter();
        public ColorParameter charFaceRimColor = new ColorParameter();
        public FloatParameter charFaceRimDir = new FloatParameter();
        public BoolParameter charIgnoreSceneAdditionalLights = new BoolParameter();
        public BoolParameter charIgnoreSceneEnv = new BoolParameter();

        [NonSerialized] private int applyCount;
        public int ApplyCount => applyCount;

        public bool ResolveGachaAuthoredStackOnceTo(
            EndfieldHGRPCharacterLightingVolume destination)
        {
            if (destination == null)
                return false;

            ApplyExactGachaRoomPriority30000Base(destination);

            // SetCharLightVolumeData copied all 30 raw value/state pairs into the
            // priority-30001 profile. VolumeManager then contributes only fields
            // whose copied overrideState is true; inactive raw values remain
            // preserved above but are not final stack values.
            if (charMainLightControl.overrideState)
                destination.manualCharacterLightControl = charMainLightControl.value;
            if (charMainLightMultiplier.overrideState)
                destination.mainLightMultiplier = charMainLightMultiplier.value;
            if (charEnvLightMultiplier.overrideState)
                destination.environmentLightMultiplier = charEnvLightMultiplier.value;
            if (charEnvShadowMultiplier.overrideState)
                destination.environmentShadowMultiplier = charEnvShadowMultiplier.value;
            if (charMainLightSpecularMultiplier.overrideState)
                destination.mainLightSpecularMultiplier = charMainLightSpecularMultiplier.value;
            if (charEyeBaseLightMultiplier.overrideState)
                destination.eyeBaseLightMultiplier = charEyeBaseLightMultiplier.value;
            if (charEyeHighlightMultiplier.overrideState)
                destination.eyeHighlightMultiplier = charEyeHighlightMultiplier.value;
            if (charEyeScatteringMultiplier.overrideState)
                destination.eyeScatteringMultiplier = charEyeScatteringMultiplier.value;
            if (charMainLightRangeBias.overrideState)
            {
                destination.mainLightRangeBias = charMainLightRangeBias.value;
                destination.overrideMainLightRangeBias = true;
            }
            if (charIgnoreMainLightShadow.overrideState)
                destination.ignoreMainLightShadow = charIgnoreMainLightShadow.value;
            if (charMainLightMode.overrideState)
                destination.mainLightMode =
                    (EndfieldHGRPCharacterLightingVolume.CharacterLightMode)
                    charMainLightMode.value;
            if (charCameraFollowMainLightBias.overrideState)
                destination.cameraFollowLightBias = charCameraFollowMainLightBias.value;
            if (charCustomMainLightDir.overrideState)
                destination.customMainLightAngles = charCustomMainLightDir.value;
            if (charMainLightOverrideColor.overrideState)
            {
                destination.mainLightOverrideColor = charMainLightOverrideColor.value;
                destination.overrideMainLightColor = true;
            }
            if (charSkinMainLightOverrideColor.overrideState)
            {
                destination.skinMainLightOverrideColor = charSkinMainLightOverrideColor.value;
                destination.overrideSkinMainLightColor = true;
            }
            if (charLightDialogMode.overrideState)
                destination.dialogueLightingMode = charLightDialogMode.value;
            if (charShadowTintControl.overrideState)
                destination.shadowTintMode =
                    (EndfieldHGRPCharacterLightingVolume.CharacterShadowTintMode)
                    charShadowTintControl.value;
            if (charShadowTintColor.overrideState)
                destination.shadowTintColor = charShadowTintColor.value;
            if (charSkinShadowTintColor.overrideState)
                destination.skinShadowTintColor = charSkinShadowTintColor.value;
            if (charAutoRimEnable.overrideState)
                destination.enableCharacterRim = charAutoRimEnable.value;
            if (charAutoRimColor.overrideState)
                destination.characterRimColor = charAutoRimColor.value;
            if (charAutoRimDir.overrideState)
                destination.characterRimDirection = charAutoRimDir.value;
            if (charAutoRimIntensity.overrideState)
                destination.characterRimIntensity = charAutoRimIntensity.value;
            if (charAutoRimWidth.overrideState)
                destination.characterRimWidth = charAutoRimWidth.value;
            if (charFaceRimEnable.overrideState)
                destination.enableFaceRim = charFaceRimEnable.value;
            if (charFaceRimIntensity.overrideState)
                destination.faceRimIntensity = charFaceRimIntensity.value;
            if (charFaceRimColor.overrideState)
                destination.faceRimColor = charFaceRimColor.value;
            if (charFaceRimDir.overrideState)
                destination.faceRimDirection = charFaceRimDir.value;
            if (charIgnoreSceneAdditionalLights.overrideState)
                destination.ignoreSceneAdditionalLights =
                    charIgnoreSceneAdditionalLights.value;
            if (charIgnoreSceneEnv.overrideState)
                destination.ignoreSceneEnvironment = charIgnoreSceneEnv.value;
            applyCount++;
            return true;
        }

        private static void ApplyExactGachaRoomPriority30000Base(
            EndfieldHGRPCharacterLightingVolume destination)
        {
            // GachaRoom_Volume/HGCharacterVolume, global priority 30000,
            // weight 1. Only its 14 active fields in the 30-field transfer
            // domain are written. Lower world/default inputs remain untouched.
            destination.enableCharacterRim = false;
            destination.cameraFollowLightBias = new Vector2(32.0f, 10.0f);
            destination.environmentLightMultiplier = 0.8f;
            destination.environmentShadowMultiplier = 0.8f;
            destination.ignoreMainLightShadow = true;
            destination.ignoreSceneEnvironment = true;
            destination.manualCharacterLightControl = true;
            destination.mainLightMode =
                EndfieldHGRPCharacterLightingVolume.CharacterLightMode.CameraFollow;
            destination.mainLightMultiplier = 0.9f;
            destination.mainLightOverrideColor = Color.white;
            destination.overrideMainLightColor = true;
            destination.mainLightRangeBias = -0.4f;
            destination.overrideMainLightRangeBias = true;
            destination.shadowTintColor =
                new Color(0.7830188f, 0.8293082f, 1.0f, 1.0f);
            destination.shadowTintMode =
                EndfieldHGRPCharacterLightingVolume.CharacterShadowTintMode.CustomTintColor;
            destination.skinShadowTintColor =
                new Color(1.0f, 0.78114647f, 0.68490565f, 1.0f);
        }
    }
}

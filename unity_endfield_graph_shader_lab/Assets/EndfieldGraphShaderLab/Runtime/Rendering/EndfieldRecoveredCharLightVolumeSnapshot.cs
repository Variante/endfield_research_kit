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

        public bool ApplyOnceTo(EndfieldHGRPCharacterLightingVolume destination)
        {
            if (destination == null)
                return false;

            // Preserve the native call order even though these are value types in the lab.
            destination.manualCharacterLightControl = charMainLightControl.value;
            destination.mainLightMultiplier = charMainLightMultiplier.value;
            destination.environmentLightMultiplier = charEnvLightMultiplier.value;
            destination.environmentShadowMultiplier = charEnvShadowMultiplier.value;
            destination.mainLightSpecularMultiplier = charMainLightSpecularMultiplier.value;
            destination.eyeBaseLightMultiplier = charEyeBaseLightMultiplier.value;
            destination.eyeHighlightMultiplier = charEyeHighlightMultiplier.value;
            destination.eyeScatteringMultiplier = charEyeScatteringMultiplier.value;
            destination.mainLightRangeBias = charMainLightRangeBias.value;
            destination.ignoreMainLightShadow = charIgnoreMainLightShadow.value;
            destination.mainLightMode =
                (EndfieldHGRPCharacterLightingVolume.CharacterLightMode)charMainLightMode.value;
            destination.cameraFollowLightBias = charCameraFollowMainLightBias.value;
            destination.customMainLightAngles = charCustomMainLightDir.value;
            destination.mainLightOverrideColor = charMainLightOverrideColor.value;
            destination.skinMainLightOverrideColor = charSkinMainLightOverrideColor.value;
            destination.dialogueLightingMode = charLightDialogMode.value;
            destination.shadowTintMode =
                (EndfieldHGRPCharacterLightingVolume.CharacterShadowTintMode)
                charShadowTintControl.value;
            destination.shadowTintColor = charShadowTintColor.value;
            destination.skinShadowTintColor = charSkinShadowTintColor.value;
            destination.enableCharacterRim = charAutoRimEnable.value;
            destination.characterRimColor = charAutoRimColor.value;
            destination.characterRimDirection = charAutoRimDir.value;
            destination.characterRimIntensity = charAutoRimIntensity.value;
            destination.characterRimWidth = charAutoRimWidth.value;
            destination.enableFaceRim = charFaceRimEnable.value;
            destination.faceRimIntensity = charFaceRimIntensity.value;
            destination.faceRimColor = charFaceRimColor.value;
            destination.faceRimDirection = charFaceRimDir.value;
            destination.ignoreSceneAdditionalLights = charIgnoreSceneAdditionalLights.value;
            destination.ignoreSceneEnvironment = charIgnoreSceneEnv.value;

            // The compatibility publisher does not implement Unity's Volume stack.
            // Keep every recovered overrideState as evidence; expose only the three
            // override selectors that the current publisher represents explicitly.
            destination.overrideMainLightRangeBias = charMainLightRangeBias.overrideState;
            destination.overrideMainLightColor = charMainLightOverrideColor.overrideState;
            destination.overrideSkinMainLightColor =
                charSkinMainLightOverrideColor.overrideState;
            applyCount++;
            return true;
        }
    }
}

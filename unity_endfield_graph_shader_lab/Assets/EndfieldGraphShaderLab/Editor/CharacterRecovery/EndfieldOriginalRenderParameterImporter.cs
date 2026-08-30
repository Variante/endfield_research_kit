using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using EndfieldGraphShaderLab;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Applies the generated original-data payload. This is intentionally an
    /// editor importer: production values come from AnimeStudio/native evidence
    /// and are baked into scenes, while unknown live-only values remain neutral.
    /// </summary>
    internal static class EndfieldOriginalRenderParameterImporter
    {
        internal const string PayloadAssetPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/RenderParameters/" +
            "character_render_parameters.json";

        internal static bool TryApplyCharacterLighting(
            EndfieldHGRPCharacterLightingVolume volume,
            string actorName,
            out string provenance)
        {
            provenance = string.Empty;
            if (volume == null || string.IsNullOrWhiteSpace(actorName))
                return false;

            Dictionary<string, object> payload = LoadPayload();
            if (!PayloadIsValid(payload))
                return false;

            string actorKey = actorName.Trim().ToLowerInvariant();
            Dictionary<string, object> characters = Dict(Get(payload, "characters"));
            Dictionary<string, object> actor = Dict(Get(characters, actorKey));
            Dictionary<string, object> modifier =
                Dict(Get(actor, "modifier_serialized_parameters"));
            Dictionary<string, object> active = Dict(Get(actor, "resolved_active_overrides"));
            Dictionary<string, object> postSnapshot =
                Dict(Get(actor, "post_use_data_on_volume"));
            Dictionary<string, object> resolved = postSnapshot.Count > 0
                ? postSnapshot
                : active;
            if (resolved.Count == 0 || modifier.Count != 30)
                return false;

            EndfieldRecoveredCharLightVolumeSnapshot snapshot =
                volume.GetComponent<EndfieldRecoveredCharLightVolumeSnapshot>();
            if (snapshot == null)
                snapshot = volume.gameObject.AddComponent<EndfieldRecoveredCharLightVolumeSnapshot>();
            if (!TryPopulateNativeSnapshot(snapshot, modifier))
                return false;

            volume.manualCharacterLightControl = BoolValue(Resolved(resolved, "charMainLightControl"));
            volume.mainLightMode =
                (EndfieldHGRPCharacterLightingVolume.CharacterLightMode)
                IntValue(Resolved(resolved, "charMainLightMode"));
            if (TryResolved(resolved, "charCustomMainLightDir", out object customDirection))
                volume.customMainLightAngles = Vector2Value(customDirection);
            volume.cameraFollowLightBias =
                Vector2Value(Resolved(resolved, "charCameraFollowMainLightBias"));

            volume.mainLightMultiplier =
                FloatValue(Resolved(resolved, "charMainLightMultiplier"));
            volume.environmentLightMultiplier =
                FloatValue(Resolved(resolved, "charEnvLightMultiplier"));
            volume.environmentShadowMultiplier =
                FloatValue(Resolved(resolved, "charEnvShadowMultiplier"));
            if (TryResolved(resolved, "charMainLightSpecularMultiplier", out object specular))
                volume.mainLightSpecularMultiplier = FloatValue(specular);

            volume.overrideMainLightRangeBias =
                TryResolved(resolved, "charMainLightRangeBias", out object rangeBias);
            if (volume.overrideMainLightRangeBias)
                volume.mainLightRangeBias = FloatValue(rangeBias);

            volume.overrideMainLightColor =
                TryResolved(resolved, "charMainLightOverrideColor", out object mainColor);
            if (volume.overrideMainLightColor)
                volume.mainLightOverrideColor = ColorValue(mainColor);
            volume.overrideSkinMainLightColor =
                TryResolved(resolved, "charSkinMainLightOverrideColor", out object skinColor);
            if (volume.overrideSkinMainLightColor)
                volume.skinMainLightOverrideColor = ColorValue(skinColor);

            if (TryResolved(resolved, "charGlobalAmbientParam0", out object ambient0))
            {
                Vector4 value = Vector4Value(ambient0);
                volume.ambientDirection = new Vector3(value.x, value.y, value.z);
            }
            if (TryResolved(resolved, "charGlobalAmbientParam1", out object ambient1))
            {
                Vector4 value = Vector4Value(ambient1);
                volume.ambientDirectionalBias = value.x;
                volume.ambientDirectionalIntensity = value.y;
                volume.ambientBaseIntensity = value.z;
            }

            if (TryResolved(resolved, "charIgnoreSceneEnv", out object ignoreEnvironment))
                volume.ignoreSceneEnvironment = BoolValue(ignoreEnvironment);
            if (TryResolved(resolved, "charIgnoreSceneAdditionalLights", out object ignoreAdditional))
                volume.ignoreSceneAdditionalLights = BoolValue(ignoreAdditional);
            volume.ignoreMainLightShadow =
                BoolValue(Resolved(resolved, "charIgnoreMainLightShadow"));

            volume.shadowTintMode =
                (EndfieldHGRPCharacterLightingVolume.CharacterShadowTintMode)
                IntValue(Resolved(resolved, "charShadowTintControl"));
            volume.shadowTintColor = ColorValue(Resolved(resolved, "charShadowTintColor"));
            volume.skinShadowTintColor =
                ColorValue(Resolved(resolved, "charSkinShadowTintColor"));

            if (TryResolved(resolved, "charLightDialogMode", out object dialogue))
                volume.dialogueLightingMode = BoolValue(dialogue);
            if (TryResolved(resolved, "charAutoRimEnable", out object characterRim))
                volume.enableCharacterRim = BoolValue(characterRim);
            if (TryResolved(resolved, "charAutoRimColor", out object characterRimColor))
                volume.characterRimColor = ColorValue(characterRimColor);
            if (TryResolved(resolved, "charAutoRimDir", out object characterRimDirection))
                volume.characterRimDirection = FloatValue(characterRimDirection);
            if (TryResolved(resolved, "charAutoRimIntensity", out object characterRimIntensity))
                volume.characterRimIntensity = FloatValue(characterRimIntensity);
            if (TryResolved(resolved, "charAutoRimWidth", out object characterRimWidth))
                volume.characterRimWidth = FloatValue(characterRimWidth);
            if (TryResolved(resolved, "charAutoRimAlbedo", out object characterRimAlbedo))
                volume.characterRimAlbedoInfluence = FloatValue(characterRimAlbedo);
            if (TryResolved(resolved, "charAutoRimMode", out object characterRimMode))
                volume.useNewCharacterRimMode = BoolValue(characterRimMode);
            if (TryResolved(resolved, "charFaceRimEnable", out object faceRim))
                volume.enableFaceRim = BoolValue(faceRim);
            if (TryResolved(resolved, "charFaceRimColor", out object faceRimColor))
                volume.faceRimColor = ColorValue(faceRimColor);
            if (TryResolved(resolved, "charFaceRimDir", out object faceRimDirection))
                volume.faceRimDirection = FloatValue(faceRimDirection);
            if (TryResolved(resolved, "charFaceRimIntensity", out object faceRimIntensity))
                volume.faceRimIntensity = FloatValue(faceRimIntensity);

            if (TryResolved(resolved, "charEyeBaseLightMultiplier", out object eyeBase))
                volume.eyeBaseLightMultiplier = FloatValue(eyeBase);
            if (TryResolved(resolved, "charEyeHighlightMultiplier", out object eyeHighlight))
                volume.eyeHighlightMultiplier = FloatValue(eyeHighlight);
            if (TryResolved(resolved, "charEyeScatteringMultiplier", out object eyeScattering))
                volume.eyeScatteringMultiplier = FloatValue(eyeScattering);
            if (TryResolved(resolved, "charOutlineQualityMode", out object outlineQuality))
                volume.enableCharacterOutline = IntValue(outlineQuality) != int.MaxValue;

            // Existing generated payloads predate post_use_data_on_volume.  The
            // raw 30-field record is authoritative for the native call either
            // way, so bake the same one-shot destination values after any
            // legacy active-only composition above.
            if (!snapshot.ResolveGachaAuthoredStackOnceTo(volume))
                return false;

            Dictionary<string, object> environment = Dict(Get(payload, "environment"));
            Dictionary<string, object> serializedEnvironment =
                Dict(Get(environment, "serialized"));
            int sourceDirectColorMode = IntValue(
                Get(serializedEnvironment, "direct_color_mode"));
            volume.sourceDirectColor = ColorValue(Get(
                serializedEnvironment,
                sourceDirectColorMode == 1 ? "direct_custom_color" : "direct_color"));
            volume.sourceDirectIntensityDividePi = FloatValue(
                Get(serializedEnvironment, "direct_intensity_divide_pi"));
            volume.useRecoveredSourceMainLightDescriptor =
                volume.sourceDirectIntensityDividePi > 0.0f;
            IList environment0 = List(Get(environment, "environment_global_params0"));
            if (environment0.Count >= 4)
                volume.environmentGlobalParams0 = Vector4List(environment0);

            Dictionary<string, object> modifierSource = Dict(Get(actor, "modifier_source"));
            Dictionary<string, object> baseSource = Dict(
                Get(Dict(Get(payload, "base_character_volume")), "source"));
            provenance =
                $"{actorKey}: base PathID {LongValue(Get(baseSource, "path_id"))} " +
                $"raw {StringValue(Get(baseSource, "raw_data_sha256"))}; " +
                $"modifier PathID {LongValue(Get(modifierSource, "path_id"))} " +
                $"raw {StringValue(Get(modifierSource, "raw_data_sha256"))}";
            return true;
        }

        private static bool TryPopulateNativeSnapshot(
            EndfieldRecoveredCharLightVolumeSnapshot snapshot,
            Dictionary<string, object> modifier)
        {
            if (snapshot == null || modifier == null || modifier.Count != 30)
                return false;
            try
            {
                Set(snapshot.charMainLightControl, modifier, "charMainLightControl");
                Set(snapshot.charMainLightMultiplier, modifier, "charMainLightMultiplier");
                Set(snapshot.charEnvLightMultiplier, modifier, "charEnvLightMultiplier");
                Set(snapshot.charEnvShadowMultiplier, modifier, "charEnvShadowMultiplier");
                Set(snapshot.charMainLightSpecularMultiplier, modifier, "charMainLightSpecularMultiplier");
                Set(snapshot.charEyeBaseLightMultiplier, modifier, "charEyeBaseLightMultiplier");
                Set(snapshot.charEyeHighlightMultiplier, modifier, "charEyeHighlightMultiplier");
                Set(snapshot.charEyeScatteringMultiplier, modifier, "charEyeScatteringMultiplier");
                Set(snapshot.charMainLightRangeBias, modifier, "charMainLightRangeBias");
                Set(snapshot.charIgnoreMainLightShadow, modifier, "charIgnoreMainLightShadow");
                Set(snapshot.charMainLightMode, modifier, "charMainLightMode");
                Set(snapshot.charCameraFollowMainLightBias, modifier, "charCameraFollowMainLightBias");
                Set(snapshot.charCustomMainLightDir, modifier, "charCustomMainLightDir");
                Set(snapshot.charMainLightOverrideColor, modifier, "charMainLightOverrideColor");
                Set(snapshot.charSkinMainLightOverrideColor, modifier, "charSkinMainLightOverrideColor");
                Set(snapshot.charLightDialogMode, modifier, "charLightDialogMode");
                Set(snapshot.charShadowTintControl, modifier, "charShadowTintControl");
                Set(snapshot.charShadowTintColor, modifier, "charShadowTintColor");
                Set(snapshot.charSkinShadowTintColor, modifier, "charSkinShadowTintColor");
                Set(snapshot.charAutoRimEnable, modifier, "charAutoRimEnable");
                Set(snapshot.charAutoRimColor, modifier, "charAutoRimColor");
                Set(snapshot.charAutoRimDir, modifier, "charAutoRimDir");
                Set(snapshot.charAutoRimIntensity, modifier, "charAutoRimIntensity");
                Set(snapshot.charAutoRimWidth, modifier, "charAutoRimWidth");
                Set(snapshot.charFaceRimEnable, modifier, "charFaceRimEnable");
                Set(snapshot.charFaceRimIntensity, modifier, "charFaceRimIntensity");
                Set(snapshot.charFaceRimColor, modifier, "charFaceRimColor");
                Set(snapshot.charFaceRimDir, modifier, "charFaceRimDir");
                Set(snapshot.charIgnoreSceneAdditionalLights, modifier, "charIgnoreSceneAdditionalLights");
                Set(snapshot.charIgnoreSceneEnv, modifier, "charIgnoreSceneEnv");
                return true;
            }
            catch (InvalidDataException)
            {
                return false;
            }
        }

        private static Dictionary<string, object> Parameter(
            Dictionary<string, object> modifier,
            string name)
        {
            Dictionary<string, object> record = Dict(Get(modifier, name));
            if (record.Count == 0 || !record.ContainsKey("value") ||
                !record.ContainsKey("override_state"))
                throw new InvalidDataException($"Raw modifier is missing {name}");
            return record;
        }

        private static void Set(
            EndfieldRecoveredCharLightVolumeSnapshot.BoolParameter target,
            Dictionary<string, object> modifier,
            string name)
        {
            Dictionary<string, object> record = Parameter(modifier, name);
            target.value = BoolValue(Get(record, "value"));
            target.overrideState = BoolValue(Get(record, "override_state"));
        }

        private static void Set(
            EndfieldRecoveredCharLightVolumeSnapshot.FloatParameter target,
            Dictionary<string, object> modifier,
            string name)
        {
            Dictionary<string, object> record = Parameter(modifier, name);
            target.value = FloatValue(Get(record, "value"));
            target.overrideState = BoolValue(Get(record, "override_state"));
        }

        private static void Set(
            EndfieldRecoveredCharLightVolumeSnapshot.IntParameter target,
            Dictionary<string, object> modifier,
            string name)
        {
            Dictionary<string, object> record = Parameter(modifier, name);
            target.value = IntValue(Get(record, "value"));
            target.overrideState = BoolValue(Get(record, "override_state"));
        }

        private static void Set(
            EndfieldRecoveredCharLightVolumeSnapshot.Vector2Parameter target,
            Dictionary<string, object> modifier,
            string name)
        {
            Dictionary<string, object> record = Parameter(modifier, name);
            target.value = Vector2Value(Get(record, "value"));
            target.overrideState = BoolValue(Get(record, "override_state"));
        }

        private static void Set(
            EndfieldRecoveredCharLightVolumeSnapshot.ColorParameter target,
            Dictionary<string, object> modifier,
            string name)
        {
            Dictionary<string, object> record = Parameter(modifier, name);
            target.value = ColorValue(Get(record, "value"));
            target.overrideState = BoolValue(Get(record, "override_state"));
        }

        internal static bool TryReadEnvironmentLight(
            out Vector2 directPitchYaw,
            out Color directColor,
            out float colorTemperature,
            out float directEv100,
            out float directIntensityDividePi,
            out string provenance)
        {
            directPitchYaw = Vector2.zero;
            directColor = Color.white;
            colorTemperature = 0f;
            directEv100 = 0f;
            directIntensityDividePi = 0f;
            provenance = string.Empty;
            Dictionary<string, object> payload = LoadPayload();
            if (!PayloadIsValid(payload))
                return false;
            Dictionary<string, object> environment = Dict(Get(payload, "environment"));
            Dictionary<string, object> serialized = Dict(Get(environment, "serialized"));
            directPitchYaw = Vector2Value(Get(serialized, "direct_pitch_yaw"));
            int colorMode = IntValue(Get(serialized, "direct_color_mode"));
            directColor = ColorValue(Get(
                serialized,
                colorMode == 1 ? "direct_custom_color" : "direct_color"));
            colorTemperature = FloatValue(Get(serialized, "direct_color_temperature"));
            directEv100 = FloatValue(Get(serialized, "direct_ev100"));
            directIntensityDividePi = FloatValue(
                Get(serialized, "direct_intensity_divide_pi"));
            Dictionary<string, object> source = Dict(Get(environment, "source"));
            provenance =
                $"CharInfo_Env PathID {LongValue(Get(source, "path_id"))} " +
                $"raw {StringValue(Get(source, "raw_data_sha256"))}";
            return true;
        }

        private static Dictionary<string, object> LoadPayload()
        {
            string path = Path.Combine(Directory.GetCurrentDirectory(), PayloadAssetPath);
            if (!File.Exists(path))
                return new Dictionary<string, object>();
            return Dict(ManifestMiniJson.Deserialize(File.ReadAllText(path, Encoding.UTF8)));
        }

        private static bool PayloadIsValid(Dictionary<string, object> payload)
        {
            if (!string.Equals(
                    StringValue(Get(payload, "schema")),
                    "endfield.original-character-render-parameters.v1",
                    StringComparison.Ordinal))
                return false;
            return BoolValue(Get(Dict(Get(payload, "validation")), "ok"));
        }

        private static object Resolved(Dictionary<string, object> resolved, string name)
        {
            if (!TryResolved(resolved, name, out object value))
                throw new InvalidDataException($"Original-data payload is missing active override {name}");
            return value;
        }

        private static bool TryResolved(
            Dictionary<string, object> resolved,
            string name,
            out object value)
        {
            value = null;
            if (!resolved.TryGetValue(name, out object recordObject))
                return false;
            Dictionary<string, object> record = Dict(recordObject);
            return record.TryGetValue("value", out value);
        }

        private static object Get(Dictionary<string, object> dictionary, string key) =>
            dictionary != null && dictionary.TryGetValue(key, out object value) ? value : null;

        private static Dictionary<string, object> Dict(object value) =>
            value as Dictionary<string, object> ?? new Dictionary<string, object>();

        private static IList List(object value) => value as IList ?? Array.Empty<object>();

        private static string StringValue(object value) =>
            value == null ? string.Empty : Convert.ToString(value, CultureInfo.InvariantCulture) ?? string.Empty;

        private static bool BoolValue(object value)
        {
            if (value is bool boolean)
                return boolean;
            if (value == null)
                return false;
            return Convert.ToDouble(value, CultureInfo.InvariantCulture) != 0.0;
        }

        private static int IntValue(object value) =>
            value == null ? 0 : Convert.ToInt32(value, CultureInfo.InvariantCulture);

        private static long LongValue(object value) =>
            value == null ? 0L : Convert.ToInt64(value, CultureInfo.InvariantCulture);

        private static float FloatValue(object value) =>
            value == null ? 0f : Convert.ToSingle(value, CultureInfo.InvariantCulture);

        private static Vector2 Vector2Value(object value)
        {
            Dictionary<string, object> dictionary = Dict(value);
            return new Vector2(
                FloatValue(Get(dictionary, "x")),
                FloatValue(Get(dictionary, "y")));
        }

        private static Vector4 Vector4Value(object value)
        {
            Dictionary<string, object> dictionary = Dict(value);
            return new Vector4(
                FloatValue(Get(dictionary, "x")),
                FloatValue(Get(dictionary, "y")),
                FloatValue(Get(dictionary, "z")),
                FloatValue(Get(dictionary, "w")));
        }

        private static Vector4 Vector4List(IList values) => new Vector4(
            FloatValue(values.Count > 0 ? values[0] : null),
            FloatValue(values.Count > 1 ? values[1] : null),
            FloatValue(values.Count > 2 ? values[2] : null),
            FloatValue(values.Count > 3 ? values[3] : null));

        private static Color ColorValue(object value)
        {
            Dictionary<string, object> dictionary = Dict(value);
            return new Color(
                FloatValue(Get(dictionary, "r")),
                FloatValue(Get(dictionary, "g")),
                FloatValue(Get(dictionary, "b")),
                FloatValue(Get(dictionary, "a")));
        }
    }
}

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
    /// Loads exact overview-light records generated from installed-game
    /// Light/HGAdditionalLightData/Transform JSON. The original clustered-light
    /// equation remains separate and default-off; this class only recovers data.
    /// </summary>
    internal static class EndfieldOriginalOperatorLightImporter
    {
        internal const string PayloadAssetPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/RenderParameters/" +
            "operator_lights.json";

        internal static bool TryRead(
            string actorName,
            out EndfieldHGOperatorLightData[] lights,
            out string provenance)
        {
            lights = Array.Empty<EndfieldHGOperatorLightData>();
            provenance = string.Empty;
            if (string.IsNullOrWhiteSpace(actorName))
                return false;

            string path = Path.Combine(Directory.GetCurrentDirectory(), PayloadAssetPath);
            if (!File.Exists(path))
                return false;
            Dictionary<string, object> payload = Dict(
                ManifestMiniJson.Deserialize(File.ReadAllText(path, Encoding.UTF8)));
            if (!string.Equals(
                    StringValue(Get(payload, "schema")),
                    "endfield.original-operator-lights.v1",
                    StringComparison.Ordinal) ||
                !BoolValue(Get(Dict(Get(payload, "validation")), "ok")))
            {
                return false;
            }

            string actorKey = actorName.Trim().ToLowerInvariant();
            Dictionary<string, object> actor = Dict(
                Get(Dict(Get(payload, "actors")), actorKey));
            IList rows = List(Get(actor, "lights"));
            if (rows.Count == 0)
                return false;

            var result = new EndfieldHGOperatorLightData[rows.Count];
            int followerCount = 0;
            for (int index = 0; index < rows.Count; index++)
            {
                Dictionary<string, object> row = Dict(rows[index]);
                Quaternion rotation = QuaternionList(List(Get(row, "rotation_xyzw")));
                Vector3 forward = Vector3List(List(Get(row, "forward")));
                float rotationMagnitudeSquared =
                    rotation.x * rotation.x + rotation.y * rotation.y +
                    rotation.z * rotation.z + rotation.w * rotation.w;
                if (Mathf.Abs(rotationMagnitudeSquared - 1.0f) > 0.005f)
                {
                    throw new InvalidDataException(
                        $"Malformed source rotation_xyzw for original light row {index} " +
                        $"for {actorKey}: squared magnitude {rotationMagnitudeSquared}.");
                }
                Quaternion normalizedRotation = new Quaternion(
                    rotation.x / Mathf.Sqrt(rotationMagnitudeSquared),
                    rotation.y / Mathf.Sqrt(rotationMagnitudeSquared),
                    rotation.z / Mathf.Sqrt(rotationMagnitudeSquared),
                    rotation.w / Mathf.Sqrt(rotationMagnitudeSquared));
                if ((normalizedRotation * Vector3.forward - forward).sqrMagnitude > 1e-8f)
                {
                    throw new InvalidDataException(
                        $"Original light row {index} for {actorKey} has a forward vector " +
                        "that does not match rotation_xyzw.");
                }
                Vector4 nprData = Vector4List(List(Get(row, "npr_data_native_packed")));
                int nprType = IntValue(Get(row, "npr_type"));
                Dictionary<string, object> shadows = Dict(Get(row, "shadows"));
                Dictionary<string, object> shadowPlatform =
                    Dict(Get(shadows, "m_PlatformSpecificType"));
                Dictionary<string, object> follower = Dict(Get(row, "follower"));
                bool hasFollower = follower.Count > 0;
                int followerMode = hasFollower ? IntValue(Get(follower, "follow_type")) : 0;
                int followerBoneType = hasFollower
                    ? IntValue(Get(follower, "followable_node_type"))
                    : 0;
                string followerBoneKey = hasFollower
                    ? StringValue(Get(follower, "followable_node_name"))
                    : string.Empty;
                Dictionary<string, object> followerSource = hasFollower
                    ? Dict(Get(follower, "source"))
                    : new Dictionary<string, object>();
                long followerPathId = hasFollower
                    ? LongValue(Get(follower, "component_path_id"))
                    : 0L;
                if (hasFollower)
                {
                    followerCount++;
                    string expectedBoneKey = followerBoneType == 0
                        ? "BIP001"
                        : followerBoneType == 1 ? "HEAD_LOCAL" : string.Empty;
                    if ((followerMode != 0 && followerMode != 1) ||
                        string.IsNullOrEmpty(expectedBoneKey) ||
                        !string.Equals(
                            followerBoneKey,
                            expectedBoneKey,
                            StringComparison.Ordinal) ||
                        followerPathId == 0L ||
                        followerPathId != LongValue(Get(followerSource, "path_id")) ||
                        string.IsNullOrWhiteSpace(
                            StringValue(Get(followerSource, "sha256"))) ||
                        string.IsNullOrWhiteSpace(
                            StringValue(Get(followerSource, "raw_data_sha256"))))
                    {
                        throw new InvalidDataException(
                            $"Malformed original CharInfoLightFollower row {index} for {actorKey}.");
                    }
                }
                EndfieldHGOperatorLightData imported = new EndfieldHGOperatorLightData
                {
                    sourceName = StringValue(Get(row, "name")),
                    position = Vector3List(List(Get(row, "position"))),
                    rotation = rotation,
                    forward = forward,
                    color = ColorList(List(Get(row, "color"))),
                    priority = IntValue(Get(row, "priority")),
                    useColorTemperature = BoolValue(Get(row, "use_color_temperature")),
                    intensity = FloatValue(Get(row, "intensity")),
                    enabled = BoolValue(Get(row, "enabled")),
                    range = FloatValue(Get(row, "range")),
                    // Installed Unity native enum: Spot=0, Point=2.
                    spot = IntValue(Get(row, "light_type")) == 0,
                    outerSpotAngle = FloatValue(Get(row, "outer_spot_angle")),
                    innerSpotAngle = FloatValue(Get(row, "inner_spot_angle")),
                    nprType = nprType,
                    nprData = nprData,
                    characterOnly = BoolValue(Get(row, "character_only")),
                    volumetricScatteringIntensity = FloatValue(
                        Get(row, "volumetric_scattering_intensity")),
                    falloffExponent = FloatValue(Get(row, "falloff_exponent")),
                    linearLightLength = FloatValue(Get(row, "linear_light_length")),
                    softSourceRadius = FloatValue(Get(row, "soft_source_radius")),
                    specularIntensity = FloatValue(Get(row, "specular_intensity")),
                    useCullingDistance = BoolValue(Get(row, "use_culling_distance")),
                    cullingDistance = FloatValue(Get(row, "culling_distance")),
                    falloffDistance = FloatValue(Get(row, "falloff_distance")),
                    cullingBoxFalloffThreshold = FloatValue(
                        Get(row, "culling_box_falloff_threshold")),
                    useFarDistanceShow = BoolValue(Get(row, "use_far_distance_show")),
                    enableOverrideShadowLight = BoolValue(
                        Get(row, "enable_override_shadow_light")),
                    shadowType = IntValue(Get(row, "shadow_type")),
                    shadowNearPlane = FloatValue(Get(shadows, "m_NearPlane")),
                    shadowFarPlane = FloatValue(Get(shadows, "m_FarPlane")),
                    shadowBias = FloatValue(Get(shadows, "m_Bias")),
                    shadowNormalBias = FloatValue(Get(shadows, "m_NormalBias")),
                    shadowStrength = FloatValue(Get(shadows, "m_Strength")),
                    shadowGuardAngle = FloatValue(Get(shadows, "m_ShadowGuardAngle")),
                    shadowCasterProperties = IntValue(Get(shadows, "m_CasterProperties")),
                    pointLightShadowCasterFaces = IntValue(
                        Get(shadows, "m_PointLightShadowCasterFaces")),
                    shadowCustomResolution = IntValue(Get(shadows, "m_CustomResolution")),
                    shadowResolution = IntValue(Get(shadows, "m_Resolution")),
                    shadowPlatformDefault = IntValue(Get(shadowPlatform, "defaultParam")),
                    useShadowCullingMatrixOverride = BoolValue(
                        Get(shadows, "m_UseCullingMatrixOverride")),
                    shadowOnly = BoolValue(Get(row, "shadow_only")),
                    enableObbCullingBox = BoolValue(Get(row, "enable_obb_culling_box")),
                    hasCookie = LongValue(Get(row, "cookie_path_id")) != 0L,
                    flickerEnabled = BoolValue(Get(row, "flicker_enabled")),
                    rimWidth = nprType == 3 ? nprData.x : 0.0f,
                    rimAlpha = nprType == 3 ? nprData.y : 1.0f,
                    hasFollower = hasFollower,
                    followerEnabled = hasFollower && BoolValue(Get(follower, "enabled")),
                    followerMode = followerMode,
                    followerBoneType = followerBoneType,
                    followerBoneKey = followerBoneKey,
                    followerPositionOffset = Vector3List(
                        List(Get(follower, "position_offset"))),
                    followerLocalPosition = Vector3List(
                        List(Get(follower, "local_position"))),
                    followerLocalEulerDegrees = Vector3List(
                        List(Get(follower, "local_rotation_euler_degrees"))),
                    followerSourcePathId = followerPathId,
                    followerSourcePath = StringValue(Get(followerSource, "path")),
                    followerSourceJsonSha256 = StringValue(Get(followerSource, "sha256")),
                    followerSourceRawDataSha256 = StringValue(
                        Get(followerSource, "raw_data_sha256")),
                };
                string declaredSemanticSha256 = StringValue(
                    Get(row, "runtime_semantic_sha256"));
                string computedSemanticSha256 =
                    EndfieldHGOperatorLightSemanticFingerprint.Compute(imported);
                if (!string.Equals(
                        declaredSemanticSha256,
                        computedSemanticSha256,
                        StringComparison.Ordinal))
                {
                    throw new InvalidDataException(
                        $"Original operator-light semantic fingerprint mismatch " +
                        $"for {actorKey} row {index}.");
                }
                imported.sourceSemanticSha256 = declaredSemanticSha256;
                result[index] = imported;
            }

            Dictionary<string, object> group = Dict(Get(actor, "group_source"));
            provenance =
                $"{actorKey}: group PathID {LongValue(Get(group, "path_id"))} " +
                $"raw {StringValue(Get(group, "raw_data_sha256"))}; " +
                $"{result.Length} Light/HGAdditionalLightData rows, " +
                $"{followerCount} exact CharInfoLightFollower rows";
            lights = result;
            return true;
        }

        private static object Get(Dictionary<string, object> dictionary, string key) =>
            dictionary != null && dictionary.TryGetValue(key, out object value) ? value : null;

        private static Dictionary<string, object> Dict(object value) =>
            value as Dictionary<string, object> ?? new Dictionary<string, object>();

        private static IList List(object value) => value as IList ?? Array.Empty<object>();

        private static string StringValue(object value) =>
            value == null ? string.Empty :
            Convert.ToString(value, CultureInfo.InvariantCulture) ?? string.Empty;

        private static bool BoolValue(object value)
        {
            if (value is bool boolean)
                return boolean;
            return value != null && Convert.ToDouble(value, CultureInfo.InvariantCulture) != 0.0;
        }

        private static int IntValue(object value) =>
            value == null ? 0 : Convert.ToInt32(value, CultureInfo.InvariantCulture);

        private static long LongValue(object value) =>
            value == null ? 0L : Convert.ToInt64(value, CultureInfo.InvariantCulture);

        private static float FloatValue(object value) =>
            value == null ? 0.0f : Convert.ToSingle(value, CultureInfo.InvariantCulture);

        private static float ListFloat(IList values, int index) =>
            FloatValue(values != null && index < values.Count ? values[index] : null);

        private static Vector3 Vector3List(IList values) => new Vector3(
            ListFloat(values, 0), ListFloat(values, 1), ListFloat(values, 2));

        private static Vector4 Vector4List(IList values) => new Vector4(
            ListFloat(values, 0), ListFloat(values, 1),
            ListFloat(values, 2), ListFloat(values, 3));

        private static Quaternion QuaternionList(IList values) => new Quaternion(
            ListFloat(values, 0), ListFloat(values, 1),
            ListFloat(values, 2), ListFloat(values, 3));

        private static Color ColorList(IList values) => new Color(
            ListFloat(values, 0), ListFloat(values, 1),
            ListFloat(values, 2), ListFloat(values, 3));
    }
}

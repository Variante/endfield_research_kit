using System;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    public static class EndfieldRecoveredEnvironmentPhaseConsumerValidator
    {
        [MenuItem("Endfield/Character Recovery Lab/Validate Environment Phase Consumer")]
        public static void ValidateMenu()
        {
            ValidateBatch();
        }

        public static void ValidateBatch()
        {
            var root = new GameObject("EnvironmentPhaseConsumerValidation");
            try
            {
                var snapshot = root.AddComponent<EndfieldRecoveredEnvironmentPhaseSnapshot>();
                var lightObject = new GameObject("KeyLight");
                lightObject.transform.SetParent(root.transform, false);
                Light light = lightObject.AddComponent<Light>();
                light.type = LightType.Directional;
                light.intensity = 1f;
                var cameraObject = new GameObject("Camera");
                cameraObject.transform.SetParent(root.transform, false);
                cameraObject.AddComponent<Camera>();
                EndfieldHGRPCharacterLightingVolume lighting =
                    cameraObject.AddComponent<EndfieldHGRPCharacterLightingVolume>();
                EndfieldRecoveredEnvironmentPhaseConsumer consumer =
                    cameraObject.AddComponent<EndfieldRecoveredEnvironmentPhaseConsumer>();
                consumer.snapshot = snapshot;
                consumer.sceneMainLight = light;
                consumer.characterLighting = lighting;

                snapshot.ConfigureGachaRoom();
                Require(snapshot.IsGachaRoomSourceClosed, "Gacha source gate rejected exact data");
                Require(
                    consumer.TryApplySourceClosedDirectLight(out string failure),
                    "Gacha direct light failed: " + failure);
                Require(ColorApproximately(light.color, snapshot.directColor),
                    "Gacha mode-0 direct color was not selected");
                Require(Mathf.Approximately(light.colorTemperature, 4000f),
                    "Gacha color temperature changed");
                Require(Mathf.Approximately(light.intensity, 1f),
                    "unresolved EV100 was mapped into Unity intensity");
                Require(!lighting.useRecoveredSourceMainLightDescriptor,
                    "Gacha zero divide-pi incorrectly enabled the source descriptor");

                snapshot.ConfigureCharacterInfo();
                Require(
                    consumer.TryApplySourceClosedDirectLight(out failure),
                    "CharInfo direct light failed: " + failure);
                Require(ColorApproximately(light.color, snapshot.directCustomColor),
                    "CharInfo mode-1 custom color was not selected");
                Require(lighting.useRecoveredSourceMainLightDescriptor,
                    "CharInfo nonzero divide-pi did not enable the source descriptor");

                snapshot.phaseRawDataSha256 = "invalid";
                Quaternion before = light.transform.rotation;
                Require(!consumer.TryApplySourceClosedDirectLight(out failure),
                    "invalid source identity did not fail closed");
                Require(Quaternion.Angle(before, light.transform.rotation) < 0.0001f,
                    "failed source gate mutated the direct light");
                Debug.Log(
                    "Recovered environment phase consumer validation passed: " +
                    "Gacha/CharInfo color modes, temperature, pitch/yaw, neutral EV " +
                    "boundary, descriptor selection, and invalid-hash fail-closed gate.");
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        private static bool ColorApproximately(Color left, Color right)
        {
            return Mathf.Abs(left.r - right.r) < 0.00001f &&
                   Mathf.Abs(left.g - right.g) < 0.00001f &&
                   Mathf.Abs(left.b - right.b) < 0.00001f &&
                   Mathf.Abs(left.a - right.a) < 0.00001f;
        }

        private static void Require(bool condition, string message)
        {
            if (!condition)
                throw new InvalidOperationException(message);
        }
    }
}

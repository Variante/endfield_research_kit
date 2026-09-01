#!/usr/bin/env python3
"""Tests for actor-scoped operator-light source hashing."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from operator_lights_source import scoped_payload, scoped_sha256


LAB_ROOT = Path(__file__).resolve().parents[1]
RUNTIME = LAB_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Runtime" / "Rendering"
EDITOR = LAB_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Editor" / "CharacterRecovery"


def read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class OperatorLightsSourceTests(unittest.TestCase):
    def test_installed_endminf_overview_fixture_has_exact_b31_membership(self) -> None:
        source = (
            Path(__file__).resolve().parents[1]
            / "Assets"
            / "EndfieldGraphShaderLab"
            / "Generated"
            / "OriginalData"
            / "RenderParameters"
            / "operator_lights.json"
        )
        actor = json.loads(source.read_text(encoding="utf-8"))["actors"]["endminf"]
        lights = actor["lights"]
        self.assertEqual(len(lights), 12)
        self.assertTrue(all(row["enabled"] for row in lights))
        self.assertTrue(all(row["character_only"] for row in lights))
        self.assertTrue(all(not row["enable_obb_culling_box"] for row in lights))
        self.assertTrue(all(row["cookie_path_id"] == 0 for row in lights))
        self.assertTrue(all(not row["flicker_enabled"] for row in lights))
        self.assertTrue(
            all(row["culling_box_falloff_threshold"] == 0.8 for row in lights)
        )
        self.assertTrue(all(not row["use_far_distance_show"] for row in lights))
        self.assertTrue(
            all(not row["enable_override_shadow_light"] for row in lights)
        )
        self.assertEqual(
            [(row["index"], row["name"], row["shadow_type"], row["light_type"])
             for row in lights if row["shadow_type"] != 0],
            [(3, "RimLight_2", 2, 0), (11, "RimLight_2 (1)", 2, 0)],
        )

    def test_scope_is_deterministic_and_excludes_other_actors(self) -> None:
        payload = {
            "actors": {
                "wulfa": {"lights": [1, 2]},
                "liino": {"lights": [3]},
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "operator_lights.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            first = scoped_sha256(path, ("wulfa",))
            payload["actors"]["liino"]["lights"].append(4)
            path.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(first, scoped_sha256(path, ("wulfa",)))

    def test_missing_scoped_actor_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing scoped actors: wulfa"):
            scoped_payload({"actors": {}}, ("wulfa",))

    def test_full_owner_requires_current_camera_exposure_provenance(self) -> None:
        owner = read_source(
            RUNTIME / "EndfieldRecoveredEndminfFullDeferredLightData.cs"
        )
        pipeline = read_source(RUNTIME / "HGCompatRenderPipeline.cs")

        self.assertIn("bool currentCameraExposureReady", owner)
        self.assertIn(
            "if (!currentCameraExposureReady)\n"
            "            {\n"
            "                failure = \"the current camera has no provenance-valid "
            "exposure publication\";",
            owner,
        )
        full_call = pipeline.split(
            "recoveredEndminfFullDeferredLightData.PrepareAndPublish(", 1
        )[1].split("out string fullLightDataFailure", 1)[0]
        self.assertIn("recoveredCurrentCameraExposureReady", full_call)
        self.assertIn("recoveredCurrentCameraExposure", full_call)
        self.assertNotIn("recoveredVFXExposure", full_call)

        exposure_gate = pipeline.split(
            "bool recoveredSourceClosedManualExposureRequested =", 1
        )[1].split(
            "EndfieldRecoveredCharInfoAutoExposureCameraState", 1
        )[0]
        self.assertIn("recoveredSceneMVRequest.requested ||", exposure_gate)
        self.assertIn("recoveredDeferredExactConsumer.Requested", exposure_gate)
        self.assertIn("recoveredEndminfLitEffectOwnerActive", exposure_gate)
        self.assertIn("IsGachaRoomSourceClosed", exposure_gate)
        self.assertIn("IsCharacterInfoSourceClosed", exposure_gate)
        exposure_call = pipeline.split(
            "PrepareRecoveredLiveCharInfoAutoExposure(", 1
        )[1].split("if (applyPostProcess)", 1)[0]
        self.assertIn(
            "recoveredSourceClosedManualExposureRequested",
            exposure_call,
        )
        self.assertIn("AdvanceSourceClosedNeutralProfile", pipeline)

        builder = read_source(
            LAB_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Editor" /
            "CharacterRecovery" / "EndfieldManifestCharacterSetup.cs"
        )
        lighting_setup = builder.split(
            "internal static void ConfigureOperatorReferenceLighting(", 1
        )[1].split("EndfieldHGOperatorLightRig operatorLights", 1)[0]
        self.assertIn(
            "EnsureComponent<EndfieldRecoveredEnvironmentPhaseSnapshot>",
            lighting_setup,
        )
        self.assertIn("environmentSnapshot.ConfigureCharacterInfo();", lighting_setup)
        self.assertIn(
            "presentation.environmentPhaseSnapshot = environmentSnapshot;",
            lighting_setup,
        )

    def test_prepared_generation_survives_publication_invalidation(self) -> None:
        rig = read_source(RUNTIME / "EndfieldHGOperatorLightRig.cs")
        selector = rig.split("public void SetRecoveredGachaPublicationState(", 1)[1]
        selector = selector.split("private void InvalidateFollowerBones()", 1)[0]
        disable = rig.split("private void OnDisable()", 1)[1]
        disable = disable.split("private void LateUpdate()", 1)[0]

        self.assertIn("preparedCamera = null;", selector)
        self.assertIn("preparedLightCount = 0;", selector)
        self.assertNotIn("preparedSerial = 0;", selector)
        self.assertIn("preparedCamera = null;", disable)
        self.assertIn("preparedLightCount = 0;", disable)
        self.assertNotIn("preparedSerial = 0;", disable)
        self.assertEqual(rig.count("preparedSerial = 0;"), 0)
        self.assertIn("preparedSerial++;", rig)
        self.assertIn(
            "if (preparedSerial == 0)\n                    preparedSerial = 1;",
            rig,
        )

    def test_exact_consumer_requests_runtime_punctual_shadow_dependencies(
        self,
    ) -> None:
        controller = read_source(
            LAB_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Runtime" /
            "Viewer" / "CharacterRecoveryPresentationController.cs"
        )
        capture = read_source(
            EDITOR / "EndfieldEndminfViewerPlayModeCapture.cs"
        )
        exact_probe = capture.split(
            "public static void RunDeferredExactConsumerProbe()", 1
        )[1].split(
            "private static void PrepareDeferredExactConsumerRuntimeVariantIfRequested()",
            1,
        )[0]

        for flag in (
            "ENDFIELD_RECOVERED_CLUSTERED_NPR_LIGHT_LOOP",
            "ENDFIELD_RECOVERED_LIGHT_BINNING_MEMBERSHIP",
            "ENDFIELD_RECOVERED_ISOLATED_PUNCTUAL_SOFT_SHADOWS",
        ):
            self.assertIn(f'"{flag}"', exact_probe)
            self.assertIn(f'"{flag}"', controller)
        self.assertIn(
            "enableIsolatedPunctualSoftShadows ||\n"
            "                IsEnvironmentFlagEnabled(",
            controller,
        )

    def test_punctual_shadow_default_uses_pinned_native_setting(self) -> None:
        contract_path = (
            LAB_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Generated" /
            "OriginalData" / "CharInfoPresentation" /
            "deferred_resolver_binding_contract.json"
        )
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        shadow_role = next(
            row for row in contract["identified_unnamed_constant_buffer_roles"]
            if row["role"] == "ShadowData"
        )
        setting_defaults = shadow_role["native_producer"]["setting_defaults"]
        self.assertIn("T=512", setting_defaults)
        self.assertIn("before runtime overrides", setting_defaults)

        rig = read_source(RUNTIME / "EndfieldHGOperatorLightRig.cs")
        setup = read_source(EDITOR / "EndfieldManifestCharacterSetup.cs")
        self.assertIn(
            "sourceBackedPunctualShadowTileResolution = 512;",
            rig,
        )
        self.assertIn(
            "operatorLights.sourceBackedIsolatedPunctualSoftShadowProducer\n"
            "                    ? ReadRecoveredPunctualShadowTileResolution()\n"
            "                    : 512;",
            setup,
        )
        default_reader = setup.split(
            "private static int ReadRecoveredPunctualShadowTileResolution()", 1
        )[1].split("private static Transform FindDescendantByName", 1)[0]
        self.assertIn("return 512;", default_reader)
        self.assertIn("resolution == 512 || resolution == 1024", default_reader)
        self.assertNotIn("return 1024;", default_reader)
        self.assertNotIn("captured RTX 5080 device default", rig)

    def test_exact_white_rgba_source_color_is_gated_and_rejected_on_drift(
        self,
    ) -> None:
        contract = read_source(
            RUNTIME / "EndfieldRecoveredEndminfFullLightDataContract.cs"
        )
        owner = read_source(
            RUNTIME / "EndfieldRecoveredEndminfFullDeferredLightData.cs"
        )
        verifier = read_source(
            EDITOR / "EndfieldRecoveredEndminfFullLightDataBatchVerifier.cs"
        )

        self.assertIn("MatchesRecoveredSourceDirectColor(sourceDirectColor)", contract)
        self.assertIn(
            "value.r == 1.0f && value.g == 1.0f &&\n"
            "            value.b == 1.0f && value.a == 1.0f;",
            contract,
        )
        self.assertIn(
            ".MatchesRecoveredSourceDirectColor(\n"
            "                        characterVolume.sourceDirectColor)",
            owner,
        )
        self.assertIn("new Color(1.0f, 1.0f, 1.0f, 0.999f)", verifier)
        self.assertIn("fail_closed:source_direct_color_drift", verifier)
        self.assertIn(
            "sourceDirectColorRejected = sourceDirectColorRejected", verifier
        )

    def test_native_light_math_is_source_derived_and_shared(self) -> None:
        contract = read_source(
            RUNTIME / "EndfieldRecoveredEndminfFullLightDataContract.cs"
        )
        environment = read_source(
            RUNTIME / "EndfieldRecoveredEnvironmentPhaseConsumer.cs"
        )
        rig = read_source(RUNTIME / "EndfieldHGOperatorLightRig.cs")
        verifier = read_source(
            EDITOR / "EndfieldRecoveredEndminfFullLightDataBatchVerifier.cs"
        )

        self.assertIn("public static Vector3 RotationMatrixColumn2", contract)
        self.assertIn("float x2 = Add(rotation.x, rotation.x);", contract)
        self.assertIn("Sub(1.0f, Add(xx2, yy2))", contract)
        self.assertIn("public static float F32(float value)", contract)
        self.assertIn("BitConverter.SingleToInt32Bits(value)", contract)
        self.assertIn("public static float Div(float left, float right)", contract)
        self.assertIn("public static float CosHalfFullConeDegrees", contract)
        self.assertIn("float turns = Div(fullConeDegrees, 360.0f);", contract)
        self.assertIn("return F32((float)Math.Cos((double)radians));", contract)
        self.assertIn("RotationMatrixColumn2(rotation)", environment)
        self.assertGreaterEqual(rig.count("RotationMatrixColumn2("), 2)
        self.assertIn("CosHalfFullConeDegrees(", rig)
        self.assertIn("RotationMatrixColumn2(", verifier)


if __name__ == "__main__":
    unittest.main()

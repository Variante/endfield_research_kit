import json
from pathlib import Path
import unittest


LAB_ROOT = Path(__file__).parents[1]
CAPTURE = (
    LAB_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Editor" /
    "CharacterRecovery" / "EndfieldEndminfViewerPlayModeCapture.cs"
)
ASSETS = LAB_ROOT / "Assets" / "EndfieldGraphShaderLab"
GYROSCOPE_RUNTIME = (
    ASSETS / "Runtime" / "Rendering" /
    "EndfieldRecoveredCharInfoGyroscopeCameraState.cs"
)
SETUP = ASSETS / "Editor" / "CharacterRecovery" / "EndfieldManifestCharacterSetup.cs"
CONTROLLER = ASSETS / "Runtime" / "Viewer" / "CharacterRecoveryPresentationController.cs"
GYROSCOPE_MANIFEST = (
    ASSETS / "Generated" / "OriginalData" / "CharInfoGyroscope" /
    "source_manifest.json"
)


class EndminfPlayModeCaptureTimingContractTests(unittest.TestCase):
    def test_report_separates_target_threshold_and_actual_clocks(self) -> None:
        source = CAPTURE.read_text(encoding="utf-8")
        self.assertIn("endminf-viewer-playmode-sequence.v23", source)
        for field in (
            "public float targetSeconds;",
            "public float requestedSeconds;",
            "public float actualSeconds;",
            "public float phaseErrorSeconds;",
        ):
            self.assertIn(field, source)
        self.assertIn("targetSeconds = target", source)
        self.assertIn("requestedSeconds = requested", source)
        self.assertIn("phaseErrorSeconds = elapsed - target", source)

    def test_explicit_targeted_times_are_not_shifted(self) -> None:
        source = CAPTURE.read_text(encoding="utf-8")
        target_assignment = source.index("targetTimes = targetedTimes")
        threshold_assignment = source.index("requestedTimes = capturePrePostHdr")
        tick = source.index("private static void Tick()")
        self.assertLess(target_assignment, threshold_assignment)
        self.assertLess(threshold_assignment, tick)
        self.assertIn("? targetTimes.Select(value =>", source[threshold_assignment:tick])
        self.assertIn(": targetTimes.ToArray();", source[threshold_assignment:tick])

    def test_ordinary_sequences_retain_two_tick_internal_lead(self) -> None:
        source = CAPTURE.read_text(encoding="utf-8")
        self.assertIn("value - PlayModeClipLeadSeconds", source)
        self.assertIn("float requested = requestedTimes[next];", source)
        self.assertIn("float target = targetTimes[next];", source)
        self.assertIn("if (elapsed + 0.0001f < requested) return;", source)

    def test_batch_gyroscope_is_deterministic_without_reference_track(self) -> None:
        source = CAPTURE.read_text(encoding="utf-8")
        self.assertIn('"serialized-entry"', source)
        self.assertIn("ConfigureDeterministicGyroscopeCapture();", source)
        self.assertIn("RecoveryMode.LiveInput", source)
        self.assertIn(
            "Canonical/batch Endminf capture rejects live-input",
            source,
        )
        self.assertIn(
            '"presentation-profile.gyroscopeEntryOffsets"',
            source,
        )
        self.assertIn('"explicit-normalized-input-selector"', source)
        for field in (
            "public string gyroscopeInputProvider;",
            "public string gyroscopeInputX;",
            "public string gyroscopeInputY;",
            "public string gyroscopeEntryOffsetX;",
            "public string gyroscopeEntryOffsetY;",
        ):
            self.assertIn(field, source)
        self.assertIn(
            'EndfieldPlayableCharInfoProfileBuilder.LoadProfile("Endminf")',
            source,
        )
        self.assertIn("Unsupported batch gyroscope mode", source)
        runtime = GYROSCOPE_RUNTIME.read_text(encoding="utf-8")
        self.assertIn("RecoveryMode.Invalid", runtime)
        self.assertIn("return RecoveryMode.Invalid;", runtime)
        self.assertIn('return "invalid";', runtime)
        self.assertNotIn(
            "return RecoveryMode.Off;\n        }\n\n        private static bool TryReadFloatSelector",
            runtime,
        )
        self.assertNotIn("RecordingGyroscopeInput", source)
        self.assertNotIn("CleanReferenceGyroscopeTrack", source)
        self.assertNotIn("ReplayCleanReferenceGyroscopeTrack", source)

    def test_gyroscope_has_one_evaluated_target_gate(self) -> None:
        source = GYROSCOPE_RUNTIME.read_text(encoding="utf-8")
        self.assertEqual(source.count("1e-10f"), 1)
        self.assertIn("previousRawTarget = Vector2.zero", source)
        self.assertIn(
            ".ShouldRetargetRawTarget(previousRawTarget, rawTarget)",
            source,
        )
        self.assertIn("tween.RetargetRawTarget(rawTarget)", source)
        self.assertNotIn("SourceInputChangeThresholdSquared", source)
        retarget = source[source.index("public void RetargetRawTarget"):]
        self.assertNotIn("sqrMagnitude", retarget)

    def test_gyroscope_retarget_uses_source_timing(self) -> None:
        source = GYROSCOPE_RUNTIME.read_text(encoding="utf-8")
        self.assertIn("entryOffsets = EvaluateCurrentOffsets();", source)
        self.assertIn("elapsed + Time.deltaTime", source)
        self.assertNotIn("Time.unscaledDeltaTime", source)
        self.assertIn(
            "1.0f - (1.0f - linear) * (1.0f - linear)",
            source,
        )
        self.assertIn("sourcePhase=PreLate", source)
        self.assertIn("adapterCallback=LateUpdate", source)
        self.assertIn("equivalenceClaim=false", source)

    def test_gyroscope_entry_offsets_are_profile_owned(self) -> None:
        setup = SETUP.read_text(encoding="utf-8")
        controller = CONTROLLER.read_text(encoding="utf-8")
        runtime = GYROSCOPE_RUNTIME.read_text(encoding="utf-8")
        self.assertIn("presentationProfile.gyroscopeEntryOffsets", setup)
        self.assertIn("profile.gyroscopeEntryOffsets", controller)
        self.assertNotIn("new Vector2(0.24835543f, -0.1448596f)", runtime)

    def test_manifest_pins_retail_input_provider_boundary(self) -> None:
        manifest = json.loads(GYROSCOPE_MANIFEST.read_text(encoding="utf-8"))
        driver = manifest["input_driver"]
        self.assertEqual(
            manifest["schema"],
            "endfield.charinfo.gyroscope-camera-state.original-data.v2",
        )
        self.assertEqual(driver["tick_option"]["tick"], "PreLate")
        self.assertEqual(driver["tick_option"]["return_value"], 8)
        self.assertEqual(
            driver["mouse_provider"]["source_type"],
            "Beyond.Input.InputManager",
        )
        self.assertEqual(
            driver["mouse_provider"]["source_method"],
            "get_mousePosition",
        )
        self.assertEqual(driver["raw_target_change_gate"]["gate_count"], 1)


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import unittest


LAB_ROOT = Path(__file__).parents[1]
CAPTURE = (
    LAB_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Editor" /
    "CharacterRecovery" / "EndfieldEndminfViewerPlayModeCapture.cs"
)


class EndminfPlayModeCaptureTimingContractTests(unittest.TestCase):
    def test_report_separates_target_threshold_and_actual_clocks(self) -> None:
        source = CAPTURE.read_text(encoding="utf-8")
        self.assertIn("endminf-viewer-playmode-sequence.v16", source)
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

    def test_clean_gyroscope_track_offset_is_bounded_and_reported(self) -> None:
        source = CAPTURE.read_text(encoding="utf-8")
        self.assertIn(
            "ENDFIELD_ENDMINF_CAPTURE_GYROSCOPE_TRACK_OFFSET_FRAMES",
            source,
        )
        self.assertIn("frames < -2 || frames > 2", source)
        self.assertIn(
            "cleanReferenceGyroscopeTrackOffsetFrames / SimulationFps",
            source,
        )
        self.assertGreaterEqual(
            source.count("cleanReferenceGyroscopeTrackOffsetFrames"),
            5,
        )


if __name__ == "__main__":
    unittest.main()

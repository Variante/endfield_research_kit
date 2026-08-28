import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / (
    "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/"
    "EndfieldEndminfViewerPlayModeCapture.cs"
)
RUNTIME_ROOT = ROOT / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"


class EndminfPeakExactCaptureTelemetryContractTests(unittest.TestCase):
    def test_report_schema_and_rows_publish_each_exact_packet_state(self) -> None:
        source = CAPTURE.read_text(encoding="utf-8")
        self.assertIn("endminf-viewer-playmode-sequence.v7", source)
        for material in ("M18", "M21", "M28"):
            for state in ("Requested", "Active", "Submitted", "Validated", "Failure"):
                field = f"endminf{material}Exact{state}"
                self.assertGreaterEqual(source.count(field), 2, field)

    def test_runtimes_reset_and_publish_per_frame_submission_state(self) -> None:
        for material in ("M18", "M21", "M28"):
            path = RUNTIME_ROOT / (
                f"EndfieldRecoveredEndminf{material}PeakExactRuntime.cs"
            )
            source = path.read_text(encoding="utf-8")
            prepare = source.index("PrepareBeforeCulling")
            render = source.index("Render(", prepare)
            self.assertIn("submittedThisFrame = false", source[prepare:render])
            self.assertIn("validatedThisFrame = false", source[prepare:render])
            self.assertIn("submittedThisFrame = true", source[render:])
            self.assertIn("validatedThisFrame = true", source[render:])


if __name__ == "__main__":
    unittest.main()

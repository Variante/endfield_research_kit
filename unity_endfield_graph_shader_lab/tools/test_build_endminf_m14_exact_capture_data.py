import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("build_endminf_m14_exact_capture_data.py")
SPEC = importlib.util.spec_from_file_location(
    "build_endminf_m14_exact_capture_data", MODULE_PATH)
target = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = target
assert SPEC.loader is not None
SPEC.loader.exec_module(target)


class BuildEndminfM14ExactCaptureDataTests(unittest.TestCase):
    def test_canonical_capture_builds_stable_payload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "capture.generated.cs"
            cpp_output = Path(directory) / "capture.generated.h"
            text = target.build(target.FRAME, target.REPORT, output, cpp_output)
            self.assertEqual(text, output.read_text(encoding="utf-8"))
            self.assertIn("internal const int QuadCount = 285;", text)
            self.assertIn("internal const int VertexCount = 1140;", text)
            self.assertIn("internal const int IndexCount = 1710;", text)
            self.assertIn("CreateVertexConstantBufferValues", text)
            self.assertIn("CreatePixelConstantBufferValues", text)
            self.assertIn(target.EXPECTED_FRAME.__str__(), text)
            cpp_text = cpp_output.read_text(encoding="utf-8")
            self.assertIn("g_EndfieldM14VertexCount = 1140", cpp_text)
            self.assertIn("g_EndfieldM14VSDeclaredFloat4Counts", cpp_text)

    def test_selected_draw_closes_stage_specific_ranges(self) -> None:
        metadata = target.load_json(target.FRAME / "metadata.json")
        constants = target.collect_constants(target.select_draw(metadata))
        self.assertEqual(
            [row["captured_count"] for row in constants[0]],
            list(target.CAPTURED_COUNTS[0]),
        )
        self.assertEqual(
            [row["captured_count"] for row in constants[4]],
            list(target.CAPTURED_COUNTS[4]),
        )


if __name__ == "__main__":
    unittest.main()

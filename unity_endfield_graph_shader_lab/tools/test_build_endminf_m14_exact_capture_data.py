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
            text = target.build(target.CAPTURE, target.REPORT, output, cpp_output)
            self.assertEqual(text, output.read_text(encoding="utf-8"))
            self.assertIn("internal const int PacketCount = 7;", text)
            self.assertIn("1405, 1413, 1421, 1429, 1437, 1445, 1453", text)
            self.assertIn("4.50f, 4.75f, 5.00f", text)
            cpp_text = cpp_output.read_text(encoding="utf-8")
            self.assertIn("g_EndfieldM14PacketCount", cpp_text)
            self.assertIn("1968u", cpp_text)
            self.assertIn("2880u", cpp_text)
            self.assertIn("g_EndfieldM14VSDeclaredFloat4Counts", cpp_text)

    def test_selected_draw_closes_stage_specific_ranges(self) -> None:
        report = target.load_json(target.REPORT)
        packets = target.collect_packets(target.CAPTURE, report)
        constants = packets[0]["constants"]
        for stage in (0, 4):
            self.assertTrue(all(
                row["captured_count"] >= target.MINIMUM_COUNTS[stage][slot]
                for slot, row in enumerate(constants[stage])
            ))
            self.assertTrue(all(
                row["captured_count"] <= target.DECLARED_COUNTS[stage][slot]
                for slot, row in enumerate(constants[stage])
            ))


if __name__ == "__main__":
    unittest.main()

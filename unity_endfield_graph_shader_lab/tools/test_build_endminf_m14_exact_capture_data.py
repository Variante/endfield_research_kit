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
            self.assertIn("internal const int PacketCount = 15;", text)
            self.assertIn("2978, 1405, 2987, 2995, 1413", text)
            self.assertIn("4.433333f, 4.500000f, 4.583333f", text)
            self.assertIn("5.516666f", text)
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

    def test_late_capture_interleaves_with_coarse_packets(self) -> None:
        early = target.collect_packets(
            target.CAPTURE, target.load_json(target.REPORT))
        late = target.collect_late_packets(
            target.LATE_CAPTURE, target.load_json(target.LATE_REPORT))
        packets = target.merge_packets(early, late)
        self.assertEqual(len(packets), 15)
        six = [row for row in packets if abs(row["phase"] - 6.0) < 0.000001]
        self.assertEqual(len(six), 1)
        self.assertEqual(six[0]["frame"], 1453)
        self.assertEqual(packets[0]["frame"], 2978)
        duplicate = [row for row in packets if abs(row["phase"] - 5.25) < 0.000001]
        self.assertEqual([row["frame"] for row in duplicate], [3027])


if __name__ == "__main__":
    unittest.main()

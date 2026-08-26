import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("build_endminf_m27_exact_capture_data.py")
SPEC = importlib.util.spec_from_file_location("build_endminf_m27_exact_capture_data", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class EndminfM27ExactCaptureDataTests(unittest.TestCase):
    def test_current_capture_generates_current_runtime_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "capture.generated.cs"
            generated = MODULE.build(MODULE.CAPTURE, output)
        self.assertEqual(generated, MODULE.OUTPUT.read_text(encoding="utf-8"))
        self.assertIn("new Vector4[DeclaredFloat4Counts[slot]]", generated)
        self.assertIn("SourceFrame = 2529", generated)
        self.assertIn("ExpandedVertexCount = 435", generated)
        self.assertIn("ExpandedIndexCount = 1080", generated)
        self.assertIn("ExactVertexEnvelopeClosed =\n            true", generated)

    def test_uses_largest_closed_shared_stage_ranges(self):
        capture = MODULE.load_capture(MODULE.CAPTURE)
        rows = MODULE.collect_payloads(MODULE.select_draw(capture))
        self.assertEqual(
            [(row["slot"], row["declared_float4s"], row["captured_float4s"]) for row in rows],
            [(0, 82, 82), (1, 106, 106), (2, 4091, 104), (3, 31, 31), (4, 1, 1)],
        )

    def test_recovers_unique_expanded_geometry_from_shared_ring_buffer(self):
        capture = MODULE.load_capture(MODULE.CAPTURE)
        geometry = MODULE.collect_geometry(MODULE.CAPTURE, capture)
        self.assertEqual(geometry["resource_kind"], 4)
        self.assertEqual(geometry["vertex_offset"], 934068)
        self.assertEqual(geometry["vertex_stride"], 60)
        self.assertEqual(geometry["vertex_count"], 435)
        self.assertEqual(geometry["index_offset"], 1115468)
        self.assertEqual(geometry["index_count"], 1080)


if __name__ == "__main__":
    unittest.main()

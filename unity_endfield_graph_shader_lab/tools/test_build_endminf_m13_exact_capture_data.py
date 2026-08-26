import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("build_endminf_m13_exact_capture_data.py")
SPEC = importlib.util.spec_from_file_location(
    "build_endminf_m13_exact_capture_data", MODULE_PATH)
target = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = target
assert SPEC.loader is not None
SPEC.loader.exec_module(target)


class BuildEndminfM13ExactCaptureDataTests(unittest.TestCase):
    def test_incomplete_capture_is_rejected_before_packet_publication(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "capture.generated.cs"
            cpp_output = Path(directory) / "capture.generated.h"
            with self.assertRaisesRegex(
                    ValueError, "stage 0 b4 backing allocation was not selected"):
                target.build(target.FRAME, output, cpp_output)
            self.assertFalse(output.exists())
            self.assertFalse(cpp_output.exists())

    def test_full_selected_buffer_closes_shared_truncated_previews(self) -> None:
        metadata = target.load_json(target.FRAME / "metadata.json")
        resources = (target.FRAME / "resources.bin").read_bytes()
        draw = target.select_draw(metadata)
        draw["constantBuffers"] = [row for row in draw["constantBuffers"]
                                   if row["bufferId"] == 117766608864]
        old_counts = target.DECLARED_COUNTS
        try:
            target.DECLARED_COUNTS = {0: (2, 82, 20, 4094),
                                      4: (28, 105, 4085)}
            constants = target.collect_constants(draw, metadata, resources)
        finally:
            target.DECLARED_COUNTS = old_counts
        self.assertEqual(len(constants[0][3]["payload"]), 4094 * 16)
        self.assertEqual(len(constants[4][2]["payload"]), 4085 * 16)


if __name__ == "__main__":
    unittest.main()

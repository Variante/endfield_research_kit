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
    def test_canonical_capture_builds_complete_packet(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "capture.generated.cs"
            cpp_output = Path(directory) / "capture.generated.h"
            text = target.build(target.FRAME, output, cpp_output)
            self.assertIn("SourceFrame = 5404", text)
            self.assertIn("RingByteOffset = 1045520", text)
            cpp = cpp_output.read_text(encoding="utf-8")
            self.assertIn("{2, 82, 20, 4094, 4}", cpp)
            self.assertIn("{28, 105, 4085, 50}", cpp)
            self.assertIn("g_EndfieldM13Texture4", cpp)

    def test_full_selected_buffer_closes_shared_truncated_previews(self) -> None:
        metadata = target.load_json(target.FRAME / "metadata.json")
        resources = (target.FRAME / "resources.bin").read_bytes()
        constants = target.collect_constants(
            target.select_draw(metadata), metadata, resources)
        self.assertEqual(len(constants[0][3]["payload"]), 4094 * 16)
        self.assertEqual(len(constants[4][2]["payload"]), 4085 * 16)
        self.assertEqual(len(constants[4][3]["payload"]), 50 * 16)


if __name__ == "__main__":
    unittest.main()

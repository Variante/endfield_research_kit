from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
SPEC = importlib.util.spec_from_file_location(
    "build_endminf_m31_peak_capture_data",
    HERE / "build_endminf_m31_peak_capture_data.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class BuildEndminfM31PeakCaptureDataTests(unittest.TestCase):
    def test_builds_exact_two_draw_frame_1818_payload(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            cs_path = Path(folder) / "payload.cs"
            cpp_path = Path(folder) / "payload.h"
            MODULE.build(MODULE.CAPTURE, cs_path, cpp_path)
            cs = cs_path.read_text(encoding="utf-8")
            cpp = cpp_path.read_text(encoding="utf-8")
            self.assertIn("SourceFrame = 1818", cs)
            self.assertIn("DrawCount = 2", cs)
            self.assertIn("PhaseSeconds = 4.350000f", cs)
            self.assertIn("DepthContractReady = true", cs)
            self.assertIn("g_EndfieldM31PeakPacketCount", cpp)
            self.assertIn("g_EndfieldM31PeakTextureT1", cpp)

    def test_owner_constant_drift_is_rejected(self) -> None:
        metadata_path = MODULE.CAPTURE / "graphics/frames/1818/metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        draw = next(row for row in metadata["drawRecords"]
                    if MODULE.is_m31(row))
        changed = copy.deepcopy(draw)
        b3 = next(row for row in changed["constantBuffers"]
                  if row["stage"] == 4 and row["slot"] == 3)
        payload = bytearray.fromhex(b3["dataHex"])
        payload[16:20] = b"\x00\x00\x00\x00"
        b3["dataHex"] = payload.hex()
        self.assertFalse(MODULE.is_m31(changed))

    def test_capture_session_is_pinned(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "source session drifted"):
                MODULE.collect(Path(folder))


if __name__ == "__main__":
    unittest.main()

import importlib.util
import struct
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("decode_endminf_skinning_capture.py")
SPEC = importlib.util.spec_from_file_location("decode_endminf_skinning_capture", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class DecodeEndminfSkinningCaptureTests(unittest.TestCase):
    def make_capture(self, root: Path, draw: int, changed_matrix: int | None = None) -> Path:
        capture = root / f"capture-{draw}"
        capture.mkdir()
        stem = (
            f"{draw:06d}-vs-t0={MODULE.EXPECTED_RESOURCE_HASH}-"
            "vs=1479b2b594b9c91a-ps=e9ccfc0d0d3c7746"
        )
        descriptor = capture / f"{stem}.dsc"
        descriptor.write_text(
            "type=Buffer byte_width=8413184 usage=\"DEFAULT\" "
            "bind_flags=\"shader_resource unordered_access\" cpu_access_flags=0 "
            "misc_flags=\"buffer_structured\" stride=16\n",
            encoding="utf-8",
        )
        rows = MODULE.EXPECTED_BYTE_WIDTH // MODULE.EXPECTED_STRIDE
        with (capture / f"{stem}.buf").open("wb") as stream:
            for row in range(rows):
                value = float(row)
                if changed_matrix is not None and row == 6 + changed_matrix * 3:
                    value += 0.25
                stream.write(struct.pack("<4f", value, value + 1, value + 2, value + 3))
        return capture

    def add_range_logged_b2(
        self, capture: Path, draw: int, first_constant: int, current: int, previous: int
    ) -> None:
        stem = (
            f"{draw:06d}-vs-cb2={MODULE.EXPECTED_CONSTANT_BUFFER_HASH}-"
            "vs=1479b2b594b9c91a-ps=e9ccfc0d0d3c7746"
        )
        (capture / f"{stem}.dsc").write_text(
            "type=Buffer byte_width=4194304 usage=\"DYNAMIC\" "
            "bind_flags=\"constant_buffer\" cpu_access_flags=\"write\" "
            "misc_flags=0 stride=0\n",
            encoding="utf-8",
        )
        data = bytearray(MODULE.EXPECTED_CONSTANT_BUFFER_BYTE_WIDTH)
        struct.pack_into("<4I", data, (first_constant + 5) * 16, current, previous, 7, 9)
        (capture / f"{stem}.buf").write_bytes(data)
        (capture / "log.txt").write_text(
            f"{draw:06d} VSSetConstantBuffers1(StartSlot:2, NumBuffers:1, "
            "ppConstantBuffers:0x1, pFirstConstant:0x2, pNumConstants:0x3)\n"
            f"       2: first_constant={first_constant} num_constants=4096\n"
            "       2: resource=0x4 hash=a517561d\n",
            encoding="utf-8",
        )

    def test_decodes_three_row_matrices_from_effective_base(self):
        with tempfile.TemporaryDirectory() as temporary:
            capture = self.make_capture(Path(temporary), 77)
            result = MODULE.decode_capture(capture, 77, 6, 2, previous_base_row=12)
        self.assertEqual(result["matrix_count"], 2)
        self.assertEqual(result["matrices_3x4"][0][0], [6.0, 7.0, 8.0, 9.0])
        self.assertEqual(result["matrices_3x4"][1][2], [11.0, 12.0, 13.0, 14.0])
        self.assertEqual(
            result["previous_matrices_3x4"][0][0], [12.0, 13.0, 14.0, 15.0]
        )

    def test_reports_contiguous_changed_matrix_ranges(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            left_capture = self.make_capture(root, 77)
            right_capture = self.make_capture(root, 78, changed_matrix=1)
            left = MODULE.decode_capture(left_capture, 77, 6, 3)
            right = MODULE.decode_capture(right_capture, 78, 6, 3)
            ranges, maximum = MODULE.changed_matrix_ranges(
                left["matrices_3x4"], right["matrices_3x4"], 1e-6
            )
        self.assertEqual(ranges, [{"start_matrix": 1, "end_matrix_exclusive": 2}])
        self.assertAlmostEqual(maximum, 0.25)

    def test_derives_current_and_previous_bases_from_range_logged_b2(self):
        with tempfile.TemporaryDirectory() as temporary:
            capture = self.make_capture(Path(temporary), 77)
            self.add_range_logged_b2(capture, 77, first_constant=128, current=12, previous=42)
            result = MODULE.decode_capture(capture, 77, None, 1)
        self.assertEqual(result["effective_base_row"], 15)
        self.assertEqual(result["previous_effective_base_row"], 45)
        self.assertEqual(result["derived_binding"]["instance_metadata_absolute_row"], 133)
        self.assertEqual(result["derived_binding"]["reserved_z"], 7)

    def test_fails_closed_when_binary_payload_is_missing(self):
        with tempfile.TemporaryDirectory() as temporary:
            capture = Path(temporary)
            (capture / (
                "000077-vs-t0=554904b3-vs=1479b2b594b9c91a-"
                "ps=e9ccfc0d0d3c7746.dsc"
            )).write_text(
                "type=Buffer byte_width=8413184 stride=16\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(MODULE.CaptureError, "binary payload is missing"):
                MODULE.select_resource(capture, 77)

    def test_fails_closed_on_descriptor_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            capture = self.make_capture(Path(temporary), 77)
            descriptor = next(capture.glob("*.dsc"))
            descriptor.write_text(
                "type=Buffer byte_width=8413184 stride=12\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(MODULE.CaptureError, "unexpected stride"):
                MODULE.decode_capture(capture, 77, 6, 1)


if __name__ == "__main__":
    unittest.main()

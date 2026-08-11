import json
import struct
import unittest

from . import decode_light_cull_capture as decoder


def _fixture(*, count: int = 1, pointer: int = 0x12345000) -> dict:
    rows = bytearray(count * decoder.ROW_STRIDE_BYTES)
    for index in range(count):
        offset = index * decoder.ROW_STRIDE_BYTES
        struct.pack_into("<I", rows, offset + 0x00, index % 3)
        struct.pack_into(
            "<4f", rows, offset + 0x04, 0.1 + index, 0.2, 0.3, 1.0
        )
        struct.pack_into(
            "<16f",
            rows,
            offset + 0x24,
            *[float(value + index) for value in range(16)],
        )
        struct.pack_into("<f", rows, offset + 0x64, 0.5 + index)
        struct.pack_into("<f", rows, offset + 0x68, 10.0 + index)
        struct.pack_into("<f", rows, offset + 0x6C, 35.0 + index)
        struct.pack_into("<i", rows, offset + 0x70, -index)
        struct.pack_into("<3f", rows, offset + 0x74, 1.0 + index, 2.0, 3.0)
        struct.pack_into("<I", rows, offset + 0x80, 0xA0 + index)
        struct.pack_into("<I", rows, offset + 0x84, 0)
        struct.pack_into("<Q", rows, offset + 0x88, 0xABC000 + index)
    return {
        "schema": decoder.SCHEMA,
        "gameBuild": decoder.GAME_BUILD,
        "binaryPins": {
            "unityPlayerSha256": decoder.UNITY_PLAYER_SHA256,
            "gameAssemblySha256": decoder.GAME_ASSEMBLY_SHA256,
        },
        "callSite": "normal",
        "result": {
            "visibleLightsPtr": f"0x{pointer:X}",
            "visibleLightCount": count,
            "rawRowsHex": rows.hex(),
        },
    }


class DecodeLightCullCaptureTests(unittest.TestCase):
    def test_decodes_build_pinned_rows(self) -> None:
        result = decoder.decode_capture(_fixture(count=2))
        self.assertEqual(result["result"]["rawBytes"], 296)
        self.assertEqual(result["rows"][1]["lightType"], 1)
        for actual, expected in zip(
            result["rows"][1]["finalColor"], [1.1, 0.2, 0.3, 1.0]
        ):
            self.assertAlmostEqual(actual, expected, places=6)
        self.assertEqual(
            result["rows"][1]["localToWorldMatrix"][8:12],
            [9.0, 10.0, 11.0, 12.0],
        )
        self.assertEqual(result["rows"][1]["specularIntensity"], 1.5)
        self.assertEqual(result["rows"][1]["priority"], -1)
        self.assertEqual(result["rows"][1]["worldPosition"], [2.0, 2.0, 3.0])
        self.assertEqual(result["rows"][1]["rawIdentityWord0x84"], 0)

    def test_zero_result_requires_null_pointer_and_empty_rows(self) -> None:
        result = decoder.decode_capture(_fixture(count=0, pointer=0))
        self.assertEqual(result["rows"], [])
        bad = _fixture(count=0, pointer=1)
        with self.assertRaisesRegex(decoder.CaptureDecodeError, "zero count"):
            decoder.decode_capture(bad)

    def test_rejects_wrong_binary_pin(self) -> None:
        bad = _fixture()
        bad["binaryPins"]["unityPlayerSha256"] = "0" * 64
        with self.assertRaisesRegex(decoder.CaptureDecodeError, "binary pin mismatch"):
            decoder.decode_capture(bad)

    def test_rejects_truncated_rows(self) -> None:
        bad = _fixture()
        bad["result"]["rawRowsHex"] = bad["result"]["rawRowsHex"][:-2]
        with self.assertRaisesRegex(decoder.CaptureDecodeError, "expected 148 bytes"):
            decoder.decode_capture(bad)

    def test_rejects_count_above_native_cap(self) -> None:
        bad = _fixture(count=1)
        bad["result"]["visibleLightCount"] = 257
        with self.assertRaisesRegex(decoder.CaptureDecodeError, "expected 0..256"):
            decoder.decode_capture(bad)

    def test_rejects_nonzero_converter_flags_word(self) -> None:
        bad = _fixture()
        raw = bytearray.fromhex(bad["result"]["rawRowsHex"])
        struct.pack_into("<I", raw, 0x84, 1)
        bad["result"]["rawRowsHex"] = raw.hex()
        with self.assertRaisesRegex(
            decoder.CaptureDecodeError,
            "rawIdentityWord0x84: expected converter-written zero",
        ):
            decoder.decode_capture(bad)


if __name__ == "__main__":
    unittest.main()

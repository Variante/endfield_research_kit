import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("decode_endminf_default_deferred_capture.py")
SPEC = importlib.util.spec_from_file_location("decode_default_deferred", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class DecodeDefaultDeferredCaptureTests(unittest.TestCase):
    def make_frame(self, root: Path, mutate=None):
        frame = root / "graphics" / "frames" / "382"
        frame.mkdir(parents=True)
        blob = bytes((index * 17 + 3) & 0xFF for index in range(131072))
        ranges = []
        first = 0
        for slot, required in enumerate(MODULE.REQUIRED_CONSTANTS):
            ranges.append({
                "slot": slot,
                "bufferId": 1234,
                "firstConstant": first,
                "numConstants": required + 16,
                "byteWidth": len(blob),
                "rangeValid": True,
            })
            first += required
        resolver = {
            "vertexCountPerInstance": 3,
            "instanceCount": 1,
            "startVertex": 0,
            "startInstance": 0,
            "priorityDefaultDeferred": True,
            "shaders": [
                {"stage": 0, "identityHash": MODULE.EXPECTED_VS_IDENTITY},
                {"stage": 4, "identityHash": MODULE.EXPECTED_PS_IDENTITY},
            ],
            "psConstantBuffers": ranges,
        }
        metadata = {
            "schema": "endfieldCapture.graphicsFrame.v1",
            "captureIncomplete": False,
            "captureFailed": False,
            "resourcesFile": "resources.bin",
            "selectedResourceRecords": [{
                "captureKind": 2,
                "objectId": 1234,
                "byteSize": len(blob),
                "blobOffset": 0,
                "blobBytes": len(blob),
                "failure": 0,
                "completed": True,
            }],
            "fullscreenResolvers": [resolver],
        }
        if mutate:
            mutate(metadata)
        (frame / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
        (frame / "resources.bin").write_bytes(blob)
        return frame, blob

    def test_decodes_all_default_lit_slices(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            frame, blob = self.make_frame(root)
            rows = MODULE.decode_frame(frame)
            self.assertEqual(len(rows), 1)
            decoded, slices = rows[0]
            self.assertEqual(len(slices), 10)
            self.assertEqual(decoded["uniqueBackingBuffers"], 1)
            expected = blob[: MODULE.REQUIRED_CONSTANTS[0] * 16]
            self.assertEqual(slices[0], expected)
            self.assertEqual(
                decoded["constantBuffers"][0]["sliceSha256"],
                hashlib.sha256(expected).hexdigest(),
            )

    def test_session_writes_source_shaped_binary_slices(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_frame(root)
            slices = root / "slices"
            report = MODULE.decode_session(root, slices)
            self.assertTrue(report["valid"], report["failures"])
            outputs = sorted(slices.glob("*.bin"))
            self.assertEqual(len(outputs), 10)
            self.assertEqual(outputs[0].stat().st_size, 45 * 16)

    def test_rejects_wrong_pixel_shader_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            def mutate(metadata):
                metadata["fullscreenResolvers"][0]["shaders"][1]["identityHash"] = 7

            frame, _ = self.make_frame(Path(temporary), mutate)
            with self.assertRaisesRegex(MODULE.CaptureError, "PS identity"):
                MODULE.decode_frame(frame)

    def test_rejects_missing_constant_slot(self):
        with tempfile.TemporaryDirectory() as temporary:
            def mutate(metadata):
                metadata["fullscreenResolvers"][0]["psConstantBuffers"].pop()

            frame, _ = self.make_frame(Path(temporary), mutate)
            with self.assertRaisesRegex(MODULE.CaptureError, "slots are"):
                MODULE.decode_frame(frame)

    def test_session_fails_closed_without_prioritized_resolver(self):
        with tempfile.TemporaryDirectory() as temporary:
            def mutate(metadata):
                metadata["fullscreenResolvers"][0]["priorityDefaultDeferred"] = False

            root = Path(temporary)
            self.make_frame(root, mutate)
            report = MODULE.decode_session(root)
            self.assertFalse(report["valid"])
            self.assertIn("no complete prioritized", report["failures"][-1]["failure"])


if __name__ == "__main__":
    unittest.main()

import importlib.util
import json
import struct
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("verify_endminf_m14_graphics_capture.py")
SPEC = importlib.util.spec_from_file_location("m14_capture", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class M14CaptureTests(unittest.TestCase):
    @staticmethod
    def particle_resource(quad_count: int, *, aspect_ratio: float = 2.0) -> bytes:
        data = bytearray(64)
        uv_rows = ((0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0))
        for quad in range(quad_count):
            center = float(quad)
            positions = (
                (center, 0.5, 0.0),
                (center + aspect_ratio, 0.5, 0.0),
                (center + aspect_ratio, -0.5, 0.0),
                (center, -0.5, 0.0),
            )
            for position, uv in zip(positions, uv_rows):
                data.extend(struct.pack(
                    "<6fI2f", *position, 0.0, 0.0, 1.0,
                    0xFFFFFFFF, *uv
                ))
        return bytes(data)

    def make_session(self, root: Path, *, include_target: bool = True,
                     c13_count: int = 16,
                     index_count: int | None = None) -> Path:
        (root / "graphics/frames/100").mkdir(parents=True)
        session = {
            "schema": "endfieldCapture.session.v1",
            "sessionId": "synthetic",
            "providers": 1,
            "graphicsProfile": "targeted",
            "evidenceLabel": "forced-d3d11",
            "gameBuild": MODULE.GAME_BUILD,
            "targetSha256": MODULE.TARGET_SHA256,
        }
        (root / "session.json").write_text(json.dumps(session), encoding="utf-8")
        constants = []
        for (stage, slot), (required, limit) in MODULE.REQUIRED_BINDINGS.items():
            captured = c13_count if (stage, slot) == (0, 3) else limit
            data = bytearray(captured * 16)
            for index in range(captured):
                struct.pack_into("<4f", data, index * 16,
                                 index + 0.1, index + 0.2,
                                 index + 0.3, index + 0.4)
            if (stage, slot) == (0, 3) and captured > 13:
                struct.pack_into("<4f", data, 13 * 16, 0.25, 0.5, 0.75, 0.0)
            constants.append({
                "stage": stage,
                "slot": slot,
                "bufferId": 1000 + stage * 10 + slot,
                "firstConstant": 7,
                "numConstants": required,
                "capturedConstants": captured,
                "rangeValid": True,
                "metadataValid": True,
                "truncated": required > limit,
                "dataHex": data.hex(),
            })
        draw = {
            "count": index_count or MODULE.M14_REFERENCE_INDEX_COUNT,
            "indexedInstanced": True,
            "instanceCount": 1,
            "startInstance": 0,
            "priorityShaderPair": include_target,
            "shaders": [
                {"stage": 0, "identityHash": MODULE.VS_IDENTITY,
                 "bytecodeSize": MODULE.VS_BYTECODE_SIZE},
                {"stage": 4, "identityHash": MODULE.PS_IDENTITY,
                 "bytecodeSize": MODULE.PS_BYTECODE_SIZE},
            ],
            "constantBuffers": constants,
        }
        metadata = {
            "schema": "endfieldCapture.graphicsFrame.v1",
            "runtimeMode": "d3d11-proxy",
            "evidenceLabel": "forced-d3d11",
            "graphicsProfile": "targeted",
            "frame": 100,
            "captureIncomplete": False,
            "captureFailed": False,
            "drawRecords": [draw],
        }
        (root / "graphics/frames/100/metadata.json").write_text(
            json.dumps(metadata), encoding="utf-8"
        )
        return root

    def test_decodes_complete_exact_draw(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = MODULE.decode_session(self.make_session(Path(temporary)))
        self.assertEqual(result["status"], "validated")
        self.assertEqual(result["m14FrameCount"], 1)
        draw = result["frames"][0]["m14Draws"][0]
        self.assertEqual(draw["vsPerDrawC13"], [0.25, 0.5, 0.75, 0.0])
        self.assertEqual(draw["vertexColorMultiplier"], [0.75, 0.5, 0.25, 1.0])
        self.assertEqual(len(draw["bindings"]["0:b1"]["float4"]), 82)
        self.assertEqual(len(draw["bindings"]["4:b1"]["float4"]), 105)

    def test_accepts_dynamic_peak_particle_count(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = MODULE.decode_session(self.make_session(
                Path(temporary), index_count=1_710
            ))
        draw = result["frames"][0]["m14Draws"][0]
        self.assertEqual(draw["indexCount"], 1_710)
        self.assertEqual(draw["quadCount"], 285)
        self.assertEqual(draw["referenceIndexCount"], 1_098)

    def test_decodes_captured_basev2_linear_tint_witness(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_session(Path(temporary))
            path = root / "graphics/frames/100/metadata.json"
            metadata = json.loads(path.read_text(encoding="utf-8"))
            draw = metadata["drawRecords"][0]
            draw["baseVertex"] = 3227
            row = next(row for row in draw["constantBuffers"]
                       if row["stage"] == 4 and row["slot"] == 3)
            data = bytearray.fromhex(row["dataHex"])
            struct.pack_into("<4f", data, 4 * 16,
                             0.29275623, 0.17861338, 0.04641925, 1.0)
            row["dataHex"] = data.hex()
            path.write_text(json.dumps(metadata), encoding="utf-8")
            result = MODULE.decode_session(root)
        frame = result["frames"][0]
        self.assertEqual(frame["capturedLinearTintWitnessCount"], 1)
        witness = frame["priorityPairDraws"][0]
        self.assertEqual(witness["material"], "M_fx_endminm_gfx_14")
        self.assertEqual(witness["materialMatch"],
                         "generated-authored-Color-linear-upload")

    def test_does_not_reuse_base_vertex_as_cross_frame_material_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_session(Path(temporary))
            path = root / "graphics/frames/100/metadata.json"
            metadata = json.loads(path.read_text(encoding="utf-8"))
            draw = metadata["drawRecords"][0]
            draw["baseVertex"] = 3227
            path.write_text(json.dumps(metadata), encoding="utf-8")
            result = MODULE.decode_session(root)
        witness = result["frames"][0]["priorityPairDraws"][0]
        self.assertNotIn("material", witness)
        self.assertEqual(
            witness["baseVertexWitnessStatus"],
            "ring_offset_reused_with_different_material_state")

    def test_decodes_raw_expanded_particle_geometry(self):
        with tempfile.TemporaryDirectory() as temporary:
            frame = Path(temporary)
            payload = self.particle_resource(6)
            (frame / "resources.bin").write_bytes(payload)
            metadata = {"selectedResourceRecords": [{
                "captureKind": 4,
                "completed": True,
                "failure": 0,
                "blobOffset": 0,
                "blobBytes": len(payload),
            }]}
            result = MODULE.decode_particle_geometry(frame, metadata, 4)
        self.assertIsNotNone(result)
        self.assertEqual(result["streamByteOffset"], 64)
        self.assertEqual(result["contiguousQuadCount"], 6)
        self.assertEqual(result["consumedQuadCount"], 4)
        self.assertAlmostEqual(result["medianAspectRatio"], 2.0)

    def test_rejects_pre_priority_recorder(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_session(Path(temporary), include_target=False)
            with self.assertRaisesRegex(MODULE.CaptureError, "no priority-retained"):
                MODULE.decode_session(root)

    def test_rejects_short_c13_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_session(Path(temporary), c13_count=13)
            with self.assertRaisesRegex(MODULE.CaptureError, "captured 13 vectors"):
                MODULE.decode_session(root)

    def test_rejects_wrong_shader_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_session(Path(temporary))
            path = root / "graphics/frames/100/metadata.json"
            metadata = json.loads(path.read_text(encoding="utf-8"))
            metadata["drawRecords"][0]["shaders"][0]["identityHash"] ^= 1
            path.write_text(json.dumps(metadata), encoding="utf-8")
            with self.assertRaisesRegex(
                    MODULE.CaptureError, "no priority-retained VS4914/PS4915"):
                MODULE.decode_session(root)


if __name__ == "__main__":
    unittest.main()

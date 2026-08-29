from __future__ import annotations

import importlib.util
import copy
import hashlib
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT_LUT = HERE.parent / (
    "Assets/EndfieldGraphShaderLab/Resources/EndfieldCharInfo/"
    "EndminfCharInfoLut1024x32Rgba16f.bytes"
)
BYTECODE = HERE / "original_dxbc_exact/bytecode"
MODULE_PATH = HERE / "verify_endminf_uber_capture.py"
SPEC = importlib.util.spec_from_file_location(
    "verify_endminf_uber_capture", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def fixture(mode: float = 3.0, priority: bool = True,
            budget: int = MODULE.MINIMUM_RESOURCE_BUDGET) -> tuple[
                dict[str, object], dict[str, object], bytes]:
    values = [0.0] * (256 * 4)
    b0_first = 4
    b1_first = 64
    vs_b0_first = 180
    values[vs_b0_first * 4:(vs_b0_first + 1) * 4] = [3840.0, 2160.0, 0.0, 0.0]
    values[(b0_first + 27) * 4:(b0_first + 28) * 4] = [1.0, 1.0, 0.0, 0.0]
    values[b1_first * 4:(b1_first + 1) * 4] = [0.51, 0.53, 0.10, 1.0]
    values[(b1_first + 25) * 4:(b1_first + 26) * 4] = [mode, 0.09, 0.0, 0.0]
    constant_blob = struct.pack(f"<{len(values)}f", *values)
    target_width = 8
    target_height = 4
    source = bytes(target_width * target_height * 8)
    bloom = bytes((target_width // 2) * (target_height // 2) * 4)
    lut = bytearray(1024 * 32 * 8)
    # The fixture needs the production LUT digest because exact live validation
    # deliberately rejects any other t2 payload.
    production_lut = (
        ROOT_LUT.read_bytes() if ROOT_LUT.is_file() else bytes(lut)
    )
    assert hashlib.sha256(production_lut).hexdigest() == (
        MODULE.EXACT_CHARINFO_LUT_SHA256
    )
    offsets = {
        "constants": 0,
        "source": len(constant_blob),
        "bloom": len(constant_blob) + len(source),
        "lut": len(constant_blob) + len(source) + len(bloom),
    }
    blob = constant_blob + source + bloom + production_lut
    session = {
        "graphicsProfile": "targeted",
        "graphicsResourceBudgetBytes": budget,
        "qpcFrequency": 10_000_000,
    }
    metadata = {
        "frame": 7,
        "selectedResourceRecords": [{
            "captureKind": 2, "objectId": 100,
            "blobOffset": offsets["constants"],
            "blobBytes": len(constant_blob),
            "completed": True, "failure": 0,
        }, {
            "captureKind": 3, "objectId": 200,
            "blobOffset": offsets["source"], "blobBytes": len(source),
            "requestedBytes": len(source), "width": target_width,
            "height": target_height, "format": 10, "viewFormat": 10,
            "completed": True, "failure": 0,
        }, {
            "captureKind": 3, "objectId": 201,
            "blobOffset": offsets["bloom"], "blobBytes": len(bloom),
            "requestedBytes": len(bloom), "width": target_width // 2,
            "height": target_height // 2, "format": 26, "viewFormat": 26,
            "completed": True, "failure": 0,
        }, {
            "captureKind": 3, "objectId": 202,
            "blobOffset": offsets["lut"],
            "blobBytes": len(production_lut),
            "requestedBytes": len(production_lut), "width": 1024,
            "height": 32, "format": 10, "viewFormat": 10,
            "completed": True, "failure": 0,
        }],
        "fullscreenResolvers": [{
            "fullscreenOrdinal": 24,
            "priorityEndminfUber": priority,
            "shaders": [{
                "stage": 0, "identityHash": MODULE.VERTEX_IDENTITY,
                "bytecodeSize": 608,
            }, {
                "stage": 4, "identityHash": MODULE.PIXEL_IDENTITY,
                "bytecodeSize": 4216,
            }],
            "resourceChain": {"psInputs": [
                {"slot": 0, "objectId": 200, "viewId": 300},
                {"slot": 1, "objectId": 201, "viewId": 301},
                {"slot": 2, "objectId": 202, "viewId": 302},
            ]},
            "vsConstantBuffers": [
                {"slot": 0, "bufferId": 100, "firstConstant": vs_b0_first,
                 "numConstants": 1, "rangeValid": True},
            ],
            "psConstantBuffers": [
                {"slot": 0, "bufferId": 100, "firstConstant": b0_first,
                 "numConstants": 28, "rangeValid": True},
                {"slot": 1, "bufferId": 100, "firstConstant": b1_first,
                 "numConstants": 32, "rangeValid": True},
            ],
            "pipelineState": {
                "valid": True,
                "target": {"width": target_width, "height": target_height,
                           "textureFormat": 28, "viewFormat": 28,
                           "sampleCount": 1, "renderTargetCount": 1,
                           "depthBound": True},
                "depthTarget": {"width": target_width, "height": target_height,
                                "textureFormat": 44, "viewFormat": 45,
                                "sampleCount": 1},
                "viewport": {"count": 1, "x": 0.0, "y": 0.0,
                             "width": float(target_width),
                             "height": float(target_height),
                             "minDepth": 0.0, "maxDepth": 1.0},
                "scissor": {"count": 1, "left": 0, "top": 0,
                            "right": target_width, "bottom": target_height},
                "sampler": {"filter": 21, "addressU": 3, "addressV": 3,
                            "addressW": 3, "comparison": 1,
                            "mipBias": 0.0, "maxAnisotropy": 1,
                            "minLod": 0.0, "maxLod": 3.4e38},
                "blend": {"enabled": False, "source": 2,
                          "destination": 1, "operation": 1,
                          "sourceAlpha": 2, "destinationAlpha": 1,
                          "operationAlpha": 1, "writeMask": 15,
                          "factor": [0.0, 0.0, 0.0, 0.0],
                          "sampleMask": 0xffffffff},
                "depthStencil": {"depthEnabled": False, "writeMask": 0,
                                 "function": 8, "stencilEnabled": False,
                                 "stencilReference": 0},
                "rasterizer": {"fillMode": 3, "cullMode": 1,
                               "frontCounterClockwise": False,
                               "depthClipEnabled": True,
                               "scissorEnabled": True,
                               "multisampleEnabled": False,
                               "antialiasedLineEnabled": False},
            },
        }],
    }
    return session, metadata, blob


class UberCaptureTests(unittest.TestCase):
    def build(self, session: dict[str, object], metadata: dict[str, object],
              blob: bytes, constant_payload_only: bool = False,
              frame_filter: int | None = None) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as temporary:
            capture = Path(temporary)
            (capture / "session.json").write_text(
                json.dumps(session), encoding="utf-8")
            frame = capture / "graphics/frames/7"
            frame.mkdir(parents=True)
            (frame / "metadata.json").write_text(
                json.dumps(metadata), encoding="utf-8")
            (frame / "resources.bin").write_bytes(blob)
            return MODULE.build_report(
                capture,
                constant_payload_only=constant_payload_only,
                frame_filter=frame_filter,
            )

    def build_sequence(
        self,
        session: dict[str, object],
        rows: list[tuple[dict[str, object], bytes]],
        summary_overrides: dict[str, object] | None = None,
    ) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as temporary:
            capture = Path(temporary)
            session = dict(session)
            session["graphicsProfile"] = "full"
            (capture / "session.json").write_text(
                json.dumps(session), encoding="utf-8")
            summary = {
                "complete": True,
                "cadenceValid": True,
                "deferredFailed": False,
                "shaderBytecodeArchiveComplete": True,
                "deferredStagedSlots": len(rows),
                "deferredPublishedSlots": len(rows),
                "sequenceFrames": len(rows),
            }
            if summary_overrides:
                summary.update(summary_overrides)
            graphics = capture / "graphics"
            graphics.mkdir(parents=True)
            (graphics / "summary.json").write_text(
                json.dumps(summary), encoding="utf-8")
            for metadata, blob in rows:
                frame = graphics / "frames" / str(metadata["frame"])
                frame.mkdir(parents=True)
                (frame / "metadata.json").write_text(
                    json.dumps(metadata), encoding="utf-8")
                (frame / "resources.bin").write_bytes(blob)
            shader_root = graphics / "shaders"
            shader_root.mkdir()
            shader_sources = (
                ("endminf_uber_post_vs.dxbc", MODULE.VERTEX_SHA256, 0),
                ("endminf_uber_post_normal_ps.dxbc",
                 MODULE.NORMAL_PIXEL_SHA256, 4),
                ("endminf_uber_post_ps.dxbc", MODULE.PIXEL_SHA256, 4),
            )
            for source_name, digest, stage in shader_sources:
                (shader_root / f"{digest}-s{stage}.dxbc").write_bytes(
                    (BYTECODE / source_name).read_bytes())
            return MODULE.build_sequence_report(capture)

    def sequence_fixture(self) -> tuple[
            dict[str, object], list[tuple[dict[str, object], bytes]]]:
        session, peak, blob = fixture()
        rows = []
        for frame, variant in ((6, "normal"), (7, "peak"), (8, "normal")):
            metadata = copy.deepcopy(peak)
            metadata["frame"] = frame
            shader = metadata["fullscreenResolvers"][0]["shaders"][1]
            if variant == "normal":
                shader["identityHash"] = MODULE.NORMAL_PIXEL_IDENTITY
                shader["bytecodeSize"] = 3416
            rows.append((metadata, blob))
        return session, rows

    def test_exact_live_binding_passes(self) -> None:
        report = self.build(*fixture())
        self.assertEqual(report["status"], "validated_exact_live_uber_binding")
        self.assertEqual(len(report["packets"][0]["vsB0"]["values"]), 1)
        self.assertEqual(len(report["packets"][0]["b0"]["values"]), 28)
        self.assertEqual(len(report["packets"][0]["b1"]["values"]), 26)
        self.assertEqual(report["packets"][0]["b1"]["c25RadialBlurParams2"][0],
                         3.0)

    def test_old_budget_fails_closed(self) -> None:
        with self.assertRaisesRegex(MODULE.VerificationError, "128-MiB"):
            self.build(*fixture(budget=96 * 1024 * 1024))

    def test_constant_only_mode_keeps_old_budget_boundary_visible(self) -> None:
        session, metadata, blob = fixture(budget=96 * 1024 * 1024)
        del metadata["fullscreenResolvers"][0]["pipelineState"]
        metadata["fullscreenResolvers"][0]["priorityEndminfUber"] = False
        report = self.build(
            session,
            metadata,
            blob,
            constant_payload_only=True,
            frame_filter=7,
        )
        self.assertEqual(
            report["status"],
            "validated_exact_uber_constant_payload_only",
        )
        self.assertNotIn("pipelineState", report["packets"][0])
        self.assertEqual(report["resourceBudgetBytes"], 96 * 1024 * 1024)
        self.assertEqual(
            report["compiledKeywords"],
            ["BLOOM", "RADIAL_BLUR", "VIGNETTE"],
        )

    def test_full_profile_constant_payload_passes(self) -> None:
        session, metadata, blob = fixture()
        session["graphicsProfile"] = "full"
        report = self.build(
            session,
            metadata,
            blob,
            constant_payload_only=True,
            frame_filter=7,
        )
        self.assertEqual(
            report["status"],
            "validated_exact_uber_constant_payload_only",
        )
        self.assertEqual(report["graphicsProfile"], "full")

    def test_unknown_profile_fails_with_expected_and_actual(self) -> None:
        session, metadata, blob = fixture()
        session["graphicsProfile"] = "debug"
        with self.assertRaisesRegex(
                MODULE.VerificationError,
                "expected targeted or full, got 'debug'"):
            self.build(session, metadata, blob)

    def test_missing_priority_tag_fails_closed(self) -> None:
        with self.assertRaisesRegex(MODULE.VerificationError, "priority tagging"):
            self.build(*fixture(priority=False))

    def test_missing_vertex_range_fails_closed(self) -> None:
        session, metadata, blob = fixture()
        metadata["fullscreenResolvers"][0]["vsConstantBuffers"] = []
        with self.assertRaisesRegex(MODULE.VerificationError, "VS b0"):
            self.build(session, metadata, blob)

    def test_unexpected_mode_fails_closed(self) -> None:
        with self.assertRaisesRegex(MODULE.VerificationError, "mode is unexpected"):
            self.build(*fixture(mode=4.0))

    def test_missing_pipeline_state_fails_closed(self) -> None:
        session, metadata, blob = fixture()
        del metadata["fullscreenResolvers"][0]["pipelineState"]
        with self.assertRaisesRegex(MODULE.VerificationError,
                                    "pipeline state is absent"):
            self.build(session, metadata, blob)

    def test_missing_bloom_payload_names_t1_gate(self) -> None:
        session, metadata, blob = fixture()
        metadata["selectedResourceRecords"] = [
            row for row in metadata["selectedResourceRecords"]
            if row["objectId"] != 201
        ]
        with self.assertRaisesRegex(
                MODULE.VerificationError,
                "t1 bloom selected texture payload is not unique"):
            self.build(session, metadata, blob)

    def test_charinfo_lut_hash_drift_fails_closed(self) -> None:
        session, metadata, blob = fixture()
        corrupted = bytearray(blob)
        corrupted[-1] ^= 0x01
        with self.assertRaisesRegex(
                MODULE.VerificationError,
                "t2 CharInfo LUT hash drifted"):
            self.build(session, metadata, bytes(corrupted))

    def test_complete_ordinary_peak_sequence_passes(self) -> None:
        report = self.build_sequence(*self.sequence_fixture())
        self.assertEqual(
            report["status"], "validated_exact_live_uber_sequence")
        self.assertEqual(report["variantCounts"], {"normal": 2, "peak": 1})
        self.assertEqual(report["peakFrame"], 7)
        self.assertEqual(report["peakPreviousFrame"], 6)
        self.assertEqual(report["peakNextFrame"], 8)
        self.assertEqual(report["packets"][0]["b1"]["declaredConstants"], 12)
        self.assertEqual(report["packets"][1]["b1"]["declaredConstants"], 26)

    def test_sequence_invalid_cadence_fails_closed(self) -> None:
        with self.assertRaisesRegex(MODULE.VerificationError,
                                    "cadence is invalid"):
            self.build_sequence(
                *self.sequence_fixture(),
                summary_overrides={"cadenceValid": False},
            )

    def test_sequence_duplicate_peak_fails_closed(self) -> None:
        session, rows = self.sequence_fixture()
        metadata, blob = rows[2]
        metadata["fullscreenResolvers"][0]["shaders"][1][
            "identityHash"] = MODULE.PIXEL_IDENTITY
        metadata["fullscreenResolvers"][0]["shaders"][1][
            "bytecodeSize"] = 4216
        with self.assertRaisesRegex(MODULE.VerificationError,
                                    "requires one peak packet, got 2"):
            self.build_sequence(session, rows)

    def test_sequence_shader_read_lane_drift_fails_closed(self) -> None:
        session, rows = self.sequence_fixture()
        metadata, blob = rows[2]
        drifted = bytearray(blob)
        struct.pack_into("<f", drifted, (64 + 1) * 16, 0.25)
        rows[2] = (metadata, bytes(drifted))
        with self.assertRaisesRegex(MODULE.VerificationError,
                                    "shader-read ordinary Uber lane varies"):
            self.build_sequence(session, rows)


if __name__ == "__main__":
    unittest.main()

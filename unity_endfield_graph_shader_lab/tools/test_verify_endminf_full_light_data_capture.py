#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import struct
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("verify_endminf_full_light_data_capture.py")
SPEC = importlib.util.spec_from_file_location("verify_endminf_full_light_data_capture", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

REPO = Path(__file__).resolve().parents[2]
CLEAN_SESSION = REPO / "scratch/reverse_engineering/endfield_capture/20260828T121603Z"
OPERATOR_LIGHTS = (
    REPO
    / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/OriginalData/RenderParameters/operator_lights.json"
)


class EndminfFullLightDataCaptureTests(unittest.TestCase):
    @unittest.skipUnless(
        CLEAN_SESSION.exists() and OPERATOR_LIGHTS.exists(),
        "clean raw capture integration fixture is not present",
    )
    def test_clean_capture_active_prefix_and_tail_boundary(self) -> None:
        report = MODULE.verify(CLEAN_SESSION, OPERATOR_LIGHTS)
        self.assertTrue(report["valid"])
        self.assertEqual(report["ownedBytes"], 1632)
        self.assertFalse(report["captureTailOwned"])

    def test_active_prefix_hash_rejects_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "resources.bin"
            active = bytes(MODULE.ACTIVE_BYTES)
            self._write_sparse_resource(path, active)
            metadata = self._minimal_metadata()
            with self.assertRaisesRegex(MODULE.VerificationError, "active prefix hash mismatch"):
                MODULE.extract_active_prefix(
                    metadata,
                    path,
                    expected_sha256="f" * 64,
                )

    def test_short_resource_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "resources.bin"
            short_size = MODULE.BLOB_OFFSET + MODULE.FIRST_CONSTANT * 16 + MODULE.ACTIVE_BYTES - 1
            with path.open("wb") as stream:
                stream.seek(short_size - 1)
                stream.write(b"\0")
            metadata = self._minimal_metadata()
            with self.assertRaisesRegex(MODULE.VerificationError, "truncated"):
                MODULE.extract_active_prefix(metadata, path)

    def test_tail_mutation_is_outside_owned_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "resources.bin"
            active = bytes(MODULE.ACTIVE_BYTES)
            self._write_sparse_resource(path, active)
            with path.open("r+b") as stream:
                stream.seek(
                    MODULE.BLOB_OFFSET +
                    MODULE.FIRST_CONSTANT * 16 +
                    MODULE.ACTIVE_BYTES + 32
                )
                stream.write(b"\xA5")
            extracted = MODULE.extract_active_prefix(
                self._minimal_metadata(),
                path,
                expected_sha256=MODULE.sha256_bytes(active),
            )
            self.assertEqual(extracted, active)

    def test_nonunique_resolver_is_rejected(self) -> None:
        metadata = self._minimal_metadata()
        metadata["fullscreenResolvers"].append(
            dict(metadata["fullscreenResolvers"][0])
        )
        with self.assertRaisesRegex(MODULE.VerificationError, "expected one"):
            MODULE.select_binding(metadata)

    def test_wrong_b5_range_is_rejected(self) -> None:
        metadata = self._minimal_metadata()
        metadata["fullscreenResolvers"][0]["psConstantBuffers"][0]["firstConstant"] += 1
        with self.assertRaisesRegex(MODULE.VerificationError, "range offset"):
            MODULE.select_binding(metadata)

    def test_wrong_retained_resource_stage_is_rejected(self) -> None:
        metadata = self._minimal_metadata()
        metadata["selectedResourceRecords"][0]["stage"] = 0
        with self.assertRaisesRegex(MODULE.VerificationError, "expected one retained"):
            MODULE.select_binding(metadata)

    def test_invariant_includes_source_stable_oct_lanes(self) -> None:
        active = bytearray(MODULE.ACTIVE_BYTES)
        before = MODULE.sha256_bytes(MODULE.invariant_bytes(active))
        byte_offset = (
            MODULE.HEADER_VECTORS + 3 * MODULE.VECTORS_PER_LIGHT + 2
        ) * 16
        active[byte_offset] ^= 0x80
        after = MODULE.sha256_bytes(MODULE.invariant_bytes(active))
        self.assertNotEqual(before, after)

    def test_source_identity_accepts_synthetic_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "operator_lights.json"
            source.write_text(json.dumps(self._synthetic_source_payload()), encoding="utf-8")
            MODULE.validate_source_identity(self._synthetic_active_prefix(), source)

    def test_source_identity_rejects_unsupported_light_type(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payload = self._synthetic_source_payload()
            payload["actors"]["endminf"]["lights"][4]["light_type"] = 1
            source = Path(directory) / "operator_lights.json"
            source.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(MODULE.VerificationError, "unsupported light type"):
                MODULE.validate_source_identity(self._synthetic_active_prefix(), source)

    def test_source_identity_rejects_shadow_source_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payload = self._synthetic_source_payload()
            payload["actors"]["endminf"]["lights"][3]["shadow_type"] = 0
            source = Path(directory) / "operator_lights.json"
            source.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(MODULE.VerificationError, "shadow source set drift"):
                MODULE.validate_source_identity(self._synthetic_active_prefix(), source)

    def test_source_identity_rejects_unsupported_shadow_type(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payload = self._synthetic_source_payload()
            payload["actors"]["endminf"]["lights"][4]["shadow_type"] = 1
            source = Path(directory) / "operator_lights.json"
            source.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(MODULE.VerificationError, "unsupported shadow type"):
                MODULE.validate_source_identity(self._synthetic_active_prefix(), source)

    def test_incomplete_summary_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory)
            (session / "graphics").mkdir()
            (session / "collected").mkdir()
            graphics = self._minimal_graphics_summary()
            graphics["complete"] = False
            (session / "graphics" / "summary.json").write_text(
                json.dumps(graphics), encoding="utf-8"
            )
            (session / "collected" / "summary.json").write_text(
                json.dumps(self._minimal_collected_summary()), encoding="utf-8"
            )
            with self.assertRaisesRegex(MODULE.VerificationError, "incomplete"):
                MODULE.validate_summaries(session)

    @staticmethod
    def _minimal_metadata() -> dict:
        return {
            "frame": MODULE.FRAME,
            "drawRecordsTruncated": False,
            "dispatchRecordsTruncated": False,
            "resourceSelectionTruncated": False,
            "captureIncomplete": False,
            "captureFailed": False,
            "fullscreenResolverRecordsTruncated": False,
            "droppedEvents": 0,
            "fullscreenResolvers": [
                {
                    "priorityDeferredRangeShape": True,
                    "fullscreenOrdinal": MODULE.FULLSCREEN_ORDINAL,
                    "shaders": [
                        {"stage": 0, "identityHash": MODULE.VERTEX_SHADER},
                        {"stage": 4, "identityHash": MODULE.PIXEL_SHADER},
                    ],
                    "psConstantBuffers": [
                        {
                            "slot": 5,
                            "bufferId": MODULE.BUFFER_ID,
                            "firstConstant": MODULE.FIRST_CONSTANT,
                            "numConstants": MODULE.BOUND_CONSTANTS,
                            "byteWidth": MODULE.BUFFER_BYTES,
                            "rangeValid": True,
                        }
                    ],
                }
            ],
            "selectedResourceRecords": [
                {
                    "captureKind": 2,
                    "objectId": MODULE.BUFFER_ID,
                    "stage": 4,
                    "slot": 0,
                    "completed": True,
                    "failure": 0,
                    "blobOffset": MODULE.BLOB_OFFSET,
                    "blobBytes": MODULE.BUFFER_BYTES,
                    "byteSize": MODULE.BUFFER_BYTES,
                }
            ],
        }

    @staticmethod
    def _minimal_graphics_summary() -> dict:
        return {
            "schema": "endfieldCapture.graphicsSummary.v1",
            "runtimeMode": "d3d11-proxy",
            "graphicsProfile": "full",
            "hooksInstalled": True,
            "attached": True,
            "dropped": 0,
            "sequenceAutomatic": True,
            "quiescentCleanup": True,
            "complete": True,
        }

    @staticmethod
    def _minimal_collected_summary() -> dict:
        return {
            "schema": "endfieldCapture.summary.v1",
            "records": 1,
            "dropped": 0,
            "invalidRecords": 0,
            "writerError": False,
            "complete": True,
        }

    @staticmethod
    def _synthetic_source_payload() -> dict:
        rows = []
        spot_sources = {0, 1, 3, 11}
        for source_index in range(MODULE.LIGHT_COUNT):
            rows.append(
                {
                    "index": source_index,
                    "light_type": 0 if source_index in spot_sources else 2,
                    "shadow_type": 2 if source_index in (3, 11) else 0,
                    "range": float(source_index + 1),
                }
            )
        return {
            "schema": "endfield.original-operator-lights.v1",
            "validation": {
                "ok": True,
                "actor_counts": {"endminf": MODULE.LIGHT_COUNT},
            },
            "actors": {
                "endminf": {
                    "count": MODULE.LIGHT_COUNT,
                    "group_name": "light_overview",
                    "lights": rows,
                }
            },
        }

    @staticmethod
    def _synthetic_active_prefix() -> bytes:
        payload = EndminfFullLightDataCaptureTests._synthetic_source_payload()
        rows = payload["actors"]["endminf"]["lights"]
        words = [0] * (MODULE.ACTIVE_BYTES // 4)
        for packed, source_index in enumerate(MODULE.EXPECTED_SOURCE_ORDER):
            base = (MODULE.HEADER_VECTORS + packed * MODULE.VECTORS_PER_LIGHT) * 4
            inverse = 1.0 / float(rows[source_index]["range"])
            words[base + 7] = struct.unpack("<I", struct.pack("<f", inverse))[0]
            if rows[source_index]["light_type"] == 0:
                shadow = 40.0 if source_index == 3 else 41.0 if source_index == 11 else -1.0
                words[base + 12] = struct.unpack("<I", struct.pack("<f", shadow))[0]
            else:
                words[base + 11] = 0xFFFFFFFF
                words[base + 12] = 0x0000FFFF
        return struct.pack(f"<{len(words)}I", *words)

    @staticmethod
    def _write_sparse_resource(path: Path, active: bytes) -> None:
        total = MODULE.BLOB_OFFSET + MODULE.BUFFER_BYTES
        with path.open("wb") as stream:
            stream.seek(total - 1)
            stream.write(b"\0")
            stream.seek(MODULE.BLOB_OFFSET + MODULE.FIRST_CONSTANT * 16)
            stream.write(active)


if __name__ == "__main__":
    unittest.main()

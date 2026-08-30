from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location(
    "convert_endminf_m27_capture_to_live_observation",
    HERE / "convert_endminf_m27_capture_to_live_observation.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, separators=(",", ":")) + "\n",
                    encoding="utf-8", newline="\n")


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PackageFixture:
    def __init__(self, parent: Path) -> None:
        self.root = parent / "capture-session"
        self.root.mkdir()
        self.frame_path = self.root / "graphics/frames/100/metadata.json"
        self.resources_path = self.root / "graphics/frames/100/resources.bin"
        self._build()

    def _build(self) -> None:
        session = {
            "schema": "endfieldCapture.session.v1",
            "sessionId": self.root.name,
            "providers": 1,
            "graphicsProfile": "targeted",
            "evidenceLabel": "unit-test",
        }
        runtime = {
            "schema": "endfieldCapture.runtimeStatus.v1",
            "graphicsProfile": "targeted",
            "graphicsSelected": True,
            "graphicsHooksInstalled": True,
            "graphicsAttached": True,
            "graphicsDropped": 0,
            "framePending": False,
            "frameCompleted": True,
            "frameIncomplete": False,
            "frameFailed": False,
        }
        collected = {
            "schema": "endfieldCapture.summary.v1",
            "dropped": 0,
            "invalidRecords": 0,
            "writerError": False,
            "complete": True,
        }
        graphics = {
            "schema": "endfieldCapture.graphicsSummary.v1",
            "evidenceLabel": "unit-test",
            "graphicsProfile": "targeted",
            "hooksInstalled": True,
            "attached": True,
            "dropped": 0,
            "deferredFailed": False,
            "quiescentCleanup": True,
            "shaderBytecodeArchiveComplete": True,
            "complete": True,
        }
        _write_json(self.root / "session.json", session)
        _write_json(self.root / "runtime.status.json", runtime)
        _write_json(self.root / "collected/summary.json", collected)
        _write_json(self.root / "graphics/summary.json", graphics)

        shader_root = self.root / "graphics/shaders"
        shader_root.mkdir(parents=True)
        for stage, digest, source in (
            (0, MODULE.VS_SHA256, "endminf_m27_hgbuffer_vs.dxbc"),
            (4, MODULE.PS_SHA256, "endminf_m27_hgbuffer_ps.dxbc"),
        ):
            data = (REPO / "unity_endfield_graph_shader_lab/tools/"
                    "original_dxbc_exact/bytecode" / source).read_bytes()
            (shader_root / f"{digest}-s{stage}.dxbc").write_bytes(data)

        indices = [index % 29 for index in range(MODULE.M27_INDEX_COUNT)]
        ia_blob = bytearray(4160)
        ia_blob[2000:4160] = struct.pack("<" + "H" * len(indices), *indices)
        t0_blob = bytes(range(64))
        texture_blobs = [bytes([slot + 1]) * 16 for slot in range(4)]
        payload = bytes(ia_blob) + t0_blob + b"".join(texture_blobs)
        self.resources_path.parent.mkdir(parents=True, exist_ok=True)
        self.resources_path.write_bytes(payload)
        (self.resources_path.parent / "bindings.v2.bin").write_bytes(b"bindings")

        selected = [
            self._resource(0, 1000, 0, 0, 4160, 0, 4160,
                           stride=60, byte_offset=0),
            self._resource(1, 1000, 0, 0, 4160, 0, 4160,
                           format_value=MODULE.R16_UINT, stride=2,
                           byte_offset=2000),
            self._resource(4, 2000, 0, 0, 64, 4160, 64),
        ]
        texture_offset = 4224
        for slot, (width, height, texture_format) in MODULE.EXPECTED_TEXTURES.items():
            selected.append(self._resource(
                3, 3000 + slot, 4, slot, 16, texture_offset + slot * 16, 16,
                width=width, height=height, format_value=texture_format,
                view_format=texture_format))

        record = bytearray(256)
        for index in range(4):
            struct.pack_into("<f", record, (index * 4 + index) * 4, 1.0)
        vs_prefix = bytes(record) + bytes(104 * 16 - len(record))
        ps_prefix = bytes(record)
        constant_buffers = [
            self._cb(0, 2, 5000, 104, vs_prefix),
            self._cb(4, 2, 5000, 16, ps_prefix),
        ]
        resources = [
            {"objectId": 1000, "viewId": 0, "bound": True,
             "descriptorHash": 1, "kind": 1, "stage": 0, "slot": 0,
             "byteSize": 4160},
            {"objectId": 2000, "viewId": 2001, "bound": True,
             "descriptorHash": 22, "kind": 1, "stage": 0, "slot": 0,
             "byteSize": 64, "viewDimension": 1, "bindFlags": 136,
             "miscFlags": 64, "structureByteStride": 16,
             "viewFirstElement": 0, "viewNumElements": 4},
        ]
        for slot, (_, _, texture_format) in MODULE.EXPECTED_TEXTURES.items():
            resources.append({
                "objectId": 3000 + slot, "viewId": 4000 + slot,
                "bound": True, "descriptorHash": 100 + slot, "kind": 3,
                "stage": 4, "slot": slot, "byteSize": 16,
                "viewFormat": texture_format,
            })
        for slot in (4, 5):
            resources.append({
                "objectId": 9000, "viewId": 9001, "bound": True,
                "descriptorHash": 9002, "kind": 3, "stage": 4,
                "slot": slot, "byteSize": 64, "viewFormat": 29,
            })
        draw = {
            "drawOrdinal": 7,
            "count": MODULE.M27_INDEX_COUNT,
            "start": 0,
            "indexedInstanced": True,
            "topology": MODULE.TRIANGLE_LIST,
            "priorityShaderPair": True,
            "priorityM27Geometry": True,
            "instanceCount": 1,
            "baseVertex": 0,
            "startInstance": 0,
            "vsCb2RangeValid": True,
            "vsCb2FirstConstant": 123,
            "vsCb2NumConstants": 4096,
            "vsCb2BufferId": 5000,
            "vsCb2MetadataValid": True,
            "inputAssembler": {
                "vertexBuffers": [
                    {"slot": 0, "objectId": 1000, "stride": 60, "offset": 0}],
                "indexBuffer": {
                    "objectId": 1000, "format": MODULE.R16_UINT, "offset": 2000},
            },
            "constantBuffers": constant_buffers,
            "shaders": [
                {"stage": 0, "identityHash": MODULE.VS_IDENTITY,
                 "bytecodeSize": MODULE.VS_BYTES},
                {"stage": 4, "identityHash": MODULE.PS_IDENTITY,
                 "bytecodeSize": MODULE.PS_BYTES},
            ],
            "resources": resources,
            "pipelineState": self._pipeline(),
        }
        frame = {
            "schema": "endfieldCapture.graphicsFrame.v1",
            "frame": 100,
            "timestampQpc": 123456,
            "draws": 1,
            "observedDraws": 1,
            "drawRecordsTruncated": False,
            "resourceSelectionTruncated": False,
            "captureIncomplete": False,
            "captureFailed": False,
            "droppedEvents": 0,
            "resourceCaptureIncomplete": False,
            "resourceCaptureFailed": False,
            "selectedResources": len(selected),
            "selectedResourceRecords": selected,
            "resourceBlobBytes": len(payload),
            "drawRecords": [draw],
            "bindingsFile": "bindings.v2.bin",
            "resourcesFile": "resources.bin",
            "backbufferFile": None,
        }
        _write_json(self.frame_path, frame)
        self.rebuild_inventory()

    @staticmethod
    def _resource(kind: int, object_id: int, stage: int, slot: int,
                  byte_size: int, blob_offset: int, blob_bytes: int,
                  **values: int) -> dict[str, object]:
        return {
            "captureKind": kind, "objectId": object_id, "stage": stage,
            "slot": slot, "byteSize": byte_size,
            "width": values.get("width", 0), "height": values.get("height", 0),
            "format": values.get("format_value", 0),
            "viewFormat": values.get("view_format", 0), "subresource": 0,
            "stride": values.get("stride", 0),
            "byteOffset": values.get("byte_offset", 0),
            "requestedBytes": byte_size, "blobOffset": blob_offset,
            "blobBytes": blob_bytes, "failure": 0, "completed": True,
        }

    @staticmethod
    def _cb(stage: int, slot: int, buffer_id: int, count: int,
            payload: bytes) -> dict[str, object]:
        return {
            "stage": stage, "slot": slot, "bufferId": buffer_id,
            "firstConstant": 123, "numConstants": 4096,
            "capturedConstants": count, "rangeValid": True,
            "metadataValid": True, "truncated": True,
            "dataHex": payload.hex(),
        }

    @staticmethod
    def _pipeline() -> dict[str, object]:
        target = {"width": 1920, "height": 1080, "textureFormat": 26,
                  "viewFormat": 26, "sampleCount": 1,
                  "renderTargetCount": 5, "depthBound": True}
        return {
            "valid": True, "target": target,
            "renderTargets": [
                {"slot": slot, "bound": slot < 5,
                 "width": 1920 if slot < 5 else 0,
                 "height": 1080 if slot < 5 else 0,
                 "textureFormat": [26, 24, 24, 24, 29][slot] if slot < 5 else 0,
                 "viewFormat": [26, 24, 24, 24, 29][slot] if slot < 5 else 0,
                 "sampleCount": 1 if slot < 5 else 0}
                for slot in range(8)],
            "depthTarget": {"width": 1920, "height": 1080,
                            "textureFormat": 19, "viewFormat": 20,
                            "sampleCount": 1},
            "viewport": {"count": 1, "x": 0, "y": 0,
                         "width": 1920, "height": 1080},
            "depthStencil": {"writeMask": 1, "function": 7},
            "rasterizer": {"cullMode": 3, "frontCounterClockwise": True,
                           "scissorEnabled": True},
            "samplers": [
                {"slot": slot, "bound": True, "filter": 20}
                for slot in range(6)],
        }

    def load_frame(self) -> dict[str, object]:
        return json.loads(self.frame_path.read_text(encoding="utf-8"))

    def save_frame(self, frame: dict[str, object]) -> None:
        _write_json(self.frame_path, frame)
        self.rebuild_inventory()

    def rebuild_inventory(self) -> None:
        inventory_path = self.root / "collected/inventory.json"
        inventory_path.unlink(missing_ok=True)
        rows = []
        for path in sorted(value for value in self.root.rglob("*") if value.is_file()):
            rows.append({
                "path": path.relative_to(self.root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _hash(path),
            })
        _write_json(inventory_path, {
            "schema": "endfieldCapture.collection.v1",
            "session": self.root.name,
            "files": len(rows),
            "bytes": sum(row["bytes"] for row in rows),
            "artifacts": rows,
        })


class ConverterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.fixture = PackageFixture(Path(self.temp.name))
        self.extent = mock.patch.multiple(
            MODULE, VERTEX_SKIN_BUFFER_BYTES=64,
            VERTEX_SKIN_BUFFER_ELEMENTS=4)
        self.extent.start()

    def tearDown(self) -> None:
        self.extent.stop()
        self.temp.cleanup()

    def test_authenticated_package_emits_only_partial_raw_evidence(self) -> None:
        result = MODULE.build_observation(self.fixture.root)
        self.assertEqual(result["schema"], MODULE.LIVE_SCHEMA)
        self.assertEqual(
            result["status"], "raw_capture_authenticated_unity_fields_unresolved")
        self.assertTrue(result["vertexResources"][0]["bound"])
        self.assertEqual(result["vertexResources"][0]["payloadBytes"], 64)
        self.assertFalse(result["vertexSkinningControl"]["skinBranchActive"])
        self.assertNotIn("sourceMeshSkinRows", result["vertexSkinningControl"])
        self.assertNotIn("renderer", result)
        self.assertNotIn("publishers", result)
        serialized = json.dumps(result)
        self.assertNotIn("dataHex", serialized)
        self.assertNotIn('"capturedPacketArrays":', serialized)

    def test_historical_v1_bindings_sidecar_is_accepted(self) -> None:
        frame = self.fixture.load_frame()
        frame["bindingsFile"] = "bindings.v1.bin"
        v2_path = self.fixture.resources_path.parent / "bindings.v2.bin"
        v1_path = self.fixture.resources_path.parent / "bindings.v1.bin"
        v1_path.write_bytes(v2_path.read_bytes())
        v2_path.unlink()
        self.fixture.save_frame(frame)
        result = MODULE.build_observation(self.fixture.root)
        self.assertEqual(result["schema"], MODULE.LIVE_SCHEMA)

    def test_inventory_hash_mismatch_is_rejected(self) -> None:
        self.fixture.resources_path.write_bytes(
            self.fixture.resources_path.read_bytes() + b"drift")
        with self.assertRaisesRegex(MODULE.ConversionError, "byte mismatch"):
            MODULE.build_observation(self.fixture.root)

    def test_incomplete_graphics_summary_is_rejected(self) -> None:
        path = self.fixture.root / "graphics/summary.json"
        summary = json.loads(path.read_text(encoding="utf-8"))
        summary["complete"] = False
        _write_json(path, summary)
        self.fixture.rebuild_inventory()
        with self.assertRaisesRegex(MODULE.ConversionError, "graphics summary"):
            MODULE.build_observation(self.fixture.root)

    def test_selected_frame_resource_truncation_is_rejected(self) -> None:
        frame = self.fixture.load_frame()
        frame["resourceSelectionTruncated"] = True
        self.fixture.save_frame(frame)
        with self.assertRaisesRegex(MODULE.ConversionError,
                                    "resourceSelectionTruncated=true"):
            MODULE.build_observation(self.fixture.root)

    def test_ambiguous_exact_draw_is_rejected(self) -> None:
        frame = self.fixture.load_frame()
        duplicate = copy.deepcopy(frame["drawRecords"][0])
        duplicate["drawOrdinal"] = 8
        frame["drawRecords"].append(duplicate)
        frame["draws"] = frame["observedDraws"] = 2
        self.fixture.save_frame(frame)
        with self.assertRaisesRegex(MODULE.ConversionError, "found 2"):
            MODULE.build_observation(self.fixture.root)

    def test_missing_explicit_vertex_t0_outcome_is_rejected(self) -> None:
        frame = self.fixture.load_frame()
        frame["drawRecords"][0]["resources"] = [
            row for row in frame["drawRecords"][0]["resources"]
            if row.get("objectId") != 2000]
        self.fixture.save_frame(frame)
        with self.assertRaisesRegex(MODULE.ConversionError,
                                    "explicit draw-local VS t0 outcome"):
            MODULE.build_observation(self.fixture.root)

    def test_explicit_unbound_vertex_t0_outcome_is_preserved(self) -> None:
        frame = self.fixture.load_frame()
        resources = frame["drawRecords"][0]["resources"]
        t0 = next(row for row in resources if row.get("objectId") == 2000)
        t0.clear()
        t0.update({
            "objectId": 0, "viewId": 0, "bound": False,
            "kind": 1, "stage": 0, "slot": 0,
        })
        self.fixture.save_frame(frame)
        result = MODULE.build_observation(self.fixture.root)
        self.assertEqual(result["vertexResources"], [{
            "slot": 0,
            "bound": False,
            "objectId": 0,
            "viewId": 0,
            "observedFromActualDraw": True,
            "synchronizedDrawId": "capture-session:frame:100:qpc:123456:draw:7",
        }])

    def test_incomplete_bound_vertex_t0_payload_is_rejected(self) -> None:
        frame = self.fixture.load_frame()
        t0 = next(row for row in frame["selectedResourceRecords"]
                  if row["captureKind"] == 4)
        t0["blobBytes"] = 63
        self.fixture.save_frame(frame)
        with self.assertRaisesRegex(MODULE.ConversionError,
                                    "captured VS t0 structured buffer"):
            MODULE.build_observation(self.fixture.root)

    def test_bound_vertex_t0_wrong_resource_kind_is_rejected(self) -> None:
        frame = self.fixture.load_frame()
        t0 = next(row for row in frame["drawRecords"][0]["resources"]
                  if row.get("objectId") == 2000)
        t0["kind"] = 3
        self.fixture.save_frame(frame)
        with self.assertRaisesRegex(MODULE.ConversionError,
                                    "explicit draw-local VS t0 outcome"):
            MODULE.build_observation(self.fixture.root)

    def test_bound_vertex_t0_requires_explicit_boolean_bound_state(self) -> None:
        for invalid in (None, 1):
            with self.subTest(bound=invalid):
                frame = self.fixture.load_frame()
                t0 = next(row for row in frame["drawRecords"][0]["resources"]
                          if row.get("objectId") == 2000)
                t0["bound"] = invalid
                self.fixture.save_frame(frame)
                with self.assertRaisesRegex(
                        MODULE.ConversionError,
                        "explicit draw-local VS t0 outcome"):
                    MODULE.build_observation(self.fixture.root)
                t0["bound"] = True
                self.fixture.save_frame(frame)


if __name__ == "__main__":
    unittest.main()

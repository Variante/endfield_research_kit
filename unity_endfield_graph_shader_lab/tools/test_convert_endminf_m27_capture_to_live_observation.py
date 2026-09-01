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
            "exactOwnerResourcePayloadTiming": "draw-local",
            "exactOwnerResourcePayloadDrawLocal": True,
            "publishableM20Packets": 1,
            "publishableM21Packets": 1,
            "publishableM27Packets": 1,
            "publishableDefaultDeferredPackets": 1,
            "publishableM27DefaultDeferredJoinedPackets": 1,
            "exactScreenShadowAdmissionRequiredPackets": 1,
            "exactScreenShadowAdmissionPassedPackets": 1,
            "exactScreenShadowAdmissionFailedPackets": 0,
            "exactScreenShadowAdmissionPassed": True,
            "exactEndminfPublishable": True,
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
        terrain_profile_buffer = bytearray(64)
        struct.pack_into("<f", terrain_profile_buffer, 16 + 12, 2.0)
        terrain_profile_offset = 4160 + 64 + 4 * 16
        payload = (bytes(ia_blob) + t0_blob + b"".join(texture_blobs) +
                   bytes(terrain_profile_buffer))
        self.resources_path.parent.mkdir(parents=True, exist_ok=True)
        self.resources_path.write_bytes(payload)

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
        for slot in (4, 5):
            selected.append(self._resource(
                3, 9000, 4, slot, 64, 4160, 64, view_format=29))
        selected.extend([
            self._resource(2, 5000, 0, 2, 65536, 0, 4160,
                           requested_bytes=4160),
            self._resource(2, 5000, 4, 2, 65536, 0, 4160,
                           requested_bytes=4160),
            self._resource(
                2, 6000, 4, MODULE.TERRAIN_PROFILE_CB_SLOT,
                len(terrain_profile_buffer), terrain_profile_offset,
                len(terrain_profile_buffer), binding_first_constant=1,
                binding_num_constants=1),
        ])
        for slot, texture_format in enumerate((26, 24, 24, 24, 29)):
            selected.append(self._resource(
                3, 8000 + slot, 4, 0x100 + slot, 16, 4224, 16,
                width=1920, height=1080, format_value=texture_format,
                view_format=texture_format,
                copy_phase=MODULE.AFTER_OWNER_PHASE))
        selected.append(self._resource(
            3, 8100, 4, 0x200, 16, 4224, 16,
            width=1920, height=1080, format_value=19, view_format=20,
            copy_phase=MODULE.AFTER_OWNER_PHASE))

        record = bytearray(256)
        for index in range(4):
            struct.pack_into("<f", record, (index * 4 + index) * 4, 1.0)
        vs_prefix = bytes(record) + bytes(104 * 16 - len(record))
        ps_prefix = bytes(record)
        constant_buffers = [
            self._cb(0, 2, 5000, 104, vs_prefix),
            self._cb(4, 2, 5000, 16, ps_prefix),
            self._cb(
                4, MODULE.TERRAIN_PROFILE_CB_SLOT, 6000, 1,
                bytes(12) + struct.pack("<f", 2.0),
                first_constant=1, num_constants=1),
        ]
        resources = [
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
            "unifiedCallOrdinal": 700,
            "presentEpoch": 70,
            "deferredOwner": MODULE.M27_DEFERRED_OWNER,
            "deferredOwnerOccurrence": 1,
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
        resolver = {
            "vertexCountPerInstance": 3,
            "instanceCount": 1,
            "startVertex": 0,
            "startInstance": 0,
            "unifiedCallOrdinal": 710,
            "presentEpoch": 70,
            "deferredOwner": 0,
            "deferredOwnerOccurrence": 0,
            "priorityDefaultDeferred": False,
            "priorityScreenShadowOutput": False,
            "priorityScreenShadowConsumer": False,
            "resourceChain": {"renderTargets": [],
                              "depthTarget": {"objectId": 0}},
        }
        frame = {
            "schema": MODULE.FRAME_SCHEMA,
            "captureLane": MODULE.M27_CAPTURE_LANE,
            "resourcePayloadTiming": "draw-local",
            "resourcePayloadDrawLocal": True,
            "joinedM27SiblingAuthenticated": False,
            "joinedM27SiblingSequenceSlot": 76,
            "joinedM27SiblingPresentEpoch": 0,
            "joinedM27SiblingCallOrdinal": 0,
            "frame": 100,
            "timestampQpc": 123456,
            "draws": 1,
            "observedDraws": 1,
            "drawRecordsTruncated": False,
            "dispatchRecordsTruncated": False,
            "fullscreenResolverRecordsTruncated": False,
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
            "fullscreenResolvers": [resolver],
            "bindingsFile": MODULE.BINDINGS_FILE,
            "bindingsLayoutHash": MODULE.BINDINGS_LAYOUT_HASH,
            "bindingsHeaderSize": MODULE.BINDINGS_HEADER.size,
            "bindingsSelectedRecordSize": MODULE.BINDINGS_RESOURCE.size,
            "bindingsDrawTimingRecordSize": MODULE.BINDINGS_DRAW.size,
            "bindingsResolverTimingRecordSize": MODULE.BINDINGS_RESOLVER.size,
            "resourcesFile": "resources.bin",
            "backbufferFile": None,
        }
        _write_json(self.frame_path, frame)
        self._write_bindings(frame)
        self.rebuild_inventory()

    @staticmethod
    def _resource(kind: int, object_id: int, stage: int, slot: int,
                  byte_size: int, blob_offset: int, blob_bytes: int,
                  **values: int) -> dict[str, object]:
        return {
            "captureKind": kind, "objectId": object_id,
            "viewId": values.get("view_id", 0), "stage": stage,
            "slot": slot, "byteSize": byte_size,
            "resourceKind": values.get(
                "resource_kind", 3 if kind == 3 else 1),
            "width": values.get("width", 0), "height": values.get("height", 0),
            "format": values.get("format_value", 0),
            "viewFormat": values.get("view_format", 0), "subresource": 0,
            "bindingFirstConstant": values.get("binding_first_constant", 0),
            "bindingNumConstants": values.get("binding_num_constants", 0),
            "stride": values.get("stride", 0),
            "byteOffset": values.get("byte_offset", 0),
            "requestedBytes": values.get("requested_bytes", byte_size),
            "blobOffset": blob_offset,
            "blobBytes": blob_bytes, "failure": 0, "hresult": 0,
            "attempted": True, "completed": True,
            "deferredOwner": MODULE.M27_DEFERRED_OWNER,
            "deferredCopyPhase": values.get(
                "copy_phase", MODULE.BEFORE_OWNER_PHASE),
            "deferredOwnerOccurrence": 1,
            "deferredUnifiedCallOrdinal": 700,
            "deferredPresentEpoch": 70,
        }

    def _write_bindings(self, frame: dict[str, object]) -> None:
        payload = bytearray(MODULE.BINDINGS_SCHEMA.encode("ascii"))
        resources = frame["selectedResourceRecords"]
        draws = frame["drawRecords"]
        resolvers = frame["fullscreenResolvers"]
        payload.extend(MODULE.BINDINGS_HEADER.pack(
            MODULE.BINDINGS_LAYOUT_HASH, frame["frame"],
            frame["joinedM27SiblingPresentEpoch"],
            frame["joinedM27SiblingCallOrdinal"],
            MODULE.BINDINGS_HEADER.size, MODULE.BINDINGS_RESOURCE.size,
            MODULE.BINDINGS_DRAW.size, MODULE.BINDINGS_RESOLVER.size,
            frame["joinedM27SiblingSequenceSlot"], len(resources),
            len(draws), len(resolvers), MODULE.M27_CAPTURE_LANE_WIRE, 1, 0,
            MODULE.M27_CAPTURE_LANE_WIRE))
        for row in resources:
            payload.extend(MODULE.BINDINGS_RESOURCE.pack(
                row["objectId"], row["viewId"], row["requestedBytes"],
                row["blobOffset"], row["blobBytes"],
                row["deferredUnifiedCallOrdinal"],
                row["deferredPresentEpoch"], row["hresult"],
                row["deferredOwnerOccurrence"], row["slot"],
                row["captureKind"], row["failure"], row["deferredOwner"],
                row["deferredCopyPhase"], row["stage"], row["resourceKind"],
                int(row["attempted"]), int(row["completed"])))
        for row in draws:
            target = row["pipelineState"]["target"]
            payload.extend(MODULE.BINDINGS_DRAW.pack(
                row["unifiedCallOrdinal"], row["presentEpoch"],
                row["deferredOwnerOccurrence"], row["count"],
                row["instanceCount"], row["start"], row["baseVertex"],
                row["startInstance"], row["deferredOwner"],
                int(row["indexedInstanced"]), target["renderTargetCount"],
                int(target["depthBound"])))
        for row in resolvers:
            chain = row["resourceChain"]
            payload.extend(MODULE.BINDINGS_RESOLVER.pack(
                row["unifiedCallOrdinal"], row["presentEpoch"],
                row["deferredOwnerOccurrence"],
                row["vertexCountPerInstance"], row["instanceCount"],
                row["startVertex"], row["startInstance"],
                row["deferredOwner"], int(row["priorityDefaultDeferred"]),
                int(row["priorityScreenShadowOutput"]),
                int(row["priorityScreenShadowConsumer"]),
                len(chain["renderTargets"]),
                int(bool(chain["depthTarget"]["objectId"])), 0, 0))
        (self.resources_path.parent / MODULE.BINDINGS_FILE).write_bytes(payload)

    @staticmethod
    def _cb(stage: int, slot: int, buffer_id: int, count: int,
            payload: bytes, *, first_constant: int = 123,
            num_constants: int = 4096) -> dict[str, object]:
        return {
            "stage": stage, "slot": slot, "bufferId": buffer_id,
            "firstConstant": first_constant, "numConstants": num_constants,
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
        self._write_bindings(frame)
        self.rebuild_inventory()

    def set_terrain_profile_word(
            self, raw_word: int, *, update_prefix: bool = True,
            update_staged_buffer: bool = True) -> None:
        frame = self.load_frame()
        binding = next(
            row for row in frame["drawRecords"][0]["constantBuffers"]
            if row["stage"] == 4 and
            row["slot"] == MODULE.TERRAIN_PROFILE_CB_SLOT)
        capture = next(
            row for row in frame["selectedResourceRecords"]
            if row["captureKind"] == 2 and row["stage"] == 4 and
            row["slot"] == MODULE.TERRAIN_PROFILE_CB_SLOT)
        if update_prefix:
            prefix = bytearray.fromhex(binding["dataHex"])
            struct.pack_into("<I", prefix,
                             MODULE.TERRAIN_PROFILE_LANE_BYTE_OFFSET,
                             raw_word)
            binding["dataHex"] = prefix.hex()
        if update_staged_buffer:
            payload = bytearray(self.resources_path.read_bytes())
            word_offset = (
                capture["blobOffset"] + binding["firstConstant"] * 16 +
                MODULE.TERRAIN_PROFILE_LANE_BYTE_OFFSET)
            struct.pack_into("<I", payload, word_offset, raw_word)
            self.resources_path.write_bytes(payload)
        self.save_frame(frame)

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
        terrain = result["terrainSubsurfaceSelectedFrame"]
        self.assertEqual(terrain["schema"],
                         MODULE.TERRAIN_SELECTED_FRAME_SCHEMA)
        self.assertEqual(terrain["status"],
                         "draw_local_selected_frame_value_authenticated")
        self.assertEqual(terrain["constantBufferSlot"], 4)
        self.assertEqual(terrain["constantRegister"], 0)
        self.assertEqual(terrain["lane"], "w")
        self.assertEqual(terrain["c0wRawWord"], 0x40000000)
        self.assertEqual(terrain["exactFloat"], 2.0)
        self.assertEqual(terrain["publishedScalar"], 2)
        for field in (
                "resourcesArtifactSha256", "bufferPayloadSha256",
                "selectedRangeSha256", "provenanceSha256"):
            self.assertRegex(terrain[field], r"^[0-9a-f]{64}$")
        self.assertEqual(
            terrain["synchronizedDrawId"],
            result["authentication"]["synchronizedDrawId"])
        serialized = json.dumps(result)
        self.assertNotIn("dataHex", serialized)
        self.assertNotIn('"capturedPacketArrays":', serialized)
        authentication = result["authentication"]
        self.assertEqual(authentication["captureLane"], "priority-m27")
        self.assertTrue(authentication["resourcePayloadDrawLocal"])
        self.assertEqual(authentication["deferredOwner"],
                         MODULE.M27_DEFERRED_OWNER)
        self.assertEqual(authentication["bindingsLayoutHash"],
                         "0xaf996b4b5428cc71")
        self.assertEqual(set(authentication["exactPacketCounters"]),
                         set(MODULE.EXACT_PACKET_COUNTERS))

    def test_bindings_wire_contract_matches_native_fixed_sizes(self) -> None:
        self.assertEqual(MODULE.BINDINGS_LAYOUT_HASH, 0xaf996b4b5428cc71)
        self.assertEqual(
            (MODULE.BINDINGS_HEADER.size, MODULE.BINDINGS_RESOURCE.size,
             MODULE.BINDINGS_DRAW.size, MODULE.BINDINGS_RESOLVER.size),
            (68, 76, 44, 44))

    def test_historical_v2_bindings_sidecar_is_rejected(self) -> None:
        frame = self.fixture.load_frame()
        frame["bindingsFile"] = "bindings.v2.bin"
        v3_path = self.fixture.resources_path.parent / MODULE.BINDINGS_FILE
        v2_path = self.fixture.resources_path.parent / "bindings.v2.bin"
        v2_path.write_bytes(v3_path.read_bytes())
        v3_path.unlink()
        self.fixture.save_frame(frame)
        with self.assertRaisesRegex(MODULE.ConversionError,
                                    "bindings sidecar declaration"):
            MODULE.build_observation(self.fixture.root)

    def test_historical_graphics_frame_v1_is_rejected(self) -> None:
        frame = self.fixture.load_frame()
        frame["schema"] = "endfieldCapture.graphicsFrame.v1"
        self.fixture.save_frame(frame)
        with self.assertRaisesRegex(MODULE.ConversionError, "schema"):
            MODULE.build_observation(self.fixture.root)

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

    def test_graphics_summary_requires_draw_local_publication(self) -> None:
        path = self.fixture.root / "graphics/summary.json"
        summary = json.loads(path.read_text(encoding="utf-8"))
        summary["exactOwnerResourcePayloadTiming"] = "frame-end"
        _write_json(path, summary)
        self.fixture.rebuild_inventory()
        with self.assertRaisesRegex(MODULE.ConversionError,
                                    "draw-local resource-payload proof"):
            MODULE.build_observation(self.fixture.root)

    def test_graphics_summary_requires_every_exact_packet_counter(self) -> None:
        path = self.fixture.root / "graphics/summary.json"
        original = json.loads(path.read_text(encoding="utf-8"))
        for counter in MODULE.EXACT_PACKET_COUNTERS:
            with self.subTest(counter=counter):
                summary = copy.deepcopy(original)
                summary[counter] = 0
                _write_json(path, summary)
                self.fixture.rebuild_inventory()
                with self.assertRaisesRegex(MODULE.ConversionError, counter):
                    MODULE.build_observation(self.fixture.root)
        summary = copy.deepcopy(original)
        summary[MODULE.EXACT_PACKET_COUNTERS[0]] = True
        _write_json(path, summary)
        self.fixture.rebuild_inventory()
        with self.assertRaisesRegex(
                MODULE.ConversionError, MODULE.EXACT_PACKET_COUNTERS[0]):
            MODULE.build_observation(self.fixture.root)

    def test_graphics_summary_requires_exact_publication(self) -> None:
        path = self.fixture.root / "graphics/summary.json"
        summary = json.loads(path.read_text(encoding="utf-8"))
        summary["exactEndminfPublishable"] = False
        _write_json(path, summary)
        self.fixture.rebuild_inventory()
        with self.assertRaisesRegex(MODULE.ConversionError,
                                    "exact Endminf publication"):
            MODULE.build_observation(self.fixture.root)

    def test_graphics_summary_requires_screen_shadow_admission(self) -> None:
        path = self.fixture.root / "graphics/summary.json"
        summary = json.loads(path.read_text(encoding="utf-8"))
        summary["exactScreenShadowAdmissionPassed"] = False
        _write_json(path, summary)
        self.fixture.rebuild_inventory()
        with self.assertRaisesRegex(MODULE.ConversionError,
                                    "screen-shadow admission"):
            MODULE.build_observation(self.fixture.root)

    def test_graphics_summary_requires_screen_shadow_packet_counts(self) -> None:
        path = self.fixture.root / "graphics/summary.json"
        original = json.loads(path.read_text(encoding="utf-8"))
        for counter, expected in MODULE.SCREEN_SHADOW_PACKET_COUNTERS.items():
            with self.subTest(counter=counter):
                summary = copy.deepcopy(original)
                summary[counter] = expected + 1
                _write_json(path, summary)
                self.fixture.rebuild_inventory()
                with self.assertRaisesRegex(MODULE.ConversionError, counter):
                    MODULE.build_observation(self.fixture.root)

    def test_exact_draw_requires_priority_m27_lane(self) -> None:
        frame = self.fixture.load_frame()
        frame["captureLane"] = "regular"
        self.fixture.save_frame(frame)
        with self.assertRaisesRegex(MODULE.ConversionError, "priority-M27"):
            MODULE.build_observation(self.fixture.root)

    def test_frame_requires_draw_local_payload_declaration(self) -> None:
        for field, invalid in (
                ("resourcePayloadTiming", "frame-end"),
                ("resourcePayloadDrawLocal", False)):
            with self.subTest(field=field):
                frame = self.fixture.load_frame()
                frame[field] = invalid
                self.fixture.save_frame(frame)
                with self.assertRaisesRegex(MODULE.ConversionError,
                                            "draw-local payload proof"):
                    MODULE.build_observation(self.fixture.root)
                frame[field] = "draw-local" if field.endswith("Timing") else True
                self.fixture.save_frame(frame)

    def test_draw_owner_and_chronology_must_be_exact(self) -> None:
        for field, invalid in (
                ("deferredOwner", 2),
                ("deferredOwnerOccurrence", 0),
                ("unifiedCallOrdinal", 0),
                ("presentEpoch", 0)):
            with self.subTest(field=field):
                frame = self.fixture.load_frame()
                draw = frame["drawRecords"][0]
                original = draw[field]
                draw[field] = invalid
                self.fixture.save_frame(frame)
                with self.assertRaisesRegex(MODULE.ConversionError,
                                            "owner chronology"):
                    MODULE.build_observation(self.fixture.root)
                draw[field] = original
                self.fixture.save_frame(frame)

    def test_selected_resource_must_be_attempted_and_completed(self) -> None:
        for field, invalid in (
                ("attempted", False), ("completed", False),
                ("failure", 1), ("hresult", 1)):
            with self.subTest(field=field):
                frame = self.fixture.load_frame()
                row = frame["selectedResourceRecords"][0]
                original = row[field]
                row[field] = invalid
                self.fixture.save_frame(frame)
                with self.assertRaisesRegex(MODULE.ConversionError,
                                            "exact owner-local proof"):
                    MODULE.build_observation(self.fixture.root)
                row[field] = original
                self.fixture.save_frame(frame)

    def test_selected_resource_must_match_owner_chronology(self) -> None:
        for field, invalid in (
                ("deferredOwner", 2),
                ("deferredOwnerOccurrence", 2),
                ("deferredUnifiedCallOrdinal", 701),
                ("deferredPresentEpoch", 71)):
            with self.subTest(field=field):
                frame = self.fixture.load_frame()
                row = frame["selectedResourceRecords"][0]
                original = row[field]
                row[field] = invalid
                self.fixture.save_frame(frame)
                with self.assertRaisesRegex(MODULE.ConversionError,
                                            "exact owner-local proof"):
                    MODULE.build_observation(self.fixture.root)
                row[field] = original
                self.fixture.save_frame(frame)

    def test_selected_resources_require_both_owner_phases(self) -> None:
        frame = self.fixture.load_frame()
        for row in frame["selectedResourceRecords"]:
            row["deferredCopyPhase"] = MODULE.BEFORE_OWNER_PHASE
        self.fixture.save_frame(frame)
        with self.assertRaisesRegex(MODULE.ConversionError,
                                    "wrong owner phase"):
            MODULE.build_observation(self.fixture.root)

    def test_every_required_draw_binding_needs_its_owner_local_payload(self) -> None:
        original = self.fixture.load_frame()
        cases = (
            ("vertex", lambda row: row["captureKind"] == 0,
             "IA vertex binding"),
            ("index", lambda row: row["captureKind"] == 1,
             "IA index binding"),
            ("constant", lambda row: row["captureKind"] == 2 and
             row["stage"] == 0, "constant-buffer binding"),
            ("srv", lambda row: row["captureKind"] == 3 and
             row["stage"] == 4 and row["slot"] == 5,
             "shader-resource binding"),
            ("render-target", lambda row: row["slot"] == 0x100,
             "render target 0"),
            ("depth", lambda row: row["slot"] == 0x200,
             "depth target"),
        )
        for label, remove, error in cases:
            with self.subTest(binding=label):
                frame = copy.deepcopy(original)
                frame["selectedResourceRecords"] = [
                    row for row in frame["selectedResourceRecords"]
                    if not remove(row)]
                frame["selectedResources"] = len(
                    frame["selectedResourceRecords"])
                self.fixture.save_frame(frame)
                with self.assertRaisesRegex(MODULE.ConversionError, error):
                    MODULE.build_observation(self.fixture.root)

    def test_bindings_sidecar_header_is_authenticated(self) -> None:
        path = self.fixture.resources_path.parent / MODULE.BINDINGS_FILE
        payload = bytearray(path.read_bytes())
        payload[0] ^= 1
        path.write_bytes(payload)
        self.fixture.rebuild_inventory()
        with self.assertRaisesRegex(MODULE.ConversionError,
                                    "schema/header"):
            MODULE.build_observation(self.fixture.root)

    def test_bindings_sidecar_record_size_matches_metadata(self) -> None:
        path = self.fixture.resources_path.parent / MODULE.BINDINGS_FILE
        payload = bytearray(path.read_bytes())
        struct.pack_into("<I", payload,
                         len(MODULE.BINDINGS_SCHEMA) + 36, 75)
        path.write_bytes(payload)
        self.fixture.rebuild_inventory()
        with self.assertRaisesRegex(MODULE.ConversionError,
                                    "wire layout"):
            MODULE.build_observation(self.fixture.root)

    def test_bindings_sidecar_exact_file_size_is_required(self) -> None:
        path = self.fixture.resources_path.parent / MODULE.BINDINGS_FILE
        path.write_bytes(path.read_bytes() + b"extra")
        self.fixture.rebuild_inventory()
        with self.assertRaisesRegex(MODULE.ConversionError,
                                    "exact file size"):
            MODULE.build_observation(self.fixture.root)

    def test_bindings_record_size_declaration_is_required(self) -> None:
        frame = self.fixture.load_frame()
        frame["bindingsSelectedRecordSize"] = 0
        self.fixture.save_frame(frame)
        with self.assertRaisesRegex(MODULE.ConversionError,
                                    "layout declaration"):
            MODULE.build_observation(self.fixture.root)

    def test_bindings_layout_hash_declaration_is_required(self) -> None:
        frame = self.fixture.load_frame()
        frame["bindingsLayoutHash"] ^= 1
        self.fixture.save_frame(frame)
        with self.assertRaisesRegex(MODULE.ConversionError,
                                    "layout declaration"):
            MODULE.build_observation(self.fixture.root)

    def test_bindings_header_counts_match_json(self) -> None:
        path = self.fixture.resources_path.parent / MODULE.BINDINGS_FILE
        payload = bytearray(path.read_bytes())
        # selected_resource_count is the sixth u32 after the four u64 values.
        count_offset = len(MODULE.BINDINGS_SCHEMA) + 32 + 5 * 4
        struct.pack_into("<I", payload, count_offset, 99)
        path.write_bytes(payload)
        self.fixture.rebuild_inventory()
        with self.assertRaisesRegex(MODULE.ConversionError,
                                    "header disagrees with JSON"):
            MODULE.build_observation(self.fixture.root)

    def test_bindings_resource_record_matches_json(self) -> None:
        path = self.fixture.resources_path.parent / MODULE.BINDINGS_FILE
        payload = bytearray(path.read_bytes())
        resource_offset = (len(MODULE.BINDINGS_SCHEMA) +
                           MODULE.BINDINGS_HEADER.size)
        struct.pack_into("<Q", payload, resource_offset + 40, 701)
        path.write_bytes(payload)
        self.fixture.rebuild_inventory()
        with self.assertRaisesRegex(MODULE.ConversionError,
                                    "resource 0 disagrees with JSON"):
            MODULE.build_observation(self.fixture.root)

    def test_bindings_resource_boolean_flags_are_canonical(self) -> None:
        path = self.fixture.resources_path.parent / MODULE.BINDINGS_FILE
        payload = bytearray(path.read_bytes())
        resource_offset = (len(MODULE.BINDINGS_SCHEMA) +
                           MODULE.BINDINGS_HEADER.size)
        payload[resource_offset + 74] = 2
        path.write_bytes(payload)
        self.fixture.rebuild_inventory()
        with self.assertRaisesRegex(MODULE.ConversionError,
                                    "non-boolean wire flags"):
            MODULE.build_observation(self.fixture.root)

    def test_bindings_draw_timing_matches_json(self) -> None:
        path = self.fixture.resources_path.parent / MODULE.BINDINGS_FILE
        frame = self.fixture.load_frame()
        payload = bytearray(path.read_bytes())
        draw_offset = (len(MODULE.BINDINGS_SCHEMA) +
                       MODULE.BINDINGS_HEADER.size +
                       len(frame["selectedResourceRecords"]) *
                       MODULE.BINDINGS_RESOURCE.size)
        struct.pack_into("<Q", payload, draw_offset, 701)
        path.write_bytes(payload)
        self.fixture.rebuild_inventory()
        with self.assertRaisesRegex(MODULE.ConversionError,
                                    "draw 0 disagrees with JSON"):
            MODULE.build_observation(self.fixture.root)

    def test_bindings_resolver_timing_matches_json(self) -> None:
        path = self.fixture.resources_path.parent / MODULE.BINDINGS_FILE
        frame = self.fixture.load_frame()
        payload = bytearray(path.read_bytes())
        resolver_offset = (len(MODULE.BINDINGS_SCHEMA) +
                           MODULE.BINDINGS_HEADER.size +
                           len(frame["selectedResourceRecords"]) *
                           MODULE.BINDINGS_RESOURCE.size +
                           len(frame["drawRecords"]) *
                           MODULE.BINDINGS_DRAW.size)
        struct.pack_into("<Q", payload, resolver_offset, 711)
        path.write_bytes(payload)
        self.fixture.rebuild_inventory()
        with self.assertRaisesRegex(MODULE.ConversionError,
                                    "resolver 0 disagrees with JSON"):
            MODULE.build_observation(self.fixture.root)

    def test_bindings_resolver_reserved_bytes_are_zero(self) -> None:
        path = self.fixture.resources_path.parent / MODULE.BINDINGS_FILE
        frame = self.fixture.load_frame()
        payload = bytearray(path.read_bytes())
        resolver_offset = (len(MODULE.BINDINGS_SCHEMA) +
                           MODULE.BINDINGS_HEADER.size +
                           len(frame["selectedResourceRecords"]) *
                           MODULE.BINDINGS_RESOURCE.size +
                           len(frame["drawRecords"]) *
                           MODULE.BINDINGS_DRAW.size)
        payload[resolver_offset + 42] = 1
        path.write_bytes(payload)
        self.fixture.rebuild_inventory()
        with self.assertRaisesRegex(MODULE.ConversionError,
                                    "flags/reserved bytes"):
            MODULE.build_observation(self.fixture.root)

    def test_selected_frame_resource_truncation_is_rejected(self) -> None:
        frame = self.fixture.load_frame()
        frame["resourceSelectionTruncated"] = True
        self.fixture.save_frame(frame)
        with self.assertRaisesRegex(MODULE.ConversionError,
                                    "resourceSelectionTruncated=true"):
            MODULE.build_observation(self.fixture.root)

    def test_terrain_profile_requires_exact_pixel_b4_binding(self) -> None:
        original = self.fixture.load_frame()
        for field, invalid in (("stage", 0), ("slot", 5)):
            with self.subTest(field=field):
                frame = copy.deepcopy(original)
                binding = next(
                    row for row in frame["drawRecords"][0]["constantBuffers"]
                    if row["stage"] == 4 and
                    row["slot"] == MODULE.TERRAIN_PROFILE_CB_SLOT)
                capture = next(
                    row for row in frame["selectedResourceRecords"]
                    if row["captureKind"] == 2 and row["stage"] == 4 and
                    row["slot"] == MODULE.TERRAIN_PROFILE_CB_SLOT)
                binding[field] = invalid
                capture[field] = invalid
                self.fixture.save_frame(frame)
                with self.assertRaisesRegex(MODULE.ConversionError,
                                            "PS b4 row"):
                    MODULE.build_observation(self.fixture.root)

    def test_terrain_profile_selected_range_must_match_draw(self) -> None:
        original = self.fixture.load_frame()
        for field, invalid in (
                ("bindingFirstConstant", 0),
                ("bindingNumConstants", 2)):
            with self.subTest(field=field):
                frame = copy.deepcopy(original)
                capture = next(
                    row for row in frame["selectedResourceRecords"]
                    if row["captureKind"] == 2 and row["stage"] == 4 and
                    row["slot"] == MODULE.TERRAIN_PROFILE_CB_SLOT)
                capture[field] = invalid
                self.fixture.save_frame(frame)
                with self.assertRaisesRegex(MODULE.ConversionError,
                                            "selected range disagrees"):
                    MODULE.build_observation(self.fixture.root)

    def test_terrain_profile_range_must_fit_staged_buffer(self) -> None:
        frame = self.fixture.load_frame()
        binding = next(
            row for row in frame["drawRecords"][0]["constantBuffers"]
            if row["stage"] == 4 and
            row["slot"] == MODULE.TERRAIN_PROFILE_CB_SLOT)
        capture = next(
            row for row in frame["selectedResourceRecords"]
            if row["captureKind"] == 2 and row["stage"] == 4 and
            row["slot"] == MODULE.TERRAIN_PROFILE_CB_SLOT)
        binding["firstConstant"] = 4
        capture["bindingFirstConstant"] = 4
        self.fixture.save_frame(frame)
        with self.assertRaisesRegex(MODULE.ConversionError,
                                    "selected range exceeds"):
            MODULE.build_observation(self.fixture.root)

    def test_terrain_profile_incomplete_prefix_is_rejected(self) -> None:
        frame = self.fixture.load_frame()
        binding = next(
            row for row in frame["drawRecords"][0]["constantBuffers"]
            if row["stage"] == 4 and
            row["slot"] == MODULE.TERRAIN_PROFILE_CB_SLOT)
        binding["capturedConstants"] = 0
        binding["dataHex"] = ""
        self.fixture.save_frame(frame)
        with self.assertRaisesRegex(MODULE.ConversionError,
                                    "buffer/range metadata is invalid"):
            MODULE.build_observation(self.fixture.root)

    def test_terrain_profile_incomplete_staged_bytes_are_rejected(self) -> None:
        frame = self.fixture.load_frame()
        capture = next(
            row for row in frame["selectedResourceRecords"]
            if row["captureKind"] == 2 and row["stage"] == 4 and
            row["slot"] == MODULE.TERRAIN_PROFILE_CB_SLOT)
        capture["blobBytes"] -= 1
        self.fixture.save_frame(frame)
        with self.assertRaisesRegex(MODULE.ConversionError,
                                    "exact owner-local proof"):
            MODULE.build_observation(self.fixture.root)

    def test_terrain_profile_owner_timing_must_match_selected_draw(self) -> None:
        original = self.fixture.load_frame()
        cases = (
            ("deferredOwner", 2),
            ("deferredCopyPhase", MODULE.AFTER_OWNER_PHASE),
            ("deferredOwnerOccurrence", 2),
            ("deferredUnifiedCallOrdinal", 701),
            ("deferredPresentEpoch", 71),
        )
        for field, invalid in cases:
            with self.subTest(field=field):
                frame = copy.deepcopy(original)
                capture = next(
                    row for row in frame["selectedResourceRecords"]
                    if row["captureKind"] == 2 and row["stage"] == 4 and
                    row["slot"] == MODULE.TERRAIN_PROFILE_CB_SLOT)
                capture[field] = invalid
                self.fixture.save_frame(frame)
                with self.assertRaisesRegex(
                        MODULE.ConversionError,
                        "exact owner-local proof|wrong owner phase"):
                    MODULE.build_observation(self.fixture.root)

    def test_terrain_profile_scalar_fails_closed(self) -> None:
        cases = (
            (0x7FC00000, "non-finite"),
            (0x7F800000, "non-finite"),
            (struct.unpack("<I", struct.pack("<f", 1.5))[0],
             "non-integral"),
            (struct.unpack("<I", struct.pack("<f", -1.0))[0],
             "outside the source publisher range"),
            (struct.unpack("<I", struct.pack("<f", 16_777_216.0))[0],
             "outside the source publisher range"),
            (0x80000000, "not a canonical exact published uint"),
        )
        for raw_word, error in cases:
            with self.subTest(raw_word=f"0x{raw_word:08x}"):
                self.fixture.set_terrain_profile_word(raw_word)
                with self.assertRaisesRegex(MODULE.ConversionError, error):
                    MODULE.build_observation(self.fixture.root)
                self.fixture.set_terrain_profile_word(0x40000000)

    def test_terrain_profile_prefix_and_staged_word_must_match(self) -> None:
        self.fixture.set_terrain_profile_word(
            0x00000000, update_prefix=False)
        with self.assertRaisesRegex(MODULE.ConversionError,
                                    "draw prefix and staged buffer disagree"):
            MODULE.build_observation(self.fixture.root)

    def test_terrain_profile_artifact_hash_mismatch_is_rejected(self) -> None:
        payload = bytearray(self.fixture.resources_path.read_bytes())
        frame = self.fixture.load_frame()
        capture = next(
            row for row in frame["selectedResourceRecords"]
            if row["captureKind"] == 2 and row["stage"] == 4 and
            row["slot"] == MODULE.TERRAIN_PROFILE_CB_SLOT)
        payload[capture["blobOffset"]] ^= 1
        self.fixture.resources_path.write_bytes(payload)
        with self.assertRaisesRegex(MODULE.ConversionError,
                                    "SHA-256 mismatch"):
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
                                    "lacks exact owner-local proof"):
            MODULE.build_observation(self.fixture.root)

    def test_bound_vertex_t0_wrong_resource_kind_is_rejected(self) -> None:
        frame = self.fixture.load_frame()
        t0 = next(row for row in frame["drawRecords"][0]["resources"]
                  if row.get("objectId") == 2000)
        t0["kind"] = 3
        self.fixture.save_frame(frame)
        with self.assertRaisesRegex(MODULE.ConversionError,
                                    "shader-resource binding"):
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

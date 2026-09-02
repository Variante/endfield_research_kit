import importlib.util
import hashlib
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("verify_endminf_screen_shadow_capture.py")
SPEC = importlib.util.spec_from_file_location("verify_screen_shadow", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class VerifyEndminfScreenShadowCaptureTests(unittest.TestCase):
    WIDTH = 4
    HEIGHT = 2

    def make_frame(self, root: Path, mutate=None):
        frame = root / "graphics" / "frames" / "4200-lane6"
        frame.mkdir(parents=True)
        object_id = 0x123456
        # P1 publishes non-constant scene-shadow R with neutral G. P2 preserves
        # R and adds non-constant character-shadow G. The consumer sees P2.
        p1 = bytes([255, 255, 220, 255, 180, 255, 140, 255,
                    100, 255, 60, 255, 20, 255, 0, 255])
        p2 = bytes([p1[index] if index % 2 == 0 else (index * 13) & 0xFF
                    for index in range(len(p1))])
        blob = p1 + p2 + p2
        expected_bytes = self.WIDTH * self.HEIGHT * 2

        def shader_pair(vertex, pixel):
            return [
                {"stage": 0, "identityHash": vertex},
                {"stage": 4, "identityHash": pixel},
            ]

        def resource_descriptor(slot):
            return {
                "slot": slot, "objectId": object_id,
                "width": self.WIDTH, "height": self.HEIGHT,
                "byteSize": expected_bytes,
                "depthOrArray": 1, "mipLevels": 1,
                "sampleCount": 1, "sampleQuality": 0,
                "format": 48, "viewFormat": 49, "viewDimension": 4,
            }

        def producer(ordinal, occurrence, pixel_shader):
            target = resource_descriptor(0)
            return {
                "instanced": False,
                "priorityScreenShadowOutput": True,
                "priorityScreenShadowConsumer": False,
                "deferredOwner": 5,
                "deferredOwnerOccurrence": occurrence,
                "unifiedCallOrdinal": ordinal,
                "presentEpoch": 77,
                "shaders": shader_pair(
                    MODULE.SCREEN_SHADOW_FULLSCREEN_VS, pixel_shader),
                "resourceChain": {"renderTargets": [target], "psInputs": []},
                "pipelineState": {
                    "valid": True,
                    "renderTargets": [{
                        "slot": 0, "bound": True,
                        "width": self.WIDTH, "height": self.HEIGHT,
                        "textureFormat": 48, "viewFormat": 49,
                        "viewDimension": 4, "sampleCount": 1,
                    }],
                    "samplers": [],
                },
            }

        consumer_input = resource_descriptor(11)
        consumer = {
            "instanced": True,
            "priorityScreenShadowOutput": False,
            "priorityScreenShadowConsumer": True,
            "deferredOwner": 4,
            "deferredOwnerOccurrence": 1,
            "unifiedCallOrdinal": 30,
            "presentEpoch": 77,
            "shaders": shader_pair(
                MODULE.SCREEN_SHADOW_FULLSCREEN_VS,
                MODULE.DEFAULT_DEFERRED_PS),
            "resourceChain": {"renderTargets": [], "psInputs": [consumer_input]},
            "pipelineState": {
                "valid": True,
                "renderTargets": [],
                "samplers": [{"slot": 1, "bound": True}],
            },
        }

        def selected(slot, owner, phase, occurrence, ordinal, offset):
            return {
                "captureKind": 3,
                "resourceKind": 1,
                "objectId": object_id,
                "stage": 4,
                "slot": slot,
                "byteSize": expected_bytes,
                "width": self.WIDTH,
                "height": self.HEIGHT,
                "depthOrArray": 1,
                "mipLevels": 1,
                "sampleCount": 1,
                "sampleQuality": 0,
                "format": 48,
                "viewFormat": 49,
                "viewDimension": 4,
                "subresource": 0,
                "requestedBytes": expected_bytes,
                "blobOffset": offset,
                "blobBytes": expected_bytes,
                "deferredOwner": owner,
                "deferredCopyPhase": phase,
                "deferredOwnerOccurrence": occurrence,
                "deferredUnifiedCallOrdinal": ordinal,
                "deferredPresentEpoch": 77,
                "failure": 0,
                "hresult": 0,
                "attempted": True,
                "completed": True,
            }

        metadata = {
            "schema": "endfieldCapture.graphicsFrame.v2",
            "captureLane": "joined-m27-default",
            "resourcePayloadTiming": "draw-local",
            "resourcePayloadDrawLocal": True,
            "joinedM27SiblingAuthenticated": True,
            "frame": 4200,
            "drawRecordsTruncated": False,
            "dispatchRecordsTruncated": False,
            "resourceSelectionTruncated": False,
            "captureIncomplete": False,
            "captureFailed": False,
            "resourceCaptureIncomplete": False,
            "resourceCaptureFailed": False,
            "droppedEvents": 0,
            "exactEndminfScreenShadowAdmissionRequired": True,
            "exactEndminfScreenShadowAdmissionPassed": True,
            "exactEndminfScreenShadowAdmissionFailure": "none",
            "exactEndminfScreenShadowObjectId": object_id,
            "exactEndminfScreenShadowProducerRecords": 2,
            "exactEndminfScreenShadowConsumerRecords": 1,
            "exactEndminfScreenShadowSelectedRecords": 3,
            "exactEndminfScreenShadowPayloadComparisonAvailable": True,
            "exactEndminfScreenShadowPayloadsEqual": True,
            "fullscreenResolvers": [
                producer(10, 1, MODULE.SCREEN_SHADOW_SCENE_PS),
                producer(20, 2, MODULE.SCREEN_SHADOW_CHARACTER_PS),
                consumer,
            ],
            "drawRecords": [{
                "unifiedCallOrdinal": 5,
                "presentEpoch": 77,
                "count": MODULE.SPHERE_OUTSIDE_INDEX_COUNT,
                "instanceCount": 1,
                "indexedInstanced": True,
                "prioritySphereOutsideGeometry": True,
                "shaders": shader_pair(
                    MODULE.SPHERE_OUTSIDE_VS, MODULE.SPHERE_OUTSIDE_PS),
            }],
            "selectedResourceRecords": [
                selected(0x100, 5, 2, 1, 10, 0),
                selected(0x100, 5, 2, 2, 20, expected_bytes),
                selected(11, 4, 1, 1, 30, expected_bytes * 2),
            ],
            "resourcesFile": "resources.bin",
        }
        if mutate:
            mutate(metadata, bytearray(blob))
        (frame / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
        (frame / "resources.bin").write_bytes(blob)
        return frame

    def make_authenticated_session(self, root: Path, summary: dict):
        (root / "collected").mkdir(parents=True, exist_ok=True)
        (root / "session.json").write_text(json.dumps({
            "schema": "endfieldCapture.session.v1",
            "gameBuild": MODULE.EXPECTED_GAME_BUILD,
            "graphicsProfile": "full",
            "runtimeSha256": "1" * 64,
            "targetSha256": "2" * 64,
        }), encoding="utf-8")
        (root / "runtime.status.json").write_text(json.dumps({
            "schema": "endfieldCapture.runtimeStatus.v1",
        }), encoding="utf-8")
        (root / "collected" / "summary.json").write_text(json.dumps({
            "schema": "endfieldCapture.summary.v1",
            "complete": True,
            "dropped": 0,
            "invalidRecords": 0,
            "writerError": False,
        }), encoding="utf-8")
        (root / "graphics" / "summary.json").write_text(
            json.dumps(summary), encoding="utf-8"
        )
        artifacts = []
        total = 0
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.name == "inventory.json":
                continue
            payload = path.read_bytes()
            artifacts.append({
                "path": path.relative_to(root).as_posix(),
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            })
            total += len(payload)
        (root / "collected" / "inventory.json").write_text(json.dumps({
            "schema": "endfieldCapture.collection.v1",
            "files": len(artifacts),
            "bytes": total,
            "artifacts": artifacts,
        }), encoding="utf-8")

    def test_accepts_exact_three_stage_draw_local_handoff(self):
        with tempfile.TemporaryDirectory() as temporary:
            frame = self.make_frame(Path(temporary))
            artifacts = Path(temporary) / "artifacts"
            report = MODULE.verify_frame(
                frame,
                width=self.WIDTH,
                height=self.HEIGHT,
                artifact_dir=artifacts,
            )
            self.assertTrue(report["valid"], report["failures"])
            self.assertTrue(report["content"]["sceneRPreserved"])
            self.assertTrue(report["content"]["characterGChanged"])
            self.assertTrue(report["content"]["producer2EqualsConsumer"])
            self.assertEqual(len(report["records"]), 3)
            self.assertEqual(len(report["artifacts"]), 8)
            for row in report["artifacts"].values():
                self.assertEqual(Path(row["path"]).read_bytes()[:8],
                                 b"\x89PNG\r\n\x1a\n")
                self.assertEqual(row["rowOrder"], "captured-native-no-flip")

    def test_rejects_old_two_record_admission(self):
        with tempfile.TemporaryDirectory() as temporary:
            def mutate(metadata, _blob):
                metadata["exactEndminfScreenShadowSelectedRecords"] = 2
                metadata["selectedResourceRecords"].pop(0)

            frame = self.make_frame(Path(temporary), mutate)
            report = MODULE.verify_frame(
                frame, width=self.WIDTH, height=self.HEIGHT
            )
            self.assertFalse(report["valid"])
            self.assertTrue(any("expected 3" in row for row in report["failures"]))
            self.assertTrue(any("producer-after" in row for row in report["failures"]))

    def test_rejects_frame_end_payload(self):
        with tempfile.TemporaryDirectory() as temporary:
            def mutate(metadata, _blob):
                metadata["resourcePayloadTiming"] = "frame-end"
                metadata["resourcePayloadDrawLocal"] = False

            frame = self.make_frame(Path(temporary), mutate)
            report = MODULE.verify_frame(
                frame, width=self.WIDTH, height=self.HEIGHT
            )
            self.assertFalse(report["valid"])
            self.assertIn(
                "resource payload timing is not draw-local", report["failures"]
            )

    def test_rejects_shader_program_or_order_drift(self):
        mutations = (
            lambda metadata: metadata["fullscreenResolvers"][0]["shaders"][1]
                .update(identityHash=0xDEADBEEF),
            lambda metadata: (
                metadata["fullscreenResolvers"][0].update(
                    shaders=metadata["fullscreenResolvers"][1]["shaders"]),
                metadata["fullscreenResolvers"][1].update(
                    shaders=metadata["fullscreenResolvers"][0]["shaders"]),
            ),
            lambda metadata: metadata["fullscreenResolvers"][2]["shaders"][1]
                .update(identityHash=0xDEADBEEF),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation), \
                    tempfile.TemporaryDirectory() as temporary:
                def mutate(metadata, _blob):
                    mutation(metadata)

                frame = self.make_frame(Path(temporary), mutate)
                report = MODULE.verify_frame(
                    frame, width=self.WIDTH, height=self.HEIGHT
                )
                self.assertFalse(report["valid"])
                self.assertTrue(any(
                    "shader pair is not exact" in failure
                    for failure in report["failures"]
                ), report["failures"])

    def test_rejects_missing_or_late_sphereoutside_carrier(self):
        mutations = (
            lambda metadata: metadata.update(drawRecords=[]),
            lambda metadata: metadata["drawRecords"][0].update(
                unifiedCallOrdinal=10),
            lambda metadata: metadata["drawRecords"][0]["shaders"][1].update(
                identityHash=0xDEADBEEF),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation), \
                    tempfile.TemporaryDirectory() as temporary:
                def mutate(metadata, _blob):
                    mutation(metadata)

                frame = self.make_frame(Path(temporary), mutate)
                report = MODULE.verify_frame(
                    frame, width=self.WIDTH, height=self.HEIGHT
                )
                self.assertFalse(report["valid"])
                self.assertTrue(any(
                    "SphereOutside" in failure
                    for failure in report["failures"]
                ), report["failures"])

    def test_rejects_resource_or_pipeline_descriptor_drift(self):
        mutations = (
            lambda metadata: metadata["fullscreenResolvers"][0]
                ["resourceChain"]["renderTargets"][0].update(depthOrArray=2),
            lambda metadata: metadata["fullscreenResolvers"][0]
                ["pipelineState"]["renderTargets"][0].update(sampleCount=4),
            lambda metadata: metadata["selectedResourceRecords"][2].update(
                mipLevels=2),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation), \
                    tempfile.TemporaryDirectory() as temporary:
                def mutate(metadata, _blob):
                    mutation(metadata)

                frame = self.make_frame(Path(temporary), mutate)
                report = MODULE.verify_frame(
                    frame, width=self.WIDTH, height=self.HEIGHT
                )
                self.assertFalse(report["valid"])
                self.assertTrue(any(
                    "descriptor" in failure or "pipeline target" in failure
                    for failure in report["failures"]
                ), report["failures"])

    def test_rejects_producer2_consumer_byte_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            frame = self.make_frame(root)
            blob_path = frame / "resources.bin"
            blob = bytearray(blob_path.read_bytes())
            blob[-1] ^= 0x7F
            blob_path.write_bytes(blob)
            report = MODULE.verify_frame(
                frame, width=self.WIDTH, height=self.HEIGHT
            )
            self.assertFalse(report["valid"])
            self.assertIn(
                "content gate failed: producer2EqualsConsumer", report["failures"]
            )

    def test_rejects_aliased_draw_local_snapshot_ranges(self):
        with tempfile.TemporaryDirectory() as temporary:
            def mutate(metadata, _blob):
                producer2 = metadata["selectedResourceRecords"][1]
                consumer = metadata["selectedResourceRecords"][2]
                consumer["blobOffset"] = producer2["blobOffset"]

            frame = self.make_frame(Path(temporary), mutate)
            report = MODULE.verify_frame(
                frame, width=self.WIDTH, height=self.HEIGHT
            )
            self.assertFalse(report["valid"])
            self.assertIn(
                "selected payload ranges overlap; draw-local snapshots are not "
                "independently stored",
                report["failures"],
            )

    def test_rejects_character_channel_that_never_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            frame = self.make_frame(Path(temporary))
            blob_path = frame / "resources.bin"
            blob = bytearray(blob_path.read_bytes())
            size = self.WIDTH * self.HEIGHT * 2
            blob[size:size * 2] = blob[:size]
            blob[size * 2:size * 3] = blob[:size]
            blob_path.write_bytes(blob)
            report = MODULE.verify_frame(
                frame, width=self.WIDTH, height=self.HEIGHT
            )
            self.assertFalse(report["valid"])
            self.assertIn(
                "content gate failed: characterGChanged", report["failures"]
            )

    def test_session_requires_complete_publishable_summary(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_frame(root)
            self.make_authenticated_session(root, {
                "complete": False,
                "automaticCollectionReady": True,
                "exactEndminfPublishable": True,
                "exactScreenShadowAdmissionPassed": True,
                "exactScreenShadowAdmissionRequiredPackets": 1,
                "exactScreenShadowAdmissionPassedPackets": 1,
                "exactScreenShadowAdmissionFailedPackets": 0,
            })
            report = MODULE.verify_session(root)
            self.assertEqual(report["status"], "rejected")
            self.assertIn("graphics summary is not complete", report["failures"])

    def test_build_report_preserves_authentication_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_frame(root)
            report = MODULE.build_report(root)
            self.assertEqual(report["status"], "rejected")
            self.assertEqual(report["framesScanned"], 0)
            self.assertIn("inventory.json", report["failures"][0])


if __name__ == "__main__":
    unittest.main()

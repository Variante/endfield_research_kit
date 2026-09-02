import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
MODULE_PATH = TOOLS / "build_endminf_screen_shadow_capture_artifact.py"
SPEC = importlib.util.spec_from_file_location("build_screen_shadow_artifact", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class BuildEndminfScreenShadowCaptureArtifactTests(unittest.TestCase):
    WIDTH = 4
    HEIGHT = 2
    BYTES = WIDTH * HEIGHT * 2

    def setUp(self):
        self.constant_patches = [
            mock.patch.object(MODULE, "WIDTH", self.WIDTH),
            mock.patch.object(MODULE, "HEIGHT", self.HEIGHT),
            mock.patch.object(MODULE, "EXPECTED_BYTES", self.BYTES),
        ]
        for patcher in self.constant_patches:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.constant_patches):
            patcher.stop()

    @staticmethod
    def _sha(payload: bytes) -> str:
        return hashlib.sha256(payload).hexdigest()

    def make_fixture(self, root: Path, *, consumer_matches=True):
        capture = root / "capture"
        frame = capture / "graphics" / "frames" / "4200-lane6"
        frame.mkdir(parents=True)
        (capture / "collected").mkdir()

        p1 = bytes([
            255, 255, 220, 255, 180, 255, 140, 255,
            100, 255, 60, 255, 20, 255, 0, 255,
        ])
        p2 = bytes([
            p1[index] if index % 2 == 0 else (index * 13) & 0xFF
            for index in range(len(p1))
        ])
        consumer = p2 if consumer_matches else p2[:-1] + bytes([p2[-1] ^ 0x7F])
        resource_blob = p1 + p2 + consumer
        (frame / "resources.bin").write_bytes(resource_blob)

        def selected(slot, owner, phase, occurrence, ordinal, offset):
            return {
                "captureKind": 3,
                "resourceKind": 1,
                "objectId": 0x123456,
                "stage": 4,
                "slot": slot,
                "byteSize": self.BYTES,
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
                "requestedBytes": self.BYTES,
                "blobOffset": offset,
                "blobBytes": self.BYTES,
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

        selected_rows = [
            selected(0x100, 5, 2, 1, 10, 0),
            selected(0x100, 5, 2, 2, 20, self.BYTES),
            selected(11, 4, 1, 1, 30, self.BYTES * 2),
        ]
        metadata = {
            "schema": MODULE.VERIFIER.SCHEMA,
            "resourcesFile": "resources.bin",
            "selectedResourceRecords": selected_rows,
        }
        (frame / "metadata.json").write_text(
            json.dumps(metadata), encoding="utf-8"
        )
        runtime_sha = "1" * 64
        target_sha = "2" * 64
        session = {
            "schema": "endfieldCapture.session.v1",
            "gameBuild": MODULE.VERIFIER.EXPECTED_GAME_BUILD,
            "runtimeSha256": runtime_sha,
            "targetSha256": target_sha,
        }
        (capture / "session.json").write_text(
            json.dumps(session), encoding="utf-8"
        )

        artifacts = []
        for path in (frame / "metadata.json", frame / "resources.bin",
                     capture / "session.json"):
            payload = path.read_bytes()
            artifacts.append({
                "path": path.relative_to(capture).as_posix(),
                "bytes": len(payload),
                "sha256": self._sha(payload),
            })
        inventory = {
            "schema": "endfieldCapture.collection.v1",
            "files": len(artifacts),
            "bytes": sum(row["bytes"] for row in artifacts),
            "artifacts": artifacts,
        }
        inventory_path = capture / "collected" / "inventory.json"
        inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
        inventory_sha = self._sha(inventory_path.read_bytes())

        names = ("producer1After", "producer2After", "consumerT11Before")
        payloads = (p1, p2, consumer)
        records = []
        for name, payload, selected_row in zip(names, payloads, selected_rows):
            records.append({
                "name": name,
                "objectId": selected_row["objectId"],
                "slot": selected_row["slot"],
                "deferredOwner": selected_row["deferredOwner"],
                "deferredCopyPhase": selected_row["deferredCopyPhase"],
                "deferredOwnerOccurrence": selected_row["deferredOwnerOccurrence"],
                "deferredUnifiedCallOrdinal":
                    selected_row["deferredUnifiedCallOrdinal"],
                "deferredPresentEpoch": selected_row["deferredPresentEpoch"],
                "blobOffset": selected_row["blobOffset"],
                "blobBytes": selected_row["blobBytes"],
                "sha256": self._sha(payload),
                "channels": MODULE._summaries(payload),
            })
        report = {
            "schema": "endfield.endminf-screen-shadow-capture.v1",
            "status": "validated",
            "failures": [],
            "authentication": {
                "gameBuild": MODULE.VERIFIER.EXPECTED_GAME_BUILD,
                "runtimeSha256": runtime_sha,
                "targetSha256": target_sha,
                "inventorySha256": inventory_sha,
            },
            "candidateCount": 1,
            "validCandidateCount": 1,
            "candidates": [{
                "valid": True,
                "failures": [],
                "frameDirectory": str(frame.resolve()),
                "content": {
                    "producer1ToProducer2Changed": True,
                    "sceneRPreserved": True,
                    "characterGChanged": True,
                    "producer2EqualsConsumer": True,
                },
                "records": records,
            }],
        }
        return capture, frame, report, p2

    def build(self, capture: Path, output: Path, report: dict):
        with mock.patch.object(MODULE.VERIFIER, "build_report", return_value=report):
            return MODULE.build_artifact(capture, output)

    def test_emits_deterministic_raw_payload_and_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            capture, _frame, report, p2 = self.make_fixture(root)
            output = root / "artifact"
            first = self.build(capture, output, report)
            first_json = (output / MODULE.MANIFEST_NAME).read_bytes()
            first_payload = (output / MODULE.PAYLOAD_NAME).read_bytes()
            second = self.build(capture, output, report)

            self.assertEqual(first, second)
            self.assertEqual(first_payload, p2)
            self.assertEqual(
                (output / MODULE.MANIFEST_NAME).read_bytes(), first_json
            )
            self.assertEqual(first["schema"], MODULE.SCHEMA)
            self.assertEqual(first["texture"], {
                "width": self.WIDTH,
                "height": self.HEIGHT,
                "graphicsFormat": "R8G8_UNorm",
                "bytesPerPixel": 2,
                "nativeRowOrder": "captured-native-no-flip",
            })
            self.assertFalse(first["presentationAuthorized"])
            self.assertFalse(first["proceduralProducerCertified"])
            self.assertTrue(first["diagnosticReplayOnly"])
            self.assertEqual(first["payload"]["sha256"], self._sha(p2))
            self.assertEqual(first["presentEpoch"], 77)
            self.assertEqual(
                [first["records"][name]["callOrdinal"] for name in (
                    "producer1After", "producer2After", "consumerT11Before")],
                [10, 20, 30],
            )

    def test_requires_one_fully_validated_candidate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            capture, _frame, report, _p2 = self.make_fixture(root)
            for mutation in (
                lambda value: value.update(status="rejected"),
                lambda value: value.update(candidateCount=2),
                lambda value: value["candidates"][0]["content"].update(
                    producer2EqualsConsumer=False),
            ):
                changed = json.loads(json.dumps(report))
                mutation(changed)
                with self.subTest(report=changed):
                    with self.assertRaises(MODULE.ArtifactError):
                        self.build(capture, root / "output", changed)

    def test_rejects_identity_and_schema_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            capture, _frame, report, _p2 = self.make_fixture(root)
            mutations = (
                lambda value: value.update(schema="wrong"),
                lambda value: value["authentication"].update(gameBuild="wrong"),
                lambda value: value["authentication"].update(runtimeSha256="bad"),
                lambda value: value["authentication"].update(inventorySha256="0" * 64),
            )
            for mutation in mutations:
                changed = json.loads(json.dumps(report))
                mutation(changed)
                with self.subTest(report=changed):
                    with self.assertRaises(MODULE.ArtifactError):
                        self.build(capture, root / "output", changed)

    def test_rejects_descriptor_size_and_chronology_drift(self):
        mutations = (
            lambda metadata: metadata["selectedResourceRecords"][1].update(width=5),
            lambda metadata: metadata["selectedResourceRecords"][1].update(format=28),
            lambda metadata: metadata["selectedResourceRecords"][1].update(byteSize=15),
            lambda metadata: metadata["selectedResourceRecords"][1].update(
                deferredUnifiedCallOrdinal=31),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                capture, frame, report, _p2 = self.make_fixture(root)
                metadata_path = frame / "metadata.json"
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                mutation(metadata)
                metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
                # Re-authenticate the deliberately malformed metadata so the
                # builder reaches its independent row validation.
                inventory_path = capture / "collected" / "inventory.json"
                inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
                row = next(item for item in inventory["artifacts"]
                           if item["path"].endswith("metadata.json"))
                row["bytes"] = metadata_path.stat().st_size
                row["sha256"] = self._sha(metadata_path.read_bytes())
                inventory["bytes"] = sum(item["bytes"] for item in inventory["artifacts"])
                inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
                report["authentication"]["inventorySha256"] = self._sha(
                    inventory_path.read_bytes()
                )
                with self.assertRaises(MODULE.ArtifactError):
                    self.build(capture, root / "output", report)

    def test_rejects_producer_consumer_ownership_drift(self):
        mutations = (
            lambda metadata: metadata["selectedResourceRecords"][0].update(
                deferredOwner=4),
            lambda metadata: metadata["selectedResourceRecords"][1].update(
                deferredOwnerOccurrence=3),
            lambda metadata: metadata["selectedResourceRecords"][2].update(slot=10),
            lambda metadata: metadata["selectedResourceRecords"][2].update(
                objectId=0xABCDEF),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                capture, frame, report, _p2 = self.make_fixture(root)
                metadata_path = frame / "metadata.json"
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                mutation(metadata)
                changed = metadata["selectedResourceRecords"]
                report_row = report["candidates"][0]["records"]
                for destination, source in zip(report_row, changed):
                    for key in (
                        "objectId", "slot", "deferredOwner", "deferredCopyPhase",
                        "deferredOwnerOccurrence", "deferredUnifiedCallOrdinal",
                        "deferredPresentEpoch", "blobOffset", "blobBytes",
                    ):
                        destination[key] = source[key]
                metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
                inventory_path = capture / "collected" / "inventory.json"
                inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
                row = next(item for item in inventory["artifacts"]
                           if item["path"].endswith("metadata.json"))
                row["bytes"] = metadata_path.stat().st_size
                row["sha256"] = self._sha(metadata_path.read_bytes())
                inventory["bytes"] = sum(item["bytes"] for item in inventory["artifacts"])
                inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
                report["authentication"]["inventorySha256"] = self._sha(
                    inventory_path.read_bytes()
                )
                with self.assertRaises(MODULE.ArtifactError):
                    self.build(capture, root / "output", report)

    def test_rejects_output_inside_authenticated_capture(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            capture, _frame, report, _p2 = self.make_fixture(root)
            output = capture / "derived-artifact"
            with self.assertRaisesRegex(
                    MODULE.ArtifactError,
                    "outside the authenticated capture"):
                self.build(capture, output, report)
            self.assertFalse(output.exists())

    def test_rejects_raw_p2_consumer_mismatch_even_if_report_claims_valid(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            capture, _frame, report, _p2 = self.make_fixture(
                root, consumer_matches=False
            )
            with self.assertRaisesRegex(
                    MODULE.ArtifactError,
                    "producer-2 and consumer-before t11 bytes differ"):
                self.build(capture, root / "output", report)

    def test_rejects_reported_frame_path_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            capture, _frame, report, _p2 = self.make_fixture(root)
            outside = root / "outside"
            outside.mkdir()
            report["candidates"][0]["frameDirectory"] = str(outside.resolve())
            with self.assertRaisesRegex(MODULE.ArtifactError, "escapes"):
                self.build(capture, root / "output", report)


if __name__ == "__main__":
    unittest.main()

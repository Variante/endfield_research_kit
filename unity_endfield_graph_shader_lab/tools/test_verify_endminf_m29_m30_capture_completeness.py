from __future__ import annotations

import importlib.util
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "verify_endminf_m29_m30_capture_completeness.py"
SPEC = importlib.util.spec_from_file_location(
    "verify_endminf_m29_m30_capture_completeness", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def b3(owner: dict[str, object], c4: tuple[float, ...] | None = None) -> str:
    values = [0.0] * (5 * 4)
    values[4:8] = owner["c1"]
    values[16:20] = owner["c4"] if c4 is None else c4
    return struct.pack("<20f", *values).hex()


def draw(owner_name: str, c4: tuple[float, ...] | None = None) -> dict[str, object]:
    owner = MODULE.OWNERS[owner_name]
    resources = [
        {"objectId": 100, "kind": 1, "stage": 0, "slot": 0, "byteSize": 64},
        {"objectId": 101, "kind": 1, "stage": 0, "slot": 0, "byteSize": 12},
        {"objectId": 200, "kind": 2, "stage": 4, "slot": 0, "byteSize": 16},
    ]
    return {
        "count": min(owner["counts"]),
        "shaders": [
            {"stage": 0, "identityHash": owner["vertex"]},
            {"stage": 4, "identityHash": owner["pixel"]},
        ],
        "constantBuffers": [{
            "stage": 4, "slot": 3, "rangeValid": True,
            "metadataValid": True, "dataHex": b3(owner, c4),
        }],
        "resources": resources,
    }


def metadata(truncated: bool = False, include_resources: bool = True) -> dict[str, object]:
    selected = [
        {"objectId": object_id, "stage": stage, "slot": slot,
         "completed": True, "blobBytes": size}
        for object_id, stage, slot, size in (
            (100, 0, 0, 64), (101, 0, 0, 12), (200, 4, 0, 16))
    ]
    rows = [draw("M29"), draw("M30"), draw("M31")]
    if not include_resources:
        rows[0]["resources"] = []
    return {
        "frame": 1,
        "resourceSelectionTruncated": truncated,
        "selectedResourceRecords": selected,
        "drawRecords": rows,
    }


class CaptureCompletenessTests(unittest.TestCase):
    def build(self, payload: dict[str, object]) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as temporary:
            capture = Path(temporary)
            frame = capture / "graphics/frames/1"
            frame.mkdir(parents=True)
            (frame / "metadata.json").write_text(
                json.dumps(payload), encoding="utf-8")
            return MODULE.build_report(capture)

    def test_complete_owner_resources_pass(self) -> None:
        report = self.build(metadata())
        self.assertEqual(report["status"], "validated_exact_owner_resource_closure")
        self.assertEqual(report["owners"]["M29"]["packetCount"], 1)
        self.assertEqual(report["owners"]["M30"]["packetCount"], 1)
        self.assertEqual(report["owners"]["M31"]["packetCount"], 1)

    def test_m31_known_tint_fingerprints_are_classified_separately(self) -> None:
        payload = metadata()
        payload["drawRecords"].append(
            draw("M31", MODULE.OWNERS["M31"]["alternateC4"][0]))
        report = self.build(payload)
        self.assertEqual(report["owners"]["M30"]["packetCount"], 1)
        self.assertEqual(report["owners"]["M31"]["packetCount"], 2)

    def test_m30_packet_cannot_satisfy_m31_gate(self) -> None:
        payload = metadata()
        payload["drawRecords"] = payload["drawRecords"][:2]
        with self.assertRaisesRegex(
                MODULE.VerificationError,
                "capture contains no exact M31 owner packets"):
            self.build(payload)

    def test_m31_unknown_tint_fails_closed(self) -> None:
        payload = metadata()
        payload["drawRecords"][2] = draw("M31", (0.5, 0.5, 0.5, 1.0))
        with self.assertRaisesRegex(
                MODULE.VerificationError,
                "capture contains no exact M31 owner packets"):
            self.build(payload)

    def test_unrelated_global_truncation_is_diagnostic_after_owner_closure(self) -> None:
        report = self.build(metadata(truncated=True))
        self.assertTrue(report["globalResourceSelectionTruncated"])
        self.assertEqual(report["resourceSelectionTruncatedFrames"], [1])

    def test_missing_owner_payload_still_fails_when_globally_truncated(self) -> None:
        payload = metadata(truncated=True)
        payload["selectedResourceRecords"] = [
            row for row in payload["selectedResourceRecords"]
            if row["objectId"] != 200
        ]
        with self.assertRaisesRegex(
                MODULE.VerificationError,
                r'M29 frame 1 draw 0.*"slot": 0, "stage": 4'):
            self.build(payload)

    def test_missing_draw_ownership_fails_closed(self) -> None:
        with self.assertRaisesRegex(MODULE.VerificationError, "owner resources"):
            self.build(metadata(include_resources=False))


if __name__ == "__main__":
    unittest.main()

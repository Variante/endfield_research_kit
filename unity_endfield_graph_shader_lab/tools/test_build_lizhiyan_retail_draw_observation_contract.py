#!/usr/bin/env python3
"""Focused tests for the Li Zhiyan retail draw/video observation importer."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("build_lizhiyan_retail_draw_observation_contract.py")
SPEC = importlib.util.spec_from_file_location("lizhiyan_draw_observation", SCRIPT)
assert SPEC and SPEC.loader
C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(C)


VIDEO = {
    "sha256": C.VIDEO_SHA256,
    "timeBase": "1/1000",
    "oracleIntervalPts": [38000, 47000],
}


def event(stage: str, seq: int, **extra: object) -> dict[str, object]:
    row: dict[str, object] = {
        "eventId": f"event-{seq}",
        "seq": seq,
        "monotonicNs": seq * 1000,
        "threadId": 7,
        "sessionId": "session-positive",
        "frameId": "frame-42",
        "presentIntervalId": "present-42",
        "stage": stage,
    }
    row.update(extra)
    return row


def positive_trace(*, omit: str | None = None, state_hash: str = "11" * 32) -> dict[str, object]:
    common_resource = {"resourceStableId": "resource-generation-3"}
    rows = [
        event("renderer_list_register", 1, **common_resource),
        event("opcode_4e_consumer", 2, **common_resource),
        event("survivor_record_append", 3, recordHex=("00" * 32 + "01000000" + "00" * 28), **common_resource),
        event("resource_publication", 4, **common_resource),
        event("opcode_2748_decode", 5, recordingEpoch="epoch-9", frontContext="front-a", derivedStateSha256=state_hash, **common_resource),
        event("descriptor_update", 6, recordingEpoch="epoch-9", frontContext="front-a", derivedStateSha256=state_hash, descriptorSet="set-5", **common_resource),
        event("opcode_2731_execute", 7, recordingEpoch="epoch-9", frontContext="front-a"),
        event("descriptor_bind", 8, descriptorSet="set-5", commandBuffer="cmd-2"),
        event("draw", 9, commandBuffer="cmd-2", drawKind="vkCmdDrawIndexedIndirect"),
        event("queue_submit", 10, commandBuffer="cmd-2"),
        event("present_pixel", 11, videoSha256=C.VIDEO_SHA256, pts=40000, timeBase="1/1000", actorIsolation="lizhiyan_only", visibleAfterDofTeal=True, decodedFrameSha256="22" * 32),
    ]
    if omit:
        rows = [row for row in rows if row["stage"] != omit]
    return {"role": "lizhiyan_positive", "targetSignature": "li-teal-resource", "events": rows}


def negative_trace(*, matching: bool = False) -> dict[str, object]:
    row = event("present_pixel", 1)
    row["sessionId"] = "session-negative"
    if matching:
        row["targetSignature"] = "li-teal-resource"
    return {
        "role": "wulfa",
        "captureProfile": "same_build_camera_and_settings",
        "events": [row],
    }


class LiZhiyanRetailDrawObservationTests(unittest.TestCase):
    def test_complete_synthetic_join_and_control_admit(self) -> None:
        positive = C.validate_positive_trace(positive_trace(), VIDEO)
        negative = C.validate_negative_trace(negative_trace(), positive)
        self.assertTrue(positive["complete"])
        self.assertTrue(negative["complete"])
        self.assertEqual(positive["descriptorSet"], "set-5")
        self.assertEqual(positive["commandBuffer"], "cmd-2")

    def test_missing_stage_is_pending_not_absence(self) -> None:
        result = C.validate_positive_trace(positive_trace(omit="descriptor_update"), VIDEO)
        self.assertFalse(result["complete"])
        self.assertEqual(result["blockedBy"], ["missing stage: descriptor_update"])

    def test_cross_recorder_join_fails_closed(self) -> None:
        trace = positive_trace()
        next(row for row in trace["events"] if row["stage"] == "descriptor_update")["recordingEpoch"] = "epoch-other"
        with self.assertRaisesRegex(C.ObservationContractError, "positive_recordingEpoch_join"):
            C.validate_positive_trace(trace, VIDEO)

    def test_descriptor_state_hash_must_match(self) -> None:
        trace = positive_trace()
        next(row for row in trace["events"] if row["stage"] == "descriptor_update")["derivedStateSha256"] = "33" * 32
        with self.assertRaisesRegex(C.ObservationContractError, "positive_derivedStateSha256_join"):
            C.validate_positive_trace(trace, VIDEO)

    def test_pointer_like_identity_cannot_replace_stable_resource_id(self) -> None:
        trace = positive_trace()
        for row in trace["events"][:6]:
            row.pop("resourceStableId", None)
            row["resourcePointer"] = "0x1234"
        with self.assertRaisesRegex(C.ObservationContractError, "positive_resource_resourceStableId_join"):
            C.validate_positive_trace(trace, VIDEO)

    def test_record_must_be_exactly_64_bytes(self) -> None:
        trace = positive_trace()
        next(row for row in trace["events"] if row["stage"] == "survivor_record_append")["recordHex"] = "00" * 63
        with self.assertRaisesRegex(C.ObservationContractError, "positive_record_hex"):
            C.validate_positive_trace(trace, VIDEO)

    def test_pts_uses_integer_time_base_not_frame_division(self) -> None:
        trace = positive_trace()
        pixel = next(row for row in trace["events"] if row["stage"] == "present_pixel")
        pixel["pts"] = 666
        with self.assertRaisesRegex(C.ObservationContractError, "positive_pixel_pts"):
            C.validate_positive_trace(trace, VIDEO)

    def test_negative_control_rejects_matching_target_signature(self) -> None:
        positive = C.validate_positive_trace(positive_trace(), VIDEO)
        with self.assertRaisesRegex(C.ObservationContractError, "negative_target_signature_absent"):
            C.validate_negative_trace(negative_trace(matching=True), positive)

    def test_trace_source_hash_pin_drift_rejects(self) -> None:
        document = positive_trace()
        document.update({
            "schema": C.TRACE_SCHEMA,
            "sourcePins": {
                "abiContractSha256": "00" * 32,
                "unityPlayerSha256": C.UNITY_PLAYER_SHA256,
                "gameAssemblySha256": C.GAME_ASSEMBLY_SHA256,
                "metadataSha256": C.METADATA_SHA256,
            },
        })
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trace.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaisesRegex(C.ObservationContractError, "trace_pin_abiContractSha256"):
                C._load_trace(path)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_protocol_registry_audit as audit  # noqa: E402


class ProtocolRegistryAuditTests(unittest.TestCase):
    def test_compressed_signed_integer_decoding(self):
        self.assertEqual(audit.read_compressed_int32(bytes([0x00]), 0), (0, 1))
        self.assertEqual(audit.read_compressed_int32(bytes([0x02]), 0), (1, 1))
        self.assertEqual(audit.read_compressed_int32(bytes([0x01]), 0), (-1, 1))
        self.assertEqual(audit.read_compressed_int32(bytes([0x80, 0x80]), 0), (64, 2))

    def test_field_names_join_constants_to_protobuf_storage(self):
        self.assertEqual(audit.normalized_field_name("SceneNumIdFieldNumber"), "scenenumid")
        self.assertEqual(audit.normalized_field_name("sceneNumId_"), "scenenumid")
        self.assertEqual(audit.normalized_field_name("TaskIdFieldNumber"), "taskid")
        self.assertEqual(audit.normalized_field_name("taskId_"), "taskid")

    def test_relevant_task_schemas_reference_separately_proven_native_paths(self):
        task_rows = [
            row for row in audit.RELEVANT_MESSAGES
            if "SCRIPT_TASK" in row["type"] or row["type"].endswith("SCRIPT_SET_DONE")
        ]
        self.assertEqual(len(task_rows), 5)
        self.assertTrue(all(
            row["classification"] in {
                "native_sender_proven_elsewhere",
                "native_handler_proven_elsewhere",
            }
            for row in task_rows
        ))
        self.assertTrue(all("MISSION" not in row["type"] for row in task_rows))

    def test_runtime_manifest_exposes_hash_locked_task_paths(self):
        paths = audit.load_native_task_paths(audit.RUNTIME_HOOK_MANIFEST)
        self.assertEqual(paths["gameBuild"], "endfield-2026-07-11-gameassembly-0c557367")
        self.assertEqual(len(paths["manifestSha256"]), 64)
        self.assertEqual(len(paths["hooks"]), 7)
        self.assertEqual(paths["hooks"]["sendProgress"]["messageId"], 105)
        self.assertEqual(paths["hooks"]["progressUpdate"]["messageId"], 815)
        self.assertEqual(
            paths["hooks"]["conditionCompletionChanged"]["fieldOffsets"]["isCompleted"],
            "0x50",
        )
        self.assertEqual(
            paths["hooks"]["conditionCompletionChanged"]["messageId"],
            815,
        )

    def test_message_125_is_native_proven_while_sibling_schemas_stay_unconfirmed(self):
        rows = {row["expectedId"]: row for row in audit.RELEVANT_MESSAGES}
        self.assertEqual(rows[125]["classification"], "native_handler_proven")
        self.assertEqual(
            audit.NATIVE_MISSION_EVENT_PATHS[125]["token"],
            "0x060052a6",
        )
        self.assertEqual(
            audit.NATIVE_MISSION_EVENT_PATHS[125]["fieldOffsets"],
            {"missionId": "0x18", "eventName": "0x20"},
        )
        self.assertEqual(
            audit.NATIVE_MISSION_EVENT_PATHS[125]["consumerSurface"],
            "keyed_global_event_bus",
        )
        self.assertEqual(
            audit.NATIVE_MISSION_EVENT_PATHS[125]["keyGenerator"]["symbol"],
            "Beyond.KeyGenerator`2.GetKey",
        )
        self.assertIn(
            "unproven",
            audit.NATIVE_MISSION_EVENT_PATHS[125]["directCallCensus"][
                "typedPairingStatus"
            ],
        )
        for message_id in (126, 316, 317):
            self.assertIn("schema_only", rows[message_id]["classification"])
            self.assertNotIn(message_id, audit.NATIVE_MISSION_EVENT_PATHS)

    def test_message_57_preserves_ctx_token_as_non_owning_event_context(self):
        evidence = audit.NATIVE_LEVEL_SCRIPT_EVENT_PATHS[57]
        self.assertEqual(evidence["token"], "0x06004dbf")
        self.assertEqual(evidence["fieldOffsets"]["ctxToken"], "0x30")
        self.assertIn("opaque event context", evidence["ctxTokenFinding"])
        self.assertIn(
            "LevelEventManager.RaiseScriptEvent",
            evidence["eventParamsPath"]["dispatch"],
        )


if __name__ == "__main__":
    unittest.main()

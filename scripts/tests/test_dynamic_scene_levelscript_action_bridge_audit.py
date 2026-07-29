from __future__ import annotations

from pathlib import Path
import struct
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.story_recovery.build_dynamic_scene_levelscript_action_bridge_audit import (
    classify_local_trigger_volume_context,
    decode_decoration_action,
    shared_control_paths,
)


PARAM_TAIL = struct.pack("<ii", -1, 0) + struct.pack("<i", -1)


def constant_u64(value: int) -> bytes:
    return b"\x04" + struct.pack("<Q", value) + PARAM_TAIL


def constant_bool(value: bool) -> bytes:
    return b"\x04" + bytes([int(value)]) + PARAM_TAIL


class DynamicSceneLevelScriptActionBridgeAuditTests(unittest.TestCase):
    def test_exact_show_new_action_is_fully_consumed(self) -> None:
        payload = constant_u64(10100282001) + constant_bool(False)
        record = {
            "start": 0,
            "payloadStart": 0,
            "unionTag": 0x0485,
            "serializedMemberCount": 10,
            "localId": 6,
            "nextId": 7,
        }
        decoded, status = decode_decoration_action(
            payload,
            record,
            next_start=len(payload),
            action_map_role="actionList#2 linked",
        )
        self.assertEqual(status, "exact")
        self.assertEqual(decoded["actionName"], "ShowSceneDecorationNew")
        self.assertEqual(
            decoded["targetDynamicEntityLogicId"],
            "10100282001",
        )
        self.assertFalse(decoded["visible"])
        self.assertTrue(decoded["payloadFullyConsumed"])

    def test_trailing_runtime_shape_fails_closed(self) -> None:
        payload = constant_u64(42) + constant_bool(True) + struct.pack("<i", 1)
        record = {
            "start": 0,
            "payloadStart": 0,
            "unionTag": 0x0486,
            "serializedMemberCount": 10,
        }
        decoded, status = decode_decoration_action(
            payload,
            record,
            next_start=len(payload),
            action_map_role="actionList#1 root",
        )
        self.assertIsNone(decoded)
        self.assertEqual(status, "unclassified_trailing_bytes")

    def test_shared_path_reports_story_before_decoration(self) -> None:
        common = {
            "headerLocalId": 4,
            "headerName": "ScriptEvent_OnLeaderEnterTriggerVolume",
            "headerOpcode": "0x1234/0x01",
            "headerUnionTag": "0x1234",
        }
        shared = shared_control_paths(
            [{**common, "pathLocalIds": [5], "path": [{"localId": 5}]}],
            [
                {
                    **common,
                    "pathLocalIds": [5, 6],
                    "path": [{"localId": 5}, {"localId": 6}],
                }
            ],
        )
        self.assertEqual(len(shared), 1)
        self.assertEqual(
            shared[0]["relation"],
            "decoration_follows_story_on_same_path",
        )

    def test_different_headers_do_not_create_shared_context(self) -> None:
        self.assertEqual(
            shared_control_paths(
                [
                    {
                        "headerLocalId": 1,
                        "headerName": "HeaderA",
                        "headerOpcode": "0x1",
                        "headerUnionTag": "0x1",
                        "pathLocalIds": [5],
                    }
                ],
                [
                    {
                        "headerLocalId": 2,
                        "headerName": "HeaderB",
                        "headerOpcode": "0x2",
                        "headerUnionTag": "0x2",
                        "pathLocalIds": [5, 6],
                    }
                ],
            ),
            [],
        )

    def test_local_trigger_volume_is_exact_but_not_a_foreign_key(self) -> None:
        context = classify_local_trigger_volume_context(
            {
                "serializedMemberCount": 27,
                "scriptIdVerified": True,
                "triggerVolumesStatus": "present",
                "triggerVolumesOffsetHex": "0x2c7",
                "triggerVolumesDetails": {
                    "parseStatus": "decoded",
                    "volumes": [
                        {
                            "slotId": 80001,
                            "triggerVolumeType": "Leader",
                            "memberCount": 8,
                            "shapeList": {
                                "shapes": [
                                    {
                                        "shapeType": "Sphere",
                                        "radius": 59.0,
                                    }
                                ]
                            },
                        }
                    ],
                },
            },
            [80001],
        )
        self.assertEqual(
            context["status"],
            "exact_local_levelscript_trigger_volume_without_foreign_identity",
        )
        self.assertEqual(context["matchedSlotIds"], [80001])
        self.assertFalse(context["foreignKeyBridgeFound"])
        self.assertEqual(context["schema"]["baseDeclaredFieldCount"], 8)
        self.assertEqual(context["schema"]["leaderDeclaredFieldCount"], 0)

    def test_missing_local_trigger_volume_fails_closed(self) -> None:
        context = classify_local_trigger_volume_context(
            {
                "triggerVolumesStatus": "present",
                "triggerVolumesDetails": {
                    "parseStatus": "decoded",
                    "volumes": [{"slotId": 80002}],
                },
            },
            [80001],
        )
        self.assertEqual(
            context["status"],
            "unresolved_local_levelscript_trigger_volume",
        )
        self.assertEqual(context["missingSlotIds"], [80001])


if __name__ == "__main__":
    unittest.main()

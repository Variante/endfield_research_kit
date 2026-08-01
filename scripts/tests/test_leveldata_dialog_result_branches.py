import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.common import read_json
from scripts.story_builder.levelscript_binary import decode_levelscript_record_payload
from scripts.story_recovery import build_source_story_gap_queue as gap_queue


ROOT = Path(__file__).resolve().parents[2]


class LevelScriptDynamicDialogDecoderTests(unittest.TestCase):
    def test_decodes_start_dialog_getter_and_string_property_path(self):
        action_payload = (
            b"\x04"
            + (-1).to_bytes(4, "little", signed=True)
            + (141).to_bytes(4, "little", signed=True)
            + (-1).to_bytes(4, "little", signed=True)
            + (-1).to_bytes(4, "little", signed=True)
        )
        action = decode_levelscript_record_payload(
            b"\0" * 32 + action_payload,
            {
                "start": 0,
                "payloadStart": 32,
                "layout": "fa",
                "code": 0x049E,
                "kind": 0x0F,
                "unionTag": 0x049E,
                "serializedMemberCount": 15,
            },
            next_start=32 + len(action_payload),
            action_map_role="actionList#1 root",
        )
        self.assertEqual(
            action["startDialogAction"]["dialogGetterLocalId"],
            141,
        )

        path = b"succeed_dialog"
        getter_payload = (
            b"\x04"
            + (-1).to_bytes(4, "little", signed=True)
            + (-1).to_bytes(4, "little", signed=True)
            + (200).to_bytes(4, "little", signed=True)
            + len(path).to_bytes(4, "little", signed=True)
            + path
        )
        getter = decode_levelscript_record_payload(
            b"\0" * 28 + getter_payload,
            {
                "start": 0,
                "payloadStart": 32,
                "layout": "fa",
                "code": 0x01A5,
                "kind": 0x08,
                "unionTag": 0x01A5,
                "serializedMemberCount": 8,
            },
            next_start=28 + len(getter_payload),
            action_map_role="getterList#1",
        )
        self.assertEqual(getter["getterString"]["path"], "succeed_dialog")

    def test_string_getter_rejects_trailing_bytes(self):
        path = b"failed_dialog"
        payload = (
            b"\x04"
            + (-1).to_bytes(4, "little", signed=True) * 2
            + (200).to_bytes(4, "little", signed=True)
            + len(path).to_bytes(4, "little", signed=True)
            + path
            + b"\0"
        )
        decoded = decode_levelscript_record_payload(
            b"\0" * 28 + payload,
            {
                "start": 0,
                "payloadStart": 32,
                "layout": "fa",
                "code": 0x01A5,
                "kind": 0x08,
            },
            next_start=28 + len(payload),
            action_map_role="getterList#1",
        )
        self.assertNotIn("getterString", decoded)


class Gm01m24DialogBranchValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.partial_report = read_json(
            ROOT / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        cls.table_root = (
            ROOT / "export_full/structured/StreamingAssets/Table"
        )

    def test_current_binary_branch_context_validates(self):
        index, status = gap_queue.build_offline_exhaustion_index(
            self.partial_report,
            self.table_root,
        )
        self.assertEqual(status["status"], "active")
        context = index["dlg_gm01m24_2"]["levelDataDialogBranchContext"]
        self.assertEqual(context["storyPropertyPath"], "succeed_dialog")
        self.assertEqual(
            [(row["resultValue"], row["dialogId"])
             for row in context["resultBranches"]],
            [(8, "dlg_gm01m24_2"), (9, "dlg_gm01m24_3")],
        )

    def test_changed_getter_path_fails_with_actionable_diagnostic(self):
        declaration = copy.deepcopy(
            gap_queue.OFFLINE_EXHAUSTION_LEVELDATA_DIALOG_BRANCH_CONTEXTS[
                "gm01m24"
            ]
        )
        source = ROOT / declaration["levelScriptFile"]
        data = source.read_bytes().replace(
            b"succeed_dialog",
            b"succeed_dialoX",
            1,
        )
        self.assertNotEqual(data, source.read_bytes())
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "3500190001.json"
            changed.write_bytes(data)
            declaration["levelScriptFile"] = str(changed)
            declaration["levelScriptSha256"] = hashlib.sha256(data).hexdigest().upper()
            with patch.dict(
                gap_queue.OFFLINE_EXHAUSTION_LEVELDATA_DIALOG_BRANCH_CONTEXTS,
                {"gm01m24": declaration},
            ):
                index, status = gap_queue.build_offline_exhaustion_index(
                    self.partial_report,
                    self.table_root,
                )
        self.assertEqual(index, {})
        self.assertEqual(
            status["status"],
            "inactive_leveldata_dialog_branch_validation_failed",
        )
        diagnostic = status["validatorDiagnostics"][0]
        self.assertEqual(
            diagnostic["validator"],
            "offlineLevelDataDialogBranchContext",
        )
        self.assertEqual(diagnostic["mission"], "gm01m24")
        self.assertEqual(
            diagnostic["gate"],
            "exactPropertiesSwitchAndStartDialogControlPaths",
        )
        self.assertEqual(len(diagnostic["sourcePaths"]), 2)
        self.assertIn("expected", diagnostic)
        self.assertIn("actual", diagnostic)


if __name__ == "__main__":
    unittest.main()

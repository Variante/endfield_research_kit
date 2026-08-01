import copy
import base64
import hashlib
import json
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


class LevelDataDialogBranchValidatorTests(unittest.TestCase):
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
        gm01m25 = index["dlg_gm01m25_2"]["levelDataDialogBranchContext"]
        self.assertEqual(gm01m25["storyPropertyPath"], "succeed_dialog")
        self.assertEqual(
            [(row["resultValue"], row["dialogId"])
             for row in gm01m25["resultBranches"]],
            [(8, "dlg_gm01m25_2"), (9, "dlg_gm01m25_3")],
        )
        self.assertEqual(
            index["dlg_gm01m25_2"]["dialogTreeTerminalOptionRoutes"],
            [{
                "optionGroup": 1,
                "routes": [{
                    "optionId": "option_dlg_gm01m25_2_1_001",
                    "targetKind": "finish",
                    "finishId": 1,
                    "finishIdSerialized": True,
                }, {
                    "optionId": "option_dlg_gm01m25_2_1_002",
                    "targetKind": "finish",
                    "finishId": None,
                    "finishIdSerialized": False,
                }],
            }],
        )
        gm01m26 = index["dlg_gm01m26_2"]["levelDataDialogBranchContext"]
        self.assertEqual(gm01m26["storyPropertyPath"], "succeed_dialog")
        self.assertEqual(gm01m26["dictionaryScriptIds"], [
            "3400010000", "3400010001", "3400010002", "3400010003",
            "3400010004", "3400010009", "3400010010", "3400010011",
            "3400010012", "3400010013", "3400010017", "3400010018",
            "3400010019", "3400010020", "3400010021", "3400010027",
            "3400010028", "3400010029", "3400010031", "3400010032",
            "3400010033", "3400010044",
        ])
        self.assertEqual(
            [(row["resultValue"], row["dialogId"])
             for row in gm01m26["resultBranches"]],
            [(8, "dlg_gm01m26_2"), (9, "dlg_gm01m26_3")],
        )
        self.assertEqual(
            index["dlg_gm01m26_1"]["dialogTreeBranchGroups"][0]
            ["targetLineIds"],
            [
                "dlg_gm01m26_1_014",
                "dlg_gm01m26_1_017",
                "dlg_gm01m26_1_009",
            ],
        )
        self.assertEqual(
            index["dlg_gm01m26_5"]["dialogTreeBranchGroups"][0]
            ["targetLineIds"],
            [
                "dlg_gm01m26_5_014",
                "dlg_gm01m26_5_006",
                "dlg_gm01m26_5_008",
            ],
        )
        gm01m5 = index["dlg_gm01m5_1"]
        self.assertEqual(
            gm01m5["evidenceKind"],
            "dialog_text_table_only_with_empty_levelscript_host",
        )
        self.assertEqual(gm01m5["optionIds"], [
            "option_dlg_gm01m5_1_0d5_001",
            "option_dlg_gm01m5_1_0d7_001",
            "option_dlg_gm01m5_1_0d8_001",
            "option_dlg_gm01m5_1_1_001",
        ])
        empty_host = gm01m5["emptyLevelScriptContext"]
        self.assertEqual(empty_host["scriptId"], "2100100004")
        self.assertEqual(empty_host["dictionaryScriptIds"], ["2100100004"])
        self.assertEqual(empty_host["propertyCount"], 0)
        self.assertEqual(empty_host["uidRecordCount"], 0)
        self.assertEqual(empty_host["actionListRecordCount"], 0)
        self.assertEqual(empty_host["taskMapCount"], 0)
        self.assertEqual(
            index["radio_gm01m5_1"]["evidenceKind"],
            "radio_definition_with_empty_levelscript_host",
        )
        self.assertEqual(
            index["radio_gm01m5_1"]["missingAudioIds"],
            ["au_radio_gm01m5_1_001", "au_radio_gm01m5_1_002"],
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

    def test_nonempty_gm01m5_action_list_fails_with_exact_diagnostic(self):
        declaration = copy.deepcopy(
            gap_queue.OFFLINE_EXHAUSTION_EMPTY_LEVELSCRIPT_CONTEXTS[
                "gm01m5"
            ]
        )
        source = ROOT / declaration["levelScriptFile"]
        data = bytearray(source.read_bytes())
        self.assertEqual(data[3], 0)
        data[3] = 1
        changed_data = bytes(data)
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "2100100004.json"
            changed.write_bytes(changed_data)
            declaration["levelScriptFile"] = str(changed)
            declaration["levelScriptSha256"] = hashlib.sha256(
                changed_data
            ).hexdigest().upper()
            with patch.dict(
                gap_queue.OFFLINE_EXHAUSTION_EMPTY_LEVELSCRIPT_CONTEXTS,
                {"gm01m5": declaration},
            ):
                index, status = gap_queue.build_offline_exhaustion_index(
                    self.partial_report,
                    self.table_root,
                )
        self.assertEqual(index, {})
        self.assertEqual(
            status["status"],
            "inactive_empty_levelscript_context_validation_failed",
        )
        diagnostic = status["validatorDiagnostics"][0]
        self.assertEqual(
            diagnostic["validator"],
            "offlineEmptyLevelScriptContext",
        )
        self.assertEqual(diagnostic["mission"], "gm01m5")
        self.assertEqual(
            diagnostic["gate"],
            "exactSinglePropertylessHostAndNoActionRecords",
        )
        self.assertEqual(
            diagnostic["expected"]["actionListRecordCount"],
            0,
        )
        self.assertEqual(
            diagnostic["actual"]["actionListRecordCount"],
            1,
        )
        self.assertEqual(len(diagnostic["sourcePaths"]), 2)

    def test_changed_terminal_finish_id_fails_with_exact_route_diagnostic(self):
        declaration = copy.deepcopy(
            gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
                "dlg_gm01m25_2"
            ]
        )
        source = (
            ROOT
            / "export_full/recovered/AnimeStudio-cli/StreamingAssets/"
            / "json_by_type/TextAsset"
            / declaration["filename"]
        )
        outer = read_json(source, {})
        tree = json.loads(
            base64.b64decode(outer["m_Script"]).decode("utf-8-sig")
        )
        finish = next(
            node for node in tree["nodes"]
            if node.get("$type") == "Beyond.Gameplay.DialogTreeFinishNode"
            and node.get("finishId") == 1
        )
        finish["finishId"] = 2
        outer["m_Script"] = base64.b64encode(
            json.dumps(tree, ensure_ascii=False).encode("utf-8")
        ).decode("ascii")
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / source.name
            changed.write_text(
                json.dumps(outer, ensure_ascii=False),
                encoding="utf-8",
            )
            declaration["filename"] = str(changed)
            declaration["sha256"] = hashlib.sha256(
                changed.read_bytes()
            ).hexdigest().upper()
            with patch.dict(
                gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS,
                {"dlg_gm01m25_2": declaration},
            ):
                index, status = gap_queue.build_offline_exhaustion_index(
                    self.partial_report,
                    self.table_root,
                )
        self.assertEqual(index, {})
        self.assertEqual(
            status["status"],
            "inactive_dialog_definition_validation_failed",
        )
        diagnostic = status["validatorDiagnostics"][0]
        self.assertEqual(diagnostic["validator"], "offlineDialogDefinition")
        self.assertEqual(diagnostic["storyKey"], "dlg_gm01m25_2")
        self.assertEqual(
            diagnostic["expected"]["terminalOptionRoutes"][0]
            ["routes"][0]["finishId"],
            1,
        )
        self.assertEqual(
            diagnostic["actual"]["terminalOptionRoutes"][0]
            ["routes"][0]["finishId"],
            2,
        )


if __name__ == "__main__":
    unittest.main()

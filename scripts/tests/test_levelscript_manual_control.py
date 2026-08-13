from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.story_builder import levelscript_manual_control as manual_index
from scripts.story_builder.codecs.levelscript.manual_control import (
    decode_manual_levelscript_control,
)


class LevelScriptManualControlTests(unittest.TestCase):
    @staticmethod
    def self_contract(*, status: str = "validated") -> dict:
        return {
            "classification": "current_context_manual_start_self_target",
            "discoveryPattern": {"serializedObjectInputs": []},
            "serializedOperandContract": {
                "levelIdParamSource": 1000,
                "scriptIdParamSource": 1002,
            },
            "validation": {"status": status},
        }

    def test_default_operands_preserve_both_numeric_param_sources(self) -> None:
        payload = (
            b"\x04"
            + b"\xff" * 8
            + (1000).to_bytes(4, "little", signed=True)
            + b"\xff" * 4
            + b"\x04"
            + b"\x00" * 16
            + b"\xff" * 4
            + (1002).to_bytes(4, "little", signed=True)
            + b"\xff" * 4
        )

        decoded = decode_manual_levelscript_control(
            payload,
            (0x0308, 0x0A),
        )

        self.assertEqual(
            decoded["parameterSources"],
            {"levelId": 1000, "scriptId": 1002},
        )
        self.assertEqual(
            decoded["payloadShape"],
            "manual-levelscript-default-operands",
        )

    def test_unknown_payload_does_not_invent_param_sources(self) -> None:
        decoded = decode_manual_levelscript_control(
            bytes(range(46)),
            (0x0308, 0x0A),
        )

        self.assertNotIn("parameterSources", decoded)

    def test_wrong_member_count_fails_closed(self) -> None:
        self.assertEqual(
            {},
            decode_manual_levelscript_control(bytes(46), (0x0308, 0x09)),
        )

    def test_typed_index_preserves_literal_and_validated_self_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            levelscript_root = Path(raw_root)
            level_dir = levelscript_root / "map_fixture"
            level_dir.mkdir()
            source = level_dir / "1001.json"
            source.write_bytes((1002).to_bytes(4, "little") + bytes(60))
            records = [
                {"start": 0, "payloadStart": 0, "code": 0x12BE, "kind": 0, "localId": 7},
                {"start": 4, "payloadStart": 4, "code": 0x0308, "kind": 0x0A, "localId": 8},
            ]
            original_load = manual_index._load_levelscript_binding_data
            original_header = manual_index.decode_levelscript_action_map_header
            original_decode = manual_index.decode_levelscript_record_payload
            try:
                manual_index._load_levelscript_binding_data = lambda *_args: {
                    "files": [{"file": str(source), "records": records}]
                }
                manual_index.decode_levelscript_action_map_header = lambda _data: {
                    "status": "present",
                    "recordCount": 2,
                }

                def decode(_data, record, *, next_start=None):
                    if record["localId"] == 7:
                        return {"actionHeader": {"nextId": 8}}
                    return {
                        "manualControl": {
                            "payloadShape": "fixture",
                            "parameterSources": {"levelId": 1000, "scriptId": 1002},
                        }
                    }

                manual_index.decode_levelscript_record_payload = decode
                indexed = manual_index.build_manual_control_index(
                    levelscript_root=levelscript_root,
                    self_control_contract=self.self_contract(),
                )
            finally:
                manual_index._load_levelscript_binding_data = original_load
                manual_index.decode_levelscript_action_map_header = original_header
                manual_index.decode_levelscript_record_payload = original_decode

        self.assertEqual(indexed.validation["status"], "validated")
        self.assertEqual(indexed.summary["validatedSelfTargets"], 1)
        control = indexed.targets[("map_fixture", "1001")][0]
        self.assertEqual(control["targetResolution"], "current_context_self")
        self.assertEqual(control["headerLinkedEvent"]["localId"], 7)

    def test_unvalidated_native_contract_fails_closed(self) -> None:
        self.assertIsNone(
            manual_index._self_contract_operands(
                self.self_contract(status="validation_failed")
            )
        )

    def test_missing_levelscript_root_fails_closed(self) -> None:
        indexed = manual_index.build_manual_control_index(
            levelscript_root=Path("missing/manual/control/fixture"),
            self_control_contract=self.self_contract(),
        )
        self.assertEqual(indexed.targets, {})
        self.assertEqual(indexed.validation["status"], "validation_failed")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import build_dialog_finish_branch_audit as audit
except ModuleNotFoundError:
    from scripts.story_recovery import build_dialog_finish_branch_audit as audit


def text_asset(nodes: list[dict], connections: list[dict], name: str = "dlg_fixture") -> dict:
    payload = {
        "type": "Beyond.Gameplay.DialogTree",
        "nodes": nodes,
        "connections": connections,
    }
    return {
        "m_Name": name,
        "m_Script": base64.b64encode(
            json.dumps(payload).encode("utf-8")
        ).decode("ascii"),
    }


def option_node(option_ids: list[str]) -> dict:
    return {
        "$id": "option",
        "$type": "Beyond.Gameplay.DialogTreeOptionNode, Gameplay.Beyond",
        "_normalOptions": [
            {"_optionId": value, "index": ordinal}
            for ordinal, value in enumerate(option_ids)
        ],
        "_hasExOption": False,
    }


def finish_node(node_id: str, finish_id: int | None, *, serialized: bool = True) -> dict:
    node = {
        "$id": node_id,
        "$type": "Beyond.Gameplay.DialogTreeFinishNode, Gameplay.Beyond",
    }
    if serialized:
        node["finishId"] = finish_id
    return node


def connection(target: str) -> dict:
    return {
        "$type": "Beyond.Gameplay.DialogTreeConnection",
        "_sourceNode": {"$ref": "option"},
        "_targetNode": {"$ref": target},
    }


class DialogTreeRouteTests(unittest.TestCase):
    def test_recovers_serialized_connection_index_finish_routes(self) -> None:
        outer = text_asset(
            [
                option_node(["option_fixture_1_001", "option_fixture_1_002"]),
                finish_node("finish1", 1),
                finish_node("finish2", 2),
            ],
            [connection("finish1"), connection("finish2")],
        )
        rows, rejected = audit.decode_dialog_tree_finish_routes(
            outer, source_file="fixture.json"
        )
        self.assertEqual(rejected, [])
        self.assertEqual(
            [(row["optionId"], row["finishId"]) for row in rows],
            [("option_fixture_1_001", 1), ("option_fixture_1_002", 2)],
        )

    def test_missing_finish_id_fails_closed_without_runtime_contract(self) -> None:
        outer = text_asset(
            [option_node(["option_fixture_1_001"]), finish_node("finish", None, serialized=False)],
            [connection("finish")],
        )
        rows, rejected = audit.decode_dialog_tree_finish_routes(
            outer, source_file="fixture.json"
        )
        self.assertEqual(rows, [])
        self.assertEqual(rejected[0]["gate"], "serializedFinishId")
        self.assertEqual(
            rejected[0]["actual"], "missing_without_validated_default"
        )

    def test_missing_finish_id_uses_validated_managed_int_default(self) -> None:
        outer = text_asset(
            [option_node(["option_fixture_1_001"]), finish_node("finish", None, serialized=False)],
            [connection("finish")],
        )
        rows, rejected = audit.decode_dialog_tree_finish_routes(
            outer,
            source_file="fixture.json",
            runtime_defaults={
                "status": "validated",
                "managedValueTypeDefaults": {"System.Int32": 0},
            },
        )
        self.assertEqual(rejected, [])
        self.assertEqual(rows[0]["finishId"], 0)
        self.assertEqual(rows[0]["finishIdSource"], "runtime_default")

    def test_explicit_finish_id_wins_over_runtime_default(self) -> None:
        outer = text_asset(
            [option_node(["option_fixture_1_001"]), finish_node("finish", 7)],
            [connection("finish")],
        )
        rows, rejected = audit.decode_dialog_tree_finish_routes(
            outer,
            source_file="fixture.json",
            runtime_defaults={
                "status": "validated",
                "managedValueTypeDefaults": {"System.Int32": 0},
            },
        )
        self.assertEqual(rejected, [])
        self.assertEqual(rows[0]["finishId"], 7)
        self.assertEqual(rows[0]["finishIdSource"], "serialized_explicit")

    def test_invalid_explicit_finish_id_is_not_replaced_by_default(self) -> None:
        outer = text_asset(
            [option_node(["option_fixture_1_001"]), finish_node("finish", True)],
            [connection("finish")],
        )
        rows, rejected = audit.decode_dialog_tree_finish_routes(
            outer,
            source_file="fixture.json",
            runtime_defaults={
                "status": "validated",
                "managedValueTypeDefaults": {"System.Int32": 0},
            },
        )
        self.assertEqual(rows, [])
        self.assertEqual(rejected[0]["actual"], "invalid_serialized_value")

    def test_out_of_bounds_route_fails_closed_without_discarding_valid_route(self) -> None:
        outer = text_asset(
            [
                option_node(["option_fixture_1_001", "option_fixture_1_002"]),
                finish_node("finish", 1),
            ],
            [connection("finish")],
        )
        rows, rejected = audit.decode_dialog_tree_finish_routes(
            outer, source_file="fixture.json"
        )
        self.assertEqual(
            [(row["optionId"], row["finishId"]) for row in rows],
            [("option_fixture_1_001", 1)],
        )
        self.assertEqual(rejected[0]["gate"], "normalOptionConnectionIndexBounds")
        self.assertEqual(rejected[0]["expected"]["maximumExclusive"], 1)
        self.assertEqual(rejected[0]["actual"], 1)

    def test_extra_option_edge_does_not_break_physical_index_mapping(self) -> None:
        option = option_node(["option_fixture_1_001", "option_fixture_1_002"])
        option["_normalOptions"][1]["index"] = 2
        option["_hasExOption"] = True
        extra = {
            "$id": "extra",
            "$type": "Beyond.Gameplay.DialogTreeExOptionNode, Gameplay.Beyond",
        }
        outer = text_asset(
            [option, finish_node("finish1", 1), extra, finish_node("finish2", 2)],
            [connection("finish1"), connection("extra"), connection("finish2")],
        )
        coverage: dict = {}
        rows, rejected = audit.decode_dialog_tree_finish_routes(
            outer,
            source_file="fixture.json",
            route_coverage=coverage,
        )
        self.assertEqual(rejected, [])
        self.assertEqual(
            [(row["optionId"], row["finishId"]) for row in rows],
            [("option_fixture_1_001", 1), ("option_fixture_1_002", 2)],
        )
        self.assertEqual(coverage["counts"]["extraOptionNodes"], 1)
        self.assertEqual(coverage["counts"]["connectionCountMismatchNodes"], 1)

    def test_non_object_option_row_fails_closed(self) -> None:
        node = option_node(["option_fixture_1_001"])
        node["_normalOptions"].append("invalid")
        outer = text_asset(
            [node, finish_node("finish", 1)],
            [connection("finish")],
        )
        rows, rejected = audit.decode_dialog_tree_finish_routes(
            outer, source_file="fixture.json"
        )
        self.assertEqual(rows, [])
        self.assertEqual(rejected[0]["gate"], "uniqueOptionIds")


class TimelineRouteTests(unittest.TestCase):
    def test_duplicate_clips_agree_and_are_collapsed(self) -> None:
        option = {
            "id": "option_fixture_1_001",
            "changeFinishNum": 1,
            "targetFinishNum": 3,
            "assetTrack": "asset.json",
        }
        rows, rejected = audit.decode_timeline_finish_routes(
            {
                "dlg_fixture": {
                    "dialogKey": "dlg_fixture",
                    "timeline": "dlgtl_fixture",
                    "sourceRoots": ["root.json"],
                    "options": [option, dict(option)],
                }
            }
        )
        self.assertEqual(rejected, [])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["finishId"], 3)
        self.assertEqual(rows[0]["serializedOccurrenceCount"], 2)

    def test_conflicting_duplicate_clips_are_rejected(self) -> None:
        rows, rejected = audit.decode_timeline_finish_routes(
            {
                "dlg_fixture": {
                    "dialogKey": "dlg_fixture",
                    "options": [
                        {
                            "id": "option_fixture_1_001",
                            "changeFinishNum": 1,
                            "targetFinishNum": 1,
                        },
                        {
                            "id": "option_fixture_1_001",
                            "changeFinishNum": 1,
                            "targetFinishNum": 2,
                        },
                    ],
                }
            }
        )
        self.assertEqual(rows, [])
        self.assertEqual(rejected[0]["gate"], "timelineOptionScopeAgreement")
        self.assertEqual(rejected[0]["finishIds"], [1, 2])


class ProducerScopeTests(unittest.TestCase):
    def test_reused_option_id_in_distinct_nodes_is_not_a_conflict(self) -> None:
        rows = [
            {
                "dialogId": "dlg_fixture",
                "optionId": "option_shared",
                "finishId": finish_id,
                "finishIdSource": "serialized_explicit",
                "producerFamily": "dialog_tree_finish_node",
                "producerScope": {
                    "kind": "dialog_tree_option_node",
                    "key": f"node:{node_id}:option:0",
                },
                "sourceFiles": [],
            }
            for node_id, finish_id in (("6", 0), ("15", 3))
        ]
        accepted, conflicts = audit._normalize_producers(rows)
        self.assertEqual(len(accepted), 2)
        self.assertEqual(conflicts, [])
        reused = audit._collect_reused_option_scopes(accepted)
        self.assertEqual(len(reused), 1)
        self.assertEqual(reused[0]["finishIds"], [0, 3])

    def test_conflicting_finish_within_one_runtime_scope_fails_closed(self) -> None:
        rows = [
            {
                "dialogId": "dlg_fixture",
                "optionId": "option_shared",
                "finishId": finish_id,
                "finishIdSource": "serialized_explicit",
                "producerFamily": "dialog_tree_finish_node",
                "producerScope": {
                    "kind": "dialog_tree_option_node",
                    "key": "node:6:option:0",
                },
                "sourceFiles": [],
            }
            for finish_id in (0, 3)
        ]
        accepted, conflicts = audit._normalize_producers(rows)
        self.assertEqual(accepted, [])
        self.assertEqual(conflicts[0]["gate"], "producerScopeAgreement")


class NativeContractTests(unittest.TestCase):
    class FakePe:
        def __init__(self, _path: Path, body: bytes) -> None:
            self.body = body

        def bytes_at_va(self, _va: int, size: int) -> bytes:
            return self.body[:size]

    def test_native_validator_accepts_hash_locked_sources_and_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            game = root / "GameAssembly.dll"
            metadata = root / "global-metadata.dat"
            game.write_bytes(b"game")
            metadata.write_bytes(b"metadata")
            body = b"native-body"
            methods = {
                "Fixture.Method": {
                    "token": "0x1",
                    "va": 0x1000,
                    "bytes": len(body),
                    "sha256": hashlib.sha256(body).hexdigest(),
                    "contract": "fixture",
                }
            }
            mapper = type(
                "Mapper",
                (),
                {
                    "PeImage": lambda _path: self.FakePe(_path, body),
                    "load_catalog_module": lambda: type(
                        "Catalog", (), {"Metadata": lambda _path: type("Metadata", (), {"types": []})()}
                    ),
                    "metadata_registration_summary": lambda _pe, _address: {
                        "fieldOffsets": "0x1"
                    },
                },
            )
            with (
                patch.object(audit, "EXPECTED_GAME_ASSEMBLY_SHA256", hashlib.sha256(b"game").hexdigest()),
                patch.object(audit, "EXPECTED_METADATA_SHA256", hashlib.sha256(b"metadata").hexdigest()),
                patch.object(audit, "NATIVE_METHODS", methods),
                patch.object(audit, "EXPECTED_RUNTIME_FIELD_OFFSETS", {}),
                patch.object(audit, "_load_mapper", return_value=mapper),
            ):
                result = audit.validate_native_contract(game, metadata)
            self.assertEqual(result["status"], "validated")
            self.assertEqual(result["methods"][0]["symbol"], "Fixture.Method")

    def test_native_validator_reports_bounded_hash_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            game = root / "GameAssembly.dll"
            metadata = root / "global-metadata.dat"
            game.write_bytes(b"drifted")
            metadata.write_bytes(b"metadata")
            with self.assertRaisesRegex(
                audit.AuditValidationError,
                r"validator=dialog_finish_native_contract gate=sourceSha256 .*expected=.* actual=.*",
            ):
                audit.validate_native_contract(game, metadata)


if __name__ == "__main__":
    unittest.main()

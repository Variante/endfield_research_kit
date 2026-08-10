import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import build_mission_pipeline_data as mission_pipeline
from scripts.story_recovery import build_source_story_partial_order as partial_order
from scripts.story_recovery.dialog_tree_control_flow import (
    ContractError,
    StaticPortFamilySpec,
    parse_static_enum_string_list_initializer,
    project_serialized_family_node,
)


class DialogTreeControlFlowTests(unittest.TestCase):
    @staticmethod
    def family() -> StaticPortFamilySpec:
        return StaticPortFamilySpec(
            family="arbitrary_family",
            node_type="Game.ArbitraryControlNode",
            selector_enum_type="Game.ArbitrarySelector",
            serialized_selector_path=("action", "selector"),
            static_port_map_field="s_ports",
            node_action_method="DoAction",
            manager_type="Game.Manager",
            manager_action_method="Open",
            global_action_type="Game.Action",
            global_action_method="Send",
            manager_next_method="Next",
            controller_type="Game.Controller",
            controller_next_method="Next",
        )

    @staticmethod
    def native_contract(labels: list[str]) -> dict:
        return {
            "schema": "fixture.v1",
            "family": "arbitrary_family",
            "serializedSelectorPath": ["action", "selector"],
            "enumMembers": [{"value": 4, "name": "ArbitraryPanel"}],
            "portMaps": [{
                "selectorValue": 4,
                "selectorName": "ArbitraryPanel",
                "labels": labels,
            }],
            "sources": {
                "gameAssembly": "installed/GameAssembly.dll",
                "gameAssemblySha256": "",
                "globalMetadata": "installed/global-metadata.dat",
                "globalMetadataSha256": "",
            },
            "currentIFix": {
                "status": "audited",
                "sourceLabel": "installed VFS/virtual.patch.bytes",
                "sha256": "CC",
                "relevantFixedMethods": [],
            },
            "nativeMethods": {},
            "staticPortMapField": {"name": "s_ports"},
            "selectionRule": "explicit nonnegative index selects serialized ordinal",
            "evidenceBoundary": "selection only",
        }

    @staticmethod
    def write_tree(path: Path) -> None:
        raw = {
            "nodes": [
                {
                    "$id": "control",
                    "$type": "Game.ArbitraryControlNode",
                    "action": {"selector": 4},
                },
                {"$id": "a", "$type": "Game.TargetA"},
                {"$id": "b", "$type": "Game.TargetB"},
            ],
            "connections": [
                {
                    "_sourceNode": {"$ref": "control"},
                    "_targetNode": {"$ref": "a"},
                },
                {
                    "_sourceNode": {"$ref": "control"},
                    "_targetNode": {"$ref": "b"},
                },
            ],
        }
        path.write_text(
            json.dumps({
                "m_Script": base64.b64encode(
                    json.dumps(raw).encode("utf-8")
                ).decode("ascii"),
            }),
            encoding="utf-8",
        )

    def test_static_enum_string_list_initializer_is_content_independent(self) -> None:
        literals = {
            0x9000: {"status": "decoded", "value": "first"},
            0x9010: {"status": "decoded", "value": "second"},
            0x9020: {"status": "decoded", "value": "only"},
        }
        instructions = [
            {"va": "0x1000", "text": "mov rdx, [rip+0x1 => 0x9000]"},
            {"va": "0x1007", "text": "mov rcx, rdi"},
            {"va": "0x100a", "text": "call 0x7000"},
            {"va": "0x100f", "text": "mov rdx, [rip+0x1 => 0x9010]"},
            {"va": "0x1016", "text": "mov rcx, rdi"},
            {"va": "0x1019", "text": "call 0x7000"},
            {"va": "0x101e", "text": "mov edx, 0x2a"},
            {"va": "0x1023", "text": "call 0x8000"},
            {"va": "0x1028", "text": "mov rdx, [rip+0x1 => 0x9020]"},
            {"va": "0x102f", "text": "mov rcx, rdi"},
            {"va": "0x1032", "text": "call 0x7000"},
            {"va": "0x1037", "text": "xor edx, edx"},
            {"va": "0x1039", "text": "call 0x8000"},
        ]

        rows = parse_static_enum_string_list_initializer(
            instructions,
            dictionary_add_targets={0x8000},
            decode_literal_slot=lambda slot: {"slot": slot, **literals[slot]},
        )

        self.assertEqual([row["selectorValue"] for row in rows], [42, 0])
        self.assertEqual(
            [[label["value"] for label in row["labels"]] for row in rows],
            [["first", "second"], ["only"]],
        )

    def test_serialized_projection_uses_installed_named_port_order(self) -> None:
        contract = {
            "serializedSelectorPath": ["action", "selector"],
            "enumMembers": [{"value": 4, "name": "ArbitraryPanel"}],
            "portMaps": [{
                "selectorValue": 4,
                "selectorName": "ArbitraryPanel",
                "labels": ["accepted", "declined"],
            }],
        }
        projected = project_serialized_family_node(
            {"action": {"selector": 4}},
            [(7, "target-a"), (9, "target-b")],
            target_types={"target-a": "A", "target-b": "B"},
            contract=contract,
        )

        self.assertEqual(projected["selectorName"], "ArbitraryPanel")
        self.assertEqual(projected["portContractStatus"], "native_named_ports")
        self.assertEqual(
            [arm["outcomeLabel"] for arm in projected["arms"]],
            ["accepted", "declined"],
        )
        self.assertEqual(
            [arm["connectionIndex"] for arm in projected["arms"]],
            [7, 9],
        )

    def test_serialized_projection_fails_closed_on_named_port_mismatch(self) -> None:
        contract = {
            "serializedSelectorPath": ["selector"],
            "enumMembers": [{"value": 1, "name": "Panel"}],
            "portMaps": [{
                "selectorValue": 1,
                "selectorName": "Panel",
                "labels": ["one", "two"],
            }],
        }
        with self.assertRaisesRegex(
            ContractError,
            "gate=named_port_count_matches_outgoing",
        ):
            project_serialized_family_node(
                {"selector": 1},
                [(0, "only-target")],
                target_types={"only-target": "Target"},
                contract=contract,
            )

    def test_unmapped_enum_keeps_external_ordinals_without_guessing_labels(self) -> None:
        contract = {
            "serializedSelectorPath": ["selector"],
            "enumMembers": [{"value": 8, "name": "UnmappedPanel"}],
            "portMaps": [],
        }
        projected = project_serialized_family_node(
            {"selector": 8},
            [(0, "a"), (1, "b")],
            target_types={"a": "A", "b": "B"},
            contract=contract,
        )
        self.assertEqual(
            projected["portContractStatus"],
            "external_index_unlabeled",
        )
        self.assertEqual(
            [arm["outcomeLabel"] for arm in projected["arms"]],
            ["", ""],
        )

    def test_family_projection_attaches_source_and_original_contract_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            installed = root / "installed"
            installed.mkdir()
            (installed / "GameAssembly.dll").write_bytes(b"fixture-gameassembly")
            (installed / "global-metadata.dat").write_bytes(b"fixture-metadata")
            source = root / "arbitrary.json"
            self.write_tree(source)
            conversation = {
                "key": "dlg_arbitrary",
                "lineGraph": {"sources": [{
                    "kind": "dialogTree",
                    "file": "arbitrary.json",
                }]},
            }
            with patch.object(partial_order, "ROOT", root):
                rows, warnings = partial_order._dialog_tree_local_static_port_controls(
                    [("conv/arbitrary.json", conversation)],
                    family_spec=self.family(),
                    native_contract=self.native_contract(["yes", "no"]),
                )
            with patch.object(mission_pipeline, "ROOT", root):
                strict_files = mission_pipeline._source_order_shell_related_files({
                    "mission": "fixture",
                    "branches": {"dialogTreeStaticPortControls": rows},
                })
                branch_files = mission_pipeline._story_branch_related_original_files({
                    "mission": "fixture",
                    "branches": {"dialogTreeStaticPortControls": rows},
                })

        self.assertEqual(warnings, [])
        self.assertEqual(len(rows), 1)
        self.assertEqual(
            [arm["outcomeLabel"] for arm in rows[0]["arms"]],
            ["yes", "no"],
        )
        self.assertEqual(
            {item["kind"] for item in rows[0]["relatedOriginalFiles"]},
            {
                "dialog_tree_source",
                "original_game_binary",
                "original_game_metadata",
            },
        )
        self.assertEqual(len(strict_files), 3)
        self.assertEqual(len(branch_files), 3)
        self.assertEqual(
            rows[0]["currentIFix"]["sourceLabel"],
            "installed VFS/virtual.patch.bytes",
        )

    def test_family_projection_reports_bounded_mismatch_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "arbitrary.json"
            self.write_tree(source)
            source_hash = hashlib.sha256(source.read_bytes()).hexdigest().upper()
            conversation = {
                "key": "dlg_arbitrary",
                "lineGraph": {"sources": [{
                    "kind": "dialogTree",
                    "file": "arbitrary.json",
                }]},
            }
            with patch.object(partial_order, "ROOT", root):
                rows, warnings = partial_order._dialog_tree_local_static_port_controls(
                    [("conv/arbitrary.json", conversation)],
                    family_spec=self.family(),
                    native_contract=self.native_contract(["only-one-label"]),
                )

        self.assertEqual(rows, [])
        self.assertEqual(len(warnings), 1)
        failure = warnings[0]
        self.assertEqual(failure["validator"], "dialogTreeStaticPortControl")
        self.assertEqual(failure["gate"], "serializedSelectorAndPortProjection")
        self.assertEqual(failure["sourceSha256"]["arbitrary.json"], source_hash)
        self.assertEqual(failure["actual"]["outgoingConnectionCount"], 2)
        self.assertIn("named_port_count_matches_outgoing", failure["actual"]["projectionError"])


if __name__ == "__main__":
    unittest.main()

import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import build_mission_pipeline_data as mission_pipeline
from scripts.story_builder import source_story_partial_order as partial_order
from scripts.story_builder.dialog_tree_control_flow import (
    ContractError,
    ExternalResultRouterSpec,
    StaticPortFamilySpec,
    parse_lua_external_result_router,
    parse_static_enum_string_list_initializer,
    project_serialized_family_node,
)


class DialogTreeControlFlowTests(unittest.TestCase):
    @staticmethod
    def router_spec() -> ExternalResultRouterSpec:
        return ExternalResultRouterSpec(
            source_root_marker="LuaRoot",
            router_path="Router.lua",
            defaults_path="Defaults.lua",
            open_message="OPEN_RESULT_UI",
            override_message="CHANGE_RESULT_INDEX",
            defaults_table="PHASE_DEFAULTS",
            native_next_expression="Native.Manager:Next",
        )

    @staticmethod
    def lua_router_sources() -> dict[str, bytes]:
        return {
            "Router.lua": b"""
                local PHASE_ID = PhaseId.Dialog
                messages = {
                    [MessageConst.OPEN_RESULT_UI] = { 'OpenUI', true },
                    [MessageConst.CHANGE_RESULT_INDEX] = { 'ChangeNextIndex', true },
                }
                function OpenUI(arg)
                    local panelIdStr = arg[1]
                    local phaseId = PhaseId[panelIdStr]
                end
                function ChangeNextIndex(args)
                    self.m_tempNextIndex = args.nextIndex
                end
                function GetNextIndex(phaseId)
                    if self.m_tempNextIndex >= 0 then return self.m_tempNextIndex end
                    return self.s_nextIndexConfig[phaseId] or 0
                end
                function BackToTop()
                    self:Next(nextIndex)
                end
                function Next(num)
                    Native.Manager:Next(num)
                end
            """,
            "Defaults.lua": b"""
                PHASE_DEFAULTS = {
                    ConfiguredPanel = 1,
                }
            """,
            "Messages.lua": b'"CHANGE_RESULT_INDEX",\n',
            "ConfiguredPanel.lua": b"""
                local PHASE_ID = PhaseId.ConfiguredPanel
                function Close()
                    Notify(MessageConst.CHANGE_RESULT_INDEX, {
                        phaseId = PHASE_ID,
                        nextIndex = 0,
                    })
                end
            """,
            "ConditionalPanel.lua": b"""
                local PANEL_ID = PanelId.ConditionalPanel
                function Close()
                    local result = 0
                    if accepted then result = 1 end
                    Notify(MessageConst.CHANGE_RESULT_INDEX, { phaseId = PANEL_ID, nextIndex = result })
                    Native.Manager:Next(1)
                end
            """,
        }

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
        def lua_source(name: str, relationship: str) -> dict:
            return {
                "kind": "original_game_lua",
                "sourceFile": f"installed StreamingAssets VFS/Lua/Data/LuaScripts/{name}",
                "sha256": "AA" * 32,
                "relationship": relationship,
                "materialized": False,
            }
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
            "externalResultRouter": {
                "defaultIndex": 0,
                "phaseDefaults": {},
                "routerSource": lua_source("Router.lua", "router"),
                "defaultsSource": lua_source("Defaults.lua", "defaults"),
                "producersByPhase": {
                    "ArbitraryPanel": [{
                        "kind": "override_message",
                        "phaseName": "ArbitraryPanel",
                        "indexExpression": "1",
                        "possibleIndexes": [1],
                        "indexStatus": "bounded_literals",
                        "line": 12,
                        "excerpt": "Notify(... nextIndex = 1)",
                        "source": lua_source("ArbitraryPanel.lua", "producer"),
                    }],
                },
            },
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

    def test_lua_external_result_router_recovers_general_defaults_and_producers(self) -> None:
        result = parse_lua_external_result_router(
            self.lua_router_sources(),
            self.router_spec(),
        )

        self.assertEqual(result["phaseDefaults"], {"ConfiguredPanel": 1})
        self.assertEqual(result["sourceCorpus"]["fileCount"], 5)
        self.assertEqual(result["sourceCorpus"]["overrideProducerCount"], 2)
        conditional = result["producersByPhase"]["ConditionalPanel"]
        self.assertEqual(
            [(row["kind"], row["possibleIndexes"]) for row in conditional],
            [("override_message", [0, 1]), ("direct_native_next", [1])],
        )
        self.assertTrue(all(row["source"]["sha256"] for row in conditional))

    def test_lua_external_result_router_fails_closed_on_unparsed_occurrence(self) -> None:
        sources = self.lua_router_sources()
        sources["Unknown.lua"] = b"dispatch(MessageConst.CHANGE_RESULT_INDEX, value)\n"
        with self.assertRaisesRegex(
            ContractError,
            r"gate=override_occurrence_census.*source=Unknown.lua",
        ):
            parse_lua_external_result_router(sources, self.router_spec())

    def test_lua_formal_parameter_recovers_general_literal_call_paths(self) -> None:
        sources = self.lua_router_sources()
        sources["ArbitraryController.lua"] = b"""
            local PHASE_ID = PhaseId.ArbitraryController
            ArbitraryController = HL.Class('ArbitraryController')
            ArbitraryController.OnCreate = HL.Method() << function(self)
                self:Finish(7)
                self:Finish(runtimeValue)
            end
            ArbitraryController.Finish = HL.Method(HL.Number) << function(self, selectedPort)
                Notify(MessageConst.CHANGE_RESULT_INDEX, {
                    phaseId = PHASE_ID,
                    nextIndex = selectedPort,
                })
            end
        """

        result = parse_lua_external_result_router(sources, self.router_spec())
        producer = result["producersByPhase"]["ArbitraryController"][0]

        self.assertEqual(producer["possibleIndexes"], [7])
        self.assertEqual(
            producer["indexStatus"],
            "literal_call_paths_with_dynamic_residual",
        )
        self.assertEqual(
            [(row["callerMethod"], row["calleeMethod"], row["value"])
             for row in producer["valueFlowEvidence"]],
            [("OnCreate", "Finish", 7)],
        )

    def test_projection_marks_proven_call_path_and_dynamic_residual(self) -> None:
        sources = self.lua_router_sources()
        sources["ArbitraryController.lua"] = b"""
            local PHASE_ID = PhaseId.ArbitraryController
            ArbitraryController = HL.Class('ArbitraryController')
            ArbitraryController.OnCreate = HL.Method() << function(self)
                self:Finish(1)
            end
            ArbitraryController.Finish = HL.Method(HL.Number) << function(self, selectedPort)
                Notify(MessageConst.CHANGE_RESULT_INDEX, {
                    phaseId = PHASE_ID,
                    nextIndex = selectedPort,
                })
            end
        """
        router = parse_lua_external_result_router(sources, self.router_spec())
        projected = project_serialized_family_node(
            {"selector": 11},
            [(0, "a"), (1, "b")],
            target_types={"a": "A", "b": "B"},
            contract={
                "serializedSelectorPath": ["selector"],
                "enumMembers": [{"value": 11, "name": "ArbitraryController"}],
                "portMaps": [],
                "externalResultRouter": router,
            },
        )

        self.assertEqual(
            projected["arms"][1]["runtimeProducerStatus"],
            "shipped_lua_producer_with_dynamic_residual",
        )
        self.assertEqual(projected["runtimeProducedArmCount"], 2)
        self.assertEqual(projected["runtimeDynamicProducerArmCount"], 1)

    def test_serialized_projection_marks_current_shipped_producer_coverage(self) -> None:
        router = parse_lua_external_result_router(
            self.lua_router_sources(),
            self.router_spec(),
        )
        contract = {
            "serializedSelectorPath": ["selector"],
            "enumMembers": [{"value": 7, "name": "ConfiguredPanel"}],
            "portMaps": [],
            "externalResultRouter": router,
        }
        projected = project_serialized_family_node(
            {"selector": 7},
            [(0, "a"), (1, "b")],
            target_types={"a": "A", "b": "B"},
            contract=contract,
        )

        self.assertEqual(projected["runtimeDefaultIndex"], 1)
        self.assertEqual(projected["runtimeProducedArmCount"], 2)
        self.assertEqual(
            [arm["runtimeProducerStatus"] for arm in projected["arms"]],
            ["shipped_lua_producer", "shipped_lua_producer"],
        )
        self.assertEqual(
            projected["arms"][0]["runtimeProducerKinds"],
            ["override_message"],
        )
        self.assertIn("configured_phase_default", projected["arms"][1]["runtimeProducerKinds"])

    def test_serialized_projection_keeps_dynamic_index_producer_unbounded(self) -> None:
        router = parse_lua_external_result_router(
            self.lua_router_sources(),
            self.router_spec(),
        )
        dynamic_source = {
            "kind": "original_game_lua",
            "sourceFile": "installed StreamingAssets VFS/Lua/Data/LuaScripts/Dynamic.lua",
            "sha256": "BB" * 32,
        }
        router["producersByPhase"]["DynamicPanel"] = [{
            "kind": "override_message",
            "phaseName": "DynamicPanel",
            "indexExpression": "result.index",
            "possibleIndexes": [],
            "indexStatus": "dynamic_expression",
            "line": 20,
            "excerpt": "nextIndex = result.index",
            "source": dynamic_source,
        }]
        projected = project_serialized_family_node(
            {"selector": 9},
            [(0, "a"), (1, "b")],
            target_types={"a": "A", "b": "B"},
            contract={
                "serializedSelectorPath": ["selector"],
                "enumMembers": [{"value": 9, "name": "DynamicPanel"}],
                "portMaps": [],
                "externalResultRouter": router,
            },
        )

        self.assertEqual(projected["runtimeProducedArmCount"], 1)
        self.assertEqual(projected["runtimeDynamicProducerArmCount"], 1)
        self.assertEqual(projected["runtimeUnproducedArmCount"], 0)
        self.assertEqual(
            projected["arms"][1]["runtimeProducerStatus"],
            "shipped_lua_dynamic_index_unbounded",
        )

    def test_serialized_projection_fails_closed_on_default_outside_arms(self) -> None:
        with self.assertRaisesRegex(
            ContractError,
            r"gate=runtime_default_index_in_outgoing_range.*actual=2",
        ):
            project_serialized_family_node(
                {"selector": 2},
                [(0, "a"), (1, "b")],
                target_types={"a": "A", "b": "B"},
                contract={
                    "serializedSelectorPath": ["selector"],
                    "enumMembers": [{"value": 2, "name": "BadDefault"}],
                    "portMaps": [],
                    "externalResultRouter": {
                        "defaultIndex": 0,
                        "phaseDefaults": {"BadDefault": 2},
                        "producersByPhase": {},
                    },
                },
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
                "original_game_lua",
            },
        )
        self.assertEqual(rows[0]["runtimeProducedArmCount"], 2)
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

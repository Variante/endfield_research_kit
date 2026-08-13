from ._support import *

class SourceGapMajorMissionContractTests(SourceGapTestCase):
    def test_declared_gm02m8_text_only_progress_dialogs_are_exact(self) -> None:
        text_only = gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS
        for number in (2, 3, 4):
            story_key = f"dlg_gm02m8_{number}"
            self.assertEqual(
                text_only[story_key],
                {
                    "missionId": "gm02m8",
                    "dialogIdRegistrationStatus": "absent",
                    "lineIds": (
                        f"{story_key}_001",
                        f"{story_key}_002",
                    ),
                    "missingAudioIds": (
                        f"au_{story_key}_001",
                        f"au_{story_key}_002",
                    ),
                },
            )
            self.assertEqual(
                gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS[story_key],
                story_key,
            )
        topology = gap_queue.OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS[
            "gm02m8"
        ]
        self.assertEqual(
            topology["mainPathQuestIds"],
            ("gm02m8_q#1", "gm02m8_q#2", "gm02m8_q#3"),
        )
        self.assertEqual(
            topology["prevQuestIdsByQuest"],
            {
                "gm02m8_q#1": (),
                "gm02m8_q#2": ("gm02m8_q#1",),
                "gm02m8_q#3": ("gm02m8_q#2",),
            },
        )

    def test_declared_a1m7_text_only_branch_frontier_is_exact(self) -> None:
        text_only = gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS
        self.assertEqual(
            text_only["dlg_a1m7_2"]["lineIds"],
            ("dlg_a1m7_2_001", "dlg_a1m7_2_002"),
        )
        self.assertEqual(
            set(text_only["dlg_a1m7_2"]["optionRows"]),
            {
                "option_dlg_a1m7_2_1_001",
                "option_dlg_a1m7_2_2_001",
                "option_dlg_a1m7_2_2_002",
            },
        )
        self.assertEqual(text_only["dlg_a1m7_12"]["optionRows"], {})
        popup = gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS[
            "text_a1m6d5_1"
        ]
        self.assertEqual(popup["readingPopupRowId"], "rp_text_a1m6d5_1")
        self.assertEqual(popup["iconType"], 3)
        self.assertEqual(len(popup["contentTextIds"]), 14)

    def test_a1m7_option_definition_validator_reports_exact_failure(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports"
            / "mission_order"
            / "source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full"
            / "structured"
            / "StreamingAssets"
            / "Table"
        )
        index, status = gap_queue.build_offline_exhaustion_index(
            partial,
            table_root,
        )
        self.assertEqual(status["status"], "active")
        self.assertEqual(
            index["dlg_a1m7_2"]["optionRouteStatus"],
            "definitions_present_route_unresolved",
        )

        definition = gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS[
            "dlg_a1m7_2"
        ]
        broken_rows = {
            key: dict(value)
            for key, value in definition["optionRows"].items()
        }
        broken_rows["option_dlg_a1m7_2_1_001"] = {
            **broken_rows["option_dlg_a1m7_2_1_001"],
            "iconType": "Changed",
        }
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS,
            {"dlg_a1m7_2": {**definition, "optionRows": broken_rows}},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(
                    partial,
                    table_root,
                )
            )
        self.assertEqual(failed_index, {})
        self.assertEqual(
            failed_status["status"],
            "inactive_text_only_dialog_definition_validation_failed",
        )
        failure = next(
            row for row in failed_status["validationFailures"]
            if row["storyKey"] == "dlg_a1m7_2"
        )
        self.assertEqual(failure["validator"], "offlineTextOnlyDialogDefinition")
        self.assertEqual(failure["gate"], "exactDialogOptionDefinitions")
        self.assertIn("dialogOptionTable", failure["sourceSha256"])
        self.assertEqual(
            failure["actual"]["option_dlg_a1m7_2_1_001"]["iconType"],
            "Default",
        )

    def test_declared_gm02m2_table_only_branch_frontier_is_exact(self) -> None:
        text_only = gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS
        self.assertEqual(
            {
                key: (
                    len(text_only[key]["lineIds"]),
                    len(text_only[key]["optionRows"]),
                    text_only[key]["dialogIdRegistrationStatus"],
                )
                for key in (
                    "dlg_gm02m2_1",
                    "dlg_gm02m2_2",
                    "dlg_gm02m2_3",
                    "dlg_gm02m2_4",
                )
            },
            {
                "dlg_gm02m2_1": (7, 3, "present_table_only"),
                "dlg_gm02m2_2": (1, 2, "present_table_only"),
                "dlg_gm02m2_3": (5, 3, "present_table_only"),
                "dlg_gm02m2_4": (3, 1, "present_table_only"),
            },
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_GM02M2_RADIOS,
            {
                "radio_gm02m2_1",
                "radio_gm02m2_2",
                "radio_gm02m2_2d5",
                "radio_gm02m2_3",
                "radio_gm02m2_4",
                "radio_gm02m2_5",
                "radio_gm02m2_6",
                "radio_gm02m2_7",
                "radio_gm02m2_10",
            },
        )

    def test_declared_gm02m3_table_only_branch_frontier_is_exact(self) -> None:
        text_only = gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS
        self.assertEqual(
            {
                key: (
                    len(text_only[key]["lineIds"]),
                    len(text_only[key]["optionRows"]),
                    text_only[key].get(
                        "dialogIdRegistrationStatus",
                        "absent",
                    ),
                )
                for key in (
                    "dlg_gm02m3_1",
                    "dlg_gm02m3_2",
                    "dlg_gm02m3_3",
                    "dlg_gm02m3_4",
                    "dlg_gm02m3_5",
                )
            },
            {
                "dlg_gm02m3_1": (12, 3, "present_table_only"),
                "dlg_gm02m3_2": (4, 2, "present_table_only"),
                "dlg_gm02m3_3": (3, 2, "present_table_only"),
                "dlg_gm02m3_4": (4, 0, "absent"),
                "dlg_gm02m3_5": (7, 3, "absent"),
            },
        )
        self.assertEqual(
            {
                key: text_only[key].get("printableOnlyDialogTokens", ())
                for key in (
                    "dlg_gm02m3_1",
                    "dlg_gm02m3_2",
                    "dlg_gm02m3_3",
                )
            },
            {
                "dlg_gm02m3_1": ("dlg_gm02m3_1X", "dlg_gm02m3_1Y"),
                "dlg_gm02m3_2": ("dlg_gm02m3_2Y", "dlg_gm02m3_2Z"),
                "dlg_gm02m3_3": ("dlg_gm02m3_3Z", "dlg_gm02m3_3d"),
            },
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_GM02M3_RADIOS,
            {f"radio_gm02m3_{number}" for number in range(1, 6)},
        )
        self.assertEqual(
            {
                key for key in gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS
                if "gm02m3" in key
            },
            {
                "dlg_gm02m3_1", "dlg_gm02m3_2", "dlg_gm02m3_3",
                "dlg_gm02m3_4", "dlg_gm02m3_5",
                "radio_gm02m3_1", "radio_gm02m3_2", "radio_gm02m3_3",
                "radio_gm02m3_4", "radio_gm02m3_5",
                "dlg_gm02m3_1X", "dlg_gm02m3_1Y",
                "dlg_gm02m3_2Y", "dlg_gm02m3_2Z",
                "dlg_gm02m3_3Z", "dlg_gm02m3_3d",
            },
        )

    def test_gm02m13_radio_frontier_and_dialog_guard_topology_are_exact(
        self,
    ) -> None:
        story_keys = {
            "radio_gm02m13_3",
            "radio_gm02m13_4",
            "radio_gm02m13_5",
        }
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_GM02M13_RADIOS,
            story_keys,
        )
        self.assertEqual(
            story_keys,
            {
                key
                for key in gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS
                if "gm02m13" in key
            },
        )
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT / "export_full/structured/StreamingAssets/Table"
        )
        index, status = gap_queue.build_offline_exhaustion_index(
            partial,
            table_root,
        )
        self.assertEqual("active", status["status"])
        self.assertTrue(story_keys <= set(index))
        for number in (3, 4, 5):
            story_key = f"radio_gm02m13_{number}"
            self.assertEqual(
                index[story_key]["missingAudioIds"],
                [f"au_radio_gm02m13_{number}_001"],
            )
        topology = index["radio_gm02m13_3"][
            "missionQuestTopologyContext"
        ]
        self.assertEqual(
            [
                "gm02m13_q#5", "gm02m13_q#6",
                "gm02m13_q#7", "gm02m13_q#15",
            ],
            topology["mainPathQuestIds"],
        )
        self.assertEqual(4, len(topology["forks"]))
        self.assertEqual(1, len(topology["merges"]))
        self.assertEqual(
            {
                "gm02m13_q#6": {"dlg_gm02m13_3", "dlg_gm02m13_4"},
                "gm02m13_q#8": {"dlg_gm02m13_2", "dlg_gm02m13_4"},
                "gm02m13_q#9": {"dlg_gm02m13_2", "dlg_gm02m13_3"},
            },
            {
                row["questId"]: {
                    finish["dialogId"]
                    for finish in row["dialogFinishes"]
                }
                for row in topology["failedDialogGuards"]
            },
        )
        self.assertTrue(all(
            not row["storyOrderEvidence"]
            for row in topology["failedDialogGuards"]
        ))
        self.assertEqual([], topology["failedQuestStateGuards"])
        self.assertEqual([], topology["storyAssignments"])
        self.assertFalse(topology["orderEvidence"])

    def test_gm02m14_radio_frontier_and_mission_topology_are_exact(
        self,
    ) -> None:
        story_keys = {"radio_gm02m14_1", "radio_gm02m14_12"}
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_GM02M14_RADIOS,
            story_keys,
        )
        self.assertEqual(
            story_keys,
            {
                key
                for key in gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS
                if "gm02m14" in key
            },
        )
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT / "export_full/structured/StreamingAssets/Table"
        )
        index, status = gap_queue.build_offline_exhaustion_index(
            partial,
            table_root,
        )
        self.assertEqual("active", status["status"])
        self.assertTrue(story_keys <= set(index))
        self.assertEqual(
            index["radio_gm02m14_1"]["missingAudioIds"],
            ["au_radio_gm02m14_1_001"],
        )
        self.assertEqual(
            index["radio_gm02m14_12"]["missingAudioIds"],
            ["au_radio_gm02m14_12_001"],
        )
        topology = index["radio_gm02m14_1"][
            "missionQuestTopologyContext"
        ]
        self.assertEqual(
            [
                "gm02m14_q#1", "gm02m14_q#2", "gm02m14_q#3",
                "gm02m14_q#5", "gm02m14_q#6", "gm02m14_q#4",
                "gm02m14_q#7", "gm02m14_q#8", "gm02m14_q#9",
                "gm02m14_q#10", "gm02m14_q#11", "gm02m14_q#12",
            ],
            topology["mainPathQuestIds"],
        )
        self.assertEqual([], topology["forks"])
        self.assertEqual([], topology["merges"])
        self.assertEqual([], topology["storyAssignments"])
        self.assertFalse(topology["orderEvidence"])

    def test_gm02m15_radio_frontier_and_objective_conjunction_are_exact(
        self,
    ) -> None:
        story_keys = {"radio_gm02m15_9", "radio_gm02m15_12"}
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_GM02M15_RADIOS,
            story_keys,
        )
        self.assertEqual(
            story_keys,
            {
                key
                for key in gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS
                if "gm02m15" in key
            },
        )
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT / "export_full/structured/StreamingAssets/Table"
        )
        index, status = gap_queue.build_offline_exhaustion_index(
            partial,
            table_root,
        )
        self.assertEqual("active", status["status"])
        self.assertTrue(story_keys <= set(index))
        self.assertEqual(
            [
                "au_radio_gm02m15_9_001",
                "au_radio_gm02m15_9_002",
                "au_radio_gm02m15_9_003",
                "au_radio_gm02m15_9_004",
            ],
            index["radio_gm02m15_9"]["missingAudioIds"],
        )
        self.assertEqual(
            [
                "au_radio_gm02m15_12_001",
                "au_radio_gm02m15_12_002",
            ],
            index["radio_gm02m15_12"]["missingAudioIds"],
        )
        topology = index["radio_gm02m15_9"][
            "missionQuestTopologyContext"
        ]
        self.assertEqual(
            [f"gm02m15_q#{number}" for number in range(1, 9)],
            topology["mainPathQuestIds"],
        )
        self.assertEqual([], topology["forks"])
        self.assertEqual([], topology["merges"])
        self.assertEqual(1, len(topology["objectiveConjunctions"]))
        conjunction = topology["objectiveConjunctions"][0]
        self.assertEqual("gm02m15_q#5", conjunction["questId"])
        self.assertEqual(
            ["jianbei1", "jianbei2", "jianbei3"],
            [row["key"] for row in conjunction["subConditions"]],
        )
        self.assertEqual(
            "all_serialized_conditions_required",
            conjunction["completionSemantics"],
        )
        self.assertEqual("not_serialized", conjunction["executionOrderStatus"])
        self.assertFalse(conjunction["storyOrderEvidence"])
        self.assertIn(
            "export_full/structured/StreamingAssets/Data/Json/"
            "LevelScriptData/map02_lv006/25000120003.json",
            conjunction["relatedSourceFiles"],
        )
        self.assertEqual([], topology["storyAssignments"])
        self.assertFalse(topology["orderEvidence"])

    def test_gm02m15_objective_conjunction_validator_fails_closed(
        self,
    ) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT / "export_full/structured/StreamingAssets/Table"
        )
        declaration = gap_queue.OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS[
            "gm02m15"
        ]
        broken_conjunctions = copy.deepcopy(
            declaration["objectiveConjunctionsByQuest"]
        )
        broken_conjunctions["gm02m15_q#5"][0]["subConditions"][1][
            "key"
        ] = "jianbei_missing"
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS,
            {"gm02m15": {
                **declaration,
                "objectiveConjunctionsByQuest": broken_conjunctions,
            }},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(
                    partial,
                    table_root,
                )
            )
        self.assertEqual({}, failed_index)
        failure = failed_status["validatorDiagnostics"][0]
        self.assertEqual("offlineMissionTopologyContext", failure["validator"])
        self.assertEqual(
            "exactQuestPredecessorGraphMainPathStateDependenciesAndObjectiveConjunctions",
            failure["gate"],
        )
        self.assertEqual("gm02m15", failure["mission"])
        expected = failure["expected"]["objectiveConjunctionsByQuest"]
        actual = failure["actual"]["objectiveConjunctionsByQuest"]
        self.assertEqual(
            "jianbei_missing",
            expected["gm02m15_q#5"][0]["subConditions"][1]["key"],
        )
        self.assertEqual(
            "jianbei2",
            actual["gm02m15_q#5"][0]["subConditions"][1]["key"],
        )
        self.assertIn("sourceSha256", failure)

    def test_gm02m21_branch_stage_gate_and_playback_inventory_are_exact(
        self,
    ) -> None:
        story_keys = {"radio_gm02m21_4", "radio_gm02m21_7"}
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_GM02M21_RADIOS,
            story_keys,
        )
        self.assertEqual(
            story_keys,
            {
                key
                for key in gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS
                if "gm02m21" in key
            },
        )
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT / "export_full/structured/StreamingAssets/Table"
        )
        index, status = gap_queue.build_offline_exhaustion_index(
            partial,
            table_root,
        )
        self.assertEqual("active", status["status"])
        self.assertTrue(story_keys <= set(index))
        self.assertEqual(
            [
                "au_radio_gm02m21_4_001",
                "au_radio_gm02m21_4_002",
            ],
            index["radio_gm02m21_4"]["missingAudioIds"],
        )
        self.assertEqual(
            ["au_radio_gm02m21_7_001"],
            index["radio_gm02m21_7"]["missingAudioIds"],
        )
        topology = index["radio_gm02m21_4"][
            "missionQuestTopologyContext"
        ]
        self.assertEqual(
            [f"gm02m21_q#{number}" for number in range(1, 6)],
            topology["mainPathQuestIds"],
        )
        self.assertEqual(
            [{
                "questId": "gm02m21_q#1",
                "successorQuestIds": ["gm02m21_q#2", "gm02m21_q#6"],
            }],
            topology["forks"],
        )
        self.assertEqual([], topology["merges"])
        self.assertEqual(
            [{
                "questId": "gm02m21_q#6",
                "conditionType": "CheckQuestState",
                "targetQuestId": "gm02m21_q#1",
                "comparer": 1,
                "targetQuestState": 3,
                "relation": "authored_quest_failure_guard",
                "branchExclusivityStatus": (
                    "not_proven_by_one_way_failure_guard"
                ),
                "storyOrderEvidence": False,
            }],
            topology["failedQuestStateGuards"],
        )
        self.assertEqual(
            [{
                "questId": "gm02m21_q#6",
                "objectiveIndex": 1,
                "targetQuestId": "gm02m21_q#2",
                "comparer": 0,
                "targetQuestState": 3,
                "scopeMask": 1,
                "useGraphScope": True,
            }],
            topology["questStateDependencies"],
        )
        conjunction = topology["objectiveConjunctions"][0]
        self.assertEqual("gm02m21_q#2", conjunction["questId"])
        self.assertEqual(
            [1, 2, 3, 4, 7],
            [row["stageValue"] for row in conjunction["subConditions"]],
        )
        self.assertEqual(
            {3},
            {row["compareOperator"] for row in conjunction["subConditions"]},
        )
        inventory = topology["levelScriptPlaybackInventories"][0]
        self.assertEqual(
            [
                "radio_gm02m21_1", "radio_gm02m21_2",
                "radio_gm02m21_3", "radio_gm02m21_5",
                "radio_gm02m21_8",
            ],
            [row["storyKey"] for row in inventory["playbackRecords"]],
        )
        self.assertTrue(all(
            row["independentActionRoot"]
            for row in inventory["playbackRecords"]
        ))
        self.assertEqual(
            ["radio_gm02m21_4", "radio_gm02m21_7"],
            inventory["absentStoryKeys"],
        )
        self.assertEqual(
            "not_execution_order",
            inventory["serializedListOrderStatus"],
        )
        self.assertFalse(inventory["storyOrderEvidence"])
        self.assertEqual([], topology["storyAssignments"])
        self.assertFalse(topology["orderEvidence"])

    def test_gm02m21_stage_conjunction_validator_fails_closed(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT / "export_full/structured/StreamingAssets/Table"
        )
        declaration = gap_queue.OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS[
            "gm02m21"
        ]
        broken_conjunctions = copy.deepcopy(
            declaration["objectiveConjunctionsByQuest"]
        )
        broken_conjunctions["gm02m21_q#2"][0]["subConditions"][4][
            "stageValue"
        ] = 6
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS,
            {"gm02m21": {
                **declaration,
                "objectiveConjunctionsByQuest": broken_conjunctions,
            }},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(
                    partial,
                    table_root,
                )
            )
        self.assertEqual({}, failed_index)
        failure = failed_status["validatorDiagnostics"][0]
        self.assertEqual("offlineMissionTopologyContext", failure["validator"])
        self.assertEqual("gm02m21", failure["mission"])
        self.assertEqual(
            6,
            failure["expected"]["objectiveConjunctionsByQuest"]
            ["gm02m21_q#2"][0]["subConditions"][4]["stageValue"],
        )
        self.assertEqual(
            7,
            failure["actual"]["objectiveConjunctionsByQuest"]
            ["gm02m21_q#2"][0]["subConditions"][4]["stageValue"],
        )

    def test_gm02m21_playback_inventory_validator_fails_closed(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT / "export_full/structured/StreamingAssets/Table"
        )
        declaration = gap_queue.OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS[
            "gm02m21"
        ]
        broken_inventories = copy.deepcopy(
            declaration["levelScriptPlaybackInventories"]
        )
        broken_inventories[0]["playbackRecords"][3][
            "storyKey"
        ] = "radio_gm02m21_missing"
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS,
            {"gm02m21": {
                **declaration,
                "levelScriptPlaybackInventories": broken_inventories,
            }},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(
                    partial,
                    table_root,
                )
            )
        self.assertEqual({}, failed_index)
        failure = failed_status["validatorDiagnostics"][0]
        self.assertEqual(
            "offlineLevelScriptPlaybackInventory",
            failure["validator"],
        )
        self.assertEqual(
            "exactTypedPlaybackRecordsIndependentRootsAndAbsentTargets",
            failure["gate"],
        )
        self.assertEqual("gm02m21", failure["mission"])
        self.assertEqual(
            "radio_gm02m21_missing",
            failure["expected"][0]["playbackRecords"][3]["storyKey"],
        )
        self.assertEqual(
            "radio_gm02m21_5",
            failure["actual"][0]["playbackRecords"][3]["storyKey"],
        )
        self.assertIn("sourceSha256", failure)

    def test_gm01m4_dialog_radio_frontier_and_linear_topology_are_exact(
        self,
    ) -> None:
        story_keys = {
            "dlg_gm01m4_7",
            "misc_dlg_gm01m4_3d5",
            "radio_gm01m4_1",
        }
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_GM01M4_RADIOS,
            {"radio_gm01m4_1"},
        )
        self.assertEqual(
            story_keys,
            {
                key
                for key in gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS
                if "gm01m4" in key
            },
        )

        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT / "export_full/structured/StreamingAssets/Table"
        )
        index, status = gap_queue.build_offline_exhaustion_index(
            partial,
            table_root,
        )
        self.assertEqual("active", status["status"])
        self.assertTrue(story_keys <= set(index))

        linear = index["dlg_gm01m4_7"]
        self.assertEqual(
            linear["missingAudioIds"],
            ["au_dlg_gm01m4_7_001", "au_dlg_gm01m4_7_002"],
        )
        self.assertEqual([], linear["dialogTreeBranchGroups"])
        self.assertEqual(
            linear["npcProxyConsumers"],
            [{
                "proxyId": "luoke_map01_v1d0d0_gm01m4man",
                "entryIndex": 3,
                "dialogId": "dlg_gm01m4_7",
                "missionId": "",
                "relation": "npc_proxy_ex_dialog_consumer_without_mission_id",
                "missionOwnership": False,
                "orderEvidence": False,
                "graphEffect": "none",
            }],
        )
        self.assertEqual(
            linear["missionNpcProxyTracking"]["questIds"],
            ["gm01m4_q#2"],
        )

        branched = index["misc_dlg_gm01m4_3d5"]
        self.assertEqual(
            branched["missingAudioIds"],
            [
                f"au_dlg_gm01m4_3d5_{number:03d}"
                for number in range(1, 7)
            ],
        )
        self.assertEqual(
            branched["npcProxyConsumers"][0]["entryIndex"],
            1,
        )
        self.assertEqual(
            branched["dialogTreeBranchGroups"],
            [{
                "optionGroup": 1,
                "optionIds": [
                    "option_dlg_gm01m4_3d5_1_001",
                    "option_dlg_gm01m4_3d5_1_002",
                ],
                "targetLineIds": [
                    "dlg_gm01m4_3d5_002",
                    "dlg_gm01m4_3d5_004",
                ],
                "routeKind": "authored_split",
            }],
        )
        self.assertEqual(
            index["radio_gm01m4_1"]["missingAudioIds"],
            ["au_radio_gm01m4_1_001"],
        )

        topology = linear["missionQuestTopologyContext"]
        self.assertEqual(
            ["gm01m4_q#1", "gm01m4_q#2"],
            topology["mainPathQuestIds"],
        )
        self.assertEqual([], topology["forks"])
        self.assertEqual([], topology["merges"])
        self.assertEqual([], topology["storyAssignments"])
        self.assertFalse(topology["orderEvidence"])
        for story_key in story_keys:
            self.assertEqual(
                index[story_key]["recoveryStatus"],
                "deferred_current_build_offline_surface_exhausted",
            )
            self.assertEqual(index[story_key]["graphEffect"], "none")

    def test_declared_gm01m22_binary_bounded_frontier_is_exact(self) -> None:
        self.assertEqual(
            {
                key for key in gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS
                if "gm01m22" in key
            },
            {
                "dlg_gm01m22_6",
                "dlg_gm01m22_7",
                "dlg_gm01m22_8",
                "misc_dlg_gm01m22_2d5",
                "misc_dlg_gm01m22_3d2",
                "misc_dlg_gm01m22_3d8",
                "misc_dlg_gm01m22_4d0",
                "radio_gm01m22_1d2",
                "radio_gm01m22_1d3",
                "sns_gm01m22_2",
                "text_gm01m22_5",
            },
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_GM01M22_RADIOS,
            {"radio_gm01m22_1d2", "radio_gm01m22_1d3"},
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_SNS_DEFINITIONS[
                "sns_gm01m22_2"
            ]["dialogType"],
            2,
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS[
                "text_gm01m22_5"
            ]["contentTextIds"],
            (
                9056785448930934737,
                -3599045778776472798,
                -8943409554594408505,
                -5685369311502986662,
            ),
        )

    def test_declared_gm01m6_npc_proxy_frontier_is_exact(self) -> None:
        story_keys = {
            "dlg_gm01m6_6",
            "dlg_gm01m6_7",
            "misc_dlg_gm01m6_1d5",
            "misc_dlg_gm01m6_3d7",
            "misc_dlg_gm01m6_4d5",
            "misc_dlg_gm01m6_4d7",
            "radio_gm01m6_0d5",
            "radio_gm01m6_4d5",
            "radio_gm01m6_6",
        }
        self.assertEqual(
            {
                key
                for key in gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS
                if "gm01m6" in key
            },
            story_keys,
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_GM01M6_RADIOS,
            {
                "radio_gm01m6_0d5",
                "radio_gm01m6_4d5",
                "radio_gm01m6_6",
            },
        )
        expected_consumers = {
            "dlg_gm01m6_6": ("heerman_map01_default", 1),
            "dlg_gm01m6_7": ("sikete_map01_default", 0),
            "misc_dlg_gm01m6_3d7": ("heerman_map01_001", 3),
            "misc_dlg_gm01m6_4d5": ("heerman_map01_002", 0),
            "misc_dlg_gm01m6_4d7": ("sikete_map01_002", 0),
        }
        for story_key, (proxy_id, entry_index) in expected_consumers.items():
            consumer = current_npc_proxy_consumer_contexts(story_key)[0]
            self.assertEqual(consumer["proxyId"], proxy_id)
            self.assertEqual(consumer["entryIndex"], entry_index)
            self.assertEqual(consumer["entry"]["missionId"], "")
        self.assertNotIn(
            "npcProxyConsumer",
            gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
                "misc_dlg_gm01m6_1d5"
            ],
        )
        for definition in (
            gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS.values()
        ):
            self.assertNotIn("missionNpcProxyTracking", definition)

    def test_gm01m6_mission_npc_tracking_is_visible_and_fails_closed(
        self,
    ) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Table"
        )
        index, status = gap_queue.build_offline_exhaustion_index(
            partial,
            table_root,
        )
        self.assertEqual(status["status"], "active")
        tracking = index["misc_dlg_gm01m6_3d7"][
            "missionNpcProxyTracking"
        ]
        self.assertEqual(tracking["proxyId"], "heerman_map01_001")
        self.assertEqual(tracking["levelId"], "map01_lv006")
        self.assertEqual(
            tracking["questIds"],
            ["gm01m6_q#3", "gm01m6_q#10"],
        )
        self.assertFalse(tracking["missionOwnership"])
        self.assertFalse(tracking["questPlaybackOwnership"])
        self.assertFalse(tracking["orderEvidence"])

        with tempfile.TemporaryDirectory() as temp_dir:
            streaming_root = Path(temp_dir) / "Streaming"
            persistent_root = Path(temp_dir) / "Persistent"
            streaming_root.mkdir()
            persistent_root.mkdir()
            tracking = {
                "$type": gap_queue.NPC_PROXY_TRACKING_INFO_TYPE,
                "useFilterCondition": False,
                "sceneId": "future_level",
                "guidingArea": 0.0,
                "npcProxyId": "proxy_future",
            }
            payload = {
                "missionId": "future_mission",
                "questDic": {
                    quest_id: {
                        "objectiveList": [{
                            "trackingInfoList": [
                                {
                                    **tracking,
                                    **(
                                        {
                                            "useFilterCondition": True,
                                            "filterCondition": {"$type": "fixture"},
                                        }
                                        if quest_id == "future_mission_q#12"
                                        else {}
                                    ),
                                },
                            ],
                        }],
                    }
                    for quest_id in (
                        "future_mission_q#12",
                        "future_mission_q#2",
                    )
                },
            }
            for root in (streaming_root, persistent_root):
                (root / "future_mission.json").write_text(
                    json.dumps(payload),
                    encoding="utf-8",
                )
            corpus = gap_queue._build_mission_npc_proxy_tracking_index(
                streaming_root,
                persistent_root,
            )
            contexts, failures = (
                gap_queue._generic_mission_npc_proxy_tracking_contexts(
                    "dlg_future_1",
                    "future_mission",
                    {"npcProxyConsumers": [{
                        "npcProxyId": "proxy_future",
                        "levelId": "future_level",
                    }]},
                    corpus,
                )
            )
        self.assertEqual(contexts, [])
        self.assertEqual(len(failures), 1)
        failure = failures[0]
        self.assertEqual(
            failure["validator"],
            "genericMissionNpcProxyTrackingContext",
        )
        self.assertEqual(
            failure["gate"],
            "exactUnfilteredSingleMissionProxyTracking",
        )
        self.assertEqual(failure["storyKey"], "dlg_future_1")
        self.assertIn("sourceSha256", failure)

    def test_general_mission_tracking_census_has_no_per_dialog_declarations(
        self,
    ) -> None:
        for definition in (
            gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS.values()
        ):
            self.assertNotIn("missionNpcProxyTracking", definition)
        streaming_root = (
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Data/Json/"
            "MissionRuntimeAsset"
        )
        persistent_root = (
            gap_queue.ROOT
            / "export_full/structured/Persistent/Data/Json/"
            "MissionRuntimeAsset"
        )
        corpus = gap_queue._build_mission_npc_proxy_tracking_index(
            streaming_root,
            persistent_root,
        )
        self.assertEqual(corpus["status"], "active")
        self.assertEqual(corpus["selection"], "complete_persistent_override")
        self.assertEqual(corpus["scannedMissionFileCount"], 490)
        self.assertEqual(corpus["typedRowCount"], 839)
        self.assertEqual(corpus["qualifiedRowCount"], 781)
        npc_proxy_ex = gap_queue.read_json(
            gap_queue.ROOT
            / "export_full/structured/Persistent/Data/Json/GameplayConfig/"
            "NpcProxyExDataTable.json",
            {},
        )
        npc_proxy = gap_queue.read_json(
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Data/Json/GameplayConfig/"
            "NpcProxyTable.json",
            {},
        )
        dialog_index = gap_queue.read_json(
            gap_queue.ROOT
            / "export_full/recovered/dialog_id_table_index.json",
            {},
        )
        qualified_story_keys = []
        consumer_failures = []
        for story_key, definition in (
            gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS.items()
        ):
            facts, failure = (
                gap_queue._generic_missionless_npc_proxy_dialog_facts(
                    story_key,
                    npc_proxy_ex,
                    npc_proxy,
                    dialog_index,
                )
            )
            if failure is not None:
                consumer_failures.append(failure)
                continue
            contexts, failures = (
                gap_queue._generic_mission_npc_proxy_tracking_contexts(
                    story_key,
                    definition["missionId"],
                    facts,
                    corpus,
                )
            )
            self.assertEqual(failures, [])
            if contexts:
                qualified_story_keys.append(story_key)
                self.assertEqual(len(contexts), 1)
                self.assertEqual(
                    contexts[0]["questIds"],
                    sorted(contexts[0]["questIds"], key=gap_queue.natural_key),
                )
                self.assertTrue(contexts[0]["sourceSha256"])
        self.assertEqual(len(qualified_story_keys), 26)
        self.assertEqual(len(consumer_failures), 1)
        self.assertEqual(
            consumer_failures[0]["gate"],
            "exactNpcProxyConsumerIdentity",
        )

    def test_gm01m13_proxy_context_and_definition_frontier_is_exact(
        self,
    ) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Table"
        )
        index, status = gap_queue.build_offline_exhaustion_index(
            partial,
            table_root,
        )
        self.assertEqual(status["status"], "active")
        self.assertEqual(
            {
                key
                for key in gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS
                if "gm01m13" in key
            },
            {
                "dlg_gm01m13_2",
                "dlg_gm01m13_3",
                "dlg_gm01m13_5",
                "text_gm01m13_1",
            },
        )
        for story_key, entry_index in (
            ("dlg_gm01m13_2", 1),
            ("dlg_gm01m13_3", 2),
        ):
            evidence = index[story_key]
            self.assertEqual(
                evidence["evidenceKind"],
                "mission_tracked_npc_proxy_dialog_context_without_playback_owner",
            )
            self.assertEqual(
                evidence["npcProxyConsumer"]["proxyId"],
                "sesidun02_map01_001",
            )
            self.assertEqual(
                evidence["npcProxyConsumer"]["entryIndex"],
                entry_index,
            )
            self.assertEqual(
                evidence["missionNpcProxyTracking"]["questIds"],
                [
                    "gm01m13_q#1",
                    "gm01m13_q#2",
                    "gm01m13_q#3",
                    "gm01m13_q#4",
                    "gm01m13_q#7",
                    "gm01m13_q#8",
                    "gm01m13_q#9",
                    "gm01m13_q#11",
                    "gm01m13_q#12",
                ],
            )
            self.assertFalse(
                evidence["missionNpcProxyTracking"]["questPlaybackOwnership"]
            )
            self.assertEqual(
                evidence["dialogTreeBranchGroups"][0]["routeKind"],
                "authored_convergence",
            )
            topology = evidence["missionQuestTopologyContext"]
            self.assertEqual(
                topology["mainPathQuestIds"],
                [
                    "gm01m13_q#1",
                    "gm01m13_q#2",
                    "gm01m13_q#3",
                    "gm01m13_q#4",
                    "gm01m13_q#8",
                    "gm01m13_q#9",
                    "gm01m13_q#5",
                    "gm01m13_q#7",
                    "gm01m13_q#11",
                ],
            )
            self.assertEqual(
                topology["forks"],
                [{
                    "questId": "gm01m13_q#2",
                    "successorQuestIds": [
                        "gm01m13_q#3",
                        "gm01m13_q#12",
                    ],
                }],
            )
            self.assertEqual(
                topology["merges"],
                [{
                    "predecessorQuestIds": [
                        "gm01m13_q#3",
                        "gm01m13_q#12",
                    ],
                    "questId": "gm01m13_q#4",
                }],
            )
        self.assertEqual(
            index["dlg_gm01m13_5"]["dialogIdRegistrationStatus"],
            "absent",
        )
        self.assertEqual(
            len(index["dlg_gm01m13_5"]["optionRows"]),
            4,
        )
        self.assertEqual(
            index["text_gm01m13_1"]["readingPopupRowId"],
            "text_gm01m13_1",
        )

        declaration = (
            gap_queue.OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS[
                "gm01m13"
            ]
        )
        broken_predecessors = {
            **declaration["prevQuestIdsByQuest"],
            "gm01m13_q#4": ("gm01m13_q#3",),
        }
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS,
            {"gm01m13": {
                **declaration,
                "prevQuestIdsByQuest": broken_predecessors,
            }},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(
                    partial,
                    table_root,
                )
            )
        self.assertEqual(failed_index, {})
        failure = next(
            row
            for row in failed_status["validatorDiagnostics"]
            if row.get("mission") == "gm01m13"
        )
        self.assertEqual(failure["validator"], "offlineMissionTopologyContext")
        self.assertEqual(
            failure["gate"],
            "exactQuestPredecessorGraphMainPathStateDependenciesAndObjectiveConjunctions",
        )
        self.assertEqual(failure["mission"], "gm01m13")
        self.assertIn("sourceSha256", failure)

    def test_gm01m15_definition_frontier_and_topology_are_exact(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Table"
        )
        index, status = gap_queue.build_offline_exhaustion_index(
            partial,
            table_root,
        )
        self.assertEqual(status["status"], "active")
        self.assertEqual(
            {
                key
                for key in gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS
                if "gm01m15" in key
            },
            {"dlg_gm01m15_7", "text_gm01m15_1", "text_gm01m15_8"},
        )

        dialog = index["dlg_gm01m15_7"]
        self.assertEqual(
            dialog["evidenceKind"],
            "dialog_text_table_only_without_registry_asset_or_consumer",
        )
        self.assertEqual(len(dialog["lineIds"]), 11)
        self.assertEqual(len(dialog["missingAudioIds"]), 11)
        self.assertEqual(len(dialog["optionIds"]), 5)
        self.assertEqual(
            dialog["optionRouteStatus"],
            "definitions_present_route_unresolved",
        )
        self.assertEqual(
            dialog["summaryDefinition"],
            {
                "summaryId": "summary_gm01m15_7_001",
                "textId": "1386392558646000191",
                "relation": "dialog_summary_map_targets_dialog",
                "missionOwnership": False,
                "orderEvidence": False,
            },
        )
        self.assertNotIn("dialogTreeBranchGroups", dialog)

        text_one = index["text_gm01m15_1"]
        self.assertEqual(
            text_one["contentTextIds"],
            [
                8242330289792353294,
                -2455707730206541547,
                -2339893156956209480,
                119766408319964938,
                -8714781499976003721,
            ],
        )
        self.assertEqual(
            text_one["prtsDefinition"],
            {
                "rowId": "nar_digital_map01_research1_16_1",
                "firstLvId": "digital_map01_research1_16",
                "type": "text",
                "order": 1,
                "relation": "prts_archive_entry_targets_story",
                "missionOwnership": False,
                "orderEvidence": False,
            },
        )
        self.assertEqual(
            index["text_gm01m15_8"]["contentTextIds"],
            [6649389232287698087],
        )
        self.assertIsNone(index["text_gm01m15_8"]["prtsDefinition"])

        topology = dialog["missionQuestTopologyContext"]
        self.assertEqual(
            topology["mainPathQuestIds"],
            [
                "gm01m15_q#2", "gm01m15_q#3", "gm01m15_q#4",
                "gm01m15_q#6", "gm01m15_q#7", "gm01m15_q#8",
                "gm01m15_q#14", "gm01m15_q#5", "gm01m15_q#10",
                "gm01m15_q#11", "gm01m15_q#12",
            ],
        )
        self.assertEqual(
            topology["forks"],
            [{
                "questId": "gm01m15_q#3",
                "successorQuestIds": ["gm01m15_q#4", "gm01m15_q#13"],
            }],
        )
        self.assertEqual(
            topology["merges"],
            [{
                "predecessorQuestIds": ["gm01m15_q#4", "gm01m15_q#13"],
                "questId": "gm01m15_q#6",
            }],
        )
        self.assertEqual(
            topology["parallelRendezvous"],
            [{
                "forkQuestId": "gm01m15_q#3",
                "parallelQuestIds": ["gm01m15_q#4", "gm01m15_q#13"],
                "mergeQuestId": "gm01m15_q#6",
                "joinSemantics": "all_predecessor_quests_required",
                "playerChoice": False,
            }],
        )
        self.assertEqual(topology["storyAssignments"], [])
        self.assertFalse(topology["orderEvidence"])
        for story_key in ("dlg_gm01m15_7", "text_gm01m15_1", "text_gm01m15_8"):
            self.assertEqual(index[story_key]["graphEffect"], "none")

        definition = gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS[
            "dlg_gm01m15_7"
        ]
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS,
            {"dlg_gm01m15_7": {
                **definition,
                "summaryDefinition": {
                    **definition["summaryDefinition"],
                    "summaryId": "summary_gm01m15_7_changed",
                },
            }},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(partial, table_root)
            )
        self.assertEqual(failed_index, {})
        failure = next(
            row for row in failed_status["validatorDiagnostics"]
            if row.get("storyKey") == "dlg_gm01m15_7"
            and row.get("gate") == "exactDialogSummaryDefinition"
        )
        self.assertEqual(failure["validator"], "offlineTextOnlyDialogDefinition")
        self.assertIn("dialogSummaryMapTable", failure["sourceSha256"])
        self.assertIn("dialogSummaryTable", failure["sourceSha256"])

    def test_declared_gm01m7_branch_frontier_is_exact(self) -> None:
        story_keys = {
            "dlg_gm01m7_1",
            "dlg_gm01m7_2",
            "dlg_gm01m7_3",
            "dlg_gm01m7_5",
            "dlg_gm01m7_7",
            "radio_gm01m7_9",
            "sns_gm01m7_1",
            "sns_gm01m7_2",
            "text_gm01m7_1",
        }
        self.assertEqual(
            {
                key
                for key in gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS
                if "gm01m7" in key
            },
            story_keys,
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_GM01M7_RADIOS,
            {"radio_gm01m7_9"},
        )
        branch = gap_queue.OFFLINE_EXHAUSTION_MISSION_BRANCH_CONTEXTS[
            "gm01m7"
        ]
        self.assertEqual(
            branch["fork"],
            {
                "questId": "gm01m7_q#1",
                "successorQuestIds": (
                    "gm01m7_q#8",
                    "gm01m7_q#14",
                ),
            },
        )
        self.assertEqual(
            branch["merge"],
            {
                "predecessorQuestIds": (
                    "gm01m7_q#14",
                    "gm01m7_q#8",
                ),
                "questId": "gm01m7_q#9",
            },
        )
        self.assertEqual(
            branch["sharedTracking"]["proxyId"],
            "sesidun_map01_001",
        )
        self.assertEqual(
            len(
                gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
                    "dlg_gm01m7_1"
                ]["treeBranchGroups"]
            ),
            2,
        )
        for story_key in (
            "dlg_gm01m7_1",
            "dlg_gm01m7_2",
            "dlg_gm01m7_3",
            "dlg_gm01m7_5",
            "dlg_gm01m7_7",
        ):
            self.assertNotIn(
                "missionNpcProxyTracking",
                gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[story_key],
            )
        self.assertEqual(
            len(
                gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
                    "dlg_gm01m7_2"
                ]["npcProxyConsumers"]
            ),
            2,
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_SNS_DEFINITIONS[
                "sns_gm01m7_1"
            ]["runtimeTracking"]["questId"],
            "gm01m12_q#16",
        )
        self.assertEqual(
            len(
                gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS[
                    "text_gm01m7_1"
                ]["contentTextIds"]
            ),
            13,
        )

    def test_gm01m7_branch_and_cross_mission_sns_context_are_visible(
        self,
    ) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Table"
        )
        index, status = gap_queue.build_offline_exhaustion_index(
            partial,
            table_root,
        )
        self.assertEqual(status["status"], "active")
        context = index["dlg_gm01m7_1"]["missionQuestBranchContext"]
        self.assertEqual(
            context["fork"]["successorQuestIds"],
            ["gm01m7_q#8", "gm01m7_q#14"],
        )
        self.assertEqual(
            context["merge"]["predecessorQuestIds"],
            ["gm01m7_q#14", "gm01m7_q#8"],
        )
        self.assertEqual(context["storyArmAssignments"], [])
        self.assertEqual(
            context["storyArmAssignmentStatus"],
            "unresolved",
        )
        self.assertFalse(context["orderEvidence"])
        dialog_tracking = index["dlg_gm01m7_1"][
            "missionNpcProxyTracking"
        ]
        self.assertTrue(dialog_tracking["crossMission"])
        self.assertEqual(dialog_tracking["missionId"], "gm01m12")
        self.assertEqual(dialog_tracking["nominalMissionId"], "gm01m7")
        self.assertEqual(dialog_tracking["questIds"], ["gm01m12_q#14"])
        shared_dialog_tracking = index["dlg_gm01m7_7"][
            "missionNpcProxyTracking"
        ]
        self.assertEqual(
            shared_dialog_tracking["questIds"],
            [
                "gm01m12_q#2",
                "gm01m12_q#3",
                "gm01m12_q#4",
                "gm01m12_q#6",
                "gm01m12_q#12",
            ],
        )
        tracking = index["sns_gm01m7_1"]["runtimeTrackingContext"]
        self.assertEqual(tracking["runtimeMissionId"], "gm01m12")
        self.assertEqual(tracking["questId"], "gm01m12_q#16")
        self.assertFalse(tracking["playback"])
        self.assertFalse(tracking["nominalMissionOwnership"])

    def test_gm01m7_branch_context_validator_fails_closed(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Table"
        )
        declaration = gap_queue.OFFLINE_EXHAUSTION_MISSION_BRANCH_CONTEXTS[
            "gm01m7"
        ]
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_MISSION_BRANCH_CONTEXTS,
            {"gm01m7": {
                **declaration,
                "fork": {
                    **declaration["fork"],
                    "successorQuestIds": ("gm01m7_q#missing",),
                },
            }},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(
                    partial,
                    table_root,
                )
            )
        self.assertEqual(failed_index, {})
        failure = failed_status["validatorDiagnostics"][0]
        self.assertEqual(failure["validator"], "offlineMissionBranchContext")
        self.assertEqual(
            failure["gate"],
            "exactForkMergeAndSharedNpcTracking",
        )
        self.assertEqual(failure["mission"], "gm01m7")
        self.assertIn("sourceSha256", failure)

    def test_declared_gm01m12_linear_frontier_is_exact(self) -> None:
        story_keys = {
            "dlg_gm01m12_1",
            "dlg_gm01m12_3",
            "dlg_gm01m12_6",
            "dlg_gm01m12_8",
            "text_gm01m12_1",
            "text_gm01m12_3",
            "text_gm01m12_5",
            "text_gm01m12_6",
            "text_gm01m12_7",
        }
        self.assertEqual(
            {
                key
                for key in gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS
                if "gm01m12" in key
            },
            story_keys,
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_MISSION_LINEAR_CONTEXTS[
                "gm01m12"
            ]["questSequence"],
            tuple(
                f"gm01m12_q#{number}"
                for number in (15, 16, 13, 14, 1, 2, 3, 4, 12, 5, 6)
            ),
        )
        self.assertEqual(
            set(gap_queue.OFFLINE_EXHAUSTION_LEVELSCRIPT_TASK_CONSUMERS),
            {"dlg_gm01m12_1", "dlg_gm01m12_3"},
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_LEVELSCRIPT_TASK_CONSUMERS[
                "dlg_gm01m12_1"
            ]["postDialogAction"]["actionName"],
            "BlackScreenFadeInAndOut",
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS[
                "text_gm01m12_5"
            ]["richContentStatus"],
            "absent",
        )

    def test_gm01m12_linear_and_task_context_are_visible(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Table"
        )
        index, status = gap_queue.build_offline_exhaustion_index(
            partial,
            table_root,
        )
        self.assertEqual(status["status"], "active")
        row = index["dlg_gm01m12_1"]
        sequence = row["missionQuestSequenceContext"]
        self.assertEqual(len(sequence["questSequence"]), 11)
        self.assertEqual(sequence["forkQuestIds"], [])
        self.assertEqual(sequence["mergeQuestIds"], [])
        self.assertEqual(sequence["storyAssignments"], [])
        self.assertFalse(sequence["orderEvidence"])
        consumer = row["levelScriptTaskConsumer"]
        self.assertEqual(consumer["conditionType"], "CheckTalkOptionFinish")
        self.assertEqual(consumer["finishId"], -1)
        self.assertFalse(consumer["playback"])
        self.assertFalse(consumer["missionOwnership"])
        self.assertEqual(
            consumer["postDialogAction"]["actionName"],
            "BlackScreenFadeInAndOut",
        )
        self.assertEqual(
            index["text_gm01m12_3"]["prtsReadingDefinition"]["rowId"],
            "term_001_gm01m7",
        )

    def test_gm01m12_linear_context_validator_fails_closed(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Table"
        )
        declaration = gap_queue.OFFLINE_EXHAUSTION_MISSION_LINEAR_CONTEXTS[
            "gm01m12"
        ]
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_MISSION_LINEAR_CONTEXTS,
            {"gm01m12": {
                **declaration,
                "questSequence": (*declaration["questSequence"][:-1], "gm01m12_q#missing"),
            }},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(partial, table_root)
            )
        self.assertEqual(failed_index, {})
        failure = failed_status["validatorDiagnostics"][0]
        self.assertEqual(failure["validator"], "offlineMissionLinearContext")
        self.assertEqual(
            failure["gate"],
            "exactSinglePredecessorQuestSequence",
        )
        self.assertEqual(failure["mission"], "gm01m12")
        self.assertIn("sourceSha256", failure)

    def test_gm01m12_levelscript_task_validator_fails_closed(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Table"
        )
        declaration = gap_queue.OFFLINE_EXHAUSTION_LEVELSCRIPT_TASK_CONSUMERS[
            "dlg_gm01m12_1"
        ]
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_LEVELSCRIPT_TASK_CONSUMERS,
            {"dlg_gm01m12_1": {
                **declaration,
                "conditionKey": "changed",
            }},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(partial, table_root)
            )
        self.assertEqual(failed_index, {})
        failure = failed_status["validatorDiagnostics"][0]
        self.assertEqual(
            failure["validator"],
            "offlineLevelScriptTaskConsumer",
        )
        self.assertEqual(
            failure["gate"],
            "exactLevelScriptTalkCompletionConsumer",
        )
        self.assertEqual(failure["storyKey"], "dlg_gm01m12_1")
        self.assertIn("sourceSha256", failure)

    def test_gm02m20_retired_radios_and_auxiliary_topology_are_exact(
        self,
    ) -> None:
        story_keys = {
            "radio_gm02m20_7",
            "radio_gm02m20_8",
            "radio_gm02m20_10",
            "radio_gm02m20_11",
            "radio_gm02m20_13",
        }
        self.assertEqual(
            story_keys,
            gap_queue.OFFLINE_EXHAUSTION_GM02M20_RADIOS,
        )
        self.assertEqual(
            story_keys,
            {
                key
                for key in gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS
                if "gm02m20" in key
            },
        )
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT / "export_full/structured/StreamingAssets/Table"
        )
        index, status = gap_queue.build_offline_exhaustion_index(
            partial,
            table_root,
        )
        self.assertEqual("active", status["status"])
        self.assertTrue(story_keys <= set(index))
        topology = index["radio_gm02m20_7"][
            "missionQuestTopologyContext"
        ]
        self.assertEqual(
            [
                "gm02m20_q#1", "gm02m20_q#2", "gm02m20_q#10",
                "gm02m20_q#11", "gm02m20_q#3", "gm02m20_q#6",
                "gm02m20_q#4", "gm02m20_q#7", "gm02m20_q#5",
                "gm02m20_q#8",
            ],
            topology["mainPathQuestIds"],
        )
        self.assertEqual(
            ["gm02m20_q#1", "gm02m20_q#9"],
            topology["entryQuestIds"],
        )
        self.assertEqual([], topology["forks"])
        self.assertEqual([], topology["merges"])
        self.assertEqual(
            [{
                "questId": "gm02m20_q#9",
                "objectiveIndex": 1,
                "targetQuestId": "gm02m20_q#1",
                "comparer": 0,
                "targetQuestState": 3,
                "scopeMask": 1,
                "useGraphScope": True,
            }],
            topology["questStateDependencies"],
        )
        self.assertEqual([], topology["storyAssignments"])
        self.assertFalse(topology["orderEvidence"])

    def test_gm01m3_original_context_and_definition_frontier_is_exact(
        self,
    ) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_GM01M3_RADIOS,
            {"radio_gm01m3_3d8"},
        )
        self.assertEqual(
            {
                key
                for key in gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS
                if "gm01m3" in key
            },
            {
                "misc_dlg_gm01m3_1d5",
                "radio_gm01m3_3d2",
                "radio_gm01m3_3d8",
                "sns_gm01m3_1",
            },
        )
        dialog = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "misc_dlg_gm01m3_1d5"
        ]
        self.assertEqual(
            dialog["lineIds"],
            ("dlg_gm01m3_1d5_001", "dlg_gm01m3_1d5_002"),
        )
        self.assertEqual(dialog["optionIds"], ())

        table_root = (
            gap_queue.ROOT / "export_full/structured/StreamingAssets/Table"
        )
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        offline_index, status = gap_queue.build_offline_exhaustion_index(
            partial,
            table_root,
            native_playback_index=(
                build_levelscript_native_story_playback_index()
            ),
            action_story_occurrences=(
                build_levelscript_action_story_occurrences()
            ),
        )
        self.assertEqual("active", status["status"])
        generic_cutscene = offline_index["cutscene_gm02m10_1"]
        self.assertEqual(
            generic_cutscene["evidenceKind"],
            "cutscene_root_without_recovered_activator",
        )
        self.assertEqual(generic_cutscene["timelineRegistryId"], 402)
        self.assertEqual(generic_cutscene["graphEffect"], "none")
        cutscene_status = status["genericCutsceneDefinitionEvidence"]
        self.assertEqual(cutscene_status["validationFailures"], [])
        self.assertEqual(cutscene_status["qualifiedStoryKeys"], 33)
        root_alias = offline_index["cutscene_f1m9d3_1"]
        playable_alias = offline_index["cutscene_f1m9d4_1"]
        self.assertEqual(root_alias["cutsceneAliasRole"], "cutscene_root")
        self.assertEqual(
            playable_alias["cutsceneAliasRole"],
            "playable_timeline_asset",
        )
        self.assertEqual(
            root_alias["rootPlaybackAlias"],
            playable_alias["rootPlaybackAlias"],
        )
        self.assertIn(
            "VFS/7064D8E2/98E51B76A48F5BEF8D07BDFD3E4DA7ED.chk",
            root_alias["originalGameFiles"],
        )
        map_cutscene = offline_index[
            "cutscene_map02_lv001_TSZ_01_3_copy"
        ]
        self.assertTrue(map_cutscene["embeddedRootGraph"])
        self.assertEqual(map_cutscene["gameObjectRowCount"], 0)
        self.assertEqual(map_cutscene["directorHostCount"], 1)
        invalid_graph = next(
            row
            for row in cutscene_status["qualificationDiagnostics"]
            if row.get("storyKey") == "cutscene_gm02m4_1"
        )
        self.assertEqual(
            invalid_graph["gate"],
            "exactDefinitionRootDirectorGraph",
        )
        self.assertEqual(
            invalid_graph["actual"]["directorHosts"],
            2,
        )
        self.assertFalse(
            invalid_graph["actual"]["directorGraphValid"],
        )
        registered_tree_status = status[
            "genericRegisteredDialogTreeNegativeConsumerEvidence"
        ]
        self.assertEqual(registered_tree_status["validationFailures"], [])
        self.assertGreaterEqual(registered_tree_status["qualifiedStoryKeys"], 375)
        self.assertEqual(
            offline_index["dlg_c27m4_15"]["evidenceKind"],
            "registered_dialog_tree_definition_binary_consumer_surface_exhausted",
        )
        self.assertEqual(offline_index["dlg_c27m4_15"]["graphEffect"], "none")
        missionless_native_status = status[
            "genericMissionlessNativePlaybackEvidence"
        ]
        self.assertEqual(missionless_native_status["validationFailures"], [])
        self.assertEqual(missionless_native_status["qualifiedStoryKeys"], 338)
        missionless_dialog = offline_index["dlg_c13m2_9"]
        self.assertEqual(
            missionless_dialog["evidenceKind"],
            "exact_missionless_native_event_playback_path",
        )
        self.assertEqual(
            missionless_dialog["recoveryStatus"],
            "deferred_exact_native_playback_without_mission_bridge",
        )
        self.assertFalse(missionless_dialog["missionOwnership"])
        self.assertTrue(missionless_dialog["nativeEventPaths"])
        c6_text_only = offline_index["cutscene_c6m1_1"]
        self.assertEqual(
            c6_text_only["evidenceKind"],
            "text_table_only_cutscene_without_recovered_original_story_consumer",
        )
        self.assertEqual(
            c6_text_only["definitionRowKeys"],
            ["cutscene_c6m1_1_02", "cutscene_c6m1_1_03"],
        )
        registered_table_status = status[
            "genericRegisteredTableDialogNegativeConsumerEvidence"
        ]
        self.assertEqual(registered_table_status["validationFailures"], [])
        self.assertEqual(
            offline_index["misc_dlg_c6m1_1d5"]["definitionRootKey"],
            "dlg_c6m1_1d5",
        )
        self.assertEqual(
            offline_index["misc_dlg_c6m1_1d5"]["evidenceKind"],
            "registered_dialog_tree_definition_binary_consumer_surface_exhausted",
        )
        self.assertEqual(
            offline_index["sns_gm01m3_1"]["relatedMissionId"],
            "gm01m3",
        )
        self.assertEqual(
            offline_index["sns_gm01m3_1"][
                "linkMissionIdsByContentId"
            ],
            {"4": "gm01m3"},
        )

        gm01m3 = gap_queue.read_json(
            gap_queue.ROOT / "webui/data/lang/CN/mission/gm01m3.json",
            {},
        )
        sns_rows = gap_queue._closed_exact_runtime_config_isolated_scenes(
            gm01m3["flow"],
            {"sns_gm01m3_1"},
            "gm01m3",
            offline_index,
        )
        self.assertEqual(
            [row["recoveryStatus"] for row in sns_rows],
            ["closed_exact_authored_sns_mission_link_no_relative_order"],
        )
        self.assertEqual(
            gap_queue._closed_exact_runtime_config_isolated_scenes(
                gm01m3["flow"],
                {"sns_gm01m3_1"},
                "gm01m3",
                {},
            ),
            [],
        )

        gm02m11 = gap_queue.read_json(
            gap_queue.ROOT / "webui/data/lang/CN/mission/gm02m11.json",
            {},
        )
        authored_sns_rows = (
            gap_queue._closed_exact_runtime_config_isolated_scenes(
                gm02m11["flow"],
                {"sns_gm02m11_1"},
                "gm02m11",
                offline_index,
            )
        )
        self.assertEqual(
            authored_sns_rows[0]["sourceFiles"],
            [
                "export_full/structured/StreamingAssets/Table/"
                "SNSDialogTable.json",
                "export_full/structured/StreamingAssets/Table/"
                "SNSDialogOptionTable.json",
                "export_full/structured/StreamingAssets/Table/"
                "SNSChatTable.json",
            ],
        )

        gm01m4 = gap_queue.read_json(
            gap_queue.ROOT / "webui/data/lang/CN/mission/gm01m4.json",
            {},
        )
        connection = next(
            row
            for row in gm01m4["flow"]["missionStoryConnections"]
            if row.get("key") == "radio_gm01m3_3d2"
        )
        native_rows = gap_queue._closed_exact_native_context_isolated_scenes(
            {"missionStoryConnections": [connection]},
            {"radio_gm01m3_3d2"},
            "gm01m3",
        )
        self.assertEqual(
            native_rows[0]["recoveryStatus"],
            "closed_exact_cross_mission_leveldata_shell_playback_context_no_relative_order",
        )
        self.assertEqual(native_rows[0]["contextMissionId"], "gm01m4")
        invalid = copy.deepcopy(connection)
        invalid["levelScriptOccurrences"][0][
            "authoritativeScopeLevelDataHosts"
        ][0]["dictionaryEntryCount"] = 13
        self.assertEqual(
            gap_queue._closed_exact_native_context_isolated_scenes(
                {"missionStoryConnections": [invalid]},
                {"radio_gm01m3_3d2"},
                "gm01m3",
            ),
            [],
        )

    def test_gm01m17_retired_definitions_and_nested_topology_are_exact(
        self,
    ) -> None:
        radio_keys = {
            "radio_gm01m17_4",
            "radio_gm01m17_5",
            "radio_gm01m17_9",
        }
        self.assertEqual(
            radio_keys,
            gap_queue.OFFLINE_EXHAUSTION_GM01M17_RADIOS,
        )
        self.assertEqual(
            radio_keys | {"text_gm01m17_1"},
            {
                key
                for key in gap_queue.OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS
                if "gm01m17" in key
            },
        )
        self.assertEqual(
            {
                "missionId": "gm01m17",
                "readingPopupRowId": "text_gm01m17_1",
                "bgType": 2,
                "iconType": 0,
                "titleId": -5216252211990160921,
                "contentTextIds": (
                    2833540280945742009,
                    -8531949106363903611,
                ),
            },
            gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS[
                "text_gm01m17_1"
            ],
        )
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT / "export_full/structured/StreamingAssets/Table"
        )
        index, status = gap_queue.build_offline_exhaustion_index(
            partial,
            table_root,
        )
        self.assertEqual("active", status["status"])
        self.assertTrue(radio_keys | {"text_gm01m17_1"} <= set(index))
        topology = index["radio_gm01m17_4"][
            "missionQuestTopologyContext"
        ]
        self.assertEqual(
            [
                "gm01m17_q#1", "gm01m17_q#2", "gm01m17_q#13",
                "gm01m17_q#14", "gm01m17_q#16", "gm01m17_q#18",
            ],
            topology["mainPathQuestIds"],
        )
        self.assertEqual(8, len(topology["entryQuestIds"]))
        self.assertEqual(3, len(topology["forks"]))
        self.assertEqual([], topology["merges"])
        self.assertEqual(12, len(topology["terminalQuestIds"]))
        self.assertEqual(4, len(topology["questStateDependencies"]))
        self.assertEqual(
            {(0, 1), (1, 1), (2, 1)},
            {
                tuple(row["conditionIndexPath"])
                for row in topology["questStateDependencies"]
                if row["questId"] == "gm01m17_q#3"
            },
        )
        self.assertEqual(
            [{
                "questId": "gm01m17_q#13",
                "conditionType": "CheckQuestState",
                "targetQuestId": "gm01m17_q#3",
                "comparer": 0,
                "targetQuestState": 3,
                "relation": "authored_quest_failure_guard",
                "branchExclusivityStatus": (
                    "not_proven_by_one_way_failure_guard"
                ),
                "storyOrderEvidence": False,
            }],
            topology["failedQuestStateGuards"],
        )
        self.assertEqual([], topology["storyAssignments"])
        self.assertFalse(topology["orderEvidence"])

    def test_gm01m17_nested_topology_validator_fails_closed(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT / "export_full/structured/StreamingAssets/Table"
        )
        declaration = gap_queue.OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS[
            "gm01m17"
        ]
        broken_dependencies = copy.deepcopy(
            declaration["questStateDependenciesByQuest"]
        )
        broken_dependencies["gm01m17_q#3"][1][
            "targetQuestId"
        ] = "gm01m17_q#missing"
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS,
            {"gm01m17": {
                **declaration,
                "questStateDependenciesByQuest": broken_dependencies,
            }},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(
                    partial,
                    table_root,
                )
            )
        self.assertEqual({}, failed_index)
        failure = failed_status["validatorDiagnostics"][0]
        self.assertEqual("offlineMissionTopologyContext", failure["validator"])
        self.assertEqual(
            "exactQuestPredecessorGraphMainPathStateDependenciesAndObjectiveConjunctions",
            failure["gate"],
        )
        self.assertEqual("gm01m17", failure["mission"])
        expected = failure["expected"]["questStateDependenciesByQuest"]
        actual = failure["actual"]["questStateDependenciesByQuest"]
        self.assertEqual(
            "gm01m17_q#missing",
            expected["gm01m17_q#3"][1]["targetQuestId"],
        )
        self.assertEqual(
            "gm01m17_q#13",
            actual["gm01m17_q#3"][1]["targetQuestId"],
        )
        self.assertEqual(
            (1, 1),
            actual["gm01m17_q#3"][1]["conditionIndexPath"],
        )

    def test_gm02m20_auxiliary_topology_validator_fails_closed(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT / "export_full/structured/StreamingAssets/Table"
        )
        declaration = gap_queue.OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS[
            "gm02m20"
        ]
        broken_dependencies = copy.deepcopy(
            declaration["questStateDependenciesByQuest"]
        )
        broken_dependencies["gm02m20_q#9"][0][
            "targetQuestId"
        ] = "gm02m20_q#missing"
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS,
            {"gm02m20": {
                **declaration,
                "questStateDependenciesByQuest": broken_dependencies,
            }},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(
                    partial,
                    table_root,
                )
            )
        self.assertEqual({}, failed_index)
        failure = failed_status["validatorDiagnostics"][0]
        self.assertEqual(
            "offlineMissionTopologyContext",
            failure["validator"],
        )
        self.assertEqual(
            "exactQuestPredecessorGraphMainPathStateDependenciesAndObjectiveConjunctions",
            failure["gate"],
        )
        self.assertEqual("gm02m20", failure["mission"])
        self.assertEqual(
            "gm02m20_q#missing",
            failure["expected"]["questStateDependenciesByQuest"]
            ["gm02m20_q#9"][0]["targetQuestId"],
        )
        self.assertEqual(
            "gm02m20_q#1",
            failure["actual"]["questStateDependenciesByQuest"]
            ["gm02m20_q#9"][0]["targetQuestId"],
        )

    def test_gm01m16_exact_topology_is_visible_without_story_assignment(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = gap_queue.ROOT / "export_full/structured/StreamingAssets/Table"
        index, status = gap_queue.build_offline_exhaustion_index(partial, table_root)
        self.assertEqual("active", status["status"])
        topology = index["radio_gm01m16_8"]["missionQuestTopologyContext"]
        self.assertEqual(26, len(
            gap_queue.OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS[
                "gm01m16"
            ]["prevQuestIdsByQuest"]
        ))
        self.assertEqual(2, len(topology["entryQuestIds"]))
        self.assertEqual(5, len(topology["forks"]))
        self.assertEqual(4, len(topology["merges"]))
        self.assertEqual(8, len(topology["terminalQuestIds"]))
        self.assertEqual(12, len(topology["mainPathQuestIds"]))
        self.assertEqual([], topology["storyAssignments"])
        self.assertFalse(topology["orderEvidence"])
        self.assertEqual("not_evidence", topology["flowIndexExclusivityStatus"])

    def test_gm01m16_topology_validator_fails_closed(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = gap_queue.ROOT / "export_full/structured/StreamingAssets/Table"
        declaration = gap_queue.OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS[
            "gm01m16"
        ]
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS,
            {"gm01m16": {
                **declaration,
                "mainPathQuestIds": (*declaration["mainPathQuestIds"][:-1], "gm01m16_q#missing"),
            }},
        ):
            failed_index, failed_status = gap_queue.build_offline_exhaustion_index(
                partial,
                table_root,
            )
        self.assertEqual({}, failed_index)
        failure = failed_status["validatorDiagnostics"][0]
        self.assertEqual("offlineMissionTopologyContext", failure["validator"])
        self.assertEqual(
            "exactQuestPredecessorGraphMainPathStateDependenciesAndObjectiveConjunctions",
            failure["gate"],
        )
        self.assertEqual("gm01m16", failure["mission"])
        self.assertIn("sourceSha256", failure)

    def test_gm01m20_exact_fork_and_main_path_are_visible(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT / "export_full/structured/StreamingAssets/Table"
        )
        index, status = gap_queue.build_offline_exhaustion_index(
            partial,
            table_root,
        )
        self.assertEqual("active", status["status"])
        topology = index["radio_gm01m20_1"]["missionQuestTopologyContext"]
        self.assertEqual(["gm01m20_q#7"], topology["entryQuestIds"])
        self.assertEqual([
            "gm01m20_q#7", "gm01m20_q#1", "gm01m20_q#6",
            "gm01m20_q#3", "gm01m20_q#4", "gm01m20_q#2",
        ], topology["mainPathQuestIds"])
        self.assertEqual([{
            "questId": "gm01m20_q#4",
            "successorQuestIds": ["gm01m20_q#2", "gm01m20_q#10"],
        }], topology["forks"])
        self.assertEqual([], topology["merges"])
        self.assertEqual(
            {"gm01m20_q#2", "gm01m20_q#10"},
            set(topology["terminalQuestIds"]),
        )
        self.assertEqual([], topology["storyAssignments"])
        self.assertEqual(
            "not_serialized_in_client_asset",
            topology["serverSuccessorSelectionStatus"],
        )

    def test_gm01m7_cross_mission_sns_validator_fails_closed(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Table"
        )
        story_key = "sns_gm01m7_1"
        definition = gap_queue.OFFLINE_EXHAUSTION_SNS_DEFINITIONS[story_key]
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_SNS_DEFINITIONS,
            {story_key: {
                **definition,
                "runtimeTracking": {
                    **definition["runtimeTracking"],
                    "questId": "gm01m12_q#missing",
                },
            }},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(
                    partial,
                    table_root,
                )
            )
        self.assertEqual(failed_index, {})
        failure = next(
            row
            for row in failed_status["validatorDiagnostics"]
            if row.get("storyKey") == story_key
        )
        self.assertEqual(failure["validator"], "offline_sns_definition")
        self.assertEqual(
            failure["gate"],
            "exactCrossMissionSnsTrackingContext",
        )
        self.assertEqual(failure["mission"], "gm01m12")
        self.assertIn("sourceSha256", failure)

    def test_gm01m22_dialog_tree_branches_are_exact_and_fail_closed(self) -> None:
        definition_root = (
            gap_queue.ROOT
            / "export_full/recovered/AnimeStudio-cli/StreamingAssets/"
              "json_by_type/TextAsset"
        )
        expected = {
            "dlg_gm01m22_6": [{
                "optionGroup": 3,
                "optionIds": [
                    "option_dlg_gm01m22_6_3_001",
                    "option_dlg_gm01m22_6_3_002",
                    "option_dlg_gm01m22_6_3_003",
                ],
                "targetLineIds": [
                    "dlg_gm01m22_6_007",
                    "dlg_gm01m22_6_009",
                    "dlg_gm01m22_6_012",
                ],
                "routeKind": "authored_split",
            }],
            "dlg_gm01m22_8": [{
                "optionGroup": 6,
                "optionIds": [
                    "option_dlg_gm01m22_8_6_001",
                    "option_dlg_gm01m22_8_6_002",
                ],
                "targetLineIds": [
                    "dlg_gm01m22_8_019",
                    "dlg_gm01m22_8_019",
                ],
                "routeKind": "authored_convergence",
            }, {
                "optionGroup": 9,
                "optionIds": [
                    "option_dlg_gm01m22_8_9_001",
                    "option_dlg_gm01m22_8_9_002",
                    "option_dlg_gm01m22_8_9_003",
                ],
                "targetLineIds": [
                    "dlg_gm01m22_8_026",
                    "dlg_gm01m22_8_028",
                    "dlg_gm01m22_8_031",
                ],
                "routeKind": "authored_split",
            }],
        }
        for story_key, groups in expected.items():
            definition = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
                story_key
            ]
            asset = gap_queue.read_json(
                definition_root / definition["filename"],
                {},
            )
            self.assertEqual(
                gap_queue._dialog_tree_branch_groups(asset),
                groups,
            )

        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Table"
        )
        definition = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_gm01m22_6"
        ]
        broken_groups = list(definition["treeBranchGroups"])
        broken_groups[0] = {
            **broken_groups[0],
            "targetLineIds": ("dlg_gm01m22_6_007",) * 3,
        }
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS,
            {"dlg_gm01m22_6": {
                **definition,
                "treeBranchGroups": broken_groups,
            }},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(
                    partial,
                    table_root,
                )
            )
        self.assertEqual(failed_index, {})
        failure = next(
            row for row in failed_status["validatorDiagnostics"]
            if row["storyKey"] == "dlg_gm01m22_6"
        )
        self.assertEqual(failure["validator"], "offlineDialogDefinition")
        self.assertEqual(failure["gate"], "exactRegisteredDialogDefinition")
        self.assertNotEqual(
            failure["expected"]["treeBranchGroups"],
            failure["actual"]["treeBranchGroups"],
        )

    def test_gm01m2_result_and_internal_dialog_branches_are_exact(self) -> None:
        root = (
            gap_queue.ROOT
            / "export_full/recovered/AnimeStudio-cli/StreamingAssets/"
              "json_by_type/TextAsset"
        )
        definitions = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS
        assets = {
            key: gap_queue.read_json(root / definitions[key]["filename"], {})
            for key in ("dlg_gm01m2_1", "dlg_gm01m2_2", "dlg_gm01m2_3")
        }
        self.assertEqual(
            gap_queue._dialog_tree_branch_groups(assets["dlg_gm01m2_1"]),
            [{
                "optionGroup": 1,
                "optionIds": [
                    f"option_dlg_gm01m2_1_1_{number:03d}"
                    for number in range(1, 5)
                ],
                "targetLineIds": [
                    "dlg_gm01m2_1_003", "dlg_gm01m2_1_004",
                    "dlg_gm01m2_1_005", "dlg_gm01m2_1_009",
                ],
                "routeKind": "authored_split",
            }],
        )
        success_routes = gap_queue._dialog_tree_terminal_option_routes(
            assets["dlg_gm01m2_2"]
        )
        failure_routes = gap_queue._dialog_tree_terminal_option_routes(
            assets["dlg_gm01m2_3"]
        )
        self.assertEqual(
            [row["finishId"] for row in success_routes[0]["routes"]],
            [1, None],
        )
        self.assertEqual(
            failure_routes[0]["routes"][1]["optionId"],
            "option_dlg_gm01m2_2_1_002",
        )
        declaration = (
            gap_queue.OFFLINE_EXHAUSTION_LEVELDATA_DIALOG_BRANCH_CONTEXTS[
                "gm01m2"
            ]
        )
        self.assertEqual(declaration["propertyCount"], 38)
        self.assertEqual(
            tuple(
                (row["value"], row["propertyPath"])
                for row in declaration["resultSwitch"]["cases"]
            ),
            ((8, "succeed_dialog"), (9, "failed_dialog")),
        )

    def test_dialog_tree_idless_non_actor_node_fails_closed(self) -> None:
        definition = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_gm01m2_1"
        ]
        path = (
            gap_queue.ROOT
            / "export_full/recovered/AnimeStudio-cli/StreamingAssets/"
              "json_by_type/TextAsset"
            / definition["filename"]
        )
        asset = gap_queue.read_json(path, {})
        payload = json.loads(
            base64.b64decode(asset["m_Script"]).decode("utf-8-sig")
        )
        payload["nodes"][0].pop("$id")
        broken = {
            **asset,
            "m_Script": base64.b64encode(
                json.dumps(payload).encode("utf-8")
            ).decode("ascii"),
        }
        self.assertIsNone(gap_queue._dialog_tree_branch_groups(broken))
        self.assertIsNone(
            gap_queue._dialog_tree_terminal_option_routes(broken)
        )

    def test_gm01m2_leveldata_property_count_fails_closed(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Table"
        )
        contexts = (
            gap_queue.OFFLINE_EXHAUSTION_LEVELDATA_DIALOG_BRANCH_CONTEXTS
        )
        declaration = contexts["gm01m2"]
        with patch.dict(
            contexts,
            {"gm01m2": {**declaration, "propertyCount": 37}},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(partial, table_root)
            )
        self.assertEqual(failed_index, {})
        failure = next(
            row for row in failed_status["validatorDiagnostics"]
            if row.get("mission") == "gm01m2"
        )
        self.assertEqual(
            failure["validator"],
            "offlineLevelDataDialogBranchContext",
        )
        self.assertEqual(failure["actual"]["propertyCount"], 38)

    def test_gm02m23_dialog_tree_convergence_and_terminal_routes_are_exact(self) -> None:
        definition_root = (
            gap_queue.ROOT
            / "export_full/recovered/AnimeStudio-cli/StreamingAssets/"
              "json_by_type/TextAsset"
        )
        definition = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_gm02m23_3"
        ]
        asset = gap_queue.read_json(
            definition_root / definition["filename"],
            {},
        )

        self.assertEqual(
            gap_queue._dialog_tree_branch_groups(asset),
            [{
                "optionGroup": 4,
                "optionIds": [
                    "option_dlg_gm02m23_3_4_001",
                    "option_dlg_gm02m23_3_4_002",
                ],
                "targetLineIds": [
                    "dlg_gm02m23_3_023",
                    "dlg_gm02m23_3_023",
                ],
                "routeKind": "authored_convergence",
            }, {
                "optionGroup": 5,
                "optionIds": [
                    "option_dlg_gm02m23_3_5_001",
                    "option_dlg_gm02m23_3_5_002",
                ],
                "targetLineIds": [
                    "dlg_gm02m23_3_024",
                    "dlg_gm02m23_3_024",
                ],
                "routeKind": "authored_convergence",
            }],
        )
        self.assertEqual(
            gap_queue._dialog_tree_terminal_option_routes(asset),
            [{
                "optionGroup": 6,
                "routes": [{
                    "optionId": "option_dlg_gm02m23_3_6_001",
                    "targetKind": "finish",
                    "finishId": None,
                    "finishIdSerialized": False,
                }, {
                    "optionId": "option_dlg_gm02m23_3_6_002",
                    "targetKind": "finish",
                    "finishId": 1,
                    "finishIdSerialized": True,
                }],
            }],
        )

    def test_gm02m2_table_only_registration_validator_fails_closed(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Table"
        )
        definition = gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS[
            "dlg_gm02m2_2"
        ]
        incomplete_options = dict(definition["optionRows"])
        incomplete_options.pop("option_dlg_gm02m2_2_1_002")
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS,
            {"dlg_gm02m2_2": {
                **definition,
                "optionRows": incomplete_options,
            }},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(
                    partial,
                    table_root,
                )
            )
        self.assertEqual(failed_index, {})
        failure = next(
            row for row in failed_status["validatorDiagnostics"]
            if row["storyKey"] == "dlg_gm02m2_2"
            and row["gate"] == "exactTableOnlyDialogIdRegistration"
        )
        self.assertEqual(failure["validator"], "offlineTextOnlyDialogDefinition")
        self.assertEqual(failure["missionId"], "gm02m2")
        self.assertEqual(failure["expected"]["optionCount"], 1)
        self.assertEqual(failure["actual"]["optionCount"], 2)
        self.assertIn("dialogIdSource", failure["sourceSha256"])
        self.assertIn("dialogIdIndex", failure["sourceSha256"])

    def test_gm02m3_printable_only_tokens_fail_closed(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Table"
        )
        definition = gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS[
            "dlg_gm02m3_1"
        ]
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS,
            {"dlg_gm02m3_1": {
                **definition,
                "printableOnlyDialogTokens": (
                    "dlg_gm02m3_1X",
                    "dlg_gm02m3_not_an_original_token",
                ),
            }},
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(
                    partial,
                    table_root,
                )
            )
        self.assertEqual(failed_index, {})
        failure = next(
            row for row in failed_status["validatorDiagnostics"]
            if row["storyKey"] == "dlg_gm02m3_1"
            and row["gate"] == "exactPrintableOnlyDialogTokens"
        )
        self.assertEqual(failure["missionId"], "gm02m3")
        self.assertIsNone(
            failure["actual"]["dlg_gm02m3_not_an_original_token"]
        )
        self.assertIn("dialogIdSource", failure["sourceSha256"])
        self.assertIn("dialogIdIndex", failure["sourceSha256"])

    def test_offline_table_only_options_leave_routes_visible_but_deferred(self) -> None:
        partial = partial_mission(
            "gm02m2",
            scenes=["dlg_gm02m2_2"],
            isolated=["dlg_gm02m2_2"],
            no_route_groups=1,
        )
        partial["summary"].update({
            "branchingNoExplicitRouteGroupCount": 1,
            "singleOptionNoExplicitRouteGroupCount": 0,
        })
        partial["branches"] = {
            "branchingNoExplicitRouteGroups": [{
                "storyKey": "dlg_gm02m2_2",
                "group": 1,
                "options": [
                    {"optionId": "option_dlg_gm02m2_2_1_001"},
                    {"optionId": "option_dlg_gm02m2_2_1_002"},
                ],
            }],
        }
        recovery = {
            "sceneKey": "dlg_gm02m2_2",
            "missionId": "gm02m2",
            "recoveryStatus":
                "deferred_current_build_offline_surface_exhausted",
            "optionRouteStatus": "definitions_present_route_unresolved",
            "optionIds": [
                "option_dlg_gm02m2_2_1_001",
                "option_dlg_gm02m2_2_1_002",
            ],
            "evidenceKind":
                "registered_dialog_table_rows_without_tree_asset_or_consumer",
            "consumerBoundary": "fixture exact-build boundary",
            "graphEffect": "none",
        }
        row = gap_queue.build_gap_row(
            partial,
            mission_payload(),
            mission_bundle_exists=True,
            offline_exhaustion_index={"dlg_gm02m2_2": recovery},
        )
        self.assertEqual(
            row["metrics"]["actionableNoExplicitOptionRouteGroups"],
            0,
        )
        self.assertEqual(
            row["metrics"]["deferredOfflineExhaustedOptionRouteGroups"],
            1,
        )
        self.assertEqual(
            row["deferredOfflineExhaustedOptionRouteGroups"][0]["optionIds"],
            recovery["optionIds"],
        )
        self.assertEqual(
            row["deferredOfflineExhaustedOptionRouteGroups"][0]["graphEffect"],
            "none",
        )

    def test_a1m8d1_sns_branch_validator_reports_exact_failure(self) -> None:
        partial = gap_queue.read_json(
            gap_queue.ROOT
            / "reports/mission_order/source_story_partial_order_CN.json",
            {},
        )
        table_root = (
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Table"
        )
        definition = gap_queue.OFFLINE_EXHAUSTION_SNS_DEFINITIONS[
            "sns_a1m8d1_1"
        ]
        self.assertEqual(
            definition["optionNextContentIds"][
                "option_sns_a1m8d1_1_2_002"
            ],
            10,
        )
        with patch.dict(
            gap_queue.OFFLINE_EXHAUSTION_SNS_DEFINITIONS,
            {
                "sns_a1m8d1_1": {
                    **definition,
                    "chatId": "changed_native_chat_id",
                },
            },
        ):
            failed_index, failed_status = (
                gap_queue.build_offline_exhaustion_index(
                    partial,
                    table_root,
                )
            )
        self.assertEqual(failed_index, {})
        self.assertEqual(
            failed_status["status"],
            "inactive_sns_definition_validation_failed",
        )
        failure = failed_status["validationFailures"][0]
        self.assertEqual(failure["validator"], "offline_sns_definition")
        self.assertEqual(failure["storyKey"], "sns_a1m8d1_1")
        self.assertEqual(
            failure["gate"],
            "dialog_shape_and_exact_key_sets",
        )
        self.assertEqual(
            failure["actual"]["chatId"],
            "sns_npc_zuoguyan_a1m8d3",
        )

    def test_declared_a1m5_definition_frontier_is_exact(self) -> None:
        dialog = gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS[
            "dlg_a1m5_5"
        ]
        self.assertEqual(dialog["missionId"], "a1m5")
        self.assertEqual(
            dialog["lineIds"],
            ("dlg_a1m5_5_001", "dlg_a1m5_5_002"),
        )
        self.assertEqual(
            dialog["missingAudioIds"],
            ("au_dlg_a1m5_5_001", "au_dlg_a1m5_5_002"),
        )
        self.assertEqual(
            dialog["allowedNonOwningRoute"]["relation"],
            "dialog_tree_reachable_story_playback",
        )
        self.assertEqual(
            dialog["nonOwningContext"]["candidateQuestIds"],
            (
                "a1m5_q#4",
                "a1m5_q#5",
                "a1m5_q#8",
                "a1m5_q#10",
                "a1m5_q#12",
                "a1m5_q#14",
                "a1m5_q#16",
            ),
        )
        expected_content_ids = {
            "text_a1m5_1": (
                7065289209916235881,
                -3793799197369702242,
            ),
            "text_a1m5_2": (145014796983259450,),
            "text_a1m5_3": (
                -4841045965292223135,
                -89499260089272388,
            ),
            "text_a1m5_4": (-4489297013210307938,),
            "text_a1m5_5": (
                -5413898867121804929,
                -1357598897532823788,
            ),
            "text_a1m5_6": (1303745015045365078,),
            "text_a1m5_7": (-7046570968636013796,),
        }
        self.assertEqual(
            {
                key: gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS[
                    key
                ]["contentTextIds"]
                for key in expected_content_ids
            },
            expected_content_ids,
        )
        self.assertEqual(
            {
                key: gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS[key][
                    "titleId"
                ]
                for key in expected_content_ids
            },
            {
                "text_a1m5_1": -8904306416814611456,
                "text_a1m5_2": -2647826485076773960,
                "text_a1m5_3": -676517154678141545,
                "text_a1m5_4": 2405623048071579055,
                "text_a1m5_5": 1365793654747611898,
                "text_a1m5_6": 5740509153553995198,
                "text_a1m5_7": 2638866450720374170,
            },
        )

    def test_offline_text_definition_validator_reports_exact_failure(
        self,
    ) -> None:
        story_key = "text_a1m5_1"
        definition = gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS[
            story_key
        ]
        popup = {
            "bgType": definition["bgType"],
            "contentId": story_key,
            "iconType": definition["iconType"],
            "id": definition["readingPopupRowId"],
            "overrideRadioId": "",
            "title": {"id": 0, "text": ""},
        }
        rich = {
            "contentList": [
                {"content": {"id": text_id, "text": ""}}
                for text_id in definition["contentTextIds"]
            ],
            "title": {"id": definition["titleId"], "text": ""},
        }

        self.assertIsNone(
            gap_queue._offline_text_definition_validation_failure(
                story_key,
                definition,
                popup,
                rich,
                {},
                {},
            )
        )

        rich["title"]["id"] = 0
        failure = gap_queue._offline_text_definition_validation_failure(
            story_key,
            definition,
            popup,
            rich,
            {},
            {},
        )
        self.assertEqual(failure["validator"], "offlineTextDefinition")
        self.assertEqual(
            failure["gate"],
            "exactReadingPopupAndRichContentRows",
        )
        self.assertEqual(failure["storyKey"], story_key)
        self.assertEqual(
            failure["expected"]["richTitle"]["id"],
            -8904306416814611456,
        )
        self.assertEqual(failure["actual"]["richTitle"]["id"], 0)

    def test_declared_a1m9_definition_frontier_is_exact(self) -> None:
        expected = {
            "text_a1m9_1": (
                "rp_text_a1m9_1", 6133950036636760715,
                (4360361720766943813, -5286642356287476400),
            ),
            "text_a1m9_2": (
                "rp_text_a1m9_2", -9061878788721069148,
                (-8710457857620610713, 195657822153420954),
            ),
            "text_a1m9_3": (
                "rp_text_a1m9_3", -4216673929559825878,
                (5233675183060561957, 4427207018166369215),
            ),
            "text_a1m9_4": (
                "rp_text_a1m9_4", 1447286566198348849,
                (1656717363105155858, -8370465523951817989),
            ),
            "text_a1m9_5": (
                "rp_text_a1m9_5", -7333612545186178263,
                (-5168759132077193528, 7120988803212617269),
            ),
            "text_a1m9_6": (
                "rp_text_a1m9_6", 93296881304760627,
                (-5058010235124771975, -8995527205053721848),
            ),
            "text_a1m9_7": (
                "rp_text_a1m9_7", -8532814195849073983,
                (1466176077223606619, 4212985633755235735),
            ),
        }
        actual = {}
        for story_key in expected:
            definition = gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS[
                story_key
            ]
            self.assertEqual(definition["missionId"], "a1m9")
            self.assertEqual(definition["bgType"], 0)
            self.assertEqual(definition["iconType"], 0)
            actual[story_key] = (
                definition["readingPopupRowId"],
                definition["titleId"],
                definition["contentTextIds"],
            )
        self.assertEqual(actual, expected)

        story_key = "text_a1m9_1"
        definition = gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS[story_key]
        popup = {
            "bgType": 0,
            "contentId": story_key,
            "iconType": 0,
            "id": definition["readingPopupRowId"],
            "overrideRadioId": "",
            "title": {"id": 0, "text": ""},
        }
        rich = {
            "contentList": [
                {"content": {"id": text_id, "text": ""}}
                for text_id in definition["contentTextIds"]
            ],
            "title": {"id": definition["titleId"], "text": ""},
        }
        self.assertIsNone(
            gap_queue._offline_text_definition_validation_failure(
                story_key, definition, popup, rich, {}, {},
            )
        )
        popup["id"] = story_key
        failure = gap_queue._offline_text_definition_validation_failure(
            story_key, definition, popup, rich, {}, {},
        )
        self.assertEqual(failure["validator"], "offlineTextDefinition")
        self.assertEqual(failure["gate"], "exactReadingPopupAndRichContentRows")
        self.assertEqual(
            failure["expected"]["popup"]["id"],
            "rp_text_a1m9_1",
        )
        self.assertEqual(failure["actual"]["popup"]["id"], story_key)

    def test_declared_e6m3_definition_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E6M3_RADIOS,
            {
                "radio_e6m3_10d6",
                "radio_e6m3_21",
                "radio_e6m3_22",
                "radio_e6m3_23",
            },
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_CUTSCENES[
                "cutscene_e6m3_2"
            ]["definitionRowKeys"],
            tuple(
                f"cutscene_e6m3_2_{number:02d}"
                for number in range(1, 15)
            ),
        )
        misc = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "misc_dlg_e6m3_3d5"
        ]
        self.assertEqual(misc["registryKey"], "dlg_e6m3_3d5")
        self.assertEqual(misc["definitionName"], "dlg_e6m3_3d5")
        self.assertEqual(
            set(gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS),
            {
                "text_gm01m7_1",
                "text_a1m6d5_1",
                "text_a1m5_1",
                "text_a1m5_2",
                "text_a1m5_3",
                "text_a1m5_4",
                "text_a1m5_5",
                "text_a1m5_6",
                "text_a1m5_7",
                "text_a1m9_1",
                "text_a1m9_2",
                "text_a1m9_3",
                "text_a1m9_4",
                "text_a1m9_5",
                "text_a1m9_6",
                "text_a1m9_7",
                "text_e0m0_1",
                "text_e6m3_1",
                "text_e6m3_4",
                "text_e6m5_1",
                "text_e7m2_2",
                "text_e7m3_1",
                "text_e7m4_1",
                "text_e8m4_1",
                "text_e10m3_4",
                "text_e10m3_6",
                "text_e10m3_8",
                "text_e10m4_1",
                "text_gm01m22_5",
                "text_gm01m12_1",
                "text_gm01m13_1",
                "text_gm01m15_1",
                "text_gm01m15_8",
                "text_gm01m12_3",
                "text_gm01m12_5",
                "text_gm01m12_6",
                "text_gm01m12_7",
                "text_gm01m14_4",
                "text_gm01m14_5",
                "text_gm01m17_1",
            },
        )

    def test_declared_e6m5_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E6M5_RADIOS,
            {"radio_e6m5_4"},
        )
        definition = gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS[
            "text_e6m5_1"
        ]
        self.assertEqual(
            definition["contentTextIds"],
            (2915169207318156019, -3317420327824307745),
        )
        self.assertEqual(
            definition["prtsDefinition"],
            {
                "rowId": "nar_collection_map02_69_1",
                "row": {
                    "contentId": "text_e6m5_1",
                    "desc": {"id": 0, "text": ""},
                    "firstLvId": "collection_map02_69",
                    "id": "nar_collection_map02_69_1",
                    "name": {"id": 6370990046482612204, "text": ""},
                    "order": 1,
                    "overrideRadioId": "",
                    "type": "text",
                },
            },
        )

    def test_declared_e2m8d5_offline_frontier_is_exact(self) -> None:
        expected = {
            "dlg_e2m8d5_2": {
                "lines": (
                    "dlg_e2m8d5_2_001",
                    "dlg_e2m8d5_2_002",
                    "dlg_e2m8d5_2_004",
                    "dlg_e2m8d5_2_006",
                    "dlg_e2m8d5_2_007",
                ),
                "options": (
                    "option_dlg_e2m8d5_2_1_001",
                    "option_dlg_e2m8d5_2_1_002",
                ),
                "proxyId": "pelica_map01_e2m8d5",
                "entryIndex": 2,
                "missionIdPresent": False,
            },
            "dlg_e2m8d5_3": {
                "lines": tuple(
                    f"dlg_e2m8d5_3_{number:03d}"
                    for number in range(1, 6)
                ),
                "options": ("option_dlg_e2m8d5_3_1_001",),
                "proxyId": "chen_map01_e2m8d5",
                "entryIndex": 0,
                "missionIdPresent": True,
            },
        }
        for story_key, facts in expected.items():
            definition = (
                gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[story_key]
            )
            self.assertEqual(definition["missionId"], "e2m8d5")
            self.assertEqual(definition["lineIds"], facts["lines"])
            self.assertEqual(definition["optionIds"], facts["options"])
            consumer = current_npc_proxy_consumer_contexts(story_key)[0]
            self.assertEqual(consumer["proxyId"], facts["proxyId"])
            self.assertEqual(consumer["entryIndex"], facts["entryIndex"])
            self.assertEqual(
                "missionId" in consumer["entry"],
                facts["missionIdPresent"],
            )
            self.assertFalse(consumer["entry"].get("missionId"))

    def test_declared_e11m8d5_offline_frontier_is_exact(self) -> None:
        registered = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_e11m8d5_1"
        ]
        self.assertEqual(len(registered["lineIds"]), 10)
        self.assertEqual(len(registered["optionIds"]), 2)
        self.assertEqual(len(registered["missingAudioIds"]), 10)
        consumer = current_npc_proxy_consumer_contexts("dlg_e11m8d5_1")[0]
        self.assertEqual(consumer["proxyId"], "lizy_map02_v1d4d0_world")
        self.assertEqual(consumer["entryIndex"], 0)
        self.assertEqual(consumer["entry"]["missionId"], "")
        text_only = gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS[
            "dlg_e11m8d5_2"
        ]
        self.assertEqual(
            text_only["lineIds"],
            ("dlg_e11m8d5_2_001", "dlg_e11m8d5_2_002"),
        )
        self.assertEqual(
            text_only["missingAudioIds"],
            ("au_dlg_e11m8d5_2_001", "au_dlg_e11m8d5_2_002"),
        )

    def test_declared_e5m5_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E5M5_RADIOS,
            {"radio_e5m5_1", "radio_e5m5_2"},
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_RADIO_MISSING_AUDIO_IDS[
                "radio_e5m5_1"
            ],
            {"au_radio_e5m5_1_001", "au_radio_e5m5_1_002"},
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_RADIO_MISSING_AUDIO_IDS[
                "radio_e5m5_2"
            ],
            {"au_radio_e5m5_2_001"},
        )

    def test_declared_e6m1_offline_frontier_is_exact(self) -> None:
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_E6M1_RADIOS,
            {"radio_e6m1_19"},
        )
        dialog = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_e6m1_14"
        ]
        self.assertEqual(len(dialog["lineIds"]), 4)
        self.assertEqual(
            current_npc_proxy_consumer_contexts("dlg_e6m1_14")[0]["proxyId"],
            "lugang_map02_e6m1ZhenLie",
        )
        dialog = gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
            "dlg_e6m1_15"
        ]
        self.assertEqual(len(dialog["lineIds"]), 3)
        self.assertEqual(len(dialog["optionIds"]), 2)
        self.assertEqual(
            {
                row["proxyId"]
                for row in current_npc_proxy_consumer_contexts("dlg_e6m1_15")
            },
            {
                "puyuan_map02_default",
                "puyuan_map02_e6m1ZhenLie",
            },
        )

    def test_declared_e10m4_definition_frontier_is_exact(self) -> None:
        self.assertEqual(
            set(gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS)
            & {"dlg_e10m4_16", "dlg_e10m4_17", "dlg_e10m4_21"},
            {"dlg_e10m4_21"},
        )
        self.assertEqual(
            set(gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS)
            & {"dlg_e10m4_16", "dlg_e10m4_17", "dlg_e10m4_21"},
            {"dlg_e10m4_16", "dlg_e10m4_17"},
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
                "dlg_e10m4_21"
            ]["missingAudioIds"],
            (
                "au_dlg_e10m4_21_001",
                "au_dlg_e10m4_21_002",
                "au_dlg_e10m4_21_003",
            ),
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[
                "dlg_e10m4_21"
            ]["extraConfigSha256"],
            "BBA7D588A2B3D0B9A44D8D4D9D58A14246096C41E85ABA330357BAFC32140B94",
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS[
                "dlg_e10m4_16"
            ]["audioVariants"],
            {
                "au_dlg_e10m4_16_001": (
                    "au_dlg_e10m4_16_001_f",
                    "au_dlg_e10m4_16_001_m",
                ),
            },
        )
        self.assertEqual(
            gap_queue.OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS[
                "dlg_e10m4_17"
            ]["missingAudioIds"],
            (
                "au_dlg_e10m4_17_001",
                "au_dlg_e10m4_17_002",
            ),
        )
        self.assertEqual(
            set(gap_queue.OFFLINE_EXHAUSTION_SNS_DEFINITIONS),
            {
                "sns_a1m8d1_1",
                "sns_e1m9_1",
                "sns_e7m4_1",
                "sns_e10m4_1",
                "sns_gm01m3_1",
                "sns_gm01m22_2",
                "sns_gm01m7_1",
                "sns_gm01m7_2",
            },
        )
        self.assertEqual(
            set(
                gap_queue.OFFLINE_EXHAUSTION_SNS_DEFINITIONS[
                    "sns_e10m4_1"
                ]["optionNextContentIds"]
            ),
            {
                "option_sns_e10m4_1_1_001",
                "option_sns_e10m4_1_2_001",
                "option_sns_e10m4_1_3_001",
                "option_sns_e10m4_1_5_001",
            },
        )
        self.assertIn(
            "text_e10m4_1",
            gap_queue.OFFLINE_EXHAUSTION_TEXT_DEFINITIONS,
        )

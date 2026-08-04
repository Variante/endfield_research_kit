from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_protocol_registry_audit as audit  # noqa: E402


class ProtocolRegistryAuditTests(unittest.TestCase):
    def test_current_report_status_requires_validated_matching_original_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            metadata = root / "global-metadata.dat"
            gameassembly = root / "GameAssembly.dll"
            report_path = root / "audit.json"
            metadata.write_bytes(b"metadata")
            gameassembly.write_bytes(b"gameassembly")
            report_path.write_text(json.dumps({
                "_schema": "endfieldProtocolRegistryAudit.v17",
                "source": {
                    "metadataSha256": audit.file_sha256(metadata),
                    "gameAssemblySha256": audit.file_sha256(gameassembly),
                },
                "stateUpdateApplicationCensus": {
                    "validation": {"status": "validated", "failures": []},
                    "questStartApplication": {
                        "validation": {"status": "validated", "failures": []},
                    },
                    "questSucceedActionApplication": {
                        "validation": {"status": "validated", "failures": []},
                    },
                    "questTopologyFieldConsumers": {
                        "validation": {"status": "validated", "failures": []},
                        "questSemanticFields": {
                            "validation": {"status": "validated", "failures": []},
                        },
                    },
                },
                "levelScriptStartPolicy": {
                    "validation": {"status": "validated", "failures": []},
                },
                "levelScriptManualSelfControl": {
                    "validation": {"status": "validated", "failures": []},
                },
                "levelScriptActivationControl": {
                    "validation": {"status": "validated", "failures": []},
                },
            }), encoding="utf-8")

            self.assertEqual(
                audit.current_report_status(report_path, metadata, gameassembly),
                (True, "validated report hashes match original inputs"),
            )
            metadata.write_bytes(b"changed")
            current, reason = audit.current_report_status(
                report_path,
                metadata,
                gameassembly,
            )
            self.assertFalse(current)
            self.assertIn("metadataSha256 differs", reason)

    def test_quest_succeed_action_observation_accepts_generic_native_flow(self):
        result = audit.validate_quest_succeed_action_observation(
            enum_values={
                "OnStartClientAction": 1,
                "OnSucceedClientAction": 2,
                "OnFailedClientAction": 4,
            },
            succeed_action_calls=[{"questActionValue": 2}],
            safe_run_action_flow={"preservesQuestActionArgument": True},
            safe_run_direct_callers=[
                {"symbol": "Beyond.Gameplay.MissionSystem.FailQuest"},
                {"symbol": "Beyond.Gameplay.MissionSystem.SucceedQuest"},
            ],
            source_file="GameAssembly.dll",
            source_hashes={"gameAssemblySha256": "a" * 64},
        )
        self.assertEqual(result, {"status": "validated", "failures": []})

    def test_quest_succeed_action_observation_reports_independent_drift(self):
        result = audit.validate_quest_succeed_action_observation(
            enum_values={"OnSucceedClientAction": 3},
            succeed_action_calls=[{"questActionValue": 3}],
            safe_run_action_flow={"preservesQuestActionArgument": False},
            safe_run_direct_callers=[
                {"symbol": "Beyond.Gameplay.MissionSystem.SucceedQuest"},
            ],
            source_file="GameAssembly.dll",
            source_hashes={"gameAssemblySha256": "b" * 64},
        )
        self.assertEqual(result["status"], "validation_failed")
        self.assertEqual(
            [failure["gate"] for failure in result["failures"]],
            [
                "questActionEnum",
                "succeedActionValue",
                "safeRunPreservesQuestAction",
                "safeRunDirectCallerCensus",
            ],
        )
        self.assertTrue(all(failure["sourceHashes"] for failure in result["failures"]))

    def test_levelscript_start_policy_observation_accepts_generic_native_flow(self):
        observation = {
            "enumValues": {
                "Beyond.GEnums.LevelScriptState": {"Active": 3},
                "Beyond.Gameplay.LevelScriptStartType": {
                    "ByEnterStartShape": 0,
                    "Manual": 1,
                    "SameWithActive": 2,
                    "Never": 3,
                },
                "Beyond.Gameplay.Core.LevelScriptRuntime+RuntimeState": {
                    "PreStart": 22,
                },
            },
            "methods": {
                name: {"mappingStatus": "mapped_unique"}
                for name in (
                    "get_state",
                    "get_isDone",
                    "get_startType",
                    "UpdateWithinStartArea",
                    "set_runtimeState",
                    "UpdateRuntimeState",
                )
            },
            "activeStateGate": {
                "comparedValue": 3,
                "branchTargetIsDoneCheck": True,
            },
            "doneGate": {
                "doneResultTested": True,
                "notDoneFallsThroughToStartPolicy": True,
            },
            "startTypeGates": {
                "Never": {
                    "comparedValue": 3,
                    "branchesAwayFromPreStart": True,
                },
                "ByEnterStartShape": {
                    "comparedValue": 0,
                    "branchTargetIsStartAreaCheck": True,
                },
                "SameWithActive": {
                    "comparedValue": 2,
                    "branchTargetIsCommonPreStart": True,
                },
            },
            "startAreaGate": {
                "resultTested": True,
                "trueFallsThroughToCommonPreStart": True,
            },
            "preStartTransition": {
                "runtimeStateValue": 22,
                "setterReceivesValue": True,
            },
        }

        result = audit.validate_levelscript_start_policy_observation(
            observation,
            source_file="GameAssembly.dll",
            source_hashes={"gameAssemblySha256": "a" * 64},
        )

        self.assertEqual(result, {"status": "validated", "failures": []})

    def test_levelscript_start_policy_observation_reports_branch_drift(self):
        observation = {
            "enumValues": {
                "Beyond.GEnums.LevelScriptState": {"Active": 3},
                "Beyond.Gameplay.LevelScriptStartType": {
                    "ByEnterStartShape": 0,
                    "Manual": 1,
                    "SameWithActive": 2,
                    "Never": 3,
                },
                "Beyond.Gameplay.Core.LevelScriptRuntime+RuntimeState": {
                    "PreStart": 22,
                },
            },
            "methods": {
                name: {"mappingStatus": "mapped_unique"}
                for name in (
                    "get_state",
                    "get_isDone",
                    "get_startType",
                    "UpdateWithinStartArea",
                    "set_runtimeState",
                    "UpdateRuntimeState",
                )
            },
            "activeStateGate": {
                "comparedValue": 3,
                "branchTargetIsDoneCheck": True,
            },
            "doneGate": {
                "doneResultTested": True,
                "notDoneFallsThroughToStartPolicy": True,
            },
            "startTypeGates": {
                "Never": {
                    "comparedValue": 3,
                    "branchesAwayFromPreStart": True,
                },
                "ByEnterStartShape": {
                    "comparedValue": 0,
                    "branchTargetIsStartAreaCheck": True,
                },
                "SameWithActive": {
                    "comparedValue": 2,
                    "branchTargetIsCommonPreStart": False,
                },
            },
            "startAreaGate": {
                "resultTested": True,
                "trueFallsThroughToCommonPreStart": True,
            },
            "preStartTransition": {
                "runtimeStateValue": 22,
                "setterReceivesValue": False,
            },
        }

        result = audit.validate_levelscript_start_policy_observation(
            observation,
            source_file="GameAssembly.dll",
            source_hashes={"gameAssemblySha256": "b" * 64},
        )

        self.assertEqual(result["status"], "validation_failed")
        self.assertEqual(
            [failure["gate"] for failure in result["failures"]],
            ["SameWithActiveGate", "commonPreStartTransition"],
        )
        self.assertEqual(result["failures"][0]["sourceFile"], "GameAssembly.dll")

    def test_manual_self_control_accepts_generic_current_context_flow(self):
        observation = {
            "paramSourceValues": {
                "CURRENT_LEVEL_ID": 1000,
                "CURRENT_SCRIPT_ID": 1002,
            },
            "runtimeStateValues": {"PreStart": 22},
            "actionFields": {
                "levelId": {
                    "runtimeType": "Beyond.Gameplay.Actions.Param`1<string>",
                },
                "scriptId": {
                    "runtimeType": (
                        "Beyond.Gameplay.Actions.Param`1<"
                        "Beyond.Gameplay.Core.LevelScriptPtr>"
                    ),
                },
            },
            "methods": {
                name: {"mappingStatus": "mapped_unique"}
                for name in (
                    "Execute",
                    "TryGetLevelScript",
                    "ManualStart",
                    "set_runtimeState",
                    "UpdateRuntimeState",
                )
            },
            "executeFlow": {
                "tryGetLevelScriptCallCount": 1,
                "manualStartCallCount": 1,
                "tryGetBeforeManualStart": True,
            },
            "manualStartFlow": {
                "runtimeStateValue": 22,
                "setterReceivesValue": True,
                "updateRuntimeStateCallCount": 1,
                "setterBeforeUpdate": True,
            },
        }

        result = audit.validate_levelscript_manual_self_control_observation(
            observation,
            source_file="GameAssembly.dll",
            source_hashes={"gameAssemblySha256": "c" * 64},
        )

        self.assertEqual(result, {"status": "validated", "failures": []})

    def test_manual_self_control_reports_independent_contract_drift(self):
        observation = {
            "paramSourceValues": {
                "CURRENT_LEVEL_ID": 1000,
                "CURRENT_SCRIPT_ID": 9999,
            },
            "runtimeStateValues": {"PreStart": 22},
            "actionFields": {
                "levelId": {"runtimeType": "wrong"},
                "scriptId": {"runtimeType": "wrong"},
            },
            "methods": {
                name: {"mappingStatus": "mapped_unique"}
                for name in (
                    "Execute",
                    "TryGetLevelScript",
                    "ManualStart",
                    "set_runtimeState",
                    "UpdateRuntimeState",
                )
            },
            "executeFlow": {
                "tryGetLevelScriptCallCount": 1,
                "manualStartCallCount": 0,
                "tryGetBeforeManualStart": False,
            },
            "manualStartFlow": {
                "runtimeStateValue": 22,
                "setterReceivesValue": False,
                "updateRuntimeStateCallCount": 1,
                "setterBeforeUpdate": True,
            },
        }

        result = audit.validate_levelscript_manual_self_control_observation(
            observation,
            source_file="GameAssembly.dll",
            source_hashes={"gameAssemblySha256": "d" * 64},
        )

        self.assertEqual(result["status"], "validation_failed")
        self.assertEqual(
            [failure["gate"] for failure in result["failures"]],
            [
                "paramSourceEnum",
                "manualStartFieldTypes",
                "executeFlow",
                "manualStartTransition",
            ],
        )

    def test_activation_control_accepts_generic_state_and_subgame_flows(self):
        observation = {
            "messageIds": {
                "CsSceneSetLevelScriptActive": 94,
                "CsSceneSetLevelScriptStart": 101,
                "ScSceneLevelScriptStateNotify": 37,
                "ScSelfSceneInfo": 25,
            },
            "messageSchemas": {
                "activationRequest": {"fields": [
                    {"name": "sceneNumId", "tag": 1},
                    {"name": "scriptId", "tag": 2},
                    {"name": "isActive", "tag": 3},
                    {"name": "leaderPos", "tag": 4},
                ]},
                "startRequest": {"fields": [
                    {"name": "sceneNumId", "tag": 1},
                    {"name": "scriptId", "tag": 2},
                    {"name": "isStart", "tag": 3},
                    {"name": "leaderPos", "tag": 4},
                ]},
                "stateNotify": {"fields": [
                    {"name": "sceneNumId", "tag": 1},
                    {"name": "scriptId", "tag": 2},
                    {"name": "state", "tag": 3},
                    {"name": "isComplete", "tag": 4},
                ]},
                "selfSceneInfo": {"fields": [
                    {"name": "sceneNumId", "tag": 1},
                    {"name": "sceneId", "tag": 2},
                    {"name": "levelScripts", "tag": 8},
                ]},
                "levelScriptInfo": {"fields": [
                    {"name": "scriptId", "tag": 1},
                    {"name": "state", "tag": 2},
                    {"name": "properties", "tag": 3},
                    {"name": "isDone", "tag": 4},
                    {"name": "stage", "tag": 5},
                    {"name": "triggerVolumeInfos", "tag": 6},
                ]},
            },
            "fieldOffsets": {
                "challengeStartPoint.m_subGameId": 0x68,
                "subGameInstanceData.bindScriptId": 0x50,
                "stateNotify.sceneNumId_": 0x18,
                "stateNotify.scriptId_": 0x20,
                "stateNotify.state_": 0x28,
                "stateNotify.isComplete_": 0x2C,
                "selfSceneInfo.sceneNumId_": 0x18,
                "selfSceneInfo.sceneId_": 0x20,
                "selfSceneInfo.levelScripts_": 0x38,
                "levelScriptInfo.scriptId_": 0x18,
                "levelScriptInfo.state_": 0x20,
                "levelScriptInfo.properties_": 0x28,
                "levelScriptInfo.isDone_": 0x30,
                "levelScriptInfo.stage_": 0x34,
                "levelScriptInfo.triggerVolumeInfos_": 0x38,
                "levelScriptRuntime.m_manualStartTriggered": 0xF8,
                "levelScriptRuntime.withinActiveArea": 0x68,
                "levelScriptRuntime.activeShapeList": 0x70,
                "levelScriptRuntime.activeShapeOutsideList": 0x78,
            },
            "methods": {
                name: {"mappingStatus": "mapped_unique"}
                for name in (
                    "SelfSceneInfoHandler",
                    "StateNotifyHandler",
                    "ManagerStateShort",
                    "ManagerStateFull",
                    "ManagerServerSyncLevelScript",
                    "ContainerState",
                    "ContainerServerSyncLevelScript",
                    "UpdateState",
                    "RuntimeServerSync",
                    "set_state",
                    "set_runtimeState",
                    "UpdateRuntimeState",
                    "get_state",
                    "get_levelScriptType",
                    "UpdateWithinActiveArea",
                    "Setup",
                    "RegisterTriggerFromLevelScript",
                    "SetAllTriggerActiveByPhase",
                    "ChallengeOnInteract",
                    "SubGameTableTryGetValue",
                    "LevelScriptPtrImplicit",
                    "TryGetLevelScript",
                    "ManualStart",
                    "ManualStartActionExecute",
                    "NetworkSetActive",
                    "NetworkSetStart",
                    "RuntimeSendActive",
                    "RuntimeSendStart",
                    "BaseSendMsg",
                )
            },
            "publicStateFlow": {
                "handlerToManagerShort": 1,
                "managerShortToManagerFull": 1,
                "managerFullToContainer": 1,
                "containerToUpdateState": 1,
                "updateStateToSetter": 1,
                "updateStateToRuntimeEvaluation": 1,
                "setterBeforeRuntimeEvaluation": True,
            },
            "publicStateSourceFlow": {
                "snapshotMessageId": 25,
                "incrementalMessageId": 37,
                "snapshotLevelScriptsRuntimeType": (
                    "Google.Protobuf.Collections.RepeatedField`1<Proto.LEVEL_SCRIPT_INFO>"
                ),
                "managerStateShortDirectCallers": [
                    "Beyond.Gameplay.GameplayNetwork._Handle_SceneLevelScriptStateNotify",
                    "Beyond.Gameplay.GameplayNetwork._Handle_SelfSceneInfo",
                ],
                "managerStateFullDirectCallers": [
                    "Beyond.Gameplay.Core.LevelScriptManager.ServerSyncLevelScriptState",
                ],
                "managerServerSyncDirectCallers": [],
                "containerStateDirectCallers": [
                    "Beyond.Gameplay.Core.LevelScriptManager.ServerSyncLevelScriptState",
                ],
                "updateStateDirectCallers": [
                    "Beyond.Gameplay.Core.LevelScriptContainer.ServerSyncLevelScriptState",
                ],
                "runtimeServerSyncDirectCallers": [
                    "Beyond.Gameplay.Core.LevelScriptContainer.ServerSyncLevelScript",
                ],
                "containerServerSyncDirectCallers": [
                    "Beyond.Gameplay.Core.LevelScriptManager.ServerSyncLevelScript",
                    "Beyond.Gameplay.GameplayNetwork._Handle_SelfSceneInfo",
                ],
                "publicStateSetterDirectCallers": [
                    "Beyond.Gameplay.Core.LevelScriptContainer.LoadFromLevelData",
                    "Beyond.Gameplay.Core.LevelScriptRuntime.Init",
                    "Beyond.Gameplay.Core.LevelScriptRuntime.ServerSync",
                    "Beyond.Gameplay.Core.LevelScriptRuntime.UpdateState",
                ],
                "publicStateSetterArguments": {
                    "Beyond.Gameplay.Core.LevelScriptContainer.LoadFromLevelData": ["0"],
                    "Beyond.Gameplay.Core.LevelScriptRuntime.Init": ["0"],
                    "Beyond.Gameplay.Core.LevelScriptRuntime.ServerSync": ["param:state"],
                    "Beyond.Gameplay.Core.LevelScriptRuntime.UpdateState": ["param:value"],
                },
            },
            "subGameInteractionFlow": {
                "subGameLookupCallCount": 1,
                "scriptPtrConversionCallCount": 1,
                "tryGetLevelScriptCallCount": 1,
                "manualStartCallCount": 1,
                "callsInCarrierOrder": True,
                "subGameIdFieldRead": True,
                "bindScriptIdFieldRead": True,
            },
            "manualStartDirectCallers": [
                {
                    "type": "Beyond.Gameplay.Actions.ManualStartLevelScript",
                    "method": "Execute",
                },
                {
                    "type": (
                        "Beyond.Gameplay.InteractiveLogicChallengeStartPoint"
                    ),
                    "method": "_OnInteract",
                },
            ],
            "clientRequestFlow": {
                "networkActiveToSendMsg": 1,
                "networkStartToSendMsg": 1,
                "runtimeActiveToSendMsg": 1,
                "runtimeStartToSendMsg": 1,
                "networkActiveDirectCallerCount": 0,
                "networkStartDirectCallerCount": 0,
                "runtimeActiveDirectCallerCount": 2,
                "runtimeStartDirectCallerCount": 2,
                "runtimeActiveArguments": [True, False],
                "runtimeStartArguments": [True, False],
                "manualStartFlagWrite": True,
                "manualStartFlagBeforeStateSetter": True,
                "startTrueFollowedByPreStartActionRunning": True,
            },
            "directCallers": {
                "NetworkSetActive": [],
                "NetworkSetStart": [],
                "RuntimeSendActive": [{
                    "type": "Beyond.Gameplay.Core.LevelScriptRuntime",
                    "method": "UpdateRuntimeState",
                    "callSites": [{}, {}],
                }],
                "RuntimeSendStart": [{
                    "type": "Beyond.Gameplay.Core.LevelScriptRuntime",
                    "method": "UpdateRuntimeState",
                    "callSites": [{}, {}],
                }],
            },
            "activeReceiverFlow": {
                "triggerActiveDuringValues": {"Active": 0, "Start": 1},
                "setupRegisterTriggerCallCount": 1,
                "activePhaseEnableArguments": [
                    {"active": True, "triggerActiveDuring": 0},
                    {"active": True, "triggerActiveDuring": 0},
                ],
                "activeBeginStateValue": 14,
                "waitForSubEntityInitNewlyStateValue": 15,
                "activePhaseEnableBetweenStateSetters": True,
            },
            "activationSelectorFlow": {
                "levelScriptTypeValues": {
                    "World": 0,
                    "Mission": 1,
                    "Game": 2,
                    "Master": 3,
                    "SubLevelScript": 4,
                    "ControlledGame": 5,
                },
                "enabledStateValue": 2,
                "activeStateValue": 3,
                "preActiveStateValue": 7,
                "preActiveEndSendActiveStateValue": 9,
                "waitForStateActiveValue": 10,
                "inactiveLevelScriptTypeCallOffset": 1240,
                "nonSubLevelEnabledStateCallOffset": 1255,
                "activeAreaGateCallOffset": 1274,
                "subLevelActiveStateCallOffset": 1288,
                "preActiveSetterCallOffset": 1313,
                "preActiveLevelScriptTypeCallOffset": 2106,
                "activeTrueRequestCallOffset": 2124,
                "waitForStateActiveSetterOffsets": [2140, 2155],
                "nonSubLevelRequiresEnabledAndActiveArea": True,
                "subLevelRequiresPublicActive": True,
                "nonSubLevelSendsActiveTrueAfterPreActive": True,
                "subLevelSkipsActiveTrueRequest": True,
            },
            "activeAreaFlow": {
                "activeShapeListFieldOffset": 112,
                "activeShapeOutsideListFieldOffset": 120,
                "withinActiveAreaFieldOffset": 104,
                "activeShapeListReadOffsets": [363, 1356, 1374],
                "activeShapeOutsideListReadOffsets": [1630, 1648],
                "withinActiveAreaAccessOffsets": [1704, 1743, 3388, 3394, 3398],
                "activeListPositiveCountSetterOffset": 430,
                "emptyActiveListBranchOffset": 555,
                "activeShapeTestCallOffset": 1617,
                "activeShapeHitBranchOffset": 1624,
                "missingOutsideListBranchOffset": 1635,
                "outsideShapeTestCallOffset": 1691,
                "outsideShapeMissBranchOffset": 1698,
                "withinFalseSetterOffsets": [1743, 3388],
                "outsideShapeHitClearOffset": 1743,
                "withinTrueSetterOffset": 3394,
                "withinReturnOffset": 3398,
                "emptyActiveListSetsWithinTrue": True,
                "activeShapeHitSetsWithinTrue": True,
                "missingOutsideListPreservesPriorWithin": True,
                "outsideShapeMissPreservesPriorWithin": True,
                "outsideShapeHitClearsWithin": True,
            },
        }

        result = audit.validate_levelscript_activation_control_observation(
            observation,
            source_file="GameAssembly.dll",
            source_hashes={"gameAssemblySha256": "e" * 64},
        )

        self.assertEqual(result, {"status": "validated", "failures": []})

    def test_activation_control_reports_independent_contract_drift(self):
        observation = {
            "messageIds": {},
            "messageSchemas": {},
            "fieldOffsets": {},
            "methods": {},
            "publicStateFlow": {},
            "subGameInteractionFlow": {},
            "manualStartDirectCallers": [],
        }

        result = audit.validate_levelscript_activation_control_observation(
            observation,
            source_file="GameAssembly.dll",
            source_hashes={"gameAssemblySha256": "f" * 64},
        )

        self.assertEqual(result["status"], "validation_failed")
        self.assertEqual(
            [failure["gate"] for failure in result["failures"]],
            [
                "messageIds",
                "messageSchemas",
                "fieldOffsets",
                "methodMapping",
                "publicStateFlow",
                "publicStateSourceFlow",
                "subGameInteractionFlow",
                "manualStartDirectCallers",
                "clientRequestFlow",
                "requestDirectCallers",
                "activationSelectorFlow",
                "activeAreaFlow",
                "activeReceiverFlow",
            ],
        )

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

    def test_quest_start_observation_accepts_single_object_initialization(self):
        result = audit.validate_quest_start_application_observation(
            field_reads={
                "objectiveList": 3,
                "questType": 0,
                "showMode": 0,
                "prevQuestIdList": 0,
                "flowIndex": 0,
            },
            quest_info_getters=[{"symbol": "Fixture.GetQuestInfo"}],
            topology_calls=[],
            source_file="GameAssembly.dll",
            source_hashes={"gameAssemblySha256": "a" * 64},
        )

        self.assertEqual(result, {"status": "validated", "failures": []})

    def test_quest_start_observation_reports_all_independent_failures(self):
        result = audit.validate_quest_start_application_observation(
            field_reads={
                "objectiveList": 0,
                "questType": 1,
                "showMode": 1,
                "prevQuestIdList": 2,
                "flowIndex": 1,
            },
            quest_info_getters=[],
            topology_calls=["Fixture.GetNextQuest"],
            source_file="GameAssembly.dll",
            source_hashes={"gameAssemblySha256": "b" * 64},
        )

        self.assertEqual(result["status"], "validation_failed")
        self.assertEqual(
            [failure["gate"] for failure in result["failures"]],
            [
                "uniqueQuestInfoGetter",
                "objectiveInitializationRead",
                "noClientTopologyReadDuringStart",
                "noQuestSemanticSelectorDuringStart",
                "noClientSuccessorTraversalCall",
            ],
        )
        self.assertEqual(
            result["failures"][2]["expected"],
            {"prevQuestIdList": 0, "flowIndex": 0},
        )
        self.assertEqual(
            result["failures"][2]["actual"],
            {"prevQuestIdList": 2, "flowIndex": 1},
        )
        self.assertEqual(
            result["failures"][3]["actual"],
            {"questType": 1, "showMode": 1},
        )
        self.assertEqual(result["failures"][0]["sourceFile"], "GameAssembly.dll")

    def test_topology_consumer_observation_accepts_display_only_uses(self):
        result = audit.validate_quest_topology_consumer_observation(
            verified_direct_calls=42,
            active_predecessor_rows=[],
            non_sort_flow_rows=[],
            main_path_read_rows=[{"caller": "fixture"}],
            lifecycle_calls=[],
            source_file="GameAssembly.dll",
            source_hashes={"gameAssemblySha256": "c" * 64},
        )

        self.assertEqual(result, {"status": "validated", "failures": []})

    def test_topology_consumer_observation_reports_independent_gates(self):
        result = audit.validate_quest_topology_consumer_observation(
            verified_direct_calls=0,
            active_predecessor_rows=[{"caller": "active-prev"}],
            non_sort_flow_rows=[{"caller": "runtime-flow"}],
            main_path_read_rows=[],
            lifecycle_calls=["Fixture.StartQuest"],
            source_file="GameAssembly.dll",
            source_hashes={"gameAssemblySha256": "d" * 64},
        )

        self.assertEqual(result["status"], "validation_failed")
        self.assertEqual(
            [failure["gate"] for failure in result["failures"]],
            [
                "verifiedQuestInfoCallers",
                "noActivePredecessorRuntimeConsumer",
                "flowIndexOnlyDisplayComparator",
                "mainPathConsumerDiscovery",
                "noTopologyDrivenLifecycleCall",
            ],
        )
        self.assertEqual(
            result["failures"][-1]["actual"],
            ["Fixture.StartQuest"],
        )

    def test_quest_semantic_fields_accept_post_lifecycle_consumption(self):
        result = audit.validate_quest_semantic_field_observation(
            quest_type_values={"Normal": 0, "Block": 1, "Optional": 2},
            show_mode_values={"AlwaysShow": 1, "AlwaysHide": 1000},
            quest_type_rows=[{
                "classification": "post_lifecycle_quest_type_behavior",
                "lifecycleCallSites": [{"offset": 20}],
                "semanticFieldReadOffsets": [30],
                "backwardLifecycleBranches": [],
            }],
            show_mode_rows=[{
                "classification": "quest_visibility_or_tracker_presentation",
                "lifecycleCallSites": [],
            }],
            source_file="GameAssembly.dll",
            source_hashes={"gameAssemblySha256": "e" * 64},
        )

        self.assertEqual(result, {"status": "validated", "failures": []})

    def test_quest_semantic_fields_report_enum_and_interleaving_failures(self):
        interleaved = {
            "classification": "quest_type_lifecycle_interleaved",
            "lifecycleCallSites": [{"offset": 30}],
            "semanticFieldReadOffsets": [20],
            "backwardLifecycleBranches": [{"offset": 40, "targetOffset": 10}],
        }
        result = audit.validate_quest_semantic_field_observation(
            quest_type_values={"Normal": 0},
            show_mode_values={"AlwaysShow": 1},
            quest_type_rows=[interleaved],
            show_mode_rows=[{
                "lifecycleCallSites": [{"offset": 10}],
            }],
            source_file="GameAssembly.dll",
            source_hashes={"gameAssemblySha256": "f" * 64},
        )

        self.assertEqual(result["status"], "validation_failed")
        self.assertEqual(
            [failure["gate"] for failure in result["failures"]],
            [
                "questTypeEnum",
                "questShowModeEnum",
                "showModeHasNoLifecycleConsumer",
                "questTypeLifecycleReadsArePostApplication",
                "noSemanticFieldBackEdgeToLifecycle",
            ],
        )

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

    def test_message_125_is_native_proven_while_sibling_fallbacks_are_inactive(self):
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
            "no exact authored pair",
            audit.NATIVE_MISSION_EVENT_PATHS[125]["directCallCensus"][
                "typedPairingStatus"
            ],
        )
        self.assertEqual(
            rows[126]["classification"],
            "native_handler_absent_current_fallback",
        )
        for message_id in (316, 317):
            self.assertEqual(
                rows[message_id]["classification"],
                "native_sender_absent_current_fallback",
            )
            self.assertNotIn(message_id, audit.NATIVE_MISSION_EVENT_PATHS)

    def test_message_125_typed_subscriber_shape_is_fail_closed(self):
        expected = (
            "Beyond.EventData`1<Beyond.Gameplay.EventData>"
        )
        self.assertEqual(
            audit.expected_event_bus_binding_type(
                "Beyond.Gameplay.EventData"
            ),
            expected,
        )
        rows = [
            {"genericArguments": ["Beyond.EventData`1<int>"]},
            {"genericArguments": [expected]},
        ]
        self.assertEqual(
            audit.matching_event_bus_subscriber_rows(
                rows,
                "Beyond.Gameplay.EventData",
            ),
            [rows[1]],
        )
        self.assertEqual(
            audit.matching_event_bus_subscriber_rows(
                rows[:1],
                "Beyond.Gameplay.EventData",
            ),
            [],
        )

    def test_message_57_preserves_ctx_token_as_non_owning_event_context(self):
        evidence = audit.NATIVE_LEVEL_SCRIPT_EVENT_PATHS[57]
        self.assertEqual(evidence["token"], "0x06004dbf")
        self.assertEqual(evidence["fieldOffsets"]["ctxToken"], "0x30")
        self.assertIn("returns it", evidence["ctxTokenFinding"])
        self.assertIn(
            "LevelEventManager.RaiseScriptEvent",
            evidence["eventParamsPath"]["dispatch"],
        )
        reader = evidence["ctxTokenReaderAudit"]
        self.assertEqual(reader["paramBlackboardKeySlotVa"], "0x18e2eef08")
        self.assertEqual(reader["directRipReferenceCount"], 4)
        self.assertEqual(reader["referencingMethodCount"], 2)
        self.assertEqual(
            reader["outboundPath"][-1]["symbol"],
            "Proto.CS_SCENE_LEVEL_SCRIPT_EVENT_TRIGGER.set_CtxToken",
        )
        self.assertEqual(
            reader["classification"],
            "level_script_event_round_trip_correlation",
        )
        self.assertEqual(reader["missionQuestReaders"], 0)
        self.assertEqual(reader["storyBindingsAdded"], 0)

    def test_protobuf_identity_classifier_and_nested_type_parser_are_exact(self):
        self.assertEqual(
            audit.protobuf_identity_field_classes("missionId_"),
            {"mission_or_quest"},
        )
        self.assertEqual(
            audit.protobuf_identity_field_classes("scriptId_"),
            {"level_script"},
        )
        self.assertEqual(
            audit.protobuf_identity_field_classes("sceneName_"),
            {"scene_host"},
        )
        self.assertEqual(
            audit.protobuf_identity_field_classes("dialogId_"),
            {"story"},
        )
        self.assertEqual(
            audit.protobuf_identity_field_classes("requestId_"),
            set(),
        )
        self.assertEqual(
            audit.protobuf_identity_field_classes("soilRequestId_"),
            set(),
        )
        self.assertEqual(
            audit.protobuf_identity_field_classes("cutsceneId_"),
            {"story"},
        )
        known = {"Proto.MISSION", "Proto.QUEST", "Proto.UNRELATED"}
        self.assertEqual(
            audit.protobuf_runtime_dependencies(
                "Google.Protobuf.Collections.MapField<string, Proto.MISSION>",
                known,
            ),
            ["Proto.MISSION"],
        )
        self.assertEqual(
            audit.protobuf_runtime_dependencies(
                "System.Tuple<Proto.QUEST, Proto.MISSION>",
                known,
            ),
            ["Proto.MISSION", "Proto.QUEST"],
        )

    def test_state_update_application_validation_accepts_generic_same_identity_flow(self):
        validation = audit.validate_state_update_application_rows(
            1,
            [{
                "type": "Proto.SC_FIXTURE_STATE_UPDATE",
                "samePacketIdentityForwardedToEveryLifecycleCall": True,
                "clientSuccessorSelectorPresent": False,
                "lifecycleCalls": [{
                    "method": "StartFixture",
                    "samePacketIdentity": True,
                    "observedArgumentOrigin": "param:msg+0x18",
                }],
            }],
            source_file="GameAssembly.dll",
            source_hashes={"gameAssemblySha256": "fixture"},
        )

        self.assertEqual(validation, {"status": "validated", "failures": []})

    def test_state_update_application_validation_reports_bounded_drift(self):
        validation = audit.validate_state_update_application_rows(
            1,
            [{
                "type": "Proto.SC_FIXTURE_STATE_UPDATE",
                "samePacketIdentityForwardedToEveryLifecycleCall": False,
                "clientSuccessorSelectorPresent": True,
                "successorLikeFields": ["nextFixtureId"],
                "lifecycleCalls": [{
                    "method": "StartFixture",
                    "samePacketIdentity": False,
                    "observedArgumentOrigin": "param:msg+0x30",
                }],
            }],
            source_file="GameAssembly.dll",
            source_hashes={"gameAssemblySha256": "fixture"},
        )

        self.assertEqual(validation["status"], "validation_failed")
        self.assertEqual(
            [failure["gate"] for failure in validation["failures"]],
            ["sameIdentityForwarding", "noClientSuccessorSelector"],
        )
        self.assertEqual(validation["failures"][0]["message"], "Proto.SC_FIXTURE_STATE_UPDATE")
        self.assertEqual(validation["failures"][0]["expected"], True)
        self.assertEqual(
            validation["failures"][0]["actual"],
            [{"method": "StartFixture", "origin": "param:msg+0x30"}],
        )
        self.assertEqual(validation["failures"][0]["sourceFile"], "GameAssembly.dll")


if __name__ == "__main__":
    unittest.main()

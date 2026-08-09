"""Build the experimental Mission Pipeline graph payload for the static WebUI.

The payload keeps authored MissionRuntimeAsset structure separate from native
runtime conclusions.  Predecessor edges are prerequisites visible in exported
data; they are never promoted to proof that the client chooses a successor.

Run from the repository root:
    python scripts/build_mission_pipeline_data.py
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any, Iterable

try:
    from common import (
        combined_non_mission_content_keys,
        compact_dict,
        read_bytes_cached,
        read_json,
        story_root_playback_aliases,
        write_report_json,
        write_text_if_changed,
    )
    from story_builder.levelscript_binary import (
        compact_callserver_serialized_contract,
        decode_levelscript_action_map_lists,
        decode_levelscript_action_header_validation,
        decode_levelscript_encounter_module_target,
        extract_levelscript_uid_records,
    )
    from story_builder.level_bindings import (
        ACTIONBASE_FORMATTER_ACTION_NAMES,
        ACTIONBASE_FORMATTER_NAME_AUDIT,
        build_levelscript_native_story_playback_index,
        decode_levelscript_native_action_topology,
    )
    from story_builder.mission_assets import (
        mission_runtime_source_summary,
        select_complete_mission_runtime_root,
    )
    from story_recovery.build_envtalk_attachment import (
        build_report as build_envtalk_attachment_report,
    )
    from story_recovery.build_callserver_callback_audit import (
        DEFAULT_JSON as CALLSERVER_CALLBACK_AUDIT_JSON,
        DEFAULT_MARKDOWN as CALLSERVER_CALLBACK_AUDIT_MARKDOWN,
        build_report as build_callserver_callback_audit_report,
        markdown_report as render_callserver_callback_audit_markdown,
    )
    from story_recovery.build_dialog_finish_branch_audit import (
        DEFAULT_JSON as DIALOG_FINISH_BRANCH_AUDIT_JSON,
        DEFAULT_MARKDOWN as DIALOG_FINISH_BRANCH_AUDIT_MARKDOWN,
        build_report as build_dialog_finish_branch_audit_report,
        markdown_report as render_dialog_finish_branch_audit_markdown,
        publish_to_pipeline_index as publish_dialog_finish_branch_audit,
    )
    from story_recovery.build_mission_dependency_graph import (
        build_report as build_mission_dependency_graph_report,
    )
    from story_recovery.build_node_attachment_coverage import (
        build_report as build_node_attachment_report,
        render_markdown as render_node_attachment_markdown,
    )
    from story_recovery.build_native_receiver_activation_frontier import (
        DEFAULT_JSON as NATIVE_RECEIVER_FRONTIER_JSON,
        DEFAULT_MANUAL_CONTROL_AUDIT as NATIVE_RECEIVER_MANUAL_CONTROL_AUDIT,
        DEFAULT_MARKDOWN as NATIVE_RECEIVER_FRONTIER_MARKDOWN,
        build_report as build_native_receiver_activation_frontier_report,
        markdown_report as render_native_receiver_activation_frontier_markdown,
        publish_to_pipeline_index as publish_native_receiver_activation_frontier,
    )
    from story_recovery.build_source_story_partial_order import (
        build_report as build_source_story_partial_order_report,
        render_markdown as render_source_story_partial_order_markdown,
    )
    from story_recovery.build_source_story_order_cross_reference import (
        build_report as build_source_story_order_cross_reference_report,
        render_markdown as render_source_story_order_cross_reference_markdown,
    )
    from story_recovery.build_timeline_embedded_story_runtime_audit import (
        DEFAULT_JSON as TIMELINE_EMBEDDED_RUNTIME_JSON,
        DEFAULT_MD as TIMELINE_EMBEDDED_RUNTIME_MARKDOWN,
        build_default_report as build_timeline_embedded_runtime_report,
        render_markdown as render_timeline_embedded_runtime_markdown,
    )
except ModuleNotFoundError:  # imported as ``scripts.build_mission_pipeline_data``
    from scripts.common import (
        combined_non_mission_content_keys,
        compact_dict,
        read_bytes_cached,
        read_json,
        story_root_playback_aliases,
        write_report_json,
        write_text_if_changed,
    )
    from scripts.story_builder.levelscript_binary import (
        compact_callserver_serialized_contract,
        decode_levelscript_action_map_lists,
        decode_levelscript_action_header_validation,
        decode_levelscript_encounter_module_target,
        extract_levelscript_uid_records,
    )
    from scripts.story_builder.level_bindings import (
        ACTIONBASE_FORMATTER_ACTION_NAMES,
        ACTIONBASE_FORMATTER_NAME_AUDIT,
        build_levelscript_native_story_playback_index,
        decode_levelscript_native_action_topology,
    )
    from scripts.story_builder.mission_assets import (
        mission_runtime_source_summary,
        select_complete_mission_runtime_root,
    )
    from scripts.story_recovery.build_envtalk_attachment import (
        build_report as build_envtalk_attachment_report,
    )
    from scripts.story_recovery.build_callserver_callback_audit import (
        DEFAULT_JSON as CALLSERVER_CALLBACK_AUDIT_JSON,
        DEFAULT_MARKDOWN as CALLSERVER_CALLBACK_AUDIT_MARKDOWN,
        build_report as build_callserver_callback_audit_report,
        markdown_report as render_callserver_callback_audit_markdown,
    )
    from scripts.story_recovery.build_dialog_finish_branch_audit import (
        DEFAULT_JSON as DIALOG_FINISH_BRANCH_AUDIT_JSON,
        DEFAULT_MARKDOWN as DIALOG_FINISH_BRANCH_AUDIT_MARKDOWN,
        build_report as build_dialog_finish_branch_audit_report,
        markdown_report as render_dialog_finish_branch_audit_markdown,
        publish_to_pipeline_index as publish_dialog_finish_branch_audit,
    )
    from scripts.story_recovery.build_mission_dependency_graph import (
        build_report as build_mission_dependency_graph_report,
    )
    from scripts.story_recovery.build_node_attachment_coverage import (
        build_report as build_node_attachment_report,
        render_markdown as render_node_attachment_markdown,
    )
    from scripts.story_recovery.build_native_receiver_activation_frontier import (
        DEFAULT_JSON as NATIVE_RECEIVER_FRONTIER_JSON,
        DEFAULT_MANUAL_CONTROL_AUDIT as NATIVE_RECEIVER_MANUAL_CONTROL_AUDIT,
        DEFAULT_MARKDOWN as NATIVE_RECEIVER_FRONTIER_MARKDOWN,
        build_report as build_native_receiver_activation_frontier_report,
        markdown_report as render_native_receiver_activation_frontier_markdown,
        publish_to_pipeline_index as publish_native_receiver_activation_frontier,
    )
    from scripts.story_recovery.build_source_story_partial_order import (
        build_report as build_source_story_partial_order_report,
        render_markdown as render_source_story_partial_order_markdown,
    )
    from scripts.story_recovery.build_source_story_order_cross_reference import (
        build_report as build_source_story_order_cross_reference_report,
        render_markdown as render_source_story_order_cross_reference_markdown,
    )
    from scripts.story_recovery.build_timeline_embedded_story_runtime_audit import (
        DEFAULT_JSON as TIMELINE_EMBEDDED_RUNTIME_JSON,
        DEFAULT_MD as TIMELINE_EMBEDDED_RUNTIME_MARKDOWN,
        build_default_report as build_timeline_embedded_runtime_report,
        render_markdown as render_timeline_embedded_runtime_markdown,
    )


ROOT = Path(__file__).resolve().parents[1]
STREAMING_MISSION_ROOT = (
    ROOT / "export_full" / "structured" / "StreamingAssets" / "Data" / "Json" / "MissionRuntimeAsset"
)
PERSISTENT_MISSION_ROOT = (
    ROOT / "export_full" / "structured" / "Persistent" / "Data" / "Json"
    / "MissionRuntimeAsset"
)
DEFAULT_MISSION_ROOT = select_complete_mission_runtime_root(
    STREAMING_MISSION_ROOT,
    PERSISTENT_MISSION_ROOT,
)
DEFAULT_SUBGAME_TABLE = (
    ROOT
    / "export_full"
    / "structured"
    / "StreamingAssets"
    / "Data"
    / "Json"
    / "GameplayConfig"
    / "SubGameInstanceDataTable.json"
)
DEFAULT_TABLE_ROOT = ROOT / "export_full" / "structured" / "StreamingAssets" / "Table"
DEFAULT_GAMEPLAY_CONFIG_ROOT = (
    ROOT / "export_full" / "structured" / "StreamingAssets" / "Data" / "Json" / "GameplayConfig"
)

# Shipped Lua is scanned as a corpus. No Story key, module, symbol, or phase is
# admitted here by hand: the current audit enumerates bounded GameAction calls,
# resolves only direct/module-constant first arguments, and fingerprints the
# exact original Lua bytes. The installed-binary audit supplies the native
# spelling boundary used for case-mismatch rejection.
DEFAULT_LUA_CONSUMER_REFERENCE_AUDIT = (
    ROOT / "reports" / "mission_order" / "lua_consumer_reference_audit.json"
)
DEFAULT_SCRIPT_TASK_EXTRA_INFO_TABLE = (
    DEFAULT_GAMEPLAY_CONFIG_ROOT / "ScriptTaskExtraInfoTable.json"
)
DEFAULT_LEVEL_SCRIPT_DATA_ROOT = (
    ROOT / "export_full" / "structured" / "StreamingAssets" / "Data" / "Json"
    / "LevelScriptData"
)
DEFAULT_PERSISTENT_LEVEL_SCRIPT_DATA_ROOT = (
    ROOT / "export_full" / "structured" / "Persistent" / "Data" / "Json"
    / "LevelScriptData"
)
DEFAULT_LEVEL_SCRIPT_DATA_ROOTS = (
    DEFAULT_LEVEL_SCRIPT_DATA_ROOT,
    DEFAULT_PERSISTENT_LEVEL_SCRIPT_DATA_ROOT,
)
DEFAULT_PROTOCOL_REGISTRY_AUDIT = (
    ROOT / "reports" / "story" / "recovery" / "protocol_registry_audit.json"
)
DEFAULT_NATIVE_CROSS_SYSTEM_CONSUMER_CENSUS = (
    ROOT / "reports" / "story" / "recovery"
    / "native_cross_system_consumer_census.json"
)
DEFAULT_CUTSCENE_CASE_RESOLUTION_AUDIT = (
    ROOT / "reports" / "story" / "recovery" / "cutscene_case_resolution_audit.json"
)
LUA_CONSUMER_REFERENCE_SCHEMA = "luaConsumerReferenceAudit.v4"
NATIVE_GAME_ACTION_TYPE = "Beyond.Gameplay.Actions.GameAction"
DEFAULT_ACTIVITY_STAGE_TABLE = DEFAULT_TABLE_ROOT / "ActivityConditionalMultiStageTable.json"
DEFAULT_ACTIVITY_DUNGEON_FIGHTING_STAGE_TABLE = (
    DEFAULT_TABLE_ROOT / "ActivityDungeonFightingStageTable.json"
)
DEFAULT_ACTIVITY_SNAPSHOT_STAGE_TABLE = (
    DEFAULT_TABLE_ROOT / "ActivitySnapShotStageTable.json"
)
DEFAULT_GAME_MECHANIC_CONDITION_TABLE = DEFAULT_TABLE_ROOT / "GameMechanicConditionTable.json"
DEFAULT_DUNGEON_TABLE = DEFAULT_TABLE_ROOT / "DungeonTable.json"
DEFAULT_TEXT_VO_ID_TABLE = DEFAULT_TABLE_ROOT / "TextVoIdTable.json"
DEFAULT_SUBMIT_ITEM_TABLE = DEFAULT_TABLE_ROOT / "SubmitItem.json"
DEFAULT_OUTPUT_ROOT = ROOT / "webui" / "data" / "mission_pipeline"
DEFAULT_LEVEL_SEQUENCE_TEXTASSET_ROOT = (
    ROOT
    / "export_full"
    / "recovered"
    / "AnimeStudio-cli"
    / "StreamingAssets"
    / "json_by_type"
    / "TextAsset"
)
DEFAULT_STORY_DATA_ROOT = ROOT / "webui" / "data" / "lang"
DEFAULT_REPORT_ROOT = ROOT / "reports" / "story" / "build"
DEFAULT_ORDER_REPORT_ROOT = ROOT / "reports" / "mission_order"
DEFAULT_STORY_ORDER_OVERRIDE = ROOT / "webui" / "overrides" / "story_order.json"
DEFAULT_STORY_ORDER_OCR = ROOT / "webui" / "data" / "story_order_ocr.json"
DEFAULT_MISSION_GRAPH_REPORT_ROOT = ROOT / "reports" / "mission_graph"
DEFAULT_SOURCE_STORY_GAP_QUEUE = (
    DEFAULT_ORDER_REPORT_ROOT / "source_story_gap_queue_CN.json"
)
SOURCE_STORY_GAP_QUEUE_SCHEMA = "sourceStoryGapQueue.v130"
DEFAULT_DYNAMIC_SCENE_MISSION_CONTROL_AUDIT = (
    ROOT
    / "reports"
    / "story"
    / "recovery"
    / "dynamic_scene_mission_control_audit.json"
)
DEFAULT_DYNAMIC_SCENE_LEVELSCRIPT_ACTION_BRIDGE_AUDIT = (
    ROOT
    / "reports"
    / "story"
    / "recovery"
    / "dynamic_scene_levelscript_action_bridge_audit.json"
)
MISSION_RUNTIME_TRACE_SCHEMA = "missionRuntimeTrace.v1"
# v3 added per-mission ``missionGraph`` and quest-tracked ambient lines. v4
# extends ``envTalkContext`` with exact atmospheric-switcher state context. v5
# adds the recursive protobuf identity-carrier census and closes
# roleBaseInfo.sceneName as position-reconciliation context. v6 adds exact
# LevelData AirWall mission/quest-state-gated radio playback contexts. v7
# records the bounded MissionOptionData alternate-action carrier result. v8
# closes the Mission property -> ParamVariable.m_scriptPtr nested-type
# candidate as runtime LevelScript subscription context. v10 closes the
# implicit ParamSource.CURRENT_MISSION_ID candidate across the complete
# authored MissionRuntime and LevelScript action surfaces. v10 closes the
# complete direct managed mission/quest identity co-carrier census and proves
# the remaining mission/scene pair is HUD/map tracking context. v11 closes the
# nested managed-carrier census. v12 recovers the shipped XLua pending-item
# submitter producer. v13 adds exact authored quest-to-submission requirements
# while keeping same-objective dialog co-gates distinct from UI ownership.
# v14 adds exact same-objective SubmitItem + LevelScript-stage co-gates and
# preserves their dialog playback context as non-owning evidence.
# v15 adds freshness-checked CutsceneRoot playback-alias routes while
# preserving their explicit mission-owner and chronology gaps.
# v16 composes an alias with an independently connected root playback route;
# the composition recovers owner context without creating Story chronology.
# v17 preserves authored quest tracking markers, visibility filters, and
# mission-variable defaults as debug context without creating graph edges.
# v18 pins the native tracking-property evaluator and server-sync path while
# preserving the unknown server producer/timing boundary. v19 adds exact
# top-level LevelScript narrative-interactive configuration routes. v20 adds
# next-record-bounded LevelData narrative-interactive configuration routes.
# v21 admits final records only through the exact LevelData member-21/member-22
# boundary and retains that boundary provenance in trigger routes.
# v22 retains exact decoded mission/quest-state progress locks on LevelData
# narrative-interactive routes without treating their owner ids as Story
# ownership or chronology.
# v23 retains nested combined-condition structure and raw NotEqual leaves.
# v24 admits final environment-only LevelData rows through the exact complete
# empty-script member suffix and retains its boundary provenance.
# v25 admits an exact authored ``int_horn.properties.dialog_id`` consumer with
# current-template/native provenance while preserving the ownership/order gap.
# v26 attaches hash-verified current-game DialogTree definitions to their exact
# objective, repeatable-talk, and failed-dialog MissionRuntime observers. v27
# exposes exact typed spaceship contexts whose complete table definition has
# no carrier in any related typed DialogTree, without inventing playback. v28
# exposes typed receiver-local control after playback. v29 publishes exact
# typed source-to-target Story transition suffixes and their branch classes.
# v30 closes the post-playback variable-setter route against every exact
# property/blackboard Story receiver and publishes the bounded result. v31
# resolves typed post-playback LevelSequence action ids to internally validated
# original TextAssets without using their names as mission/order evidence. v32
# names the complete ActionBase surface through one hash-validated formatter
# table recovered from the installed binary. v40 joins exact receiver headers
# to their serialized Active/Start phase and the binary-validated registration
# lifecycle while preserving the unresolved public-Active producer boundary.
# v41 joins the exact LevelData LevelScriptType to the binary activation
# selector and exposes the client-produced active=true branch without treating
# the server-side rule choosing public Enabled, its spatial outcome, or server
# acceptance as mission evidence.
# v42 decodes the authored active volume generically and joins it to the binary
# inside/outside gate while keeping the runtime player-position result unknown.
# v43 distinguishes the full-scene LevelScript snapshot from incremental public
# state notifications and publishes their closed current-AOT application paths.
# v45 retains every complete authored scene/script/task condition tuple and
# fail-closed joins it to the original task table and LevelScript source. v46
# attaches the generic binary-decoded typed-control topology observed by each
# authored LevelScript condition, without promoting it to Story ownership/order.
SCHEMA_VERSION = 46
PIPELINE_STORY_KINDS = {"dlg", "sns", "cutscene", "black", "remotecomm", "radio"}
PIPELINE_VISIBLE_NON_MISSION_EVIDENCE_KINDS = {
    "guide_runtime_asset",
    "spaceship_dialog_tree",
    "character_profile_voice",
    "spaceship_dialog_definition_without_tree_carrier",
}
BATTLE_SIGNAL_PRODUCER_MAPPING_ID = (
    "gameassembly-2026-07-22-ability-actiondata-0x0134"
)
BATTLE_SIGNAL_RECEIVER_MAPPING_ID = (
    "gameassembly-2026-07-11-cr-0x18b9217d0-actionheader"
)
BATTLE_SIGNAL_PAYLOAD_MAPPING_ID = (
    "gameassembly-2026-07-17-memorypack-native-event-fields"
)


RUNTIME_CONTRACT = {
    "authority": {
        "owner": "server",
        "summary": (
            "The examined client applies synchronized quest states. It does not use "
            "prevQuestIdList or flowIndex to choose the next quest."
        ),
        "boundary": (
            "Predecessor and condition edges explain prerequisites visible to the client, "
            "not the server's complete authored successor policy."
        ),
        "nativeScope": (
            "Addresses and control flow describe the installed build. IFix dispatch can "
            "replace methods in principle. The current installed Gameplay.Beyond patch was "
            "fully parsed at 30 targets and contains no receiver-ownership or LevelScript "
            "task registration/completion target or explicit reference."
        ),
        "protocolAudit": "reports/story/recovery/protocol_registry_audit.json",
        "protocolBoundary": (
            "The complete current-build CS/SC enum and selected protobuf schemas are an "
            "identity inventory only. Message names and fields do not create mission "
            "ownership, ordering, branch, or merge edges."
        ),
    },
    "serverPlaceholder": {
        "type": "Beyond.Gameplay.GameConditionServerPlaceHolder",
        "conditionTypeFallback": 2147483647,
        "clientOnlyConditionType": 9999,
        "conditionTypeAddress": "0x18479ec70",
        "startQuestBinderAddress": "0x183a89700",
        "identityFields": ["questId", "conditionId"],
        "outboundMessage": None,
        "inboundMessage": "SC_QUEST_OBJECTIVES_UPDATE (116)",
        "inboundFields": [
            "questId",
            "questObjectives[].conditionId",
            "questObjectives[].extraDetails",
            "questObjectives[].values",
            "questObjectives[].isComplete",
            "questObjectives[].descriptionIndex",
        ],
        "finding": (
            "The installed-build fallback returns int.MaxValue, not ClientOnly (9999). "
            "MissionSystem.StartQuest therefore does not bind the placeholder to the "
            "client ResultChange callback and this condition does not send "
            "CS_UPDATE_QUEST_OBJECTIVE. Server progress is applied by the composite "
            "(questId, conditionId) key."
        ),
        "patchBoundary": (
            "The current installed Gameplay.Beyond patch has 30 signature targets and "
            "matches none of patch ids 0x5605, 0x54d1, or 0x54d2. Future patches can "
            "change that result, so rebuild-scoped audits must still fail closed."
        ),
        "installedPatch": {
            "source": "Persistent VFS: Data/IFixPatchOut/Windows/Gameplay.Beyond.patch.bytes",
            "size": 82021,
            "sha256": "737134081e06371f13c073988547e887037fccf2f57e1052be35dd255d27bc21",
            "signatureTargetCount": 30,
            "relevantPatchIds": ["0x5605", "0x54d1", "0x54d2"],
            "matchedRelevantPatchIds": [],
            "taskCompletionTargetMatches": 0,
            "taskCompletionExplicitReferenceMatches": 0,
            "receiverOwnershipTargetMatches": 0,
            "receiverOwnershipExplicitReferenceMatches": 0,
            "missionHudTargets": 2,
            "dialogCinematicTargets": 7,
            "auditReport": "reports/story/recovery/current_ifix_mission_graph_audit.json",
        },
        "confidence": "native_proven",
    },
    "teleportMissionScriptCarrier": {
        "type": "Beyond.Gameplay.TeleportParam",
        "size": "0x38",
        "layout": {
            "source": "0x00",
            "uiType": "0x04",
            "options": "0x08",
            "resetMap": "0x0c",
            "callbackHandle": "0x10",
            "missionId": "0x18",
            "levelScriptId": "0x20",
            "actionId": "0x28",
            "performId": "0x30",
        },
        "metadataCandidateCount": 20,
        "directCallerCensus": {
            "GameLevelLoader.OpenLevel": 2,
            "GameLevelLoader.LoadAtPos": 1,
            "GameLevelLoader.LoadAtPosInCurrentMap": 2,
            "SquadManager.ServerTeleportSquad": 1,
            "LoadingPipeline.get_teleportParam": 2,
        },
        "producerFinding": (
            "The current direct AOT producers either zero all 0x38 bytes or populate only "
            "source/UI/options/reset/callback fields. The server pass-through decoder "
            "explicitly leaves missionId, levelScriptId, actionId, and performId zero, so "
            "no audited producer co-populates missionId and levelScriptId."
        ),
        "consumerFinding": (
            "LoadFinishStep consumes source with levelScriptId/actionId for the local "
            "teleport-finish LevelScript event, or source with callbackHandle for the "
            "callback lane. PerformerFactory consumes performId. No audited current "
            "consumer reads missionId."
        ),
        "finding": (
            "Although this was the sole new actionable type in a 20-type nominal "
            "mission/script co-carrier census, its missionId field is unused on the "
            "audited current loading paths and creates no mission ownership or order edge."
        ),
        "patchBoundary": (
            "The current 30-target Gameplay.Beyond IFix payload does not target the "
            "audited TeleportProcessor, GameLevelLoader, LoadingPipeline, or "
            "PerformerFactory methods. Future patches and unresolved indirect, reflection, "
            "or XLua construction remain outside this bounded result."
        ),
        "storyBindingsAdded": 0,
        "confidence": "native_proven_bounded",
    },
    "levelScriptCtxTokenAudit": {
        "serverMessage": "SC_SCENE_TRIGGER_CLIENT_LEVEL_SCRIPT_EVENT (57)",
        "clientMessage": "CS_SCENE_LEVEL_SCRIPT_EVENT_TRIGGER (55)",
        "paramBlackboardKeySlot": "0x18e2eef08",
        "directKeySlotReferences": 4,
        "referencingMethods": [
            "Beyond.Gameplay.GameplayNetwork._Handle_SceneTriggerClientLevelScriptEvent",
            "Beyond.Gameplay.Actions.CallServer.Execute",
        ],
        "writer": {
            "symbol": (
                "Beyond.Gameplay.GameplayNetwork."
                "_Handle_SceneTriggerClientLevelScriptEvent"
            ),
            "address": "0x187386320",
            "operation": "ParamBlackboard.SetValue(ctxToken)",
        },
        "reader": {
            "symbol": "Beyond.Gameplay.Actions.CallServer.Execute",
            "address": "0x1845f6000",
            "operation": "ParamBlackboard.TryGetValue(netToken)",
        },
        "outboundPath": [
            "Beyond.Gameplay.Actions.GameAction.TriggerServerEvent(..., netToken)",
            "Beyond.Gameplay.GameplayNetwork.TriggerLevelScriptServerEvent(..., netToken)",
            "Proto.CS_SCENE_LEVEL_SCRIPT_EVENT_TRIGGER.set_CtxToken",
        ],
        "finding": (
            "The sole current direct AOT reader of message 57's blackboard key names "
            "the recovered value netToken and returns it on a client-to-server "
            "LevelScript event. This is a server-event round-trip/correlation lane, not "
            "a mission, quest, condition, or Story identity carrier."
        ),
        "patchBoundary": (
            "The current 30-target Gameplay.Beyond IFix payload targets none of the "
            "handler, CallServer.Execute, GameAction.TriggerServerEvent, or "
            "GameplayNetwork.TriggerLevelScriptServerEvent methods. Direct references "
            "through a separately constructed equal key, reflection, native memory "
            "manipulation, future IFix, and future builds remain outside this bound."
        ),
        "storyBindingsAdded": 0,
        "confidence": "native_proven_bounded",
    },
    "protobufIdentityCarrierAudit": {
        "source": "reports/story/recovery/protocol_registry_audit.json",
        "coverage": {
            "protoTypeDefinitions": 3743,
            "csScTypeDefinitions": 1983,
            "registryEntries": 1186,
            "registryMessageTypes": 983,
            "fieldBearingRegistryMessageTypes": 936,
            "missionOrQuestMessageTypes": 33,
            "levelScriptMessageTypes": 29,
        },
        "exactMissionScriptOrStoryCandidateCount": 0,
        "weakMissionSceneCandidateCount": 3,
        "weakCandidates": [
            {
                "message": "CS_MISSION_CLIENT_TRIGGER_DONE (317)",
                "fields": ["missionId", "sceneName"],
                "classification": "inactive_current_fallback_sender",
                "finding": (
                    "The schema co-carries the fields, but the current fallback has no "
                    "gameplay constructor/sender and the installed IFix adds none."
                ),
            },
            {
                "message": "SC_MISSION_STATE_UPDATE (112)",
                "fields": ["missionId", "roleBaseInfo.sceneName"],
                "classification": "role_snapshot_position_correction",
            },
            {
                "message": "SC_QUEST_STATE_UPDATE (111)",
                "fields": ["questId", "roleBaseInfo.sceneName"],
                "classification": "role_snapshot_position_correction",
            },
        ],
        "roleSnapshotConsumer": {
            "handlers": [
                {
                    "symbol": "MissionSystem.Handle_MissionStateUpdate",
                    "token": "0x060052a2",
                    "address": "0x1873be300",
                    "fallbackPatchId": "0x5ec5",
                },
                {
                    "symbol": "MissionSystem.Handle_QuestStateUpdate",
                    "token": "0x0600529e",
                    "address": "0x1873bf0a0",
                    "fallbackPatchId": "0x5ebe",
                },
            ],
            "symbol": "MissionSystem.CharacterPositionCorrection",
            "token": "0x0600527b",
            "address": "0x1873b84c4",
            "fallbackPatchId": "0x5ea7",
            "fields": [
                "roleBaseInfo.leaderPosition",
                "roleBaseInfo.leaderRotation",
                "roleBaseInfo.sceneName",
            ],
            "finding": (
                "The handlers use the role snapshot to reconcile the player's map and "
                "position. sceneName is not retained as an authored mission/quest scene "
                "host and creates no Story ownership or order edge."
            ),
        },
        "installedPatch": {
            "sha256": "737134081e06371f13c073988547e887037fccf2f57e1052be35dd255d27bc21",
            "signatureTargetCount": 30,
            "relevantPatchIds": ["0x5ec5", "0x5ebe", "0x5ea7"],
            "matchedMethods": 0,
        },
        "finding": (
            "Recursive typed-field traversal across every current enum-backed CS/SC "
            "message found no mission/quest + LevelScript/Story identity co-carrier. "
            "The only weaker scene carriers are one inactive sender and two operational "
            "role-position snapshots."
        ),
        "boundary": (
            "Opaque bytes, dynamic parameter values, server-only schemas, native memory "
            "construction, future IFix, and future builds remain outside this bound."
        ),
        "storyBindingsAdded": 0,
        "confidence": "native_proven_bounded",
    },
    "missionOptionCarrierAudit": {
        "source": "reports/story/recovery/mission_option_carrier_audit.json",
        "managedCarrier": {
            "type": "Beyond.Gameplay.MissionOptionData",
            "typeToken": "0x02000986",
            "baseType": "Beyond.Gameplay.DialogTreeOptionBase",
            "fields": [
                {
                    "name": "missionId",
                    "token": "0x04003bcd",
                    "type": "string",
                    "offset": "0x68",
                },
                {
                    "name": "callDialogId",
                    "token": "0x04003bce",
                    "type": "string",
                    "offset": "0x70",
                },
            ],
            "handlerType": {
                "enum": "Beyond.Gameplay.DialogEnums+OptionHandlerType",
                "value": 3,
                "name": "Mission",
            },
        },
        "nativeConsumer": {
            "symbol": "Beyond.Gameplay.Core.MissionOptionHandler._DoAction",
            "token": "0x0600fa1a",
            "address": "0x186e510a4",
            "fallbackPatchId": "0xc337",
            "callDialogBranch": (
                "when callDialogId is non-empty, call "
                "DialogManager.StopAndPlayDialogById(callDialogId), then jump to end"
            ),
            "missionBranch": (
                "only when callDialogId is empty and missionId is non-empty, call "
                "MissionSystem.AcceptMission(missionId)"
            ),
        },
        "authoredInstanceSearch": {
            "monoBehaviourRows": 1325026,
            "monoBehaviourBytes": 3240614105,
            "textAssets": 8195,
            "textAssetScriptBytes": 687580854,
            "structuredJsonFiles": 179925,
            "installedLuaFiles": 1291,
            "installedLuaBytes": 20161714,
            "matches": 0,
        },
        "wholeBinaryDirectCallCensus": {
            "MissionOptionDataConstructor": 0,
            "MissionOptionDataHandlerTypeGetter": 0,
            "MissionOptionHandlerDoAction": 2,
            "doActionCallers": [
                "MissionOptionHandler.OnSelectWhenDialogEnd",
                "MissionOptionHandler.OnSelectWhenOptionEnd",
            ],
        },
        "installedPatch": {
            "sha256": "737134081e06371f13c073988547e887037fccf2f57e1052be35dd255d27bc21",
            "signatureTargetCount": 30,
            "matchedMethods": 0,
        },
        "finding": (
            "missionId and callDialogId are mutually exclusive action alternatives "
            "in the current native fallback. Their co-carriage creates no "
            "mission-to-dialog causality, Story ownership, or order edge."
        ),
        "boundary": (
            "No exact authored instance exists in current exported MonoBehaviour, "
            "TextAsset, structured JsonData, or installed Lua surfaces. Reflection, "
            "dynamically constructed names, server-only construction, unexported "
            "object kinds, future IFix, and future builds remain possible."
        ),
        "classification": "schema_only_current_export_absent",
        "storyBindingsAdded": 0,
        "confidence": "native_proven_bounded",
    },
    "missionPropertyScriptPtrAudit": {
        "source": "reports/story/recovery/mission_property_scriptptr_audit.json",
        "managedLayout": {
            "MissionRuntimeAsset": {
                "missionId": {"token": "0x04003206", "offset": "0x10"},
                "properties": {"token": "0x04003224", "offset": "0xe0"},
                "propertyDic": {"token": "0x0400322b", "offset": "0xf8"},
            },
            "MissionSystem+MissionData": {
                "missionId": {"token": "0x0400487f", "offset": "0x10"},
                "propertyDict": {"token": "0x04004882", "offset": "0x20"},
            },
            "ParamVariable": {
                "m_sendToScript": {"token": "0x040038d4", "offset": "0x68"},
                "m_scriptPtr": {"token": "0x040038d5", "offset": "0x70"},
            },
        },
        "authoredMissionProperties": {
            "missionFiles": 490,
            "missionsWithProperties": 71,
            "propertyRows": 217,
            "uniquePropertyKeys": 189,
            "valueTypeCounts": {"1": 10, "3": 207},
            "serializedFieldKeys": [
                "key",
                "type",
                "value",
                "valueArray",
                "valueBit64",
                "valueString",
            ],
            "levelScriptPointerFieldRows": 0,
        },
        "trackingPropertyFilterRuntime": {
            "conditionType": (
                "Beyond.Gameplay.SimpleConditionCheckMissionVariableInt"
            ),
            "authoredRows": 204,
            "authoredMissions": 46,
            "authoredVariables": 110,
            "evaluator": {
                "symbol": (
                    "SimpleConditionCheckMissionVariableInt."
                    "GetResultWithoutListening"
                ),
                "token": "0x06004b72",
                "address": "0x18736e6b0",
                "flow": [
                    "MissionSystem.TryGetSaveProperty(missionId, missionVarName)",
                    "TableUtils.DoCompare(value, compareOperator, compareTarget)",
                ],
            },
            "listener": {
                "start": {
                    "symbol": (
                        "SimpleConditionCheckMissionVariableInt."
                        "InnerStartListening"
                    ),
                    "token": "0x06004b6f",
                    "address": "0x18736e8ec",
                    "operation": "EventManager.BindGlobal",
                },
                "end": {
                    "symbol": (
                        "SimpleConditionCheckMissionVariableInt."
                        "InnerEndListening"
                    ),
                    "token": "0x06004b70",
                    "address": "0x18736e7e8",
                    "operation": "EventManager.UnBindGlobal",
                },
                "onChange": {
                    "symbol": (
                        "SimpleConditionCheckMissionVariableInt."
                        "_OnMissionVarChange"
                    ),
                    "token": "0x06004b71",
                    "address": "0x18736ea90",
                    "operation": (
                        "match changed mission/property identity and "
                        "reevaluate the condition"
                    ),
                },
            },
            "serverUpdate": {
                "message": "SC_UPDATE_MISSION_PROPERTY (124)",
                "direction": "server_to_client",
                "fields": [
                    "missionId",
                    "properties{propertyId -> DYNAMIC_PARAMETER}",
                ],
                "handler": "MissionSystem.Handle_UpdateMissionProperty",
                "token": "0x060052a1",
                "address": "0x1873c02e4",
                "flow": [
                    "MissionPropertyKeyIdTable.TryGetPropertyKey",
                    "ParamVariableExtensions.ToVariable",
                    "MissionData.propertyDict.TryInsert",
                    "EventManager.SendGlobal",
                ],
            },
            "finding": (
                "Tracking filters are local conditions over server-synchronized "
                "MissionData.propertyDict values. They control marker/HUD "
                "visibility, but the exported client does not contain the "
                "server-side producer or timing rule for an individual property."
            ),
            "boundary": (
                "The exact client evaluator and inbound update path do not prove "
                "which server rule changes a property, when it changes, or that "
                "the change starts/completes a quest or plays Story."
            ),
            "classification": (
                "server_synchronized_tracking_visibility_no_graph_edge"
            ),
            "storyBindingsAdded": 0,
            "missionOrderEdgesAdded": 0,
        },
        "missionPropertyWriters": [
            {
                "symbol": "MissionSystem.Handle_SyncAllMission",
                "token": "0x0600529c",
                "address": "0x1833784e0",
                "toVariableOffset": "0x2044",
            },
            {
                "symbol": "MissionSystem.Handle_UpdateMissionProperty",
                "token": "0x060052a1",
                "address": "0x1873c02e4",
                "toVariableOffset": "0x2c8",
            },
            {
                "symbol": "MissionSystem.Handle_MissionStateUpdate",
                "token": "0x060052a2",
                "address": "0x1873be300",
                "toVariableOffset": "0x416",
            },
        ],
        "scriptPointerWriters": [
            {
                "symbol": (
                    "ParamVariable."
                    "SetupOnPropertyChangedEventForLevelScript"
                ),
                "token": "0x06003626",
                "address": "0x183be53e0",
                "managedDirectCallers": 2,
            },
            {
                "symbol": (
                    "ParamVariable."
                    "SetupOnBBVariableChangedEventForLevelScript"
                ),
                "token": "0x0600362d",
                "address": "0x1849832c0",
                "managedDirectCallers": 1,
                "unmappedNativeOrGenericCallers": 1,
            },
        ],
        "directCallCensus": {
            "ParamVariableExtensions.ToVariable": 7,
            "SetupOnPropertyChangedEventForLevelScript": 2,
            "SetupOnBBVariableChangedEventForLevelScript": 2,
            "missionSystemScriptPointerSetterCalls": 0,
        },
        "installedPatch": {
            "sha256": "737134081e06371f13c073988547e887037fccf2f57e1052be35dd255d27bc21",
            "signatureTargetCount": 30,
            "matchedMethods": 0,
        },
        "finding": (
            "The nested managed type shape is not a mission-to-LevelScript foreign "
            "key. Authored/server mission properties are converted into MissionData."
            "propertyDict, while m_scriptPtr is attached only by local LevelScript "
            "property/blackboard event subscription setup."
        ),
        "boundary": (
            "One BB setter callsite is native/generic with no mapped managed owner; "
            "its call shape carries a LevelScriptPtr and key but no mission identity. "
            "Indirect/delegate/reflection construction, unexported data, future IFix, "
            "and future builds remain outside the bound."
        ),
        "classification": "runtime_context_only_no_mission_levelscript_edge",
        "storyBindingsAdded": 0,
        "confidence": "native_proven_bounded",
    },
    "paramSourceMissionContextAudit": {
        "source": (
            "reports/story/recovery/param_source_mission_context_audit.json"
        ),
        "managedContract": {
            "enum": "Beyond.Gameplay.Actions.ParamSource",
            "currentMissionId": 1004,
            "paramType": "Beyond.Gameplay.Actions.Param<T>",
            "paramSourceFieldToken": "0x04006c3d",
            "contextFieldToken": "0x04006c41",
            "currentMissionGetterToken": "0x060091d6",
        },
        "authoredMissionRuntime": {
            "missionFiles": 490,
            "paramSourceOccurrences": 18,
            "currentMissionIdOccurrences": 18,
            "missions": 6,
            "actionTypes": {
                "CheckMissionBoolProperty": 1,
                "CheckMissionIntProperty": 17,
            },
            "storyPlaybackOperands": 0,
        },
        "authoredLevelScripts": {
            "levelScriptFiles": 4512,
            "uidRecords": 74839,
            "rawCurrentMissionIdValues": 0,
            "validatedParamTails": 0,
            "embeddedJsonCurrentMissionIdValues": 0,
        },
        "installedPatch": {
            "sha256": "737134081e06371f13c073988547e887037fccf2f57e1052be35dd255d27bc21",
            "signatureTargetCount": 30,
            "matchedMethods": 0,
        },
        "finding": (
            "CURRENT_MISSION_ID is a real implicit action-context source, but every "
            "current authored use is a MissionRuntime self-property check whose "
            "mission owner is already explicit. The complete LevelScript corpus "
            "contains no use, and no current use co-carries a Story playback id."
        ),
        "boundary": (
            "Server-only action graphs, opaque runtime-created Param objects, "
            "reflection/XLua construction, future IFix, and future builds remain "
            "outside the bound."
        ),
        "classification": (
            "implicit_context_only_missionruntime_no_levelscript_story_edge"
        ),
        "storyBindingsAdded": 0,
        "missionOrderEdgesAdded": 0,
        "confidence": "metadata_and_complete_authored_corpus_bounded",
    },
    "managedIdentityCarrierCensus": {
        "source": (
            "reports/story/recovery/managed_identity_carrier_census.json"
        ),
        "metadata": {
            "managedTypeCount": 63987,
            "directCandidateTypes": 10,
            "runtimeObjectCandidates": 8,
            "unreviewedCandidates": 0,
        },
        "authored": {
            "focusModeMissionRadioRows": 13,
            "focusModeUniqueRadios": 10,
            "npcProxyExMissionDialogRows": 453,
            "subGameMissionScriptRows": 20,
            "missionOptionAuthoredMatches": 0,
        },
        "trackingClosure": {
            "classification": "closed_tracking_ui_context",
            "commonTrackingFields": {
                "missionId": {
                    "token": "0x04003f3b",
                    "offset": "0x20",
                },
                "sceneId": {
                    "token": "0x04003f3d",
                    "offset": "0x30",
                },
            },
            "nativeConsumers": [{
                "symbol": "CommonTrackingPointInfoBase._UpdateVisible",
                "token": "0x0600403b",
                "address": "0x183482bb0",
            }, {
                "symbol": "CommonTrackingSystem.AddMissionTrack",
                "token": "0x0600407e",
                "address": "0x184792ac0",
            }, {
                "symbol": "TrackingInfoBase.ActivateTrackUnit",
                "token": "0x06004c8a",
                "address": "0x184792960",
            }],
            "finding": (
                "The mission/scene fields create and display a HUD/map tracking "
                "point. sceneId is mapped to the current system map for visibility, "
                "while missionId is stored on the tracking point; no audited method "
                "calls Story playback."
            ),
        },
        "finding": (
            "All ten direct managed mission/quest identity co-carrier types are "
            "reviewed. Productive FocusMode, NpcProxyEx, and SubGame pairs are "
            "already represented by their bounded evidence classes; the remaining "
            "object pairs and two apparent enum/static pairs add no new Story "
            "ownership or order edge."
        ),
        "boundary": (
            "Nested object graphs, indirect/reflection/XLua construction, opaque "
            "server-only state, unexported asset kinds, future IFix, and future "
            "builds remain outside the bound."
        ),
        "classification": "all_direct_managed_identity_carriers_reviewed",
        "storyBindingsAdded": 0,
        "missionOrderEdgesAdded": 0,
        "confidence": "metadata_and_native_consumers_bounded",
    },
    "nestedManagedIdentityCarrierCensus": {
        "source": (
            "reports/story/recovery/nested_managed_identity_carrier_census.json"
        ),
        "metadata": {
            "managedTypeRecords": 63987,
            "runtimeTypeEntries": 272743,
            "traversalMode": "cycle_safe_shortest_path_fixed_point",
            "maximumShortestPathDepth": 10,
            "maximumTraversedDepth": 10,
            "candidateTypes": 112,
            "directExactCandidateTypes": 11,
            "nestedDependentCandidateTypes": 101,
            "reviewedCandidateTypes": 112,
            "unreviewedCandidateTypes": 0,
        },
        "runtimeEntityHubClosure": {
            "classification": (
                "closed_runtime_entity_graph_reachability_without_serialized_instance_join"
            ),
            "hubType": "Beyond.Gameplay.Core.Entity",
            "candidateTypes": 86,
            "targetTypes": [
                "Beyond.Gameplay.Core.Entity",
                "Beyond.Gameplay.Core.InteractiveRootComponent",
                "Beyond.Gameplay.Core.NpcInteractComponent",
            ],
            "exactIndexedTypeLabels": 0,
            "indexedOriginalObjects": 1335450,
            "objectsWithTruncatedScalars": 1384,
            "finding": (
                "Eighty-six newly visible candidates reach their missing identity "
                "only through the mutable Entity/component graph. Installed metadata "
                "proves the type paths, while the complete original-object indexes "
                "expose no exact Entity/component script or scalar type label that "
                "can populate a mission/Story ownership join. The 1,384 rows with "
                "truncated scalar projections remain an explicit boundary."
            ),
        },
        "sharedRuntimeAggregateClosure": {
            "classification": (
                "closed_shared_runtime_aggregate_reachability_without_same_record_join"
            ),
            "candidateTypes": 1,
            "hubFamilies": [
                "runtime_entity_component_graph",
                "mission_runtime_property_or_action_graph",
            ],
            "finding": (
                "One mixed candidate reaches different identities through the "
                "Entity and MissionRuntime aggregate graphs; graph reachability "
                "does not make the independent manager records one authored row."
            ),
        },
        "relatedOriginalFiles": [{
            "sourceFile": (
                r"D:\Program Files\Endfield Game\GameAssembly.dll"
            ),
            "sha256": (
                "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
            ),
            "role": "native managed-field consumers",
        }, {
            "sourceFile": (
                r"D:\Program Files\Endfield Game\Endfield_Data\il2cpp_data\Metadata\global-metadata.dat"
            ),
            "sha256": (
                "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
            ),
            "role": "installed managed type graph",
        }, {
            "sourceFile": (
                "export_full/recovered/AnimeStudio-cli/StreamingAssets/"
                "object_index/objects.jsonl.gz"
            ),
            "sha256": (
                "6f59db82177cd1abd027bfed385145337403a5b0791bcb628287b53e1ad341cd"
            ),
            "role": "original StreamingAssets serialized-object census",
        }, {
            "sourceFile": (
                "export_full/recovered/AnimeStudio-cli/Persistent/"
                "object_index/objects.jsonl.gz"
            ),
            "sha256": (
                "65cd90a9f99d0da09ebcbd9de01e0b69960d513a857c5438de4272f5de1dd3bd"
            ),
            "role": "original Persistent serialized-object census",
        }],
        "pendingItemSubmitterClosure": {
            "classification": (
                "active_shipped_xlua_producer_with_exact_submission_context_without_ui_join"
            ),
            "fields": {
                "DialogManager.m_pendingItemSubmitter": {
                    "token": "0x0400b304",
                    "offset": "0x200",
                },
                "InventoryItemSubmitter.questId": {
                    "token": "0x04004759",
                    "offset": "0x20",
                },
            },
            "methods": [{
                "symbol": "InventoryItemSubmitter..ctor",
                "token": "0x060050ef",
                "address": "0x1873b0234",
                "nativeDirectCallerCount": 0,
            }, {
                "symbol": "InventoryItemSubmitter.TryGetSubmitMsg",
                "token": "0x060050f0",
                "address": "0x1873b0144",
                "nativeDirectCallerCount": 1,
            }, {
                "symbol": "DialogManager.RegisterPendingSubmission",
                "token": "0x0600f77e",
                "address": "0x186e17bc8",
                "nativeDirectCallerCount": 0,
            }],
            "nativeOpenUiBridge": {
                "callee": {
                    "symbol": "GameAction.DialogOpenUIPanel",
                    "token": "0x06008031",
                    "address": "0x1875e0224",
                    "nativeDirectCallerCount": 2,
                },
                "callers": [{
                    "symbol": "DialogManager.OpenUI",
                    "token": "0x0600f795",
                    "address": "0x186e145d8",
                }, {
                    "symbol": (
                        "BeyondGameplayActionsGameActionWrap."
                        "_m_DialogOpenUIPanel_xlua_st_"
                    ),
                    "token": "0x060033f2",
                    "address": "0x18630c078",
                }],
            },
            "shippedLuaProducer": {
                "logicalPath": (
                    "Data/LuaScripts/UI/Panels/SubmitItem/SubmitItemCtrl.lua"
                ),
                "sha256": (
                    "1c2a81f42d5512fc0bcfa35b78820d6482af15e2a2c8189fe85d81199286128e"
                ),
                "constructorAndRegistrationCalls": 1,
                "orderedConstructorArgumentMatches": 1,
                "constructorArguments": [
                    "scope",
                    "chapterId",
                    "submitId",
                    "questId",
                    "objId",
                    "instItems",
                    "itemIds",
                ],
            },
            "fallbackParamFlow": {
                "nativePath": [
                    "DialogTreeOpenUINode.DoAction@0x1872a5e1c",
                    "DialogManager.OpenUI@0x186e145d8",
                    "GameAction.DialogOpenUIPanel@0x1875e0224",
                ],
                "shippedLuaConsumer": {
                    "logicalPath": (
                        "Data/LuaScripts/Phase/Dialog/PhaseDialog.lua"
                    ),
                    "sha256": (
                        "59df40f905d038f8a0527d680eca612e7b2ed4e0e9b3f7cfc96bf97bbe882b13"
                    ),
                },
                "finding": (
                    "The native fallback forwards the original action and param "
                    "string. PhaseDialog JSON-decodes that string and adds only "
                    "fromDialog and actionData; it performs no quest lookup or "
                    "submission-identity substitution."
                ),
            },
            "authoredOpenUiActions": {
                "typedTerminalActions": 95,
                "submitItemPanelType": 9,
                "submitItemActions": 13,
                "parameterizedSubmitItemActions": 3,
                "placeholderSubmitItemActions": 3,
                "emptyParamSubmitItemActions": 10,
                "concreteQuestIdActions": 0,
            },
            "authoredMissionObjectives": {
                "conditionCount": 3,
                "questCount": 3,
                "missionCount": 3,
                "tableDefinedCount": 3,
                "dialogCoGateCount": 2,
                "dialogCoGateOpenUiOverlap": 0,
                "withSubGameConditionCount": 0,
                "finding": (
                    "Three exact MissionRuntime quest objectives resolve to "
                    "SubmitItem table requirements. Two share an authored AND "
                    "objective with a dialog finish, but those dialog ids do not "
                    "overlap the 13 SubmitItem OpenUI terminals."
                ),
            },
            "sendFinishDialog": {
                "symbol": "CinematicSystem.SendFinishDialog",
                "token": "0x06004027",
                "address": "0x1872f0d88",
            },
            "installedPatchMatches": 0,
            "finding": (
                "Shipped SubmitItemCtrl Lua constructs InventoryItemSubmitter and "
                "calls RegisterPendingSubmission through XLua. The zero native "
                "direct-call counts therefore describe only the AOT call surface, "
                "not an inactive producer. Thirteen typed SubmitItem OpenUI terminals "
                "exist, but three contain only stock placeholder params, ten contain "
                "no params, and none exports a concrete quest id. Three separate "
                "quest objectives do resolve exact submission requirements; two "
                "have bounded same-AND dialog co-gates, with zero overlap against "
                "the SubmitItem OpenUI dialog set. The fallback parameter flow "
                "does not supply a missing quest identity."
            ),
        },
        "finding": (
            "All 112 managed identity candidates reachable at the cycle-safe type-"
            "graph fixed point are reviewed. Productive contexts were already "
            "recovered; remaining joins are shared runtime aggregates, previously "
            "closed paths, static registries, or the active XLua pending-submission "
            "bridge with exact quest-to-submission context but no quest-to-OpenUI join."
        ),
        "boundary": (
            "The exact shipped SubmitItem XLua producer, fallback OpenUI parameter "
            "pass-through, and authored submission objectives are included. "
            "Dynamic mutation or reflection outside this path, native-only opaque "
            "objects, server-only state, unexported asset kinds, future IFix, and "
            "future builds remain outside the bound."
        ),
        "classification": "all_nested_managed_identity_carriers_reviewed",
        "storyBindingsAdded": 0,
        "missionOrderEdgesAdded": 0,
        "confidence": "metadata_registration_and_native_consumers_bounded",
    },
    "nativeCrossSystemConsumerCensus": {
        "source": (
            "reports/story/recovery/native_cross_system_consumer_census.json"
        ),
        "method": (
            "Complete current-build E8 rel32 census across GameAssembly .text and "
            "il2cpp sections, mapped through current IL2CPP method and generic-method "
            "pointers. Shared pointers with more than eight aliases or mixed API-family "
            "aliases are rejected. No mission, quest, Story, scene, or object id is seeded."
        ),
        "counts": {
            "mappedMethodPointers": 500976,
            "familyTargetPointers": 7214,
            "crossSystemCallers": 17,
            "missionStateDynamicSceneCallers": 4,
            "dynamicSceneLevelScriptCallers": 4,
            "dynamicSceneStoryCallers": 8,
            "missionStoryCallers": 1,
            "missionLevelScriptCallers": 0,
            "tripleOrGreaterFamilyCallers": 0,
            "unreviewedCallers": 0,
            "closureReachableMethods": 23,
            "closureDirectEdges": 30,
            "closureLevelScriptMethods": 0,
            "closureStoryMethods": 0,
            "unreviewedIndirectSites": 0,
        },
        "classifications": {
            "missionStateControlsDynamicComponentAvailability": 4,
            "sharedTriggerGeometryAdapters": 3,
            "globalLevelLoadSynchronization": 1,
            "storyDynamicSceneVisualContext": 8,
            "missionOrDialogAlternateActionConsumer": 1,
        },
        "deferredRefreshClosure": {
            "pendingField": {
                "name": "m_pendingRefreshCompSet",
                "token": "0x0400e5f9",
                "offset": "0x48",
            },
            "chain": [
                "MissionSystem mission/quest state",
                "DynamicScene cared component enqueue",
                "m_pendingRefreshCompSet@0x48",
                "DynamicSceneMissionControlSystem.BeforeTick",
                "DynamicSceneMissionControlSystem._UpdateConditionValue",
                "DynamicSceneEntitySystem.RefreshEntityStatus",
            ],
            "classification": (
                "mission_state_drives_deferred_dynamic_scene_availability_refresh"
            ),
        },
        "missionRuntimeSurface": {
            "counts": {
                "missionIdentityTypes": 174,
                "familyTargetPointers": 4322,
                "crossSystemCallers": 2,
                "missionRuntimeLevelScriptCallers": 1,
                "missionRuntimeStoryCallers": 1,
                "crossFamilyMethodSignatures": 0,
                "trackingMissionFieldWrites": 0,
                "trackingSceneFieldWrites": 3,
                "unreviewedCallers": 0,
            },
            "trackingFieldFlow": {
                "fieldLayout": {
                    "missionId": {
                        "name": "missionId",
                        "token": "0x04003f3b",
                        "offset": "0x20",
                    },
                    "sceneId": {
                        "name": "sceneId",
                        "token": "0x04003f3d",
                        "offset": "0x30",
                    },
                },
                "writes": {
                    "missionId": [],
                    "sceneId": [
                        {"va": "0x186fb6567"},
                        {"va": "0x186fb6675"},
                        {"va": "0x186fb66e4"},
                    ],
                },
            },
            "finding": (
                "The broadened 174-type mission/quest runtime surface adds no "
                "activation bridge. Its sole LevelScript caller constructs a "
                "tracking point and writes sceneId, but never writes missionId; "
                "the other caller is the audited MissionOption alternate action. "
                "No managed method signature co-carries both runtime families."
            ),
            "boundary": (
                "Tracking UI context creates no receiver activation, Story "
                "ownership, branch, or order edge."
            ),
            "classification": (
                "full_mission_runtime_surface_reviewed_no_activation_bridge"
            ),
        },
        "managedCallableSurface": {
            "counts": {
                "callableFields": 13,
                "missionRuntimeCallableFields": 9,
                "levelScriptCallableFields": 4,
                "crossIdentityCallableFields": 0,
                "callableEntryMethods": 5,
                "callableEntryTargetPointers": 5,
                "directBindingCalls": 5,
                "missionLevelScriptBindings": 0,
                "unreviewedBindingCallers": 0,
            },
            "finding": (
                "The complete managed callable surface contains 13 fields and five "
                "callable-parameter binding entry points. MissionSystem binds only "
                "MissionAcceptMode, while LevelScriptRuntime binds only its local task "
                "condition notifications; no binding joins the two families."
            ),
            "boundary": (
                "Typed managed fields and direct native calls to their binding entry "
                "points are closed for this build. Runtime field mutation, reflection, "
                "XLua, IFix, native-only registries, and server selection remain outside "
                "the bound."
            ),
            "classification": (
                "managed_callable_carriers_reviewed_no_activation_bridge"
            ),
        },
        "finding": (
            "Four native DynamicSceneMissionControlSystem paths read exact mission or "
            "quest state and update cared DynamicScene components. Their fixed-point "
            "direct-call closure reaches 23 gameplay methods across 30 edges, with no "
            "LevelScript or Story method. Metadata and native field access prove that "
            "the pending set is consumed by BeforeTick to re-evaluate conditions and "
            "RefreshEntityStatus. The remaining cross-system routes "
            "are shared trigger geometry, global level-load synchronization, Story visual "
            "override/actor context, or the separately audited MissionOption alternate "
            "mission/dialog actions."
        ),
        "boundary": (
            "The closure reviews its sole decoded indirect site as an IL2CPP class-"
            "initializer guard, but the partial decoder is not a general x64 proof. "
            "Reflection, XLua, server-only logic, opaque dynamic dispatch, and future "
            "builds remain outside the census. Mission-controlled "
            "DynamicScene rows are availability context, not LevelScript activation, Story "
            "ownership, playback causality, or mission order."
        ),
        "relatedOriginalFiles": [{
            "sourceFile": "D:/Program Files/Endfield Game/GameAssembly.dll",
            "sha256": (
                "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
            ),
            "role": "complete native direct-call consumer corpus",
        }, {
            "sourceFile": (
                "D:/Program Files/Endfield Game/Endfield_Data/il2cpp_data/Metadata/"
                "global-metadata.dat"
            ),
            "sha256": (
                "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
            ),
            "role": "managed method, type, and generic-instantiation mapping",
        }],
        "classification": "mission_state_drives_deferred_dynamic_scene_availability_refresh",
        "storyBindingsAdded": 0,
        "missionOrderEdgesAdded": 0,
        "confidence": "hash_locked_direct_and_deferred_native_closure",
    },
    "airWallMissionRadioContext": {
        "managedCarrier": {
            "manager": "Beyond.Gameplay.AirWallManager",
            "group": "Beyond.Gameplay.AirWallGroup",
            "checkData": "Beyond.Gameplay.AirWallCheckData",
            "predicate": "Beyond.Gameplay.MissionCheckData",
            "levelDataField": "Beyond.Gameplay.LevelData.airWalls",
        },
        "memoryPackSchema": {
            "levelDataMemberCount": 43,
            "airWallsMemberIndex": 0,
            "airWallGroupMemberCount": 8,
            "airWallGroupMemberOrder": [
                "bounds",
                "checkData",
                "defaultOn",
                "groupId",
                "polyLineWalls",
                "pushBackRadioId",
                "scriptId",
                "slotId",
            ],
            "missionCheckFields": [
                "detailState",
                "id",
                "isQuest",
                "isSame",
            ],
        },
        "corpus": {
            "levelDataFiles": 958,
            "filesWithAirWalls": 228,
            "airWallGroups": 822,
            "missionCheckedGroups": 211,
            "radioGroups": 78,
            "missionCheckedRadioGroups": 60,
            "acceptedStoryContexts": 58,
            "rejectedUnresolvedOrInconsistentContexts": 2,
            "missionAttachmentEdges": 61,
            "attachedMissions": 30,
            "storyRadioIds": 20,
            "parseFailures": 0,
        },
        "nativeChain": [
            {
                "symbol": "AirWallManager._InitMissionListener",
                "token": "0x06001c6f",
                "address": "0x1845d5df0",
                "fallbackPatchId": "0x260e",
                "effect": "binds global mission and quest state listeners",
            },
            {
                "symbol": (
                    "AirWallManager._OnMissionStateChanged / "
                    "_OnQuestStateChanged"
                ),
                "tokens": ["0x06001c71", "0x06001c72"],
                "addresses": ["0x186f49038", "0x186f49278"],
                "fallbackPatchIds": ["0x260f", "0x2610"],
                "effect": "routes exact cared identifiers to AirWallGroupAgent",
            },
            {
                "symbol": (
                    "AirWallGroupAgent.OnMissionStateChanged / "
                    "OnQuestStateChanged"
                ),
                "tokens": ["0x06001c5e", "0x06001c5f"],
                "address": "0x186f45be8 / 0x186f45c50",
                "effect": "re-evaluates the authored MissionCheckData predicates",
            },
            {
                "symbol": (
                    "AirWallManager.TriggerMainCharGoBack callback -> "
                    "GameAction.PlayRadio"
                ),
                "token": "0x06001cb9",
                "address": "0x186f4ecc0 + 0x24a",
                "effect": "plays pushBackRadioId after local AirWall contact",
            },
        ],
        "installedPatch": {
            "sha256": "737134081e06371f13c073988547e887037fccf2f57e1052be35dd255d27bc21",
            "signatureTargetCount": 30,
            "matchedAirWallMethods": 0,
        },
        "finding": (
            "This is an exact state-gated playback context: synchronized mission/quest "
            "state controls an authored AirWall, and later player contact can play its "
            "pushback radio. It is not a mission-transition playback trigger, quest "
            "activation/completion edge, Story owner, or ordering edge."
        ),
        "confidence": "native_exact_serialized_co_carrier",
    },
    "guideCompletion": {
        "conditionType": 11,
        "conditionTypeName": "GuideFinish",
        "completeTypeNames": {
            "0": "All",
            "1": "Manual",
            "2": "AutoClose",
        },
        "serverBackedRequest": "CS_COMPLETE_GUIDE_GROUP { GuideGroupId, IsClose }",
        "serverBackedResponse": "SC_COMPLETE_GUIDE_GROUP { GuideGroupId, IsClosed }",
        "clientOnlyFinding": (
            "ManuallyStartGuideGroup registers a client-only group. Its completion "
            "calls the local completion path and skips CS_COMPLETE_GUIDE_GROUP."
        ),
        "conditionFinding": (
            "CheckGuideGroupComplete queries completed server groups and current-scope "
            "completed client groups, then subscribes to the local completion event. "
            "CompleteType.All accepts Manual or AutoClose completion."
        ),
        "confidence": "native_proven",
    },
    "subGameMissionRegistry": {
        "type": "Beyond.Gameplay.Core.SubGameInstanceData",
        "identityFields": ["id", "bindScriptId", "dungeonMissionId"],
        "finding": (
            "A typed original-data row can carry one subgame id, one bound LevelScript id, "
            "and one dungeon mission id together. This is exact mission-shell runtime "
            "context, but it does not identify a quest or prove that any Story action in "
            "the script is played by that mission."
        ),
        "runtimeBoundary": (
            "SC_GAME_MECHANICS_SYNC_ENTER_GAME_INST.gameId reaches "
            "SubGameManager.SrvCreateSubGame, and GameModeFactory.CreateGame resolves the "
            "same SubGameInstanceDataTable row before constructing its concrete runtime. "
            "gameInstId and gameUniqueId identify only the live runtime instance."
        ),
        "bindScriptFinding": (
            "The installed MemoryPack setter stores bindScriptId at row offset +0x50. "
            "InteractiveLogicChallengeStartPoint._OnInteract resolves the typed row, "
            "reads that exact field, resolves the LevelScript, and calls "
            "LevelScriptRuntime.ManualStart. WorldChallengeGame.SendQuit reads the same "
            "field before ManualEnd and the stop request. These prove the generic bound-"
            "script lifecycle, not which interaction occurred."
        ),
        "ownershipBoundary": (
            "No audited GameMechanics lifecycle packet carries missionId, questId, "
            "sceneNumId, or bindScriptId. The row has no questId or sceneNumId, so the "
            "operational script identity cannot by itself attach a Story file."
        ),
        "missionlessPlaybackAudit": {
            "referenceScope": (
                "Current exported Table and GameplayConfig JSON exact-identity census, "
                "plus the complete decoded receiver task/condition audit."
            ),
            "subGameRows": 10,
            "uniqueStoryFiles": 9,
            "storyPlacements": 14,
            "primaryTaskIds": 10,
            "secondaryTaskIds": 3,
            "exactMissionAssociations": 1,
            "questUnlockPrerequisites": 1,
            "previousSubGamePrerequisites": 5,
            "missionRuntimeTaskConsumers": 0,
            "finding": (
                "The ten current missionless SubGame playback nodes have no additional "
                "exported ownership carrier. Only activity_qingxi_qiangti_6 has an exact "
                "mission association, and that typed stage relation is explicitly "
                "non-owning. Boss-rush references provide one quest unlock, five prior-"
                "challenge gates, and scene/reward grouping. Task ids remain local "
                "LevelScript/SubGame display identities with zero MissionRuntime consumer."
            ),
            "storyBindingsAdded": 0,
            "confidence": "complete_current_export_reference_census",
        },
        "confidence": "typed_original_data_and_native_runtime",
    },
    "activityQuestLevelHosts": {
        "types": [
            "Beyond.Cfg.ActivityDungeonFightingStageData",
            "Beyond.Cfg.ActivitySnapShotStageData",
        ],
        "identityFields": ["questId", "levelId"],
        "finding": (
            "Each typed activity-stage row co-identifies one quest and one level. "
            "Installed get_questId/get_levelId accessors independently validate the "
            "field meanings. This is exact quest-level context, not Story ownership."
        ),
        "confidence": "typed_original_data_and_native_accessors",
    },
    "npcProxyDialogSelection": {
        "sourceTable": "NpcProxyExDataTable.json",
        "serverStateMessages": [
            "SC_NPC_ENTER_MAP_RESYNC",
            "SC_NPC_ACTIVE_CHANGE_NTF",
        ],
        "selectorFields": ["proxyNumId", "metaKvs", "activeCondIndex"],
        "clientExecution": (
            "The server-provided one-based activeCondIndex selects exDatas[index - 1]. "
            "NpcInteractComponent then reads that row's dialogId."
        ),
        "bindingBoundary": (
            "The selector reads dialogId but not the adjacent missionId and never calls "
            "MissionSystem. missionId is consumed separately only as a paused-mission "
            "proxy-deactivation guard. A proxy-id or active-row match is therefore not "
            "mission/Story ownership evidence."
        ),
        "clientRequest": False,
        "expectedClientReply": False,
        "confidence": "typed_original_data_and_native_runtime",
    },
    "systemStoryCarriers": {
        "domainDepotDeliveryDialog": {
            "sourceTables": [
                "DomainDepotConst.json",
                "DomainDepotDeliverTargetDialogTable.json",
                "DomainDepotDeliverTargetTable.json",
            ],
            "missionId": "f1m25",
            "questId": None,
            "clientExecution": (
                "The receive-package response updates the delivery state, resolves the exact "
                "typed target/dialog rows, installs the NPC override dialog, and registers its "
                "finish callback. Finishing that target dialog sends the package request."
            ),
            "exchangeIds": [
                "domain-depot-recv-package-request",
                "domain-depot-recv-package-response",
                "domain-depot-send-package-request",
                "domain-depot-send-package-response",
            ],
            "bindingBoundary": (
                "The typed tables and native consumer prove a mission-level f1m25 dialog "
                "carrier. They do not serialize an individual quest placement, and neither "
                "packet carries a Story id, mission id, or quest id."
            ),
            "confidence": "typed_original_data_and_native_runtime",
        },
        "skipChapterDialog": {
            "sourceTables": ["SkipChapterTable.json"],
            "missionId": "e5m1",
            "questId": None,
            "clientExecution": (
                "SendDoSkipChapter constructs the request from the exact same-row "
                "skipChapterConfigId used by the e5m1 dialog carrier and sends it through "
                "BasePlayerManager.SendUIMsg."
            ),
            "exchangeIds": [
                "skip-chapter-request",
                "skip-chapter-response",
            ],
            "bindingBoundary": (
                "The table row directly co-identifies bindDlgId and missionId, but provides "
                "no quest id; the request/reply carries only skipChapterConfigId."
            ),
            "confidence": "typed_original_data_and_native_runtime",
        },
        "factoryBuildingPanelLockRadio": {
            "sourceTables": ["FactoryBuildingPanelLock.json"],
            "missionId": None,
            "questIds": ["e1m1_q#01", "e1m4_q#5"],
            "clientExecution": (
                "CheckBuildingLock reads both exact configured quest states from the local "
                "MissionSystem cache. The public lock checks construct RadioRuntimeData and "
                "dispatch the configured radio when notification is requested."
            ),
            "exchangeIds": [],
            "serverExchange": False,
            "bindingBoundary": (
                "This is a non-owning dependency on two exact quest-state boundaries. The "
                "carrier has no direct request or expected response and does not prove an "
                "e1m2 mission owner from the radio filename."
            ),
            "confidence": "typed_original_data_and_native_runtime",
        },
        "dialogTreeQuestStateBranch": {
            "sourceTypes": ["AnimeStudio TextAsset/DialogTree"],
            "conditionType": "Beyond.Gameplay.CheckQuestState",
            "nodeTypes": [
                "Beyond.Gameplay.DialogTreeIfNode",
                "Beyond.Gameplay.DialogTreeBranchNode",
            ],
            "clientExecution": (
                "CheckQuestState reads the exact serialized quest id, comparer, and "
                "target state from MissionSystem's synchronized local cache. The typed "
                "If/Branch node then selects an authored outgoing DialogTree connection."
            ),
            "exchangeIds": [],
            "serverExchange": False,
            "bindingBoundary": (
                "This is a non-owning dependency explaining local dialog branch selection. "
                "It does not make the quest the Story owner, and the condition evaluation "
                "does not send a request or expect a response."
            ),
            "confidence": "typed_original_data_and_native_runtime",
        },
    },
    "localOnly": [
        {
            "id": "battle-signal",
            "event": "LevelEvent_OnBattleSignal (0x28)",
            "handler": (
                "SendBattleSignalToLevel.ExecuteInternal -> "
                "LevelEventManager.RaiseLevelEvent -> OnBattleSignal.Process"
            ),
            "address": "0x186d27734 -> 0x18318f2a0 -> 0x186aa3260",
            "fields": ["signalId", "doubleValue"],
            "effect": (
                "Raise a local client LevelEvent from an Ability action. The receiver "
                "filters only signalId/floatValue and has no sender, entity, spawner, "
                "mission, or quest selector."
            ),
            "serverExchange": False,
            "confidence": "native_proven",
        },
        {
            "id": "spawner-group-begin",
            "event": "LevelEvent_OnSpawnerGroupBegin (0x3b)",
            "handler": (
                "TimelineGroupBlock.StartGroup -> LevelEventManager.RaiseLevelEvent -> "
                "OnSpawnerGroupBegin.Process"
            ),
            "address": "0x186fd61e4 -> 0x18318f2a0",
            "fields": ["spawnerId", "groupKey"],
            "effect": (
                "Raise the group-begin event locally after an acknowledged spawner wave "
                "starts. There is no group-begin RPC; the upstream begin-wave request/"
                "response carries sceneNumId, spawnerId, and waveId but no groupKey or "
                "mission/quest identity."
            ),
            "serverExchange": False,
            "upstreamExchangeFamily": "spawner_begin_wave",
            "confidence": "native_proven",
        },
        {
            "id": "entity-hp-changed",
            "event": "LevelEvent_OnEntityHpChanged (0x09)",
            "handler": (
                "AbilitySystem.SetHpInternal -> LevelEventManager.RaiseLevelEvent -> "
                "OnEntityHpChanged.Process"
            ),
            "address": "0x183a92014 -> 0x18318f2a0",
            "fields": ["entity", "oldHpRatio", "newHpRatio"],
            "effect": (
                "Raise a local event for the AbilitySystem owner whose HP changed. A Down "
                "listener fires when the old normalized HP is above its serialized threshold "
                "and the new value is at or below it. No mission/quest or network payload is "
                "part of this dispatch."
            ),
            "serverExchange": False,
            "confidence": "native_proven",
        },
        {
            "id": "npc-patrol-checkpoint",
            "event": "LevelEvent_OnNpcPatrolCheckpointReach (0x2a)",
            "handler": (
                "NpcAIPatrolController._RaiseCheckpointReachEvent -> "
                "LevelEventManager.RaiseLevelEvent -> OnNpcPatrolCheckpointReach.Process"
            ),
            "address": "0x186b4d610/0x186b7576c -> 0x18318f2a0 -> 0x186ab44d0",
            "fields": ["npcEntity", "patrolId", "checkpointIndex", "npcPosition"],
            "effect": (
                "Raise a local patrol event with the controller entity as both sender and "
                "receiver. The exact selector has no mission/quest id and sends no request."
            ),
            "serverExchange": False,
            "confidence": "native_proven",
        },
        {
            "id": "entity-cast-skill",
            "event": "LevelEvent_OnEntityCastSkill (0x04)",
            "handler": (
                "AbilitySystem.BeforeCastStart -> LevelEventManager.RaiseLevelEvent -> "
                "OnEntityCastSkill.Process"
            ),
            "address": "0x1842afe20 -> 0x1842b0d53",
            "fields": ["entity", "entityTemplateId", "firstTargetId", "skillId"],
            "effect": (
                "Raise a local cast event. Current residual listeners have filter mode "
                "disabled, so their entity/template/target/skill fields are outputs, not "
                "mission selectors. No request or expected server response exists on this path."
            ),
            "serverExchange": False,
            "confidence": "native_proven",
        },
        {
            "id": "entity-die",
            "event": "LevelEvent_OnAnyEntityDie / OnSpecificEntityDie (0x03)",
            "handler": (
                "WorldInfo.OnEntityDie -> LevelEventManager.RaiseLevelEvent -> "
                "typed death receiver Process"
            ),
            "address": "0x183ed3210 -> 0x183ed40e8",
            "fields": ["entity", "isMonster", "filterByList", "entityList/filterEntity"],
            "effect": (
                "Dispatch local entity-death state to exact serialized filters. Entity "
                "identity does not add a mission/quest id or a network exchange."
            ),
            "serverExchange": False,
            "confidence": "native_proven",
        },
        {
            "id": "squad-fight-state",
            "event": "LevelEvent_OnSquadInFightChanged (0x15)",
            "handler": (
                "BattleManager._OnSquadInFight -> LevelEventManager.RaiseLevelEvent -> "
                "OnSquadInFightChanged.Process"
            ),
            "address": "0x183823204",
            "fields": ["inFight (output only)"],
            "effect": (
                "Raise the local squad combat-state event. The installed listener has no "
                "payload filter, request, expected response, mission id, or quest id."
            ),
            "serverExchange": False,
            "confidence": "native_proven",
        },
        {
            "id": "script-property-blackboard-change",
            "event": "ScriptEvent_OnPropertyChanged / OnBBVariableChanged",
            "handler": (
                "ParamVariable local property/blackboard subscription -> exact key/path "
                "comparison -> typed receiver Process"
            ),
            "fields": ["propertyKey/blackboardKey", "oldValue", "value"],
            "effect": (
                "Observe a change inside the owning LevelScript. Value comparisons belong "
                "to later action gates; the event itself sends nothing to the server."
            ),
            "serverExchange": False,
            "confidence": "native_proven",
        },
        {
            "id": "script-complete",
            "event": "ScriptEvent_OnScriptComplete (0x08)",
            "handler": (
                "LevelScriptRuntime.UpdateRuntimeState -> _RaiseOnScriptEvent(8) -> "
                "OnScriptComplete.Process"
            ),
            "address": "0x1834bfa20",
            "fields": ["owning LevelScript receiver identity"],
            "effect": (
                "Raise the SELF-scoped local completion event for the owning script. "
                "This lifecycle callback has no direct request or expected server response."
            ),
            "serverExchange": False,
            "confidence": "native_proven",
        },
        {
            "id": "scripted-character-patrol-event",
            "event": "LevelEvent_OnScriptedCharPatrolEvent",
            "handler": (
                "CharPatrolPointAction.SendEvent -> OnScriptedCharPatrolEvent.Process"
            ),
            "fields": ["event key", "entity output", "patrolId output"],
            "effect": (
                "Emit the authored patrol-point event locally and filter its exact key. "
                "The receiver does not send a request or await a server reply."
            ),
            "serverExchange": False,
            "confidence": "native_proven",
        },
        {
            "id": "factory-building-panel-lock-radio",
            "event": "FactoryBuildingPanelLock quest-state radio gate",
            "handler": (
                "FactoryUtil.CheckBuildingLock -> CheckIsBuildingInteractLocked / "
                "CheckIsBuildingMoveAndDelLocked -> GameAction.RadioRuntimeData"
            ),
            "address": "0x18747ec68 -> 0x18747f034 / 0x18747f3a8",
            "fields": ["startQuestId", "endQuestId", "lockType", "args", "radioId"],
            "effect": (
                "Read the synchronized local states for the two exact configured quest ids, "
                "apply the lock-type and optional interaction-index filter, and dispatch the "
                "configured radio locally when notification is requested. This carrier sends "
                "no request and expects no server response."
            ),
            "serverExchange": False,
            "storyOwnership": False,
            "confidence": "typed_original_data_and_native_runtime",
        },
        {
            "id": "dialog-tree-quest-state-branch",
            "event": "DialogTree CheckQuestState branch evaluation",
            "handler": (
                "CheckQuestState.OnActivate / _OnQuestStateChange (condition result); "
                "DialogTreeIfNode._TrySelectIfBranch or "
                "DialogTreeBranchNode._TrySelectBranch (route selection)"
            ),
            "address": (
                "0x18400f840 / 0x1873418f0; "
                "0x1872a5280 or 0x1872a1d0c"
            ),
            "fields": ["_questId", "_comparer", "_targetQuestState", "connections"],
            "effect": (
                "Read the synchronized local state for the exact serialized quest id, "
                "compare it with the target state, and select an authored DialogTree "
                "route. This evaluation sends no request and expects no server response; "
                "SC_SYNC_ALL_MISSION and SC_QUEST_STATE_UPDATE independently maintain the "
                "local cache."
            ),
            "serverExchange": False,
            "storyOwnership": False,
            "upstreamStateSources": ["SC_SYNC_ALL_MISSION", "SC_QUEST_STATE_UPDATE"],
            "confidence": "typed_original_data_and_native_runtime",
        },
    ],
    "inbound": [
        {
            "id": "npc-proxy-enter-map-resync",
            "direction": "server_to_client",
            "message": "SC_NPC_ENTER_MAP_RESYNC",
            "handler": "NpcProxyDataSys.SyncAllActiveProxy",
            "address": "0x183480890",
            "fields": [
                "SCD_NPC_PROXY_INFO.proxyNumId",
                "SCD_NPC_PROXY_INFO.metaKvs",
                "SCD_NPC_PROXY_INFO.activeCondIndex",
            ],
            "effect": (
                "Resynchronize active NPC proxies. activeCondIndex is copied into local "
                "ProxyInfo, converted from one-based to zero-based, and selects an exDatas "
                "row whose dialogId can become the NPC interaction dialog. The message "
                "carries no missionId, questId, or dialogId and has no client request in "
                "this decoded selector chain."
            ),
            "confidence": "native_proven",
        },
        {
            "id": "npc-proxy-active-change",
            "direction": "server_to_client",
            "message": "SC_NPC_ACTIVE_CHANGE_NTF",
            "handler": "NpcProxyDataSys.OnProxyChange",
            "address": "0x18706550c",
            "fields": [
                "SCD_NPC_PROXY_INFO.proxyNumId",
                "SCD_NPC_PROXY_INFO.metaKvs",
                "SCD_NPC_PROXY_INFO.activeCondIndex",
            ],
            "effect": (
                "Apply a server-pushed NPC active-row change and refresh env talk, options, "
                "and interaction dialog consumers. The selected-row dialogId and separate "
                "paused-mission deactivation guard must not be conflated as ownership."
            ),
            "confidence": "native_proven",
        },
        {
            "id": "full-mission-sync",
            "direction": "server_to_client",
            "message": "SC_SYNC_ALL_MISSION",
            "handler": "MissionSystem.Handle_SyncAllMission",
            "address": "0x1833784e0",
            "fields": [
                "trackMissionId",
                "missions",
                "curQuests",
                "dailyMissionId",
                "newMissionTags",
                "curMainMissionId",
                "earlyAcceptMissionChapters",
            ],
            "effect": "Rebuild mission and current-quest state during initial/full synchronization.",
            "confidence": "native_proven",
        },
        {
            "id": "mission-client-event",
            "direction": "server_to_client",
            "message": (
                "SC_SCENE_TRIGGER_CLIENT_MISSION_EVENT (125) "
                "{ missionId, eventName }"
            ),
            "messageId": 125,
            "handler": (
                "MissionSystem.Handle_ClientMissionEvent -> "
                "KeyGenerator<T1,T2>.GetKey -> EventManager.SendGlobal"
            ),
            "address": "0x1873bdf58 -> 0x184a428a0 -> 0x187bdfd38",
            "fields": ["missionId", "eventName"],
            "effect": (
                "Interns the exact missionId/eventName pair as a two-part CombineKey and "
                "publishes it through the global EventManager bus. This does not target "
                "the serialized MissionEvent_OnCustomEventForMission action family. The "
                "exact publisher specialization is SendGlobal<Beyond.Gameplay.EventData>, "
                "while the complete current-build AOT table contains no required "
                "BindGlobal<Beyond.EventData<Beyond.Gameplay.EventData>> specialization. "
                "This closes compiled managed typed subscribers, including indirect final "
                "call forms. Native memory manipulation, runtime reflection, future IFix, "
                "and future builds remain outside the bound. No Story-file, quest-order, "
                "branch, or merge edge is created."
            ),
            "exchangeFamily": "mission_event",
            "exchangeRole": "server_push",
            "runtimeScope": "MissionSystem / keyed global EventManager bus",
            "asynchronous": True,
            "questScoped": False,
            "typedConsumerStatus": "no_current_aot_typed_subscriber",
            "confidence": "native_proven_aot_subscriber_absence",
        },
        {
            "id": "full-dialog-sync",
            "direction": "server_to_client",
            "message": "SC_SYNC_ALL_DIALOG",
            "handler": "CinematicSystem._Handle_SyncAllDialog",
            "address": "0x1837a2530",
            "fields": ["dialogs[].dialogId", "optionIds[]", "finishNums[]"],
            "effect": "Rebuild the dialog history that exact-finish mission conditions query.",
            "confidence": "native_proven",
        },
        {
            "id": "mission-state",
            "direction": "server_to_client",
            "message": "SC_MISSION_STATE_UPDATE",
            "handler": "MissionSystem.Handle_MissionStateUpdate",
            "address": "0x1873be300",
            "fields": [
                "missionId",
                "missionState",
                "succeedId",
                "properties",
                "externalSystemType",
                "externalSystemId",
                "acceptTime",
                "roleBaseInfo",
            ],
            "effect": (
                "Dispatch to AvailableMission, StartMission, or CompleteMission. On the "
                "completion path succeedId is the completion outcome/result selector; it "
                "is not a successor mission id and must not create an order edge. "
                "roleBaseInfo leader position/rotation/sceneName is passed only to "
                "CharacterPositionCorrection for operational map/position reconciliation; "
                "it is not an authored mission scene host."
            ),
            "confidence": "native_proven",
        },
        {
            "id": "quest-start",
            "direction": "server_to_client",
            "message": "SC_QUEST_STATE_UPDATE { questId, questState = 2, bRollback, roleBaseInfo }",
            "handler": "MissionSystem.Handle_QuestStateUpdate -> MissionRuntime.StartQuest",
            "address": "0x1873bf0a0 -> 0x183a885d0",
            "effect": (
                "Create/bind the active client quest and its objective callbacks. "
                "roleBaseInfo leader position/rotation/sceneName is consumed only by "
                "CharacterPositionCorrection and adds no quest-to-scene or Story edge."
            ),
            "confidence": "native_proven",
        },
        {
            "id": "quest-succeed",
            "direction": "server_to_client",
            "message": "SC_QUEST_STATE_UPDATE { questId, questState = 3, bRollback, roleBaseInfo }",
            "handler": "MissionSystem.Handle_QuestStateUpdate -> MissionRuntime.SucceedQuest",
            "address": "0x1873bf0a0 -> 0x1873c32ac",
            "effect": (
                "Mark the quest completed on the client. Any roleBaseInfo sceneName is "
                "position-reconciliation context, not an authored quest host."
            ),
            "confidence": "native_proven",
        },
        {
            "id": "quest-objectives",
            "direction": "server_to_client",
            "message": "SC_QUEST_OBJECTIVES_UPDATE",
            "messageId": 116,
            "handler": "MissionSystem.Handle_QuestObjectiveUpdate",
            "address": "0x183a882e0",
            "fields": [
                "questId",
                "questObjectives[].conditionId",
                "questObjectives[].extraDetails",
                "questObjectives[].values",
                "questObjectives[].isComplete",
                "questObjectives[].descriptionIndex",
            ],
            "effect": (
                "Look up the exact questId, copy objective state by the composite "
                "(questId, conditionId) identity, and refresh HUD progress. Completion "
                "still arrives as a separate quest-state update."
            ),
            "confidence": "native_proven",
        },
        {
            "id": "quest-fail",
            "direction": "server_to_client",
            "message": "SC_QUEST_FAILED",
            "handler": "Handle_QuestFailed -> MissionRuntime.FailQuest",
            "address": "0x1873bef80 -> 0x1873bac84",
            "effect": "Mark the quest failed on the client.",
            "confidence": "native_proven",
        },
        {
            "id": "dialog-finish-echo",
            "direction": "server_to_client",
            "message": "SC_FINISH_DIALOG { dialogId, optionIds[], finishNums[] }",
            "handler": "CinematicSystem._Handle_FinishDialog",
            "address": "0x1872f1758",
            "effect": "CheckTalkOptionFinish can test any finish or an exact finish id.",
            "confidence": "native_proven",
        },
        {
            "id": "guide-group-complete-response",
            "direction": "server_to_client",
            "message": "SC_COMPLETE_GUIDE_GROUP { GuideGroupId, IsClosed }",
            "handler": "GuideSystem._HandleCompleteGuideGroup -> _OnCompleteGuideGroup",
            "fields": ["GuideGroupId", "IsClosed"],
            "effect": (
                "Record server-backed guide completion and raise the local guide-group "
                "completion event observed by CheckGuideGroupComplete. The packet carries "
                "no mission, quest, or condition id."
            ),
            "exchangeFamily": "guide_completion",
            "exchangeRole": "response",
            "runtimeScope": "GuideSystem",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "level-script-client-event",
            "direction": "server_to_client",
            "message": (
                "SC_SCENE_TRIGGER_CLIENT_LEVEL_SCRIPT_EVENT { sceneNumId:int32, "
                "scriptId:uint64, eventName:string, ctxToken:bytes }"
            ),
            "handler": (
                "GameplayNetwork._Handle_SceneTriggerClientLevelScriptEvent -> "
                "LevelEventManager.RaiseScriptEvent"
            ),
            "address": "0x187386320 -> 0x186f922a4",
            "fields": ["sceneNumId", "scriptId", "eventName", "ctxToken"],
            "effect": (
                "Raise the named client event on the exact LevelScript receiver selected "
                "by scriptId. CallServer can read ctxToken back as netToken and return it "
                "on a client LevelScript event, making it round-trip correlation context. "
                "The push carries no mission, quest, condition, or Story id, so neither "
                "event-name equality nor token presence can attach it to a pipeline."
            ),
            "exchangeFamily": "level_script_event",
            "exchangeRole": "server_push",
            "runtimeScope": "LevelScriptRuntime",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "level-script-event-ack",
            "direction": "server_to_client",
            "message": "SC_SCENE_LEVEL_SCRIPT_EVENT_TRIGGER { }",
            "handler": "empty protocol acknowledgement",
            "effect": "Acknowledge the LevelScript event request; quest progression still arrives through objective or state updates.",
            "fields": [],
            "exchangeFamily": "level_script_event",
            "exchangeRole": "response",
            "runtimeScope": "LevelScriptRuntime",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "level-script-stage-change",
            "direction": "server_to_client",
            "message": (
                "SC_SCENE_LEVEL_SCRIPT_STAGE_CHANGE { sceneNumId:int32, "
                "scriptId:uint64, stage:int32 }"
            ),
            "handler": (
                "GameplayNetwork._Handle_SyncLevelScriptStage -> "
                "LevelScriptManager.ServerSyncLevelScriptStage -> "
                "LevelScriptRuntime.UpdateStage"
            ),
            "address": "0x1873867cc -> 0x186f95310 -> 0x186fad930",
            "fields": ["sceneNumId", "scriptId", "stage"],
            "effect": (
                "Apply the server-authored stage to the exact ready LevelScript, then "
                "raise the local SELF-scoped OnScriptStageChanged event. Current metadata "
                "has no client stage-change request or expected return on this path, and "
                "the packet carries no mission or quest id."
            ),
            "exchangeFamily": "level_script_stage",
            "exchangeRole": "server_push",
            "runtimeScope": "LevelScriptRuntime",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "global-var-update",
            "direction": "server_to_client",
            "message": "SC_UPDATE_GAME_VAR { key:int32, value:int64, type:int32 }",
            "handler": "GlobalVarSystem.Handle_UpdateGameVar",
            "fields": ["key", "value", "type"],
            "effect": (
                "Raise ON_SERVER_GLOBAL_VAR_CHANGED (0x5e). If this key has a pending "
                "client write, also raise ON_CLIENT_GLOBAL_VAR_CHANGED (0x5d) and "
                "decrement its pending-write count. The type discriminator remains raw."
            ),
            "exchangeFamily": "global_var",
            "exchangeRole": "server_update_or_confirmation",
            "runtimeScope": "GlobalVarSystem",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "spawner-begin-wave-response",
            "direction": "server_to_client",
            "message": (
                "SC_SCENE_MONSTER_SPAWNER_BEGIN_WAVE { sceneNumId:int32, "
                "spawnerId:uint64, waveId:int32 }"
            ),
            "handler": (
                "_Handle_EnemySpawnerBeginWave -> SpawnerManager.OnEnemySpawnerBeginWave "
                "-> SpawnerRuntime.OnWaveBeginResponse -> TimelineWaveBlock.StartWave"
            ),
            "fields": ["sceneNumId", "spawnerId", "waveId"],
            "effect": (
                "Apply the acknowledged wave start and raise local ON_SPAWNER_WAVE_BEGIN "
                "(0x38). ON_SPAWNER_GROUP_BEGIN (0x3b) is derived locally after wave "
                "start; it is not a separate server exchange."
            ),
            "exchangeFamily": "spawner_wave",
            "exchangeRole": "response",
            "runtimeScope": "SpawnerRuntime",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "spawner-complete",
            "direction": "server_to_client",
            "message": "SC_SCENE_MONSTER_SPAWNER_COMPLETE { sceneNumId:int32, spawnerId:uint64 }",
            "handler": (
                "GameplayNetwork._Handle_EnemySpawnerComplete -> "
                "SpawnerManager.OnEnemySpawnerComplete -> SpawnerRuntime.OnSpawnerComplete"
            ),
            "fields": ["sceneNumId", "spawnerId"],
            "effect": "Apply the server completion push and raise local ON_SPAWNER_COMPLETE (0x37).",
            "exchangeFamily": "spawner_completion",
            "exchangeRole": "server_push",
            "runtimeScope": "SpawnerRuntime",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "touch-trigger-volume-response",
            "direction": "server_to_client",
            "message": (
                "SC_SCENE_TOUCH_TRIGGER_VOLUME_RSP { sceneNumId:int32, scriptId:uint64, "
                "scriptLocalId:uint32, isLeaveAction:bool }"
            ),
            "handler": "OnEnterWaitSrv / OnLeave wait-server path -> NetBus.ResultHandler",
            "fields": ["sceneNumId", "scriptId", "scriptLocalId", "isLeaveAction"],
            "effect": (
                "Return the server result for the exact trigger-volume touch request. "
                "The packet identifies a LevelScript trigger slot, not a mission or quest."
            ),
            "exchangeFamily": "trigger_volume_touch",
            "exchangeRole": "response",
            "runtimeScope": "LevelScriptRuntime",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "trigger-volume-state-sync",
            "direction": "server_to_client",
            "message": (
                "SC_SCENE_MODIFY_TRIGGER_VOLUME_SYNC { sceneNumId:int32, scriptId:uint64, "
                "triggerVolumeInfos[]:{ scriptLocalId:uint32, isHidden:bool, triggerCount:int32 } }"
            ),
            "handler": (
                "_Handle_SyncLevelScriptTriggerVolume -> ServerSyncTriggerVolumes -> "
                "MarkEnabled / MarkDisabled"
            ),
            "fields": [
                "sceneNumId",
                "scriptId",
                "triggerVolumeInfos[].scriptLocalId",
                "triggerVolumeInfos[].isHidden",
                "triggerVolumeInfos[].triggerCount",
            ],
            "effect": (
                "Push server-owned enabled/hidden and trigger-count state into registered "
                "LevelScript trigger slots. This push is not a paired quest update."
            ),
            "exchangeFamily": "trigger_volume_state",
            "exchangeRole": "server_push",
            "runtimeScope": "LevelScriptRuntime",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "scene-teleport",
            "direction": "server_to_client",
            "message": "SC_SCENE_TELEPORT",
            "handler": "TeleportProcessor.OnServerTeleport",
            "address": "0x18315a3f0",
            "fields": [
                "objIdList[]",
                "sceneNumId",
                "position",
                "rotation",
                "serverTime",
                "teleportReason",
                "tpUuid",
                "passThroughData",
            ],
            "effect": (
                "Apply a server teleport command or accepted teleport state. The client "
                "later acknowledges completion with the same tpUuid; no mission, quest, "
                "LevelScript, or Story id is present."
            ),
            "exchangeFamily": "scene_teleport",
            "exchangeRole": "server_push",
            "runtimeScope": "TeleportProcessor",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "subgame-enter",
            "direction": "server_to_client",
            "message": (
                "SC_GAME_MECHANICS_SYNC_ENTER_GAME_INST { gameId, isHunterMode, "
                "gameInstId, gameUniqueId, isReenter }"
            ),
            "messageId": 1257,
            "handler": "GameMechanicsSystem._Handle_EnterSubGameInst",
            "address": "0x18736b59c",
            "fields": ["gameId", "isHunterMode", "gameInstId", "gameUniqueId", "isReenter"],
            "effect": (
                "Resolve gameId through SubGameInstanceDataTable and construct the live "
                "runtime. Runtime instance ids do not become mission or Story ids."
            ),
            "exchangeFamily": "subgame_lifecycle",
            "exchangeRole": "server_push",
            "runtimeScope": "SubGameRuntime",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "subgame-challenge-start",
            "direction": "server_to_client",
            "message": (
                "SC_GAME_MECHANICS_SYNC_CHALLENGE_START { gameId, challengeStartTs, "
                "challengeExpireTs, prepareChallengeSeconds }"
            ),
            "messageId": 1254,
            "handler": "GameMechanicsSystem._Handle_ChallengeStart",
            "address": "0x18736b190",
            "fields": ["gameId", "challengeStartTs", "challengeExpireTs", "prepareChallengeSeconds"],
            "effect": (
                "Resolve the runtime by gameId, then invoke its prepare or start path. "
                "SubGameStartParam carries timestamps only."
            ),
            "exchangeFamily": "subgame_lifecycle",
            "exchangeRole": "server_push",
            "runtimeScope": "SubGameRuntime",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "subgame-challenge-complete",
            "direction": "server_to_client",
            "message": (
                "SC_GAME_MECHANICS_SYNC_CHALLENGE_COMPLETE { gameId, isPass, "
                "forceLeaveTs, passTime }"
            ),
            "messageId": 1255,
            "handler": "GameMechanicsSystem._Handle_ChallengeComplete",
            "address": "0x18736aef0",
            "fields": ["gameId", "isPass", "forceLeaveTs", "passTime"],
            "effect": (
                "Resolve the runtime by gameId and invoke its fail or complete path. "
                "SubGameCompleteParam carries passTime only."
            ),
            "exchangeFamily": "subgame_lifecycle",
            "exchangeRole": "server_push",
            "runtimeScope": "SubGameRuntime",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "subgame-completion-reward",
            "direction": "server_to_client",
            "message": (
                "SC_GAME_MECHANICS_SYNC_COMPLETION_REWARD { gameId, isPass, "
                "forceLeaveTs, rewardMultiplier, withoutStaminaReward, useStaminaReduce }"
            ),
            "messageId": 1256,
            "handler": "GameMechanicsSystem._Handle_CompletionReward",
            "address": "0x18736b290",
            "fields": [
                "gameId",
                "isPass",
                "forceLeaveTs",
                "rewardMultiplier",
                "withoutStaminaReward",
                "useStaminaReduce",
            ],
            "effect": "Apply the server-authored completion reward and leave timing for the runtime.",
            "exchangeFamily": "subgame_lifecycle",
            "exchangeRole": "server_push",
            "runtimeScope": "SubGameRuntime",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "subgame-leave",
            "direction": "server_to_client",
            "message": (
                "SC_GAME_MECHANICS_SYNC_LEAVE_GAME_INST { gameId, gameInstId, gameUniqueId }"
            ),
            "messageId": 1258,
            "handler": "GameMechanicsSystem._Handle_LeaveSubGameInst",
            "address": "0x18736b8a4",
            "fields": ["gameId", "gameInstId", "gameUniqueId"],
            "effect": "Resolve and leave the live SubGame runtime; no mission/quest or scene/script pair is returned.",
            "exchangeFamily": "subgame_lifecycle",
            "exchangeRole": "server_push",
            "runtimeScope": "SubGameRuntime",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "domain-depot-recv-package-response",
            "direction": "server_to_client",
            "message": "SC_DOMAIN_DEPOT_RECV_PACKAGE_FOR_DELIVER_RSP { deliverInstId }",
            "handler": "DomainDepotSystem._HandleDomainDepotRecvPackageForDeliverRsp",
            "address": "0x18730424c",
            "fields": ["deliverInstId"],
            "effect": (
                "Resolve the exact delivery instance, update its local delivery state, call "
                "_AddDialogInDelivering, install the typed NPC override dialog, and register "
                "the target-dialog finish callback."
            ),
            "exchangeFamily": "domain_depot_delivery",
            "exchangeRole": "response",
            "runtimeScope": "DomainDepotSystem / f1m25 mission shell",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "domain-depot-send-package-response",
            "direction": "server_to_client",
            "message": (
                "SC_DOMAIN_DEPOT_SEND_PACKAGE_FOR_DELIVER_RSP { deliverInstId, "
                "rewardValue, extraCreditCount }"
            ),
            "handler": "DomainDepotSystem._HandleDomainDepotSendPackageForDeliverRsp",
            "address": "0x187304774",
            "fields": ["deliverInstId", "rewardValue", "extraCreditCount"],
            "effect": (
                "Resolve the delivery instance and remove the delivery dialog override. The "
                "response also supplies the exact reward value and extra-credit count."
            ),
            "exchangeFamily": "domain_depot_delivery",
            "exchangeRole": "response",
            "runtimeScope": "DomainDepotSystem / f1m25 mission shell",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "skip-chapter-response",
            "direction": "server_to_client",
            "message": "SC_DO_SKIP_CHAPTER { skipChapterConfigId }",
            "handler": "ActivitySystem._HandleDoSkipChapter",
            "address": "0x1872cf2b8",
            "fields": ["skipChapterConfigId"],
            "effect": (
                "Handle the reply carrying the same skip-chapter configuration id. The "
                "installed fallback exposes no additional resolved non-wrapper side effect, "
                "so the contract does not infer quest placement or completion behavior."
            ),
            "exchangeFamily": "skip_chapter",
            "exchangeRole": "response",
            "runtimeScope": "ActivitySystem / e5m1 mission shell",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "level-script-task-state",
            "direction": "server_to_client",
            "message": (
                "SC_SCENE_LEVEL_SCRIPT_TASK_STATE_UPDATE (813) { sceneNumId, scriptId, "
                "taskId, taskState }"
            ),
            "handler": (
                "GameplayNetwork._Handle_LevelScriptTaskStateUpdate -> "
                "LevelScriptManager.UpdateLevelScriptTaskState -> "
                "LevelScriptRuntime.UpdateTaskState"
            ),
            "address": "0x183bd6fa0 -> 0x183bd7140 -> 0x183bd71f0",
            "fields": ["sceneNumId", "scriptId", "taskId", "taskState"],
            "effect": (
                "Resolve the exact scene/script runtime and task, then apply its server "
                "state. Nested local script events can now retain this task context in a "
                "runtime capture. The packet carries no missionId or questId."
            ),
            "exchangeFamily": "level_script_task",
            "exchangeRole": "server_push",
            "runtimeScope": "LevelScriptRuntime",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "level-script-task-progress-update",
            "direction": "server_to_client",
            "message": (
                "SC_SCENE_LEVEL_SCRIPT_TASK_PROGRESS_UPDATE (815) { sceneNumId, scriptId, "
                "taskId, conditionCompletedMap }"
            ),
            "handler": (
                "GameplayNetwork._Handle_LevelScriptTaskProgressUpdate -> "
                "LevelScriptRuntime.UpdateTaskMainObjectiveIsCompleted -> "
                "TaskCondition.InvokeOnIsCompleteChangeAction"
            ),
            "address": "0x1842ba410 -> 0x1842b9140 -> 0x1842bad00",
            "fields": ["sceneNumId", "scriptId", "taskId", "conditionCompletedMap"],
            "effect": (
                "Apply the server condition-completion map to one exact LevelScript task. "
                "The maintained hook keeps the map object opaque but records each exact "
                "condition id and its post-application completion boolean when the runtime "
                "synchronously notifies that condition."
            ),
            "exchangeFamily": "level_script_task",
            "exchangeRole": "server_push",
            "runtimeScope": "LevelScriptRuntime",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "level-script-task-start-finish",
            "direction": "server_to_client",
            "message": (
                "SC_SCENE_LEVEL_SCRIPT_TASK_START_FINISH (816) { sceneNumId, scriptId, "
                "taskId }"
            ),
            "handler": (
                "GameplayNetwork._Handle_LevelScriptTaskStartFinish -> "
                "LevelScriptManager.UpdateLevelScriptTaskStartFinish"
            ),
            "address": "0x1845e7f50 -> 0x1845e8090",
            "fields": ["sceneNumId", "scriptId", "taskId"],
            "effect": (
                "Route a server task lifecycle boundary to the exact scene/script/task. "
                "It proves no Story ordering by itself and supplies no mission/quest id."
            ),
            "exchangeFamily": "level_script_task",
            "exchangeRole": "server_push",
            "runtimeScope": "LevelScriptRuntime",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "level-script-set-done",
            "direction": "server_to_client",
            "message": "SC_SCENE_LEVEL_SCRIPT_SET_DONE (823) { sceneNumId, scriptId }",
            "handler": (
                "GameplayNetwork._Handle_SceneLevelScriptStateNotify -> "
                "LevelScriptManager.ServerSyncLevelScriptIsDone"
            ),
            "address": "0x187386060 -> 0x186f95218",
            "fields": ["sceneNumId", "scriptId"],
            "effect": (
                "Apply a server-authored done boundary to one LevelScript. The message has "
                "neither taskId nor mission/quest/Story identity."
            ),
            "exchangeFamily": "level_script_task",
            "exchangeRole": "server_push",
            "runtimeScope": "LevelScriptRuntime",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
    ],
    "outbound": [
        {
            "id": "accept-mission",
            "direction": "client_to_server",
            "message": "CS_ACCEPT_MISSION { missionId }",
            "messageId": 315,
            "handler": "MissionSystem.AcceptMission -> BasePlayerManager.SendMsg",
            "address": "0x1873b7b48",
            "fields": ["missionId"],
            "effect": "Request mission acceptance; await an asynchronous mission-state update rather than a paired accept response.",
            "responseMessage": None,
            "expectedServerPush": "SC_MISSION_STATE_UPDATE (112)",
            "asynchronous": True,
            "confidence": "native_proven",
        },
        {
            "id": "objective-progress",
            "direction": "client_to_server",
            "message": "CS_UPDATE_QUEST_OBJECTIVE",
            "messageId": 314,
            "handler": "MissionSystem.OnSubConditionProgressChanged -> BasePlayerManager.SendMsg",
            "address": "0x183a6fc20",
            "fields": [
                "questId",
                "objectiveValueOps[].conditionId",
                "objectiveValueOps[].value",
                "objectiveValueOps[].isAdd=false",
            ],
            "effect": (
                "Report an absolute value only when a ClientOnly condition leaf has a bound "
                "ResultChange callback. The server-placeholder fallback does not use this path."
            ),
            "responseMessage": None,
            "expectedServerPushes": [
                "SC_QUEST_OBJECTIVES_UPDATE (116)",
                "SC_QUEST_STATE_UPDATE (111)",
            ],
            "asynchronous": True,
            "confidence": "native_proven",
        },
        {
            "id": "level-script-task-progress",
            "direction": "client_to_server",
            "message": (
                "CS_SCENE_UPDATE_SCRIPT_TASK_PROGRESS (105) { sceneNumId, scriptId, "
                "taskId, objectiveValueOps[]:{ conditionId, value } }"
            ),
            "handler": (
                "LevelScriptRuntime.TaskCondition._OnConditionResultChanged -> "
                "GameplayNetwork.SendLevelScriptUpdateTaskProgress -> "
                "BaseNetworkSystem.SendMsg"
            ),
            "address": "0x186fb0f9c -> 0x1873825c8 -> 0x183f54e20",
            "fields": [
                "sceneNumId",
                "scriptId",
                "taskId",
                "objectiveValueOps[].conditionId",
                "objectiveValueOps[].value",
            ],
            "effect": (
                "A changed local task condition reports its exact scene/script/task, "
                "condition id, and absolute progress value. The payload carries no "
                "missionId, questId, or Story key; server consequences remain asynchronous."
            ),
            "responseMessage": None,
            "possibleServerPushes": [
                "SC_SCENE_LEVEL_SCRIPT_TASK_PROGRESS_UPDATE (815)",
                "SC_SCENE_LEVEL_SCRIPT_TASK_STATE_UPDATE (813)",
            ],
            "exchangeFamily": "level_script_task",
            "exchangeRole": "request_after_local_condition_change",
            "runtimeScope": "LevelScriptRuntime.TaskCondition",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "dialog-finish",
            "direction": "client_to_server",
            "message": "CS_FINISH_DIALOG",
            "messageId": 341,
            "handler": "DialogManager.FinishDialog -> _SendServer -> CinematicSystem.SendFinishDialog",
            "address": "0x186e0f2d4 -> 0x186e2d2c0 -> 0x1872f0d88",
            "fields": ["dialogId", "optionIds[]", "finishNums[]", "dialogExtraInfoType", "submitInfo?"],
            "effect": (
                "Submit the stable selected option ids and resolved dialog finish. "
                "SC_FINISH_DIALOG (131) is an asynchronous confirmation echo; the wire "
                "schema has no request UUID, so it is not a synchronous return."
            ),
            "expectedConfirmation": "SC_FINISH_DIALOG (131)",
            "correlationId": None,
            "asynchronous": True,
            "confidence": "native_proven",
        },
        {
            "id": "guide-group-complete-request",
            "direction": "client_to_server",
            "message": "CS_COMPLETE_GUIDE_GROUP { GuideGroupId, IsClose }",
            "handler": "GuideSystem._CompleteCurGuideGroup -> BasePlayerManager.SendMsg",
            "fields": ["GuideGroupId", "IsClose"],
            "effect": (
                "Submit completion for a server-backed guide group. A group registered "
                "through ManuallyStartGuideGroup is client-only and skips this request."
            ),
            "exchangeFamily": "guide_completion",
            "exchangeRole": "request",
            "runtimeScope": "GuideSystem",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "level-script-event",
            "direction": "client_to_server",
            "message": (
                "CS_SCENE_LEVEL_SCRIPT_EVENT_TRIGGER { sceneNumId:int32, "
                "scriptId:uint64, eventName:string, properties:map<string,string>, "
                "ctxToken:bytes }"
            ),
            "handler": "GameplayNetwork.TriggerLevelScriptServerEvent[WithProperties]",
            "address": "0x1845f6710 / 0x187383640",
            "fields": ["sceneNumId", "scriptId", "eventName", "properties", "ctxToken"],
            "effect": (
                "Trigger a server LevelScript event and await an empty acknowledgement. "
                "When CallServer handles a server-pushed client event, it can echo that "
                "event's ctxToken as netToken; the token still carries no mission, quest, "
                "condition, or Story identity."
            ),
            "exchangeFamily": "level_script_event",
            "exchangeRole": "request",
            "runtimeScope": "LevelScriptRuntime",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "client-global-var-update",
            "direction": "client_to_server",
            "message": "CS_UPDATE_CLIENT_GAME_VAR { key:int32, value:int64 }",
            "handler": (
                "SetClientGlobalVar.Execute -> GlobalVarSystem.SetClientVar -> "
                "BasePlayerManager.SendMsg"
            ),
            "fields": ["key", "value"],
            "effect": (
                "Resolve the authored string key through clientGameVarStringIdToNum, "
                "increment its pending-write count, raise local "
                "ON_CLIENT_GLOBAL_VAR_CHANGED (0x5d), and send the update."
            ),
            "exchangeFamily": "global_var",
            "exchangeRole": "request_after_local_event",
            "runtimeScope": "GlobalVarSystem",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "spawner-begin-wave",
            "direction": "client_to_server",
            "message": (
                "CS_SCENE_MONSTER_SPAWNER_BEGIN_WAVE { sceneNumId:int32, "
                "spawnerId:uint64, waveId:int32, clientTimestamp:double }"
            ),
            "handler": (
                "TimelineWaveBlock.TryToSendStart -> GameplayNetwork.SpawnerSendBeginWave "
                "-> BaseNetworkSystem.SendMsg"
            ),
            "fields": ["sceneNumId", "spawnerId", "waveId", "clientTimestamp"],
            "effect": "Request that the server begin the identified spawner wave.",
            "exchangeFamily": "spawner_wave",
            "exchangeRole": "request",
            "runtimeScope": "SpawnerRuntime",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "spawner-wave-confirm-complete",
            "direction": "client_to_server",
            "message": (
                "CS_SCENE_MONSTER_SPAWNER_WAVE_CONFIRM_COMPLETE { sceneNumId:int32, "
                "spawnerId:uint64, waveId:int32 }"
            ),
            "handler": (
                "SpawnerRuntime.TimelineWaveBlock.CheckAndSendConfirmWaveComplete -> "
                "GameplayNetwork.SpawnerSendWaveConfirmComplete"
            ),
            "fields": ["sceneNumId", "spawnerId", "waveId"],
            "effect": "Acknowledge completion of the identified wave to the server.",
            "exchangeFamily": "spawner_wave",
            "exchangeRole": "completion_acknowledgement",
            "runtimeScope": "SpawnerRuntime",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "touch-trigger-volume-request",
            "direction": "client_to_server",
            "message": (
                "CS_SCENE_TOUCH_TRIGGER_VOLUME_REQ { sceneNumId:int32, scriptId:uint64, "
                "scriptLocalId:uint32, isLeaveAction:bool }"
            ),
            "handler": "_OnLeaderTouchTriggerVolume -> BaseNetworkSystem.SendMsg",
            "address": "0x184256ac0",
            "fields": ["sceneNumId", "scriptId", "scriptLocalId", "isLeaveAction"],
            "effect": (
                "Report leader entry or exit for one LevelScript trigger slot and await the "
                "matching response on wait-server paths. No mission or quest id is sent."
            ),
            "exchangeFamily": "trigger_volume_touch",
            "exchangeRole": "request",
            "runtimeScope": "LevelScriptRuntime",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "scene-teleport-request",
            "direction": "client_to_server",
            "message": "CS_SCENE_TELEPORT",
            "handler": "TeleportProcessor.SendC2STeleportMsg",
            "address": "0x183a4c6f0",
            "fields": [
                "sceneNumId",
                "position",
                "rotation",
                "teleportReason",
                "passThroughData",
                "tpPosId",
                "tpReasonDetail(oneof)",
            ],
            "effect": (
                "Request a teleport. The reason-detail oneof can carry hub, camp, spatial-"
                "crossing, cutscene, or guide detail, but not a mission or quest id."
            ),
            "exchangeFamily": "scene_teleport",
            "exchangeRole": "request",
            "runtimeScope": "TeleportProcessor",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "scene-teleport-finish",
            "direction": "client_to_server",
            "message": "CS_SCENE_TELEPORT_FINISH { tpUuid:uint64 }",
            "handler": "TeleportProcessor._OnTeleportFinish",
            "address": "0x184970510",
            "fields": ["tpUuid"],
            "effect": (
                "Acknowledge completion of the SC_SCENE_TELEPORT identified by tpUuid. "
                "The packet does not carry the LevelEvent_OnTeleportFinish actionId filter."
            ),
            "exchangeFamily": "scene_teleport",
            "exchangeRole": "completion_acknowledgement",
            "runtimeScope": "TeleportProcessor",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "subgame-start-request",
            "direction": "client_to_server",
            "message": (
                "CS_GAME_MECHANICS_REQ_START { gameId, interactiveObjId, npcProxyId, npcObjId }"
            ),
            "messageId": 385,
            "handler": "GameMechanicsSystem.SendReqStartGameMechanic",
            "address": "0x18736a320",
            "fields": ["gameId", "interactiveObjId", "npcProxyId", "npcObjId"],
            "effect": (
                "Request the authored SubGame identified by gameId. Expect asynchronous "
                "enter and challenge-start pushes rather than a paired response."
            ),
            "exchangeFamily": "subgame_lifecycle",
            "exchangeRole": "request",
            "runtimeScope": "SubGameRuntime",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "subgame-stop-request",
            "direction": "client_to_server",
            "message": "CS_GAME_MECHANICS_REQ_STOP { curGameId }",
            "messageId": 386,
            "handler": "GameMechanicsSystem.SendReqStopGameMechanic",
            "address": "0x18736a5ec",
            "fields": ["curGameId"],
            "effect": (
                "Request that the current SubGame stop. WorldChallengeGame first ends its "
                "bound LevelScript when required, then expects an asynchronous leave push."
            ),
            "exchangeFamily": "subgame_lifecycle",
            "exchangeRole": "request",
            "runtimeScope": "SubGameRuntime",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "domain-depot-recv-package-request",
            "direction": "client_to_server",
            "message": "CS_DOMAIN_DEPOT_RECV_PACKAGE_FOR_DELIVER_REQ { deliverInstId }",
            "handler": (
                "DomainDepotSystem._SendDomainDepotRecvPackageForDeliverReq -> "
                "BasePlayerManager.SendMsg"
            ),
            "address": "0x18730628c",
            "fields": ["deliverInstId"],
            "effect": (
                "Ask the server to receive the package for one delivery instance. The "
                "expected response carries the same deliverInstId; its handler starts the "
                "typed target-dialog presentation."
            ),
            "expectedResponse": (
                "SC_DOMAIN_DEPOT_RECV_PACKAGE_FOR_DELIVER_RSP { deliverInstId }"
            ),
            "exchangeFamily": "domain_depot_delivery",
            "exchangeRole": "request",
            "runtimeScope": "DomainDepotSystem / f1m25 mission shell",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "domain-depot-send-package-request",
            "direction": "client_to_server",
            "message": "CS_DOMAIN_DEPOT_SEND_PACKAGE_FOR_DELIVER_REQ { deliverInstId }",
            "handler": (
                "DomainDepotSystem._OnTargetDialogFinish -> "
                "_SendDomainDepotSendPackageForDeliverReq -> BasePlayerManager.SendMsg"
            ),
            "address": "0x187305764 -> 0x18730632c",
            "fields": ["deliverInstId"],
            "effect": (
                "After the exact target dialog finishes, submit the delivery instance. The "
                "expected response returns deliverInstId, rewardValue, and extraCreditCount."
            ),
            "expectedResponse": (
                "SC_DOMAIN_DEPOT_SEND_PACKAGE_FOR_DELIVER_RSP { deliverInstId, "
                "rewardValue, extraCreditCount }"
            ),
            "exchangeFamily": "domain_depot_delivery",
            "exchangeRole": "request",
            "runtimeScope": "DomainDepotSystem / f1m25 mission shell",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
        {
            "id": "skip-chapter-request",
            "direction": "client_to_server",
            "message": "CS_DO_SKIP_CHAPTER { skipChapterConfigId }",
            "handler": "ActivitySystem.SendDoSkipChapter -> BasePlayerManager.SendUIMsg",
            "address": "0x1872cd7d0",
            "fields": ["skipChapterConfigId"],
            "effect": (
                "Construct and send the request using the exact typed SkipChapterTable "
                "configuration id. The expected reply carries that same id."
            ),
            "expectedResponse": "SC_DO_SKIP_CHAPTER { skipChapterConfigId }",
            "exchangeFamily": "skip_chapter",
            "exchangeRole": "request",
            "runtimeScope": "ActivitySystem / e5m1 mission shell",
            "asynchronous": True,
            "questScoped": False,
            "confidence": "native_proven",
        },
    ],
    "nativeEvidence": [
        {
            "symbol": "GameConditionServerPlaceHolder.get_conditionType",
            "address": "0x18479ec70",
            "finding": (
                "The installed-build fallback returns int.MaxValue (0x7fffffff); "
                "the method is IFix-gated at patch id 0x5605."
            ),
            "confidence": "native_proven",
        },
        {
            "symbol": "Gameplay.Beyond.patch.bytes",
            "finding": (
                "The current 82,021-byte Persistent IFix payload parses completely as "
                "30 signature targets. It replaces no selected receiver-ownership or "
                "LevelScript task registration/completion method and contains no explicit "
                "selected task-lane reference. Its two MissionSystem targets are HUD "
                "presentation methods; its seven dialog/cinematic targets alter playback "
                "implementation without adding an exact mission/task/LevelScript owner."
            ),
            "confidence": "installed_patch_proven",
        },
        {
            "symbol": "MissionSystem.<StartQuest>g__BindCallback|0",
            "address": "0x183a89700",
            "finding": (
                "Keeps a ResultChange callback only when conditionType equals ClientOnly "
                "(9999 / 0x270f), excluding the unpatched server placeholder."
            ),
            "confidence": "native_proven",
        },
        {
            "symbol": "LevelEvent.OnTeleportFinish.Process",
            "address": "0x186abe000",
            "finding": (
                "Compares the authored actionId filter with the local teleport-finish "
                "event actionId by exact string equality. That actionId is not tpUuid and "
                "does not appear in the teleport protocol payloads."
            ),
            "confidence": "native_proven",
        },
        {
            "symbol": "TeleportParam -> LoadingPipeline.LoadFinishStep",
            "address": "0x18315a6c0 -> 0x18315ade0 -> 0x183dd8c60",
            "finding": (
                "A whole-metadata census found 20 nominal mission/script co-carrier "
                "types; the sole new actionable carrier was TeleportParam. Current "
                "producers zero missionId and levelScriptId or never set them together. "
                "LoadFinishStep consumes source/levelScriptId/actionId or callbackHandle, "
                "and PerformerFactory consumes performId; no audited consumer reads "
                "missionId. This adds zero ownership or order edges."
            ),
            "confidence": "native_proven_bounded",
        },
        {
            "symbol": "MissionSystem.StartQuest",
            "address": "0x183a885d0",
            "finding": "Binds local quest/objective callbacks; no successor traversal was found.",
            "confidence": "native_proven",
        },
        {
            "symbol": "MissionRuntimeAsset.RunQuestAction",
            "address": "0x1872208d0 (action chain: 0x18722154c)",
            "finding": (
                "QuestAction is a flags enum: slot 1 is OnStartClientAction, slot 2 is "
                "OnSucceedClientAction, and slot 4 is OnFailedClientAction. SucceedQuest "
                "passes 2 and FailQuest passes 4 through SafeRunQuestAction; both clear "
                "a pending slot-1 action. Story refs reached by these action chains therefore "
                "run from the synchronized quest transition toward the Story file."
            ),
            "confidence": "native_proven",
        },
        {
            "symbol": "MissionSystem.Handle_ClientMissionEvent",
            "address": "0x1873bdf58 -> 0x184a428a0 -> 0x187bdfd38",
            "finding": (
                "Reads SC_SCENE_TRIGGER_CLIENT_MISSION_EVENT.missionId at +0x18 and "
                "eventName at +0x20, interns that exact pair through "
                "KeyGenerator<T1,T2>/CombineKeyManager, and publishes the resulting key "
                "through EventManager.SendGlobal. It does not target the serialized "
                "OnCustomEventForMission family. The publisher is the exact "
                "SendGlobal<Beyond.Gameplay.EventData> specialization; zero of 51 current "
                "BindGlobal specializations has the required "
                "Beyond.EventData<Beyond.Gameplay.EventData> subscriber shape. Compiled "
                "managed typed subscribers are absent; native manipulation, reflection, "
                "future IFix, and future builds remain outside the bound."
            ),
            "confidence": "native_proven_aot_subscriber_absence",
        },
        {
            "symbol": "GameplayNetwork._Handle_SceneTriggerClientLevelScriptEvent",
            "address": (
                "0x187386320 -> 0x1845f6000 -> 0x1845f6640 -> "
                "0x1845f6710 -> 0x1865a3aac"
            ),
            "finding": (
                "Consumes SC_SCENE_TRIGGER_CLIENT_LEVEL_SCRIPT_EVENT, constructs the "
                "LevelScript receiver from scriptId, copies a non-empty ctxToken into "
                "EventParams/ParamBlackboard, and raises eventName through "
                "LevelEventManager. The only current direct AOT reader of the same key is "
                "CallServer.Execute: it names the value netToken and passes it through "
                "GameAction.TriggerServerEvent and GameplayNetwork."
                "TriggerLevelScriptServerEvent to "
                "CS_SCENE_LEVEL_SCRIPT_EVENT_TRIGGER.set_CtxToken. This closes the token "
                "as round-trip/correlation context, not mission/quest identity; neither "
                "packet carries a mission, quest, condition, or Story identity."
            ),
            "confidence": "native_proven_bounded",
        },
        {
            "symbol": (
                "MissionSystem.Handle_MissionStateUpdate / Handle_QuestStateUpdate "
                "-> CharacterPositionCorrection"
            ),
            "address": "0x1873be300 / 0x1873bf0a0 -> 0x1873b84c4",
            "finding": (
                "Recursive runtime-type traversal across all 983 current enum-backed "
                "CS/SC message classes found zero mission/quest + LevelScript/Story "
                "identity co-carriers. The two active weaker scene carriers are messages "
                "112 and 111: their handlers pass roleBaseInfo leader position, rotation, "
                "and sceneName to CharacterPositionCorrection. That method resolves the "
                "scene to a map and performs guarded player-position reconciliation; it "
                "does not retain an authored mission/quest scene host. The installed "
                "30-target Gameplay IFix matches none of the two handlers or consumer."
            ),
            "confidence": "native_proven_bounded",
        },
        {
            "symbol": (
                "AirWallManager mission/quest listeners -> AirWallGroupAgent "
                "-> TriggerMainCharGoBack -> GameAction.PlayRadio"
            ),
            "address": (
                "0x1845d5df0 -> 0x186f49038 / 0x186f49278 -> "
                "0x186f45be8 / 0x186f45c50 -> 0x186f4ecc0"
            ),
            "finding": (
                "LevelData member 0 contains 822 exactly decoded AirWallGroup rows. "
                "Sixty co-carry typed mission/quest predicates and a pushback radio; "
                "58 resolve completely to 20 Story radios and produce 61 non-owning "
                "mission context attachments. Mission/quest state changes only "
                "re-evaluate the wall; radio playback occurs later on local player "
                "pushback. The current 30-target Gameplay IFix replaces no AirWall "
                "method."
            ),
            "confidence": "native_exact_serialized_co_carrier",
        },
        {
            "symbol": "GameplayNetwork._Handle_SyncLevelScriptStage",
            "address": "0x1873867cc",
            "finding": (
                "Consumes the one-way SC_SCENE_LEVEL_SCRIPT_STAGE_CHANGE packet, resolves "
                "the exact scene/script runtime, and updates its stage. On ready containers "
                "this raises a local SELF-scoped OnScriptStageChanged event; no mission, "
                "quest, client request, or paired response is present."
            ),
            "confidence": "native_proven",
        },
        {
            "symbol": "SendBattleSignalToLevel.ExecuteInternal",
            "address": "0x186d27734",
            "finding": (
                "Resolves the authored signal/value and raises local LevelEvent 0x28 "
                "directly. No network packet is sent; OnBattleSignal filters only the "
                "signal/value and cannot select an ability owner, spawner, mission, or quest."
            ),
            "confidence": "native_proven",
        },
        {
            "symbol": "SubGameManager.SrvCreateSubGame -> GameModeFactory.CreateGame",
            "address": "0x1870b31c8 -> 0x186f55a38",
            "finding": (
                "SC_GAME_MECHANICS_SYNC_ENTER_GAME_INST.gameId selects the authored table "
                "row and concrete client runtime. Typed rows containing bindScriptId and "
                "dungeonMissionId are exact mission-shell evidence, never a quest or Story "
                "playback edge."
            ),
            "confidence": "native_proven",
        },
        {
            "symbol": "WorldChallengeGame.SendQuit",
            "address": "0x186f60cc8",
            "finding": (
                "Reads SubGameInstanceData.bindScriptId at exact row offset +0x50, resolves "
                "the LevelScript, calls LevelScriptRuntime.ManualEnd when its type is not 5, "
                "then sends CS_GAME_MECHANICS_REQ_STOP. This proves cleanup/lifecycle use, "
                "not activation, quest ownership, or Story ownership."
            ),
            "confidence": "native_proven",
        },
        {
            "symbol": (
                "InteractiveLogicChallengeStartPoint._OnInteract -> "
                "LevelScriptRuntime.ManualStart"
            ),
            "address": "0x18713e548 + 0x34a -> 0x186faac74",
            "finding": (
                "Resolves the typed SubGame row from m_subGameId, reads "
                "bindScriptId at exact row offset +0x50, resolves that LevelScript, "
                "and calls ManualStart. This proves a generic interaction-start "
                "carrier for the exact bound script, not that an interaction fired, "
                "which mission owns Story playback, or Story order."
            ),
            "confidence": "native_proven",
        },
        {
            "symbol": "MissionSystem.OnSubConditionProgressChanged",
            "address": "0x183a6fc20",
            "finding": "Sends an absolute CS_UPDATE_QUEST_OBJECTIVE operation for the changed condition id.",
            "confidence": "native_proven",
        },
        {
            "symbol": "DialogTreeController.SelectIndex -> DialogTree.Continue",
            "finding": "The resolved option index selects an outgoing DialogTree connection.",
            "confidence": "native_proven",
        },
        {
            "symbol": "DialogTreeFinishNode.DoExecute -> DialogManager.FinishDialog",
            "finding": "The finish node supplies the finish id sent and synchronized later.",
            "confidence": "native_proven",
        },
        {
            "symbol": "CheckTalkOptionFinish.Check",
            "finding": (
                "Negative finish id means any recorded finish; a nonnegative id requires "
                "exact membership in dialogFinishInfos."
            ),
            "confidence": "native_proven",
        },
    ],
    "protocolOnly": [
        {
            "id": "fail-mission-capability",
            "message": "CS_FAIL_MISSION (311) { missionId }",
            "fields": ["missionId"],
            "possibleServerPush": "SC_MISSION_FAILED (114) { missionId }",
            "effect": (
                "The request schema exists, but no non-protobuf fallback constructor "
                "caller was recovered in the installed binary. Do not draw an active send."
            ),
            "confidence": "protocol_schema_only_sender_unconfirmed",
        },
        {
            "id": "mission-event-capability",
            "message": (
                "CS_MISSION_EVENT_TRIGGER (316) { missionId, eventName, properties }"
            ),
            "fields": ["missionId", "eventName", "properties"],
            "possibleServerPush": (
                "SC_MISSION_EVENT_TRIGGER (126) { missionId, eventName }"
            ),
            "effect": (
                "The request and server schemas exist, but the installed fallback has no "
                "gameplay constructor caller for request 316 and no typed handler for push "
                "126. They are inactive current-build fallback surfaces, not an inferred "
                "request/response pair."
            ),
            "confidence": "native_fallback_sender_and_handler_absent",
        },
        {
            "id": "mission-client-trigger-done-capability",
            "message": (
                "CS_MISSION_CLIENT_TRIGGER_DONE (317) { missionId, sceneName, areaId }"
            ),
            "fields": ["missionId", "sceneName", "areaId"],
            "possibleServerPush": None,
            "effect": (
                "The schema exists, but the installed fallback has no gameplay constructor "
                "caller; references are limited to generated protobuf copy and parser "
                "factories. Message 125 has a separate native inbound handler, and the "
                "different fields do not prove that 317 acknowledges it."
            ),
            "confidence": "native_fallback_sender_absent",
        },
    ],
}


CASE_STUDIES: dict[str, dict[str, Any]] = {
    "e7m3": {
        "title": "Parallel fork and AND join",
        "summary": (
            "MissionRuntime q16 fans out to two dialog objectives, and authored quest-state "
            "conditions require both before q29 advances; flowIndex does not make them exclusive."
        ),
        "nodes": {
            "e7m3_q#16": "fanout",
            "e7m3_q#17": "parallel objective",
            "e7m3_q#18": "parallel objective",
            "e7m3_q#29": "AND join",
        },
        "confidence": "asset_native",
    },
    "c16m3": {
        "title": "Condition-driven AND join",
        "summary": (
            "q21 has one predecessor but actively ANDs Completed-state checks for q2, q3, and q4. "
            "Joins are not encoded only by multiple prevQuestIdList entries."
        ),
        "nodes": {
            "c16m3_q#2": "monitored completion",
            "c16m3_q#3": "monitored completion",
            "c16m3_q#4": "monitored completion",
            "c16m3_q#21": "active AND monitor",
        },
        "confidence": "asset_proven",
    },
    "e2m5": {
        "title": "Repeatable outcomes, not an exclusive route",
        "summary": (
            "MissionRuntime q24 and q27 listen for finishes 1 and 2 of the same dialog, while "
            "q23 requires both persisted result properties; this is not an exclusive branch."
        ),
        "nodes": {
            "e2m5_q#12": "fanout",
            "e2m5_q#23": "requires both result properties",
            "e2m5_q#24": "dialog finish 1 flag",
            "e2m5_q#27": "dialog finish 2 flag",
        },
        "confidence": "asset_native",
    },
    "e7m4": {
        "title": "Persisted cinematic timeline result",
        "summary": (
            "Timeline finish routing maps 'confront Ruan Yi' to finish 0/q9 and 'prepare longer' "
            "to finish 1/q2. Only q2 is referenced by later LevelScript 23300030006; the exact "
            "high-level gated action remains unresolved."
        ),
        "nodes": {
            "e7m4_q#9": "timeline result 2 -> finish 0",
            "e7m4_q#2": "timeline result 1 -> finish 1; consumed later",
        },
        "confidence": "asset_native",
    },
}


SERVER_CONDITION_TYPES = {"GameConditionServerPlaceHolder"}
SYNC_HISTORY_TYPES = {"CheckTalkOptionFinish"}
SYNC_STATE_TYPES = {
    "CheckQuestState",
    "SimpleConditionCheckQuestState",
    "CheckMissionSucceedId",
}

QUEST_ACTION_TRIGGERS = {
    1: "OnStartClientAction",
    2: "OnSucceedClientAction",
    4: "OnFailedClientAction",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mission-root", type=Path, default=DEFAULT_MISSION_ROOT)
    parser.add_argument("--subgame-table", type=Path, default=DEFAULT_SUBGAME_TABLE)
    parser.add_argument("--activity-stage-table", type=Path, default=DEFAULT_ACTIVITY_STAGE_TABLE)
    parser.add_argument(
        "--activity-dungeon-fighting-stage-table",
        type=Path,
        default=DEFAULT_ACTIVITY_DUNGEON_FIGHTING_STAGE_TABLE,
    )
    parser.add_argument(
        "--activity-snapshot-stage-table",
        type=Path,
        default=DEFAULT_ACTIVITY_SNAPSHOT_STAGE_TABLE,
    )
    parser.add_argument(
        "--game-mechanic-condition-table",
        type=Path,
        default=DEFAULT_GAME_MECHANIC_CONDITION_TABLE,
    )
    parser.add_argument("--dungeon-table", type=Path, default=DEFAULT_DUNGEON_TABLE)
    parser.add_argument("--text-vo-id-table", type=Path, default=DEFAULT_TEXT_VO_ID_TABLE)
    parser.add_argument(
        "--lua-consumer-audit",
        type=Path,
        default=DEFAULT_LUA_CONSUMER_REFERENCE_AUDIT,
        help="complete shipped-Lua GameAction census used for exact Story playback",
    )
    parser.add_argument(
        "--cutscene-case-audit",
        type=Path,
        action="append",
        help=(
            "installed-binary spelling audit used to reject a matching Lua "
            "case mismatch; repeatable"
        ),
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--story-data-root", type=Path, default=DEFAULT_STORY_DATA_ROOT)
    parser.add_argument("--story-language", default="CN")
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    parser.add_argument(
        "--source-story-gap-queue",
        type=Path,
        default=DEFAULT_SOURCE_STORY_GAP_QUEUE,
        help=(
            "fresh source-story gap queue whose exact offline-exhaustion "
            "boundaries are projected into Story trigger metadata"
        ),
    )
    parser.add_argument(
        "--refresh-source-story-gap-queue",
        action="store_true",
        help=(
            "rebuild and validate the source-story gap queue after current "
            "partial-order and Story coverage reports are published, before "
            "projecting recovery evidence into Mission Pipeline"
        ),
    )
    parser.add_argument(
        "--runtime-trace-bundle",
        type=Path,
        help=(
            "normalized missionRuntimeTrace.v1 JSON to publish as an observed-only "
            "Mission Pipeline overlay"
        ),
    )
    return parser.parse_args()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    path.write_text(encoded + "\n", encoding="utf-8", newline="\n")


def refresh_source_story_gap_queue(
    language: str,
    queue_path: Path,
) -> dict[str, Any]:
    """Refresh the canonical queue only after all of its generated inputs exist."""
    queue_path = queue_path.resolve()
    expected_path = (
        queue_path.parent / f"source_story_gap_queue_{language}.json"
    ).resolve()
    if queue_path != expected_path:
        raise ValueError(
            "source Story gap refresh requires the canonical language filename: "
            f"expected={expected_path} actual={queue_path}"
        )
    command = [
        sys.executable,
        str(
            ROOT
            / "scripts"
            / "story_recovery"
            / "build_source_story_gap_queue.py"
        ),
        "--language",
        language,
        "--reports-dir",
        str(queue_path.parent),
    ]
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode:
        raise RuntimeError(
            "source Story gap refresh failed: "
            f"returncode={result.returncode} queue={repo_path(queue_path)}"
        )
    if not queue_path.is_file():
        raise RuntimeError(
            "source Story gap refresh produced no queue: "
            f"queue={repo_path(queue_path)}"
        )
    report = read_json(queue_path)
    failures: list[dict[str, Any]] = []
    if report.get("_schema") != SOURCE_STORY_GAP_QUEUE_SCHEMA:
        failures.append({
            "gate": "schema",
            "expected": SOURCE_STORY_GAP_QUEUE_SCHEMA,
            "actual": report.get("_schema"),
        })
    if str(report.get("language") or "").upper() != language.upper():
        failures.append({
            "gate": "language",
            "expected": language.upper(),
            "actual": report.get("language"),
        })
    validator_statuses: list[tuple[str, dict[str, Any]]] = []
    pending_statuses: list[tuple[str, Any]] = [("report", report)]
    while pending_statuses:
        validator, status = pending_statuses.pop()
        if not isinstance(status, dict):
            continue
        if any(
            key in status
            for key in (
                "status",
                "validationFailures",
                "validationFailureDetails",
                "sourceHashMismatches",
            )
        ):
            validator_statuses.append((validator, status))
        pending_statuses.extend(
            (f"{validator}.{key}", value)
            for key, value in status.items()
            if isinstance(value, dict)
        )
    for validator, status in validator_statuses:
        validation_failures = [
            *(
                status.get("validationFailures")
                if isinstance(status.get("validationFailures"), list)
                else []
            ),
            *(
                status.get("validationFailureDetails")
                if isinstance(status.get("validationFailureDetails"), list)
                else []
            ),
        ]
        hash_mismatches = (
            status.get("sourceHashMismatches")
            if isinstance(status.get("sourceHashMismatches"), list)
            else []
        )
        state = str(status.get("status") or "")
        if (
            validation_failures
            or hash_mismatches
            or "fail" in state
            or "mismatch" in state
        ):
            first_validation_failure = (
                validation_failures[0] if validation_failures else None
            )
            first_hash_mismatch = (
                hash_mismatches[0] if hash_mismatches else None
            )
            diagnostic = (
                first_validation_failure
                if isinstance(first_validation_failure, dict)
                else first_hash_mismatch
                if isinstance(first_hash_mismatch, dict)
                else {}
            )
            failures.append({
                "gate": "validator",
                "validator": validator,
                "status": state,
                "validationFailureCount": len(validation_failures),
                "sourceHashMismatchCount": len(hash_mismatches),
                "expected": diagnostic.get("expected"),
                "actual": diagnostic.get("actual"),
                "missionId": diagnostic.get("missionId"),
                "storyKey": diagnostic.get("storyKey"),
                "sourceFile": (
                    diagnostic.get("sourceFile")
                    or diagnostic.get("source")
                    or status.get("source")
                ),
                "firstFailure": first_validation_failure,
                "firstSourceHashMismatch": first_hash_mismatch,
            })
    if failures:
        first = failures[0]
        raise RuntimeError(
            "source Story gap validation failed: "
            f"gate={first.get('gate')} "
            f"validator={first.get('validator') or '-'} "
            f"mission={first.get('missionId') or '-'} "
            f"story={first.get('storyKey') or '-'} "
            f"expected={first.get('expected')} "
            f"actual={first.get('actual')} "
            f"source={first.get('sourceFile') or '-'} "
            f"queue={repo_path(queue_path)}"
        )
    print(
        "Source Story gap queue refreshed and validated: "
        f"{repo_path(queue_path)}"
    )
    return report


def repo_path(path: Path) -> str:
    path = path.resolve()
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.as_posix()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _lua_phase(module: str) -> str:
    parts = Path(module).as_posix().split("/")
    if len(parts) >= 2 and parts[0].casefold() == "phase":
        return re.sub(r"(?<!^)(?=[A-Z])", "_", parts[1]).lower()
    scope = parts[-2] if len(parts) >= 2 else Path(module).stem
    return re.sub(r"(?<!^)(?=[A-Z])", "_", scope).lower()


def load_lua_story_playback_evidence(
    lua_audit_path: Path = DEFAULT_LUA_CONSUMER_REFERENCE_AUDIT,
    case_audit_paths: Iterable[Path] = (DEFAULT_CUTSCENE_CASE_RESOLUTION_AUDIT,),
) -> dict[str, Any]:
    """Validate and normalize corpus-scanned shipped-Lua Story playback.

    This is deliberately data-driven: every accepted/rejected row comes from
    the complete Lua audit. Exact spelling is admitted; a spelling mismatch is
    rejected only when a current installed-binary audit matches that exact call.
    """
    validator = "lua_story_playback_evidence"
    lua_audit_path = lua_audit_path.resolve()
    if not lua_audit_path.is_file():
        raise RuntimeError(
            f"validator={validator} failed: gate=audit_exists expected=file "
            f"actual=missing source={repo_path(lua_audit_path)}"
        )
    audit_sha = sha256_path(lua_audit_path)
    audit = read_json(lua_audit_path)
    schema = str(audit.get("schemaVersion") or "")
    if schema != LUA_CONSUMER_REFERENCE_SCHEMA:
        raise RuntimeError(
            f"validator={validator} failed: gate=schema expected={LUA_CONSUMER_REFERENCE_SCHEMA} "
            f"actual={schema or '<missing>'} source={repo_path(lua_audit_path)}"
        )
    summary = audit.get("summary") or {}
    if int(summary.get("readErrorCount") or 0):
        raise RuntimeError(
            f"validator={validator} failed: gate=complete_scan expected=readErrorCount:0 "
            f"actual={summary.get('readErrorCount')} source={repo_path(lua_audit_path)}"
        )

    calls = list((audit.get("gameActionAudit") or {}).get("storyPlaybackCalls") or [])
    malformed: list[str] = []
    for index, row in enumerate(calls):
        required = {
            "module": row.get("module"),
            "sourcePath": row.get("sourcePath"),
            "sourceSha256": row.get("sourceSha256"),
            "line": row.get("line"),
            "method": row.get("method"),
            "argumentSemantics": row.get("argumentSemantics"),
            "registryStatus": row.get("registryStatus"),
        }
        missing = [key for key, value in required.items() if value in (None, "")]
        source_sha = str(row.get("sourceSha256") or "")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", source_sha):
            missing.append("sourceSha256:sha256")
        if missing:
            malformed.append(f"row={index} missing={','.join(missing)}")
            continue
        source_path = ROOT / str(row["sourcePath"])
        if source_path.is_file():
            actual_sha = sha256_path(source_path)
            if actual_sha.casefold() != source_sha.casefold():
                malformed.append(
                    f"row={index} sourceHash expected={source_sha} actual={actual_sha} "
                    f"source={repo_path(source_path)}"
                )
        table_resolution = row.get("tableFieldResolution")
        if isinstance(table_resolution, dict):
            table_required = {
                "table": table_resolution.get("table"),
                "tableSourcePath": table_resolution.get("tableSourcePath"),
                "tableSourceSha256": table_resolution.get("tableSourceSha256"),
                "field": table_resolution.get("field"),
            }
            table_missing = [
                key for key, value in table_required.items()
                if value in (None, "")
            ]
            table_sha = str(table_resolution.get("tableSourceSha256") or "")
            if not re.fullmatch(r"[0-9a-fA-F]{64}", table_sha):
                table_missing.append("tableSourceSha256:sha256")
            candidates = table_resolution.get("candidateRows") or []
            if row.get("literalResolution") == "table_field_singleton":
                if len(candidates) != 1 or not table_resolution.get("exactSingleton"):
                    table_missing.append("candidateRows:exact_singleton")
            if table_missing:
                malformed.append(
                    f"row={index} tableResolution={','.join(table_missing)}"
                )
                continue
            table_source = ROOT / str(table_resolution["tableSourcePath"])
            if table_source.is_file():
                actual_table_sha = sha256_path(table_source)
                if actual_table_sha.casefold() != table_sha.casefold():
                    malformed.append(
                        f"row={index} tableSourceHash expected={table_sha} "
                        f"actual={actual_table_sha} source={repo_path(table_source)}"
                    )
    if malformed:
        raise RuntimeError(
            f"validator={validator} failed: gate=row_provenance expected=complete_exact_rows "
            f"actual={malformed[0]} source={repo_path(lua_audit_path)}"
        )

    case_audits: list[tuple[Path, dict[str, Any]]] = []
    for path in case_audit_paths:
        resolved = path.resolve()
        if not resolved.is_file():
            continue
        case = read_json(resolved)
        source = case.get("source") or {}
        conclusion = case.get("conclusion") or {}
        if (
            int(case.get("schemaVersion") or 0) != 1
            or str(source.get("luaAuditSha256") or "").casefold() != audit_sha.casefold()
            or conclusion.get("caseResolution") != "case_sensitive"
            or conclusion.get("literalResolvesToCanonicalKey") is not False
            or not re.fullmatch(r"[0-9a-fA-F]{64}", str(source.get("gameAssemblySha256") or ""))
            or not re.fullmatch(r"[0-9a-fA-F]{64}", str(source.get("metadataSha256") or ""))
        ):
            raise RuntimeError(
                f"validator={validator} failed: gate=binary_case_audit expected=current_lua_hash+case_sensitive "
                f"actual=invalid source={repo_path(resolved)}"
            )
        case_audits.append((resolved, case))

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in calls:
        status = str(row.get("registryStatus") or "")
        method = str(row.get("method") or "")
        native_entry = f"{NATIVE_GAME_ACTION_TYPE}::{method}"
        if status == "exact_registry_match":
            story_key = str(row.get("canonicalStoryKey") or "")
            if (
                not story_key
                or row.get("argumentSemantics") != "story_id"
                or row.get("resolvedLiteral") != story_key
            ):
                continue
            module = str(row["module"])
            virtual_lua_file = f"Lua/Data/LuaScripts/{module}"
            table_resolution = row.get("tableFieldResolution") or {}
            table_candidates = table_resolution.get("candidateRows") or []
            table_candidate = (
                table_candidates[0]
                if len(table_candidates) == 1
                and row.get("literalResolution") == "table_field_singleton"
                else {}
            )
            row_fields = table_candidate.get("rowFields") or {}
            mission_id = str(row_fields.get("missionId") or "") or None
            quest_id = str(row_fields.get("questId") or "") or None
            table_source_path = str(
                table_resolution.get("tableSourcePath") or ""
            )
            is_table_carrier = bool(table_candidate)
            accepted.append({
                "storyKey": story_key,
                "luaFile": virtual_lua_file,
                "luaSourcePath": str(row["sourcePath"]),
                "luaSourceSha256": str(row["sourceSha256"]).lower(),
                "luaLine": int(row["line"]),
                "luaSymbol": str(row.get("firstArgument") or ""),
                "luaCall": f"GameAction.{method}",
                "nativeEntry": native_entry,
                "phase": _lua_phase(module),
                "playbackKind": row.get("playbackKind"),
                "literalResolution": str(row.get("literalResolution") or ""),
                "missionId": mission_id,
                "questId": quest_id,
                "table": str(table_resolution.get("table") or ""),
                "tableKey": str(table_candidate.get("tableKey") or ""),
                "tableField": str(table_resolution.get("field") or ""),
                "tableLookupKeyExpression": str(
                    table_resolution.get("lookupKeyExpression") or ""
                ),
                "tableSourcePath": table_source_path,
                "tableSourceSha256": str(
                    table_resolution.get("tableSourceSha256") or ""
                ).lower(),
                "auditReport": repo_path(lua_audit_path),
                "auditSha256": audit_sha,
                "note": (
                    (
                        "The complete shipped-Lua census traced this typed GameAction "
                        "call through one exact current-table row. That same row "
                        "co-carries the published mission/quest identity."
                    )
                    if is_table_carrier and (mission_id or quest_id)
                    else (
                        "The complete shipped-Lua census found an exact-case literal at "
                        "this typed GameAction playback call. The Lua controller owns "
                        "playback; no mission or quest identity is serialized."
                    )
                ),
            })
            continue
        if status != "case_mismatch_registry_match":
            continue
        for case_path, case in case_audits:
            proof_row = case.get("luaPlayback") or {}
            comparable = ("module", "line", "method", "resolvedLiteral", "canonicalStoryKey")
            if not all(proof_row.get(key) == row.get(key) for key in comparable):
                continue
            source = case.get("source") or {}
            rejected.append({
                "storyKey": str(row.get("canonicalStoryKey") or ""),
                "luaLiteral": str(row.get("resolvedLiteral") or ""),
                "luaFile": f"Lua/Data/LuaScripts/{row['module']}",
                "luaSourcePath": str(row["sourcePath"]),
                "luaSourceSha256": str(row["sourceSha256"]).lower(),
                "luaLine": int(row["line"]),
                "luaSymbol": str(row.get("firstArgument") or ""),
                "luaCall": f"GameAction.{method}",
                "nativeEntry": native_entry,
                "reason": "case_sensitive_native_resource_lookup",
                "confidence": "binary_proven_rejection",
                "auditReport": repo_path(case_path),
                "gameAssemblySha256": str(source["gameAssemblySha256"]).lower(),
                "metadataSha256": str(source["metadataSha256"]).lower(),
                "note": (
                    "The installed binary preserves this mismatched literal through "
                    "StringPathHash lookup, so it cannot prove playback of the "
                    "differently-cased Story registry key."
                ),
            })
            break

    accepted.sort(key=lambda row: (natural_quest_key(row["storyKey"]), row["luaFile"], row["luaLine"]))
    rejected.sort(key=lambda row: (natural_quest_key(row["storyKey"]), row["luaFile"], row["luaLine"]))
    runtime_dispatchers = [
        row for row in calls
        if row.get("playbackRole") == "runtime_queue_dispatcher"
    ]
    runtime_contract = (audit.get("gameActionAudit") or {}).get(
        "runtimeHandleContract"
    ) or {}
    action_producer_routes = runtime_contract.get("actionProducerRoutes") or []
    if runtime_dispatchers and (
        not runtime_contract.get("report")
        or not re.fullmatch(
            r"[0-9a-fA-F]{64}",
            str(runtime_contract.get("sha256") or ""),
        )
        or not {
            str(row.get("method") or "") for row in runtime_dispatchers
        }.issubset(set(runtime_contract.get("dispatcherMethods") or []))
        or not action_producer_routes
        or any(
            not row.get("actionType")
            or not row.get("producerMethod")
            or not row.get("actionToken")
            for row in action_producer_routes
        )
    ):
        raise RuntimeError(
            f"validator={validator} failed: gate=runtime_handle_contract "
            f"expected=complete_binary_dispatch_family actual=invalid "
            f"source={repo_path(lua_audit_path)}"
        )
    return {
        "validator": validator,
        "status": "validated",
        "schemaVersion": LUA_CONSUMER_REFERENCE_SCHEMA,
        "auditReport": repo_path(lua_audit_path),
        "auditSha256": audit_sha,
        "scannedPlaybackCalls": len(calls),
        "acceptedExactPlaybackCalls": accepted,
        "rejectedCaseMismatchCalls": rejected,
        "runtimeHandleDispatcherCalls": runtime_dispatchers,
        "runtimeHandleDispatcherCallCount": len(runtime_dispatchers),
        "runtimeHandleDispatcherFamilyCount": 1 if runtime_dispatchers else 0,
        "runtimeHandleContract": runtime_contract,
        "unresolvedPlaybackCalls": (
            len(calls) - len(accepted) - len(rejected) - len(runtime_dispatchers)
        ),
        "acceptedTableCarrierCalls": sum(
            1 for row in accepted if row.get("literalResolution") == "table_field_singleton"
        ),
        "binaryCaseAuditCount": len(case_audits),
        "evidenceBoundary": (
            "Exact shipped-Lua bytes and typed GameAction calls prove controller "
            "playback. A mission/quest attachment is admitted only when the same "
            "resolved original table row co-carries that identity; otherwise Lua "
            "does not supply mission ownership or Story order. "
            "Binary-proven cinematic-handle calls are one polymorphic runtime "
            "dispatcher family and are not counted as unresolved authored references. "
            "A binary-discovered typed action-to-producer route can annotate an exact "
            "LevelScript playback route and attach its audit file, but cannot supply "
            "mission ownership or order by itself. "
            "Case-folded matches create no route without matching installed-binary proof."
        ),
    }


def offline_story_kind(story_key: str) -> str:
    """Preserve the Story kind for denominator-neutral recovery overlays."""
    if story_key.startswith("radio_"):
        return "radio"
    if story_key.startswith("cutscene_"):
        return "cutscene"
    if story_key.startswith("sns_"):
        return "sns"
    if story_key.startswith("black_"):
        return "black"
    if story_key.startswith(("dlg_", "misc_dlg_")):
        return "dlg"
    return "text"


def publish_offline_story_recovery(
    story_trigger_manifest: dict[str, dict[str, Any]],
    gap_queue_path: Path | None,
) -> dict[str, Any]:
    """Attach fail-closed offline recovery boundaries without adding routes.

    The source-story gap queue is a recovery worklist, not graph evidence.
    Only its exact current schema and active, graph-neutral evidence block are
    accepted. Published rows annotate existing manifest records. Story kinds
    outside the coverage denominator are emitted in a separate overlay with an
    explicit denominator-neutral status. Neither path changes an existing
    ``attachmentStatus`` nor adds trigger routes.
    """
    inactive = {
        "status": "unavailable",
        "schema": "",
        "mappingId": "",
        "graphEffect": "none",
        "publishedStoryKeys": 0,
        "publishedRuntimeContextStoryKeys": 0,
        "publishedProjectAuthoredStoryKeys": 0,
        "outsidePipelineCoverageStoryKeys": 0,
        "storyTriggerManifestOverlay": {},
        "questAttachmentDiagnosticStatus": "unavailable",
        "questAttachmentDiagnosticMappingId": "",
        "questAttachmentDiagnostics": {},
        "source": repo_path(gap_queue_path) if gap_queue_path else "",
    }
    if gap_queue_path is None or not gap_queue_path.is_file():
        return inactive
    payload = read_json(gap_queue_path)
    if not isinstance(payload, dict):
        return inactive
    schema = str(payload.get("_schema") or "")
    status = payload.get("offlineExhaustionEvidence")
    if (
        schema != SOURCE_STORY_GAP_QUEUE_SCHEMA
        or not isinstance(status, dict)
        or status.get("status") != "active"
        or status.get("graphEffect") != "none"
        or status.get("sourceHashMismatches")
    ):
        return {
            **inactive,
            "schema": schema,
            "status": "rejected_stale_or_incompatible",
        }

    published = 0
    published_keys: set[str] = set()
    published_partial_keys: set[str] = set()
    published_runtime_context_keys: set[str] = set()
    published_project_authored_keys: set[str] = set()
    manifest_overlay: dict[str, dict[str, Any]] = {}
    diagnostic_status = payload.get("questAttachmentDiagnosticEvidence")
    diagnostic_active = (
        isinstance(diagnostic_status, dict)
        and diagnostic_status.get("status") == "active"
        and diagnostic_status.get("graphEffect") == "none"
        and not diagnostic_status.get("sourceHashMismatches")
        and not diagnostic_status.get("validationFailures")
    )
    quest_attachment_diagnostics: dict[str, dict[str, Any]] = {}
    project_status = payload.get("projectAuthoredStoryEvidence")
    project_active = (
        isinstance(project_status, dict)
        and project_status.get("status") == "validated"
        and project_status.get("graphEffect") == "none"
        and not project_status.get("validationFailures")
    )
    for mission in payload.get("missions") or []:
        if not isinstance(mission, dict):
            continue
        if diagnostic_active:
            for row in mission.get("closedQuestAttachmentDiagnostics") or []:
                if not isinstance(row, dict) or row.get("graphEffect") != "none":
                    continue
                quest_id = str(row.get("questId") or "")
                if not quest_id:
                    continue
                quest_attachment_diagnostics[quest_id] = {
                    key: value
                    for key, value in row.items()
                    if key not in {"sourceHashes", "expectedSourceHashes"}
                }
        for row in mission.get("deferredOfflineExhaustedIsolatedScenes") or []:
            if not isinstance(row, dict) or row.get("graphEffect") != "none":
                continue
            story_key = str(row.get("sceneKey") or "")
            if not story_key:
                continue
            # Keep the exact negative-evidence boundary useful in the static UI
            # while dropping bulk source hashes and internal queue metrics.
            recovery = {
                key: value
                for key, value in row.items()
                if key not in {"sceneKey", "gameAssemblySha256"}
            }
            manifest_row = story_trigger_manifest.get(story_key)
            if isinstance(manifest_row, dict):
                manifest_row["offlineRecovery"] = recovery
                published += 1
                published_keys.add(story_key)
            else:
                manifest_overlay[story_key] = {
                    "key": story_key,
                    "kind": str(row.get("storyKind") or "")
                        or offline_story_kind(story_key),
                    "nominalMissionId": str(row.get("missionId") or ""),
                    "attachmentStatus":
                        "offline_exhausted_outside_pipeline_coverage_denominator",
                    "routes": [],
                    "offlineRecovery": recovery,
                }

        for row in mission.get("partialRegisteredDialogTreeCarriers") or []:
            if (
                not isinstance(row, dict)
                or row.get("graphEffect") != "none"
                or row.get("recoveryStatus")
                != "actionable_partial_registered_dialog_tree_partition"
            ):
                continue
            story_key = str(row.get("sceneKey") or "")
            if not story_key:
                continue
            recovery = {
                key: value
                for key, value in row.items()
                if key not in {"sceneKey", "gameAssemblySha256"}
            }
            manifest_row = story_trigger_manifest.get(story_key)
            if isinstance(manifest_row, dict):
                manifest_row["partialRecovery"] = recovery
            else:
                overlay = manifest_overlay.setdefault(story_key, {
                    "key": story_key,
                    "kind": offline_story_kind(story_key),
                    "nominalMissionId": str(row.get("missionId") or ""),
                    "attachmentStatus":
                        "partial_carrier_outside_pipeline_coverage_denominator",
                    "routes": [],
                })
                overlay["partialRecovery"] = recovery
            published_partial_keys.add(story_key)

        if project_active:
            for row in mission.get(
                "closedNonMissionContentIsolatedScenes"
            ) or []:
                if (
                    not isinstance(row, dict)
                    or row.get("evidenceKind")
                    != "project_authored_story_content"
                    or row.get("recoveryStatus")
                    != "excluded_project_authored_story_content"
                    or row.get("graphEffect") != "none"
                    or row.get("gameDataEvidence") is not False
                ):
                    continue
                story_key = str(row.get("sceneKey") or "")
                if not story_key:
                    continue
                recovery = {
                    key: value
                    for key, value in row.items()
                    if key != "sceneKey"
                }
                manifest_row = story_trigger_manifest.get(story_key)
                if isinstance(manifest_row, dict):
                    manifest_row["contentProvenance"] = recovery
                else:
                    overlay = manifest_overlay.setdefault(story_key, {
                        "key": story_key,
                        "kind": str(row.get("storyKind") or "")
                            or offline_story_kind(story_key),
                        "nominalMissionId": str(mission.get("mission") or ""),
                        "attachmentStatus":
                            "project_authored_outside_game_coverage_denominator",
                        "routes": [],
                    })
                    overlay["contentProvenance"] = recovery
                published_project_authored_keys.add(story_key)

        approved_runtime_contexts = {
            (
                "objective_tracking_story_reference",
                "closed_exact_mission_tracking_context_no_relative_order",
            ),
            (
                "dialog_tree_prime_reachable_story_playback_dependency",
                "closed_exact_parent_dialog_dependency_no_relative_order",
            ),
            (
                "mission_accept_dialog",
                "closed_exact_mission_accept_dialog_no_relative_order",
            ),
            (
                "sns_authored_mission_link",
                "closed_exact_authored_sns_mission_link_no_relative_order",
            ),
            (
                "airwall_mission_state_radio_playback_context",
                "closed_exact_native_playback_context_no_relative_order",
            ),
            (
                "npc_proxy_tracking_dialog_navigation_context",
                "closed_exact_non_owning_dialog_context_no_relative_order",
            ),
            (
                "npc_proxy_lazy_destroy_dialog_context",
                "closed_exact_non_owning_dialog_context_no_relative_order",
            ),
            (
                "npc_proxy_ex_mission_context",
                "closed_exact_runtime_config_no_relative_order",
            ),
            (
                "npc_proxy_ex_mission_context",
                "closed_exact_cross_mission_runtime_config_no_relative_order",
            ),
            (
                "npc_proxy_ex_mission_context",
                "closed_exact_multi_mission_runtime_config_no_relative_order",
            ),
        }
        for row in mission.get(
            "closedExactRuntimeConfigIsolatedScenes"
        ) or []:
            if not isinstance(row, dict):
                continue
            if (
                str(row.get("relation") or ""),
                str(row.get("recoveryStatus") or ""),
            ) not in approved_runtime_contexts:
                continue
            story_key = str(row.get("sceneKey") or "")
            if not story_key:
                continue
            recovery = {
                key: value
                for key, value in row.items()
                if key != "sceneKey"
            }
            recovery["graphEffect"] = "none"
            manifest_row = story_trigger_manifest.get(story_key)
            if isinstance(manifest_row, dict):
                manifest_row["runtimeContextRecovery"] = recovery
                published_runtime_context_keys.add(story_key)
            else:
                overlay = manifest_overlay.setdefault(story_key, {
                    "key": story_key,
                    "kind": offline_story_kind(story_key),
                    "nominalMissionId": str(
                        row.get("missionId")
                        or mission.get("mission")
                        or ""
                    ),
                    "attachmentStatus":
                        "runtime_context_outside_pipeline_coverage_denominator",
                    "routes": [],
                })
                overlay["runtimeContextRecovery"] = recovery
                published_runtime_context_keys.add(story_key)

        approved_native_contexts = {
            (
                "authoritative_scope_leveldata_mission_context",
                "closed_exact_cross_mission_leveldata_shell_playback_context_no_relative_order",
            ),
            (
                "cutscene_root_playback_alias_composed",
                "closed_exact_composed_root_playback_context_no_relative_order",
            ),
            (
                "lua_controller_playback",
                "closed_exact_lua_controller_playback_no_mission_owner_or_relative_order",
            ),
            (
                "timeline_dialog_contains_black",
                "closed_exact_timeline_black_carrier_context_owner_or_order_unresolved",
            ),
            (
                "dialog_tree_narrative_action",
                "closed_exact_dialog_tree_black_carrier_context_no_file_order",
            ),
            (
                "leveldata_levelscript_mission_context",
                "closed_exact_cross_mission_leveldata_playback_context_no_relative_order",
            ),
            (
                "leveldata_levelscript_mission_context",
                "closed_exact_same_mission_leveldata_playback_context_no_relative_order",
            ),
            (
                "cross_owner_levelscript_quest_playback_context",
                "closed_exact_cross_mission_quest_playback_context_no_relative_order",
            ),
            (
                "dialog_tree_reachable_story_playback",
                "closed_exact_connected_dialog_tree_playback_context_no_relative_order",
            ),
            (
                "levelscript_quest_state_gate",
                "closed_exact_quest_state_gated_playback_context_no_relative_order",
            ),
        }
        for row in mission.get("closedExactNativeIsolatedScenes") or []:
            if not isinstance(row, dict):
                continue
            if (
                str(row.get("relation") or ""),
                str(row.get("recoveryStatus") or ""),
            ) not in approved_native_contexts:
                continue
            story_key = str(row.get("sceneKey") or "")
            if not story_key:
                continue
            recovery = {
                key: value
                for key, value in row.items()
                if key != "sceneKey"
            }
            recovery["graphEffect"] = "none"
            manifest_row = story_trigger_manifest.get(story_key)
            if isinstance(manifest_row, dict):
                manifest_row["runtimeContextRecovery"] = recovery
                published_runtime_context_keys.add(story_key)
            else:
                overlay = manifest_overlay.setdefault(story_key, {
                    "key": story_key,
                    "kind": offline_story_kind(story_key),
                    "nominalMissionId": str(
                        row.get("nominalStoryMissionId")
                        or mission.get("mission")
                        or ""
                    ),
                    "attachmentStatus":
                        "runtime_context_outside_pipeline_coverage_denominator",
                    "routes": [],
                })
                overlay["runtimeContextRecovery"] = recovery
                published_runtime_context_keys.add(story_key)

    for story_key, entry in manifest_overlay.items():
        story_trigger_manifest.setdefault(story_key, entry)

    return {
        "status": "active",
        "schema": schema,
        "mappingId": str(status.get("mappingId") or ""),
        "graphEffect": "none",
        "publishedStoryKeys": len(published_keys),
        "publishedRows": published,
        "publishedPartialStoryKeys": len(published_partial_keys),
        "publishedRuntimeContextStoryKeys": len(
            published_runtime_context_keys
        ),
        "publishedProjectAuthoredStoryKeys": len(
            published_project_authored_keys
        ),
        "outsidePipelineCoverageStoryKeys": len(manifest_overlay),
        "storyTriggerManifestOverlay": manifest_overlay,
        "questAttachmentDiagnosticStatus": (
            "active" if diagnostic_active else "unavailable"
        ),
        "questAttachmentDiagnosticMappingId": (
            str(diagnostic_status.get("mappingId") or "")
            if diagnostic_active
            else ""
        ),
        "questAttachmentDiagnostics": quest_attachment_diagnostics,
        "source": repo_path(gap_queue_path),
    }


def publish_offline_recovery_mission_shells(
    index: dict[str, Any],
    output_root: Path,
    offline_recovery: dict[str, Any],
    gap_queue_path: Path,
) -> list[str]:
    """Publish navigable graph-neutral shells for exhausted non-runtime missions.

    A Story mission can exist in authored tables without a MissionRuntimeAsset.
    Its exact-build recovery boundary still belongs in Mission Pipeline, but a
    shell must never imply quests, ownership, playback, or order edges.
    """
    if offline_recovery.get("status") != "active":
        return []
    queue = read_json(gap_queue_path)
    if not isinstance(queue, dict):
        return []
    queue_rows = {
        str(row.get("mission") or ""): row
        for row in queue.get("missions") or []
        if isinstance(row, dict) and row.get("mission")
    }
    existing = {
        str(row.get("id") or "")
        for row in index.get("missions") or []
        if isinstance(row, dict) and row.get("id")
    }
    overlay = offline_recovery.get("storyTriggerManifestOverlay") or {}
    keys_by_mission: dict[str, list[str]] = defaultdict(list)
    kind_by_key: dict[str, str] = {}
    for story_key, entry in overlay.items():
        recovery = (
            entry.get("offlineRecovery") or entry.get("contentProvenance")
        ) if isinstance(entry, dict) else None
        mission_id = str(
            (recovery or {}).get("missionId")
            or (entry or {}).get("nominalMissionId")
            or ""
        )
        if mission_id and mission_id not in existing:
            keys_by_mission[mission_id].append(str(story_key))
            kind_by_key[str(story_key)] = str(entry.get("kind") or "")

    published: list[str] = []
    mission_output = output_root / "missions"
    mission_output.mkdir(parents=True, exist_ok=True)
    for mission_id in sorted(keys_by_mission, key=natural_quest_key):
        order_row = queue_rows.get(mission_id)
        if not isinstance(order_row, dict):
            continue
        story_keys = sorted(keys_by_mission[mission_id], key=natural_quest_key)
        metrics = order_row.get("metrics") or {}
        components = [
            {
                "id": f"p{index}",
                "sceneKeys": [story_key],
                "cyclic": False,
                "internalEdgeIndexes": [],
            }
            for index, story_key in enumerate(story_keys, start=1)
        ]
        story_order = {
            "mission": mission_id,
            "summary": {
                "sceneCount": int(metrics.get("sceneCount") or len(story_keys)),
                "strongEdgeCount": 0,
                "weakEdgeCount": 0,
                "cycleCount": 0,
                "unorderedScenePairs": int(metrics.get("totalScenePairs") or 0),
                "isolatedSceneCount": int(
                    metrics.get("isolatedScenes") or len(story_keys)
                ),
                "weakOnlySceneCount": 0,
            },
            "nodes": [
                {
                    "key": story_key,
                    "kind": kind_by_key.get(story_key)
                        or offline_story_kind(story_key),
                    "membership": "index",
                    "component": component["id"],
                    "relationStatus": "isolated",
                }
                for story_key, component in zip(story_keys, components)
            ],
            "components": components,
            "componentEdges": [],
            "reducedComponentEdges": [],
            "topologicalLayers": [[row["id"] for row in components]],
            "directEdges": [],
            "containments": [],
            "cycles": [],
            "branches": {
                "sceneGraphOptions": [],
                "nativeControlBranches": [],
                "nativeControlMerges": [],
                "nativeOrderedSequences": [],
                "nativeRelatedActionTopologies": [],
                "dialogLineOptions": [],
                "questForks": [],
                "questMerges": [],
            },
            "isolatedSceneKeys": story_keys,
            "weakOnlySceneKeys": [],
            "unknownSceneKeys": story_keys,
            "unresolvedSourceNodes": [],
            "sourceGapQueue": order_row,
        }
        payload = {
            "schemaVersion": SCHEMA_VERSION,
            "mission": {
                "id": mission_id,
                "nameKey": "",
                "descriptionKey": "",
                "levelId": "",
                "missionType": None,
                "rewardId": "",
                "mainPath": [],
                "entryQuestIds": [],
                "nativeRuntimeBindings": [],
                "source": repo_path(gap_queue_path),
                "offlineRecoveryShell": True,
                "sourceBoundary": (
                    "No MissionRuntimeAsset exists in the current export; this "
                    "shell exposes exact graph-neutral Story recovery only."
                ),
            },
            "nodes": [],
            "edges": [],
            "caseStudy": None,
            "missionGraph": {"upstream": {}, "downstream": {}},
            "envTalkContext": [],
            "storyOrder": story_order,
        }
        write_json(mission_output / f"{mission_id}.json", payload)
        summary = {
            "id": mission_id,
            "nameKey": "",
            "levelId": "",
            "questCount": 0,
            "mainPathCount": 0,
            "entryCount": 0,
            "fanoutCount": 0,
            "multiPrevJoinCount": 0,
            "activeJoinCount": 0,
            "exactFinishCount": 0,
            "serverPlaceholderCount": 0,
            "serverPlaceholderQuestCount": 0,
            "failureConditionCount": 0,
            "externalDependencyCount": 0,
            "submitItemConditionCount": 0,
            "submitItemQuestCount": 0,
            "submitItemDialogCoGateCount": 0,
            "submitItemLevelScriptCoGateCount": 0,
            "nativeRuntimeBindingCount": 0,
            "activityStageHostCount": 0,
            "activityStageHostedQuestCount": 0,
            "trackingInfoCount": 0,
            "trackingObjectiveCount": 0,
            "missionPropertyCount": 0,
            "conditionTypes": [],
            "caseStudy": False,
            "file": f"missions/{mission_id}.json",
            "offlineRecoveryShell": True,
            "offlineRecoveryStoryCount": len(story_keys),
            "storyOrderSceneCount": int(metrics.get("sceneCount") or 0),
            "storyOrderStrongEdgeCount": int(
                metrics.get("strongEdgeCount") or 0
            ),
            "storyOrderCycleCount": int(metrics.get("sourceCycles") or 0),
        }
        index.setdefault("missions", []).append(summary)
        published.append(mission_id)
        existing.add(mission_id)
    index["missions"].sort(key=lambda row: natural_quest_key(row["id"]))
    index.setdefault("counts", {})["missions"] = len(index["missions"])
    index["counts"]["offlineRecoveryMissionShells"] = len(published)
    return published


def classify_definition_only_current_build_consumers(
    story_keys: Iterable[str],
    text_vo_id_table_path: Path | None,
) -> dict[str, Any]:
    """Classify definition-only Story files without creating ownership edges.

    ``TextVoIdTable`` maps exact Story line ids to voice/audio ids.  A non-empty
    mapping proves only that non-Story audio metadata exists; an explicit empty
    mapping is useful negative evidence for a likely legacy definition.  Neither
    class is a playback consumer or a mission/quest ownership source.
    """
    source_rows: dict[str, Any] = {}
    source_status = "missing"
    if text_vo_id_table_path is not None and text_vo_id_table_path.is_file():
        payload = read_json(text_vo_id_table_path)
        if isinstance(payload, dict):
            source_rows = payload
            source_status = "loaded"
        else:
            source_status = "invalid_non_object"

    class_keys: dict[str, list[str]] = defaultdict(list)
    records: list[dict[str, Any]] = []
    for story_key in sorted({str(value) for value in story_keys if value}, key=natural_quest_key):
        prefix = f"{story_key}_"
        line_rows = [
            {
                "lineId": str(line_id),
                "voiceId": str(voice_id or "").strip(),
            }
            for line_id, voice_id in source_rows.items()
            if str(line_id).startswith(prefix)
        ]
        line_rows.sort(key=lambda row: natural_quest_key(row["lineId"]))
        voice_ids = sorted({row["voiceId"] for row in line_rows if row["voiceId"]})
        if voice_ids:
            classification = "original_audio_metadata_without_playback_consumer"
            likely_legacy: bool | None = False
            finding = (
                "At least one exact TextVoIdTable line mapping has a non-empty audio id. "
                "This is audio metadata only and supplies neither a playback consumer nor "
                "mission/quest ownership."
            )
        elif line_rows:
            classification = "explicit_empty_audio_metadata_likely_legacy_definition"
            likely_legacy = True
            finding = (
                "Exact TextVoIdTable line rows exist but every audio id is empty, and the "
                "Story sidecar recovered no current-build playback consumer. This supports "
                "a likely legacy definition, not a mission binding."
            )
        else:
            classification = "no_audio_metadata_or_playback_consumer_recovered"
            likely_legacy = None
            finding = (
                "No exact TextVoIdTable line row or current-build playback consumer was "
                "recovered. Absence alone is not mission ownership evidence."
            )
        class_keys[classification].append(story_key)
        records.append({
            "key": story_key,
            "classification": classification,
            "finding": finding,
            "textVoRows": line_rows,
            "voiceIds": voice_ids,
            "likelyLegacy": likely_legacy,
            "currentBuildPlaybackConsumer": False,
            "missionOwnershipEvidence": False,
            "storyBinding": False,
        })

    ordered_classes = {
        classification: sorted(keys, key=natural_quest_key)
        for classification, keys in sorted(class_keys.items())
    }
    return {
        "policy": (
            "Negative current-build consumer classification only. TextVoIdTable is "
            "non-Story audio metadata and never promotes a Story-to-mission edge."
        ),
        "source": {
            "textVoIdTable": (
                repo_path(text_vo_id_table_path)
                if text_vo_id_table_path is not None
                else None
            ),
            "status": source_status,
            "tableRows": len(source_rows),
        },
        "counts": {
            classification: len(keys)
            for classification, keys in ordered_classes.items()
        },
        "keysByClassification": ordered_classes,
        "records": records,
    }


def load_activity_quest_level_hosts(
    table_paths: Iterable[Path | None],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Load typed activity-stage ``questId -> levelId`` host rows.

    These rows enrich a quest's authored level context.  They deliberately do
    not create a Story edge: neither table contains a Story or LevelScript
    identity.
    """
    rows_by_quest: dict[str, list[dict[str, Any]]] = defaultdict(list)
    sources: list[str] = []
    seen: set[tuple[str, str, str, str]] = set()
    for path in table_paths:
        if path is None or not path.is_file():
            continue
        source = repo_path(path)
        sources.append(source)
        payload = read_json(path)
        if not isinstance(payload, dict):
            continue
        table_name = path.stem
        for stage_id, raw in sorted(payload.items()):
            if not isinstance(raw, dict):
                continue
            quest_id = str(raw.get("questId") or "").strip()
            level_id = str(raw.get("levelId") or "").strip()
            if not quest_id or not level_id:
                continue
            signature = (table_name, str(stage_id), quest_id, level_id)
            if signature in seen:
                continue
            seen.add(signature)
            rows_by_quest[quest_id].append({
                "relation": "activity_stage_quest_level_host",
                "table": table_name,
                "stageId": str(stage_id),
                "questId": quest_id,
                "levelId": level_id,
                "storyBinding": False,
                "source": source,
                "confidence": "typed_original_data_and_native_accessors",
            })
    for rows in rows_by_quest.values():
        rows.sort(key=lambda row: (row["table"], row["stageId"], row["levelId"]))
    return dict(rows_by_quest), {
        "sources": sorted(set(sources)),
        "rowCount": sum(len(rows) for rows in rows_by_quest.values()),
        "questCount": len(rows_by_quest),
        "distinctLevelCount": len({
            row["levelId"]
            for rows in rows_by_quest.values()
            for row in rows
        }),
        "storyBindingsAdded": 0,
        "evidence": RUNTIME_CONTRACT["activityQuestLevelHosts"],
    }


def load_subgame_mission_bindings(
    table_path: Path | None,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Load exact mission/script identities co-authored in typed SubGame rows.

    The relation is deliberately mission-shell context. Authored task lanes are
    retained so later generic recovery can require an exact script/task carrier.
    It never attaches a quest or Story file merely because the script is bound.
    """
    if table_path is None or not table_path.is_file():
        return {}, {
            "available": False,
            "source": repo_path(table_path) if table_path is not None else "",
            "rowCount": 0,
            "rowsWithBindScriptId": 0,
            "rowsWithDungeonMissionId": 0,
            "missionBindingCount": 0,
            "boundMissionCount": 0,
            "distinctScriptCount": 0,
            "storyBindingsAdded": 0,
        }
    payload = read_json(table_path)
    data_table = payload.get("dataTable") if isinstance(payload, dict) else None
    if not isinstance(data_table, dict):
        raise ValueError(f"SubGameInstanceData table has no dataTable map: {table_path}")
    bindings: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, str, int]] = set()
    rows_with_bind_script_id = 0
    rows_with_dungeon_mission_id = 0
    for subgame_id, raw in sorted(data_table.items()):
        if not isinstance(raw, dict):
            continue
        mission_id = raw.get("dungeonMissionId")
        script_id = raw.get("bindScriptId")
        if isinstance(script_id, int) and script_id > 0:
            rows_with_bind_script_id += 1
        if isinstance(mission_id, str) and mission_id:
            rows_with_dungeon_mission_id += 1
        if not isinstance(mission_id, str) or not mission_id or not isinstance(script_id, int) or script_id <= 0:
            continue
        identity = (mission_id, str(subgame_id), script_id)
        if identity in seen:
            continue
        seen.add(identity)
        runtime_type = str(raw.get("$type") or "")
        if "," in runtime_type:
            runtime_type = runtime_type.split(",", 1)[0]
        task_lanes: dict[str, list[dict[str, Any]]] = {}
        for source_field, lane in (
            ("mainTasks", "main"),
            ("extraTasks", "extra"),
            ("failTasks", "fail"),
        ):
            values = raw.get(source_field)
            if not isinstance(values, list):
                raise ValueError(
                    "SubGame task lane is not an array: "
                    f"source={table_path} subGameId={subgame_id} "
                    f"lane={source_field} actual={type(values).__name__}"
                )
            task_lanes[lane] = [
                {
                    key: value
                    for key, value in task.items()
                    if key in {"taskId", "levelScriptId", "failInfo"}
                }
                for task in values
                if isinstance(task, dict) and str(task.get("taskId") or "")
            ]
        bindings[mission_id].append({
            "subGameId": str(subgame_id),
            "bindScriptId": str(script_id),
            "dungeonMissionId": mission_id,
            "subDataParentId": str(raw.get("subDataParentId") or ""),
            "runtimeType": runtime_type,
            "modeId": str(raw.get("modeId") or ""),
            "modeType": raw.get("modeType"),
            "gameMechanicsType": raw.get("gameMechanicsType"),
            "relation": "subgame_bind_script_runtime",
            "confidence": "typed_original_data",
            "source": repo_path(table_path),
            "storyBinding": False,
            "taskLanes": task_lanes,
            "networkIdentity": {
                "authoredKeyField": "gameId",
                "authoredKeyValue": str(subgame_id),
                "startRequest": "CS_GAME_MECHANICS_REQ_START",
                "enterPush": "SC_GAME_MECHANICS_SYNC_ENTER_GAME_INST",
                "challengeStartPush": "SC_GAME_MECHANICS_SYNC_CHALLENGE_START",
                "challengeCompletePush": "SC_GAME_MECHANICS_SYNC_CHALLENGE_COMPLETE",
                "completionRewardPush": "SC_GAME_MECHANICS_SYNC_COMPLETION_REWARD",
                "stopRequest": "CS_GAME_MECHANICS_REQ_STOP",
                "leavePush": "SC_GAME_MECHANICS_SYNC_LEAVE_GAME_INST",
            },
        })
    for rows in bindings.values():
        rows.sort(key=lambda row: (row["subGameId"], row["bindScriptId"]))
    return dict(bindings), {
        "available": True,
        "source": repo_path(table_path),
        "rowCount": len(data_table),
        "rowsWithBindScriptId": rows_with_bind_script_id,
        "rowsWithDungeonMissionId": rows_with_dungeon_mission_id,
        "missionBindingCount": len(seen),
        "boundMissionCount": len(bindings),
        "distinctScriptCount": len({script_id for _, _, script_id in seen}),
        "storyBindingsAdded": 0,
        "packetIdentity": {
            "authoredRowKey": "gameId",
            "runtimeOnlyFields": ["gameInstId", "gameUniqueId", "isReenter"],
            "missingOwnershipFields": ["missionId", "questId", "sceneNumId", "bindScriptId"],
        },
        "bindScriptNativeEvidence": {
            "serializedFieldOffset": "0x50",
            "startConsumer": "InteractiveLogicChallengeStartPoint._OnInteract",
            "startConsumerToken": "0x0600231a",
            "startConsumerAddress": "0x18713e548",
            "startEffect": (
                "SubGame table lookup -> bindScriptId read -> "
                "LevelScriptManager.TryGetLevelScript -> LevelScriptRuntime.ManualStart"
            ),
            "stopConsumer": "WorldChallengeGame.SendQuit",
            "stopConsumerAddress": "0x186f60cc8",
            "stopEffect": (
                "LevelScriptManager.TryGetLevelScript -> "
                "LevelScriptRuntime.ManualEnd -> send stop request"
            ),
            "auditedOnStartConsumerFound": True,
        },
        "evidenceBoundary": (
            "Exact typed mission-to-SubGame-to-LevelScript shell and authored task "
            "lanes only; the binary proves the generic interaction ManualStart "
            "carrier but not that it fired. No quest or Story attachment is inferred "
            "from co-membership. OCR, manual, and gameplay cross-references cannot "
            "promote this relation."
        ),
    }


def _connection_rows(flow: dict[str, Any]) -> Iterable[dict[str, Any]]:
    quests = flow.get("quests") or []
    if isinstance(quests, dict):
        quests = quests.values()
    for quest in quests:
        if not isinstance(quest, dict):
            continue
        for row in quest.get("storyConnections") or []:
            if isinstance(row, dict):
                yield row
    for row in flow.get("missionStoryConnections") or []:
        if isinstance(row, dict):
            yield row


def _scoped_connection_rows(
    flow: dict[str, Any],
) -> Iterable[tuple[dict[str, Any], str, str]]:
    quests = flow.get("quests") or []
    if isinstance(quests, dict):
        quests = quests.values()
    for quest in quests:
        if not isinstance(quest, dict):
            continue
        quest_id = str(quest.get("id") or quest.get("questId") or "")
        for row in quest.get("storyConnections") or []:
            if isinstance(row, dict):
                yield row, quest_id, "quest"
    for row in flow.get("missionStoryConnections") or []:
        if isinstance(row, dict):
            yield row, "", "mission"


def _unique_route_strings(*values: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        items = value if isinstance(value, (list, tuple, set)) else [value]
        for item in items:
            text = str(item or "").strip()
            if text and text not in seen:
                seen.add(text)
                result.append(text)
    return result


NATIVE_OCCURRENCE_FIELDS = (
    "occurrences",
    "levelScriptOccurrences",
    "nativeOccurrences",
    "nativeBlackActionOccurrences",
    "parentDialogNativeOccurrences",
    "preloadOccurrences",
    "worldEntityLevelScriptEvidence",
)


def _native_occurrence_rows(row: dict[str, Any]) -> list[dict[str, Any]]:
    occurrences: list[dict[str, Any]] = []
    seen: set[str] = set()
    for field in NATIVE_OCCURRENCE_FIELDS:
        for occurrence in row.get(field) or []:
            if not isinstance(occurrence, dict):
                continue
            if (
                field == "worldEntityLevelScriptEvidence"
                and isinstance(occurrence.get("listener"), dict)
            ):
                occurrence = {
                    **occurrence,
                    "actionName": (
                        occurrence.get("actionName")
                        or occurrence.get("nativeAction")
                    ),
                    "nativeEventOwners": [occurrence["listener"]],
                }
            signature = json.dumps(
                occurrence,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            if signature not in seen:
                seen.add(signature)
                occurrences.append(occurrence)
    return occurrences


def _compact_native_trigger_paths(row: dict[str, Any]) -> list[dict[str, Any]]:
    occurrences = _native_occurrence_rows(row)
    if not occurrences and isinstance(row.get("nativeEventOwners"), list):
        occurrences = [{
            "levelId": next(iter(row.get("levelIds") or []), ""),
            "scriptId": next(iter(row.get("scriptIds") or []), ""),
            "sourceFile": next(iter(row.get("sourceFiles") or []), ""),
            "nativeEventOwners": row.get("nativeEventOwners") or [],
        }]

    paths: list[dict[str, Any]] = []
    seen: set[str] = set()
    for occurrence in occurrences:
        level_id = str(occurrence.get("levelId") or "")
        script_id = str(occurrence.get("scriptId") or "")
        source_file = str(occurrence.get("sourceFile") or "")
        for owner in occurrence.get("nativeEventOwners") or []:
            if not isinstance(owner, dict):
                continue
            event_name = str(owner.get("headerName") or "").strip()
            event_detail = (
                owner.get("eventDetail")
                if isinstance(owner.get("eventDetail"), dict)
                else {}
            )
            header_local_id = (
                int(owner["headerLocalId"])
                if isinstance(owner.get("headerLocalId"), int)
                else None
            )
            selector = exact_native_runtime_selector(
                event_name,
                event_detail,
                level_id=level_id,
                script_id=script_id,
                header_local_id=header_local_id,
            )
            steps = []
            for step in owner.get("path") or []:
                if not isinstance(step, dict):
                    continue
                compact_step = {
                    key: step[key]
                    for key in (
                        "edge",
                        "localId",
                        "actionName",
                        "recordClass",
                        "unionTag",
                    )
                    if step.get(key) is not None
                }
                if compact_step:
                    steps.append(compact_step)
            path = {
                "eventName": event_name,
                "eventSummary": str(event_detail.get("summary") or ""),
                "transport": str(event_detail.get("transport") or ""),
                "serverExchange": event_detail.get("serverExchange"),
                "levelId": level_id,
                "scriptId": script_id,
                "sourceFile": source_file,
                "headerLocalId": header_local_id,
                "selector": selector or None,
                "steps": steps,
            }
            signature = json.dumps(
                path,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            if signature not in seen:
                seen.add(signature)
                paths.append(path)
    return paths


def build_story_trigger_route(
    row: dict[str, Any],
    *,
    mission_id: str,
    quest_id: str = "",
    scope: str = "mission",
    owner_status: str = "connected",
) -> dict[str, Any] | None:
    """Normalize one Story relation into a compact, evidence-typed route."""
    key = str(row.get("key") or "")
    if not key:
        return None
    relation = str(row.get("relation") or "unknown")
    direction = str(row.get("direction") or "context")
    owner_unresolved = owner_status in {
        "unresolved",
        "unresolved_playback",
    }
    if relation == "original_text_definition_without_consumer":
        causality = "definition_only"
    elif owner_status == "unresolved_playback":
        causality = "playback_owner_unresolved"
    elif owner_unresolved:
        causality = "context_owner_unresolved"
    elif direction == "quest_to_story":
        causality = "playback"
    elif direction == "story_to_quest":
        causality = "condition"
    elif row.get("dependencyOnly") is True or row.get("ownership") is False:
        causality = "dependency"
    else:
        causality = "context"

    native_paths = _compact_native_trigger_paths(row)
    native_occurrences = _native_occurrence_rows(row)
    event_names = _unique_route_strings(
        row.get("event"),
        row.get("nativeEventNames"),
        [path.get("eventName") for path in native_paths],
    )
    event_summaries = _unique_route_strings(
        row.get("nativeEventSummaries"),
        [path.get("eventSummary") for path in native_paths],
    )
    action_names = _unique_route_strings(
        row.get("actionType"),
        row.get("actionName"),
        row.get("nativeAction"),
        row.get("nativeActions"),
        [occurrence.get("actionName") for occurrence in native_occurrences],
        [
            step.get("actionName")
            for path in native_paths
            for step in path.get("steps") or []
            if str(step.get("recordClass") or "").startswith("play_")
        ],
    )
    script_ids = _unique_route_strings(
        row.get("scriptId"),
        row.get("scriptIds"),
        [path.get("scriptId") for path in native_paths],
    )
    source_files = _unique_route_strings(
        row.get("sourceFile"),
        row.get("sourceFiles"),
        row.get("assetPaths"),
        row.get("trackPaths"),
        row.get("rootPaths"),
        [path.get("sourceFile") for path in native_paths],
    )
    timeline_dialog_containments = [
        containment
        for containment in row.get("timelineDialogContainments") or []
        if isinstance(containment, dict)
    ]
    parent_story_key = str(row.get("parentStoryKey") or "")
    timeline_ids = _unique_route_strings(
        row.get("timelines"),
        [
            containment.get("timeline")
            for containment in timeline_dialog_containments
        ],
    )
    embedded_line_ids = _unique_route_strings(
        row.get("textIds"),
        [
            line_id
            for containment in timeline_dialog_containments
            for line_id in containment.get("lineIds") or []
        ],
    )
    embedded_option_ids = _unique_route_strings(
        row.get("optionIds"),
        [
            option_id
            for containment in timeline_dialog_containments
            for option_id in containment.get("optionIds") or []
        ],
    )
    before_parent_line_ids = _unique_route_strings([
        containment.get("beforeParentLineId")
        for containment in timeline_dialog_containments
    ])
    after_parent_line_ids = _unique_route_strings([
        containment.get("afterParentLineId")
        for containment in timeline_dialog_containments
    ])

    owner_step = {
        "kind": "ownership_gap" if owner_unresolved else scope,
        "id": quest_id if scope == "quest" and quest_id else mission_id,
        "phase": str(row.get("phase") or ""),
    }
    story_step = {
        "kind": (
            "dialog_definition"
            if row.get("dialogDefinitionOnly") is True
            else "story"
        ),
        "id": key,
    }
    middle_steps: list[dict[str, Any]] = []
    if row.get("serverMessage"):
        middle_steps.append({
            "kind": "server_message",
            "id": str(row["serverMessage"]),
            "fields": _unique_route_strings(row.get("serverFields")),
        })
    if event_names:
        middle_steps.append({
            "kind": "native_event",
            "ids": event_names,
            "summaries": event_summaries,
        })
    if script_ids:
        middle_steps.append({"kind": "levelscript", "ids": script_ids})
    if relation == "leveldata_interactive_narrative_config":
        leveldata_assets = _unique_route_strings(row.get("levelDataAssets"))
        if leveldata_assets:
            middle_steps.append({
                "kind": "leveldata",
                "ids": leveldata_assets,
            })
        progress_conditions = [
            dict(condition)
            for condition in row.get("progressLockConditions") or []
            if isinstance(condition, dict)
        ]
        if (
            row.get("progressLockConditionStatus") == "decoded"
            and progress_conditions
        ):
            condition_summaries: list[str] = []

            def summarize_condition(node: object, depth: int = 0) -> None:
                if not isinstance(node, dict):
                    return
                if node.get("conditionType") == "CombinedConditionRuntime":
                    condition_summaries.append(
                        (
                            f"{'nested ' if depth else ''}combined operator "
                            f"{node.get('conditionOperator')} runtime flag "
                            f"{str(node.get('serializedRuntimeFlag')).lower()}"
                        )
                    )
                    for child in node.get("conditions") or []:
                        summarize_condition(child, depth + 1)
                    return
                condition_summaries.append(
                    (
                        f"{node.get('ownerKind')} "
                        f"{node.get('ownerId')} state "
                        f"{node.get('compareTarget')} "
                        f"(compare {node.get('compareOperator')})"
                    )
                )

            tree = row.get("progressLockConditionTree")
            if isinstance(tree, dict):
                summarize_condition(tree)
            else:
                for condition in progress_conditions:
                    summarize_condition(condition)
            middle_steps.append({
                "kind": "availability_condition",
                "id": str(row.get("progressLockConditionType") or ""),
                "summaries": condition_summaries,
            })
    if (
        relation in {
            "levelscript_interactive_narrative_config",
            "leveldata_interactive_narrative_config",
        }
        and (
            row.get("localInteractiveId") is not None
            or row.get("entityLogicId") is not None
        )
    ):
        interactive_summaries = _unique_route_strings(
            row.get("rawTypeId"),
            row.get("entityTemplateIds"),
        )
        middle_steps.append({
            "kind": "narrative_interactive",
            "id": str(
                row.get("localInteractiveId")
                if row.get("localInteractiveId") is not None
                else row.get("entityLogicId")
            ),
            "summaries": interactive_summaries,
        })
    if action_names:
        middle_steps.append({"kind": "native_action", "ids": action_names})
    if relation == "timeline_dialog_contains_foreign_dialog":
        if parent_story_key:
            middle_steps.append({
                "kind": "parent_story",
                "id": parent_story_key,
            })
        if timeline_ids:
            middle_steps.append({
                "kind": "dialog_timeline",
                "ids": timeline_ids,
                "beforeParentLineIds": before_parent_line_ids,
                "afterParentLineIds": after_parent_line_ids,
            })
    if direction == "story_to_quest":
        steps = [story_step, *middle_steps, owner_step]
    else:
        steps = [owner_step, *middle_steps, story_step]

    return {
        "storyKey": key,
        "missionId": mission_id,
        "questId": quest_id or None,
        "scope": scope,
        "ownerStatus": "unresolved" if owner_unresolved else owner_status,
        "relation": relation,
        "direction": direction,
        "phase": str(row.get("phase") or ""),
        "causality": causality,
        "confidence": str(row.get("confidence") or ""),
        "evidenceTier": str(row.get("evidenceTier") or ""),
        "nativeMappingId": str(row.get("nativeMappingId") or ""),
        "certainty": str(row.get("certainty") or ""),
        "eventNames": event_names,
        "eventSummaries": event_summaries,
        "actionNames": action_names,
        "scriptIds": script_ids,
        "levelId": str(row.get("levelId") or ""),
        "sourcePathIds": _unique_route_strings(row.get("sourcePathIds")),
        "parentScopeRelations": _unique_route_strings(
            row.get("parentScopeRelations")
        ),
        "carrierKinds": _unique_route_strings(row.get("carrierKinds")),
        "occurrenceCount": row.get("occurrenceCount"),
        "runtimeReplacementPossible": row.get("runtimeReplacementPossible"),
        "headerLocalId": row.get("headerLocalId"),
        "gateActionLocalId": row.get("gateActionLocalId"),
        "conditionType": str(row.get("conditionType") or ""),
        "conditionComparer": str(row.get("conditionComparer") or ""),
        "conditionQuestState": row.get("conditionQuestState"),
        "actionLocalId": row.get("actionLocalId"),
        "actionCode": str(row.get("actionCode") or ""),
        "actionKind": str(row.get("actionKind") or ""),
        "levelDataAssets":
            _unique_route_strings(row.get("levelDataAssets")),
        "localInteractiveId": row.get("localInteractiveId"),
        "entityLogicId": row.get("entityLogicId"),
        "interactiveRecordIndex": row.get("interactiveRecordIndex"),
        "interactiveRecordBoundarySource":
            str(row.get("interactiveRecordBoundarySource") or ""),
        "narrativeConsumerKind":
            str(row.get("narrativeConsumerKind") or ""),
        "dialogDefinitionOnly":
            row.get("dialogDefinitionOnly") is True,
        "dialogDefinitionBinding":
            row.get("dialogDefinitionBinding") is True,
        "dialogDefinitionConsumerMission":
            str(row.get("dialogDefinitionConsumerMission") or ""),
        "dialogDefinitionConsumerQuestId":
            str(row.get("dialogDefinitionConsumerQuestId") or ""),
        "dialogIdEntryOffset": row.get("dialogIdEntryOffset"),
        "interactiveHornTemplateSha256":
            str(row.get("interactiveHornTemplateSha256") or ""),
        "interactiveHornNativeMappingId":
            str(row.get("interactiveHornNativeMappingId") or ""),
        "levelDataMember21Offset": row.get("levelDataMember21Offset"),
        "levelIdNum": row.get("levelIdNum"),
        "levelScriptBriefDictionaryCountOffset":
            row.get("levelScriptBriefDictionaryCountOffset"),
        "levelScriptBriefDictionaryCount":
            row.get("levelScriptBriefDictionaryCount"),
        "levelScriptDataPathDictionaryCountOffset":
            row.get("levelScriptDataPathDictionaryCountOffset"),
        "levelScriptDataPathDictionaryCount":
            row.get("levelScriptDataPathDictionaryCount"),
        "levelDataSafeZoneOffset": row.get("levelDataSafeZoneOffset"),
        "levelDataSceneId": str(row.get("levelDataSceneId") or ""),
        "levelDataSpecificDataOffset":
            row.get("levelDataSpecificDataOffset"),
        "levelDataEmptySuffixEndOffset":
            row.get("levelDataEmptySuffixEndOffset"),
        "levelDataFinalBoundaryValidation":
            str(row.get("levelDataFinalBoundaryValidation") or ""),
        "progressLockConditionStatus":
            str(row.get("progressLockConditionStatus") or ""),
        "progressLockConditionUnionTag":
            row.get("progressLockConditionUnionTag"),
        "progressLockConditionSerializedMemberCount":
            row.get("progressLockConditionSerializedMemberCount"),
        "progressLockConditionType":
            str(row.get("progressLockConditionType") or ""),
        "progressLockConditionOperator":
            row.get("progressLockConditionOperator"),
        "progressLockSerializedRuntimeFlag":
            row.get("progressLockSerializedRuntimeFlag"),
        "progressLockConditionTree":
            row.get("progressLockConditionTree"),
        "progressLockConditions": [
            dict(condition)
            for condition in row.get("progressLockConditions") or []
            if isinstance(condition, dict)
        ],
        "rawTypeId": str(row.get("rawTypeId") or ""),
        "entityDetailIds": _unique_route_strings(row.get("entityDetailIds")),
        "entityTemplateIds": _unique_route_strings(row.get("entityTemplateIds")),
        "parentStoryKey": parent_story_key,
        "timelineIds": timeline_ids,
        "embeddedLineIds": embedded_line_ids,
        "embeddedOptionIds": embedded_option_ids,
        "beforeParentLineIds": before_parent_line_ids,
        "afterParentLineIds": after_parent_line_ids,
        "placementBoundary": str(row.get("placementBoundary") or ""),
        "graphEffect": str(row.get("graphEffect") or ""),
        "controlPathCount": int(row.get("nativeControlPathCount") or len(native_paths)),
        "nativePaths": native_paths,
        "sourceFiles": source_files,
        "serverMessage": str(row.get("serverMessage") or ""),
        "serverFields": _unique_route_strings(row.get("serverFields")),
        "upstreamServerStateSources": _unique_route_strings(
            row.get("upstreamServerStateSources")
        ),
        "serverExchange": row.get("serverExchange"),
        "clientRequest": row.get("clientRequest"),
        "expectedClientReply": row.get("expectedClientReply"),
        "npcProxyId": str(row.get("npcProxyId") or ""),
        "candidateQuestIds": _unique_route_strings(
            row.get("candidateQuestIds")
        ),
        "activeRowIndex": row.get("activeRowIndex"),
        "configuredDialogIds": _unique_route_strings(
            row.get("configuredDialogIds")
        ),
        "selectionOrderStatus": str(
            row.get("selectionOrderStatus") or ""
        ),
        "questTriggerStatus": str(row.get("questTriggerStatus") or ""),
        "steps": steps,
    }


def story_trigger_route_sort_key(route: dict[str, Any]) -> tuple:
    """Keep direct playback/condition routes ahead of context diagnostics."""
    causality = str(route.get("causality") or "")
    causality_rank = {
        "playback": 0,
        "condition": 1,
        "dependency": 2,
        "context": 3,
        "playback_owner_unresolved": 4,
        "context_owner_unresolved": 5,
        "definition_only": 6,
    }.get(causality, 7)
    return (
        causality_rank,
        natural_quest_key(str(route.get("missionId") or "")),
        natural_quest_key(str(route.get("questId") or "")),
        str(route.get("relation") or ""),
    )


def build_composed_root_playback_alias_route(
    alias: dict[str, Any],
    root_route: dict[str, Any],
) -> dict[str, Any] | None:
    """Compose an owned root playback route with one exact playback alias.

    The root route must already terminate at the alias's root Story key and
    contain a native playback action. This excludes condition/dependency-only
    attachments and keeps a standalone alias non-owning.
    """
    root_key = str(alias.get("rootStoryKey") or "")
    playable_key = str(alias.get("playableAssetStoryKey") or "")
    steps = root_route.get("steps")
    if (
        not root_key
        or not playable_key
        or root_key == playable_key
        or root_route.get("ownerStatus") != "connected"
        or not root_route.get("missionId")
        or not isinstance(steps, list)
        or not steps
        or not any(
            isinstance(step, dict) and step.get("kind") == "native_action"
            for step in steps
        )
        or not isinstance(steps[-1], dict)
        or steps[-1].get("kind") != "story"
        or steps[-1].get("id") != root_key
    ):
        return None

    composed_steps = [
        dict(step)
        for step in steps
        if isinstance(step, dict)
    ]
    composed_steps[-1]["kind"] = "story_root"
    composed_steps.extend([
        {
            "kind": "native_action",
            "id": "CutsceneRoot._director -> TimelineHandle.Play",
        },
        {
            "kind": "story",
            "id": playable_key,
        },
    ])
    return {
        **root_route,
        "storyKey": playable_key,
        "relation": "cutscene_root_playback_alias_composed",
        "causality": "playback_alias_owner_connected",
        "confidence": (
            "exact_connected_root_playback_plus_serialized_director_alias"
        ),
        "evidenceTier": "native_serialized_composed_exact",
        "rootStoryKey": root_key,
        "rootBaseRelation": str(root_route.get("relation") or ""),
        "rootBaseCausality": str(root_route.get("causality") or ""),
        "aliasRelation": str(alias.get("relation") or ""),
        "nativeMappingId": str(alias.get("nativeMappingId") or ""),
        "auditReport": str(alias.get("evidenceReport") or ""),
        "sourceFiles": _unique_route_strings(
            root_route.get("sourceFiles"),
            (alias.get("directorObject") or {}).get("source"),
            alias.get("evidenceReport"),
        ),
        "questTriggerStatus": (
            "connected_root_native_playback_composed_with_exact_alias"
        ),
        "note": (
            "An independently connected native playback route terminates at "
            "this exact CutsceneRoot Story key. Its resolved _director PPtr "
            "and the current TimelineHandle.Play path execute the target "
            "TimelineAsset. This composes owner context, not relative Story "
            "order."
        ),
        "steps": composed_steps,
    }


def load_missionless_subgames_by_script(
    table_path: Path | None,
) -> dict[str, list[dict[str, Any]]]:
    """Index authored SubGame rows with a script but no mission owner."""
    if table_path is None or not table_path.is_file():
        return {}
    payload = read_json(table_path)
    data_table = payload.get("dataTable") if isinstance(payload, dict) else None
    if not isinstance(data_table, dict):
        return {}
    rows_by_script: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for subgame_id, raw in sorted(data_table.items()):
        if not isinstance(raw, dict):
            continue
        script_id = raw.get("bindScriptId")
        mission_id = raw.get("dungeonMissionId")
        if not isinstance(script_id, int) or script_id <= 0:
            continue
        if isinstance(mission_id, str) and mission_id:
            continue
        runtime_type = str(raw.get("$type") or "")
        if "," in runtime_type:
            runtime_type = runtime_type.split(",", 1)[0]
        task_ids = sorted({
            str(task.get("taskId") or "")
            for field in ("mainTasks", "extraTasks", "failTasks")
            for task in raw.get(field) or []
            if isinstance(task, dict) and task.get("taskId")
        })
        rows_by_script[str(script_id)].append({
            "subGameId": str(subgame_id),
            "bindScriptId": str(script_id),
            "runtimeType": runtime_type,
            "subDataParentId": str(raw.get("subDataParentId") or ""),
            "modeId": str(raw.get("modeId") or ""),
            "mainTaskIds": task_ids,
            "source": repo_path(table_path),
        })
    return dict(rows_by_script)


def load_subgame_cross_references(
    subgame_ids: set[str],
    activity_stage_table_path: Path | None,
    game_mechanic_condition_table_path: Path | None,
    dungeon_table_path: Path | None,
) -> dict[str, dict[str, Any]]:
    """Load exact non-owning associations and scene hosts for SubGame nodes."""
    cross_refs: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"associations": [], "sceneHosts": []}
    )
    if activity_stage_table_path is not None and activity_stage_table_path.is_file():
        payload = read_json(activity_stage_table_path)
        if isinstance(payload, dict):
            for activity in payload.values():
                if not isinstance(activity, dict):
                    continue
                for stage in (activity.get("stageList") or {}).values():
                    if not isinstance(stage, dict):
                        continue
                    subgame_id = str(stage.get("rankRelatedId") or "")
                    mission_id = str(stage.get("missionId") or "")
                    if subgame_id not in subgame_ids or not mission_id:
                        continue
                    cross_refs[subgame_id]["associations"].append({
                        "relation": "activity_stage_mission_association",
                        "sourceId": str(stage.get("stageId") or ""),
                        "targetType": "mission",
                        "targetId": mission_id,
                        "ownership": False,
                        "finding": (
                            "The stage row co-identifies missionId and rankRelatedId; "
                            "native runtime keeps stage mission state separate from "
                            "rank-related GameMechanics state."
                        ),
                        "source": repo_path(activity_stage_table_path),
                        "confidence": "typed_original_data_non_owning",
                    })
    if (
        game_mechanic_condition_table_path is not None
        and game_mechanic_condition_table_path.is_file()
    ):
        payload = read_json(game_mechanic_condition_table_path)
        if isinstance(payload, dict):
            for condition in payload.values():
                if not isinstance(condition, dict):
                    continue
                subgame_id = str(condition.get("gameMechanicsId") or "")
                if subgame_id not in subgame_ids:
                    continue
                params = [
                    str(value)
                    for parameter in condition.get("parameter") or []
                    if isinstance(parameter, dict)
                    for value in parameter.get("valueStringList") or []
                    if value not in (None, "")
                ]
                condition_type = condition.get("conditionType")
                association: dict[str, Any] | None = None
                if condition_type == 18 and params:
                    association = {
                        "relation": "subgame_unlock_quest_prerequisite",
                        "targetType": "quest",
                        "targetId": params[0],
                        "conditionType": 18,
                        "conditionTypeName": "QuestStateEqual",
                        "finding": "The quest state gates SubGame availability; it does not own runtime playback.",
                    }
                elif condition_type == 19 and params:
                    association = {
                        "relation": "subgame_unlock_mission_prerequisite",
                        "targetType": "mission",
                        "targetId": params[0],
                        "conditionType": 19,
                        "conditionTypeName": "MissionStateEqual",
                        "finding": (
                            "The mission state gates SubGame availability; it "
                            "does not own or trigger runtime playback."
                        ),
                    }
                elif condition_type == 5031 and params:
                    association = {
                        "relation": "subgame_unlock_previous_game_mechanic",
                        "targetType": "subgame",
                        "targetId": params[0],
                        "conditionType": 5031,
                        "conditionTypeName": "CheckPassGameMechanicsId",
                        "finding": "The prior challenge gates this SubGame; it supplies no mission owner.",
                    }
                if association is not None:
                    association.update({
                        "sourceId": str(condition.get("conditionId") or ""),
                        "ownership": False,
                        "source": repo_path(game_mechanic_condition_table_path),
                        "confidence": "typed_original_data_and_native_enum_non_owning",
                    })
                    cross_refs[subgame_id]["associations"].append(association)
    if dungeon_table_path is not None and dungeon_table_path.is_file():
        payload = read_json(dungeon_table_path)
        if isinstance(payload, dict):
            for dungeon in payload.values():
                if not isinstance(dungeon, dict):
                    continue
                subgame_id = str(dungeon.get("dungeonId") or "")
                if subgame_id not in subgame_ids:
                    continue
                cross_refs[subgame_id]["sceneHosts"].append({
                    "sceneId": str(dungeon.get("sceneId") or ""),
                    "levelId": str(dungeon.get("levelId") or ""),
                    "dungeonSeriesId": str(dungeon.get("dungeonSeriesId") or ""),
                    "source": repo_path(dungeon_table_path),
                    "confidence": "typed_original_data",
                })
    return dict(cross_refs)


def exact_native_runtime_selector(
    event_name: str,
    event_detail: dict[str, Any],
    *,
    level_id: str,
    script_id: str,
    header_local_id: int | None = None,
) -> dict[str, Any]:
    """Return only exact serialized fields that select a runtime receiver.

    A selector is useful for placing an otherwise missionless Story playback
    under an original-data runtime node.  It is deliberately not an ownership
    inference: level/script context remains part of every selector and no
    filename, OCR, spatial proximity, or display-name match is accepted.
    """
    if (
        not event_name
        or not isinstance(event_detail, dict)
        or event_detail.get("payloadSchemaStatus")
        != "exact_current_build_memorypack_fields"
    ):
        return {}

    selector: dict[str, Any] = {
        "levelId": level_id,
        "listenerScriptId": script_id,
    }
    if isinstance(header_local_id, int) and header_local_id >= 0:
        # localId is the authored receiver identity inside one serialized
        # LevelScript.  It remains exact even when an event intentionally has
        # no active subtype filter (for example SquadInFightChanged or a
        # filter-mode-disabled EntityCastSkill listener).
        selector["listenerHeaderLocalId"] = header_local_id
    target = event_detail.get("targetEntity")
    target_param = event_detail.get("targetEntityParam")
    if isinstance(target, dict):
        if target.get("useSlotId") and target.get("slotId"):
            selector["entitySlotId"] = int(target["slotId"])
        elif target.get("logicId"):
            selector["entityLogicId"] = str(target["logicId"])
    if isinstance(target_param, dict) and target_param.get("path"):
        selector["entityPropertyPath"] = str(target_param["path"])
        selector["entityPropertySource"] = target_param.get("paramSource")

    entity_list = event_detail.get("entityListFilter")
    if isinstance(entity_list, dict) and entity_list.get("path"):
        selector["entityListPropertyPath"] = str(entity_list["path"])
        selector["entityListPropertySource"] = entity_list.get("paramSource")
    elif isinstance(entity_list, list) and entity_list:
        normalized_entity_list = []
        for row in entity_list:
            if not isinstance(row, dict):
                continue
            normalized = {
                key: row[key]
                for key in ("logicId", "slotId", "useSlotId")
                if key in row
            }
            if normalized:
                normalized_entity_list.append(normalized)
        if normalized_entity_list:
            selector["entityListFilter"] = normalized_entity_list

    npc_entity = event_detail.get("npcEntityFilter")
    if isinstance(npc_entity, dict):
        if npc_entity.get("path"):
            selector["npcEntityPropertyPath"] = str(npc_entity["path"])
            selector["npcEntityPropertySource"] = npc_entity.get("paramSource")
        elif npc_entity.get("useSlotId") and npc_entity.get("slotId"):
            selector["npcEntitySlotId"] = int(npc_entity["slotId"])
        elif npc_entity.get("logicId"):
            selector["npcEntityLogicId"] = str(npc_entity["logicId"])

    entity_filter = event_detail.get("entityFilter")
    if isinstance(entity_filter, dict) and entity_filter:
        normalized = {
            key: entity_filter[key]
            for key in (
                "logicId",
                "slotId",
                "useSlotId",
                "idRef",
                "paramSource",
                "path",
            )
            if key in entity_filter and entity_filter[key] not in (None, "")
        }
        if normalized:
            selector["entityFilter"] = normalized
    elif isinstance(entity_filter, list) and entity_filter:
        normalized_filters = []
        for row in entity_filter:
            if not isinstance(row, dict):
                continue
            normalized = {
                key: row[key]
                for key in ("logicId", "slotId", "useSlotId")
                if key in row
            }
            if normalized:
                normalized_filters.append(normalized)
        if normalized_filters:
            selector["entityFilters"] = normalized_filters

    scalar_fields = (
        "spawnerFilterId",
        "groupKeyFilter",
        "waveKeyFilter",
        "triggerSlotIdFilter",
        "eventKey",
        "signalId",
        "guideIdFilter",
        "newStageFilter",
        "actionIdFilter",
        "dialogIdFilter",
        "npcProxyIdFilter",
        "checkpointFilter",
        "patrolIdFilter",
        "checkpointIndexFilter",
        "hpRatio",
        "changedDirectionName",
        "entityTemplateIdFilter",
        "blackboardKeyFilter",
        "propertyKeyFilter",
        "scriptedCharEventKeyFilter",
        "levelScriptVariableFilter",
        "isMonsterFilter",
        "filterByList",
    )
    for field in scalar_fields:
        value = event_detail.get(field)
        if value not in (None, "", [], {}):
            selector[field] = value

    if event_detail.get("specifiedTargetScriptId"):
        selector["targetScriptId"] = str(event_detail["specifiedTargetScriptId"])
    elif event_detail.get("scriptEventScope") == "owning-level-script":
        selector["targetScriptId"] = script_id

    identity_fields = set(selector) - {"levelId", "listenerScriptId"}
    return selector if identity_fields else {}


def is_exact_battle_signal_producer_route(
    producer: dict[str, Any],
    *,
    story_key: str,
    signal_id: str,
    level_id: str,
    script_id: str,
    header_local_id: int | None,
    source_file: str,
) -> bool:
    """Validate a sidecar's original-data producer-to-receiver route.

    The pipeline builder intentionally consumes the Story sidecar rather than
    rescanning SkillData/BuffData.  Rechecking every current-build identity
    here keeps a malformed or stale route from becoming visible evidence.
    """
    signal = producer.get("signalId") or {}
    numeric = producer.get("doubleValue") or {}
    return bool(
        producer.get("relation") == "ability_battle_signal_local_causality"
        and producer.get("storyKey") == story_key
        and producer.get("actionType")
        == "Core_SendBattleSignalToLevel_Data"
        and producer.get("actionUnionTag") == "0x0134"
        and producer.get("serializedMemberCount") == 6
        and producer.get("producerMappingId")
        == BATTLE_SIGNAL_PRODUCER_MAPPING_ID
        and producer.get("producerDomain") in {"SkillData", "BuffData"}
        and producer.get("producerAssetId")
        and producer.get("producerSourceFile")
        and producer.get("actionOffset")
        and (producer.get("prefix") or {}).get("isEnable") is True
        and signal.get("memberCount") == 3
        and signal.get("useBlackboardKey") is False
        and signal.get("value") == signal_id
        and numeric.get("memberCount") == 3
        and numeric.get("useBlackboardKey") is False
        and producer.get("receiverSignalId") == signal_id
        and producer.get("listenerLevelId") == level_id
        and producer.get("listenerScriptId") == script_id
        and producer.get("listenerHeaderLocalId") == header_local_id
        and producer.get("listenerSourceFile") == source_file
        and producer.get("receiverMappingId")
        == BATTLE_SIGNAL_RECEIVER_MAPPING_ID
        and producer.get("receiverPayloadMappingId")
        == BATTLE_SIGNAL_PAYLOAD_MAPPING_ID
        and producer.get("executionSide") == "client"
        and producer.get("transport") == "local-level-runtime-event"
        and producer.get("serverExchange") is False
        and producer.get("clientRequest") is False
        and producer.get("expectedServerReturn") is False
        and producer.get("missionOwnerStatus") == "unresolved"
        and producer.get("storyBinding") is False
    )


def load_dynamic_scene_identity_cross_references(
    audit_path: Path = DEFAULT_DYNAMIC_SCENE_MISSION_CONTROL_AUDIT,
    action_bridge_path: Path | None = None,
) -> dict[str, Any] | None:
    """Publish compact candidate-only DynamicScene/LevelScript cross-references.

    The source audit intentionally proves no runtime ownership bridge. Refuse
    publication if that boundary changes so a future positive result receives
    an explicit graph-admission review instead of silently inheriting this
    non-owning WebUI path.
    """
    audit = read_json(audit_path)
    if not isinstance(audit, dict) or audit.get("schemaVersion") != 1:
        return None
    boundary = audit.get("nativeIdentityBoundary")
    if (
        not isinstance(boundary, dict)
        or boundary.get("classification")
        != "exact_cross_reference_not_runtime_owner"
        or boundary.get("directBridgeFound") is not False
        or boundary.get("missionActivationBridgeFound") not in (None, False)
        or boundary.get("missionGraphAction") != "none"
    ):
        return None

    if action_bridge_path is None and audit_path == DEFAULT_DYNAMIC_SCENE_MISSION_CONTROL_AUDIT:
        action_bridge_path = DEFAULT_DYNAMIC_SCENE_LEVELSCRIPT_ACTION_BRIDGE_AUDIT
    bridge_report: dict[str, Any] = {}
    bridges_by_logic_id: dict[str, dict[str, Any]] = {}
    if action_bridge_path is not None and action_bridge_path.is_file():
        candidate_bridge_report = read_json(action_bridge_path)
        bridge_boundary = (
            candidate_bridge_report.get("boundary")
            if isinstance(candidate_bridge_report, dict)
            else None
        )
        trigger_volume_boundary = (
            bridge_boundary.get("levelScriptTriggerVolumeBoundary")
            if isinstance(bridge_boundary, dict)
            else None
        )
        identity_source = (
            (candidate_bridge_report.get("sources") or {}).get("identityAudit")
            if isinstance(candidate_bridge_report, dict)
            else None
        )
        current_audit_sha = hashlib.sha256(audit_path.read_bytes()).hexdigest()
        if (
            not isinstance(candidate_bridge_report, dict)
            or candidate_bridge_report.get("schemaVersion") != 1
            or not isinstance(bridge_boundary, dict)
            or bridge_boundary.get("classification")
            != "exact_local_context_without_mission_activation_edge"
            or bridge_boundary.get("missionActivationBridgeFound") is not False
            or bridge_boundary.get("missionGraphAction") != "none"
            or not isinstance(trigger_volume_boundary, dict)
            or trigger_volume_boundary.get("classification")
            != (
                "exact_local_trigger_geometry_without_dynamic_scene_"
                "or_mission_foreign_key"
            )
            or trigger_volume_boundary.get("foreignKeyBridgeFound") is not False
            or trigger_volume_boundary.get("schemaMappingId")
            != "current-global-metadata-levelscript-trigger-volume-data-fields"
            or trigger_volume_boundary.get("leaderDeclaredFieldCount") != 0
            or not isinstance(identity_source, dict)
            or identity_source.get("sha256") != current_audit_sha
        ):
            return None
        bridge_report = candidate_bridge_report
        for bridge_row in bridge_report.get("bridgeRows") or []:
            if (
                not isinstance(bridge_row, dict)
                or bridge_row.get("missionOwnerStatus") != "unresolved"
                or bridge_row.get("storyBinding") is not False
                or bridge_row.get("orderEvidence") is not False
                or bridge_row.get("missionGraphAction") != "none"
            ):
                continue
            logic_id = str(bridge_row.get("logicId") or "")
            exact_actions: list[dict[str, Any]] = []
            shared_story_keys: set[str] = set()
            for action in bridge_row.get("exactTargetActions") or []:
                target = action.get("targetParam") if isinstance(action, dict) else None
                visible = action.get("visibleParam") if isinstance(action, dict) else None
                if (
                    not isinstance(action, dict)
                    or action.get("actionName")
                    not in {
                        "ShowSceneDecorationNew",
                        "ShowSceneDecorationWithHandle",
                    }
                    or action.get("serializedMemberCount") != 10
                    or action.get("payloadFullyConsumed") is not True
                    or str(action.get("targetDynamicEntityLogicId") or "")
                    != logic_id
                    or not isinstance(target, dict)
                    or target.get("idRef") != -1
                    or target.get("paramSource") != 0
                    or target.get("path") is not None
                    or not isinstance(visible, dict)
                    or visible.get("idRef") != -1
                    or visible.get("paramSource") != 0
                    or visible.get("path") is not None
                ):
                    continue
                story_links: list[dict[str, Any]] = []
                shared_selector_slots: set[int] = set()
                for link in action.get("storyControlPathLinks") or []:
                    if not isinstance(link, dict):
                        continue
                    story_key = str(link.get("storyKey") or "")
                    shared_paths: list[dict[str, Any]] = []
                    for shared in link.get("sharedControlPaths") or []:
                        if (
                            not isinstance(shared, dict)
                            or shared.get("status")
                            != "exact_serialized_shared_control_path"
                        ):
                            continue
                        event_detail = shared.get("eventDetail") or {}
                        trigger_slot_id = event_detail.get(
                            "triggerSlotIdFilter"
                        )
                        if isinstance(trigger_slot_id, int):
                            shared_selector_slots.add(trigger_slot_id)
                        shared_paths.append(compact_dict({
                            "relation": str(shared.get("relation") or ""),
                            "headerName": str(shared.get("headerName") or ""),
                            "headerLocalId": shared.get("headerLocalId"),
                            "eventSummary": str(event_detail.get("summary") or ""),
                            "triggerSlotId": trigger_slot_id,
                            "storyPathLocalIds":
                                shared.get("storyPathLocalIds") or [],
                            "decorationPathLocalIds":
                                shared.get("decorationPathLocalIds") or [],
                        }))
                    if story_key and shared_paths:
                        shared_story_keys.add(story_key)
                        story_links.append({
                            "storyKey": story_key,
                            "storyRecordOffset": link.get("storyRecordOffset"),
                            "storyActionName": str(
                                link.get("storyActionName") or ""
                            ),
                            "sharedControlPaths": shared_paths,
                        })
                local_trigger_context: dict[str, Any] | None = None
                if shared_selector_slots:
                    candidate_context = action.get("localTriggerVolumeContext")
                    schema = (
                        candidate_context.get("schema")
                        if isinstance(candidate_context, dict)
                        else None
                    )
                    selector_slots = (
                        candidate_context.get("selectorSlotIds")
                        if isinstance(candidate_context, dict)
                        else None
                    )
                    matched_slots = (
                        candidate_context.get("matchedSlotIds")
                        if isinstance(candidate_context, dict)
                        else None
                    )
                    if (
                        not isinstance(candidate_context, dict)
                        or candidate_context.get("status")
                        != (
                            "exact_local_levelscript_trigger_volume_without_"
                            "foreign_identity"
                        )
                        or sorted(selector_slots or [])
                        != sorted(shared_selector_slots)
                        or sorted(matched_slots or [])
                        != sorted(shared_selector_slots)
                        or candidate_context.get("missingSlotIds") not in ([], None)
                        or candidate_context.get("scriptIdVerified") is not True
                        or candidate_context.get("triggerVolumesStatus")
                        != "present"
                        or candidate_context.get("triggerVolumesParseStatus")
                        != "decoded"
                        or candidate_context.get(
                            "dynamicSceneIdentityFieldPresent"
                        ) is not False
                        or candidate_context.get(
                            "missionOrQuestIdentityFieldPresent"
                        ) is not False
                        or candidate_context.get("foreignKeyBridgeFound")
                        is not False
                        or candidate_context.get("missionGraphAction") != "none"
                        or not isinstance(schema, dict)
                        or schema.get("baseDeclaredFieldCount") != 8
                        or schema.get("leaderDeclaredFieldCount") != 0
                        or schema.get("serializedMemberCount") != 8
                        or schema.get("mappingId")
                        != (
                            "current-global-metadata-levelscript-trigger-"
                            "volume-data-fields"
                        )
                    ):
                        continue
                    compact_volumes: list[dict[str, Any]] = []
                    for volume in candidate_context.get("triggerVolumes") or []:
                        if (
                            not isinstance(volume, dict)
                            or volume.get("slotId") not in shared_selector_slots
                            or volume.get("keySlotId") != volume.get("slotId")
                            or volume.get("triggerVolumeType") != "Leader"
                            or volume.get("memberCount") != 8
                        ):
                            continue
                        shape_list = volume.get("shapeList") or {}
                        if (
                            not isinstance(shape_list, dict)
                            or shape_list.get("parseStatus") != "decoded"
                        ):
                            continue
                        shapes = [
                            compact_dict({
                                "shapeType": shape.get("shapeType"),
                                "position": shape.get("position"),
                                "radius": shape.get("radius"),
                                "rotation": shape.get("rotation"),
                                "size": shape.get("size"),
                            })
                            for shape in shape_list.get("shapes") or []
                            if isinstance(shape, dict)
                        ]
                        compact_volumes.append(compact_dict({
                            "slotId": volume.get("slotId"),
                            "triggerVolumeType":
                                volume.get("triggerVolumeType"),
                            "triggerCountLimit":
                                volume.get("triggerCountLimit"),
                            "enterCheckOnGround":
                                volume.get("enterCheckOnGround"),
                            "isImportant": volume.get("isImportant"),
                            "triggerOnPole": volume.get("triggerOnPole"),
                            "waitSrvRes": volume.get("waitSrvRes"),
                            "shapes": shapes,
                        }))
                    if {
                        volume.get("slotId") for volume in compact_volumes
                    } != shared_selector_slots:
                        continue
                    local_trigger_context = {
                        "status": candidate_context.get("status"),
                        "selectorSlotIds": sorted(shared_selector_slots),
                        "triggerVolumes": compact_volumes,
                        "schemaMappingId": schema.get("mappingId"),
                        "foreignKeyBridgeFound": False,
                        "missionGraphAction": "none",
                    }
                exact_actions.append(compact_dict({
                    "actionName": action.get("actionName"),
                    "unionTag": action.get("unionTag"),
                    "serializedMemberCount":
                        action.get("serializedMemberCount"),
                    "recordOffset": action.get("recordOffset"),
                    "actionMapRole": action.get("actionMapRole"),
                    "localId": action.get("localId"),
                    "nextId": action.get("nextId"),
                    "targetDynamicEntityLogicId":
                        action.get("targetDynamicEntityLogicId"),
                    "visible": action.get("visible"),
                    "sourceFile": action.get("sourceFile"),
                    "storyControlPathLinks": story_links,
                    "localTriggerVolumeContext": local_trigger_context,
                }))
            if logic_id and exact_actions:
                bridges_by_logic_id[logic_id] = {
                    "classification": str(
                        bridge_row.get("classification") or ""
                    ),
                    "exactTargetActions": exact_actions,
                    "sharedStoryKeys": sorted(shared_story_keys),
                    "missionOwnerStatus": "unresolved",
                    "storyBinding": False,
                    "orderEvidence": False,
                    "missionGraphAction": "none",
                }

    rows: list[dict[str, Any]] = []
    for candidate in audit.get("storyIdentityCandidates") or []:
        if not isinstance(candidate, dict):
            continue
        logic_id = str(candidate.get("logicId") or "")
        scene = str(candidate.get("scene") or "")
        conditions: list[dict[str, Any]] = []
        seen_conditions: set[str] = set()
        for control in candidate.get("missionControls") or []:
            if not isinstance(control, dict):
                continue
            for condition in control.get("conditions") or []:
                if not isinstance(condition, dict):
                    continue
                identifier = str(condition.get("identifier") or "")
                if not identifier:
                    continue
                row = {
                    "identifier": identifier,
                    "isQuest": condition.get("isQuest") is True,
                    "state": condition.get("state"),
                    "isSame": condition.get("isSame") is True,
                    "compareType": control.get("compareType"),
                    "toBeTrue": control.get("toBeTrue") is True,
                }
                signature = json.dumps(row, sort_keys=True, separators=(",", ":"))
                if signature not in seen_conditions:
                    seen_conditions.add(signature)
                    conditions.append(row)

        story_occurrences: list[dict[str, Any]] = []
        seen_occurrences: set[str] = set()
        for occurrence in candidate.get("storyOccurrences") or []:
            if not isinstance(occurrence, dict):
                continue
            story_key = str(occurrence.get("storyKey") or "")
            script_id = str(occurrence.get("scriptId") or "")
            if not story_key or not script_id or script_id != logic_id:
                continue
            row = compact_dict({
                "storyKey": story_key,
                "levelId": str(occurrence.get("levelId") or ""),
                "scriptId": script_id,
                "recordOffset": occurrence.get("recordOffset"),
                "actionName": str(occurrence.get("actionName") or ""),
                "sourceFile": str(occurrence.get("sourceFile") or ""),
                "nativeEventOwnerStatus": str(
                    occurrence.get("nativeEventOwnerStatus") or ""
                ),
            })
            signature = json.dumps(row, sort_keys=True, separators=(",", ":"))
            if signature not in seen_occurrences:
                seen_occurrences.add(signature)
                story_occurrences.append(row)
        if not logic_id or not scene or not conditions or not story_occurrences:
            continue
        published_row = {
            "scene": scene,
            "logicId": logic_id,
            "scriptId": logic_id,
            "conditions": conditions,
            "storyOccurrences": story_occurrences,
            "dynamicSourceFile": str(candidate.get("sourceFile") or ""),
            "classification": boundary["classification"],
            "missionOwnerStatus": "unresolved",
            "storyBinding": False,
            "orderEvidence": False,
            "missionGraphAction": "none",
        }
        bridge = bridges_by_logic_id.get(logic_id)
        if bridge:
            occurrence_keys = {
                occurrence["storyKey"] for occurrence in story_occurrences
            }
            if set(bridge.get("sharedStoryKeys") or []).issubset(occurrence_keys):
                published_row["localContextBridge"] = bridge
        rows.append(published_row)

    rows.sort(key=lambda row: (
        row["scene"],
        natural_quest_key(row["logicId"]),
        row["dynamicSourceFile"],
    ))
    return {
        "classification": boundary["classification"],
        "finding": (
            "Exact authored DynamicScene logic ids equal exported LevelScript "
            "script ids and co-carry mission/quest state conditions. One current "
            "LevelScript also targets its matching DynamicScene root on the "
            "same local control path as Story playback. No evidence shows that "
            "the DynamicScene mission condition activates that LevelScript "
            "header, so every row remains non-owning context."
        ),
        "boundary": boundary.get("promotionRequirement"),
        "directBridgeFound": False,
        "missionActivationBridgeFound": False,
        "missionGraphAction": "none",
        "reportJson": repo_path(audit_path),
        "actionBridgeReportJson": (
            repo_path(action_bridge_path)
            if bridge_report and action_bridge_path is not None
            else ""
        ),
        "counts": {
            "candidateRoots": len(rows),
            "storyOccurrences": sum(
                len(row["storyOccurrences"]) for row in rows
            ),
            "exactTargetBridgeRoots": sum(
                bool(row.get("localContextBridge")) for row in rows
            ),
            "sharedControlPathStoryOccurrences": sum(
                len(
                    (row.get("localContextBridge") or {}).get(
                        "sharedStoryKeys"
                    ) or []
                )
                for row in rows
            ),
            "exactLocalTriggerVolumeContexts": sum(
                bool(
                    action.get("localTriggerVolumeContext")
                )
                for row in rows
                for action in (
                    (row.get("localContextBridge") or {}).get(
                        "exactTargetActions"
                    ) or []
                )
            ),
            "triggerVolumeForeignKeyBridges": 0,
        },
        "rows": rows,
    }


def _playback_gate_operand_label(operand: Any) -> str:
    if not isinstance(operand, dict):
        return ""
    if operand.get("path"):
        return str(operand["path"])
    if isinstance(operand.get("getterLocalId"), int):
        return f"getter #{operand['getterLocalId']}"
    if "value" in operand:
        return json.dumps(operand.get("value"), ensure_ascii=False)
    return ""


def _playback_gate_child_summary(tree: dict[str, Any], path: str) -> str:
    for child in tree.get("children") or []:
        if str(child.get("path") or "") == path:
            return _playback_gate_tree_summary(child.get("predicate") or {})
    return ""


def _playback_gate_tree_summary(tree: dict[str, Any]) -> str:
    """Render an identity-agnostic exact predicate tree for the WebUI."""
    if not isinstance(tree, dict):
        return ""
    predicate_type = str(tree.get("predicateType") or "")
    predicate = tree.get("predicate") or {}

    def operand(field: str) -> str:
        nested = _playback_gate_child_summary(
            tree,
            f"{field}.getterLocalId",
        )
        return nested or _playback_gate_operand_label(predicate.get(field))

    if predicate_type in {"boolGetterAnd", "boolGetterOr"}:
        left = operand("valueA")
        right = operand("valueB")
        operator = "AND" if predicate_type == "boolGetterAnd" else "OR"
        return f"({left} {operator} {right})" if left and right else ""
    if predicate_type == "boolGetterInvert":
        value = operand("value")
        return f"NOT ({value})" if value else ""
    if predicate_type == "boolGetterMultiAnd":
        values = [
            _playback_gate_child_summary(
                tree,
                f"values[{index}].getterLocalId",
            )
            for index, _value in enumerate(predicate.get("values") or [])
        ]
        return (
            f"ALL ({' AND '.join(values)})"
            if values and all(values)
            else ""
        )
    if predicate_type == "booleanCompare":
        left = operand("valueA")
        right = operand("valueB")
        operator = {"Equal": "==", "NotEqual": "!="}.get(
            str(predicate.get("comparerName") or ""),
            "",
        )
        return f"{left} {operator} {right}" if left and operator and right else ""
    if predicate_type == "intEqual":
        left = operand("valueA")
        right = operand("valueB")
        return f"{left} == {right}" if left and right else ""
    if predicate_type in {"intCompare", "floatNewCompare"}:
        left = _playback_gate_child_summary(tree, "valueAGetterLocalId")
        right = _playback_gate_operand_label(predicate.get("valueB"))
        operator = {
            "Equal": "==",
            "NotEqual": "!=",
            "GreaterThan": ">",
            "GreaterEqual": ">=",
            "LessThan": "<",
            "LessEqual": "<=",
        }.get(str(predicate.get("comparerName") or ""), "")
        return f"{left} {operator} {right}" if left and operator and right else ""
    if predicate_type in {"getterBool", "getterInt"}:
        return _playback_gate_operand_label(predicate.get("value"))
    if predicate_type == "getLevelScriptStage":
        script_ptr = predicate.get("scriptPtr") or {}
        script_id = str(script_ptr.get("scriptId") or "current script")
        return f"{script_id}.stage"
    if predicate_type == "getLsmIsCompleted":
        lsm_ptr = predicate.get("lsmPtr") or {}
        identity = str(lsm_ptr.get("rawValueHex") or "LSM")
        return f"LSM[{identity}].completed"
    if predicate_type == "interactiveCheckState":
        target = predicate.get("target") or {}
        identity = (
            f"slot {target.get('slotId')}"
            if target.get("useSlotId")
            else f"entity {target.get('logicId')}"
        )
        operator = {
            "Equal": "==",
            "NotEqual": "!=",
            "GreaterThan": ">",
            "GreaterEqual": ">=",
            "LessThan": "<",
            "LessEqual": "<=",
        }.get(str(predicate.get("comparerName") or ""), "")
        value = _playback_gate_operand_label(predicate.get("value"))
        return f"{identity}.interactiveState {operator} {value}" if operator and value else ""
    return ""


def _playback_gate_tree_metrics(tree: dict[str, Any]) -> tuple[int, int]:
    if not isinstance(tree, dict) or not tree:
        return 0, 0
    child_metrics = [
        _playback_gate_tree_metrics(child.get("predicate") or {})
        for child in tree.get("children") or []
    ]
    return (
        1 + sum(count for count, _depth in child_metrics),
        1 + max((depth for _count, depth in child_metrics), default=0),
    )


def exact_native_receiver_playback_gate(
    data: bytes,
    header_local_id: int,
    *,
    source_file: str,
) -> dict[str, Any]:
    """Build a UI-safe exact gate without specializing Story ids or objects."""
    validation = decode_levelscript_action_header_validation(
        data,
        header_local_id,
    )
    predicate_type = str(validation.get("predicateType") or "")
    predicate = validation.get("predicate")
    if not validation or not isinstance(predicate, dict):
        return {}
    predicate_tree = validation.get("predicateTree") or {
        "predicateType": predicate_type,
        "predicate": predicate,
        "children": [],
    }
    summary = _playback_gate_tree_summary(predicate_tree)
    if not summary:
        return {}
    predicate_node_count, predicate_depth = _playback_gate_tree_metrics(
        predicate_tree
    )
    return {
        **validation,
        "summary": summary,
        "predicateNodeCount": predicate_node_count,
        "predicateDepth": predicate_depth,
        "effect": "receiver_playback_allowed_when_true",
        "branchScope": "this_receiver_header_only",
        "sourceFile": source_file,
        "branchEvidence": True,
        "missionOwnershipEvidence": False,
        "crossStoryOrderEvidence": False,
        "serverWriteEvidence": False,
        "evidenceBoundary": (
            "The installed client evaluates this ActionHeader validation before "
            "the receiver proceeds. It does not identify a mission owner, order "
            "different Story files, or prove any later server-side state write."
        ),
    }


def exact_native_receiver_post_playback_control(
    owner: dict[str, Any],
    *,
    story_key: str,
    playback_local_id: int,
    source_file: str,
) -> dict[str, Any]:
    """Compact exact typed successors after any native Story action.

    ``_levelscript_native_control_paths_to_record`` already walks the current
    runtime action slots and every typed successor field.  This projection is
    deliberately identity-agnostic: it accepts any Story/action/header and
    preserves only serialized control-flow.  It never interprets a callback
    label as a server handler, mission id, or quest id.
    """
    if (
        not isinstance(owner, dict)
        or owner.get("status") not in {
            "exact_serialized_control_path",
            "exact_serialized_control_path_equivalent_duplicates",
            "exact_serialized_control_path_runtime_shadowing",
        }
        or owner.get("downstreamControlStatus")
        != "exact_serialized_typed_reachability"
        or not story_key
        or not isinstance(playback_local_id, int)
        or not source_file
    ):
        return {}
    paths: list[list[dict[str, Any]]] = []
    seen_paths: set[tuple[tuple[str, int], ...]] = set()
    for raw_path in owner.get("downstreamControlPaths") or []:
        if not isinstance(raw_path, list) or not raw_path:
            continue
        path: list[dict[str, Any]] = []
        signature: list[tuple[str, int]] = []
        for raw_step in raw_path:
            if not isinstance(raw_step, dict):
                path = []
                break
            edge = str(raw_step.get("edge") or "")
            local_id = raw_step.get("localId")
            if not edge or not isinstance(local_id, int):
                path = []
                break
            step = compact_dict({
                "edge": edge,
                "localId": local_id,
                "opcode": str(raw_step.get("opcode") or ""),
                "unionTag": str(raw_step.get("unionTag") or ""),
                "serializedMemberCount": raw_step.get(
                    "serializedMemberCount"
                ),
                "actionName": str(raw_step.get("actionName") or ""),
                "recordClass": str(raw_step.get("recordClass") or ""),
                "texts": [
                    str(value)
                    for value in raw_step.get("texts") or []
                    if str(value)
                ][:8],
                "callServerContract": raw_step.get("callServerContract") or None,
                "branchPredicate": raw_step.get("branchPredicate") or None,
            })
            path.append(step)
            signature.append((edge, local_id))
        path_signature = tuple(signature)
        if path and path_signature not in seen_paths:
            seen_paths.add(path_signature)
            paths.append(path)
    if not paths:
        return {}

    # The producer publishes every reachable prefix. Keep only maximal paths
    # for display while deriving a de-duplicated edge/node graph from all of
    # them. This is structural and works for linear, split, conditional,
    # switch, loop, and wait-success/failure successor families.
    signatures = [
        tuple((str(step["edge"]), int(step["localId"])) for step in path)
        for path in paths
    ]
    maximal_paths = [
        path
        for index, path in enumerate(paths)
        if not any(
            len(other) > len(signatures[index])
            and other[: len(signatures[index])] == signatures[index]
            for other in signatures
        )
    ]
    action_nodes: dict[int, dict[str, Any]] = {}
    edges: dict[tuple[int, int, str], dict[str, Any]] = {}
    outgoing: dict[int, set[tuple[int, str]]] = defaultdict(set)
    for path in paths:
        source_local_id = playback_local_id
        for step in path:
            local_id = int(step["localId"])
            action_nodes.setdefault(local_id, {
                key: value for key, value in step.items() if key != "edge"
            })
            edge = str(step["edge"])
            edge_key = (source_local_id, local_id, edge)
            edges[edge_key] = {
                "sourceLocalId": source_local_id,
                "targetLocalId": local_id,
                "edge": edge,
            }
            outgoing[source_local_id].add((local_id, edge))
            source_local_id = local_id
    branch_points = sorted(
        source for source, targets in outgoing.items() if len(targets) > 1
    )
    server_handoffs = []
    for node in action_nodes.values():
        if node.get("recordClass") != "server_handoff":
            continue
        labels = [
            value
            for value in node.get("texts") or []
            if isinstance(value, str) and value.startswith("#")
        ]
        callback_header_uids = node.get("callServerCallbackOutputUIDs")
        serialized_contract = node.get("callServerContract") or {}
        if not callback_header_uids and isinstance(
            serialized_contract.get("callClientOutputUIDs"), list
        ):
            callback_header_uids = serialized_contract["callClientOutputUIDs"]
        server_handoffs.append({
            key: value
            for key, value in {
                "localId": node.get("localId"),
                "actionName": node.get("actionName") or "CallServer",
                "callbackCorrelationLabels": labels,
                "possibleCallbackHeaderUIDs": (
                    callback_header_uids
                    if isinstance(callback_header_uids, list)
                    else None
                ),
                "callbackHeaderMappingId": node.get(
                    "callServerCallbackMappingId"
                ),
                "serializedContract": serialized_contract or None,
                "relatedOriginalFiles": [{
                    "kind": "LevelScriptData",
                    "sourceFile": source_file,
                    "relationship": "serialized_callserver_action",
                }],
                "serverHandlerIdentity": False,
            }.items()
            if value is not None
        })
    return {
        "schema": "exactNativePostPlaybackControl.v1",
        "status": "exact_serialized_typed_reachability",
        "storyKey": story_key,
        "playbackLocalId": playback_local_id,
        "sourceFile": source_file,
        "actions": sorted(action_nodes.values(), key=lambda row: row["localId"]),
        "edges": sorted(
            edges.values(),
            key=lambda row: (
                row["sourceLocalId"],
                row["targetLocalId"],
                row["edge"],
            ),
        ),
        "maximalReachablePaths": maximal_paths,
        "branchPointLocalIds": branch_points,
        "serverHandoffs": server_handoffs,
        "intraScriptControlFlowEvidence": True,
        "missionOwnershipEvidence": False,
        "crossStoryOrderEvidence": False,
        "serverHandlerIdentityEvidence": False,
        "evidenceBoundary": (
            "Typed successor fields prove only the exact local action graph "
            "after this Story action. The installed binary additionally proves "
            "that non-empty CallServer output lists name possible callback "
            "headers; those conditional paths are admitted only through exact "
            "same-file UID/event/header matches. Callback labels do not identify "
            "a server handler, mission/quest owner, or state write."
        ),
    }


def attach_post_playback_callserver_contracts(
    runtime_nodes: list[dict[str, Any]],
    callback_audit: dict[str, Any],
) -> dict[str, Any]:
    """Attach complete-corpus CallServer rows by exact source/local identity.

    The join is intentionally generic across all missions, maps, and Story
    actions. It fails closed on duplicate or disagreeing rows and never treats
    an event name or argument path as a mission/quest foreign key.
    """
    audit_rows: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in callback_audit.get("rows") or []:
        source_file = str(row.get("sourceFile") or "").replace("\\", "/")
        local_id = row.get("callServerLocalId")
        if source_file and isinstance(local_id, int):
            audit_rows[(source_file, local_id)].append(row)

    counts: Counter[str] = Counter()
    event_identities: Counter[str] = Counter()
    argument_paths: Counter[str] = Counter()
    flag_combinations: Counter[str] = Counter()
    failures: list[dict[str, Any]] = []
    for node in runtime_nodes:
        for control in node.get("postPlaybackControls") or []:
            source_file = str(control.get("sourceFile") or "").replace("\\", "/")
            for handoff in control.get("serverHandoffs") or []:
                counts["handoffs"] += 1
                local_id = handoff.get("localId")
                candidates = audit_rows.get((source_file, local_id), [])
                if len(candidates) != 1:
                    counts["unresolvedContracts"] += 1
                    failures.append({
                        "gate": "post_playback_callserver_exact_identity",
                        "source": source_file,
                        "localId": local_id,
                        "expectedCandidateCount": 1,
                        "actualCandidateCount": len(candidates),
                    })
                    continue
                audit_contract = compact_callserver_serialized_contract(
                    candidates[0].get("serializedContract") or {}
                )
                path_contract = compact_callserver_serialized_contract(
                    handoff.get("serializedContract") or {}
                )
                if path_contract and path_contract != audit_contract:
                    counts["contractMismatches"] += 1
                    failures.append({
                        "gate": "post_playback_callserver_contract_match",
                        "source": source_file,
                        "localId": local_id,
                        "expected": audit_contract,
                        "actual": path_contract,
                    })
                    continue
                handoff["serializedContract"] = audit_contract
                handoff["contractStatus"] = "exact_source_local_id_match"
                handoff["missionOwnershipEvidence"] = False
                counts["exactContracts"] += 1
                event_identities[
                    str(audit_contract.get("eventNameIdentity") or "other")
                ] += 1
                event_args = audit_contract.get("eventArgsPtr") or {}
                argument_paths[
                    str(event_args.get("path") or "<null>")
                ] += 1
                flag_combinations[
                    "custom={custom},wait={wait},args={args}".format(
                        custom=int(bool(audit_contract.get("useCustomEvent"))),
                        wait=int(bool(audit_contract.get("waitForCallback"))),
                        args=int(bool(audit_contract.get("withEventArgs"))),
                    )
                ] += 1
    return {
        "status": "validated" if not failures else "validation_failed",
        "summary": {
            **dict(sorted(counts.items())),
            "eventNameIdentityDistribution": dict(sorted(event_identities.items())),
            "eventArgsParamPathDistribution": dict(sorted(argument_paths.items())),
            "flagDistribution": dict(sorted(flag_combinations.items())),
        },
        "validationFailures": failures,
        "missionOwnershipEvidence": False,
        "evidenceBoundary": (
            "Every post-playback CallServer is joined to the complete original-data "
            "action audit by exact source file and local action id. Serialized event "
            "names, argument parameters, flags, and callback UIDs describe the client "
            "handoff contract; absent an independent original-data foreign key, they "
            "do not identify a mission/quest owner or order another Story file."
        ),
    }


def build_level_sequence_textasset_index(
    root: Path = DEFAULT_LEVEL_SEQUENCE_TEXTASSET_ROOT,
) -> dict[str, Any]:
    """Index original LevelSequence TextAssets by three-way exact identity.

    A filename is only an enumeration aid. A row is eligible for a join when
    the exported Unity ``m_Name`` and ``Name`` fields and the decoded payload's
    ``cutsceneName`` all agree. This keeps the resolver reusable across maps,
    missions, and sequence ids while failing closed on malformed or ambiguous
    exports.
    """
    assets_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    failures: list[dict[str, Any]] = []
    source_files = sorted(root.glob("levelseq_*.json")) if root.is_dir() else []
    for source_path in source_files:
        try:
            raw = source_path.read_bytes()
            outer = json.loads(raw.decode("utf-8-sig"))
            if not isinstance(outer, dict):
                raise ValueError("outer JSON is not an object")
            unity_name = str(outer.get("m_Name") or "")
            exported_name = str(outer.get("Name") or "")
            encoded_payload = outer.get("m_Script")
            if not unity_name or unity_name != exported_name:
                raise ValueError(
                    f"outer identity mismatch m_Name={unity_name!r} Name={exported_name!r}"
                )
            if not isinstance(encoded_payload, str) or not encoded_payload:
                raise ValueError("m_Script is not a non-empty base64 string")
            decoded = base64.b64decode(encoded_payload, validate=True)
            payload = json.loads(decoded.decode("utf-8-sig"))
            if not isinstance(payload, dict):
                raise ValueError("decoded m_Script JSON is not an object")
            payload_name = str(payload.get("cutsceneName") or "")
            if payload_name != unity_name:
                raise ValueError(
                    f"payload identity mismatch cutsceneName={payload_name!r} m_Name={unity_name!r}"
                )
            path_id_match = re.search(r"_p([0-9A-Fa-f]+)\.json$", source_path.name)
            assets_by_id[unity_name].append(compact_dict({
                "levelSequenceId": unity_name,
                "sourceFile": repo_path(source_path),
                "pathId": (
                    f"0x{path_id_match.group(1).upper()}"
                    if path_id_match
                    else ""
                ),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "payloadPath": str(payload.get("path") or ""),
                "payloadVersion": payload.get("version"),
                "targetFrameRate": payload.get("targetFrameRate"),
                "identityStatus": "exact_m_name_name_cutscene_name_match",
            }))
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
            failures.append({
                "validator": "levelSequenceTextAssetIdentity",
                "gate": "m_Name_equals_Name_equals_decoded_cutsceneName",
                "sourceFile": repo_path(source_path),
                "actual": str(error)[:400],
            })

    ambiguous_ids = sorted(
        sequence_id
        for sequence_id, rows in assets_by_id.items()
        if len(rows) != 1
    )
    exact_assets = {
        sequence_id: rows[0]
        for sequence_id, rows in sorted(assets_by_id.items())
        if len(rows) == 1
    }
    return {
        "schema": "exactLevelSequenceTextAssetIndex.v1",
        "root": repo_path(root),
        "status": (
            "exact_complete"
            if source_files and not failures and not ambiguous_ids
            else "degraded_fail_closed"
        ),
        "assetsById": exact_assets,
        "summary": {
            "sourceFilesScanned": len(source_files),
            "exactUniqueIdentities": len(exact_assets),
            "validationFailures": len(failures),
            "ambiguousIdentities": len(ambiguous_ids),
        },
        "validationFailures": failures,
        "ambiguousLevelSequenceIds": ambiguous_ids,
    }


def attach_exact_level_sequence_assets(
    runtime_nodes: list[dict[str, Any]],
    asset_index: dict[str, Any],
) -> dict[str, Any]:
    """Attach exact original files to typed LevelSequence control actions.

    Action classes come from the installed ActionBase formatter table. The
    family test is intentionally type-based (``LevelSeq`` in that recovered
    class name); no mission, map, object, or sequence identifier is hardcoded.
    """
    assets_by_id = asset_index.get("assetsById") or {}
    action_placements = 0
    exact_placements = 0
    serialized_ids: set[str] = set()
    exact_ids: set[str] = set()
    unresolved_ids: set[str] = set()
    related_files: set[str] = set()
    for node in runtime_nodes:
        for control in node.get("postPlaybackControls") or []:
            for action in control.get("actions") or []:
                action_name = str(action.get("actionName") or "")
                if "LevelSeq" not in action_name:
                    continue
                sequence_ids = sorted({
                    str(value)
                    for value in action.get("texts") or []
                    if str(value).startswith("levelseq_")
                })
                if not sequence_ids:
                    continue
                action_placements += 1
                references = []
                for sequence_id in sequence_ids:
                    serialized_ids.add(sequence_id)
                    asset = assets_by_id.get(sequence_id)
                    if isinstance(asset, dict):
                        exact_placements += 1
                        exact_ids.add(sequence_id)
                        related_files.add(str(asset.get("sourceFile") or ""))
                        references.append({
                            **asset,
                            "relation": "exact_serialized_action_id_to_textasset_identity",
                            "missionOwnershipEvidence": False,
                            "crossStoryOrderEvidence": False,
                        })
                    else:
                        unresolved_ids.add(sequence_id)
                        references.append({
                            "levelSequenceId": sequence_id,
                            "identityStatus": "no_exact_validated_textasset",
                            "missionOwnershipEvidence": False,
                            "crossStoryOrderEvidence": False,
                        })
                action["levelSequenceReferences"] = references

    return {
        "schema": "postPlaybackLevelSequenceAssetAudit.v1",
        "status": (
            "exact_matches_with_unresolved_ids"
            if unresolved_ids
            else "all_serialized_ids_resolved"
        ),
        "sourceIndex": {
            key: asset_index.get(key)
            for key in (
                "schema", "root", "status", "summary",
                "validationFailures", "ambiguousLevelSequenceIds",
            )
        },
        "summary": {
            "typedActionPlacements": action_placements,
            "serializedLevelSequenceIds": len(serialized_ids),
            "exactAssetPlacements": exact_placements,
            "exactResolvedLevelSequenceIds": len(exact_ids),
            "unresolvedLevelSequenceIds": len(unresolved_ids),
            "relatedOriginalFiles": len({value for value in related_files if value}),
        },
        "unresolvedLevelSequenceIds": sorted(unresolved_ids),
        "usesOcrOrManualOrder": False,
        "missionOwnershipEvidence": False,
        "crossStoryOrderEvidence": False,
        "evidenceBoundary": (
            "The installed formatter type and serialized action id identify a local "
            "LevelSequence reference; the original TextAsset is attached only after "
            "m_Name, Name, and decoded cutsceneName agree. This does not identify a "
            "mission owner or order separate Story files."
        ),
    }


def build_post_playback_action_name_audit(
    runtime_nodes: list[dict[str, Any]],
    *,
    formatter_names: dict[int, str] | None = None,
    formatter_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Measure binary formatter naming across the complete control surface."""
    formatter_names = (
        ACTIONBASE_FORMATTER_ACTION_NAMES
        if formatter_names is None
        else formatter_names
    )
    formatter_audit = (
        ACTIONBASE_FORMATTER_NAME_AUDIT
        if formatter_audit is None
        else formatter_audit
    )
    shape_counts: Counter[tuple[str, str]] = Counter()
    formatter_named_actions = 0
    fallback_named_actions = 0
    unresolved_actions = 0
    mismatches: list[dict[str, Any]] = []
    opcode_pattern = re.compile(r"^0x([0-9a-f]+)/0x([0-9a-f]+)$", re.IGNORECASE)
    for node in runtime_nodes:
        for control in node.get("postPlaybackControls") or []:
            for action in control.get("actions") or []:
                opcode = str(action.get("opcode") or "")
                action_name = str(action.get("actionName") or "")
                shape_counts[(opcode, action_name)] += 1
                match = opcode_pattern.match(opcode)
                union_tag_text = str(action.get("unionTag") or "")
                try:
                    union_tag = int(union_tag_text, 16)
                except ValueError:
                    union_tag = int(match.group(1), 16) if match else -1
                serialized_member_count = action.get("serializedMemberCount")
                if not isinstance(serialized_member_count, int):
                    serialized_member_count = (
                        int(match.group(2), 16) if match else 0
                    )
                if union_tag < 0:
                    unresolved_actions += 1
                    continue
                formatter_name = (
                    str(formatter_names.get(union_tag) or "")
                    if serialized_member_count > 0
                    else ""
                )
                if formatter_name:
                    if action_name == formatter_name:
                        formatter_named_actions += 1
                    else:
                        mismatches.append({
                            "validator": "postPlaybackActionFormatterName",
                            "gate": "action_name_equals_formatter_tag",
                            "sourceFile": str(control.get("sourceFile") or ""),
                            "storyKey": str(control.get("storyKey") or ""),
                            "actionLocalId": action.get("localId"),
                            "expected": {
                                "opcode": opcode,
                                "unionTag": f"0x{union_tag:04x}",
                                "serializedMemberCount": serialized_member_count,
                                "actionName": formatter_name,
                            },
                            "actual": {"actionName": action_name},
                        })
                elif action_name:
                    fallback_named_actions += 1
                else:
                    unresolved_actions += 1
    total_actions = sum(shape_counts.values())
    unresolved_shapes = [
        {"opcode": opcode, "count": count}
        for (opcode, action_name), count in sorted(shape_counts.items())
        if not action_name
    ]
    source_failures = list(formatter_audit.get("validationFailures") or [])
    failures = source_failures + mismatches
    return {
        "schema": "postPlaybackActionNameAudit.v1",
        "status": (
            "validated_complete_actionbase_surface"
            if not failures and not unresolved_actions
            else "validated_actionbase_complete_outside_families_retained"
            if not failures
            else "validation_failed"
        ),
        "formatterTable": formatter_audit,
        "summary": {
            "actionPlacements": total_actions,
            "formatterNamedActionPlacements": formatter_named_actions,
            "fallbackNamedActionPlacements": fallback_named_actions,
            "unresolvedOutsideActionBasePlacements": unresolved_actions,
            "distinctActionShapes": len(shape_counts),
            "unresolvedOutsideActionBaseShapes": len(unresolved_shapes),
            "validationFailures": len(failures),
        },
        "unresolvedActionShapes": unresolved_shapes,
        "validationFailures": failures,
        "usesOcrOrManualOrder": False,
        "missionOwnershipEvidence": False,
        "crossStoryOrderEvidence": False,
        "evidenceBoundary": (
            "The installed ActionBase MemoryPack formatter names action classes "
            "from the compact unionTag plus serializedMemberCount. Legacy combined "
            "raw opcodes remain display provenance and are never used as the tag. "
            "A class name does not identify a mission owner, select a branch, or "
            "order separate Story files."
        ),
    }


POST_PLAYBACK_VARIABLE_SETTER_ACTIONS = {
    "SetBool",
    "SetInt",
    "SetIntIncrease",
}


def load_native_cross_system_consumer_contract(
    audit_path: Path = DEFAULT_NATIVE_CROSS_SYSTEM_CONSUMER_CENSUS,
) -> dict[str, Any]:
    """Publish the generic hash-locked closure audit when locally available."""
    fallback = copy.deepcopy(RUNTIME_CONTRACT["nativeCrossSystemConsumerCensus"])
    if not audit_path.is_file():
        return fallback
    audit = read_json(audit_path)
    if audit.get("schemaVersion") != "nativeCrossSystemConsumerCensus.v4":
        raise RuntimeError(
            "validator=nativeCrossSystemConsumerCensus gate=auditSchema "
            "expected='nativeCrossSystemConsumerCensus.v4' "
            f"actual={audit.get('schemaVersion')!r} source={audit_path}"
        )
    validation = audit.get("validation") or {}
    if validation.get("status") != "passed":
        failure = (validation.get("failures") or [{}])[0]
        raise RuntimeError(
            "validator=nativeCrossSystemConsumerCensus "
            f"gate={failure.get('gate') or 'upstreamValidation'} "
            f"expected={failure.get('expected')!r} actual={failure.get('actual')!r} "
            f"source={failure.get('sourceFile') or audit_path}"
        )
    summary = audit.get("summary") or {}
    closure = audit.get("directConsumerClosure") or {}
    closure_counts = closure.get("counts") or {}
    deferred = audit.get("deferredRefreshClosure") or {}
    mission_runtime_surface = audit.get("missionRuntimeSurface") or {}
    managed_callable_surface = audit.get("managedCallableSurface") or {}
    source = audit.get("source") or {}
    classifications = summary.get("classificationCounts") or {}
    return {
        "source": repo_path(audit_path),
        "method": " ".join(filter(None, [
            str((audit.get("method") or {}).get("selection") or ""),
            str(closure.get("method") or ""),
        ])),
        "counts": {
            "mappedMethodPointers": (audit.get("method") or {}).get("mappedMethodPointers", 0),
            "familyTargetPointers": (audit.get("method") or {}).get("familyTargetPointers", 0),
            "crossSystemCallers": summary.get("crossSystemCallers", 0),
            "missionStateDynamicSceneCallers": classifications.get(
                "mission_state_controls_dynamic_component_availability", 0
            ),
            "missionLevelScriptCallers": summary.get("missionLevelScriptCallers", 0),
            "tripleOrGreaterFamilyCallers": summary.get("tripleOrGreaterFamilyCallers", 0),
            "dynamicSceneStoryCallers": classifications.get(
                "story_dynamic_scene_visual_context", 0
            ),
            "unreviewedCallers": summary.get("unreviewedCallers", 0),
            "closureReachableMethods": closure_counts.get("reachableMethods", 0),
            "closureDirectEdges": closure_counts.get("directEdges", 0),
            "closureLevelScriptMethods": closure_counts.get("levelScriptMethods", 0),
            "closureStoryMethods": closure_counts.get("storyMethods", 0),
            "unreviewedIndirectSites": closure_counts.get("unreviewedIndirectSites", 0),
        },
        "deferredRefreshClosure": deferred,
        "missionRuntimeSurface": mission_runtime_surface,
        "managedCallableSurface": managed_callable_surface,
        "finding": audit.get("finding"),
        "boundary": audit.get("boundary"),
        "relatedOriginalFiles": [{
            "sourceFile": source.get("gameAssembly"),
            "sha256": source.get("gameAssemblySha256"),
            "role": "native consumer and deferred refresh implementation",
        }, {
            "sourceFile": source.get("globalMetadata"),
            "sha256": source.get("globalMetadataSha256"),
            "role": "managed identities and runtime field layout",
        }],
        "classification": deferred.get(
            "classification", "binary_cross_system_consumers_reviewed"
        ),
        "storyBindingsAdded": 0,
        "missionOrderEdgesAdded": 0,
        "confidence": "hash_locked_direct_and_deferred_native_closure",
    }


def load_state_update_application_contract(
    audit_path: Path = DEFAULT_PROTOCOL_REGISTRY_AUDIT,
) -> dict[str, Any]:
    """Load and revalidate the binary-derived branch-authority contract."""
    if not audit_path.is_file():
        raise RuntimeError(
            "validator=state_update_application_contract gate=auditExists "
            f"expected=file actual=missing source={audit_path}"
        )
    audit = read_json(audit_path)
    if audit.get("_schema") != "endfieldProtocolRegistryAudit.v20":
        raise RuntimeError(
            "validator=state_update_application_contract gate=auditSchema "
            "expected='endfieldProtocolRegistryAudit.v20' "
            f"actual={audit.get('_schema')!r} source={audit_path}"
        )
    census = audit.get("stateUpdateApplicationCensus") or {}
    validation = census.get("validation") or {}
    if validation.get("status") != "validated":
        failure = (validation.get("failures") or [{}])[0]
        raise RuntimeError(
            "validator=state_update_application_contract "
            f"gate={failure.get('gate') or 'upstreamValidation'} "
            f"message={failure.get('message')} expected={failure.get('expected')!r} "
            f"actual={failure.get('actual')!r} "
            f"source={failure.get('sourceFile') or audit_path}"
        )
    quest_state_lifecycle = census.get("questStateLifecycleApplication") or {}
    quest_state_validation = quest_state_lifecycle.get("validation") or {}
    if quest_state_validation.get("status") != "validated":
        failure = (quest_state_validation.get("failures") or [{}])[0]
        raise RuntimeError(
            "validator=state_update_application_contract "
            f"gate={failure.get('gate') or 'questStateLifecycleApplication'} "
            f"message={failure.get('message')} expected={failure.get('expected')!r} "
            f"actual={failure.get('actual')!r} "
            f"source={failure.get('sourceFile') or audit_path}"
        )
    if quest_state_lifecycle.get("schema") != "questStateLifecycleApplication.v1":
        raise RuntimeError(
            "validator=state_update_application_contract "
            "gate=questStateLifecycleSchema "
            "expected='questStateLifecycleApplication.v1' "
            f"actual={quest_state_lifecycle.get('schema')!r} source={audit_path}"
        )
    transitions = quest_state_lifecycle.get("transitions") or []
    transition_shapes = {
        tuple(call.get("method") for call in row.get("reachableLifecycleCalls") or [])
        for row in transitions
    }
    successor_fields = (
        (quest_state_lifecycle.get("message") or {}).get("successorLikeFields")
        or []
    )
    if len(transitions) < 2 or len(transition_shapes) < 2 or successor_fields:
        raise RuntimeError(
            "validator=state_update_application_contract "
            "gate=questStateLifecycleShape "
            "expected='>=2 distinct state routes and no successor field' "
            f"actual={{'transitions': {transitions!r}, "
            f"'successorLikeFields': {successor_fields!r}}} source={audit_path}"
        )
    quest_enable_lifecycle = census.get("questEnableLifecycleApplication") or {}
    quest_enable_validation = quest_enable_lifecycle.get("validation") or {}
    if quest_enable_validation.get("status") != "validated":
        failure = (quest_enable_validation.get("failures") or [{}])[0]
        raise RuntimeError(
            "validator=state_update_application_contract "
            f"gate={failure.get('gate') or 'questEnableLifecycleApplication'} "
            f"message={failure.get('message')} expected={failure.get('expected')!r} "
            f"actual={failure.get('actual')!r} "
            f"source={failure.get('sourceFile') or audit_path}"
        )
    enable_message = quest_enable_lifecycle.get("message") or {}
    enable_routes = quest_enable_lifecycle.get("routes") or []
    packet_fields = enable_message.get("consumedControlFields") or []
    runtime_field = str(
        (quest_enable_lifecycle.get("runtimeControl") or {}).get("field") or ""
    )
    route_values = sorted({
        (
            (route.get("values") or {}).get(packet_fields[0]),
            (route.get("values") or {}).get(runtime_field),
        )
        for route in enable_routes
    }) if len(packet_fields) == 1 and runtime_field else []
    route_calls = [
        route.get("reachableLifecycleCalls") or [] for route in enable_routes
    ]
    enable_shape = {
        "schema": quest_enable_lifecycle.get("schema"),
        "identityField": enable_message.get("identityField"),
        "packetControlFieldCount": len(packet_fields),
        "runtimeControlField": runtime_field,
        "routeValues": route_values,
        "oneCallPerRoute": bool(route_calls)
        and all(len(calls) == 1 for calls in route_calls),
        "distinctLifecycleMethods": len({
            calls[0].get("method")
            for calls in route_calls
            if len(calls) == 1
        }),
        "samePacketIdentity": bool(route_calls)
        and all(
            calls[0].get("samePacketIdentity") is True
            for calls in route_calls
            if len(calls) == 1
        ),
        "unreadControlFieldCount": len(
            enable_message.get("unreadControlFields") or []
        ),
        "successorLikeFields": enable_message.get("successorLikeFields") or [],
    }
    expected_route_values = [
        (False, False), (False, True), (True, False), (True, True)
    ]
    if (
        enable_shape["schema"] != "questEnableLifecycleApplication.v1"
        or not enable_shape["identityField"]
        or enable_shape["packetControlFieldCount"] != 1
        or not enable_shape["runtimeControlField"]
        or enable_shape["routeValues"] != expected_route_values
        or not enable_shape["oneCallPerRoute"]
        or enable_shape["distinctLifecycleMethods"] < 3
        or not enable_shape["samePacketIdentity"]
        or enable_shape["unreadControlFieldCount"] < 1
        or enable_shape["successorLikeFields"]
    ):
        raise RuntimeError(
            "validator=state_update_application_contract "
            "gate=questEnableLifecycleShape "
            "expected='generic complete two-boolean matrix, one identity-preserving "
            "lifecycle call per route, >=3 methods, unread context, no successor field' "
            f"actual={enable_shape!r} source={audit_path}"
        )
    quest_start = census.get("questStartApplication") or {}
    quest_start_validation = quest_start.get("validation") or {}
    if quest_start_validation.get("status") != "validated":
        failure = (quest_start_validation.get("failures") or [{}])[0]
        raise RuntimeError(
            "validator=state_update_application_contract "
            f"gate={failure.get('gate') or 'questStartApplication'} "
            f"message={failure.get('message')} expected={failure.get('expected')!r} "
            f"actual={failure.get('actual')!r} "
            f"source={failure.get('sourceFile') or audit_path}"
        )
    quest_succeed = census.get("questSucceedActionApplication") or {}
    quest_succeed_validation = quest_succeed.get("validation") or {}
    if quest_succeed_validation.get("status") != "validated":
        failure = (quest_succeed_validation.get("failures") or [{}])[0]
        raise RuntimeError(
            "validator=state_update_application_contract "
            f"gate={failure.get('gate') or 'questSucceedActionApplication'} "
            f"message={failure.get('message')} expected={failure.get('expected')!r} "
            f"actual={failure.get('actual')!r} "
            f"source={failure.get('sourceFile') or audit_path}"
        )
    quest_dispatch_shape = {
        "schema": quest_succeed.get("schema"),
        "classification": quest_succeed.get("classification"),
        "startActionDispatchers": quest_succeed.get("startActionDispatchers") or [],
        "sharedPendingCarrier": (
            (quest_succeed.get("runQuestActionFlow") or {}).get(
                "sharedPendingCarrier"
            )
        ),
    }
    expected_dispatch_shape = {
        "schema": "questLifecycleClientAction.v2",
        "classification": "bounded_current_aot_quest_action_dispatch",
        "startActionDispatchers": [],
        "sharedPendingCarrier": True,
    }
    if quest_dispatch_shape != expected_dispatch_shape:
        raise RuntimeError(
            "validator=state_update_application_contract "
            "gate=questActionDispatchShape "
            f"expected={expected_dispatch_shape!r} "
            f"actual={quest_dispatch_shape!r} source={audit_path}"
        )
    topology_consumers = census.get("questTopologyFieldConsumers") or {}
    topology_validation = topology_consumers.get("validation") or {}
    if topology_validation.get("status") != "validated":
        failure = (topology_validation.get("failures") or [{}])[0]
        raise RuntimeError(
            "validator=state_update_application_contract "
            f"gate={failure.get('gate') or 'questTopologyFieldConsumers'} "
            f"message={failure.get('message')} expected={failure.get('expected')!r} "
            f"actual={failure.get('actual')!r} "
            f"source={failure.get('sourceFile') or audit_path}"
        )
    semantic_fields = topology_consumers.get("questSemanticFields") or {}
    if semantic_fields.get("schema") != "questSemanticFieldConsumers.v2":
        raise RuntimeError(
            "validator=state_update_application_contract "
            "gate=questSemanticFieldsSchema "
            "expected='questSemanticFieldConsumers.v2' "
            f"actual={semantic_fields.get('schema')!r} source={audit_path}"
        )
    semantic_validation = semantic_fields.get("validation") or {}
    if semantic_validation.get("status") != "validated":
        failure = (semantic_validation.get("failures") or [{}])[0]
        raise RuntimeError(
            "validator=state_update_application_contract "
            f"gate={failure.get('gate') or 'questSemanticFields'} "
            f"message={failure.get('message')} expected={failure.get('expected')!r} "
            f"actual={failure.get('actual')!r} "
            f"source={failure.get('sourceFile') or audit_path}"
        )
    optional_validation = (
        (semantic_fields.get("optionalObjectiveFlag") or {}).get("validation")
        or {}
    )
    if optional_validation.get("status") != "validated":
        failure = (optional_validation.get("failures") or [{}])[0]
        raise RuntimeError(
            "validator=state_update_application_contract "
            f"gate={failure.get('gate') or 'optionalObjectiveFlag'} "
            f"message={failure.get('message')} expected={failure.get('expected')!r} "
            f"actual={failure.get('actual')!r} "
            f"source={failure.get('sourceFile') or audit_path}"
        )
    source = audit.get("source") or {}
    source_checks = [
        ("gameAssembly", "gameAssemblySha256"),
        ("metadata", "metadataSha256"),
    ]
    related_files: list[dict[str, Any]] = []
    for path_key, hash_key in source_checks:
        source_text = str(source.get(path_key) or "")
        expected_hash = str(source.get(hash_key) or "").lower()
        source_path = Path(source_text)
        if not source_text or not source_path.is_file():
            raise RuntimeError(
                "validator=state_update_application_contract gate=sourceExists "
                f"expected=file actual=missing source={source_text or path_key}"
            )
        actual_hash = sha256_path(source_path)
        if actual_hash != expected_hash:
            raise RuntimeError(
                "validator=state_update_application_contract gate=sourceHash "
                f"expected={expected_hash!r} actual={actual_hash!r} source={source_path}"
            )
        related_files.append(
            {
                "kind": (
                    "original_game_binary"
                    if path_key == "gameAssembly"
                    else "original_game_metadata"
                ),
                "sourceFile": str(source_path.resolve()),
                "sha256": actual_hash,
                "relationship": "native_mission_branch_authority_contract",
            }
        )
    return {
        "source": audit_path.relative_to(ROOT).as_posix()
        if audit_path.is_relative_to(ROOT)
        else audit_path.as_posix(),
        "classification": census.get("classification"),
        "discoveryPattern": census.get("discoveryPattern") or {},
        "candidateCount": census.get("candidateCount", 0),
        "validatedCandidateCount": census.get("validatedCandidateCount", 0),
        "clientSuccessorSelectors": census.get("clientSuccessorSelectors", 0),
        "questStateLifecycleApplication": {
            **quest_state_lifecycle,
            "source": (
                audit_path.relative_to(ROOT).as_posix()
                if audit_path.is_relative_to(ROOT)
                else audit_path.as_posix()
            ),
            "relatedOriginalFiles": related_files,
        },
        "questEnableLifecycleApplication": {
            **quest_enable_lifecycle,
            "source": (
                audit_path.relative_to(ROOT).as_posix()
                if audit_path.is_relative_to(ROOT)
                else audit_path.as_posix()
            ),
            "relatedOriginalFiles": related_files,
        },
        "questStartApplication": quest_start,
        "questSucceedActionApplication": {
            **quest_succeed,
            "source": (
                audit_path.relative_to(ROOT).as_posix()
                if audit_path.is_relative_to(ROOT)
                else audit_path.as_posix()
            ),
            "relatedOriginalFiles": related_files,
        },
        "questTopologyFieldConsumers": topology_consumers,
        "allLifecycleCallsUsePacketIdentity": census.get(
            "allLifecycleCallsUsePacketIdentity", False
        ),
        "finding": census.get("finding") or "",
        "boundary": census.get("boundary") or "",
        "rows": census.get("rows") or [],
        "relatedOriginalFiles": related_files,
        "validation": validation,
    }


def load_action_extra_thread_scheduler_contract(
    audit_path: Path = DEFAULT_PROTOCOL_REGISTRY_AUDIT,
) -> dict[str, Any]:
    """Revalidate binary-derived parallel child-launch semantics."""
    validator = "action_extra_thread_scheduler_contract"
    if not audit_path.is_file():
        raise RuntimeError(
            f"validator={validator} gate=auditExists expected=file "
            f"actual=missing source={audit_path}"
        )
    audit = read_json(audit_path)
    if audit.get("_schema") != "endfieldProtocolRegistryAudit.v20":
        raise RuntimeError(
            f"validator={validator} gate=auditSchema "
            "expected='endfieldProtocolRegistryAudit.v20' "
            f"actual={audit.get('_schema')!r} source={audit_path}"
        )
    contract = audit.get("actionExtraThreadSchedulerCensus") or {}
    validation = contract.get("validation") or {}
    if validation.get("status") != "validated":
        failure = (validation.get("failures") or [{}])[0]
        raise RuntimeError(
            f"validator={validator} "
            f"gate={failure.get('gate') or 'upstreamValidation'} "
            f"message={failure.get('message')} expected={failure.get('expected')!r} "
            f"actual={failure.get('actual')!r} "
            f"source={failure.get('sourceFile') or audit_path}"
        )
    discovery = contract.get("discoveryPattern") or {}
    actual_shape = {
        "schema": contract.get("schema"),
        "classification": contract.get("classification"),
        "objectIdentityInputs": discovery.get("objectIdentityInputs"),
    }
    expected_shape = {
        "schema": "actionExtraThreadSchedulerCensus.v1",
        "classification": "typed_children_launch_as_parallel_extra_threads",
        "objectIdentityInputs": [],
    }
    if actual_shape != expected_shape:
        raise RuntimeError(
            f"validator={validator} gate=genericContractShape "
            f"expected={expected_shape!r} actual={actual_shape!r} "
            f"source={audit_path}"
        )
    writers = contract.get("extraThreadExecuteMethods") or []
    if not writers:
        raise RuntimeError(
            f"validator={validator} gate=writerMethods expected=>=1 actual=0 "
            f"source={audit_path}"
        )
    source = audit.get("source") or {}
    related_files: list[dict[str, Any]] = []
    for path_key, hash_key, kind in (
        ("gameAssembly", "gameAssemblySha256", "original_game_binary"),
        ("metadata", "metadataSha256", "original_game_metadata"),
    ):
        source_text = str(source.get(path_key) or "")
        expected_hash = str(source.get(hash_key) or "").lower()
        source_path = Path(source_text)
        if not source_text or not source_path.is_file():
            raise RuntimeError(
                f"validator={validator} gate=sourceExists expected=file "
                f"actual=missing source={source_text or path_key}"
            )
        actual_hash = sha256_path(source_path)
        if actual_hash != expected_hash:
            raise RuntimeError(
                f"validator={validator} gate=sourceHash expected={expected_hash!r} "
                f"actual={actual_hash!r} source={source_path}"
            )
        related_files.append({
            "kind": kind,
            "sourceFile": str(source_path.resolve()),
            "sha256": actual_hash,
            "relationship": "native_action_extra_thread_scheduler_authority",
        })
    return {
        **contract,
        "source": repo_path(audit_path),
        "relatedOriginalFiles": related_files,
    }


def load_levelscript_task_authority_contract(
    audit_path: Path = DEFAULT_PROTOCOL_REGISTRY_AUDIT,
) -> dict[str, Any]:
    """Validate the generic binary/protobuf identity boundary for script tasks."""
    validator = "levelscript_task_authority_contract"
    if not audit_path.is_file():
        raise RuntimeError(
            f"validator={validator} gate=auditExists expected=file "
            f"actual=missing source={audit_path}"
        )
    audit = read_json(audit_path)
    if audit.get("_schema") != "endfieldProtocolRegistryAudit.v20":
        raise RuntimeError(
            f"validator={validator} gate=auditSchema "
            "expected='endfieldProtocolRegistryAudit.v20' "
            f"actual={audit.get('_schema')!r} source={audit_path}"
        )

    expected_schemas = {
        "Proto.CS_SCENE_UPDATE_SCRIPT_TASK_PROGRESS": (
            105,
            "client_to_server",
            ["sceneNumId", "scriptId", "taskId", "objectiveValueOps"],
        ),
        "Proto.SC_SCENE_LEVEL_SCRIPT_TASK_STATE_UPDATE": (
            813,
            "server_to_client",
            ["sceneNumId", "scriptId", "taskId", "taskState"],
        ),
        "Proto.SC_SCENE_LEVEL_SCRIPT_TASK_PROGRESS_UPDATE": (
            815,
            "server_to_client",
            ["sceneNumId", "scriptId", "taskId", "conditionCompletedMap"],
        ),
        "Proto.SC_SCENE_LEVEL_SCRIPT_TASK_START_FINISH": (
            816,
            "server_to_client",
            ["sceneNumId", "scriptId", "taskId"],
        ),
    }
    schemas = {
        str(row.get("type") or ""): row
        for row in audit.get("selectedSchemas") or []
        if isinstance(row, dict) and row.get("type")
    }
    messages: list[dict[str, Any]] = []
    for schema_name, (message_id, direction, field_names) in expected_schemas.items():
        row = schemas.get(schema_name)
        actual = {
            "messageId": row.get("messageId") if row else None,
            "direction": row.get("direction") if row else None,
            "fields": [
                str(field.get("name") or "")
                for field in (row or {}).get("fields") or []
                if isinstance(field, dict)
            ],
            "idMatches": row.get("idMatches") if row else None,
        }
        expected = {
            "messageId": message_id,
            "direction": direction,
            "fields": field_names,
            "idMatches": True,
        }
        if actual != expected:
            raise RuntimeError(
                f"validator={validator} gate=taskPacketSchema "
                f"message={schema_name} expected={expected!r} actual={actual!r} "
                f"source={audit_path}"
            )
        if {"missionId", "questId", "storyId"} & set(actual["fields"]):
            raise RuntimeError(
                f"validator={validator} gate=noMissionQuestStoryIdentity "
                f"message={schema_name} expected=[] actual={actual['fields']!r} "
                f"source={audit_path}"
            )
        messages.append({
            "type": schema_name,
            "messageId": message_id,
            "direction": direction,
            "fields": field_names,
        })

    native_paths = audit.get("nativeTaskPaths") or {}
    expected_native_paths = {
        "conditionResultChanged": None,
        "sendProgress": 105,
        "stateUpdate": 813,
        "progressUpdate": 815,
        "conditionCompletionChanged": 815,
        "startFinish": 816,
        "scriptSetDone": 823,
    }
    for path_name, message_id in expected_native_paths.items():
        row = native_paths.get(path_name)
        actual_id = row.get("messageId") if isinstance(row, dict) else None
        if not isinstance(row, dict) or not row.get("symbol") or (
            message_id is not None and actual_id != message_id
        ):
            raise RuntimeError(
                f"validator={validator} gate=nativeTaskPath path={path_name} "
                f"expected={{'symbol': 'nonempty', 'messageId': {message_id!r}}} "
                f"actual={{'symbol': {(row or {}).get('symbol')!r}, "
                f"'messageId': {actual_id!r}}} source={audit_path}"
            )

    source = audit.get("source") or {}
    related_files: list[dict[str, Any]] = []
    for path_key, hash_key, kind in (
        ("gameAssembly", "gameAssemblySha256", "original_game_binary"),
        ("metadata", "metadataSha256", "original_game_metadata"),
    ):
        source_text = str(source.get(path_key) or "")
        expected_hash = str(source.get(hash_key) or "").lower()
        source_path = Path(source_text)
        if not source_text or not source_path.is_file():
            raise RuntimeError(
                f"validator={validator} gate=sourceExists expected=file "
                f"actual=missing source={source_text or path_key}"
            )
        actual_hash = sha256_path(source_path)
        if actual_hash != expected_hash:
            raise RuntimeError(
                f"validator={validator} gate=sourceHash "
                f"expected={expected_hash!r} actual={actual_hash!r} "
                f"source={source_path}"
            )
        related_files.append({
            "kind": kind,
            "sourceFile": str(source_path.resolve()),
            "sha256": actual_hash,
            "relationship": "native_levelscript_task_authority_contract",
        })

    return {
        "schema": "levelScriptTaskAuthority.v1",
        "source": repo_path(audit_path),
        "classification": "server_selected_scene_script_task_identity",
        "identityFields": ["sceneNumId", "scriptId", "taskId"],
        "messages": messages,
        "nativePaths": {
            name: native_paths[name] for name in expected_native_paths
        },
        "missionQuestIdentityFields": [],
        "relatedOriginalFiles": related_files,
        "validation": {
            "status": "validated",
            "validator": validator,
            "packetSchemas": len(messages),
            "nativePaths": len(expected_native_paths),
        },
        "finding": (
            "The current client and protobuf schemas identify LevelScript task "
            "traffic only by scene, script, task, and condition/progress data. "
            "No validated packet co-carries missionId, questId, or Story identity."
        ),
        "evidenceBoundary": (
            "This proves a server-authored LevelScript task lifecycle and exact "
            "task identity. It does not identify a MissionRuntime owner, select a "
            "Story branch, or order playback files."
        ),
    }


def load_levelscript_task_lifecycle_contract(
    audit_path: Path = DEFAULT_PROTOCOL_REGISTRY_AUDIT,
) -> dict[str, Any]:
    """Revalidate the current-binary generic task-condition lifecycle."""
    validator = "levelscript_task_lifecycle_contract"
    if not audit_path.is_file():
        raise RuntimeError(
            f"validator={validator} gate=auditExists expected=file "
            f"actual=missing source={audit_path}"
        )
    audit = read_json(audit_path)
    if audit.get("_schema") != "endfieldProtocolRegistryAudit.v20":
        raise RuntimeError(
            f"validator={validator} gate=auditSchema "
            "expected='endfieldProtocolRegistryAudit.v20' "
            f"actual={audit.get('_schema')!r} source={audit_path}"
        )
    contract = audit.get("levelScriptTaskLifecycle") or {}
    expected = {
        "schema": "levelScriptTaskLifecycle.v1",
        "classification": "generic_server_selected_task_condition_lifecycle",
        "status": "validated",
        "states": {"None": 0, "Processing": 1, "Completed": 2},
        "taskTypes": {
            "None": 0,
            "Main": 1,
            "Extra": 2,
            "Fail": 3,
            "Custom": 4,
        },
        "stateArgumentForwarding": True,
        "conditionProgressSender": (
            "Beyond.Gameplay.GameplayNetwork.SendLevelScriptUpdateTaskProgress"
        ),
        "conditionIdentityFieldReads": [
            "levelScriptPtr",
            "levelNum",
            "taskKey",
            "conditionId",
        ],
    }
    actual = {
        "schema": contract.get("schema"),
        "classification": contract.get("classification"),
        "status": (contract.get("validation") or {}).get("status"),
        "states": contract.get("scriptTaskStateEnum"),
        "taskTypes": contract.get("levelScriptTaskTypeEnum"),
        "stateArgumentForwarding": contract.get("stateArgumentForwarding"),
        "conditionProgressSender": contract.get("conditionProgressSender"),
        "conditionIdentityFieldReads": contract.get(
            "conditionIdentityFieldReads"
        ),
    }
    if actual != expected:
        raise RuntimeError(
            f"validator={validator} gate=contractShape "
            f"expected={expected!r} actual={actual!r} source={audit_path}"
        )
    processing_calls = contract.get("processingConditionCallCount")
    if not isinstance(processing_calls, int) or processing_calls < 1:
        raise RuntimeError(
            f"validator={validator} gate=processingConditionCallCount "
            f"expected=>=1 actual={processing_calls!r} source={audit_path}"
        )
    expected_operations = [
        "Beyond.Gameplay.GameCondition+ResultChange..ctor",
        "System.Delegate.Combine",
        "Beyond.Gameplay.GameCondition.Activate",
        "Beyond.Gameplay.GameCondition.BindingEvent",
    ]
    if contract.get("conditionProcessingOperations") != expected_operations:
        raise RuntimeError(
            f"validator={validator} gate=conditionProcessingOperations "
            f"expected={expected_operations!r} "
            f"actual={contract.get('conditionProcessingOperations')!r} "
            f"source={audit_path}"
        )
    source = audit.get("source") or {}
    related_files: list[dict[str, Any]] = []
    for path_key, hash_key, kind in (
        ("gameAssembly", "gameAssemblySha256", "original_game_binary"),
        ("metadata", "metadataSha256", "original_game_metadata"),
    ):
        source_text = str(source.get(path_key) or "")
        expected_hash = str(source.get(hash_key) or "").lower()
        source_path = Path(source_text)
        if not source_text or not source_path.is_file():
            raise RuntimeError(
                f"validator={validator} gate=sourceExists expected=file "
                f"actual=missing source={source_text or path_key}"
            )
        actual_hash = sha256_path(source_path)
        if actual_hash != expected_hash:
            raise RuntimeError(
                f"validator={validator} gate=sourceHash "
                f"expected={expected_hash!r} actual={actual_hash!r} "
                f"source={source_path}"
            )
        related_files.append({
            "kind": kind,
            "sourceFile": str(source_path.resolve()),
            "sha256": actual_hash,
            "relationship": "generic_levelscript_task_lifecycle",
        })
    return {
        **contract,
        "source": repo_path(audit_path),
        "relatedOriginalFiles": related_files,
    }


def load_levelscript_start_policy_contract(
    audit_path: Path = DEFAULT_PROTOCOL_REGISTRY_AUDIT,
) -> dict[str, Any]:
    """Revalidate the original binary behind generic SameWithActive semantics."""
    validator = "levelscript_start_policy_contract"
    if not audit_path.is_file():
        raise RuntimeError(
            f"validator={validator} gate=auditExists expected=file "
            f"actual=missing source={audit_path}"
        )
    audit = read_json(audit_path)
    if audit.get("_schema") != "endfieldProtocolRegistryAudit.v20":
        raise RuntimeError(
            f"validator={validator} gate=auditSchema "
            "expected='endfieldProtocolRegistryAudit.v20' "
            f"actual={audit.get('_schema')!r} source={audit_path}"
        )
    contract = audit.get("levelScriptStartPolicy") or {}
    validation = contract.get("validation") or {}
    if validation.get("status") != "validated":
        failure = (validation.get("failures") or [{}])[0]
        raise RuntimeError(
            f"validator={validator} "
            f"gate={failure.get('gate') or 'upstreamValidation'} "
            f"message={failure.get('message')} "
            f"expected={failure.get('expected')!r} "
            f"actual={failure.get('actual')!r} "
            f"source={failure.get('sourceFile') or audit_path}"
        )
    discovery = contract.get("discoveryPattern") or {}
    actual_shape = {
        "schema": contract.get("schema"),
        "classification": contract.get("classification"),
        "objectIdentityInputs": discovery.get("objectIdentityInputs"),
    }
    expected_shape = {
        "schema": "levelScriptStartPolicy.v1",
        "classification": "same_with_active_enters_prestart_when_active",
        "objectIdentityInputs": [],
    }
    if actual_shape != expected_shape:
        raise RuntimeError(
            f"validator={validator} gate=genericContractShape "
            f"expected={expected_shape!r} actual={actual_shape!r} "
            f"source={audit_path}"
        )

    source = audit.get("source") or {}
    related_files: list[dict[str, Any]] = []
    for path_key, hash_key, kind in (
        ("gameAssembly", "gameAssemblySha256", "original_game_binary"),
        ("metadata", "metadataSha256", "original_game_metadata"),
    ):
        source_text = str(source.get(path_key) or "")
        expected_hash = str(source.get(hash_key) or "").lower()
        source_path = Path(source_text)
        if not source_text or not source_path.is_file():
            raise RuntimeError(
                f"validator={validator} gate=sourceExists expected=file "
                f"actual=missing source={source_text or path_key}"
            )
        actual_hash = sha256_path(source_path)
        if actual_hash != expected_hash:
            raise RuntimeError(
                f"validator={validator} gate=sourceHash "
                f"expected={expected_hash!r} actual={actual_hash!r} "
                f"source={source_path}"
            )
        related_files.append({
            "kind": kind,
            "sourceFile": str(source_path.resolve()),
            "sha256": actual_hash,
            "relationship": "native_levelscript_start_policy_contract",
        })

    return {
        "schema": contract.get("schema"),
        "source": repo_path(audit_path),
        "classification": contract.get("classification"),
        "discoveryPattern": discovery,
        "enumValues": contract.get("enumValues") or {},
        "methods": contract.get("methods") or {},
        "activeStateGate": contract.get("activeStateGate") or {},
        "doneGate": contract.get("doneGate") or {},
        "startTypeGates": contract.get("startTypeGates") or {},
        "startAreaGate": contract.get("startAreaGate") or {},
        "preStartTransition": contract.get("preStartTransition") or {},
        "finding": contract.get("finding") or "",
        "evidenceBoundary": contract.get("boundary") or "",
        "relatedOriginalFiles": related_files,
        "validation": validation,
    }


def load_levelscript_manual_self_control_contract(
    audit_path: Path = DEFAULT_PROTOCOL_REGISTRY_AUDIT,
) -> dict[str, Any]:
    """Revalidate the binary-derived current-context ManualStart contract."""
    validator = "levelscript_manual_self_control_contract"
    if not audit_path.is_file():
        raise RuntimeError(
            f"validator={validator} gate=auditExists expected=file "
            f"actual=missing source={audit_path}"
        )
    audit = read_json(audit_path)
    if audit.get("_schema") != "endfieldProtocolRegistryAudit.v20":
        raise RuntimeError(
            f"validator={validator} gate=auditSchema "
            "expected='endfieldProtocolRegistryAudit.v20' "
            f"actual={audit.get('_schema')!r} source={audit_path}"
        )
    contract = audit.get("levelScriptManualSelfControl") or {}
    validation = contract.get("validation") or {}
    if validation.get("status") != "validated":
        failure = (validation.get("failures") or [{}])[0]
        raise RuntimeError(
            f"validator={validator} "
            f"gate={failure.get('gate') or 'upstreamValidation'} "
            f"message={failure.get('message')} "
            f"expected={failure.get('expected')!r} "
            f"actual={failure.get('actual')!r} "
            f"source={failure.get('sourceFile') or audit_path}"
        )
    discovery = contract.get("discoveryPattern") or {}
    actual_shape = {
        "schema": contract.get("schema"),
        "classification": contract.get("classification"),
        "serializedObjectInputs": discovery.get("serializedObjectInputs"),
    }
    expected_shape = {
        "schema": "levelScriptManualSelfControl.v1",
        "classification": "current_context_manual_start_self_target",
        "serializedObjectInputs": [],
    }
    if actual_shape != expected_shape:
        raise RuntimeError(
            f"validator={validator} gate=genericContractShape "
            f"expected={expected_shape!r} actual={actual_shape!r} "
            f"source={audit_path}"
        )

    source = audit.get("source") or {}
    related_files: list[dict[str, Any]] = []
    for path_key, hash_key, kind in (
        ("gameAssembly", "gameAssemblySha256", "original_game_binary"),
        ("metadata", "metadataSha256", "original_game_metadata"),
    ):
        source_text = str(source.get(path_key) or "")
        expected_hash = str(source.get(hash_key) or "").lower()
        source_path = Path(source_text)
        if not source_text or not source_path.is_file():
            raise RuntimeError(
                f"validator={validator} gate=sourceExists expected=file "
                f"actual=missing source={source_text or path_key}"
            )
        actual_hash = sha256_path(source_path)
        if actual_hash != expected_hash:
            raise RuntimeError(
                f"validator={validator} gate=sourceHash "
                f"expected={expected_hash!r} actual={actual_hash!r} "
                f"source={source_path}"
            )
        related_files.append({
            "kind": kind,
            "sourceFile": str(source_path.resolve()),
            "sha256": actual_hash,
            "relationship": "native_levelscript_manual_self_control_contract",
        })

    return {
        "schema": contract.get("schema"),
        "source": repo_path(audit_path),
        "classification": contract.get("classification"),
        "discoveryPattern": discovery,
        "serializedOperandContract": (
            contract.get("serializedOperandContract") or {}
        ),
        "paramSourceValues": contract.get("paramSourceValues") or {},
        "runtimeStateValues": contract.get("runtimeStateValues") or {},
        "actionFields": contract.get("actionFields") or {},
        "methods": contract.get("methods") or {},
        "executeFlow": contract.get("executeFlow") or {},
        "manualStartFlow": contract.get("manualStartFlow") or {},
        "finding": contract.get("finding") or "",
        "evidenceBoundary": contract.get("boundary") or "",
        "relatedOriginalFiles": related_files,
        "validation": validation,
    }


def load_levelscript_activation_control_contract(
    audit_path: Path = DEFAULT_PROTOCOL_REGISTRY_AUDIT,
) -> dict[str, Any]:
    """Revalidate server-state and SubGame ManualStart binary paths."""
    validator = "levelscript_activation_control_contract"
    if not audit_path.is_file():
        raise RuntimeError(
            f"validator={validator} gate=auditExists expected=file "
            f"actual=missing source={audit_path}"
        )
    audit = read_json(audit_path)
    if audit.get("_schema") != "endfieldProtocolRegistryAudit.v20":
        raise RuntimeError(
            f"validator={validator} gate=auditSchema "
            "expected='endfieldProtocolRegistryAudit.v20' "
            f"actual={audit.get('_schema')!r} source={audit_path}"
        )
    contract = audit.get("levelScriptActivationControl") or {}
    validation = contract.get("validation") or {}
    if validation.get("status") != "validated":
        failure = (validation.get("failures") or [{}])[0]
        raise RuntimeError(
            f"validator={validator} "
            f"gate={failure.get('gate') or 'upstreamValidation'} "
            f"message={failure.get('message')} "
            f"expected={failure.get('expected')!r} "
            f"actual={failure.get('actual')!r} "
            f"source={failure.get('sourceFile') or audit_path}"
        )
    discovery = contract.get("discoveryPattern") or {}
    expected_inputs = [
        "SubGameInstanceData.id",
        "SubGameInstanceData.bindScriptId",
    ]
    actual_shape = {
        "schema": contract.get("schema"),
        "classification": contract.get("classification"),
        "serializedObjectInputs": discovery.get("serializedObjectInputs"),
    }
    expected_shape = {
        "schema": "levelScriptActivationControl.v6",
        "classification": "server_state_subgame_and_runtime_request_paths",
        "serializedObjectInputs": expected_inputs,
    }
    if actual_shape != expected_shape:
        raise RuntimeError(
            f"validator={validator} gate=genericContractShape "
            f"expected={expected_shape!r} actual={actual_shape!r} "
            f"source={audit_path}"
        )

    source = audit.get("source") or {}
    related_files: list[dict[str, Any]] = []
    for path_key, hash_key, kind in (
        ("gameAssembly", "gameAssemblySha256", "original_game_binary"),
        ("metadata", "metadataSha256", "original_game_metadata"),
    ):
        source_text = str(source.get(path_key) or "")
        expected_hash = str(source.get(hash_key) or "").lower()
        source_path = Path(source_text)
        if not source_text or not source_path.is_file():
            raise RuntimeError(
                f"validator={validator} gate=sourceExists expected=file "
                f"actual=missing source={source_text or path_key}"
            )
        actual_hash = sha256_path(source_path)
        if actual_hash != expected_hash:
            raise RuntimeError(
                f"validator={validator} gate=sourceHash "
                f"expected={expected_hash!r} actual={actual_hash!r} "
                f"source={source_path}"
            )
        related_files.append({
            "kind": kind,
            "sourceFile": str(source_path.resolve()),
            "sha256": actual_hash,
            "relationship": "native_levelscript_activation_control_contract",
        })

    return {
        "schema": contract.get("schema"),
        "source": repo_path(audit_path),
        "classification": contract.get("classification"),
        "discoveryPattern": discovery,
        "messageIds": contract.get("messageIds") or {},
        "messageSchemas": contract.get("messageSchemas") or {},
        "fieldOffsets": contract.get("fieldOffsets") or {},
        "methods": contract.get("methods") or {},
        "publicStateFlow": contract.get("publicStateFlow") or {},
        "publicStateSourceFlow": (
            contract.get("publicStateSourceFlow") or {}
        ),
        "subGameInteractionFlow": (
            contract.get("subGameInteractionFlow") or {}
        ),
        "manualStartDirectCallers": (
            contract.get("manualStartDirectCallers") or []
        ),
        "directCallers": contract.get("directCallers") or {},
        "clientRequestFlow": contract.get("clientRequestFlow") or {},
        "activeReceiverFlow": contract.get("activeReceiverFlow") or {},
        "activationSelectorFlow": (
            contract.get("activationSelectorFlow") or {}
        ),
        "activeAreaFlow": contract.get("activeAreaFlow") or {},
        "finding": contract.get("finding") or "",
        "evidenceBoundary": contract.get("boundary") or "",
        "relatedOriginalFiles": related_files,
        "validation": validation,
    }


POST_PLAYBACK_VARIABLE_LISTENER_FIELDS = {
    "blackboardKeyFilter": "blackboard",
    "propertyKeyFilter": "property",
}


def build_post_playback_variable_bridge_audit(
    native_story_playback_index: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Census exact Story setter-to-listener candidates without promoting them.

    The installed ActionBase formatter identifies the three setter classes and
    their MemoryPack runtime shape carries a key/value pair. Exact native event
    payloads independently identify property and blackboard listener keys. A
    candidate requires the same level, same LevelScript, and exact key; class
    names, file order, Story names, and numeric ids never participate.

    Even a candidate remains context-only until the installed generic
    ``Set<T>.Execute`` body proves which notification family it emits. The
    current build has no candidate, which closes this route more strongly: no
    execution-semantics assumption could create a Story-to-Story edge.
    """
    listeners: dict[tuple[str, str, str], dict[tuple[Any, ...], dict[str, Any]]] = (
        defaultdict(dict)
    )
    setters: dict[tuple[Any, ...], dict[str, Any]] = {}
    occurrence_count = 0
    for story_key, occurrences in sorted(native_story_playback_index.items()):
        for occurrence in occurrences:
            occurrence_count += 1
            level_id = str(occurrence.get("levelId") or "")
            script_id = str(occurrence.get("scriptId") or "")
            source_file = str(occurrence.get("sourceFile") or "")
            playback_local_id = occurrence.get("localId")
            if not level_id or not script_id or not source_file:
                continue
            for owner in occurrence.get("nativeEventOwners") or []:
                if not isinstance(owner, dict):
                    continue
                detail = owner.get("eventDetail") or {}
                if (
                    owner.get("status") not in {
                        "exact_serialized_control_path",
                        "exact_serialized_control_path_equivalent_duplicates",
                        "exact_serialized_control_path_runtime_shadowing",
                    }
                    or detail.get("payloadSchemaStatus")
                    != "exact_current_build_memorypack_fields"
                ):
                    continue
                for field, listener_kind in (
                    POST_PLAYBACK_VARIABLE_LISTENER_FIELDS.items()
                ):
                    variable_key = str(detail.get(field) or "")
                    if not variable_key:
                        continue
                    listener = compact_dict({
                        "storyKey": story_key,
                        "listenerKind": listener_kind,
                        "eventName": str(owner.get("headerName") or ""),
                        "headerLocalId": owner.get("headerLocalId"),
                        "levelId": level_id,
                        "scriptId": script_id,
                        "variableKey": variable_key,
                        "sourceFile": source_file,
                    })
                    signature = (
                        story_key,
                        listener_kind,
                        listener.get("eventName"),
                        listener.get("headerLocalId"),
                        source_file,
                    )
                    listeners[(level_id, script_id, variable_key)][signature] = (
                        listener
                    )
                if not isinstance(playback_local_id, int):
                    continue
                control = exact_native_receiver_post_playback_control(
                    owner,
                    story_key=story_key,
                    playback_local_id=playback_local_id,
                    source_file=source_file,
                )
                for action in control.get("actions") or []:
                    action_name = str(action.get("actionName") or "")
                    if action_name not in POST_PLAYBACK_VARIABLE_SETTER_ACTIONS:
                        continue
                    keys = sorted({
                        str(value)
                        for value in action.get("texts") or []
                        if str(value) and not str(value).startswith(("$", "#"))
                    })
                    if len(keys) != 1:
                        continue
                    variable_key = keys[0]
                    setter = {
                        "storyKey": story_key,
                        "levelId": level_id,
                        "scriptId": script_id,
                        "playbackLocalId": playback_local_id,
                        "setterLocalId": action.get("localId"),
                        "setterAction": action_name,
                        "variableKey": variable_key,
                        "sourceFile": source_file,
                    }
                    signature = (
                        story_key,
                        level_id,
                        script_id,
                        playback_local_id,
                        action.get("localId"),
                        action_name,
                        variable_key,
                        source_file,
                    )
                    setters[signature] = setter

    setter_rows: list[dict[str, Any]] = []
    exact_match_count = 0
    cross_story_match_count = 0
    for setter in setters.values():
        matches = sorted(
            listeners.get((
                setter["levelId"],
                setter["scriptId"],
                setter["variableKey"],
            ), {}).values(),
            key=lambda row: (
                str(row.get("storyKey") or ""),
                str(row.get("listenerKind") or ""),
                int(row.get("headerLocalId") or -1),
            ),
        )
        exact_match_count += len(matches)
        cross_story_matches = [
            match
            for match in matches
            if match.get("storyKey") != setter.get("storyKey")
        ]
        cross_story_match_count += len(cross_story_matches)
        setter_rows.append({
            **setter,
            "exactListenerMatches": matches,
            "crossStoryListenerMatchCount": len(cross_story_matches),
            "orderEvidence": False,
            "missionOwnershipEvidence": False,
        })
    setter_rows.sort(key=lambda row: (
        str(row.get("levelId") or ""),
        str(row.get("scriptId") or ""),
        int(row.get("setterLocalId") or -1),
        str(row.get("storyKey") or ""),
    ))
    listener_rows = [
        row
        for bucket in listeners.values()
        for row in bucket.values()
    ]
    return {
        "schema": "postPlaybackVariableBridgeAudit.v1",
        "summary": {
            "nativeStoryKeys": len(native_story_playback_index),
            "nativePlaybackOccurrences": occurrence_count,
            "exactVariableListenerSelectors": len(listeners),
            "exactVariableListenerRows": len(listener_rows),
            "postPlaybackVariableSetters": len(setter_rows),
            "exactSetterListenerMatches": exact_match_count,
            "crossStorySetterListenerMatches": cross_story_match_count,
            "setterActions": dict(sorted(Counter(
                row["setterAction"] for row in setter_rows
            ).items())),
            "listenerKinds": dict(sorted(Counter(
                row["listenerKind"] for row in listener_rows
            ).items())),
        },
        "status": (
            "closed_no_exact_same_script_key_match"
            if exact_match_count == 0
            else "context_only_execute_notification_family_unproven"
        ),
        "setters": setter_rows,
        "evidenceBoundary": (
            "The installed formatter and exact MemoryPack payloads prove the "
            "setter classes, serialized keys, listener classes, and listener "
            "keys. They do not prove that generic Set<T>.Execute emits the "
            "property or blackboard notification family. No current setter "
            "matches any exact same-level, same-script, same-key Story listener, "
            "so this route creates no ownership, branch, or order edge."
        ),
        "usesOcrOrManualOrder": False,
    }


def build_story_binding_coverage(
    pipeline_index: dict[str, Any],
    pipeline_index_path: Path,
    story_data_root: Path,
    language: str,
    report_root: Path,
    subgame_table_path: Path | None = None,
    activity_stage_table_path: Path | None = None,
    game_mechanic_condition_table_path: Path | None = None,
    dungeon_table_path: Path | None = None,
    text_vo_id_table_path: Path | None = DEFAULT_TEXT_VO_ID_TABLE,
    lua_consumer_audit_path: Path = DEFAULT_LUA_CONSUMER_REFERENCE_AUDIT,
    cutscene_case_audit_paths: Iterable[Path] = (
        DEFAULT_CUTSCENE_CASE_RESOLUTION_AUDIT,
    ),
    *,
    native_story_playback_index: dict[str, list[dict[str, Any]]] | None = None,
    callserver_callback_audit: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Write a unique-file Story-to-pipeline coverage audit.

    Connection evidence can place one Story file on more than one mission shell,
    so unique files, mission placements, and raw evidence rows are counted
    separately. Only generated original-data connections are accepted here;
    OCR/manual/gameplay-observed ordering never contributes coverage.
    """
    language = language.upper()
    language_root = story_data_root / language
    story_index_path = language_root / "index.json"
    mission_sidecar_root = language_root / "mission"
    if not story_index_path.is_file() or not mission_sidecar_root.is_dir():
        return None

    story_index = read_json(story_index_path)
    mission_ids = {
        str(row.get("id") or "")
        for row in pipeline_index.get("missions") or []
        if isinstance(row, dict) and row.get("id")
    }
    all_index_rows: dict[str, dict[str, Any]] = {}
    all_story_rows: dict[str, dict[str, Any]] = {}
    story_rows: dict[str, dict[str, Any]] = {}
    for row in story_index.get("entries") or []:
        if not isinstance(row, dict):
            continue
        key = str(row.get("k") or "")
        kind = str(row.get("d") or "")
        mission_id = str(row.get("m") or "")
        if key:
            normalized_row = {
                "key": key,
                "kind": kind,
                "missionId": mission_id,
                "preview": str(row.get("p") or ""),
            }
            all_index_rows[key] = normalized_row
        if key and kind in PIPELINE_STORY_KINDS:
            all_story_rows[key] = normalized_row
            if mission_id in mission_ids:
                story_rows[key] = normalized_row

    # Exact authored non-mission content. Table-only continuation/topic rows
    # remain outside the pipeline denominator as before. A freshness-checked
    # exact runtime consumers are admitted explicitly so their Story trigger
    # cards can be classified even though their nominal buckets are not
    # MissionRuntime missions.
    non_mission_content = combined_non_mission_content_keys(
        DEFAULT_TABLE_ROOT
    )
    for key, evidence in non_mission_content.items():
        if (
            evidence.get("evidenceKind")
            in PIPELINE_VISIBLE_NON_MISSION_EVIDENCE_KINDS
            and key in all_story_rows
            and key not in story_rows
        ):
            story_rows[key] = {
                **all_story_rows[key],
                "pipelineOwnerStatus": "non_mission_content",
            }

    connected_keys: set[str] = set()
    connected_cross_owner_keys: set[str] = set()
    pipeline_owned_story_keys = set(story_rows)
    connected_by_mission: dict[str, set[str]] = defaultdict(set)
    relation_counts: Counter[str] = Counter()
    evidence_tier_counts: Counter[str] = Counter()
    connected_keys_by_evidence_tier: dict[str, set[str]] = defaultdict(set)
    evidence_row_count = 0
    native_playback_unscoped: set[str] = set()
    native_playback_event_keys: dict[str, set[str]] = defaultdict(set)
    native_playback_without_named_event: set[str] = set()
    unresolved_timeline_containment: set[str] = set()
    unresolved_dialog_tree_containment: set[str] = set()
    unlinked_dialog_tree_containment: set[str] = set()
    unresolved_dialog_tree_left_subtitle: set[str] = set()
    unlinked_dialog_tree_left_subtitle: set[str] = set()
    unresolved_dialog_tree_story_playback: set[str] = set()
    unlinked_definition_only: set[str] = set()
    mission_state_dependency_keys: set[str] = set()
    mission_state_dependency_cross_owner_keys: set[str] = set()
    mission_state_dependency_placements: set[tuple[str, str]] = set()
    mission_state_dependency_rows: list[dict[str, Any]] = []
    missionless_subgames_by_script = load_missionless_subgames_by_script(subgame_table_path)
    missionless_subgame_ids = {
        row["subGameId"]
        for rows in missionless_subgames_by_script.values()
        for row in rows
    }
    subgame_cross_references = load_subgame_cross_references(
        missionless_subgame_ids,
        activity_stage_table_path,
        game_mechanic_condition_table_path,
        dungeon_table_path,
    )
    missionless_subgame_nodes: dict[str, dict[str, Any]] = {}
    missionless_native_runtime_nodes: dict[str, dict[str, Any]] = {}
    native_receiver_gate_cache: dict[tuple[str, int], dict[str, Any]] = {}
    story_trigger_routes: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    context_only_trigger_route_keys: set[str] = set()
    definition_only_interactive_config_keys: set[str] = set()
    sidecars_read = 0
    lua_playback_evidence = load_lua_story_playback_evidence(
        lua_consumer_audit_path,
        cutscene_case_audit_paths,
    )
    cinematic_contract = lua_playback_evidence.get("runtimeHandleContract") or {}
    cinematic_report = str(cinematic_contract.get("report") or "")
    cinematic_producers_by_action: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for producer_route in cinematic_contract.get("actionProducerRoutes") or []:
        action_type = str(producer_route.get("actionType") or "")
        if action_type:
            cinematic_producers_by_action[action_type].append(producer_route)

    def add_trigger_route(route: dict[str, Any] | None) -> None:
        if not route:
            return
        key = str(route.get("storyKey") or "")
        if not key:
            return
        matched_producers: list[dict[str, Any]] = []
        for action_name in route.get("actionNames") or []:
            for producer in cinematic_producers_by_action.get(
                str(action_name),
                [],
            ):
                compact = {
                    field: producer.get(field)
                    for field in (
                        "actionType",
                        "actionFullType",
                        "actionMethod",
                        "actionToken",
                        "actionVa",
                        "producerType",
                        "producerMethod",
                        "producerToken",
                        "producerVa",
                    )
                    if producer.get(field) not in (None, "")
                }
                if compact not in matched_producers:
                    matched_producers.append(compact)
        if matched_producers:
            route["nativeCinematicProducerRoutes"] = matched_producers
            route["sourceFiles"] = _unique_route_strings(
                route.get("sourceFiles"),
                cinematic_report,
            )
        signature = json.dumps(
            route,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        story_trigger_routes[key][signature] = route

    for call_site in lua_playback_evidence["acceptedExactPlaybackCalls"]:
        mission_id = call_site.get("missionId")
        quest_id = call_site.get("questId")
        table_source = str(call_site.get("tableSourcePath") or "")
        has_table_owner = bool(table_source and (mission_id or quest_id))
        lua_steps: list[dict[str, Any]] = []
        if has_table_owner:
            lua_steps.extend([
                {
                    "kind": "quest" if quest_id else "mission",
                    "id": quest_id or mission_id,
                },
                {
                    "kind": "originalTableRow",
                    "id": f"{call_site['table']}:{call_site['tableKey']}",
                    "summaries": [
                        f"{call_site['tableField']} = {call_site['storyKey']}",
                        f"SHA-256 {call_site['tableSourceSha256']}",
                    ],
                },
            ])
        lua_steps.extend([
            {
                "kind": "luaController",
                "id": call_site["luaFile"],
                "phase": call_site["phase"],
                "summaries": [
                    f"line {call_site['luaLine']}",
                    f"SHA-256 {call_site['luaSourceSha256']}",
                ],
            },
            {
                "kind": "nativePlayback",
                "id": call_site["nativeEntry"],
            },
        ])
        add_trigger_route({
            "storyKey": call_site["storyKey"],
            "relation": (
                "lua_table_controller_playback"
                if has_table_owner
                else "lua_controller_playback"
            ),
            "causality": "context" if has_table_owner else "playback_owner_unresolved",
            "direction": "playback",
            "scope": "quest" if quest_id else ("mission" if mission_id else "phase"),
            "phase": call_site["phase"],
            "evidenceTier": "direct",
            "confidence": (
                "corpus_scanned_shipped_lua_table_row_plus_native_entry"
                if has_table_owner
                else "corpus_scanned_shipped_lua_literal_plus_native_entry"
            ),
            "ownerStatus": "connected" if has_table_owner else "unresolved",
            "questTriggerStatus": (
                "exact_same_table_row_identity"
                if has_table_owner
                else "no_mission_or_quest_identity_serialized"
            ),
            "missionId": mission_id,
            "questId": quest_id,
            "serverExchange": False,
            "luaFile": call_site["luaFile"],
            "luaSourcePath": call_site["luaSourcePath"],
            "luaSourceSha256": call_site["luaSourceSha256"],
            "luaLine": call_site["luaLine"],
            "luaSymbol": call_site["luaSymbol"],
            "luaCall": call_site["luaCall"],
            "nativeEntry": call_site["nativeEntry"],
            "auditReport": call_site["auditReport"],
            "auditSha256": call_site["auditSha256"],
            "table": call_site.get("table"),
            "tableKey": call_site.get("tableKey"),
            "tableField": call_site.get("tableField"),
            "tableLookupKeyExpression": call_site.get("tableLookupKeyExpression"),
            "tableSourceSha256": call_site.get("tableSourceSha256"),
            "sourceFiles": [
                call_site["luaFile"],
                *([table_source] if table_source else []),
                call_site["auditReport"],
            ],
            "note": call_site["note"],
            "steps": lua_steps,
        })

    root_playback_alias_rows = [
        row
        for row in story_root_playback_aliases()
        if row["playableAssetStoryKey"] in story_rows
    ]
    for alias in root_playback_alias_rows:
        root_key = alias["rootStoryKey"]
        playable_key = alias["playableAssetStoryKey"]
        add_trigger_route({
            "storyKey": playable_key,
            "relation": "cutscene_root_playback_alias",
            "causality": "playback_alias_owner_unresolved",
            "direction": "playback",
            "scope": "cutscene_root",
            "evidenceTier": "direct",
            "confidence":
                "exact_serialized_root_director_plus_native_playback",
            "ownerStatus": "unresolved",
            "questTriggerStatus":
                "no_mission_or_quest_selector_recovered",
            "missionId": None,
            "questId": None,
            "serverExchange": False,
            "rootStoryKey": root_key,
            "nativeMappingId": alias["nativeMappingId"],
            "auditReport": alias["evidenceReport"],
            "sourceFiles": [
                value
                for value in (
                    alias["directorObject"].get("source"),
                    alias["evidenceReport"],
                )
                if value
            ],
            "note": (
                "The exact CutsceneRoot._director PPtr lands on the "
                "PlayableDirector whose asset is this Story key, and the "
                "current native TimelineHandle.Play path executes that "
                "director. This is a root playback alias, not Story order or "
                "mission ownership."
            ),
            "steps": [
                {
                    "kind": "story_root",
                    "id": root_key,
                },
                {
                    "kind": "native_action",
                    "id": "CutsceneRoot._director -> TimelineHandle.Play",
                },
                {
                    "kind": "story",
                    "id": playable_key,
                },
            ],
        })

    for mission_id in sorted(mission_ids):
        sidecar_path = mission_sidecar_root / f"{mission_id}.json"
        if not sidecar_path.is_file():
            continue
        payload = read_json(sidecar_path)
        flow = payload.get("flow") if isinstance(payload, dict) else None
        if not isinstance(flow, dict):
            continue
        sidecars_read += 1
        for row in flow.get("missionStateStoryDependencies") or []:
            if not isinstance(row, dict):
                continue
            key = str(row.get("key") or "")
            if key not in all_story_rows:
                continue
            mission_state_dependency_keys.add(key)
            if key not in pipeline_owned_story_keys:
                mission_state_dependency_cross_owner_keys.add(key)
            mission_state_dependency_placements.add((mission_id, key))
            mission_state_dependency_rows.append({
                **row,
                "missionId": mission_id,
            })
            add_trigger_route(build_story_trigger_route(
                row,
                mission_id=mission_id,
                scope="mission",
            ))
        for row, quest_id, scope in _scoped_connection_rows(flow):
            key = str(row.get("key") or "")
            if (
                str(row.get("relation") or "") in {
                    "levelscript_interactive_narrative_config",
                    "leveldata_interactive_narrative_config",
                }
                and (
                    key in all_index_rows
                    or row.get("dialogDefinitionOnly") is True
                )
            ):
                if row.get("dialogDefinitionOnly") is True:
                    definition_only_interactive_config_keys.add(key)
                if key not in all_story_rows:
                    context_only_trigger_route_keys.add(key)
                add_trigger_route(build_story_trigger_route(
                    row,
                    mission_id=mission_id,
                    quest_id=quest_id,
                    scope=scope,
                ))
            if key not in story_rows and key in all_story_rows:
                story_rows[key] = {
                    **all_story_rows[key],
                    "pipelineOwnerStatus": "connected_cross_owner",
                }
                connected_cross_owner_keys.add(key)
            if key not in story_rows:
                continue
            connected_keys.add(key)
            connected_by_mission[mission_id].add(key)
            relation_counts[str(row.get("relation") or "unknown")] += 1
            evidence_tier = str(row.get("evidenceTier") or "").strip()
            if evidence_tier:
                evidence_tier_counts[evidence_tier] += 1
                connected_keys_by_evidence_tier[evidence_tier].add(key)
            evidence_row_count += 1
            add_trigger_route(build_story_trigger_route(
                row,
                mission_id=mission_id,
                quest_id=quest_id,
                scope=scope,
            ))
        for row in flow.get("unlinkedNativePlayback") or []:
            if isinstance(row, dict) and str(row.get("key") or "") in story_rows:
                key = str(row["key"])
                native_playback_unscoped.add(key)
                add_trigger_route(build_story_trigger_route(
                    row,
                    mission_id=mission_id,
                    scope="mission",
                    owner_status="unresolved_playback",
                ))
                event_names = {
                    str(value).strip()
                    for value in row.get("nativeEventNames") or []
                    if str(value).strip()
                }
                if event_names:
                    for event_name in event_names:
                        native_playback_event_keys[event_name].add(key)
                else:
                    native_playback_without_named_event.add(key)
                for occurrence in row.get("occurrences") or []:
                    if not isinstance(occurrence, dict):
                        continue
                    script_id = str(occurrence.get("scriptId") or "")
                    if not script_id:
                        continue
                    for subgame in missionless_subgames_by_script.get(script_id, []):
                        subgame_id = subgame["subGameId"]
                        node = missionless_subgame_nodes.setdefault(subgame_id, {
                            **subgame,
                            **subgame_cross_references.get(subgame_id, {}),
                            "relation": "subgame_bind_script_native_playback",
                            "confidence": "typed_original_data_and_native_playback",
                            "missionOwnerStatus": "unresolved",
                            "storyBinding": False,
                            "storyFiles": {},
                        })
                        files = node["storyFiles"]
                        story = files.setdefault(key, {
                            "key": key,
                            "kind": story_rows[key]["kind"],
                            "levelIds": set(),
                            "sourceFiles": set(),
                            "nativeActions": set(),
                            "nativeEventNames": set(),
                        })
                        if occurrence.get("levelId"):
                            story["levelIds"].add(str(occurrence["levelId"]))
                        if occurrence.get("sourceFile"):
                            story["sourceFiles"].add(str(occurrence["sourceFile"]))
                        if occurrence.get("actionName"):
                            story["nativeActions"].add(str(occurrence["actionName"]))
                        story["nativeEventNames"].update(event_names)
                    for owner in occurrence.get("nativeEventOwners") or []:
                        if (
                            not isinstance(owner, dict)
                            or owner.get("status") != "exact_serialized_control_path"
                        ):
                            continue
                        event_name = str(owner.get("headerName") or "").strip()
                        event_detail = owner.get("eventDetail") or {}
                        level_id = str(occurrence.get("levelId") or "")
                        selector = exact_native_runtime_selector(
                            event_name,
                            event_detail,
                            level_id=level_id,
                            script_id=script_id,
                            header_local_id=(
                                int(owner["headerLocalId"])
                                if isinstance(owner.get("headerLocalId"), int)
                                else None
                            ),
                        )
                        if not selector:
                            continue
                        source_file = str(occurrence.get("sourceFile") or "")
                        source_path = ROOT / source_file
                        runtime_target = (
                            owner.get("runtimeTarget")
                            if isinstance(owner.get("runtimeTarget"), dict)
                            else {}
                        )
                        if (
                            not runtime_target
                            and event_name
                            == "LevelEvent_OnEncounterBattlePartBegin"
                            and isinstance(
                                event_detail.get("levelScriptVariableFilter"),
                                int,
                            )
                        ):
                            try:
                                runtime_target = (
                                    decode_levelscript_encounter_module_target(
                                        read_bytes_cached(source_path),
                                        event_detail["levelScriptVariableFilter"],
                                        script_id,
                                    )
                                )
                            except OSError:
                                runtime_target = {}
                            if runtime_target:
                                runtime_target["sourceFile"] = repo_path(source_path)
                        selector_key = json.dumps(
                            [event_name, selector],
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        )
                        runtime_node = missionless_native_runtime_nodes.setdefault(
                            selector_key,
                            {
                                "relation": "exact_native_runtime_receiver_playback",
                                "confidence": "exact_current_build_memorypack_fields",
                                "missionOwnerStatus": "unresolved",
                                "storyBinding": False,
                                "eventName": event_name,
                                "eventSummary": str(event_detail.get("summary") or ""),
                                "transport": str(event_detail.get("transport") or ""),
                                "serverExchange": event_detail.get("serverExchange"),
                                "selector": selector,
                                "payloadSchemaMappingId": str(
                                    event_detail.get("payloadSchemaMappingId") or ""
                                ),
                                "runtimeTarget": (
                                    runtime_target or None
                                ),
                                "ownershipBoundary": str(
                                    runtime_target.get("ownershipBoundary") or ""
                                ),
                                "_playbackGates": {},
                                "_postPlaybackControls": {},
                                "_localProducerRoutes": {},
                                "storyFiles": {},
                            },
                        )
                        header_local_id = selector.get("listenerHeaderLocalId")
                        if source_file and isinstance(header_local_id, int):
                            gate_cache_key = (source_file, header_local_id)
                            if gate_cache_key not in native_receiver_gate_cache:
                                try:
                                    native_receiver_gate_cache[gate_cache_key] = (
                                        exact_native_receiver_playback_gate(
                                            read_bytes_cached(source_path),
                                            header_local_id,
                                            source_file=source_file,
                                        )
                                    )
                                except OSError:
                                    native_receiver_gate_cache[gate_cache_key] = {}
                            playback_gate = native_receiver_gate_cache[gate_cache_key]
                            if playback_gate:
                                gate_signature = json.dumps(
                                    playback_gate,
                                    ensure_ascii=False,
                                    sort_keys=True,
                                    separators=(",", ":"),
                                )
                                runtime_node["_playbackGates"][gate_signature] = (
                                    playback_gate
                                )
                        playback_local_id = occurrence.get("localId")
                        if isinstance(playback_local_id, int):
                            post_playback = (
                                exact_native_receiver_post_playback_control(
                                    owner,
                                    story_key=key,
                                    playback_local_id=playback_local_id,
                                    source_file=source_file,
                                )
                            )
                            if post_playback:
                                post_signature = json.dumps(
                                    [
                                        source_file,
                                        key,
                                        playback_local_id,
                                        post_playback.get("edges") or [],
                                    ],
                                    ensure_ascii=False,
                                    sort_keys=True,
                                    separators=(",", ":"),
                                )
                                runtime_node["_postPlaybackControls"][
                                    post_signature
                                ] = post_playback
                        if runtime_target and not runtime_node.get("runtimeTarget"):
                            runtime_node["runtimeTarget"] = runtime_target
                            runtime_node["ownershipBoundary"] = str(
                                runtime_target.get("ownershipBoundary") or ""
                            )
                        if event_name == "LevelEvent_OnBattleSignal":
                            signal_id = str(selector.get("signalId") or "")
                            producer_routes = runtime_node["_localProducerRoutes"]
                            exact_receiver = bool(
                                owner.get("headerUnionTag") == "0x004c"
                                and owner.get("headerSerializedMemberCount") == 16
                                and owner.get("nativeHeaderMappingId")
                                == BATTLE_SIGNAL_RECEIVER_MAPPING_ID
                                and event_detail.get("payloadSchemaMappingId")
                                == BATTLE_SIGNAL_PAYLOAD_MAPPING_ID
                            )
                            for producer in (
                                (row.get("nativeEventProducerRoutes") or [])
                                if exact_receiver
                                else ()
                            ):
                                if (
                                    not isinstance(producer, dict)
                                    or not is_exact_battle_signal_producer_route(
                                        producer,
                                        story_key=key,
                                        signal_id=signal_id,
                                        level_id=level_id,
                                        script_id=script_id,
                                        header_local_id=(
                                            int(owner["headerLocalId"])
                                            if isinstance(
                                                owner.get("headerLocalId"), int
                                            )
                                            else None
                                        ),
                                        source_file=str(
                                            occurrence.get("sourceFile") or ""
                                        ),
                                    )
                                ):
                                    continue
                                producer_signature = json.dumps(
                                    [
                                        producer.get("producerSourceFile"),
                                        producer.get("actionOffset"),
                                        producer.get("receiverSignalId"),
                                        producer.get("listenerLevelId"),
                                        producer.get("listenerScriptId"),
                                        producer.get("listenerHeaderLocalId"),
                                    ],
                                    ensure_ascii=False,
                                    separators=(",", ":"),
                                )
                                producer_routes[producer_signature] = producer
                                runtime_node.update({
                                    "executionSide": "client",
                                    "transport": "local-level-runtime-event",
                                    "serverExchange": False,
                                    "clientRequest": False,
                                    "expectedServerReturn": False,
                                    "producerReceiverBoundary": (
                                        "OnBattleSignal selects only signalId; it has "
                                        "no serialized sender, entity, spawner, "
                                        "mission, or quest selector"
                                    ),
                                })
                        runtime_stories = runtime_node["storyFiles"]
                        runtime_story = runtime_stories.setdefault(
                            key,
                            {
                                "key": key,
                                "kind": story_rows[key]["kind"],
                                "sourceFiles": set(),
                                "nativeActions": set(),
                            },
                        )
                        if occurrence.get("sourceFile"):
                            runtime_story["sourceFiles"].add(
                                str(occurrence["sourceFile"])
                            )
                        if occurrence.get("actionName"):
                            runtime_story["nativeActions"].add(
                                str(occurrence["actionName"])
                            )
        for row in flow.get("unlinkedTimelineContainment") or []:
            if isinstance(row, dict) and str(row.get("key") or "") in story_rows:
                unresolved_timeline_containment.add(str(row["key"]))
                add_trigger_route(build_story_trigger_route(
                    row,
                    mission_id=mission_id,
                    scope="mission",
                    owner_status="unresolved",
                ))
        unresolved_dialog_rows = (
            flow.get("unresolvedDialogTreeNarrativeActions")
            if "unresolvedDialogTreeNarrativeActions" in flow
            else flow.get("unlinkedDialogTreeNarrativeActions")
        )
        for row in unresolved_dialog_rows or []:
            if isinstance(row, dict) and str(row.get("key") or "") in story_rows:
                unresolved_dialog_tree_containment.add(str(row["key"]))
                add_trigger_route(build_story_trigger_route(
                    row,
                    mission_id=mission_id,
                    scope="mission",
                    owner_status="unresolved",
                ))
        for row in flow.get("unlinkedDialogTreeNarrativeActions") or []:
            if isinstance(row, dict) and str(row.get("key") or "") in story_rows:
                unlinked_dialog_tree_containment.add(str(row["key"]))
        unresolved_left_subtitle_rows = (
            flow.get("unresolvedDialogTreeLeftSubtitleActions")
            if "unresolvedDialogTreeLeftSubtitleActions" in flow
            else flow.get("unlinkedDialogTreeLeftSubtitleActions")
        )
        for row in unresolved_left_subtitle_rows or []:
            if isinstance(row, dict) and str(row.get("key") or "") in story_rows:
                unresolved_dialog_tree_left_subtitle.add(str(row["key"]))
                add_trigger_route(build_story_trigger_route(
                    row,
                    mission_id=mission_id,
                    scope="mission",
                    owner_status="unresolved",
                ))
        for row in flow.get("unlinkedDialogTreeLeftSubtitleActions") or []:
            if isinstance(row, dict) and str(row.get("key") or "") in story_rows:
                unlinked_dialog_tree_left_subtitle.add(str(row["key"]))
        for row in flow.get("unresolvedDialogTreeStoryPlaybackCarriers") or []:
            if isinstance(row, dict) and str(row.get("key") or "") in story_rows:
                unresolved_dialog_tree_story_playback.add(str(row["key"]))
                add_trigger_route(build_story_trigger_route(
                    row,
                    mission_id=mission_id,
                    scope="mission",
                    owner_status="unresolved",
                ))
        for row in flow.get("unlinkedDefinitionOnly") or []:
            if isinstance(row, dict) and str(row.get("key") or "") in story_rows:
                key = str(row["key"])
                unlinked_definition_only.add(key)
                definition_row = {
                    **row,
                    "relation": "original_text_definition_without_consumer",
                    "direction": "context",
                }
                add_trigger_route(build_story_trigger_route(
                    definition_row,
                    mission_id=mission_id,
                    scope="mission",
                    owner_status="unresolved",
                ))

    composed_root_playback_alias_rows: list[dict[str, Any]] = []
    composed_route_signatures: set[str] = set()
    for alias in root_playback_alias_rows:
        root_key = alias["rootStoryKey"]
        playable_key = alias["playableAssetStoryKey"]
        for root_route in list(
            story_trigger_routes.get(root_key, {}).values()
        ):
            composed_route = build_composed_root_playback_alias_route(
                alias,
                root_route,
            )
            if composed_route is None:
                continue
            signature = json.dumps(
                composed_route,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            if signature in composed_route_signatures:
                continue
            composed_route_signatures.add(signature)
            add_trigger_route(composed_route)
            connected_keys.add(playable_key)
            mission_id = str(composed_route["missionId"])
            connected_by_mission[mission_id].add(playable_key)
            relation_counts[composed_route["relation"]] += 1
            evidence_tier = str(composed_route["evidenceTier"])
            evidence_tier_counts[evidence_tier] += 1
            connected_keys_by_evidence_tier[evidence_tier].add(
                playable_key
            )
            evidence_row_count += 1
            composed_root_playback_alias_rows.append({
                "rootStoryKey": root_key,
                "playableAssetStoryKey": playable_key,
                "missionId": mission_id,
                "questId": composed_route.get("questId"),
                "rootBaseRelation": composed_route["rootBaseRelation"],
                "rootBaseCausality": composed_route["rootBaseCausality"],
                "nativeMappingId": composed_route["nativeMappingId"],
            })

    unlinked = [row for key, row in story_rows.items() if key not in connected_keys]
    unlinked.sort(key=lambda row: (natural_quest_key(row["missionId"]), row["kind"], natural_quest_key(row["key"])))
    definition_only_classification = classify_definition_only_current_build_consumers(
        unlinked_definition_only,
        text_vo_id_table_path,
    )
    definition_only_class_counts = definition_only_classification["counts"]
    unlinked_non_mission_content = {
        key: non_mission_content[key]
        for key in story_rows
        if key not in connected_keys and key in non_mission_content
    }
    story_trigger_manifest: dict[str, dict[str, Any]] = {}
    rejected_playback_by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in lua_playback_evidence["rejectedCaseMismatchCalls"]:
        rejected_playback_by_key[str(candidate["storyKey"])].append(
            dict(candidate)
        )
    story_files_with_trigger_routes = 0
    unlinked_files_with_trigger_routes = 0
    trigger_route_count = 0
    context_only_trigger_route_files = 0
    context_only_trigger_route_count = 0
    for key, story in sorted(story_rows.items(), key=lambda item: natural_quest_key(item[0])):
        routes = list(story_trigger_routes.get(key, {}).values())
        routes.sort(key=story_trigger_route_sort_key)
        if key in connected_keys:
            attachment_status = "connected"
        elif key in native_playback_unscoped:
            attachment_status = "trigger_known_owner_unresolved"
        elif key in unlinked_definition_only:
            attachment_status = "definition_only_no_consumer"
        elif key in unlinked_non_mission_content:
            attachment_status = "non_mission_content"
        elif any(
            str(route.get("causality") or "").startswith("playback")
            for route in routes
        ):
            # A recovered PLAYBACK route outside the LevelScript lane (currently
            # shipped-Lua controller playback). The trigger is known; the
            # mission/quest owner is not. Condition, context, and dependency
            # routes must never be promoted here: they are not playback
            # triggers, and relabelling them would overstate the evidence.
            attachment_status = "trigger_known_owner_unresolved"
        else:
            attachment_status = "unlinked_no_trigger_route"
        if routes:
            story_files_with_trigger_routes += 1
            trigger_route_count += len(routes)
            if key not in connected_keys:
                unlinked_files_with_trigger_routes += 1
        manifest_row = {
            "key": key,
            "kind": story["kind"],
            "nominalMissionId": story["missionId"],
            "attachmentStatus": attachment_status,
            "routes": routes,
        }
        if rejected_playback_by_key.get(key):
            manifest_row["rejectedPlaybackCandidates"] = (
                rejected_playback_by_key[key]
            )
        story_trigger_manifest[key] = manifest_row
    for key in sorted(context_only_trigger_route_keys, key=natural_quest_key):
        if key in story_trigger_manifest:
            continue
        story = all_index_rows.get(key)
        if not story and key in definition_only_interactive_config_keys:
            routes_for_key = list(story_trigger_routes[key].values())
            story = {
                "key": key,
                "kind": "dialogDefinition",
                "missionId": next(
                    (
                        str(route.get("missionId") or "")
                        for route in routes_for_key
                        if route.get("missionId")
                    ),
                    "",
                ),
            }
        if not story:
            continue
        routes = list(story_trigger_routes[key].values())
        routes.sort(key=story_trigger_route_sort_key)
        if not routes:
            continue
        context_only_trigger_route_files += 1
        context_only_trigger_route_count += len(routes)
        trigger_route_count += len(routes)
        story_trigger_manifest[key] = {
            "key": key,
            "kind": story["kind"],
            "nominalMissionId": story["missionId"],
            "attachmentStatus":
                (
                    "registered_dialog_definition_context_only"
                    if key in definition_only_interactive_config_keys
                    else
                    "context_only_outside_pipeline_coverage_denominator"
                ),
            "routes": routes,
        }
    kind_counts: dict[str, dict[str, int]] = {}
    for kind in sorted(PIPELINE_STORY_KINDS):
        total = sum(1 for row in story_rows.values() if row["kind"] == kind)
        connected = sum(1 for key in connected_keys if story_rows[key]["kind"] == kind)
        kind_counts[kind] = {"total": total, "connected": connected, "unlinked": total - connected}

    missionless_nodes: list[dict[str, Any]] = []
    missionless_story_keys: set[str] = set()
    missionless_story_placements = 0
    for node in missionless_subgame_nodes.values():
        story_files = []
        for story in node.pop("storyFiles").values():
            normalized = {
                **story,
                "levelIds": sorted(story["levelIds"]),
                "sourceFiles": sorted(story["sourceFiles"]),
                "nativeActions": sorted(story["nativeActions"]),
                "nativeEventNames": sorted(story["nativeEventNames"]),
            }
            story_files.append(normalized)
            missionless_story_keys.add(story["key"])
            missionless_story_placements += 1
        node["storyFiles"] = sorted(story_files, key=lambda row: natural_quest_key(row["key"]))
        missionless_nodes.append(node)
    missionless_nodes.sort(key=lambda row: natural_quest_key(row["subGameId"]))

    missionless_runtime_nodes: list[dict[str, Any]] = []
    missionless_runtime_story_keys: set[str] = set()
    missionless_runtime_story_placements = 0
    for node in missionless_native_runtime_nodes.values():
        playback_gates = sorted(
            node.pop("_playbackGates", {}).values(),
            key=lambda row: (
                str(row.get("sourceFile") or ""),
                int(row.get("headerLocalId") or -1),
            ),
        )
        if playback_gates:
            node["playbackGates"] = playback_gates
        post_playback_controls = sorted(
            node.pop("_postPlaybackControls", {}).values(),
            key=lambda row: (
                str(row.get("sourceFile") or ""),
                str(row.get("storyKey") or ""),
                int(row.get("playbackLocalId") or -1),
            ),
        )
        if post_playback_controls:
            node["postPlaybackControls"] = post_playback_controls
        local_producer_routes = sorted(
            node.pop("_localProducerRoutes", {}).values(),
            key=lambda row: (
                str(row.get("producerDomain") or ""),
                str(row.get("producerAssetId") or ""),
                str(row.get("actionOffset") or ""),
            ),
        )
        if local_producer_routes:
            node["localProducerRoutes"] = local_producer_routes
        story_files = []
        for story in node.pop("storyFiles").values():
            normalized = {
                **story,
                "sourceFiles": sorted(story["sourceFiles"]),
                "nativeActions": sorted(story["nativeActions"]),
            }
            story_files.append(normalized)
            missionless_runtime_story_keys.add(story["key"])
            missionless_runtime_story_placements += 1
        node["storyFiles"] = sorted(
            story_files,
            key=lambda story: natural_quest_key(story["key"]),
        )
        missionless_runtime_nodes.append(node)
    missionless_runtime_nodes.sort(
        key=lambda node: (
            node["eventName"],
            str(node["selector"].get("levelId") or ""),
            str(node["selector"].get("listenerScriptId") or ""),
            json.dumps(node["selector"], sort_keys=True),
        )
    )

    level_sequence_textasset_index = build_level_sequence_textasset_index()
    post_playback_action_name_audit = build_post_playback_action_name_audit(
        missionless_runtime_nodes
    )
    action_name_summary = post_playback_action_name_audit.get("summary") or {}
    callback_audit = (
        callserver_callback_audit
        if isinstance(callserver_callback_audit, dict)
        else {}
    )
    callback_audit_summary = callback_audit.get("summary") or {}
    post_playback_callserver_contract_audit = (
        attach_post_playback_callserver_contracts(
            missionless_runtime_nodes,
            callback_audit,
        )
    )
    post_playback_callserver_summary = (
        post_playback_callserver_contract_audit.get("summary") or {}
    )
    if (
        callback_audit.get("status") == "validated_complete_corpus"
        and post_playback_callserver_contract_audit.get("status")
        != "validated"
    ):
        failures = (
            post_playback_callserver_contract_audit.get("validationFailures")
            or []
        )
        raise ValueError(json.dumps({
            "validator": "post_playback_callserver_contract_audit",
            "gate": "exact_source_local_id_contract_join",
            "summary": post_playback_callserver_summary,
            "firstFailure": failures[0] if failures else None,
            "validationFailures": failures[:100],
        }, ensure_ascii=False, indent=2))
    callback_story_routes = []
    for callback_row in callback_audit.get("rows") or []:
        if not isinstance(callback_row, dict):
            continue
        for callback in callback_row.get("callbackOutputs") or []:
            graph = callback.get("controlGraph") or {}
            if not graph.get("storyKeys"):
                continue
            callback_story_routes.append({
                "levelId": callback_row.get("levelId"),
                "scriptId": callback_row.get("scriptId"),
                "sourceFile": callback_row.get("sourceFile"),
                "callServerLocalId": callback_row.get("callServerLocalId"),
                "callServerUid": callback_row.get("callServerUid"),
                "callbackHeaderUid": callback.get("headerUid"),
                "callbackHeaderLocalId": callback.get("headerLocalId"),
                "storyKeys": graph.get("storyKeys") or [],
                "actionCount": graph.get("actionCount", 0),
                "branchPointCount": graph.get("branchPointCount", 0),
            })
    compact_callback_audit = {
        "schema": callback_audit.get("schema"),
        "status": callback_audit.get("status"),
        "source": repo_path(CALLSERVER_CALLBACK_AUDIT_JSON),
        "summary": callback_audit_summary,
        "storyCallbackRoutes": callback_story_routes,
        "postPlaybackContractAudit": post_playback_callserver_contract_audit,
        "unresolvedCallbackOutputs": (
            callback_audit.get("unresolvedCallbackOutputs") or []
        ),
        "validationFailures": callback_audit.get("validationFailures") or [],
        "nativeContract": (
            (callback_audit.get("sources") or {}).get("nativeContract") or {}
        ),
        "evidenceBoundary": callback_audit.get("evidenceBoundary") or "",
        "missionOwnershipEvidence": False,
        "usesOcrOrManualOrder": False,
    }
    post_playback_level_sequence_asset_audit = attach_exact_level_sequence_assets(
        missionless_runtime_nodes,
        level_sequence_textasset_index,
    )
    level_sequence_asset_summary = (
        post_playback_level_sequence_asset_audit.get("summary") or {}
    )
    post_playback_variable_bridge_audit = (
        build_post_playback_variable_bridge_audit(
            native_story_playback_index
            if native_story_playback_index is not None
            else build_levelscript_native_story_playback_index()
        )
    )
    variable_bridge_summary = (
        post_playback_variable_bridge_audit.get("summary") or {}
    )
    dynamic_scene_identity = load_dynamic_scene_identity_cross_references()
    report = {
        "schemaVersion": 17,
        "generated": int(time.time()),
        "language": language,
        "policy": (
            "Original exported game data and current-build native serialization only; "
            "OCR, manual overrides, and gameplay observations do not promote a connection. "
            "Story rows whose nominal owner is not a pipeline mission enter the denominator "
            "only when an accepted generated pipeline edge connects them."
        ),
        "sources": {
            "pipelineIndex": repo_path(pipeline_index_path),
            "storyIndex": repo_path(story_index_path),
            "missionSidecars": repo_path(mission_sidecar_root),
            "definitionOnlyAudioMetadata": definition_only_classification["source"],
            "luaPlaybackAudit": lua_playback_evidence["auditReport"],
            "luaPlaybackAuditSha256": lua_playback_evidence["auditSha256"],
            "cinematicQueueRuntimeAudit": cinematic_report,
            "levelSequenceTextAssets": repo_path(
                DEFAULT_LEVEL_SEQUENCE_TEXTASSET_ROOT
            ),
            "actionBaseFormatterTable": str(
                ACTIONBASE_FORMATTER_NAME_AUDIT.get("sourceFile") or ""
            ),
            "callServerCallbackAudit": repo_path(
                CALLSERVER_CALLBACK_AUDIT_JSON
            ),
        },
        "counts": {
            "pipelineMissions": len(mission_ids),
            "missionSidecarsRead": sidecars_read,
            "uniqueStoryFiles": len(story_rows),
            "connectedUniqueStoryFiles": len(connected_keys),
            "connectedCrossOwnerStoryFiles": len(connected_cross_owner_keys),
            "unlinkedUniqueStoryFiles": len(unlinked),
            "connectedMissionPlacements": sum(len(keys) for keys in connected_by_mission.values()),
            "connectionEvidenceRows": evidence_row_count,
            "storyTriggerRoutes": trigger_route_count,
            "storyFilesWithTriggerRoutes": story_files_with_trigger_routes,
            "nativeCinematicProducerStoryFiles": sum(
                any(route.get("nativeCinematicProducerRoutes") for route in row.get("routes") or [])
                for row in story_trigger_manifest.values()
            ),
            "nativeCinematicProducerRouteAttachments": sum(
                len(route.get("nativeCinematicProducerRoutes") or [])
                for row in story_trigger_manifest.values()
                for route in row.get("routes") or []
            ),
            "contextOnlyTriggerRouteFiles":
                context_only_trigger_route_files,
            "contextOnlyTriggerRoutes": context_only_trigger_route_count,
            "definitionOnlyInteractiveConfigFiles": len({
                key
                for key in definition_only_interactive_config_keys
                if key in story_trigger_manifest
            }),
            "definitionOnlyInteractiveConfigRoutes": sum(
                len(story_trigger_manifest[key].get("routes") or [])
                for key in definition_only_interactive_config_keys
                if key in story_trigger_manifest
            ),
            "unlinkedStoryFilesWithTriggerRoutes": unlinked_files_with_trigger_routes,
            "rootPlaybackAliasFiles": len({
                row["playableAssetStoryKey"]
                for row in root_playback_alias_rows
            }),
            "rootPlaybackAliasRows": len(root_playback_alias_rows),
            "composedRootPlaybackAliasFiles": len({
                row["playableAssetStoryKey"]
                for row in composed_root_playback_alias_rows
            }),
            "composedRootPlaybackAliasRows":
                len(composed_root_playback_alias_rows),
            "rejectedStoryPlaybackCandidates": sum(
                len(rows)
                for key, rows in rejected_playback_by_key.items()
                if key in story_rows
            ),
            "scannedLuaStoryPlaybackCalls":
                lua_playback_evidence["scannedPlaybackCalls"],
            "acceptedLuaExactPlaybackCalls": len(
                lua_playback_evidence["acceptedExactPlaybackCalls"]
            ),
            "acceptedLuaTableCarrierCalls":
                lua_playback_evidence["acceptedTableCarrierCalls"],
            "rejectedLuaCaseMismatchCalls": len(
                lua_playback_evidence["rejectedCaseMismatchCalls"]
            ),
            "runtimeLuaHandleDispatcherCalls":
                lua_playback_evidence["runtimeHandleDispatcherCallCount"],
            "runtimeLuaHandleDispatcherFamilies":
                lua_playback_evidence["runtimeHandleDispatcherFamilyCount"],
            "unresolvedLuaAuthoredPlaybackCalls":
                lua_playback_evidence["unresolvedPlaybackCalls"],
            "missionStateDependencyStoryFiles": len(
                mission_state_dependency_keys
            ),
            "missionStateDependencyCrossOwnerStoryFiles": len(
                mission_state_dependency_cross_owner_keys
            ),
            "missionStateDependencyPlacements": len(
                mission_state_dependency_placements
            ),
            "unlinkedNativePlaybackFiles": len(native_playback_unscoped),
            "unlinkedNativePlaybackWithoutNamedEvent": len(native_playback_without_named_event),
            "unresolvedTimelineContainmentFiles": len(unresolved_timeline_containment),
            "unresolvedDialogTreeNarrativeFiles": len(unresolved_dialog_tree_containment),
            "unlinkedDialogTreeNarrativeFiles": len(unlinked_dialog_tree_containment),
            "unresolvedDialogTreeLeftSubtitleFiles": len(
                unresolved_dialog_tree_left_subtitle
            ),
            "unlinkedDialogTreeLeftSubtitleFiles": len(
                unlinked_dialog_tree_left_subtitle
            ),
            "unresolvedDialogTreeStoryPlaybackFiles": len(
                unresolved_dialog_tree_story_playback
            ),
            "unlinkedDefinitionOnlyFiles": len(unlinked_definition_only),
            "nonMissionContentFiles": len(unlinked_non_mission_content),
            "unlinkedDefinitionOnlyAudioMetadataFiles": definition_only_class_counts.get(
                "original_audio_metadata_without_playback_consumer",
                0,
            ),
            "unlinkedDefinitionOnlyEmptyAudioLikelyLegacyFiles": definition_only_class_counts.get(
                "explicit_empty_audio_metadata_likely_legacy_definition",
                0,
            ),
            "unlinkedDefinitionOnlyWithoutAudioMetadataFiles": definition_only_class_counts.get(
                "no_audio_metadata_or_playback_consumer_recovered",
                0,
            ),
            "missionlessSubGameRows": len(missionless_nodes),
            "missionlessSubGameStoryFiles": len(missionless_story_keys),
            "missionlessSubGameStoryPlacements": missionless_story_placements,
            "missionlessNativeRuntimeRows": len(missionless_runtime_nodes),
            "missionlessNativeRuntimeStoryFiles": len(missionless_runtime_story_keys),
            "missionlessNativeRuntimeStoryPlacements": missionless_runtime_story_placements,
            "missionlessNativeRuntimeProducerRoutes": sum(
                len(node.get("localProducerRoutes") or [])
                for node in missionless_runtime_nodes
            ),
            "missionlessNativeRuntimePlaybackGates": sum(
                len(node.get("playbackGates") or [])
                for node in missionless_runtime_nodes
            ),
            "missionlessNativeRuntimePlaybackGateStoryFiles": len({
                story["key"]
                for node in missionless_runtime_nodes
                if node.get("playbackGates")
                for story in node.get("storyFiles") or []
            }),
            "missionlessNativeRuntimePostPlaybackControls": sum(
                len(node.get("postPlaybackControls") or [])
                for node in missionless_runtime_nodes
            ),
            "missionlessNativeRuntimePostPlaybackBranchPoints": sum(
                len(control.get("branchPointLocalIds") or [])
                for node in missionless_runtime_nodes
                for control in node.get("postPlaybackControls") or []
            ),
            "missionlessNativeRuntimePostPlaybackServerHandoffs": sum(
                len(control.get("serverHandoffs") or [])
                for node in missionless_runtime_nodes
                for control in node.get("postPlaybackControls") or []
            ),
            "missionlessNativeRuntimePostPlaybackCallbackHeaderUids": sum(
                len(handoff.get("possibleCallbackHeaderUIDs") or [])
                for node in missionless_runtime_nodes
                for control in node.get("postPlaybackControls") or []
                for handoff in control.get("serverHandoffs") or []
            ),
            "callServerActions": callback_audit_summary.get(
                "callServerActions", 0
            ),
            "callServerCallbackOutputUids": callback_audit_summary.get(
                "callbackOutputUids", 0
            ),
            "callServerExactCallbackHeaders": callback_audit_summary.get(
                "exactCallbackHeaders", 0
            ),
            "callServerCallbackHeadersReachingStory": callback_audit_summary.get(
                "callbackHeadersReachingStory", 0
            ),
            "callServerUnresolvedCallbackOutputs": callback_audit_summary.get(
                "unresolvedCallbackOutputs", 0
            ),
            "postPlaybackCallServerExactContracts": (
                post_playback_callserver_summary.get("exactContracts", 0)
            ),
            "postPlaybackCallServerUnresolvedContracts": (
                post_playback_callserver_summary.get("unresolvedContracts", 0)
            ),
            "postPlaybackLevelSequenceActions": level_sequence_asset_summary.get(
                "typedActionPlacements", 0
            ),
            "postPlaybackLevelSequenceIds": level_sequence_asset_summary.get(
                "serializedLevelSequenceIds", 0
            ),
            "postPlaybackLevelSequenceExactAssets": level_sequence_asset_summary.get(
                "exactResolvedLevelSequenceIds", 0
            ),
            "postPlaybackLevelSequenceUnresolvedIds": level_sequence_asset_summary.get(
                "unresolvedLevelSequenceIds", 0
            ),
            "postPlaybackLevelSequenceRelatedOriginalFiles": (
                level_sequence_asset_summary.get("relatedOriginalFiles", 0)
            ),
            "postPlaybackActionPlacements": action_name_summary.get(
                "actionPlacements", 0
            ),
            "postPlaybackFormatterNamedActions": action_name_summary.get(
                "formatterNamedActionPlacements", 0
            ),
            "postPlaybackFallbackNamedActions": action_name_summary.get(
                "fallbackNamedActionPlacements", 0
            ),
            "postPlaybackUnresolvedActionShapes": action_name_summary.get(
                "unresolvedOutsideActionBaseShapes", 0
            ),
            "postPlaybackVariableSetters": variable_bridge_summary.get(
                "postPlaybackVariableSetters", 0
            ),
            "postPlaybackVariableExactListenerMatches": (
                variable_bridge_summary.get("exactSetterListenerMatches", 0)
            ),
            "postPlaybackVariableCrossStoryListenerMatches": (
                variable_bridge_summary.get(
                    "crossStorySetterListenerMatches", 0
                )
            ),
            "partiallyConnectedDialogTreeNarrativeFiles": len(
                unresolved_dialog_tree_containment & connected_keys
            ),
        },
        "byKind": kind_counts,
        "relationEvidenceRows": dict(sorted(relation_counts.items())),
        "evidenceTierRows": dict(sorted(evidence_tier_counts.items())),
        "evidenceTierUniqueStoryFiles": {
            tier: len(keys)
            for tier, keys in sorted(connected_keys_by_evidence_tier.items())
        },
        "missionStateStoryDependencies": sorted(
            mission_state_dependency_rows,
            key=lambda row: (
                natural_quest_key(str(row.get("missionId") or "")),
                natural_quest_key(str(row.get("key") or "")),
            ),
        ),
        "storyTriggerManifest": story_trigger_manifest,
        "postPlaybackActionNameAudit": post_playback_action_name_audit,
        "callServerCallbackAudit": compact_callback_audit,
        "postPlaybackLevelSequenceAssetAudit": (
            post_playback_level_sequence_asset_audit
        ),
        "luaStoryPlaybackEvidence": lua_playback_evidence,
        "rootPlaybackAliases": root_playback_alias_rows,
        "composedRootPlaybackAliases":
            composed_root_playback_alias_rows,
        "missionStateDependencyCrossOwnerStoryKeys": sorted(
            mission_state_dependency_cross_owner_keys,
            key=natural_quest_key,
        ),
        "nativePlaybackEventFamilies": {
            event_name: len(keys)
            for event_name, keys in sorted(native_playback_event_keys.items())
        },
        "nativePlaybackEventFamilyKeys": {
            event_name: sorted(keys, key=natural_quest_key)
            for event_name, keys in sorted(native_playback_event_keys.items())
        },
        "unlinkedNativePlaybackWithoutNamedEventKeys": sorted(
            native_playback_without_named_event,
            key=natural_quest_key,
        ),
        "unlinked": unlinked,
        "connectedCrossOwnerStoryKeys": sorted(
            connected_cross_owner_keys,
            key=natural_quest_key,
        ),
        "unlinkedNativePlaybackKeys": sorted(native_playback_unscoped, key=natural_quest_key),
        "unresolvedTimelineContainmentKeys": sorted(unresolved_timeline_containment, key=natural_quest_key),
        "unresolvedDialogTreeNarrativeKeys": sorted(
            unresolved_dialog_tree_containment,
            key=natural_quest_key,
        ),
        "unlinkedDialogTreeNarrativeKeys": sorted(
            unlinked_dialog_tree_containment,
            key=natural_quest_key,
        ),
        "unresolvedDialogTreeLeftSubtitleKeys": sorted(
            unresolved_dialog_tree_left_subtitle,
            key=natural_quest_key,
        ),
        "unlinkedDialogTreeLeftSubtitleKeys": sorted(
            unlinked_dialog_tree_left_subtitle,
            key=natural_quest_key,
        ),
        "unresolvedDialogTreeStoryPlaybackKeys": sorted(
            unresolved_dialog_tree_story_playback,
            key=natural_quest_key,
        ),
        "unlinkedDefinitionOnlyKeys": sorted(
            unlinked_definition_only,
            key=natural_quest_key,
        ),
        "definitionOnlyNegativeConsumerClassification": definition_only_classification,
        "nonMissionContentKeys": [
            {"key": key, **unlinked_non_mission_content[key]}
            for key in sorted(unlinked_non_mission_content, key=natural_quest_key)
        ],
        "missionlessSubGamePlaybackNodes": missionless_nodes,
        "missionlessNativeRuntimeNodes": missionless_runtime_nodes,
        "postPlaybackVariableBridgeAudit": (
            post_playback_variable_bridge_audit
        ),
        "dynamicSceneIdentityCrossReferences": dynamic_scene_identity,
        "partiallyConnectedDialogTreeNarrativeKeys": sorted(
            unresolved_dialog_tree_containment & connected_keys,
            key=natural_quest_key,
        ),
    }
    report_root.mkdir(parents=True, exist_ok=True)
    stem = f"mission_pipeline_story_binding_coverage_{language}"
    write_json(report_root / f"{stem}.json", report)
    counts = report["counts"]
    lines = [
        f"# Mission Pipeline Story Binding Coverage ({language})",
        "",
        report["policy"],
        "",
        "## Summary",
        "",
        f"- Pipeline missions: `{counts['pipelineMissions']}`",
        f"- Unique Story files: `{counts['uniqueStoryFiles']}`",
        f"- Connected unique Story files: `{counts['connectedUniqueStoryFiles']}`",
        f"- Connected cross-owner Story files admitted by exact pipeline edges: `{counts['connectedCrossOwnerStoryFiles']}`",
        f"- Unlinked unique Story files: `{counts['unlinkedUniqueStoryFiles']}`",
        f"- Connected mission placements: `{counts['connectedMissionPlacements']}`",
        f"- Connection evidence rows: `{counts['connectionEvidenceRows']}`",
        f"- Normalized Story trigger/context routes: `{counts['storyTriggerRoutes']}`",
        f"- Story files with at least one normalized route: `{counts['storyFilesWithTriggerRoutes']}`",
        f"- Unlinked Story files with a known trigger/context route: `{counts['unlinkedStoryFilesWithTriggerRoutes']}`",
        f"- Shipped-Lua Story playback calls scanned: `{counts['scannedLuaStoryPlaybackCalls']}`",
        f"- Exact-case Lua playback calls admitted: `{counts['acceptedLuaExactPlaybackCalls']}`",
        f"- Case-mismatched Lua calls rejected by installed-binary proof: `{counts['rejectedLuaCaseMismatchCalls']}`",
        f"- Runtime Lua handle dispatcher branches: `{counts['runtimeLuaHandleDispatcherCalls']}` in `{counts['runtimeLuaHandleDispatcherFamilies']}` polymorphic queue family",
        f"- Unresolved authored Lua playback references: `{counts['unresolvedLuaAuthoredPlaybackCalls']}`",
        f"- Exact root playback alias rows: `{counts['rootPlaybackAliasRows']}`",
        f"- TimelineAsset Story files reached by those aliases: `{counts['rootPlaybackAliasFiles']}`",
        f"- Alias rows composed with an independently connected root playback route: `{counts['composedRootPlaybackAliasRows']}`",
        f"- Story files connected by that composition: `{counts['composedRootPlaybackAliasFiles']}`",
        f"- Non-owning mission-state dependency Story files: `{counts['missionStateDependencyStoryFiles']}`",
        f"- Dependency-only Story files whose nominal owner is outside the pipeline: `{counts['missionStateDependencyCrossOwnerStoryFiles']}`",
        f"- Non-owning mission-state dependency placements: `{counts['missionStateDependencyPlacements']}`",
        f"- Unlinked files with exact native playback: `{counts['unlinkedNativePlaybackFiles']}`",
        f"- Exact native playbacks without a named event owner: `{counts['unlinkedNativePlaybackWithoutNamedEvent']}`",
        f"- Unresolved serialized Timeline containment: `{counts['unresolvedTimelineContainmentFiles']}`",
        f"- Unresolved typed DialogTree narrative containment: `{counts['unresolvedDialogTreeNarrativeFiles']}`",
        f"- Unlinked typed DialogTree narrative files: `{counts['unlinkedDialogTreeNarrativeFiles']}`",
        f"- Unresolved typed DialogTree left-subtitle containment: `{counts['unresolvedDialogTreeLeftSubtitleFiles']}`",
        f"- Unlinked typed DialogTree left-subtitle files: `{counts['unlinkedDialogTreeLeftSubtitleFiles']}`",
        f"- Unresolved typed DialogTree Story playback carriers: `{counts['unresolvedDialogTreeStoryPlaybackFiles']}`",
        f"- Definition-only black-screen files with no current-build playback consumer: `{counts['unlinkedDefinitionOnlyFiles']}`",
        f"- Those with non-empty original audio metadata only: `{counts['unlinkedDefinitionOnlyAudioMetadataFiles']}`",
        f"- Those with explicit empty audio mappings (likely legacy definitions): `{counts['unlinkedDefinitionOnlyEmptyAudioLikelyLegacyFiles']}`",
        f"- Those with no original audio metadata row: `{counts['unlinkedDefinitionOnlyWithoutAudioMetadataFiles']}`",
        f"- Exact non-mission authored content (speaker radio continuation, character SNS topics, factory guides): `{counts['nonMissionContentFiles']}`",
        f"- Missionless SubGame runtime nodes with exact playback: `{counts['missionlessSubGameRows']}`",
        f"- Unique Story files attached to those missionless nodes: `{counts['missionlessSubGameStoryFiles']}`",
        f"- Missionless SubGame-to-Story placements: `{counts['missionlessSubGameStoryPlacements']}`",
        f"- Exact missionless native runtime receiver nodes: `{counts['missionlessNativeRuntimeRows']}`",
        f"- Unique Story files attached to exact runtime receivers: `{counts['missionlessNativeRuntimeStoryFiles']}`",
        f"- Exact runtime-receiver-to-Story placements: `{counts['missionlessNativeRuntimeStoryPlacements']}`",
        f"- Exact receiver playback gates: `{counts['missionlessNativeRuntimePlaybackGates']}`",
        f"- Story files controlled by those exact gates: `{counts['missionlessNativeRuntimePlaybackGateStoryFiles']}`",
        f"- Exact post-playback control graphs: `{counts['missionlessNativeRuntimePostPlaybackControls']}`",
        f"- Typed branch points in those graphs: `{counts['missionlessNativeRuntimePostPlaybackBranchPoints']}`",
        f"- Server handoffs with unresolved handler identity: `{counts['missionlessNativeRuntimePostPlaybackServerHandoffs']}`",
        f"- Post-playback ActionBase placements named by the complete binary formatter: `{counts['postPlaybackFormatterNamedActions']}` / `{counts['postPlaybackActionPlacements']}`",
        f"- Remaining action shapes outside ActionBase: `{counts['postPlaybackUnresolvedActionShapes']}`",
        f"- Typed post-playback LevelSequence action placements: `{counts['postPlaybackLevelSequenceActions']}`",
        f"- Unique serialized LevelSequence ids: `{counts['postPlaybackLevelSequenceIds']}`",
        f"- Exact internally validated original LevelSequence TextAssets: `{counts['postPlaybackLevelSequenceExactAssets']}`",
        f"- Unresolved serialized LevelSequence ids: `{counts['postPlaybackLevelSequenceUnresolvedIds']}`",
        f"- Typed variable setters after any native Story playback: `{counts['postPlaybackVariableSetters']}`",
        f"- Exact same-level/script/key Story listener matches: `{counts['postPlaybackVariableExactListenerMatches']}`",
        f"- Cross-Story matches eligible for a future execution-semantics bridge: `{counts['postPlaybackVariableCrossStoryListenerMatches']}`",
        f"- Connected files with another unresolved DialogTree parent use: `{counts['partiallyConnectedDialogTreeNarrativeFiles']}`",
        "",
        "## By kind",
        "",
        "| kind | total | connected | unlinked |",
        "| --- | ---: | ---: | ---: |",
    ]
    for kind, values in kind_counts.items():
        lines.append(f"| `{kind}` | {values['total']} | {values['connected']} | {values['unlinked']} |")
    lines.extend([
        "",
        "## Shipped-Lua playback census",
        "",
        f"Validator: `{lua_playback_evidence['validator']}` / "
        f"`{lua_playback_evidence['status']}`.",
        "",
        lua_playback_evidence["evidenceBoundary"],
        "",
        f"Audit: `{lua_playback_evidence['auditReport']}` "
        f"SHA-256 `{lua_playback_evidence['auditSha256']}`.",
    ])
    for row in lua_playback_evidence["acceptedExactPlaybackCalls"]:
        lines.append(
            f"- admitted `{row['storyKey']}` from `{row['luaFile']}:{row['luaLine']}` "
            f"(source SHA-256 `{row['luaSourceSha256']}`)"
        )
    for row in lua_playback_evidence["rejectedCaseMismatchCalls"]:
        lines.append(
            f"- rejected literal `{row['luaLiteral']}` for `{row['storyKey']}` "
            f"via `{row['auditReport']}`"
        )
    if root_playback_alias_rows:
        lines.extend([
            "",
            "## Exact CutsceneRoot playback aliases",
            "",
            "These rows prove root-to-TimelineAsset playback, not mission "
            "ownership or relative Story order.",
            "",
            "| root Story key | played TimelineAsset Story key | native mapping |",
            "| --- | --- | --- |",
        ])
        for row in root_playback_alias_rows:
            lines.append(
                f"| `{row['rootStoryKey']}` | "
                f"`{row['playableAssetStoryKey']}` | "
                f"`{row['nativeMappingId']}` |"
            )
    if native_playback_event_keys:
        lines.extend([
            "",
            "## Unlinked exact-native playback event families",
            "",
            "One Story file can occur under more than one decoded native event family.",
            "",
            "| native event | unique unlinked Story files |",
            "| --- | ---: |",
        ])
        for event_name, keys in sorted(
            native_playback_event_keys.items(),
            key=lambda item: (-len(item[1]), item[0]),
        ):
            lines.append(f"| `{event_name}` | {len(keys)} |")
    if missionless_nodes:
        lines.extend([
            "",
            "## Missionless original-data SubGame playback nodes",
            "",
            "These are exact SubGame/script/playback attachments, not mission-owned Story bindings.",
            "",
            "| SubGame | bound script | task ids | exact Story files | non-owning cross-references |",
            "| --- | ---: | --- | --- | --- |",
        ])
        for node in missionless_nodes:
            story_keys = ", ".join(f"`{row['key']}`" for row in node["storyFiles"])
            task_ids = ", ".join(f"`{value}`" for value in node["mainTaskIds"]) or "-"
            associations = ", ".join(
                f"`{row['relation']} -> {row['targetId']}`"
                for row in node.get("associations") or []
            ) or "-"
            lines.append(
                f"| `{node['subGameId']}` | `{node['bindScriptId']}` | {task_ids} | "
                f"{story_keys} | {associations} |"
            )
    if evidence_tier_counts:
        lines.extend([
            "",
            "## Explicit evidence tiers",
            "",
            "| tier | evidence rows | unique Story files |",
            "| --- | ---: | ---: |",
        ])
        for tier, row_count in sorted(evidence_tier_counts.items()):
            lines.append(
                f"| `{tier}` | {row_count} | {len(connected_keys_by_evidence_tier[tier])} |"
            )
    definition_classes = definition_only_classification["keysByClassification"]
    if definition_classes:
        lines.extend([
            "",
            "## Definition-only negative consumer classification",
            "",
            definition_only_classification["policy"],
            "",
            "| classification | files |",
            "| --- | ---: |",
        ])
        for classification, keys in definition_classes.items():
            lines.append(f"| `{classification}` | {len(keys)} |")
    lines.extend([
        "",
        "The JSON report contains the complete unlinked inventory and unresolved native-evidence keys.",
        "",
    ])
    (report_root / f"{stem}.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return report


def type_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.split(",", 1)[0].rsplit(".", 1)[-1]


def const_value(value: Any) -> Any:
    if isinstance(value, dict) and "constValue" in value:
        return value.get("constValue")
    return value


def iter_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from iter_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_dicts(child)


def natural_quest_key(value: str) -> tuple[str, int, str]:
    mission, marker, suffix = str(value).partition("_q#")
    try:
        number = int(suffix) if marker else 10**9
    except ValueError:
        number = 10**9
    return mission, number, suffix


def _serialized_branch_story_keys(value: Any) -> set[str]:
    """Collect only Story keys carried by serialized Branch playback records.

    The native Branch inventory is deliberately a typed, corpus-wide census.  A
    mission projection may use it only when the exact Story key is present on a
    playback arm (including nested typed controls); arbitrary strings such as
    action names, level ids, and file paths are not candidates.
    """
    keys: set[str] = set()

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            for field in ("playbackStoryKeys", "storyKeys"):
                values = node.get(field)
                if isinstance(values, str) and values:
                    keys.add(values)
                elif isinstance(values, list):
                    keys.update(
                        str(item) for item in values
                        if isinstance(item, str) and item
                    )
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(value)
    return keys


def _serialized_branch_controls(value: Any) -> list[dict[str, Any]]:
    """Return nested typed controls without relying on a control-name allowlist."""
    controls: list[dict[str, Any]] = []

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            if (
                isinstance(node.get("arms"), list)
                and ("controlKind" in node or "controlRuntimeMappingId" in node)
            ):
                controls.append(node)
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(value)
    return controls


def attach_serialized_branch_story_contexts(
    order_row: dict[str, Any],
    inventory_rows: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Project exact serialized Branch/Story intersections into one mission row.

    This is intentionally a projection, not an ownership or chronology rule:
    the only admission gate is an exact Story key shared by the mission's
    serialized Story nodes and the original LevelScript Branch census.  The
    complete typed row and its original-file evidence remain attached so the
    WebUI can show the unresolved native context without inventing a route.
    """
    projected = copy.deepcopy(order_row)
    inventory_rows = [
        row for row in inventory_rows
        if isinstance(row, dict)
    ]
    if not inventory_rows:
        return projected
    mission_story_keys = {
        str(node if isinstance(node, str) else node.get("key") or "")
        for node in order_row.get("nodes") or []
        if (isinstance(node, str) and node) or (isinstance(node, dict) and node.get("key"))
    }
    contexts: list[dict[str, Any]] = []
    seen: set[tuple[str, str, tuple[str, ...]]] = set()
    context_story_keys: set[str] = set()
    related_source_files: set[str] = set()
    multi_playback_count = 0

    for source_row in inventory_rows:
        serialized_story_keys = _serialized_branch_story_keys(source_row)
        mission_keys = serialized_story_keys & mission_story_keys
        if not mission_keys:
            continue
        dedupe_hash = str(source_row.get("sha256") or "")
        if not dedupe_hash:
            dedupe_hash = "|".join(
                sorted(
                    str(value).replace("\\", "/")
                    for value in source_row.get("sourceFiles") or []
                    if value
                )
            )
        dedupe_key = (
            dedupe_hash,
            str(source_row.get("branchLocalId") or ""),
            tuple(sorted(mission_keys)),
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        context = copy.deepcopy(source_row)
        context["relation"] = "serialized_branch_story_context"
        context["missionStoryKeys"] = sorted(mission_keys)
        context["externalStoryKeys"] = sorted(serialized_story_keys - mission_story_keys)
        context["ownership"] = False
        context["orderEvidence"] = False
        context["contextEvidenceBoundary"] = (
            "Exact serialized Branch playback keys intersect this mission's Story "
            "nodes. The original LevelScript, GameAssembly, and metadata files are "
            "attached for inspection; this context does not prove mission ownership, "
            "activation, arm exclusivity, or Story file order."
        )
        contexts.append(context)
        context_story_keys.update(mission_keys)
        related_source_files.update(
            str(related.get("sourceFile") or "")
            for related in source_row.get("relatedOriginalFiles") or []
            if isinstance(related, dict) and related.get("sourceFile")
        )
        multi_playback_count += int(
            int(source_row.get("playbackArmCount") or 0) > 1
        )
        multi_playback_count += sum(
            1
            for control in _serialized_branch_controls(source_row)
            if control.get("branchingStatus") == "multi_playback_arms"
        )

    contexts.sort(
        key=lambda row: (
            str(row.get("levelId") or ""),
            str(row.get("scriptId") or ""),
            str(row.get("branchLocalId") or ""),
            str(row.get("sha256") or ""),
            tuple(row.get("missionStoryKeys") or []),
        )
    )
    branches = projected.setdefault("branches", {})
    branches["nativeSerializedBranchContexts"] = contexts
    branches["nativeSerializedBranchContextEvidenceBoundary"] = (
        "These rows are exact serialized Branch playback contexts projected by Story "
        "key intersection. They retain original-file hashes but are not mission "
        "ownership, activation, arm exclusivity, or chronology evidence."
    )
    summary = projected.setdefault("summary", {})
    summary["nativeSerializedBranchContextCount"] = len(contexts)
    summary["nativeSerializedBranchContextStoryCount"] = len(context_story_keys)
    summary["nativeSerializedBranchContextMultiPlaybackCount"] = multi_playback_count
    summary["nativeSerializedBranchContextRelatedFileCount"] = len(related_source_files)
    return projected


def compact_scalar(value: Any) -> Any:
    value = const_value(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        scalars = [compact_scalar(item) for item in value[:12]]
        return [item for item in scalars if item is not None]
    if isinstance(value, dict):
        kept: dict[str, Any] = {}
        for key in sorted(value):
            item = compact_scalar(value[key])
            if item not in (None, "", [], {}):
                kept[str(key)] = item
            if len(kept) >= 12:
                break
        return kept
    return str(value)


FACT_KEYS = (
    "conditionEvalString",
    "_dialogId",
    "_finishId",
    "_submissionId",
    "_questId",
    "questId",
    "_targetQuestId",
    "_targetQuestState",
    "targetQuestState",
    "compareTarget",
    "_sceneId",
    "sceneId",
    "_levelId",
    "levelId",
    "_entityId",
    "entityId",
    "_scriptId",
    "scriptId",
    "_taskId",
    "taskId",
    "missionId",
    "missionVarName",
    "compareOperator",
    "_compareValue",
    "compareValue",
    "_comparer",
    "comparer",
    "_propertyKey",
    "_key",
    "_guideGroupId",
    "_completeType",
    "_areaId",
    "_mapId",
    "needAllKill",
)

_SUBMIT_ITEM_ROWS_CACHE: dict[str, Any] | None = None


def submit_item_requirements(submission_id: str) -> dict[str, Any]:
    """Return exact authored SubmitItem requirements for one submission id."""
    global _SUBMIT_ITEM_ROWS_CACHE
    if _SUBMIT_ITEM_ROWS_CACHE is None:
        payload = read_json(DEFAULT_SUBMIT_ITEM_TABLE)
        _SUBMIT_ITEM_ROWS_CACHE = payload if isinstance(payload, dict) else {}
    row = _SUBMIT_ITEM_ROWS_CACHE.get(submission_id)
    if not isinstance(row, dict):
        return {
            "submissionId": submission_id,
            "tableDefined": False,
            "requirementGroups": [],
        }
    groups: list[dict[str, Any]] = []
    for group_index, group in enumerate(row.get("paramData") or []):
        if not isinstance(group, dict):
            continue
        params = group.get("paramList") or []
        item_param = params[0] if len(params) > 0 and isinstance(params[0], dict) else {}
        count_param = params[1] if len(params) > 1 and isinstance(params[1], dict) else {}
        item_ids = [
            str(value)
            for value in item_param.get("valueStringList") or []
            if value not in (None, "")
        ]
        counts = [
            int(value)
            for value in count_param.get("valueIntList") or []
            if isinstance(value, (int, float))
        ]
        items = [{
            "itemId": item_id,
            "count": counts[index] if index < len(counts) else (
                counts[0] if counts else None
            ),
        } for index, item_id in enumerate(item_ids)]
        groups.append({
            "index": group_index + 1,
            "type": group.get("type"),
            "items": items,
        })
    return {
        "submissionId": submission_id,
        "tableDefined": True,
        "requirementGroups": groups,
    }


def submission_dialog_co_gates(condition: Any) -> list[dict[str, Any]]:
    """Find direct SubmitItem + dialog-finish siblings under authored AND groups."""
    output: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        if not isinstance(value, dict):
            return
        children = [
            child
            for child in value.get("subConditions") or []
            if isinstance(child, dict)
        ]
        expression = str(value.get("conditionEvalString") or "").lower()
        if children and "and" in expression:
            submissions = []
            dialogs = []
            for child in children:
                child_type = type_name(child.get("$type"))
                if child_type == "CheckQuestSubmitItem":
                    submission_id = get_const(
                        child, "_submissionId", "submissionId"
                    )
                    if isinstance(submission_id, str) and submission_id:
                        submissions.append(submission_id)
                elif child_type == "CheckTalkOptionFinish":
                    dialog_id = get_const(child, "_dialogId", "dialogId")
                    finish_id = get_const(child, "_finishId", "finishId")
                    if isinstance(dialog_id, str) and dialog_id:
                        dialogs.append((dialog_id, finish_id))
            for submission_id in submissions:
                for dialog_id, finish_id in dialogs:
                    output.append({
                        "submissionId": submission_id,
                        "dialogId": dialog_id,
                        "finishId": finish_id,
                        "combineConditionId": str(
                            value.get("uniqueId") or ""
                        ),
                        "relation": "same_authored_and_objective",
                    })
        for child in children:
            walk(child)

    walk(condition)
    return output


def submission_level_script_co_gates(condition: Any) -> list[dict[str, Any]]:
    """Find direct SubmitItem + LevelScript-stage siblings under authored AND groups."""
    output: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        if not isinstance(value, dict):
            return
        children = [
            child
            for child in value.get("subConditions") or []
            if isinstance(child, dict)
        ]
        expression = str(value.get("conditionEvalString") or "").lower()
        if children and "and" in expression:
            submissions: list[str] = []
            level_scripts: list[tuple[str, str, str]] = []
            for child in children:
                child_type = type_name(child.get("$type"))
                if child_type == "CheckQuestSubmitItem":
                    submission_id = get_const(
                        child, "_submissionId", "submissionId"
                    )
                    if isinstance(submission_id, str) and submission_id:
                        submissions.append(submission_id)
                elif child_type == "CheckLevelScriptStageReachMax":
                    level_id = get_const(child, "_levelId", "levelId")
                    script_id = get_const(child, "_scriptId", "scriptId")
                    if isinstance(script_id, dict):
                        script_id = script_id.get("scriptId")
                    if isinstance(script_id, (str, int)) and str(script_id):
                        level_scripts.append((
                            str(level_id or ""),
                            str(script_id),
                            str(child.get("uniqueId") or ""),
                        ))
            for submission_id in submissions:
                for level_id, script_id, condition_id in level_scripts:
                    output.append({
                        "submissionId": submission_id,
                        "levelId": level_id,
                        "scriptId": script_id,
                        "conditionId": condition_id,
                        "combineConditionId": str(
                            value.get("uniqueId") or ""
                        ),
                        "relation": "same_authored_and_objective",
                    })
        for child in children:
            walk(child)

    walk(condition)
    return output


def condition_tree(condition: Any) -> dict[str, Any] | None:
    if not isinstance(condition, dict):
        return None
    name = type_name(condition.get("$type")) or "UnknownCondition"
    facts = {
        key.lstrip("_"): compact_scalar(condition.get(key))
        for key in FACT_KEYS
        if condition.get(key) not in (None, "", [], {})
    }
    children: list[dict[str, Any]] = []
    for key in ("subConditions", "conditions", "conditionList"):
        for child in condition.get(key) or []:
            normalized = condition_tree(child)
            if normalized:
                children.append(normalized)
    row: dict[str, Any] = {"type": name}
    if facts:
        row["facts"] = facts
    if children:
        row["children"] = children
    return row


def vector3_row(value: Any) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    try:
        return {
            "x": float(value.get("x", 0.0)),
            "y": float(value.get("y", 0.0)),
            "z": float(value.get("z", 0.0)),
        }
    except (TypeError, ValueError):
        return None


def tracking_info_row(info: Any, index: int) -> dict[str, Any] | None:
    """Keep exact quest-marker configuration without creating graph edges."""
    if not isinstance(info, dict):
        return None
    row: dict[str, Any] = {
        "index": index,
        "type": type_name(info.get("$type")) or "TrackingInfo",
    }
    for key in (
        "sceneId",
        "npcProxyId",
        "missionAreaId",
        "jumpId",
        "trackScriptEntity",
        "entityLogicId",
        "scriptId",
        "entitySlotId",
        "guidingArea",
        "shapeType",
        "radius",
        "routePointCount",
        "snsDialogId",
        "useFilterCondition",
    ):
        if key in info and info[key] not in (None, "", [], {}):
            row[key] = compact_scalar(info[key])
        elif key in {"trackScriptEntity", "useFilterCondition"} and key in info:
            row[key] = bool(info[key])
    for key in ("trackingPos", "position", "rotation"):
        vector = vector3_row(info.get(key))
        if vector is not None:
            row[key] = vector
    filter_condition = condition_tree(info.get("filterCondition"))
    if filter_condition:
        row["filterCondition"] = filter_condition
    return row


def mission_property_rows(mission: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize authored mission-variable defaults without assigning writers."""
    output: list[dict[str, Any]] = []
    for raw in mission.get("properties") or []:
        if not isinstance(raw, dict) or raw.get("key") in (None, ""):
            continue
        value = raw.get("value") or {}
        values: list[dict[str, Any]] = []
        for item in value.get("valueArray") or []:
            if not isinstance(item, dict):
                continue
            values.append({
                key: item[key]
                for key in ("valueBit64", "valueString")
                if key in item
            })
        output.append({
            "key": str(raw["key"]),
            "type": value.get("type"),
            "values": values,
        })
    return output


def condition_objects(condition: Any) -> list[dict[str, Any]]:
    if not isinstance(condition, dict):
        return []
    return [row for row in iter_dicts(condition) if isinstance(row.get("$type"), str)]


def quest_condition_objects(quest: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for objective in quest.get("objectiveList") or []:
        if isinstance(objective, dict):
            rows.extend(condition_objects(objective.get("condition")))
    rows.extend(condition_objects(quest.get("failedCondition")))
    return rows


def classify_authority(condition_types: Iterable[str]) -> str:
    values = set(condition_types)
    classes: set[str] = set()
    if values & SERVER_CONDITION_TYPES:
        classes.add("server")
    if values & SYNC_HISTORY_TYPES:
        classes.add("synchronized_history")
    if values & SYNC_STATE_TYPES:
        classes.add("synchronized_state")
    if values - SERVER_CONDITION_TYPES - SYNC_HISTORY_TYPES - SYNC_STATE_TYPES:
        classes.add("client_observed")
    if not classes:
        return "unknown"
    if len(classes) == 1:
        return next(iter(classes))
    return "mixed"


def get_const(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row:
            return const_value(row.get(key))
    return None


def level_script_task_dependencies(condition: Any) -> list[dict[str, Any]]:
    """Recover every exact scene/script/task tuple by authored field shape.

    This deliberately does not enumerate missions, scripts, tasks, or condition
    classes. A condition joins the task corpus only when all three serialized
    identity fields are present and scalar after const-wrapper decoding.
    """
    dependencies: list[dict[str, Any]] = []
    for row in condition_objects(condition):
        level_id = get_const(row, "_sceneId", "sceneId", "_levelId", "levelId")
        script_id = get_const(row, "_scriptId", "scriptId")
        task_id = get_const(row, "_taskId", "taskId")
        if isinstance(script_id, dict):
            script_id = script_id.get("scriptId")
        if not all(isinstance(value, (str, int)) and str(value) for value in (
            level_id, script_id, task_id
        )):
            continue
        dependencies.append({
            "conditionType": type_name(row.get("$type")) or "UnknownCondition",
            "conditionId": str(row.get("uniqueId") or ""),
            "levelId": str(level_id),
            "scriptId": str(script_id),
            "taskId": str(task_id),
            "relation": "mission_objective_waits_for_levelscript_task",
            "runtimeAuthorityReference": "runtimeContract.levelScriptTaskAuthorityAudit",
            "evidenceBoundary": (
                "The authored mission objective waits for this exact LevelScript "
                "task. This does not prove that the mission activates the script, "
                "owns its Story playback, or selects a Story branch."
            ),
        })
    return dependencies


_LEVEL_SCRIPT_NATIVE_CONTROL_EVIDENCE_CACHE: dict[str, dict[str, Any]] = {}


def resolve_active_level_script_source(
    level_id: str,
    script_id: str,
    *,
    level_script_root: Path = DEFAULT_LEVEL_SCRIPT_DATA_ROOT,
    level_script_roots: Iterable[Path] | None = None,
) -> tuple[Path | None, dict[str, Any]]:
    """Resolve one logical LevelScript through an ordered source overlay.

    Roots are fallback-to-override.  Default production lookup therefore uses
    StreamingAssets followed by Persistent, while callers that pass a custom
    singular root keep the historical one-root behavior unless they explicitly
    provide ``level_script_roots``.
    """
    if level_script_roots is None:
        roots = (
            DEFAULT_LEVEL_SCRIPT_DATA_ROOTS
            if level_script_root == DEFAULT_LEVEL_SCRIPT_DATA_ROOT
            else (level_script_root,)
        )
    else:
        roots = tuple(Path(root) for root in level_script_roots)
    if not roots:
        return None, {
            "rule": "later root wins",
            "searchedSources": [],
            "activeSourceFile": None,
            "shadowedSources": [],
        }

    candidates: list[dict[str, Any]] = []
    searched: list[str] = []
    for priority, root in enumerate(roots):
        path = root / level_id / f"{script_id}.json"
        searched.append(repo_path(path))
        if path.is_file():
            candidates.append({
                "priority": priority,
                "sourceFile": repo_path(path),
                "sha256": sha256_path(path),
                "path": path,
            })
    active = candidates[-1] if candidates else None
    shadowed = [
        {
            "priority": row["priority"],
            "sourceFile": row["sourceFile"],
            "sha256": row["sha256"],
            "sameBytesAsActive": bool(
                active and row["sha256"] == active["sha256"]
            ),
        }
        for row in candidates[:-1]
    ]
    return (
        active["path"] if active else None,
        {
            "rule": "later root wins; Persistent overrides StreamingAssets",
            "searchedSources": searched,
            "activeSourceFile": active["sourceFile"] if active else None,
            "activeSha256": active["sha256"] if active else None,
            "activePriority": active["priority"] if active else None,
            "shadowedSources": shadowed,
            "changedOverride": any(
                not row["sameBytesAsActive"] for row in shadowed
            ),
        },
    )


def level_script_native_control_evidence(
    data: bytes,
    source_path: Path,
) -> dict[str, Any]:
    """Summarize every binary-mapped typed control in one original script.

    This is intentionally corpus-driven.  The action decoder owns the set of
    native control families and their serialized fields; this helper only
    projects those decoded rows into a compact mission-context attachment.
    Event-root reachability is exact within this file.  It is never treated as
    Story ownership or inter-file order evidence.
    """
    cache_key = str(source_path.resolve())
    cached = _LEVEL_SCRIPT_NATIVE_CONTROL_EVIDENCE_CACHE.get(cache_key)
    if cached is not None:
        return copy.deepcopy(cached)
    topology, diagnostic = decode_levelscript_native_action_topology(data)
    if not isinstance(topology, dict):
        topology = {
            "schema": "levelScriptNativeActionTopology.v4",
            "status": "unavailable_fail_closed",
            "actionControlFlowEvidence": False,
            "storyOrderEvidence": False,
        }

    # Build only the action-to-action adjacency.  Event roots are kept as
    # independent invocation sources and are joined to controls by exact
    # serialized reachability, not by physical record order.
    adjacency: dict[int, list[int]] = defaultdict(list)
    for edge in topology.get("edges") or []:
        if edge.get("sourceKind") != "action":
            continue
        source_id = edge.get("sourceLocalId")
        target_id = edge.get("targetActionLocalId")
        if isinstance(source_id, int) and isinstance(target_id, int) and target_id > 0:
            adjacency[source_id].append(target_id)
    roots_by_action: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for root in topology.get("eventRoots") or []:
        start_id = root.get("nextActionLocalId")
        if not isinstance(start_id, int) or start_id <= 0:
            continue
        root_ref = {
            key: root[key]
            for key in ("localId", "headerName", "nextActionLocalId")
            if root.get(key) not in (None, "", [], {})
        }
        queue = deque([start_id])
        visited: set[int] = set()
        while queue:
            local_id = queue.popleft()
            if local_id in visited:
                continue
            visited.add(local_id)
            roots_by_action[local_id].append(root_ref)
            queue.extend(adjacency.get(local_id) or [])

    controls: list[dict[str, Any]] = []
    family_counts: Counter[str] = Counter()
    for action in topology.get("actions") or []:
        if not isinstance(action, dict):
            continue
        control_kind = str(action.get("controlKind") or "")
        mapping_id = action.get("controlRuntimeMappingId")
        if not control_kind and not mapping_id:
            continue
        if control_kind:
            family_counts[control_kind] += 1
        local_id = action.get("localId")
        outgoing = [
            edge
            for edge in topology.get("edges") or []
            if edge.get("sourceKind") == "action"
            and edge.get("sourceLocalId") == local_id
        ]
        outgoing.extend(
            edge
            for edge in topology.get("runtimeTerminalTargets") or []
            if edge.get("sourceKind") == "action"
            and edge.get("sourceLocalId") == local_id
        )
        rows = {
            "localId": local_id,
            "actionName": action.get("actionName"),
            "controlKind": control_kind,
            "controlRuntimeMappingId": mapping_id,
            "controlDetail": action.get("controlDetail") or {},
            "serializedOutgoingEdges": outgoing,
            "eventRoots": sorted(
                roots_by_action.get(local_id) or [],
                key=lambda row: (
                    int(row.get("localId") or 0),
                    int(row.get("nextActionLocalId") or 0),
                ),
            ),
            "reachability": (
                "exact_serialized_event_to_control"
                if roots_by_action.get(local_id)
                else "serialized_control_without_decoded_event_root"
            ),
        }
        controls.append({
            key: value
            for key, value in rows.items()
            if value not in (None, "", [], {})
        })
    controls.sort(key=lambda row: int(row.get("localId") or 0))
    result: dict[str, Any] = {
        "schema": "levelScriptNativeControlEvidence.v1",
        "topologySchema": topology.get("schema"),
        "status": topology.get("status"),
        "controlCount": len(controls),
        "controlFamilyCounts": dict(sorted(family_counts.items())),
        "eventRootCount": int(topology.get("eventRootCount") or 0),
        "eventToControlReachableCount": sum(
            1 for row in controls if row.get("eventRoots")
        ),
        "controls": controls,
        "actionControlFlowEvidence": bool(
            topology.get("actionControlFlowEvidence")
        ),
        "storyOrderEvidence": bool(topology.get("storyOrderEvidence")),
        "nativeActionMappingId": topology.get("nativeActionMappingId"),
        "evidenceBoundary": (
            "The original binary decoder identifies typed control families and "
            "exact serialized event-to-control reachability inside this one "
            "LevelScript. MissionRuntime condition references establish mission "
            "context only; these controls do not prove Story playback ownership "
            "or inter-file Story order."
        ),
    }
    if diagnostic:
        result["validatorDiagnostic"] = diagnostic
    _LEVEL_SCRIPT_NATIVE_CONTROL_EVIDENCE_CACHE[cache_key] = result
    return copy.deepcopy(result)


def level_script_source_evidence(
    condition: Any,
    *,
    level_script_root: Path = DEFAULT_LEVEL_SCRIPT_DATA_ROOT,
    level_script_roots: Iterable[Path] | None = None,
) -> list[dict[str, Any]]:
    """Attach exact authored LevelScript files and executable-map boundaries.

    The join is field-shaped across the entire condition corpus: any condition
    carrying both a level/map identity and a LevelScript identity is eligible.
    Story-like literals outside the three decoded ActionSerializedMap lists are
    retained only as serialized context and never promoted to playback/order.
    """
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in condition_objects(condition):
        level_id = get_const(row, "_sceneId", "sceneId", "_levelId", "levelId", "_mapId", "mapId")
        script_id = get_const(row, "_scriptId", "scriptId")
        if isinstance(script_id, dict):
            script_id = script_id.get("scriptId")
        if not all(isinstance(value, (str, int)) and str(value) for value in (level_id, script_id)):
            continue
        identity = (str(level_id), str(script_id))
        if identity in seen:
            continue
        seen.add(identity)
        source_path, overlay = resolve_active_level_script_source(
            identity[0],
            identity[1],
            level_script_root=level_script_root,
            level_script_roots=level_script_roots,
        )
        if source_path is None:
            raise RuntimeError(
                "validator=level_script_source_evidence gate=levelScriptExists "
                f"condition={row.get('uniqueId') or '-'} identity={identity[0]}/{identity[1]} "
                "expected=active_overlay_file actual=missing "
                f"sources={overlay['searchedSources']!r}"
            )
        data = read_bytes_cached(source_path)
        records = extract_levelscript_uid_records(data)
        action_map = decode_levelscript_action_map_lists(data, records)
        native_control_evidence = level_script_native_control_evidence(
            data,
            source_path,
        )
        exact_empty = bool(action_map.get("exactEmptyActionMap"))
        out.append({
            "levelId": identity[0],
            "scriptId": identity[1],
            "conditionType": type_name(row.get("$type")) or "UnknownCondition",
            "actionMapStatus": (
                "exact_empty_action_map"
                if exact_empty
                else str(action_map.get("status") or "absent")
            ),
            "actionMapListCounts": action_map.get("listCounts") or {},
            "serializedTailRecordCount": sum(
                int(item.get("count") or 0)
                for item in action_map.get("serializedLists") or []
                if item.get("name") == "outsideSerializedActionMap"
            ),
            "levelScriptOverlay": overlay,
            "nativeControlEvidence": native_control_evidence,
            "relatedOriginalFiles": [{
                "kind": "level_script",
                "sourceFile": repo_path(source_path),
                "relationship": "authored_condition_operand_active_overlay",
                "sha256": sha256_path(source_path),
            }],
            "evidenceBoundary": (
                "The three original serialized action-list counts are exactly zero. "
                "Later UID-shaped objects and Story-like strings are outside the "
                "executable action map and provide no playback, ownership, branch, or order evidence."
                if exact_empty
                else "Only records inside the decoded ActionSerializedMap lists are executable evidence; the condition observes this script but does not prove playback ownership, branch selection, or Story order."
            ),
        })
    return out


def validate_level_script_task_dependency(
    dependency: dict[str, Any],
    *,
    mission_id: str,
    quest_id: str,
    mission_source: Path,
    task_table_path: Path = DEFAULT_SCRIPT_TASK_EXTRA_INFO_TABLE,
    level_script_root: Path = DEFAULT_LEVEL_SCRIPT_DATA_ROOT,
    level_script_roots: Iterable[Path] | None = None,
) -> dict[str, Any]:
    """Fail closed while joining an authored tuple to original serialized files."""
    validator = "level_script_task_dependency"
    level_id = str(dependency.get("levelId") or "")
    script_id = str(dependency.get("scriptId") or "")
    task_id = str(dependency.get("taskId") or "")
    identity = f"{level_id}/{script_id}/{task_id}"
    if not task_table_path.is_file():
        raise RuntimeError(
            f"validator={validator} gate=taskTableExists mission={mission_id} "
            f"quest={quest_id} identity={identity} expected=file actual=missing "
            f"source={task_table_path}"
        )
    table_payload = read_json(task_table_path)
    table = table_payload.get("dataTable") if isinstance(table_payload, dict) else None
    task_row = (
        (((table or {}).get(level_id) or {}).get(script_id) or {}).get(task_id)
        if isinstance(table, dict) else None
    )
    if not isinstance(task_row, dict):
        raise RuntimeError(
            f"validator={validator} gate=taskTuple mission={mission_id} "
            f"quest={quest_id} identity={identity} expected=authored_task_row "
            f"actual=missing source={task_table_path} "
            f"sourceHashes={{'taskTable':'{sha256_path(task_table_path)}'}}"
        )
    level_script_path, overlay = resolve_active_level_script_source(
        level_id,
        script_id,
        level_script_root=level_script_root,
        level_script_roots=level_script_roots,
    )
    if level_script_path is None:
        raise RuntimeError(
            f"validator={validator} gate=levelScriptExists mission={mission_id} "
            f"quest={quest_id} identity={identity} expected=file actual=missing "
            f"sources={overlay['searchedSources']!r} "
            f"sourceHashes={{'taskTable':'{sha256_path(task_table_path)}'}}"
        )

    related: list[dict[str, Any]] = []
    for kind, path, relationship in (
        ("mission_runtime", mission_source, "authored_objective_condition"),
        ("level_script", level_script_path, "exact_task_host"),
        ("script_task_extra_info_table", task_table_path, "exact_task_metadata"),
    ):
        if not path.is_file():
            raise RuntimeError(
                f"validator={validator} gate=relatedOriginalFile mission={mission_id} "
                f"quest={quest_id} identity={identity} expected=file actual=missing "
                f"source={path}"
            )
        related.append({
            "kind": kind,
            "sourceFile": repo_path(path),
            "relationship": relationship,
            "sha256": sha256_path(path),
        })
    result = dict(dependency)
    result.update({
        "taskMetadata": {
            "titleKey": ((task_row.get("taskTitle") or {}).get("key") or ""),
            "descriptionKey": (
                (task_row.get("singleDescription") or {}).get("key") or ""
            ),
            "objectiveCount": task_row.get("objectiveCount"),
        },
        "relatedOriginalFiles": related,
        "levelScriptOverlay": overlay,
        "validation": {"status": "validated", "validator": validator},
    })
    return result


def objective_row(
    objective: dict[str, Any],
    index: int,
    *,
    include_level_script_source_evidence: bool = True,
) -> dict[str, Any]:
    condition = objective.get("condition")
    objects = condition_objects(condition)
    types = sorted({type_name(row.get("$type")) for row in objects if type_name(row.get("$type"))})
    dialog_finishes: list[dict[str, Any]] = []
    quest_state_refs: list[dict[str, Any]] = []
    level_scripts: set[str] = set()
    properties: set[str] = set()
    server_placeholder_condition_ids: set[str] = set()
    submission_checks: list[dict[str, Any]] = []
    for row in objects:
        name = type_name(row.get("$type"))
        if name == "GameConditionServerPlaceHolder":
            condition_id = row.get("uniqueId")
            if condition_id not in (None, ""):
                server_placeholder_condition_ids.add(str(condition_id))
        if name == "CheckTalkOptionFinish":
            dialog = get_const(row, "_dialogId", "dialogId")
            finish = get_const(row, "_finishId", "finishId")
            if isinstance(dialog, str):
                dialog_finishes.append({"dialogId": dialog, "finishId": finish})
        if name == "CheckQuestSubmitItem":
            submission_id = get_const(row, "_submissionId", "submissionId")
            if isinstance(submission_id, str) and submission_id:
                submission_check = submit_item_requirements(submission_id)
                submission_check["conditionId"] = str(row.get("uniqueId") or "")
                submission_checks.append(submission_check)
        if name in {"CheckQuestState", "SimpleConditionCheckQuestState"}:
            quest_id = get_const(row, "_questId", "questId", "_targetQuestId", "targetQuestId")
            state = get_const(row, "_targetQuestState", "targetQuestState", "compareTarget")
            if isinstance(quest_id, str):
                quest_state_refs.append({"questId": quest_id, "state": state})
        script = get_const(row, "_scriptId", "scriptId")
        if isinstance(script, dict):
            script = script.get("scriptId")
        if isinstance(script, (str, int)):
            level_scripts.add(str(script))
        prop = get_const(row, "_propertyKey", "propertyKey", "_key", "key")
        if isinstance(prop, str):
            properties.add(prop)
    description = objective.get("description") or {}
    tracking = [
        normalized
        for tracking_index, info in enumerate(
            objective.get("trackingInfoList") or []
        )
        if (
            normalized := tracking_info_row(info, tracking_index)
        ) is not None
    ]
    return {
        "index": index,
        "conditionId": condition.get("uniqueId") if isinstance(condition, dict) else "",
        "descriptionKey": description.get("key") if isinstance(description, dict) else "",
        "multiple": bool(objective.get("multiple")),
        "condition": condition_tree(condition),
        "conditionTypes": types,
        "authority": classify_authority(types),
        "serverPlaceholderConditionIds": sorted(server_placeholder_condition_ids),
        "dialogFinishes": dialog_finishes,
        "submissionChecks": submission_checks,
        "submissionDialogCoGates": submission_dialog_co_gates(condition),
        "submissionLevelScriptCoGates": submission_level_script_co_gates(
            condition
        ),
        "questStateRefs": quest_state_refs,
        "levelScriptIds": sorted(level_scripts),
        "levelScriptSources": (
            level_script_source_evidence(condition)
            if include_level_script_source_evidence
            else []
        ),
        "levelScriptTaskDependencies": level_script_task_dependencies(condition),
        "propertyKeys": sorted(properties),
        "tracking": tracking,
    }


def action_rows(mission: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    action_by_id: dict[Any, dict[str, Any]] = {}
    next_action_by_id: dict[Any, Any] = {}
    data_map = ((mission.get("actionMapRaw") or {}).get("dataMap") or {})
    for action in data_map.get("actionList") or []:
        if not isinstance(action, dict):
            continue
        action_id = action.get("_ID")
        facts = {
            key.lstrip("_"): compact_scalar(value)
            for key, value in action.items()
            if key not in {"$type", "_ID", "_uid"} and value not in (None, "", [], {})
        }
        action_by_id[action_id] = {
            "id": action_id,
            "type": type_name(action.get("$type")) or "UnknownAction",
            "facts": facts,
        }
        next_action_by_id[action_id] = action.get("_nextID")
    keys = mission.get("clientActionMapKey") or []
    values = mission.get("clientActionMapValue") or []
    output: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, key in enumerate(keys):
        if not isinstance(key, dict):
            continue
        quest_id = key.get("questId")
        if not isinstance(quest_id, str):
            continue
        root_action_id = values[index] if index < len(values) else None
        action_id = root_action_id
        seen_action_ids: set[Any] = set()
        chain_index = 0
        while action_id not in seen_action_ids:
            seen_action_ids.add(action_id)
            action = dict(action_by_id.get(action_id) or {"id": action_id, "type": "UnknownAction"})
            action["trigger"] = key.get("action")
            action["triggerName"] = QUEST_ACTION_TRIGGERS.get(key.get("action"), "UnknownQuestAction")
            action["rootActionId"] = root_action_id
            action["chainIndex"] = chain_index
            output[quest_id].append(action)
            next_action_id = next_action_by_id.get(action_id)
            if not isinstance(next_action_id, int) or next_action_id < 0:
                break
            action_id = next_action_id
            chain_index += 1
    return dict(output)


def annotate_quest_action_dispatch(
    payload: dict[str, Any],
    contract: dict[str, Any],
) -> Counter[str]:
    """Apply the corpus-wide binary dispatcher census to authored action rows."""
    dispatched = {
        int(row["questActionValue"]): row
        for row in contract.get("safeRunDirectCallers") or []
        if isinstance(row, dict) and isinstance(row.get("questActionValue"), int)
    }
    start_value = int(
        (contract.get("questActionEnum") or {}).get("OnStartClientAction", 1)
    )
    start_dispatchers = contract.get("startActionDispatchers") or []
    counts: Counter[str] = Counter()
    for node in payload.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        for action in node.get("clientActions") or []:
            if not isinstance(action, dict):
                continue
            value = action.get("trigger")
            if value in dispatched:
                caller = dispatched[value]
                status = (
                    "binary_proven_server_success_dispatch"
                    if value == 2
                    else "binary_proven_server_failure_dispatch"
                )
                action["runtimeDispatchHandler"] = caller.get("symbol") or ""
            elif value == start_value and not start_dispatchers:
                status = "authored_definition_no_current_aot_dispatch"
            else:
                status = "runtime_dispatch_unresolved"
            action["runtimeDispatchStatus"] = status
            action["runtimeDispatchSource"] = contract.get("source") or ""
            action["runtimeDispatchBoundary"] = contract.get("boundary") or ""
            counts[f"rows:{status}"] += 1
            if action.get("chainIndex") == 0:
                counts[f"roots:{status}"] += 1
    return counts


def annotate_quest_fork_state_application(
    payload: dict[str, Any],
    contract: dict[str, Any],
) -> Counter[str]:
    """Attach one binary-discovered state application shape to every fork arm."""
    validator = "quest_fork_state_application"
    if contract.get("schema") != "questStateLifecycleApplication.v1":
        raise RuntimeError(
            f"validator={validator} gate=contractSchema "
            "expected='questStateLifecycleApplication.v1' "
            f"actual={contract.get('schema')!r}"
        )
    if (contract.get("validation") or {}).get("status") != "validated":
        failure = ((contract.get("validation") or {}).get("failures") or [{}])[0]
        raise RuntimeError(
            f"validator={validator} gate={failure.get('gate') or 'contractValidation'} "
            f"expected={failure.get('expected')!r} actual={failure.get('actual')!r} "
            f"source={failure.get('sourceFile') or contract.get('source') or ''}"
        )
    message = contract.get("message") or {}
    identity_field = str(message.get("identityField") or "")
    transitions = contract.get("transitions") or []
    if not identity_field or not transitions or message.get("successorLikeFields"):
        raise RuntimeError(
            f"validator={validator} gate=applicationShape "
            "expected='identity field, state routes, no successor fields' "
            f"actual={{'identityField': {identity_field!r}, "
            f"'transitionCount': {len(transitions)}, "
            f"'successorLikeFields': {message.get('successorLikeFields') or []!r}}}"
        )
    compact_contract = {
        "schema": contract.get("schema"),
        "classification": contract.get("classification"),
        "message": {
            "type": message.get("type"),
            "messageId": message.get("messageId"),
            "identityField": identity_field,
            "stateField": message.get("stateField"),
            "successorLikeFields": [],
            "handler": message.get("handler") or {},
        },
        "stateEnum": contract.get("stateEnum") or {},
        "transitions": transitions,
        "source": contract.get("source") or "",
        "relatedOriginalFiles": contract.get("relatedOriginalFiles") or [],
        "finding": contract.get("finding") or "",
        "boundary": contract.get("boundary") or "",
    }
    counts: Counter[str] = Counter()
    forks = ((payload.get("questTopology") or {}).get("forks") or [])
    for fork in forks:
        if not isinstance(fork, dict):
            continue
        fork["serverQuestStateApplication"] = compact_contract
        counts["forks"] += 1
        for arm in fork.get("arms") or []:
            if not isinstance(arm, dict) or not arm.get("questId"):
                raise RuntimeError(
                    f"validator={validator} gate=armQuestIdentity "
                    f"expected=non-empty actual={arm!r}"
                )
            arm["serverApplicationIdentity"] = {
                "field": identity_field,
                "value": str(arm["questId"]),
                "contractReference": (
                    "runtimeContract.stateUpdateApplicationAudit."
                    "questStateLifecycleApplication"
                ),
            }
            counts["arms"] += 1
    return counts


def annotate_quest_fork_enable_application(
    payload: dict[str, Any],
    contract: dict[str, Any],
) -> Counter[str]:
    """Attach a corpus-derived boolean lifecycle matrix to every quest fork."""
    validator = "quest_fork_enable_application"
    if contract.get("schema") != "questEnableLifecycleApplication.v1":
        raise RuntimeError(
            f"validator={validator} gate=contractSchema "
            "expected='questEnableLifecycleApplication.v1' "
            f"actual={contract.get('schema')!r}"
        )
    if (contract.get("validation") or {}).get("status") != "validated":
        failure = ((contract.get("validation") or {}).get("failures") or [{}])[0]
        raise RuntimeError(
            f"validator={validator} gate={failure.get('gate') or 'contractValidation'} "
            f"expected={failure.get('expected')!r} actual={failure.get('actual')!r} "
            f"source={failure.get('sourceFile') or contract.get('source') or ''}"
        )
    message = contract.get("message") or {}
    runtime_control = contract.get("runtimeControl") or {}
    identity_field = str(message.get("identityField") or "")
    packet_fields = message.get("consumedControlFields") or []
    runtime_field = str(runtime_control.get("field") or "")
    routes = contract.get("routes") or []
    matrix = sorted({
        (
            (route.get("values") or {}).get(packet_fields[0]),
            (route.get("values") or {}).get(runtime_field),
        )
        for route in routes
    }) if len(packet_fields) == 1 and runtime_field else []
    expected_matrix = [
        (False, False), (False, True), (True, False), (True, True)
    ]
    route_calls = [
        route.get("reachableLifecycleCalls") or [] for route in routes
    ]
    if (
        not identity_field
        or matrix != expected_matrix
        or not route_calls
        or not all(len(calls) == 1 for calls in route_calls)
        or len({calls[0].get("method") for calls in route_calls}) < 3
        or not all(calls[0].get("samePacketIdentity") is True for calls in route_calls)
        or message.get("successorLikeFields")
    ):
        raise RuntimeError(
            f"validator={validator} gate=applicationShape "
            "expected='complete generic two-boolean identity-preserving matrix, "
            "one call per route, >=3 methods, no successor fields' "
            f"actual={{'identityField': {identity_field!r}, 'matrix': {matrix!r}, "
            f"'routeCalls': {route_calls!r}, "
            f"'successorLikeFields': {message.get('successorLikeFields') or []!r}}}"
        )
    compact_contract = {
        "schema": contract.get("schema"),
        "classification": contract.get("classification"),
        "message": {
            "type": message.get("type"),
            "messageId": message.get("messageId"),
            "identityField": identity_field,
            "consumedControlFields": packet_fields,
            "unreadControlFields": message.get("unreadControlFields") or [],
            "successorLikeFields": [],
            "handler": message.get("handler") or {},
        },
        "runtimeControl": runtime_control,
        "routes": routes,
        "source": contract.get("source") or "",
        "relatedOriginalFiles": contract.get("relatedOriginalFiles") or [],
        "finding": contract.get("finding") or "",
        "boundary": contract.get("boundary") or "",
    }
    counts: Counter[str] = Counter()
    for fork in ((payload.get("questTopology") or {}).get("forks") or []):
        if not isinstance(fork, dict):
            continue
        fork["serverQuestEnableApplication"] = compact_contract
        counts["forks"] += 1
        for arm in fork.get("arms") or []:
            if not isinstance(arm, dict) or not arm.get("questId"):
                raise RuntimeError(
                    f"validator={validator} gate=armQuestIdentity "
                    f"expected=non-empty actual={arm!r}"
                )
            arm["serverEnableApplicationIdentity"] = {
                "field": identity_field,
                "value": str(arm["questId"]),
                "contractReference": (
                    "runtimeContract.stateUpdateApplicationAudit."
                    "questEnableLifecycleApplication"
                ),
            }
            counts["arms"] += 1
    return counts


def _quest_reachability_distances(
    start: str,
    successors: dict[str, list[str]],
) -> dict[str, int]:
    """Return shortest authored-predecessor distances from one quest arm."""
    distances = {start: 0}
    pending = deque([start])
    while pending:
        current = pending.popleft()
        for target in successors.get(current, []):
            if target in distances:
                continue
            distances[target] = distances[current] + 1
            pending.append(target)
    return distances


def build_quest_fork_semantics(
    nodes: list[dict[str, Any]],
    source_path: Path,
) -> dict[str, Any]:
    """Describe every authored quest fan-out without guessing activation policy.

    This is intentionally data-driven. It derives arm roles, typed completion
    conditions, terminal status, and first common descendants from normalized
    MissionRuntime nodes. The original MissionRuntime file is attached to each
    fork. Main-path membership and flowIndex are descriptive fields only; the
    installed binary audit remains the authority that neither selects arms.
    """
    nodes_by_id = {
        str(node.get("id") or ""): node
        for node in nodes
        if isinstance(node, dict) and node.get("id")
    }
    successors = {
        quest_id: [
            str(target)
            for target in node.get("successors") or []
            if str(target)
        ]
        for quest_id, node in nodes_by_id.items()
    }
    source_file = repo_path(source_path)
    source_hash = sha256_path(source_path) if source_path.is_file() else ""
    related_files = [{
        "kind": "mission_runtime",
        "sourceFile": source_file,
        "relationship": "authored_quest_fork_topology",
        "sha256": source_hash,
    }]
    failures: list[dict[str, Any]] = []

    def fail(
        gate: str,
        quest_id: str,
        expected: Any,
        actual: Any,
    ) -> None:
        failures.append({
            "validator": "quest_fork_semantics",
            "gate": gate,
            "mission": source_path.stem,
            "questId": quest_id,
            "expected": expected,
            "actual": actual,
            "sourceFile": source_file,
            "sourceHashes": {"missionRuntimeSha256": source_hash},
        })

    forks: list[dict[str, Any]] = []
    for quest_id in sorted(nodes_by_id, key=natural_quest_key):
        arm_ids = successors.get(quest_id, [])
        if len(arm_ids) < 2:
            continue
        missing = [arm_id for arm_id in arm_ids if arm_id not in nodes_by_id]
        if missing:
            fail("allForkArmsResolve", quest_id, [], missing)
            continue
        arm_distances = [
            _quest_reachability_distances(arm_id, successors)
            for arm_id in arm_ids
        ]
        common_descendants = (
            set.intersection(*(set(row) for row in arm_distances))
            if arm_distances else set()
        )
        first_common = None
        if common_descendants:
            common_id = min(
                common_descendants,
                key=lambda candidate: (
                    max(row[candidate] for row in arm_distances),
                    sum(row[candidate] for row in arm_distances),
                    natural_quest_key(candidate),
                ),
            )
            first_common = {
                "questId": common_id,
                "distanceByArm": {
                    arm_id: arm_distances[index][common_id]
                    for index, arm_id in enumerate(arm_ids)
                },
                "predecessorQuestIds": list(
                    nodes_by_id[common_id].get("prev") or []
                ),
            }

        arms: list[dict[str, Any]] = []
        for arm_index, arm_id in enumerate(arm_ids):
            node = nodes_by_id[arm_id]
            failed_condition = node.get("failedCondition") or None
            sibling_reachable = set().union(*(
                set(row)
                for index, row in enumerate(arm_distances)
                if index != arm_index
            ))
            sibling_exclusive = sorted(
                set(arm_distances[arm_index]) - sibling_reachable,
                key=lambda candidate: (
                    arm_distances[arm_index][candidate],
                    natural_quest_key(candidate),
                ),
            )
            objective_condition_types = sorted({
                str(condition_type)
                for objective in node.get("objectives") or []
                if isinstance(objective, dict)
                for condition_type in objective.get("conditionTypes") or []
                if str(condition_type)
            })
            arms.append({
                "questId": arm_id,
                "role": "main_path" if node.get("mainPath") else "auxiliary",
                "mainPathOrder": node.get("mainPathOrder"),
                "flowIndex": node.get("flowIndex", 0),
                "flowIndexRole": "display_sort_only",
                "questType": node.get("questType"),
                "showMode": node.get("showMode"),
                "objectiveConditionTypes": objective_condition_types,
                "failedCondition": failed_condition,
                "terminal": not bool(successors.get(arm_id)),
                "successorQuestIds": successors.get(arm_id, []),
                "siblingExclusiveQuestIds": sibling_exclusive,
                "corridorEvidenceBoundary": (
                    "These quests are reachable from this immediate successor and "
                    "not from another immediate successor of the same authored fork. "
                    "This is sibling-relative topology, not proof that the server "
                    "selected or exclusively executed this arm."
                ),
            })

        main_path_count = sum(arm["role"] == "main_path" for arm in arms)
        if main_path_count == 1:
            structure = "main_path_plus_auxiliary"
        elif main_path_count == 0:
            structure = "all_auxiliary"
        elif main_path_count == len(arms):
            structure = "multiple_main_path_successors"
        else:
            structure = "multiple_main_path_plus_auxiliary"
        terminal_count = sum(bool(arm["terminal"]) for arm in arms)
        if first_common:
            outcome = "reconverging"
        elif terminal_count == len(arms):
            outcome = "divergent_terminals"
        elif terminal_count:
            outcome = "mixed_terminal_and_continuing"
        else:
            outcome = "open_divergence"
        forks.append({
            "questId": quest_id,
            "successorQuestIds": arm_ids,
            "source": "MissionRuntimeAsset.questDic[*].prevQuestIdList",
            "structure": structure,
            "outcome": outcome,
            "arms": arms,
            "guardedArmCount": sum(bool(arm["failedCondition"]) for arm in arms),
            "firstCommonDescendant": first_common,
            "activationPolicy": "server_selected_unresolved",
            "relatedOriginalFiles": related_files,
            "evidenceBoundary": (
                "Main-path membership, predecessor topology, typed completion "
                "conditions, and reconvergence are authored facts. They do not "
                "prove that arms start in parallel or are mutually exclusive; "
                "flowIndex is display sorting in the current binary."
            ),
        })

    expected_forks = sum(
        len(node.get("successors") or []) > 1 for node in nodes_by_id.values()
    )
    if len(forks) != expected_forks:
        fail("allForksClassified", "", expected_forks, len(forks))
    validation = {
        "status": "validation_failed" if failures else "validated",
        "failures": failures,
    }
    counts = Counter(fork["structure"] for fork in forks)
    outcomes = Counter(fork["outcome"] for fork in forks)
    return {
        "schema": "missionQuestForkSemantics.v2",
        "forks": forks,
        "counts": {
            "forks": len(forks),
            "guardedForks": sum(bool(fork["guardedArmCount"]) for fork in forks),
            "structures": dict(sorted(counts.items())),
            "outcomes": dict(sorted(outcomes.items())),
        },
        "validation": validation,
        "evidenceBoundary": (
            "This graph describes original MissionRuntime structure and exact "
            "arm-local conditions. Server-only activation and exclusivity remain "
            "unknown unless an explicit typed selector is present."
        ),
    }


def build_mission(
    mission: dict[str, Any],
    source_path: Path,
    native_runtime_bindings: list[dict[str, Any]] | None = None,
    activity_quest_level_hosts: dict[str, list[dict[str, Any]]] | None = None,
    mission_graph_entry: dict[str, Any] | None = None,
    env_talk_contexts: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    mission_id = str(mission.get("missionId") or source_path.stem)
    quest_map = mission.get("questDic") or {}
    main_path = [str(value) for value in mission.get("mainPathQuests") or []]
    main_index = {quest_id: index for index, quest_id in enumerate(main_path)}
    actions = action_rows(mission)
    successors: dict[str, list[str]] = defaultdict(list)
    for raw in quest_map.values():
        if not isinstance(raw, dict):
            continue
        quest_id = str(raw.get("questId") or "")
        for parent in raw.get("prevQuestIdList") or []:
            if isinstance(parent, str) and quest_id:
                successors[parent].append(quest_id)

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    condition_counts: Counter[str] = Counter()
    exact_finish_count = 0
    server_placeholder_count = 0
    server_placeholder_quest_count = 0
    active_join_count = 0
    failure_count = 0
    external_dependency_count = 0
    submit_item_count = 0
    submit_item_quest_count = 0
    submit_item_dialog_co_gate_count = 0
    submit_item_level_script_co_gate_count = 0
    level_script_task_dependency_count = 0
    annotations = (CASE_STUDIES.get(mission_id) or {}).get("nodes") or {}

    ordered_quests = sorted(
        (row for row in quest_map.values() if isinstance(row, dict)),
        key=lambda row: (
            main_index.get(str(row.get("questId") or ""), 10**6),
            int(row.get("flowIndex") or 0),
            natural_quest_key(str(row.get("questId") or "")),
        ),
    )
    for raw in ordered_quests:
        quest_id = str(raw.get("questId") or "")
        objectives = [
            objective_row(objective, index + 1)
            for index, objective in enumerate(raw.get("objectiveList") or [])
            if isinstance(objective, dict)
        ]
        condition_types = sorted({item for objective in objectives for item in objective["conditionTypes"]})
        condition_counts.update(condition_types)
        dialog_finishes = [item for objective in objectives for item in objective["dialogFinishes"]]
        submission_checks = [
            item
            for objective in objectives
            for item in objective["submissionChecks"]
        ]
        for objective in objectives:
            objective["levelScriptTaskDependencies"] = [
                validate_level_script_task_dependency(
                    dependency,
                    mission_id=mission_id,
                    quest_id=quest_id,
                    mission_source=source_path,
                )
                for dependency in objective.get("levelScriptTaskDependencies") or []
            ]
        level_script_task_dependencies_for_quest = [
            dependency
            for objective in objectives
            for dependency in objective.get("levelScriptTaskDependencies") or []
        ]
        level_script_task_dependency_count += len(
            level_script_task_dependencies_for_quest
        )
        submission_dialog_co_gates = [
            item
            for objective in objectives
            for item in objective["submissionDialogCoGates"]
        ]
        submission_level_script_co_gates = [
            item
            for objective in objectives
            for item in objective["submissionLevelScriptCoGates"]
        ]
        submit_item_count += len(submission_checks)
        if submission_checks:
            submit_item_quest_count += 1
        submit_item_dialog_co_gate_count += len(submission_dialog_co_gates)
        submit_item_level_script_co_gate_count += len(
            submission_level_script_co_gates
        )
        exact_finish_count += sum(1 for item in dialog_finishes if isinstance(item.get("finishId"), int) and item["finishId"] >= 0)
        placeholder_condition_ids = [
            condition_id
            for objective in objectives
            for condition_id in objective["serverPlaceholderConditionIds"]
        ]
        server_placeholder_count += len(placeholder_condition_ids)
        if placeholder_condition_ids:
            server_placeholder_quest_count += 1
        quest_state_refs = [item for objective in objectives for item in objective["questStateRefs"]]
        if len({item["questId"] for item in quest_state_refs}) >= 2:
            active_join_count += 1
        failed_condition = condition_tree(raw.get("failedCondition"))
        if failed_condition:
            failure_count += 1
        prev = [str(value) for value in raw.get("prevQuestIdList") or [] if isinstance(value, str)]
        authority = classify_authority(condition_types)
        node = {
            "id": quest_id,
            "flowIndex": raw.get("flowIndex", 0),
            "showMode": raw.get("showMode"),
            "questType": raw.get("questType"),
            "mainPath": quest_id in main_index,
            "mainPathOrder": main_index.get(quest_id),
            "prev": prev,
            "successors": sorted(successors.get(quest_id, []), key=natural_quest_key),
            "objectives": objectives,
            "submissionChecks": submission_checks,
            "submissionDialogCoGates": submission_dialog_co_gates,
            "submissionLevelScriptCoGates": submission_level_script_co_gates,
            "levelScriptTaskDependencies": level_script_task_dependencies_for_quest,
            "serverPlaceholderKeys": [
                {"questId": quest_id, "conditionId": condition_id}
                for condition_id in placeholder_condition_ids
            ],
            "conditionTypes": condition_types,
            "authority": authority,
            "clientActions": actions.get(quest_id, []),
            "activityStageHosts": list(
                (activity_quest_level_hosts or {}).get(quest_id, [])
            ),
            "failedCondition": failed_condition,
            "network": {
                "outbound": "dialog_finish" if dialog_finishes else (
                    "server_owned" if authority == "server" else (
                        "objective_progress" if objectives else "unresolved"
                    )
                ),
                "inbound": ["quest_start", "quest_succeed"] + (["quest_fail"] if failed_condition else []),
            },
        }
        if quest_id in annotations:
            node["annotation"] = annotations[quest_id]
        nodes.append(node)
        for parent in prev:
            edges.append({
                "source": parent,
                "target": quest_id,
                "type": "predecessor",
                "confidence": "asset_direct",
                "serverDecision": True,
            })
        for objective_index, objective in enumerate(objectives, 1):
            for ref in objective["questStateRefs"]:
                external_source = ref["questId"] not in quest_map
                if external_source:
                    external_dependency_count += 1
                edge = {
                    "source": ref["questId"],
                    "target": quest_id,
                    "type": "condition_dependency",
                    "targetState": ref.get("state"),
                    "objectiveIndex": objective_index,
                    "confidence": "asset_direct",
                }
                if external_source:
                    edge["externalSource"] = True
                edges.append(edge)

    quest_topology = build_quest_fork_semantics(nodes, source_path)
    if quest_topology["validation"]["status"] != "validated":
        first = quest_topology["validation"]["failures"][0]
        raise RuntimeError(
            "validator=quest_fork_semantics "
            f"gate={first['gate']} mission={first['mission']} "
            f"quest={first.get('questId') or '-'} "
            f"expected={first['expected']!r} actual={first['actual']!r} "
            f"source={first['sourceFile']} "
            f"sourceHashes={first['sourceHashes']!r}"
        )
    roots = [node["id"] for node in nodes if not node["prev"]]
    fanouts = [node["id"] for node in nodes if len(node["successors"]) > 1]
    multi_prev = [node["id"] for node in nodes if len(node["prev"]) > 1]
    mission_name = mission.get("missionName") or {}
    mission_desc = mission.get("missionDescription") or {}
    mission_task_dependencies = [
        {**dependency, "questId": node["id"], "objectiveIndex": objective["index"]}
        for node in nodes
        for objective in node.get("objectives") or []
        for dependency in objective.get("levelScriptTaskDependencies") or []
    ]
    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "mission": {
            "id": mission_id,
            "nameKey": mission_name.get("key") if isinstance(mission_name, dict) else "",
            "descriptionKey": mission_desc.get("key") if isinstance(mission_desc, dict) else "",
            "levelId": mission.get("levelId") or "",
            "missionType": mission.get("missionType"),
            "rewardId": mission.get("rewardId") or "",
            "mainPath": main_path,
            "entryQuestIds": roots,
            "onMissionAcceptId": mission.get("onMissionAcceptId"),
            "onMissionCompletedId": mission.get("onMissionCompletedId"),
            "onMissionFailedId": mission.get("onMissionFailedId"),
            "nativeRuntimeBindings": list(native_runtime_bindings or []),
            "levelScriptTaskDependencies": mission_task_dependencies,
            "source": source_path.relative_to(ROOT).as_posix() if source_path.is_relative_to(ROOT) else source_path.as_posix(),
        },
        "nodes": nodes,
        "edges": sorted(edges, key=lambda row: (row["type"], natural_quest_key(row["source"]), natural_quest_key(row["target"]))),
        "caseStudy": CASE_STUDIES.get(mission_id),
        # Cross-mission relations recovered from authored mission/quest state
        # conditions. Only ``requiresCompleted`` carries precedence; the other
        # relations are co-active or mutually exclusive and must not be read as
        # ordering. See build_mission_dependency_graph.py.
        "missionGraph": mission_graph_entry or {"upstream": {}, "downstream": {}},
        "questTopology": quest_topology,
        # Ambient envTalk lines configured on an NPC proxy that a quest of this
        # mission tracks. Navigation/configuration context only -- never
        # playback ownership. See build_envtalk_attachment.py.
        "envTalkContext": sorted(
            env_talk_contexts or [],
            key=lambda row: (natural_quest_key(row.get("questId") or ""), row.get("storyKey") or ""),
        ),
    }
    properties = mission_property_rows(mission)
    if properties:
        payload["mission"]["properties"] = properties
    summary = {
        "id": mission_id,
        "nameKey": payload["mission"]["nameKey"],
        "levelId": payload["mission"]["levelId"],
        "questCount": len(nodes),
        "mainPathCount": len(main_path),
        "entryCount": len(roots),
        "fanoutCount": len(fanouts),
        "multiPrevJoinCount": len(multi_prev),
        "activeJoinCount": active_join_count,
        "exactFinishCount": exact_finish_count,
        "serverPlaceholderCount": server_placeholder_count,
        "serverPlaceholderQuestCount": server_placeholder_quest_count,
        "failureConditionCount": failure_count,
        "questForkSemanticCount": quest_topology["counts"]["forks"],
        "questForkGuardedCount": quest_topology["counts"]["guardedForks"],
        "questForkStructureCounts": quest_topology["counts"]["structures"],
        "questForkOutcomeCounts": quest_topology["counts"]["outcomes"],
        "externalDependencyCount": external_dependency_count,
        "submitItemConditionCount": submit_item_count,
        "submitItemQuestCount": submit_item_quest_count,
        "submitItemDialogCoGateCount": submit_item_dialog_co_gate_count,
        "submitItemLevelScriptCoGateCount": (
            submit_item_level_script_co_gate_count
        ),
        "levelScriptTaskDependencyCount": level_script_task_dependency_count,
        "nativeRuntimeBindingCount": len(native_runtime_bindings or []),
        "activityStageHostCount": sum(
            len(node.get("activityStageHosts") or []) for node in nodes
        ),
        "activityStageHostedQuestCount": sum(
            1 for node in nodes if node.get("activityStageHosts")
        ),
        "trackingInfoCount": sum(
            len(objective.get("tracking") or [])
            for node in nodes
            for objective in node.get("objectives") or []
        ),
        "trackingObjectiveCount": sum(
            1
            for node in nodes
            for objective in node.get("objectives") or []
            if objective.get("tracking")
        ),
        "missionPropertyCount": len(properties),
        "conditionTypes": sorted(condition_counts),
        "caseStudy": mission_id in CASE_STUDIES,
        "file": f"missions/{mission_id}.json",
    }
    return payload, summary


def env_talk_contexts_by_mission(report: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Regroup exact envTalk navigation/state context by mission.

    Level- and character-scoped rows still have no mission and are intentionally
    dropped. Atmospheric rows contribute only through their fail-closed,
    same-level full-NPC-set switcher join; they remain state context, never
    playback ownership.
    """
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in report.get("entries") or []:
        for context in entry.get("questContexts") or []:
            mission_id = str(context.get("missionId") or "")
            if not mission_id:
                continue
            grouped[mission_id].append(
                {
                    "storyKey": entry["storyKey"],
                    "envTalkId": entry["envTalkId"],
                    "questId": context.get("questId") or "",
                    "npcProxyId": context.get("npcProxyId") or "",
                    "levelId": context.get("levelId") or "",
                    "relation": entry["relation"],
                }
            )
        for context in entry.get("stateContexts") or []:
            quest_owners = context.get("questOwners") or {}
            for mission_id in context.get("missionIds") or []:
                mission_id = str(mission_id or "")
                if not mission_id:
                    continue
                grouped[mission_id].append(
                    {
                        "storyKey": entry["storyKey"],
                        "envTalkId": entry["envTalkId"],
                        "questIds": sorted(
                            quest_id
                            for quest_id, owner in quest_owners.items()
                            if owner == mission_id
                        ),
                        "conditionQuestIds": list(context.get("questIds") or []),
                        "conditionMissionIds": list(
                            context.get("conditionMissionIds") or []
                        ),
                        "bindMissionId": context.get("bindMissionId") or "",
                        "clusterId": context.get("clusterId") or "",
                        "switcherId": context.get("switcherId") or "",
                        "switcherGroupId": context.get("switcherGroupId") or "",
                        "npcIds": list(context.get("npcIds") or []),
                        "levelId": context.get("levelId") or "",
                        "relation": "atmosphericSwitcherStateContext",
                    }
                )
    return grouped


def env_talk_trigger_manifest(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Story-page trigger manifest for ambient ``env_*`` files.

    Kept separate from ``storyCoverage.storyTriggerManifest`` on purpose. The
    mission pipeline's denominator counts only mission-ownable Story kinds, and
    folding ~2k ambient files into it would silently move every coverage ratio.
    The Story page merges the two maps client-side so a lookup still works.

    Every route is ``context``. There is no ``playback`` causality here: nothing
    in the shipped data proves what triggers an ambient line.
    """
    manifest: dict[str, dict[str, Any]] = {}
    for entry in report.get("entries") or []:
        story_key = entry.get("storyKey")
        if not story_key:
            continue
        routes = [
            {
                "storyKey": story_key,
                "causality": "context",
                "relation": "env_talk_quest_tracked_proxy",
                "missionId": context.get("missionId") or "",
                "questId": context.get("questId") or "",
                "npcProxyId": context.get("npcProxyId") or "",
                "levelId": context.get("levelId") or "",
                "evidence": context.get("jsonPath") or "",
            }
            for context in entry.get("questContexts") or []
        ]
        for context in entry.get("stateContexts") or []:
            quest_owners = context.get("questOwners") or {}
            for mission_id in context.get("missionIds") or []:
                routes.append(
                    compact_dict(
                        {
                            "storyKey": story_key,
                            "causality": "context",
                            "relation": "env_talk_atmospheric_switcher_state_context",
                            "missionId": mission_id,
                            "questIds": sorted(
                                quest_id
                                for quest_id, owner in quest_owners.items()
                                if owner == mission_id
                            ),
                            "conditionQuestIds": list(context.get("questIds") or []),
                            "conditionMissionIds": list(
                                context.get("conditionMissionIds") or []
                            ),
                            "bindMissionId": context.get("bindMissionId") or "",
                            "clusterId": context.get("clusterId") or "",
                            "switcherId": context.get("switcherId") or "",
                            "switcherGroupId": context.get("switcherGroupId") or "",
                            "levelId": context.get("levelId") or "",
                            "evidence": (
                                f"{context.get('switcherGroupId') or ''} -> "
                                f"{context.get('clusterId') or ''}"
                            ),
                        }
                    )
                )
        manifest[story_key] = compact_dict({
            "attachmentStatus": "ambient_world_content",
            "envTalkRelation": entry.get("relation") or "",
            "levelIds": list(entry.get("levelIds") or []),
            "consumerCount": entry.get("consumerCount") or 0,
            "routes": routes,
        })
    return manifest


def build_all(
    mission_root: Path,
    output_root: Path,
    subgame_table: Path | None = None,
    activity_dungeon_fighting_stage_table: Path | None = None,
    activity_snapshot_stage_table: Path | None = None,
) -> dict[str, Any]:
    if not mission_root.is_dir():
        raise FileNotFoundError(f"MissionRuntimeAsset root not found: {mission_root}")
    mission_output = output_root / "missions"
    mission_output.mkdir(parents=True, exist_ok=True)
    summaries: list[dict[str, Any]] = []
    produced: set[str] = set()
    condition_counts: Counter[str] = Counter()
    placeholder_condition_counts: Counter[str] = Counter()
    subgame_bindings, subgame_registry = load_subgame_mission_bindings(subgame_table)
    activity_hosts, activity_host_registry = load_activity_quest_level_hosts((
        activity_dungeon_fighting_stage_table,
        activity_snapshot_stage_table,
    ))
    mission_graph = build_mission_dependency_graph_report(mission_root)
    mission_graph_index = mission_graph.get("missions") or {}
    env_talk = build_envtalk_attachment_report(
        table_root=DEFAULT_TABLE_ROOT,
        gameplay_root=DEFAULT_GAMEPLAY_CONFIG_ROOT,
        mission_root=mission_root,
    )
    env_talk_by_mission = env_talk_contexts_by_mission(env_talk)
    env_talk_state_context_files = {
        row.get("storyKey")
        for rows in env_talk_by_mission.values()
        for row in rows
        if row.get("relation") == "atmosphericSwitcherStateContext"
        and row.get("storyKey")
    }
    env_talk_state_context_missions = {
        mission_id
        for mission_id, rows in env_talk_by_mission.items()
        if any(
            row.get("relation") == "atmosphericSwitcherStateContext"
            for row in rows
        )
    }
    quest_count = 0
    for path in sorted(mission_root.glob("*.json")):
        if path.name.endswith("_meta.json"):
            continue
        mission = read_json(path)
        if not isinstance(mission, dict) or not isinstance(mission.get("questDic"), dict):
            continue
        mission_id = str(mission.get("missionId") or path.stem)
        payload, summary = build_mission(
            mission,
            path,
            subgame_bindings.get(mission_id, []),
            activity_hosts,
            mission_graph_index.get(mission_id),
            env_talk_by_mission.get(mission_id),
        )
        target = mission_output / f"{summary['id']}.json"
        write_json(target, payload)
        produced.add(target.name)
        summaries.append(summary)
        quest_count += summary["questCount"]
        condition_counts.update(summary["conditionTypes"])
        placeholder_condition_counts.update(
            str(key.get("conditionId") or "")
            for node in payload.get("nodes") or []
            if isinstance(node, dict)
            for key in node.get("serverPlaceholderKeys") or []
            if isinstance(key, dict) and key.get("conditionId")
        )
    for stale in mission_output.glob("*.json"):
        if stale.name not in produced:
            stale.unlink()
    summaries.sort(key=lambda row: natural_quest_key(row["id"]))
    default_mission_root = select_complete_mission_runtime_root(
        STREAMING_MISSION_ROOT,
        PERSISTENT_MISSION_ROOT,
    )
    if mission_root.resolve() == default_mission_root.resolve():
        source_summary = mission_runtime_source_summary(
            STREAMING_MISSION_ROOT,
            PERSISTENT_MISSION_ROOT,
        )
        source_summary["selectedRoot"] = repo_path(
            Path(source_summary["selectedRoot"])
        )
    else:
        source_summary = {
            "selectedRoot": repo_path(mission_root),
            "selection": "explicit_mission_root",
        }
    state_update_contract = load_state_update_application_contract()
    extra_thread_scheduler_contract = (
        load_action_extra_thread_scheduler_contract()
    )
    task_authority_contract = load_levelscript_task_authority_contract()
    task_lifecycle_contract = load_levelscript_task_lifecycle_contract()
    start_policy_contract = load_levelscript_start_policy_contract()
    manual_self_control_contract = (
        load_levelscript_manual_self_control_contract()
    )
    activation_control_contract = (
        load_levelscript_activation_control_contract()
    )
    runtime_contract = {
        **RUNTIME_CONTRACT,
        "nativeCrossSystemConsumerCensus": (
            load_native_cross_system_consumer_contract()
        ),
        "stateUpdateApplicationAudit": state_update_contract,
        "actionExtraThreadSchedulerAudit": extra_thread_scheduler_contract,
        "levelScriptTaskAuthorityAudit": task_authority_contract,
        "levelScriptTaskLifecycleAudit": task_lifecycle_contract,
        "levelScriptStartPolicyAudit": start_policy_contract,
        "levelScriptManualSelfControlAudit": manual_self_control_contract,
        "levelScriptActivationControlAudit": activation_control_contract,
    }
    quest_action_dispatch = (
        state_update_contract.get("questSucceedActionApplication") or {}
    )
    quest_state_application = (
        state_update_contract.get("questStateLifecycleApplication") or {}
    )
    quest_enable_application = (
        state_update_contract.get("questEnableLifecycleApplication") or {}
    )
    quest_action_dispatch_counts: Counter[str] = Counter()
    quest_state_application_counts: Counter[str] = Counter()
    quest_enable_application_counts: Counter[str] = Counter()
    for summary in summaries:
        mission_path = mission_output / f"{summary['id']}.json"
        payload = read_json(mission_path)
        if not isinstance(payload, dict):
            continue
        quest_action_dispatch_counts.update(
            annotate_quest_action_dispatch(payload, quest_action_dispatch)
        )
        quest_state_application_counts.update(
            annotate_quest_fork_state_application(
                payload,
                quest_state_application,
            )
        )
        quest_enable_application_counts.update(
            annotate_quest_fork_enable_application(
                payload,
                quest_enable_application,
            )
        )
        write_json(mission_path, payload)
    index = {
        "schemaVersion": SCHEMA_VERSION,
        "generated": int(time.time()),
        "source": mission_root.relative_to(ROOT).as_posix() if mission_root.is_relative_to(ROOT) else mission_root.as_posix(),
        "missionRuntimeSource": source_summary,
        "counts": {
            "missions": len(summaries),
            "quests": quest_count,
            "caseStudies": sum(1 for row in summaries if row["caseStudy"]),
            "missionGraphEdges": mission_graph["counts"]["edges"],
            "missionGraphPrecedenceEdges": mission_graph["counts"]["precedenceEdges"],
            "missionGraphMissions": mission_graph["counts"]["missionsInGraph"],
            "missionGraphInterleavings": mission_graph["counts"]["missionInterleavings"],
            "envTalkQuestContextFiles": env_talk["counts"]["relationCounts"][
                "questTrackedNpcProxy"
            ],
            "envTalkQuestContextMissions": env_talk["counts"]["questContextMissions"],
            "envTalkStateContextFiles": len(env_talk_state_context_files),
            "envTalkStateContextMissions": len(env_talk_state_context_missions),
            "serverPlaceholderConditions": sum(row["serverPlaceholderCount"] for row in summaries),
            "serverPlaceholderQuests": sum(row["serverPlaceholderQuestCount"] for row in summaries),
            "serverPlaceholderMissions": sum(1 for row in summaries if row["serverPlaceholderCount"]),
            "serverPlaceholderDistinctConditionIds": len(placeholder_condition_counts),
            "serverPlaceholderReusedConditionIds": sum(
                1 for count in placeholder_condition_counts.values() if count > 1
            ),
            "serverPlaceholderRowsWithReusedConditionId": sum(
                count for count in placeholder_condition_counts.values() if count > 1
            ),
            "serverPlaceholderMaxConditionIdReuse": max(
                placeholder_condition_counts.values(),
                default=0,
            ),
            "submitItemConditions": sum(
                row["submitItemConditionCount"] for row in summaries
            ),
            "submitItemQuests": sum(
                row["submitItemQuestCount"] for row in summaries
            ),
            "submitItemMissions": sum(
                1 for row in summaries if row["submitItemConditionCount"]
            ),
            "submitItemDialogCoGates": sum(
                row["submitItemDialogCoGateCount"] for row in summaries
            ),
            "submitItemLevelScriptCoGates": sum(
                row["submitItemLevelScriptCoGateCount"] for row in summaries
            ),
            "levelScriptTaskDependencies": sum(
                row["levelScriptTaskDependencyCount"] for row in summaries
            ),
            "missionsWithLevelScriptTaskDependencies": sum(
                1 for row in summaries if row["levelScriptTaskDependencyCount"]
            ),
            "nativeRuntimeBindings": subgame_registry["missionBindingCount"],
            "nativeRuntimeBoundMissions": subgame_registry["boundMissionCount"],
            "nativeRuntimeDistinctScriptIds": subgame_registry["distinctScriptCount"],
            "activityQuestLevelRows": activity_host_registry["rowCount"],
            "activityQuestLevelQuests": activity_host_registry["questCount"],
            "activityQuestLevelMissions": sum(
                1 for row in summaries if row["activityStageHostCount"]
            ),
            "trackingInfoRows": sum(
                row["trackingInfoCount"] for row in summaries
            ),
            "trackingObjectives": sum(
                row["trackingObjectiveCount"] for row in summaries
            ),
            "missionPropertyRows": sum(
                row["missionPropertyCount"] for row in summaries
            ),
            "missionsWithProperties": sum(
                1 for row in summaries if row["missionPropertyCount"]
            ),
            "questForkSemantics": sum(
                row["questForkSemanticCount"] for row in summaries
            ),
            "questForkGuarded": sum(
                row["questForkGuardedCount"] for row in summaries
            ),
            "questForkMainPathPlusAuxiliary": sum(
                row["questForkStructureCounts"].get(
                    "main_path_plus_auxiliary", 0
                )
                for row in summaries
            ),
            "questForkAllAuxiliary": sum(
                row["questForkStructureCounts"].get("all_auxiliary", 0)
                for row in summaries
            ),
            "questForkMultipleMainPath": sum(
                row["questForkStructureCounts"].get(
                    "multiple_main_path_successors", 0
                )
                + row["questForkStructureCounts"].get(
                    "multiple_main_path_plus_auxiliary", 0
                )
                for row in summaries
            ),
            "questForkReconverging": sum(
                row["questForkOutcomeCounts"].get("reconverging", 0)
                for row in summaries
            ),
            "questForkServerStateApplications": quest_state_application_counts[
                "forks"
            ],
            "questForkServerStateApplicationArms": quest_state_application_counts[
                "arms"
            ],
            "questForkServerEnableApplications": quest_enable_application_counts[
                "forks"
            ],
            "questForkServerEnableApplicationArms": quest_enable_application_counts[
                "arms"
            ],
            "stateUpdateApplicationCandidates": state_update_contract[
                "candidateCount"
            ],
            "stateUpdateApplicationCandidatesValidated": state_update_contract[
                "validatedCandidateCount"
            ],
            "stateUpdateClientSuccessorSelectors": state_update_contract[
                "clientSuccessorSelectors"
            ],
            "questStartPredecessorReads": state_update_contract[
                "questStartApplication"
            ].get("fieldReadCounts", {}).get("prevQuestIdList", 0),
            "questStartFlowIndexReads": state_update_contract[
                "questStartApplication"
            ].get("fieldReadCounts", {}).get("flowIndex", 0),
            "questStartTopologyTraversalCalls": len(
                state_update_contract["questStartApplication"].get(
                    "topologyTraversalCalls", []
                )
            ),
            "questTopologyActivePredecessorConsumers": state_update_contract[
                "questTopologyFieldConsumers"
            ].get("activePredecessorConsumerCount", 0),
            "questTopologyFlowIndexNonSortConsumers": state_update_contract[
                "questTopologyFieldConsumers"
            ].get("flowIndexNonSortConsumerCount", 0),
            "questTopologyLifecycleCalls": len(
                state_update_contract["questTopologyFieldConsumers"].get(
                    "topologyLifecycleCalls", []
                )
            ),
            "questTypeConsumers": (
                state_update_contract["questTopologyFieldConsumers"]
                .get("questSemanticFields", {})
                .get("questType", {})
                .get("consumerCount", 0)
            ),
            "questTypePostLifecycleConsumers": (
                state_update_contract["questTopologyFieldConsumers"]
                .get("questSemanticFields", {})
                .get("questType", {})
                .get("postLifecycleConsumerCount", 0)
            ),
            "questTypeBlockNotificationConsumers": (
                state_update_contract["questTopologyFieldConsumers"]
                .get("questSemanticFields", {})
                .get("questType", {})
                .get("blockNotificationConsumerCount", 0)
            ),
            "questOptionalObjectiveFlagValidated": (
                state_update_contract["questTopologyFieldConsumers"]
                .get("questSemanticFields", {})
                .get("optionalObjectiveFlag", {})
                .get("validation", {})
                .get("status")
                == "validated"
            ),
            "questShowModeConsumers": (
                state_update_contract["questTopologyFieldConsumers"]
                .get("questSemanticFields", {})
                .get("showMode", {})
                .get("consumerCount", 0)
            ),
            "questShowModeLifecycleConsumers": (
                state_update_contract["questTopologyFieldConsumers"]
                .get("questSemanticFields", {})
                .get("showMode", {})
                .get("lifecycleConsumerCount", 0)
            ),
            "actionExtraThreadWriterMethods": len(
                extra_thread_scheduler_contract.get(
                    "extraThreadExecuteMethods", []
                )
            ),
            "actionExtraThreadDirectCalls": len(
                extra_thread_scheduler_contract.get("directCalls", [])
            ),
            "questActionStartDefinitionRoots": quest_action_dispatch_counts[
                "roots:authored_definition_no_current_aot_dispatch"
            ],
            "questActionStartDefinitionRows": quest_action_dispatch_counts[
                "rows:authored_definition_no_current_aot_dispatch"
            ],
            "questActionBinaryDispatchedRoots": sum(
                count
                for key, count in quest_action_dispatch_counts.items()
                if key.startswith("roots:binary_proven_")
            ),
            "questActionBinaryDispatchedRows": sum(
                count
                for key, count in quest_action_dispatch_counts.items()
                if key.startswith("rows:binary_proven_")
            ),
        },
        "conditionTypeMissionCounts": dict(sorted(condition_counts.items())),
        "runtimeContract": runtime_contract,
        "nativeRuntimeRegistry": subgame_registry,
        "activityQuestLevelRegistry": activity_host_registry,
        "missionGraph": {
            "schema": mission_graph["schemaVersion"],
            "counts": mission_graph["counts"],
            "relationSemantics": mission_graph["relationSemantics"],
            "evidencePolicy": mission_graph["evidencePolicy"],
            "edges": mission_graph["edges"],
            "interleavings": mission_graph["missionInterleavings"],
            "reportJson": "reports/mission_graph/mission_dependency_graph.json",
            "reportMarkdown": "reports/mission_graph/mission_dependency_graph.md",
        },
        "envTalkAttachment": {
            "schema": env_talk["schemaVersion"],
            "counts": env_talk["counts"],
            "relationSemantics": env_talk["relationSemantics"],
            "evidencePolicy": env_talk["evidencePolicy"],
            "danglingConsumerReferences": env_talk["danglingConsumerReferences"],
            "envTalkTriggerManifest": env_talk_trigger_manifest(env_talk),
            "reportJson": "reports/mission_graph/envtalk_attachment.json",
            "reportMarkdown": "reports/mission_graph/envtalk_attachment.md",
        },
        "missions": summaries,
    }
    write_json(output_root / "index.json", index)
    return index


def publish_source_story_partial_order(
    index: dict[str, Any],
    output_root: Path,
    story_data_root: Path,
    language: str,
    report_root: Path = DEFAULT_ORDER_REPORT_ROOT,
) -> dict[str, Any] | None:
    """Publish strict Story ordering evidence into lazy mission payloads."""
    story_index = story_data_root / language / "index.json"
    if not story_index.is_file():
        return None
    state_contract = (
        (index.get("runtimeContract") or {}).get("stateUpdateApplicationAudit")
        or {}
    )
    quest_succeed_contract = dict(
        state_contract.get("questSucceedActionApplication") or {}
    )
    quest_succeed_contract["relatedOriginalFiles"] = (
        state_contract.get("relatedOriginalFiles") or []
    )
    extra_thread_contract = (
        (index.get("runtimeContract") or {}).get(
            "actionExtraThreadSchedulerAudit"
        )
        or {}
    )
    report = build_source_story_partial_order_report(
        language,
        story_data_root=story_data_root,
        quest_succeed_lifecycle_contract=quest_succeed_contract,
        extra_thread_scheduler_contract=extra_thread_contract,
    )
    quest_start = state_contract.get("questStartApplication") or {}
    topology_consumers = state_contract.get("questTopologyFieldConsumers") or {}
    quest_fork_authority = {
        "classification": "server_selected_start_topology_only",
        "questInfoType": quest_start.get("questInfoType"),
        "questInfoFieldOffsets": quest_start.get("questInfoFieldOffsets") or {},
        "fieldReadCounts": quest_start.get("fieldReadCounts") or {},
        "topologyTraversalCalls": quest_start.get("topologyTraversalCalls") or [],
        "startQuest": quest_start.get("startQuest") or {},
        "sourceMessages": quest_start.get("sourceMessages") or [],
        "topologyFieldConsumers": topology_consumers,
        "finding": quest_start.get("finding") or "",
        "boundary": quest_start.get("boundary") or "",
        "relatedOriginalFiles": state_contract.get("relatedOriginalFiles") or [],
        "validation": quest_start.get("validation") or {},
    }
    semantic_forks_by_id: dict[str, dict[str, Any]] = {}
    for mission_summary in index.get("missions") or []:
        if not isinstance(mission_summary, dict):
            continue
        semantic_path = output_root / str(mission_summary.get("file") or "")
        semantic_payload = (
            read_json(semantic_path) if semantic_path.is_file() else {}
        )
        for fork in (
            (semantic_payload.get("questTopology") or {}).get("forks") or []
        ):
            if not isinstance(fork, dict) or not fork.get("questId"):
                continue
            quest_id = str(fork["questId"])
            existing = semantic_forks_by_id.get(quest_id)
            if existing and existing != fork:
                raise RuntimeError(
                    "validator=quest_fork_semantics_publication "
                    "gate=globallyUniqueQuestForkId "
                    f"quest={quest_id} expected=unique actual=duplicate "
                    f"source={semantic_path}"
                )
            semantic_forks_by_id[quest_id] = fork
    for row in report.get("missions") or []:
        if not isinstance(row, dict):
            continue
        branches = row.get("branches") or {}
        if branches.get("questForks"):
            branches["questForkAuthority"] = quest_fork_authority
            missing_semantics = [
                str(fork.get("questId") or "")
                for fork in branches["questForks"]
                if isinstance(fork, dict)
                and str(fork.get("questId") or "") not in semantic_forks_by_id
            ]
            if missing_semantics:
                raise RuntimeError(
                    "validator=quest_fork_semantics_publication "
                    "gate=allStoryOrderForksHaveSemantics "
                    f"mission={row.get('mission') or '-'} "
                    "expected=[] "
                    f"actual={missing_semantics!r} "
                    f"source={output_root / 'missions'}"
                )
            branches["questForks"] = [
                semantic_forks_by_id[str(fork.get("questId") or "")]
                for fork in branches["questForks"]
                if isinstance(fork, dict)
            ]
    report_root.mkdir(parents=True, exist_ok=True)
    report_json = report_root / f"source_story_partial_order_{language}.json"
    report_markdown = report_root / f"source_story_partial_order_{language}.md"
    write_report_json(report_json, report)
    write_text_if_changed(
        report_markdown,
        render_source_story_partial_order_markdown(report),
    )

    order_cross_reference = build_source_story_order_cross_reference_report(
        report,
        read_json(DEFAULT_STORY_ORDER_OVERRIDE)
        if DEFAULT_STORY_ORDER_OVERRIDE.is_file()
        else {},
        read_json(DEFAULT_STORY_ORDER_OCR)
        if DEFAULT_STORY_ORDER_OCR.is_file()
        else {},
    )
    cross_reference_json = (
        report_root / f"source_story_order_cross_reference_{language}.json"
    )
    cross_reference_markdown = (
        report_root / f"source_story_order_cross_reference_{language}.md"
    )
    order_cross_reference["reportJson"] = repo_path(cross_reference_json)
    order_cross_reference["reportMarkdown"] = repo_path(cross_reference_markdown)
    write_report_json(cross_reference_json, order_cross_reference)
    write_text_if_changed(
        cross_reference_markdown,
        render_source_story_order_cross_reference_markdown(order_cross_reference),
    )

    publication = attach_source_story_partial_order(
        index,
        output_root,
        report,
        create_variant_aggregate_shells=False,
        require_complete_branch_publication=False,
        order_cross_reference=order_cross_reference,
    )

    order_summary = report.get("summary") or {}
    index["storyOrder"] = {
        "schema": report.get("_schema"),
        "language": language,
        "summary": order_summary,
        "nativeSerializedBranchInventory": copy.deepcopy(
            report.get("nativeSerializedBranchInventory") or {}
        ),
        "evidencePolicy": report.get("evidencePolicy") or {},
        "reportJson": repo_path(report_json),
        "reportMarkdown": repo_path(report_markdown),
        "publication": publication,
        "crossReference": _compact_story_order_cross_reference_index(
            order_cross_reference
        ),
    }
    write_json(output_root / "index.json", index)
    return report


def _update_story_order_summary(
    summary: dict[str, Any],
    order_row: dict[str, Any],
) -> None:
    order_summary = order_row.get("summary") or {}
    mappings = {
        "storyOrderSceneCount": "sceneCount",
        "storyOrderStrongEdgeCount": "strongEdgeCount",
        "storyOrderCycleCount": "cycleCount",
        "storyOrderNativeBranchCount": "nativeControlBranchCount",
        "storyOrderNativeMergeCount": "nativeControlMergeCount",
        "storyOrderNativeTransitionCount": "nativeControlPathTransitionEdgeCount",
        "storyOrderQuestSucceedLifecycleCount": "questSucceedLifecycleEdgeCount",
        "storyOrderNativeTransitionStepCount": "nativeControlPathTransitionStepCount",
        "storyOrderNativeNamedActionEndpointCount": "nativeControlPathNamedActionEndpointCount",
        "storyOrderNativeUnresolvedActionEndpointCount": "nativeControlPathUnresolvedActionEndpointCount",
        "storyOrderNativeBranchingTransitionCount": "nativeControlPathBranchingTransitionEdgeCount",
        "storyOrderNativeOrderedSequenceCount": "nativeOrderedSequenceCount",
        "storyOrderNativeOrderedSequenceContextCount": "nativeOrderedSequenceContextCount",
        "storyOrderNativeRelatedActionTopologyCount": "nativeRelatedActionTopologyCount",
        "storyOrderNativeSerializedBranchGroupCount": "nativeSerializedBranchGroupCount",
        "storyOrderNativeSerializedBranchArmCount": "nativeSerializedBranchArmCount",
        "storyOrderNativeSerializedPlaybackArmCount": "nativeSerializedPlaybackArmCount",
        "storyOrderNativeSerializedMultiPlaybackBranchCount": "nativeSerializedMultiPlaybackBranchCount",
        "storyOrderNativeSerializedBranchContextCount": "nativeSerializedBranchContextCount",
        "storyOrderNativeSerializedBranchContextStoryCount": "nativeSerializedBranchContextStoryCount",
        "storyOrderNativeSerializedBranchContextMultiPlaybackCount": "nativeSerializedBranchContextMultiPlaybackCount",
        "storyOrderNativeSerializedBranchContextRelatedFileCount": "nativeSerializedBranchContextRelatedFileCount",
        "storyOrderNativeSerializedNestedControlCount": "nativeSerializedNestedControlCount",
        "storyOrderNativeSerializedNestedControlFamilyCounts": "nativeSerializedNestedControlFamilyCounts",
        "storyOrderNativeSerializedNestedControlArmSchemaUnavailableCount": "nativeSerializedNestedControlArmSchemaUnavailableCount",
        "storyOrderNativeSerializedNestedPlaybackArmCount": "nativeSerializedNestedPlaybackArmCount",
        "storyOrderNativeSerializedNestedMultiPlaybackControlCount": "nativeSerializedNestedMultiPlaybackControlCount",
        "storyOrderNativeSerializedNestedPlaybackControlCount": "nativeSerializedNestedPlaybackControlCount",
        "storyOrderNativeSerializedNestedPlaybackPredicateGapCount": "nativeSerializedNestedPlaybackPredicateGapCount",
        "storyOrderNativeSerializedNestedControlReferenceCount": "nativeSerializedNestedControlReferenceCount",
        "storyOrderNativeSerializedNestedArmCount": "nativeSerializedNestedArmCount",
        "storyOrderNativeSerializedNestedExactActiveArmCount": "nativeSerializedNestedExactActiveArmCount",
        "storyOrderNativeSerializedNestedInactiveArmCount": "nativeSerializedNestedInactiveArmCount",
        "storyOrderNativeSerializedNestedRuntimeTerminalArmCount": "nativeSerializedNestedRuntimeTerminalArmCount",
        "storyOrderNativeSerializedNestedUnavailableArmCount": "nativeSerializedNestedUnavailableArmCount",
        "storyOrderNativeSerializedBranchPredicateConflictCount": "nativeSerializedBranchPredicateConflictCount",
        "storyOrderNativeNamedPredicateCount": "nativeNamedPredicateCount",
        "storyOrderNativeInlinePredicateCount": "nativeInlinePredicateCount",
        "storyOrderNativeSemanticPredicateCount": "nativeSemanticPredicateCount",
        "storyOrderNativeClassOnlyPredicateCount": "nativeClassOnlyPredicateCount",
        "storyOrderNativeUnresolvedPredicateCount": "nativeUnresolvedPredicateCount",
        "storyOrderQuestForkCount": "questForkCount",
        "storyOrderQuestMergeCount": "questMergeCount",
        "storyOrderDialogConditionalBranchCount": "dialogConditionalBranchCount",
        "storyOrderDialogConditionalBranchArmCount": "dialogConditionalBranchArmCount",
        "storyOrderDialogConditionalBranchValidationFailureCount": "dialogConditionalBranchValidationFailureCount",
        "storyOrderDialogTreeBranchNodeCount": "dialogTreeBranchNodeCount",
        "storyOrderDialogTreeBranchNodeArmCount": "dialogTreeBranchNodeArmCount",
        "storyOrderDialogTreeBranchNodeValidationFailureCount": "dialogTreeBranchNodeValidationFailureCount",
        "storyOrderDialogTreeIfNodeCount": "dialogTreeIfNodeCount",
        "storyOrderDialogTreeIfNodeArmCount": "dialogTreeIfNodeArmCount",
        "storyOrderDialogTreeIfNodeValidationFailureCount": "dialogTreeIfNodeValidationFailureCount",
        "storyOrderDialogLineOptionBinaryValidatedGroupCount": "dialogLineOptionBinaryValidatedGroupCount",
        "storyOrderDialogLineOptionBinaryValidationFailureCount": "dialogLineOptionBinaryValidationFailureCount",
        "storyOrderDialogLineOptionRelatedFileCount": "dialogLineOptionRelatedFileCount",
    }
    for target, source in mappings.items():
        summary[target] = int(order_summary.get(source) or 0)
    cross_reference = order_row.get("crossReference") or {}
    if isinstance(cross_reference, dict):
        summary["storyOrderCrossReferenceStrictEdgeCount"] = int(
            cross_reference.get("strictEdgeCount") or 0
        )
        summary["storyOrderCrossReferenceOverrideDisagreeCount"] = int(
            (cross_reference.get("override") or {}).get("disagrees") or 0
        )
        summary["storyOrderCrossReferenceOcrDisagreeCount"] = int(
            (cross_reference.get("ocr") or {}).get("disagrees") or 0
        )
        summary["storyOrderCrossReferenceConflictCount"] = int(
            cross_reference.get("conflictCount") or 0
        )


def _cross_reference_status_counts(
    counts: dict[str, Any] | None,
    reference: str,
) -> dict[str, int]:
    counts = counts or {}
    return {
        status: int(counts.get(f"{reference}_{status}") or 0)
        for status in ("agrees", "disagrees", "uncovered")
    }


def _compact_story_order_cross_reference(
    mission_row: dict[str, Any],
    cross_reference: dict[str, Any],
) -> dict[str, Any]:
    """Attach diagnostic override/OCR comparison without changing evidence."""
    counts = mission_row.get("counts") or {}
    disagreement_edges: list[dict[str, Any]] = []
    for edge in mission_row.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        override = edge.get("override") or {}
        ocr = edge.get("ocr") or {}
        if (
            override.get("status") != "disagrees"
            and ocr.get("status") != "disagrees"
            and not edge.get("crossReferenceConflict")
        ):
            continue
        disagreement_edges.append({
            "from": str(edge.get("from") or ""),
            "to": str(edge.get("to") or ""),
            "kind": str(edge.get("kind") or "sourceEdge"),
            "override": {
                "status": str(override.get("status") or "uncovered"),
                "fromIndex": override.get("fromIndex"),
                "toIndex": override.get("toIndex"),
                "missing": [
                    str(value)
                    for value in override.get("missing") or []
                    if value
                ],
            },
            "ocr": {
                "status": str(ocr.get("status") or "uncovered"),
                "fromIndex": ocr.get("fromIndex"),
                "toIndex": ocr.get("toIndex"),
                "missing": [
                    str(value)
                    for value in ocr.get("missing") or []
                    if value
                ],
            },
            "crossReferenceConflict": bool(
                edge.get("crossReferenceConflict")
            ),
            "orderEvidence": False,
        })
    disagreement_edges.sort(
        key=lambda edge: (
            str(edge.get("from") or ""),
            str(edge.get("to") or ""),
            str(edge.get("kind") or ""),
        )
    )
    return {
        "schema": str(cross_reference.get("_schema") or ""),
        "status": "cross_reference_only",
        "strictEdgeCount": int(mission_row.get("strictEdgeCount") or 0),
        "override": _cross_reference_status_counts(counts, "override"),
        "ocr": _cross_reference_status_counts(counts, "ocr"),
        "conflictCount": sum(
            bool(edge.get("crossReferenceConflict"))
            for edge in mission_row.get("edges") or []
            if isinstance(edge, dict)
        ),
        "disagreementEdges": disagreement_edges,
        "policy": (
            "Only strict source partial-order edges are evidence. Manual "
            "override and OCR lists are diagnostic cross-references; they "
            "never create, strengthen, weaken, or remove an edge."
        ),
        "reportJson": str(cross_reference.get("reportJson") or ""),
        "reportMarkdown": str(cross_reference.get("reportMarkdown") or ""),
        "orderEvidence": False,
    }


def _compact_story_order_cross_reference_index(
    cross_reference: dict[str, Any],
) -> dict[str, Any]:
    """Keep the global index compact while retaining the full report on disk."""
    return {
        "schema": str(cross_reference.get("_schema") or ""),
        "status": "cross_reference_only",
        "policy": cross_reference.get("policy") or {},
        "inputs": cross_reference.get("inputs") or {},
        "summary": cross_reference.get("summary") or {},
        "reportJson": str(cross_reference.get("reportJson") or ""),
        "reportMarkdown": str(cross_reference.get("reportMarkdown") or ""),
        "orderEvidence": False,
    }


def _resolve_report_source_path(source: str) -> Path:
    path = Path(source)
    return path if path.is_absolute() else ROOT / path


def _source_order_shell_related_files(
    order_row: dict[str, Any],
    *,
    hash_cache: dict[Path, str] | None = None,
    additional_files: list[Any] | None = None,
) -> list[dict[str, Any]]:
    """Collect and hash original files for a strict source-order shell.

    The collector walks the generated evidence shape instead of naming a
    LevelScript class, mission, or action family.  Every listed original file
    must still exist and match its report hash before a shell is published.
    """
    validator = "source_story_order_shell"
    related: dict[tuple[str, str], dict[str, Any]] = {}
    resolved_hash_cache = hash_cache if hash_cache is not None else {}

    def add_file(raw: Any, *, fallback_kind: str, fallback_relationship: str) -> None:
        if isinstance(raw, str):
            raw = {"sourceFile": raw}
        if not isinstance(raw, dict):
            return
        source = str(raw.get("sourceFile") or "")
        if not source:
            return
        path = _resolve_report_source_path(source)
        if not path.is_file():
            raise RuntimeError(
                f"validator={validator} gate=relatedOriginalFile "
                f"mission={order_row.get('mission') or '-'} expected=file "
                f"actual=missing source={source}"
            )
        actual_hash = resolved_hash_cache.get(path)
        if actual_hash is None:
            actual_hash = sha256_path(path)
            resolved_hash_cache[path] = actual_hash
        expected_hash = str(raw.get("sha256") or "")
        if expected_hash and expected_hash.casefold() != actual_hash.casefold():
            raise RuntimeError(
                f"validator={validator} gate=relatedOriginalFileHash "
                f"mission={order_row.get('mission') or '-'} "
                f"expected={expected_hash.upper()} actual={actual_hash.upper()} "
                f"source={source}"
            )
        normalized = dict(raw)
        normalized["sourceFile"] = repo_path(path)
        normalized["sha256"] = actual_hash
        normalized.setdefault("kind", fallback_kind)
        normalized.setdefault("relationship", fallback_relationship)
        key = (
            str(normalized["sourceFile"]),
            str(normalized.get("relationship") or ""),
        )
        related[key] = normalized

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            rows = value.get("relatedOriginalFiles")
            if isinstance(rows, list):
                for row in rows:
                    add_file(
                        row,
                        fallback_kind="original_authored_source",
                        fallback_relationship="strict_source_story_order_context",
                    )
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    strong_edges = [
        edge
        for edge in order_row.get("directEdges") or []
        if isinstance(edge, dict) and str(edge.get("tier") or "") == "strong"
    ]
    for edge in strong_edges:
        for source in edge.get("sourceFiles") or []:
            source_text = str(source or "")
            normalized_source = source_text.replace("\\", "/")
            if "LevelScriptData/" in normalized_source:
                kind = "original_level_script"
            elif "MissionRuntimeAsset/" in normalized_source:
                kind = "original_mission_runtime"
            elif normalized_source.casefold().endswith("gameassembly.dll"):
                kind = "original_game_binary"
            elif normalized_source.casefold().endswith("global-metadata.dat"):
                kind = "original_game_metadata"
            else:
                kind = "original_authored_source"
            add_file(
                source_text,
                fallback_kind=kind,
                fallback_relationship="strict_source_story_order_edge",
            )
    for raw in additional_files or []:
        add_file(
            raw,
            fallback_kind="original_mission_runtime",
            fallback_relationship="source_order_mission_runtime_context",
        )
    walk(order_row.get("branches") or {})
    return sorted(
        related.values(),
        key=lambda row: (
            str(row.get("sourceFile") or ""),
            str(row.get("relationship") or ""),
        ),
    )


def _story_branch_related_original_files(
    order_row: dict[str, Any],
    *,
    hash_cache: dict[Path, str] | None = None,
) -> list[dict[str, Any]]:
    """Hash exact original files cited by authored Story branch records.

    Dialog-line/Tree branch projections often cite the recovered TextAsset that
    contains the branch while having no LevelScript source-order edge.  Bounded
    DialogTree validation warnings also identify original files for malformed
    or non-promotable branch carriers.  Keep all of those files in a separate
    catalog: they are useful original-data context, but they are not chronology
    or mission-ownership evidence.  The walk is intentionally shape-driven and
    ignores generated WebUI paths.
    """
    validator = "story_branch_original_files"
    related: dict[str, dict[str, Any]] = {}
    resolved_hash_cache = hash_cache if hash_cache is not None else {}

    def classify(path: Path) -> str:
        normalized = path.as_posix().casefold()
        if "levelscriptdata/" in normalized:
            return "original_level_script"
        if "missionruntimeasset/" in normalized:
            return "original_mission_runtime"
        if normalized.endswith("gameassembly.dll"):
            return "original_game_binary"
        if normalized.endswith("global-metadata.dat"):
            return "original_game_metadata"
        if "/textasset/" in normalized or "json_by_type/textasset/" in normalized:
            return "original_dialog_tree_source"
        return "original_authored_source"

    def add_source(
        raw: Any,
        *,
        relationship: str = "authored_story_branch_source_file",
        expected_hash: str = "",
    ) -> None:
        source = str(raw or "")
        if not source:
            return
        normalized = source.replace("\\", "/").casefold()
        # Branch projections also carry generated conversation paths.  Only
        # original export/game paths are eligible for this hash-validated list.
        if normalized.startswith((
            "webui/",
            "reports/",
            "scratch/",
            "tmp/",
        )) or "/webui/data/" in normalized:
            return
        path = _resolve_report_source_path(source)
        if not path.is_file():
            raise RuntimeError(
                f"validator={validator} gate=sourceFile "
                f"mission={order_row.get('mission') or '-'} expected=file "
                f"actual=missing source={source}"
            )
        actual_hash = resolved_hash_cache.get(path)
        if actual_hash is None:
            actual_hash = sha256_path(path)
            resolved_hash_cache[path] = actual_hash
        if expected_hash and actual_hash.casefold() != expected_hash.casefold():
            raise RuntimeError(
                f"validator={validator} gate=sourceHash "
                f"mission={order_row.get('mission') or '-'} "
                f"expected={expected_hash!r} actual={actual_hash!r} "
                f"source={source}"
            )
        related.setdefault(repo_path(path), {
            "kind": classify(path),
            "sourceFile": repo_path(path),
            "sha256": actual_hash,
            "relationship": relationship,
        })

    def source_hashes(value: Any) -> dict[str, str]:
        if not isinstance(value, dict):
            return {}
        hashes: dict[str, str] = {}
        for raw_path, raw_hash in value.items():
            path_text = str(raw_path or "").replace("\\", "/")
            hash_text = str(raw_hash or "")
            if not path_text or not hash_text:
                continue
            hashes[path_text.casefold()] = hash_text
            hashes[Path(path_text).name.casefold()] = hash_text
        return hashes

    def source_values(value: Any) -> list[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, (list, tuple)):
            return [str(item) for item in value if str(item or "")]
        return []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            # Branch projections may already carry a normalized
            # ``relatedOriginalFiles`` row (for example the exact
            # GameAssembly file used to validate a DialogTree selector).
            # Preserve that relationship and hash instead of requiring every
            # producer to duplicate it under ``sourceFiles``.  This remains
            # shape-driven: no mission, Story key, or concrete branch class is
            # special-cased here.
            related_rows = value.get("relatedOriginalFiles")
            if isinstance(related_rows, list):
                for row in related_rows:
                    if isinstance(row, dict):
                        add_source(
                            row.get("sourceFile"),
                            relationship=(
                                str(row.get("relationship") or "")
                                or "authored_story_branch_related_original_file"
                            ),
                            expected_hash=str(row.get("sha256") or ""),
                        )
                    elif isinstance(row, str):
                        add_source(row)
            for source in source_values(value.get("sourceFiles")):
                add_source(source)
            # Authored branch projections use both plural ``sourceFiles`` and
            # singular ``sourceFile`` fields.  Walk the singular shape as
            # well; this keeps the collector corpus-driven instead of
            # requiring each branch producer (dialog options, tree nodes,
            # native controls, and validation records) to be named here.
            singular_source = value.get("sourceFile")
            expected_singular_hash = str(
                value.get("sourceSha256") or value.get("sha256") or ""
            )
            for source in source_values(singular_source):
                add_source(
                    source,
                    expected_hash=expected_singular_hash,
                )
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(order_row.get("branches") or {})
    for warning in order_row.get("warnings") or []:
        if not isinstance(warning, dict):
            continue
        # Validation diagnostics are evidence-bearing only when they identify
        # their validator and an original source path.  This keeps unrelated
        # UI/report warnings out of the branch-file catalog without naming a
        # mission, scene, or concrete branch object.
        if not str(warning.get("validator") or ""):
            continue
        expected_hashes = source_hashes(warning.get("sourceSha256"))
        warning_sources = [
            *source_values(warning.get("sourcePaths")),
            *source_values(warning.get("sourceFiles")),
            *source_values(warning.get("sourceFile")),
        ]
        for source in warning_sources:
            normalized = source.replace("\\", "/").casefold()
            expected = expected_hashes.get(normalized)
            if not expected:
                expected = expected_hashes.get(Path(normalized).name.casefold(), "")
            add_source(
                source,
                relationship="authored_story_branch_validation_source_file",
                expected_hash=expected,
            )
    return sorted(related.values(), key=lambda row: str(row["sourceFile"]))


def _source_order_shell_candidate(
    order_row: dict[str, Any],
    *,
    hash_cache: dict[Path, str] | None = None,
) -> bool:
    """Return whether a missing pipeline mission has strict source evidence."""
    if not str(order_row.get("mission") or ""):
        return False
    if not any(
        isinstance(edge, dict) and str(edge.get("tier") or "") == "strong"
        for edge in order_row.get("directEdges") or []
    ):
        return False
    mission_data = str(order_row.get("missionData") or "")
    if not mission_data or not _resolve_report_source_path(mission_data).is_file():
        return False
    return bool(_source_order_shell_related_files(order_row, hash_cache=hash_cache))


def _story_branch_shell_candidate(
    order_row: dict[str, Any],
    *,
    hash_cache: dict[Path, str] | None = None,
) -> bool:
    """Return whether a missing pipeline mission has branch-source context."""
    if not str(order_row.get("mission") or ""):
        return False
    mission_data = str(order_row.get("missionData") or "")
    if not mission_data or not _resolve_report_source_path(mission_data).is_file():
        return False
    return bool(_story_branch_related_original_files(order_row, hash_cache=hash_cache))


def _create_story_branch_shell(
    index: dict[str, Any],
    output_root: Path,
    order_row: dict[str, Any],
    *,
    hash_cache: dict[Path, str] | None = None,
) -> dict[str, Any]:
    """Publish a graph-neutral shell for branch context without a mission owner."""
    mission_id = str(order_row.get("mission") or "")
    mission_data = str(order_row.get("missionData") or "")
    mission_data_path = _resolve_report_source_path(mission_data)
    branch_related_files = _story_branch_related_original_files(
        order_row,
        hash_cache=hash_cache,
    )
    if not mission_id or not mission_data_path.is_file() or not branch_related_files:
        raise RuntimeError(
            "validator=story_branch_shell gate=eligibleSourceMission "
            f"mission={mission_id or '-'} expected=localized-sidecar-and-branch-files "
            f"actual=missionData={mission_data or '-'} "
            f"branchFiles={len(branch_related_files)}"
        )
    level_ids = sorted({
        str(level_id)
        for edge in order_row.get("directEdges") or []
        if isinstance(edge, dict)
        for level_id in edge.get("levelIds") or []
        if level_id
    }, key=natural_quest_key)
    boundary = (
        "These hash-validated original files are cited by authored Story branch "
        "or bounded branch-validation records. They provide branch-definition "
        "context only; they do not establish mission ownership, activation, or "
        "cross-file chronology."
    )
    story_order = copy.deepcopy(order_row)
    story_order["storyBranchShell"] = True
    story_order["storyBranchShellBoundary"] = (
        "This graph-neutral shell exposes authored Story branch and validation "
        "context for a Story namespace without a MissionRuntimeAsset owner. It "
        "does not establish mission ownership, activation, or Story-file order."
    )
    story_order["storyBranchRelatedOriginalFiles"] = copy.deepcopy(
        branch_related_files
    )
    story_order["storyBranchRelatedFilesBoundary"] = boundary
    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "mission": {
            "id": mission_id,
            "nameKey": "",
            "descriptionKey": "",
            "levelId": level_ids[0] if len(level_ids) == 1 else "",
            "missionType": None,
            "rewardId": "",
            "mainPath": [],
            "entryQuestIds": [],
            "nativeRuntimeBindings": [],
            "source": repo_path(mission_data_path),
            "storyBranchShell": True,
            "storyBranchShellBoundary": story_order["storyBranchShellBoundary"],
            "storyBranchRelatedOriginalFiles": copy.deepcopy(branch_related_files),
            "storyBranchRelatedFilesBoundary": boundary,
            "relatedOriginalFiles": [],
            "sourceBoundary": (
                "No MissionRuntimeAsset payload exists for this Story namespace. "
                "The page exposes authored branch/validation context only; it is "
                "not a mission or quest owner and does not establish Story order."
            ),
        },
        "nodes": [],
        "edges": [],
        "caseStudy": None,
        "missionGraph": {"upstream": {}, "downstream": {}},
        "envTalkContext": [],
        "storyOrder": story_order,
    }
    mission_output = output_root / "missions"
    mission_output.mkdir(parents=True, exist_ok=True)
    write_json(mission_output / f"{mission_id}.json", payload)
    summary = {
        "id": mission_id,
        "nameKey": "",
        "levelId": payload["mission"]["levelId"],
        "questCount": 0,
        "mainPathCount": 0,
        "entryCount": 0,
        "fanoutCount": 0,
        "multiPrevJoinCount": 0,
        "activeJoinCount": 0,
        "exactFinishCount": 0,
        "serverPlaceholderCount": 0,
        "serverPlaceholderQuestCount": 0,
        "failureConditionCount": 0,
        "externalDependencyCount": 0,
        "submitItemConditionCount": 0,
        "submitItemQuestCount": 0,
        "submitItemDialogCoGateCount": 0,
        "submitItemLevelScriptCoGateCount": 0,
        "nativeRuntimeBindingCount": 0,
        "activityStageHostCount": 0,
        "activityStageHostedQuestCount": 0,
        "trackingInfoCount": 0,
        "trackingObjectiveCount": 0,
        "missionPropertyCount": 0,
        "conditionTypes": [],
        "caseStudy": False,
        "file": f"missions/{mission_id}.json",
        "storyBranchShell": True,
        "storyBranchRelatedFileCount": len(branch_related_files),
    }
    _update_story_order_summary(summary, story_order)
    index.setdefault("missions", []).append(summary)
    return summary


def _create_source_order_shell(
    index: dict[str, Any],
    output_root: Path,
    order_row: dict[str, Any],
    *,
    hash_cache: dict[Path, str] | None = None,
) -> dict[str, Any]:
    """Publish a graph-neutral shell for strict original-data Story order."""
    mission_id = str(order_row.get("mission") or "")
    mission_data = str(order_row.get("missionData") or "")
    mission_data_path = _resolve_report_source_path(mission_data)
    related_files = _source_order_shell_related_files(
        order_row,
        hash_cache=hash_cache,
    )
    branch_related_files = _story_branch_related_original_files(
        order_row,
        hash_cache=hash_cache,
    )
    if not mission_id or not mission_data_path.is_file() or not related_files:
        raise RuntimeError(
            "validator=source_story_order_shell gate=eligibleSourceMission "
            f"mission={mission_id or '-'} expected=localized-sidecar-and-original-files "
            f"actual=missionData={mission_data or '-'} relatedFiles={len(related_files)}"
        )
    level_ids = sorted({
        str(level_id)
        for edge in order_row.get("directEdges") or []
        if isinstance(edge, dict)
        for level_id in edge.get("levelIds") or []
        if level_id
    }, key=natural_quest_key)
    story_order = copy.deepcopy(order_row)
    story_order["sourceOrderShell"] = True
    story_order["sourceOrderShellBoundary"] = (
        "This graph-neutral shell publishes strict original-data Story order and "
        "its hashed related files without claiming MissionRuntime, quest, playback "
        "ownership, activation, branch selection, or additional chronology."
    )
    story_order["sourceOrderRelatedOriginalFiles"] = copy.deepcopy(related_files)
    story_order["sourceOrderRelatedFilesBoundary"] = (
        "These original files are attached to the strict source-order report for "
        "auditability only. They do not establish mission ownership, activation, "
        "branch selection, or a total Story-file order."
    )
    story_order["storyBranchRelatedOriginalFiles"] = copy.deepcopy(
        branch_related_files
    )
    story_order["storyBranchRelatedFilesBoundary"] = (
        "These hash-validated original files are cited by authored Story branch "
        "or bounded branch-validation records. They provide branch-definition "
        "context only; they do not establish mission ownership, activation, or "
        "cross-file chronology."
    )
    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "mission": {
            "id": mission_id,
            "nameKey": "",
            "descriptionKey": "",
            "levelId": level_ids[0] if len(level_ids) == 1 else "",
            "missionType": None,
            "rewardId": "",
            "mainPath": [],
            "entryQuestIds": [],
            "nativeRuntimeBindings": [],
            "source": repo_path(mission_data_path),
            "sourceOrderShell": True,
            "sourceOrderRelatedOriginalFiles": copy.deepcopy(related_files),
            "sourceOrderRelatedFilesBoundary": (
                "These original files are attached to the strict source-order "
                "report for auditability only. They do not establish mission "
                "ownership, activation, branch selection, or a total Story-file "
                "order."
            ),
            "storyBranchRelatedOriginalFiles": copy.deepcopy(
                branch_related_files
            ),
            "storyBranchRelatedFilesBoundary": (
                "These hash-validated original files are cited by authored Story "
                "branch or bounded branch-validation records. They provide "
                "branch-definition context only; they do not establish mission "
                "ownership, activation, or cross-file chronology."
            ),
            "relatedOriginalFiles": related_files,
            "sourceBoundary": (
                "No MissionRuntimeAsset payload exists for this Story namespace. "
                "The page exposes exact strict source-order evidence and hashed "
                "original files only; it is not a mission or quest owner."
            ),
        },
        "nodes": [],
        "edges": [],
        "caseStudy": None,
        "missionGraph": {"upstream": {}, "downstream": {}},
        "envTalkContext": [],
        "storyOrder": story_order,
    }
    mission_output = output_root / "missions"
    mission_output.mkdir(parents=True, exist_ok=True)
    write_json(mission_output / f"{mission_id}.json", payload)
    summary = {
        "id": mission_id,
        "nameKey": "",
        "levelId": payload["mission"]["levelId"],
        "questCount": 0,
        "mainPathCount": 0,
        "entryCount": 0,
        "fanoutCount": 0,
        "multiPrevJoinCount": 0,
        "activeJoinCount": 0,
        "exactFinishCount": 0,
        "serverPlaceholderCount": 0,
        "serverPlaceholderQuestCount": 0,
        "failureConditionCount": 0,
        "externalDependencyCount": 0,
        "submitItemConditionCount": 0,
        "submitItemQuestCount": 0,
        "submitItemDialogCoGateCount": 0,
        "submitItemLevelScriptCoGateCount": 0,
        "nativeRuntimeBindingCount": 0,
        "activityStageHostCount": 0,
        "activityStageHostedQuestCount": 0,
        "trackingInfoCount": 0,
        "trackingObjectiveCount": 0,
        "missionPropertyCount": 0,
        "conditionTypes": [],
        "caseStudy": False,
        "file": f"missions/{mission_id}.json",
        "sourceOrderShell": True,
        "sourceOrderRelatedFileCount": len(related_files),
        "storyBranchRelatedFileCount": len(branch_related_files),
    }
    _update_story_order_summary(summary, story_order)
    index.setdefault("missions", []).append(summary)
    return summary


def _create_story_variant_aggregate_shell(
    index: dict[str, Any],
    output_root: Path,
    order_row: dict[str, Any],
) -> dict[str, Any]:
    """Create a non-owning shell from declared, validated Story variants.

    The rule is corpus-driven: a missing Story namespace is eligible only when
    its generated mission bundle declares variant mission bundles, every bundle
    identifies itself exactly, and every variant already has a Mission Pipeline
    payload backed by an original MissionRuntimeAsset.
    """
    mission_id = str(order_row.get("mission") or "")
    variant_sources = [
        str(value) for value in order_row.get("missionDataVariants") or [] if value
    ]
    validator = "source_story_order_publication"
    if not mission_id or not variant_sources:
        raise RuntimeError(
            f"validator={validator} gate=aggregateHasDeclaredVariants "
            f"mission={mission_id or '-'} expected=nonempty actual={variant_sources!r} "
            f"source={order_row.get('missionData') or '-'}"
        )
    summaries = {
        str(row.get("id") or ""): row
        for row in index.get("missions") or []
        if isinstance(row, dict) and row.get("id")
    }
    variant_ids: list[str] = []
    related_files: list[dict[str, Any]] = []
    level_ids: set[str] = set()
    for variant_source in variant_sources:
        generated_path = _resolve_report_source_path(variant_source)
        generated = read_json(generated_path) if generated_path.is_file() else None
        variant_id = str((generated or {}).get("mission") or "")
        if not variant_id:
            raise RuntimeError(
                f"validator={validator} gate=variantBundleIdentifiesMission "
                f"mission={mission_id} expected=mission-id actual={variant_id or '-'} "
                f"source={generated_path}"
            )
        variant_summary = summaries.get(variant_id)
        if not variant_summary:
            raise RuntimeError(
                f"validator={validator} gate=declaredVariantHasPipelineMission "
                f"mission={mission_id} expected={variant_id!r} actual=missing "
                f"source={generated_path}"
            )
        pipeline_path = output_root / str(variant_summary.get("file") or "")
        pipeline_payload = read_json(pipeline_path) if pipeline_path.is_file() else None
        original_source = str(((pipeline_payload or {}).get("mission") or {}).get("source") or "")
        original_path = _resolve_report_source_path(original_source) if original_source else Path()
        if not original_source or not original_path.is_file():
            raise RuntimeError(
                f"validator={validator} gate=variantHasOriginalMissionRuntime "
                f"mission={mission_id} variant={variant_id} expected=file actual={original_source or '-'} "
                f"source={pipeline_path}"
            )
        related_files.append({
            "kind": "original_mission_runtime",
            "sourceFile": repo_path(original_path),
            "sha256": sha256_path(original_path),
            "relationship": "declared_story_graph_variant_context",
            "variantMissionId": variant_id,
        })
        variant_ids.append(variant_id)
        if variant_summary.get("levelId"):
            level_ids.add(str(variant_summary["levelId"]))

    variant_ids = sorted(set(variant_ids), key=natural_quest_key)
    related_files.sort(key=lambda row: (natural_quest_key(row["variantMissionId"]), row["sourceFile"]))
    mission_output = output_root / "missions"
    mission_output.mkdir(parents=True, exist_ok=True)
    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "mission": {
            "id": mission_id,
            "nameKey": "",
            "descriptionKey": "",
            "levelId": next(iter(level_ids)) if len(level_ids) == 1 else "",
            "missionType": None,
            "rewardId": "",
            "mainPath": [],
            "entryQuestIds": [],
            "nativeRuntimeBindings": [],
            "source": str(order_row.get("missionData") or ""),
            "storyAggregateShell": True,
            "variantMissionIds": variant_ids,
            "relatedOriginalFiles": related_files,
            "sourceBoundary": (
                "This Story namespace aggregates exact serialized Story and LevelScript "
                "evidence across its declared mission variants. It is not itself a "
                "MissionRuntimeAsset and does not prove mission ownership, quest ownership, "
                "branch selection, or chronology beyond the attached typed evidence."
            ),
        },
        "nodes": [],
        "edges": [],
        "caseStudy": None,
        "missionGraph": {"upstream": {}, "downstream": {}},
        "envTalkContext": [],
        "storyOrder": copy.deepcopy(order_row),
    }
    write_json(mission_output / f"{mission_id}.json", payload)
    summary = {
        "id": mission_id,
        "nameKey": "",
        "levelId": payload["mission"]["levelId"],
        "questCount": 0,
        "mainPathCount": 0,
        "entryCount": 0,
        "fanoutCount": 0,
        "multiPrevJoinCount": 0,
        "activeJoinCount": 0,
        "exactFinishCount": 0,
        "serverPlaceholderCount": 0,
        "serverPlaceholderQuestCount": 0,
        "failureConditionCount": 0,
        "externalDependencyCount": 0,
        "submitItemConditionCount": 0,
        "submitItemQuestCount": 0,
        "submitItemDialogCoGateCount": 0,
        "submitItemLevelScriptCoGateCount": 0,
        "nativeRuntimeBindingCount": 0,
        "activityStageHostCount": 0,
        "activityStageHostedQuestCount": 0,
        "trackingInfoCount": 0,
        "trackingObjectiveCount": 0,
        "missionPropertyCount": 0,
        "conditionTypes": [],
        "caseStudy": False,
        "file": f"missions/{mission_id}.json",
        "storyAggregateShell": True,
        "storyAggregateVariantCount": len(variant_ids),
    }
    _update_story_order_summary(summary, order_row)
    index.setdefault("missions", []).append(summary)
    return summary


def attach_source_story_partial_order(
    index: dict[str, Any],
    output_root: Path,
    report: dict[str, Any],
    *,
    create_variant_aggregate_shells: bool,
    require_complete_branch_publication: bool,
    order_cross_reference: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Attach every recovered row that has a validated pipeline destination."""
    rows_by_mission = {
        str(row.get("mission") or ""): row
        for row in report.get("missions") or []
        if isinstance(row, dict) and row.get("mission")
    }
    existing_ids = {
        str(row.get("id") or "")
        for row in index.get("missions") or []
        if isinstance(row, dict)
    }
    aggregate_shells: list[str] = []
    source_order_shells: list[str] = []
    story_branch_shells: list[str] = []
    source_order_hash_cache: dict[Path, str] = {}
    if create_variant_aggregate_shells:
        for mission_id, order_row in sorted(rows_by_mission.items()):
            branch_count = len(
                ((order_row.get("branches") or {}).get("nativeControlBranches") or [])
            )
            if mission_id in existing_ids:
                continue
            if order_row.get("missionDataVariants") and branch_count:
                _create_story_variant_aggregate_shell(index, output_root, order_row)
                existing_ids.add(mission_id)
                aggregate_shells.append(mission_id)
                continue
            if _source_order_shell_candidate(
                order_row,
                hash_cache=source_order_hash_cache,
            ):
                _create_source_order_shell(
                    index,
                    output_root,
                    order_row,
                    hash_cache=source_order_hash_cache,
                )
                existing_ids.add(mission_id)
                source_order_shells.append(mission_id)
                continue
            if _story_branch_shell_candidate(
                order_row,
                hash_cache=source_order_hash_cache,
            ):
                _create_story_branch_shell(
                    index,
                    output_root,
                    order_row,
                    hash_cache=source_order_hash_cache,
                )
                existing_ids.add(mission_id)
                story_branch_shells.append(mission_id)

    published_missions: list[str] = []
    published_branches = 0
    source_order_related_file_missions: list[str] = []
    source_order_related_file_rows = 0
    source_order_related_distinct_files: set[str] = set()
    story_branch_related_file_missions: list[str] = []
    story_branch_related_file_rows = 0
    story_branch_related_distinct_files: set[str] = set()
    cross_reference_by_mission = {
        str(row.get("mission") or ""): row
        for row in (order_cross_reference or {}).get("missions") or []
        if isinstance(row, dict) and row.get("mission")
    }
    for summary in index.get("missions") or []:
        if not isinstance(summary, dict):
            continue
        mission_id = str(summary.get("id") or "")
        order_row = rows_by_mission.get(mission_id)
        mission_path = output_root / str(summary.get("file") or "")
        if not order_row or not mission_path.is_file():
            continue
        payload = read_json(mission_path)
        if not isinstance(payload, dict):
            continue
        inventory_rows = (
            (report.get("nativeSerializedBranchInventory") or {}).get("rows") or []
        )
        published_order = attach_serialized_branch_story_contexts(
            order_row,
            inventory_rows,
        )
        previous_order = payload.get("storyOrder") or {}
        if previous_order.get("sourceGapQueue"):
            published_order["sourceGapQueue"] = previous_order["sourceGapQueue"]
        if previous_order.get("sourceOrderShell"):
            published_order["sourceOrderShell"] = True
            published_order["sourceOrderShellBoundary"] = str(
                previous_order.get("sourceOrderShellBoundary") or ""
            )
        if previous_order.get("storyBranchShell"):
            published_order["storyBranchShell"] = True
            published_order["storyBranchShellBoundary"] = str(
                previous_order.get("storyBranchShellBoundary") or ""
            )
        mission_source = str(
            (payload.get("mission") or {}).get("source") or ""
        )
        additional_source_files = (
            [mission_source]
            if "MissionRuntimeAsset/" in mission_source.replace("\\", "/")
            else []
        )
        related_files = _source_order_shell_related_files(
            order_row,
            hash_cache=source_order_hash_cache,
            additional_files=additional_source_files,
        )
        branch_related_files = _story_branch_related_original_files(
            order_row,
            hash_cache=source_order_hash_cache,
        )
        if related_files:
            related_boundary = (
                "These original files are attached to the strict source-order "
                "report for auditability only. They do not establish mission "
                "ownership, activation, branch selection, or a total Story-file "
                "order."
            )
            published_order["sourceOrderRelatedOriginalFiles"] = copy.deepcopy(
                related_files
            )
            published_order["sourceOrderRelatedFilesBoundary"] = related_boundary
            mission_data = payload.setdefault("mission", {})
            mission_data["sourceOrderRelatedOriginalFiles"] = copy.deepcopy(
                related_files
            )
            mission_data["sourceOrderRelatedFilesBoundary"] = related_boundary
            summary["sourceOrderRelatedFileCount"] = len(related_files)
            source_order_related_file_missions.append(mission_id)
            source_order_related_file_rows += len(related_files)
            source_order_related_distinct_files.update(
                str(row.get("sourceFile") or "")
                for row in related_files
                if row.get("sourceFile")
            )
        if branch_related_files:
            branch_related_boundary = (
                "These hash-validated original files are cited by authored Story "
                "branch or bounded branch-validation records. They provide "
                "branch-definition context only; they do not establish mission "
                "ownership, activation, or cross-file chronology."
            )
            published_order["storyBranchRelatedOriginalFiles"] = copy.deepcopy(
                branch_related_files
            )
            published_order["storyBranchRelatedFilesBoundary"] = (
                branch_related_boundary
            )
            mission_data = payload.setdefault("mission", {})
            mission_data["storyBranchRelatedOriginalFiles"] = copy.deepcopy(
                branch_related_files
            )
            mission_data["storyBranchRelatedFilesBoundary"] = (
                branch_related_boundary
            )
            summary["storyBranchRelatedFileCount"] = len(branch_related_files)
            story_branch_related_file_missions.append(mission_id)
            story_branch_related_file_rows += len(branch_related_files)
            story_branch_related_distinct_files.update(
                str(row.get("sourceFile") or "")
                for row in branch_related_files
                if row.get("sourceFile")
            )
        cross_reference_row = cross_reference_by_mission.get(mission_id)
        if cross_reference_row is not None:
            cross_reference_payload = _compact_story_order_cross_reference(
                cross_reference_row,
                order_cross_reference or {},
            )
            published_order["crossReference"] = cross_reference_payload
            order_summary = published_order.setdefault("summary", {})
            order_summary["crossReferenceStrictEdgeCount"] = int(
                cross_reference_payload.get("strictEdgeCount") or 0
            )
            order_summary["crossReferenceOverrideDisagreeCount"] = int(
                (cross_reference_payload.get("override") or {}).get(
                    "disagrees"
                )
                or 0
            )
            order_summary["crossReferenceOcrDisagreeCount"] = int(
                (cross_reference_payload.get("ocr") or {}).get("disagrees")
                or 0
            )
            order_summary["crossReferenceConflictCount"] = int(
                cross_reference_payload.get("conflictCount") or 0
            )
        elif isinstance(previous_order.get("crossReference"), dict):
            # The canonical builder publishes the order once before coverage
            # attachment and once after it. Preserve the full per-mission
            # diagnostic comparison on the second pass; it is deliberately
            # not reconstructed from the compact global index summary.
            published_order["crossReference"] = copy.deepcopy(
                previous_order["crossReference"]
            )
        payload["storyOrder"] = published_order
        write_json(mission_path, payload)
        _update_story_order_summary(summary, published_order)
        published_missions.append(mission_id)
        published_branches += len(
            ((order_row.get("branches") or {}).get("nativeControlBranches") or [])
        )

    expected_branches = sum(
        len(((row.get("branches") or {}).get("nativeControlBranches") or []))
        for row in rows_by_mission.values()
    )
    missing_branch_missions = [
        mission_id
        for mission_id, row in sorted(rows_by_mission.items())
        if ((row.get("branches") or {}).get("nativeControlBranches") or [])
        and mission_id not in published_missions
    ]
    publication = {
        "validator": "source_story_order_publication",
        "status": "validated" if not missing_branch_missions else "incomplete",
        "expectedNativeBranchPlacements": expected_branches,
        "publishedNativeBranchPlacements": published_branches,
        "unpublishedNativeBranchPlacements": expected_branches - published_branches,
        "publishedMissionRows": len(published_missions),
        "variantAggregateShells": aggregate_shells,
        "sourceOrderShells": source_order_shells,
        "storyBranchShells": story_branch_shells,
        "sourceOrderRelatedFileMissions": source_order_related_file_missions,
        "sourceOrderRelatedFileRows": source_order_related_file_rows,
        "sourceOrderRelatedDistinctFiles": len(source_order_related_distinct_files),
        "storyBranchRelatedFileMissions": story_branch_related_file_missions,
        "storyBranchRelatedFileRows": story_branch_related_file_rows,
        "storyBranchRelatedDistinctFiles": len(story_branch_related_distinct_files),
        "missingBranchMissions": missing_branch_missions,
    }
    index.setdefault("counts", {})["missions"] = len(index.get("missions") or [])
    index["counts"]["sourceOrderMissionShells"] = len(source_order_shells)
    index["counts"]["storyBranchMissionShells"] = len(story_branch_shells)
    index["counts"]["sourceOrderRelatedFileMissions"] = len(
        source_order_related_file_missions
    )
    index["counts"]["sourceOrderRelatedFileRows"] = source_order_related_file_rows
    index["counts"]["sourceOrderRelatedDistinctFiles"] = len(
        source_order_related_distinct_files
    )
    index["counts"]["storyBranchRelatedFileMissions"] = len(
        story_branch_related_file_missions
    )
    index["counts"]["storyBranchRelatedFileRows"] = story_branch_related_file_rows
    index["counts"]["storyBranchRelatedDistinctFiles"] = len(
        story_branch_related_distinct_files
    )
    index.setdefault("storyOrder", {})["publication"] = publication
    index.setdefault("counts", {})["storyVariantAggregateShells"] = len(
        [row for row in index.get("missions") or [] if row.get("storyAggregateShell")]
    )
    index["counts"]["missions"] = len(index.get("missions") or [])
    index["missions"].sort(key=lambda row: natural_quest_key(str(row.get("id") or "")))
    if require_complete_branch_publication and missing_branch_missions:
        first = missing_branch_missions[0]
        row = rows_by_mission[first]
        actual = len(
            ((row.get("branches") or {}).get("nativeControlBranches") or [])
        )
        raise RuntimeError(
            "validator=source_story_order_publication "
            "gate=allRecoveredNativeBranchesPublished "
            f"mission={first} expected={actual} actual=0 "
            f"source={row.get('missionData') or '-'}"
        )
    write_json(output_root / "index.json", index)
    return publication


def publish_quest_objective_story_scope(
    index: dict[str, Any],
    output_root: Path,
    story_data_root: Path,
    language: str,
    coverage_report: Path,
    report_root: Path = DEFAULT_MISSION_GRAPH_REPORT_ROOT,
) -> dict[str, Any] | None:
    """Publish exact objective-to-LevelScript joins as non-owning quest context.

    The node-attachment audit admits a Story row when its hosting LevelScript is
    named by exactly one same-mission quest objective in the generated pipeline.
    When several objectives name the same script, an exact uniquely-decoded
    quest getter on that Story occurrence's serialized playback path may select
    one member of that owner set. These rows are deliberately dependency
    context, never playback ownership or ordering.
    """
    flow_root = story_data_root / language / "mission"
    mission_root = output_root / "missions"
    if (
        not flow_root.is_dir()
        or not mission_root.is_dir()
        or not coverage_report.is_file()
    ):
        return None

    report = build_node_attachment_report(
        flow_root,
        coverage_report,
        mission_root,
    )
    report_root.mkdir(parents=True, exist_ok=True)
    report_json = report_root / "node_attachment_coverage.json"
    report_markdown = report_root / "node_attachment_coverage.md"
    write_report_json(report_json, report)
    write_text_if_changed(report_markdown, render_node_attachment_markdown(report))

    placements_by_mission: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for placement in report.get("scriptScopedQuestPlacements") or []:
        if not isinstance(placement, dict):
            continue
        mission_id = str(placement.get("missionId") or "")
        quest_id = str(placement.get("questId") or "")
        story_key = str(placement.get("storyKey") or "")
        if not mission_id or not quest_id or not story_key:
            continue
        script_ids = sorted(
            {
                str(value)
                for value in placement.get("scriptIds") or []
                if str(value)
            }
        )
        discriminator = str(placement.get("scopeDiscriminator") or "")
        predicate_evidence = [
            row
            for row in placement.get("questPredicateEvidence") or []
            if isinstance(row, dict)
        ]
        if discriminator == "exact_playback_path_quest_predicate":
            evidence_text = (
                "quest objective names the hosting LevelScript and an exact "
                "uniquely-decoded quest getter gates this Story playback path"
            )
            confidence = "derived_exact_quest_scope_path_predicate"
        elif (
            discriminator
            == "exact_quest_condition_and_complete_native_playback_scope"
        ):
            evidence_text = (
                "quest condition names this LevelScript and the complete exact "
                "native Story occurrence carries that same quest condition"
            )
            confidence = "derived_exact_quest_condition_scope"
        else:
            evidence_text = (
                "quest objective names the unique LevelScript that hosts "
                "this Story occurrence"
            )
            confidence = "derived_exact_quest_scope"
        placements_by_mission[mission_id][quest_id].append(
            compact_dict(
                {
                    "key": story_key,
                    "kind": placement.get("kind") or "",
                    "relation": "quest_objective_levelscript_scope_context",
                    "sourceRelation": placement.get("sourceRelation") or "",
                    "direction": "context",
                    "phase": "objective_scope",
                    "confidence": confidence,
                    "scriptIds": script_ids,
                    "scopeDiscriminator": discriminator,
                    "questPredicateEvidence": predicate_evidence,
                    "questTriggerStatus": placement.get("questTriggerStatus") or "",
                    "ownershipStatus": "non_owning_context",
                    "playbackOwnership": False,
                    "orderEvidence": False,
                    "source": repo_path(report_json),
                    "evidence": evidence_text,
                }
            )
        )

    published_rows = 0
    published_keys: set[str] = set()
    published_quests = 0
    published_missions = 0
    for summary in index.get("missions") or []:
        if not isinstance(summary, dict):
            continue
        mission_id = str(summary.get("id") or "")
        mission_path = output_root / str(summary.get("file") or "")
        if not mission_path.is_file():
            continue
        payload = read_json(mission_path)
        if not isinstance(payload, dict):
            continue
        mission_rows = 0
        mission_quests = 0
        for node in payload.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            node.pop("storyScopeContexts", None)
            quest_id = str(node.get("id") or "")
            rows = placements_by_mission.get(mission_id, {}).get(quest_id, [])
            if not rows:
                continue
            deduplicated = {
                (
                    str(row.get("key") or ""),
                    str(row.get("sourceRelation") or ""),
                    str(row.get("scopeDiscriminator") or ""),
                    tuple(row.get("scriptIds") or []),
                ): row
                for row in rows
            }
            node["storyScopeContexts"] = sorted(
                deduplicated.values(),
                key=lambda row: (
                    str(row.get("key") or ""),
                    str(row.get("sourceRelation") or ""),
                    str(row.get("scopeDiscriminator") or ""),
                    tuple(row.get("scriptIds") or []),
                ),
            )
            mission_quests += 1
            mission_rows += len(node["storyScopeContexts"])
            published_keys.update(
                str(row.get("key") or "") for row in node["storyScopeContexts"]
            )
        summary["storyScopeContextCount"] = mission_rows
        summary["storyScopeContextQuestCount"] = mission_quests
        if mission_rows:
            published_missions += 1
            published_quests += mission_quests
            published_rows += mission_rows
        write_json(mission_path, payload)

    counts = report.get("counts") or {}
    index["nodeAttachmentCoverage"] = {
        "schema": report.get("schemaVersion"),
        "language": language,
        "counts": counts,
        "evidencePolicy": {
            "classification": "derived_exact_quest_scope",
            "ownershipPromotion": False,
            "orderPromotion": False,
            "boundary": (
                "A unique objective owner, or an exact playback-path quest predicate "
                "selecting one member of the objective-owner set, proves shared quest "
                "dependency scope only; it does not prove playback ownership or "
                "chronology."
            ),
        },
        "published": {
            "missions": published_missions,
            "quests": published_quests,
            "rows": published_rows,
            "uniqueStoryKeys": len(published_keys),
        },
        "reportJson": repo_path(report_json),
        "reportMarkdown": repo_path(report_markdown),
    }
    return report


def publish_quest_dialog_tree_definitions(
    index: dict[str, Any],
    output_root: Path,
    story_data_root: Path,
    language: str,
) -> dict[str, Any]:
    """Attach hash-verified DialogTree definitions to exact quest observers.

    MissionRuntime ``CheckTalkOptionFinish`` and
    ``CheckRepeatableTalkFinish`` prove that a quest observes a DialogTree
    root. The recovered TextAsset proves that root's internal graph; it does
    not prove which client action starts the dialog or add cross-file
    chronology.
    """
    sidecar_root = story_data_root / language.upper() / "mission"
    unique_story_keys: set[str] = set()
    placements = 0
    missions = 0
    quests = 0
    if not sidecar_root.is_dir():
        result = {
            "schema": "missionPipelineDialogTreeDefinitions.v1",
            "published": {
                "missions": 0,
                "quests": 0,
                "placements": 0,
                "uniqueStoryKeys": 0,
            },
        }
        index["dialogTreeDefinitions"] = result
        return result

    for summary in index.get("missions") or []:
        if not isinstance(summary, dict):
            continue
        mission_id = str(summary.get("id") or "")
        sidecar_path = sidecar_root / f"{mission_id}.json"
        mission_path = output_root / str(summary.get("file") or "")
        if not sidecar_path.is_file() or not mission_path.is_file():
            continue
        sidecar = read_json(sidecar_path)
        timeline_recovery = (
            sidecar.get("timelineRecovery")
            if isinstance(sidecar, dict)
            else None
        )
        raw_definitions = (
            timeline_recovery.get("sceneDialogTreeEvidence")
            if isinstance(timeline_recovery, dict)
            else None
        )
        if not isinstance(raw_definitions, dict) or not raw_definitions:
            continue

        definitions: dict[str, dict[str, Any]] = {}
        for scene_key, raw in raw_definitions.items():
            if not isinstance(raw, dict):
                raise ValueError(
                    f"DialogTree evidence is not an object: {sidecar_path} {scene_key}"
                )
            source_file = str(raw.get("sourceFile") or "")
            source_sha256 = str(raw.get("sourceSha256") or "").upper()
            if (
                str(raw.get("sceneKey") or "") != str(scene_key)
                or raw.get("assetType") != "Beyond.Gameplay.DialogTree"
                or raw.get("evidenceKind") != "exact_dialog_tree_definition"
                or not re.fullmatch(r"[0-9A-F]{64}", source_sha256)
                or not source_file
            ):
                raise ValueError(
                    f"DialogTree evidence failed shape validation: "
                    f"{sidecar_path} {scene_key}"
                )
            source_path = (ROOT / source_file).resolve()
            if not source_path.is_relative_to(ROOT) or not source_path.is_file():
                raise ValueError(
                    f"DialogTree evidence source is missing/outside repo: "
                    f"{sidecar_path} {scene_key} {source_file}"
                )
            actual_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest().upper()
            if actual_sha256 != source_sha256:
                raise ValueError(
                    f"DialogTree evidence source hash mismatch: {sidecar_path} "
                    f"{scene_key} expected={source_sha256} actual={actual_sha256}"
                )
            definitions[str(scene_key)] = raw

        payload = read_json(mission_path)
        if not isinstance(payload, dict):
            continue
        mission_placements = 0
        mission_quests: set[str] = set()
        mission_observed_dialogs: set[str] = set()
        for node in payload.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            observers_by_dialog: dict[str, list[dict[str, Any]]] = defaultdict(list)

            def collect_observers(
                condition: Any,
                relation: str,
                objective_index: int | None = None,
            ) -> None:
                if isinstance(condition, list):
                    for child in condition:
                        collect_observers(child, relation, objective_index)
                    return
                if not isinstance(condition, dict):
                    return
                condition_type = str(condition.get("type") or "")
                facts = condition.get("facts")
                if (
                    condition_type in {
                        "CheckTalkOptionFinish",
                        "CheckRepeatableTalkFinish",
                    }
                    and isinstance(facts, dict)
                    and facts.get("dialogId")
                ):
                    dialog_id = str(facts["dialogId"])
                    observer = {
                        "relation": relation,
                        "conditionType": condition_type,
                    }
                    if objective_index is not None:
                        observer["objectiveIndex"] = objective_index
                    if "finishId" in facts:
                        observer["finishId"] = facts["finishId"]
                    if observer not in observers_by_dialog[dialog_id]:
                        observers_by_dialog[dialog_id].append(observer)
                for value in condition.values():
                    if isinstance(value, (dict, list)):
                        collect_observers(value, relation, objective_index)

            for objective in node.get("objectives") or []:
                if isinstance(objective, dict):
                    collect_observers(
                        objective.get("condition"),
                        "objective_condition",
                        objective.get("index"),
                    )
            collect_observers(node.get("failedCondition"), "failed_condition")
            observed_dialogs = set(observers_by_dialog)
            mission_observed_dialogs.update(observed_dialogs)
            rows = [
                {
                    **definitions[dialog_id],
                    "missionObservers": observers_by_dialog[dialog_id],
                }
                for dialog_id in sorted(observed_dialogs, key=natural_quest_key)
                if dialog_id in definitions
            ]
            if not rows:
                continue
            node["dialogTreeDefinitions"] = rows
            mission_placements += len(rows)
            mission_quests.add(str(node.get("id") or ""))
            unique_story_keys.update(
                str(row.get("sceneKey") or "") for row in rows
            )
        unplaced = sorted(
            set(definitions) - mission_observed_dialogs,
            key=natural_quest_key,
        )
        if unplaced:
            raise ValueError(
                "DialogTree definitions have no supported MissionRuntime "
                f"observer: mission={mission_id} source={sidecar_path} "
                f"expected={unplaced[:8]} "
                f"actual={sorted(mission_observed_dialogs, key=natural_quest_key)[:16]}"
            )
        if not mission_placements:
            continue
        summary["dialogTreeDefinitionCount"] = mission_placements
        summary["dialogTreeDefinitionQuestCount"] = len(mission_quests)
        write_json(mission_path, payload)
        placements += mission_placements
        quests += len(mission_quests)
        missions += 1

    result = {
        "schema": "missionPipelineDialogTreeDefinitions.v1",
        "evidencePolicy": (
            "Exact MissionRuntime CheckTalkOptionFinish or "
            "CheckRepeatableTalkFinish observer plus a typed, hash-verified "
            "current-game DialogTree TextAsset. Definition/internal branch "
            "evidence only; no activation or cross-file order promotion."
        ),
        "sourceRoot": repo_path(sidecar_root),
        "published": {
            "missions": missions,
            "quests": quests,
            "placements": placements,
            "uniqueStoryKeys": len(unique_story_keys),
        },
    }
    index["dialogTreeDefinitions"] = result
    write_json(output_root / "index.json", index)
    return result


def publish_quest_fork_arm_evidence(
    index: dict[str, Any],
    output_root: Path,
    story_data_root: Path,
    language: str,
) -> dict[str, Any]:
    """Attach exact Story evidence to sibling-exclusive authored fork arms.

    The corridor membership comes only from MissionRuntime predecessor topology.
    Story rows come from the generated typed mission sidecar, whose action names
    are backed by the complete installed-binary ActionBase formatter audit. Any
    original file named by a row is resolved, bounded to the repository, and
    hashed before publication. OCR and manual order are deliberately absent.
    """
    validator = "quest_fork_arm_evidence"
    audit = ACTIONBASE_FORMATTER_NAME_AUDIT
    audit_source = str(audit.get("sourceFile") or "")
    if audit.get("status") != "validated" or not audit_source:
        raise RuntimeError(
            f"validator={validator} gate=binaryActionNameAudit "
            "expected={'status':'validated','sourceFile':'nonempty'} "
            f"actual={{'status':{audit.get('status')!r},'sourceFile':{audit_source!r}}} "
            "source=scripts/story_builder/level_bindings.py"
        )
    audit_path = (ROOT / audit_source).resolve()
    expected_audit_hash = str(audit.get("sourceSha256") or "").upper()
    if not audit_path.is_relative_to(ROOT) or not audit_path.is_file():
        raise RuntimeError(
            f"validator={validator} gate=binaryActionNameAuditSource "
            f"expected=fileWithinRepo actual={audit_path} source={audit_source}"
        )
    actual_audit_hash = sha256_path(audit_path).upper()
    if actual_audit_hash != expected_audit_hash:
        raise RuntimeError(
            f"validator={validator} gate=binaryActionNameAuditHash "
            f"expected={expected_audit_hash!r} actual={actual_audit_hash!r} "
            f"source={audit_source}"
        )
    audit_payload = read_json(audit_path)
    audit_metadata = (
        audit_payload.get("metadata")
        if isinstance(audit_payload, dict)
        and isinstance(audit_payload.get("metadata"), dict)
        else {}
    )

    sidecar_root = story_data_root / language.upper() / "mission"
    file_cache: dict[str, dict[str, Any]] = {}

    def related_original_file(
        source_file: str,
        relationship: str,
        expected_hash: str = "",
    ) -> dict[str, Any]:
        normalized = str(source_file or "").replace("\\", "/")
        cache_key = f"{normalized}\0{relationship}"
        cached = file_cache.get(cache_key)
        if cached is not None:
            return cached
        source_path = Path(normalized)
        if not source_path.is_absolute():
            source_path = ROOT / source_path
        source_path = source_path.resolve()
        if not source_path.is_relative_to(ROOT) or not source_path.is_file():
            raise RuntimeError(
                f"validator={validator} gate=relatedOriginalFile "
                f"expected=fileWithinRepo actual={source_path} "
                f"source={normalized}"
            )
        actual_hash = sha256_path(source_path)
        if expected_hash and actual_hash.upper() != expected_hash.upper():
            raise RuntimeError(
                f"validator={validator} gate=relatedOriginalFileHash "
                f"expected={expected_hash.upper()!r} "
                f"actual={actual_hash.upper()!r} source={normalized}"
            )
        row = {
            "kind": "original_authored_source",
            "sourceFile": repo_path(source_path),
            "relationship": relationship,
            "sha256": actual_hash,
        }
        file_cache[cache_key] = row
        return row

    missions = 0
    forks = 0
    arms = 0
    arms_with_story = 0
    story_placements = 0
    binary_named_action_placements = 0
    story_keys: set[str] = set()
    distinct_original_files: set[str] = set()
    for summary in index.get("missions") or []:
        if not isinstance(summary, dict):
            continue
        mission_id = str(summary.get("id") or "")
        mission_path = output_root / str(summary.get("file") or "")
        if not mission_path.is_file():
            continue
        payload = read_json(mission_path)
        topology = payload.get("questTopology") if isinstance(payload, dict) else None
        mission_forks = topology.get("forks") if isinstance(topology, dict) else None
        if not mission_forks:
            continue
        sidecar_path = sidecar_root / f"{mission_id}.json"
        if not sidecar_path.is_file():
            raise RuntimeError(
                f"validator={validator} gate=missionSidecar "
                f"mission={mission_id} expected=file actual=missing "
                f"source={sidecar_path}"
            )
        sidecar = read_json(sidecar_path)
        flow = sidecar.get("flow") if isinstance(sidecar, dict) else None
        quest_rows = flow.get("quests") if isinstance(flow, dict) else None
        if isinstance(quest_rows, dict):
            quest_rows = list(quest_rows.values())
        if not isinstance(quest_rows, list):
            raise RuntimeError(
                f"validator={validator} gate=missionSidecarQuests "
                f"mission={mission_id} expected=list actual={type(quest_rows).__name__} "
                f"source={sidecar_path}"
            )
        sidecar_quests = {
            str(row.get("id") or row.get("questId") or ""): row
            for row in quest_rows
            if isinstance(row, dict) and (row.get("id") or row.get("questId"))
        }
        nodes = {
            str(row.get("id") or ""): row
            for row in payload.get("nodes") or []
            if isinstance(row, dict) and row.get("id")
        }
        mission_story_placements = 0
        for fork in mission_forks:
            if not isinstance(fork, dict):
                continue
            forks += 1
            for arm in fork.get("arms") or []:
                if not isinstance(arm, dict):
                    continue
                arms += 1
                corridor = arm.get("siblingExclusiveQuestIds")
                if not isinstance(corridor, list):
                    raise RuntimeError(
                        f"validator={validator} gate=siblingExclusiveCorridor "
                        f"mission={mission_id} quest={fork.get('questId') or '-'} "
                        "expected=list actual=missing "
                        f"source={mission_path}"
                    )
                missing_quests = [
                    quest_id for quest_id in corridor
                    if quest_id not in sidecar_quests or quest_id not in nodes
                ]
                if missing_quests:
                    raise RuntimeError(
                        f"validator={validator} gate=corridorQuestsResolve "
                        f"mission={mission_id} quest={fork.get('questId') or '-'} "
                        f"expected=[] actual={missing_quests[:16]!r} "
                        f"source={sidecar_path}"
                    )
                evidence_by_signature: dict[tuple[str, ...], dict[str, Any]] = {}
                related_by_file: dict[str, dict[str, Any]] = {}
                for quest_id in corridor:
                    sidecar_quest = sidecar_quests[quest_id]
                    node = nodes[quest_id]
                    raw_rows = [
                        row for row in sidecar_quest.get("storyConnections") or []
                        if isinstance(row, dict) and row.get("key")
                    ]
                    raw_rows.extend(
                        row for row in node.get("storyScopeContexts") or []
                        if isinstance(row, dict) and row.get("key")
                    )
                    for raw in raw_rows:
                        raw_source_files = raw.get("sourceFiles")
                        if not isinstance(raw_source_files, list):
                            raw_source_files = []
                        source_files = sorted({
                            str(value).replace("\\", "/")
                            for value in [
                                raw.get("file"),
                                raw.get("sourceFile"),
                                *raw_source_files,
                            ]
                            if isinstance(value, str) and value
                        })
                        evidence = compact_dict({
                            "questId": quest_id,
                            "key": str(raw.get("key") or ""),
                            "kind": raw.get("kind") or "",
                            "relation": raw.get("relation") or "",
                            "direction": raw.get("direction") or "",
                            "phase": raw.get("phase") or "",
                            "confidence": raw.get("confidence") or "",
                            "actionType": raw.get("actionType") or raw.get("actionName") or "",
                            "conditionType": raw.get("conditionType") or "",
                            "finishId": raw.get("finishId"),
                            "evidenceTier": raw.get("evidenceTier") or "",
                            "ownership": raw.get("ownership") or raw.get("ownershipStatus") or "",
                            "questTriggerStatus": raw.get("questTriggerStatus") or "",
                            "nativeMappingId": raw.get("nativeMappingId") or "",
                            "source": raw.get("source") or "",
                            "sourceFiles": source_files,
                        })
                        signature = tuple(str(evidence.get(key) or "") for key in (
                            "questId", "key", "relation", "direction", "phase",
                            "confidence", "source",
                        ))
                        evidence_by_signature[signature] = evidence
                        for source_file in source_files:
                            related = related_original_file(
                                source_file,
                                "fork_arm_typed_story_relation",
                            )
                            related_by_file[related["sourceFile"]] = related
                    evidence_keys = {
                        str(row.get("key") or "")
                        for row in raw_rows
                    }
                    for definition in node.get("dialogTreeDefinitions") or []:
                        if not isinstance(definition, dict):
                            continue
                        scene_key = str(definition.get("sceneKey") or "")
                        if scene_key not in evidence_keys:
                            continue
                        source_file = str(definition.get("sourceFile") or "")
                        if not source_file:
                            continue
                        related = related_original_file(
                            source_file,
                            "fork_arm_observed_dialog_tree_definition",
                            str(definition.get("sourceSha256") or ""),
                        )
                        related_by_file[related["sourceFile"]] = related
                evidence_rows = sorted(
                    evidence_by_signature.values(),
                    key=lambda row: (
                        natural_quest_key(str(row.get("questId") or "")),
                        str(row.get("key") or ""),
                        str(row.get("relation") or ""),
                        str(row.get("source") or ""),
                    ),
                )
                arm["storyEvidence"] = evidence_rows
                arm["relatedOriginalFiles"] = sorted(
                    related_by_file.values(),
                    key=lambda row: (row["sourceFile"], row["relationship"]),
                )
                arm["storyEvidenceBoundary"] = (
                    "Rows are exact typed relations on quests in this sibling-relative "
                    "corridor. Context rows remain non-owning; even direct playback or "
                    "completion rows do not prove server arm selection or exclusivity."
                )
                story_placements += len(evidence_rows)
                binary_named_action_placements += sum(
                    bool(row.get("actionType")) for row in evidence_rows
                )
                mission_story_placements += len(evidence_rows)
                if evidence_rows:
                    arms_with_story += 1
                    story_keys.update(str(row.get("key") or "") for row in evidence_rows)
                distinct_original_files.update(related_by_file)
        order_branches = (
            (payload.get("storyOrder") or {}).get("branches")
            if isinstance(payload.get("storyOrder"), dict)
            else None
        )
        if isinstance(order_branches, dict) and order_branches.get("questForks"):
            forks_by_id = {
                str(row.get("questId") or ""): row
                for row in mission_forks
                if isinstance(row, dict) and row.get("questId")
            }
            order_branches["questForks"] = [
                forks_by_id[str(row.get("questId") or "")]
                for row in order_branches["questForks"]
                if isinstance(row, dict)
                and str(row.get("questId") or "") in forks_by_id
            ]
        summary["questForkArmStoryEvidenceCount"] = mission_story_placements
        write_json(mission_path, payload)
        missions += 1

    result = {
        "schema": "missionQuestForkArmEvidence.v1",
        "language": language.upper(),
        "binaryActionTypeAuthority": {
            **audit,
            "gameAssemblySha256": audit_metadata.get("gameAssemblySha256"),
            "metadataSha256": audit_metadata.get("metadataSha256"),
        },
        "counts": {
            "missions": missions,
            "forks": forks,
            "arms": arms,
            "armsWithStoryEvidence": arms_with_story,
            "storyEvidencePlacements": story_placements,
            "uniqueStoryKeys": len(story_keys),
            "binaryNamedActionPlacements": binary_named_action_placements,
            "distinctRelatedOriginalFiles": len(distinct_original_files),
        },
        "evidencePolicy": {
            "classification": "typed_sibling_relative_fork_arm_context",
            "ownershipPromotion": False,
            "orderPromotion": False,
            "usesOcrOrManualOrder": False,
            "boundary": (
                "MissionRuntime predecessor reachability defines each corridor. "
                "Typed quest Story relations and their original files are attached "
                "without claiming server selection, exclusivity, or a total order."
            ),
        },
    }
    index["questForkArmEvidence"] = result
    write_json(output_root / "index.json", index)
    return result


def _compact_runtime_observation(row: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "sessionId",
        "seq",
        "monotonicMs",
        "storyKey",
        "playbackType",
        "chainId",
        "triggerStatus",
        "ownershipStatus",
        "levelId",
        "scriptId",
        "headerLocalId",
        "actionLocalId",
        "actionType",
        "route",
    )
    return {key: row[key] for key in keys if key in row}


def publish_mission_runtime_trace(
    index: dict[str, Any],
    output_root: Path,
    trace_bundle_path: Path,
) -> dict[str, Any]:
    """Publish an observed-only runtime overlay without promoting ownership/order."""
    if not trace_bundle_path.is_file():
        raise FileNotFoundError(f"Mission runtime trace bundle not found: {trace_bundle_path}")
    bundle = read_json(trace_bundle_path)
    if not isinstance(bundle, dict) or bundle.get("_schema") != MISSION_RUNTIME_TRACE_SCHEMA:
        raise ValueError(
            f"Mission runtime trace must use {MISSION_RUNTIME_TRACE_SCHEMA}: {trace_bundle_path}"
        )
    observations = bundle.get("storyObservations")
    if not isinstance(observations, dict):
        raise ValueError("Mission runtime trace storyObservations must be an object")

    observations_by_mission: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for story_key, raw_rows in observations.items():
        if not isinstance(story_key, str) or not isinstance(raw_rows, list):
            raise ValueError("Mission runtime trace observations have an invalid shape")
        for row in raw_rows:
            if not isinstance(row, dict) or str(row.get("storyKey") or "") != story_key:
                raise ValueError(f"Mission runtime trace observation mismatch for {story_key}")
            mission_ids = {
                str(item.get("missionId") or "")
                for item in [*(row.get("activeMissions") or []), *(row.get("activeQuests") or [])]
                if isinstance(item, dict) and item.get("missionId")
            }
            for mission_id in sorted(mission_ids):
                observations_by_mission[mission_id].append(row)

    edges_by_mission: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in bundle.get("observedEdges") or []:
        if not isinstance(edge, dict):
            continue
        for mission_id in edge.get("sharedMissionIds") or []:
            if isinstance(mission_id, str) and mission_id:
                edges_by_mission[mission_id].append(edge)
        for quest in edge.get("sharedQuests") or []:
            if isinstance(quest, dict) and quest.get("missionId"):
                mission_id = str(quest["missionId"])
                if edge not in edges_by_mission[mission_id]:
                    edges_by_mission[mission_id].append(edge)

    published_missions = 0
    quest_placements = 0
    mission_context_only = 0
    unmatched_mission_ids = sorted(
        set(observations_by_mission)
        - {
            str(summary.get("id") or "")
            for summary in index.get("missions") or []
            if isinstance(summary, dict)
        }
    )
    for summary in index.get("missions") or []:
        if not isinstance(summary, dict):
            continue
        mission_id = str(summary.get("id") or "")
        mission_rows = observations_by_mission.get(mission_id) or []
        if not mission_rows:
            continue
        mission_path = output_root / str(summary.get("file") or "")
        if not mission_path.is_file():
            continue
        payload = read_json(mission_path)
        if not isinstance(payload, dict):
            continue
        nodes = {
            str(node.get("id") or ""): node
            for node in payload.get("nodes") or []
            if isinstance(node, dict) and node.get("id")
        }
        context_only_rows = []
        unique_rows: dict[tuple[str, int, str], dict[str, Any]] = {}
        for row in mission_rows:
            compact = _compact_runtime_observation(row)
            signature = (
                str(compact.get("sessionId") or ""),
                int(compact.get("seq") or 0),
                str(compact.get("storyKey") or ""),
            )
            unique_rows[signature] = compact
            quest_ids = sorted({
                str(item.get("questId") or "")
                for item in row.get("activeQuests") or []
                if isinstance(item, dict)
                and str(item.get("missionId") or "") == mission_id
                and item.get("questId")
            })
            attached = False
            for quest_id in quest_ids:
                node = nodes.get(quest_id)
                if node is None:
                    continue
                node.setdefault("runtimeStoryObservations", []).append(compact)
                quest_placements += 1
                attached = True
            if not attached:
                context_only_rows.append(compact)
                mission_context_only += 1
        for node in nodes.values():
            if node.get("runtimeStoryObservations"):
                node["runtimeStoryObservations"].sort(
                    key=lambda row: (
                        str(row.get("sessionId") or ""),
                        int(row.get("seq") or 0),
                        str(row.get("storyKey") or ""),
                    )
                )
        payload["runtimeTrace"] = {
            "schema": MISSION_RUNTIME_TRACE_SCHEMA,
            "evidenceClassification": "observed_runtime",
            "ownershipPromotion": False,
            "orderPromotion": False,
            "storyObservationCount": len(unique_rows),
            "questObservationPlacements": sum(
                len(node.get("runtimeStoryObservations") or []) for node in nodes.values()
            ),
            "missionContextOnly": context_only_rows,
            "observedEdges": edges_by_mission.get(mission_id, []),
        }
        summary["runtimeStoryObservationCount"] = len(unique_rows)
        summary["runtimeQuestObservationPlacementCount"] = payload["runtimeTrace"][
            "questObservationPlacements"
        ]
        write_json(mission_path, payload)
        published_missions += 1

    bundle_summary = bundle.get("summary") or {}
    index["runtimeTrace"] = {
        "schema": MISSION_RUNTIME_TRACE_SCHEMA,
        "source": repo_path(trace_bundle_path),
        "evidenceClassification": "observed_runtime",
        "ownershipPromotion": False,
        "orderPromotion": False,
        "evidencePolicy": bundle.get("evidencePolicy") or {},
        "summary": bundle_summary,
        "sessions": bundle.get("sessions") or [],
        "published": {
            "missions": published_missions,
            "questObservationPlacements": quest_placements,
            "missionContextOnlyObservations": mission_context_only,
            "unmatchedMissionIds": unmatched_mission_ids,
        },
        "observedForks": bundle.get("observedForks") or [],
        "observedMerges": bundle.get("observedMerges") or [],
    }
    write_json(output_root / "index.json", index)
    return bundle


def main() -> int:
    args = parse_args()
    output_root = args.output_root.resolve()
    index = build_all(
        args.mission_root.resolve(),
        output_root,
        args.subgame_table.resolve(),
        getattr(
            args,
            "activity_dungeon_fighting_stage_table",
            DEFAULT_ACTIVITY_DUNGEON_FIGHTING_STAGE_TABLE,
        ).resolve(),
        getattr(
            args,
            "activity_snapshot_stage_table",
            DEFAULT_ACTIVITY_SNAPSHOT_STAGE_TABLE,
        ).resolve(),
    )
    dialog_tree_definitions = publish_quest_dialog_tree_definitions(
        index,
        output_root,
        args.story_data_root.resolve(),
        args.story_language,
    )
    dialog_finish_branch_audit: dict[str, Any] = {}
    if output_root == DEFAULT_OUTPUT_ROOT.resolve():
        (
            dialog_finish_branch_audit,
            dialog_finish_pipeline_payloads,
        ) = build_dialog_finish_branch_audit_report(
            index,
            output_root,
        )
        write_report_json(
            DIALOG_FINISH_BRANCH_AUDIT_JSON,
            dialog_finish_branch_audit,
        )
        write_text_if_changed(
            DIALOG_FINISH_BRANCH_AUDIT_MARKDOWN,
            render_dialog_finish_branch_audit_markdown(
                dialog_finish_branch_audit
            ),
        )
        publish_dialog_finish_branch_audit(
            index,
            dialog_finish_branch_audit,
            dialog_finish_pipeline_payloads,
            output_root,
        )
        write_json(output_root / "index.json", index)
    order_report = publish_source_story_partial_order(
        index,
        output_root,
        args.story_data_root.resolve(),
        args.story_language,
    )
    # The complete-corpus callback audit is generated once for the canonical
    # pipeline. Reduced fixture outputs never overwrite or silently consume it.
    callserver_callback_audit: dict[str, Any] = {}
    timeline_embedded_runtime_audit: dict[str, Any] = {}
    if output_root == DEFAULT_OUTPUT_ROOT.resolve():
        callserver_callback_audit = build_callserver_callback_audit_report()
        write_report_json(
            CALLSERVER_CALLBACK_AUDIT_JSON,
            callserver_callback_audit,
        )
        write_text_if_changed(
            CALLSERVER_CALLBACK_AUDIT_MARKDOWN,
            render_callserver_callback_audit_markdown(
                callserver_callback_audit
            ),
        )
        timeline_embedded_runtime_audit = build_timeline_embedded_runtime_report()
        write_report_json(
            TIMELINE_EMBEDDED_RUNTIME_JSON,
            timeline_embedded_runtime_audit,
        )
        write_text_if_changed(
            TIMELINE_EMBEDDED_RUNTIME_MARKDOWN,
            render_timeline_embedded_runtime_markdown(
                timeline_embedded_runtime_audit
            ),
        )
    coverage = build_story_binding_coverage(
        index,
        output_root / "index.json",
        args.story_data_root.resolve(),
        args.story_language,
        args.report_root.resolve(),
        args.subgame_table.resolve(),
        args.activity_stage_table.resolve(),
        args.game_mechanic_condition_table.resolve(),
        args.dungeon_table.resolve(),
        getattr(args, "text_vo_id_table", DEFAULT_TEXT_VO_ID_TABLE).resolve(),
        getattr(
            args,
            "lua_consumer_audit",
            DEFAULT_LUA_CONSUMER_REFERENCE_AUDIT,
        ).resolve(),
        tuple(
            path.resolve()
            for path in (
                getattr(args, "cutscene_case_audit", None)
                or [DEFAULT_CUTSCENE_CASE_RESOLUTION_AUDIT]
            )
        ),
        callserver_callback_audit=callserver_callback_audit,
    )
    node_attachment = None
    fork_arm_evidence = None
    if coverage:
        source_story_gap_queue = getattr(
            args,
            "source_story_gap_queue",
            DEFAULT_SOURCE_STORY_GAP_QUEUE,
        ).resolve()
        if getattr(args, "refresh_source_story_gap_queue", False):
            refresh_source_story_gap_queue(
                args.story_language,
                source_story_gap_queue,
            )
        offline_recovery = publish_offline_story_recovery(
            coverage["storyTriggerManifest"],
            source_story_gap_queue,
        )
        offline_recovery["missionShells"] = (
            publish_offline_recovery_mission_shells(
                index,
                output_root,
                offline_recovery,
                source_story_gap_queue,
            ) if output_root == DEFAULT_OUTPUT_ROOT.resolve() else []
        )
        if order_report:
            order_cross_reference = None
            cross_reference_meta = (
                (index.get("storyOrder") or {}).get("crossReference") or {}
            )
            cross_reference_source = cross_reference_meta.get("reportJson")
            if cross_reference_source:
                cross_reference_path = _resolve_report_source_path(
                    str(cross_reference_source)
                )
                if cross_reference_path.is_file():
                    order_cross_reference = read_json(cross_reference_path)
            attach_source_story_partial_order(
                index,
                output_root,
                order_report,
                create_variant_aggregate_shells=True,
                require_complete_branch_publication=True,
                order_cross_reference=order_cross_reference,
            )
        report_stem = f"mission_pipeline_story_binding_coverage_{coverage['language']}"
        coverage_report = args.report_root.resolve() / f"{report_stem}.json"
        index["storyCoverage"] = {
            "language": coverage["language"],
            "policy": coverage["policy"],
            "counts": coverage["counts"],
            "nativePlaybackEventFamilies": coverage["nativePlaybackEventFamilies"],
            "storyTriggerManifest": coverage["storyTriggerManifest"],
            "luaStoryPlaybackEvidence":
                coverage.get("luaStoryPlaybackEvidence") or {},
            "offlineRecoveryEvidence": offline_recovery,
            "rootPlaybackAliases":
                coverage.get("rootPlaybackAliases") or [],
            "composedRootPlaybackAliases":
                coverage.get("composedRootPlaybackAliases") or [],
            "nonMissionContentKeys": coverage.get("nonMissionContentKeys") or [],
            "missionlessSubGamePlaybackNodes": coverage["missionlessSubGamePlaybackNodes"],
            "missionlessNativeRuntimeNodes": coverage["missionlessNativeRuntimeNodes"],
            "postPlaybackActionNameAudit": (
                coverage.get("postPlaybackActionNameAudit") or {}
            ),
            "callServerCallbackAudit": (
                coverage.get("callServerCallbackAudit") or {}
            ),
            "postPlaybackLevelSequenceAssetAudit": (
                coverage.get("postPlaybackLevelSequenceAssetAudit") or {}
            ),
            "postPlaybackVariableBridgeAudit": (
                coverage.get("postPlaybackVariableBridgeAudit") or {}
            ),
            "dynamicSceneIdentityCrossReferences":
                coverage.get("dynamicSceneIdentityCrossReferences"),
            "timelineEmbeddedStoryRuntimeAudit": (
                timeline_embedded_runtime_audit or {}
            ),
            "reportJson": repo_path(coverage_report),
            "reportMarkdown": repo_path(args.report_root.resolve() / f"{report_stem}.md"),
        }
        activation_frontier = build_native_receiver_activation_frontier_report(
            index,
            read_json(NATIVE_RECEIVER_MANUAL_CONTROL_AUDIT) or {},
            mission_root=output_root / "missions",
            subgame_table_path=args.subgame_table.resolve(),
            game_mechanic_condition_table_path=(
                args.game_mechanic_condition_table.resolve()
            ),
            dungeon_table_path=args.dungeon_table.resolve(),
        )
        identity_validation = (
            activation_frontier.get("structuredIdentityCarrierCensus") or {}
        ).get("validation") or {}
        if identity_validation.get("status") != "validated":
            failure = (identity_validation.get("failures") or [{}])[0]
            raise RuntimeError(
                "structured identity census failed: "
                f"validator={failure.get('validator')}; "
                f"gate={failure.get('gate')}; "
                f"source={failure.get('sourceFile')}; "
                f"expected={failure.get('expected')!r}; "
                f"actual={failure.get('actual')!r}"
            )
        # Fixture/test builds use temporary output roots and must not overwrite
        # the canonical recovery report with their reduced corpus.
        if output_root == DEFAULT_OUTPUT_ROOT.resolve():
            write_report_json(
                NATIVE_RECEIVER_FRONTIER_JSON,
                activation_frontier,
            )
            write_text_if_changed(
                NATIVE_RECEIVER_FRONTIER_MARKDOWN,
                render_native_receiver_activation_frontier_markdown(
                    activation_frontier
                ),
            )
        publish_native_receiver_activation_frontier(
            index,
            activation_frontier,
            mission_root=output_root / "missions",
        )
        node_attachment = publish_quest_objective_story_scope(
            index,
            output_root,
            args.story_data_root.resolve(),
            coverage["language"],
            coverage_report,
        )
        fork_arm_evidence = publish_quest_fork_arm_evidence(
            index,
            output_root,
            args.story_data_root.resolve(),
            coverage["language"],
        )
        write_json(output_root / "index.json", index)
    runtime_trace = None
    runtime_trace_path = getattr(args, "runtime_trace_bundle", None)
    if runtime_trace_path:
        runtime_trace = publish_mission_runtime_trace(
            index,
            output_root,
            runtime_trace_path.resolve(),
        )
    print(
        f"Mission pipeline: {index['counts']['missions']} missions, "
        f"{index['counts']['quests']} quests -> {args.output_root}"
    )
    print(
        "Quest semantic fields: "
        f"{index['counts'].get('questTypeConsumers', 0)} questType consumers "
        f"({index['counts'].get('questTypePostLifecycleConsumers', 0)} "
        "post-lifecycle / "
        f"{index['counts'].get('questTypeBlockNotificationConsumers', 0)} "
        "Block notifications), "
        f"{index['counts'].get('questShowModeConsumers', 0)} showMode consumers "
        f"({index['counts'].get('questShowModeLifecycleConsumers', 0)} lifecycle), "
        "Optional objective flag="
        f"{index['counts'].get('questOptionalObjectiveFlagValidated', False)}"
    )
    if coverage:
        counts = coverage["counts"]
        print(
            f"Story binding coverage: {counts['connectedUniqueStoryFiles']} connected, "
            f"{counts['unlinkedUniqueStoryFiles']} unlinked unique files"
        )
        if node_attachment:
            published = index["nodeAttachmentCoverage"]["published"]
            print(
                "Quest objective Story scope: "
                f"{published['rows']} context rows across "
                f"{published['quests']} quest nodes"
            )
        if fork_arm_evidence:
            published = fork_arm_evidence["counts"]
            print(
                "Quest fork arm evidence: "
                f"{published['storyEvidencePlacements']} Story placements across "
                f"{published['armsWithStoryEvidence']}/{published['arms']} arms; "
                f"{published['distinctRelatedOriginalFiles']} original files"
            )
    else:
        print(f"Story binding coverage skipped: no {args.story_language.upper()} Story bundle")
    published_dialog_trees = dialog_tree_definitions.get("published") or {}
    print(
        "Quest DialogTree definitions: "
        f"{published_dialog_trees.get('placements', 0)} placements across "
        f"{published_dialog_trees.get('quests', 0)} quest nodes"
    )
    if order_report:
        summary = order_report.get("summary") or {}
        publication = (index.get("storyOrder") or {}).get("publication") or {}
        print(
            f"Story partial order: {summary.get('strongEdges', 0)} strong edges, "
            f"{summary.get('questSucceedLifecycleEdges', 0)} binary-proven quest-success edges, "
            f"{summary.get('questForks', 0)} quest forks, "
            f"{summary.get('questMerges', 0)} quest merges, "
            f"{summary.get('nativeControlBranches', 0)} native branch groups, "
            f"{summary.get('nativeControlFullArmBranches', 0)} full-arm placements / "
            f"{summary.get('nativeControlSerializedArms', 0)} serialized slots "
            f"({summary.get('nativeControlNonStoryArms', 0)} active non-Story, "
            f"{summary.get('nativeControlInactiveTargetArms', 0)} inactive, "
            f"{summary.get('nativeControlRuntimeTerminalArms', 0)} runtime terminal, "
            f"{summary.get('nativeControlFullArmValidationFailures', 0)} validation failures), "
            f"{summary.get('nativeControlMerges', 0)} native convergences, "
            f"{summary.get('nativeControlCrossBoundaryBranches', 0)} complete cross-boundary groups "
            f"({summary.get('nativeControlCrossBoundaryExternalStories', 0)} external Story references), "
            f"{summary.get('nativeMissionStateBranches', 0)} mission-state alternative groups "
            f"({summary.get('nativeMissionStateBranchExternalStories', 0)} cross-mission references), "
            f"{summary.get('nativeControlPathTransitionEdges', 0)} exact native Story transitions "
            f"({summary.get('nativeControlPathBranchingTransitionEdges', 0)} branch-bearing), "
            f"{summary.get('nativeControlPathNamedActionEndpoints', 0)}/"
            f"{summary.get('nativeControlPathTransitionActionEndpoints', 0)} named transition endpoints, "
            f"{summary.get('dialogConditionalBranches', 0)} binary-validated local DialogTree conditionals, "
            f"{summary.get('dialogTreeBranchNodes', 0)} binary-validated DialogTree branch nodes / "
            f"{summary.get('dialogTreeBranchNodeArms', 0)} branch arms, "
            f"{summary.get('dialogTreeIfNodes', 0)} binary-validated DialogTree IfNodes / "
            f"{summary.get('dialogTreeIfNodeArms', 0)} IfNode arms, "
            f"{summary.get('dialogLineOptionBinaryValidatedGroups', 0)} binary-validated Timeline option groups / "
            f"{summary.get('dialogLineOptionRelatedFiles', 0)} related option-route files / "
            f"{summary.get('dialogLineOptionBinaryValidationFailures', 0)} Timeline option validation failures, "
            f"{summary.get('nativeOrderedSequences', 0)} native ordered sequences, "
            f"{summary.get('nativeOrderedSequenceContexts', 0)} native sequence contexts, "
            f"{summary.get('nativeSerializedBranchGroupCount', 0)} corpus serialized Branch groups / "
            f"{summary.get('nativeSerializedBranchArmCount', 0)} slots / "
            f"{summary.get('nativeSerializedPlaybackArmCount', 0)} playback arms / "
            f"{summary.get('nativeSerializedMultiPlaybackBranchCount', 0)} multi-playback groups, "
            f"{summary.get('nativeSerializedNestedControlCount', 0)} nested controls / "
            f"{summary.get('nativeSerializedNestedPlaybackArmCount', 0)} nested playback arms / "
            f"{summary.get('nativeSerializedNestedMultiPlaybackControlCount', 0)} multi-playback controls / "
            f"{summary.get('nativeSerializedNestedPlaybackControlCount', 0)} playback controls / "
            f"{summary.get('nativeSerializedNestedPlaybackPredicateGapCount', 0)} playback predicate gaps / "
            f"{summary.get('nativeSerializedNestedControlReferenceCount', 0)} nested control references / "
            f"{summary.get('nativeSerializedNestedArmCount', 0)} nested slots / "
            f"{summary.get('nativeSerializedNestedExactActiveArmCount', 0)} nested active / "
            f"{summary.get('nativeSerializedNestedInactiveArmCount', 0)} nested inactive / "
            f"{summary.get('nativeSerializedNestedUnavailableArmCount', 0)} nested unavailable / "
            f"{summary.get('nativeSerializedNestedControlArmSchemaUnavailableCount', 0)} arm-schema gaps / "
            f"{summary.get('nativeSerializedBranchPredicateConflictCount', 0)} predicate conflicts, "
            f"{summary.get('nativeRelatedActionTopologies', 0)} related action graphs, "
            f"{summary.get('nativeNamedPredicates', 0)} named predicates, "
            f"{summary.get('nativeInlinePredicates', 0)} inline predicates, "
            f"{summary.get('nativeSemanticPredicates', 0)} semantic predicates, "
            f"{summary.get('nativeClassOnlyPredicates', 0)} class-only predicates, "
            f"{summary.get('nativeUnresolvedPredicates', 0)} unresolved predicates"
        )
        print(
            "Story-order publication: "
            f"{publication.get('publishedNativeBranchPlacements', 0)}/"
            f"{publication.get('expectedNativeBranchPlacements', 0)} recovered native "
            "branch placements attached; "
            f"{len(publication.get('variantAggregateShells') or [])} validated "
            "variant aggregate shells"
        )
    if runtime_trace:
        summary = runtime_trace.get("summary") or {}
        print(
            f"Observed runtime trace: {summary.get('storyPlaybacks', 0)} playbacks, "
            f"{summary.get('exactEventActionChains', 0)} exact chains, "
            f"{summary.get('observedForks', 0)} forks, "
            f"{summary.get('observedMerges', 0)} merges"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

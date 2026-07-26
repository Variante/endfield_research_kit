"""Build the experimental Mission Pipeline graph payload for the static WebUI.

The payload keeps authored MissionRuntimeAsset structure separate from native
runtime conclusions.  Predecessor edges are prerequisites visible in exported
data; they are never promoted to proof that the client chooses a successor.

Run from the repository root:
    python scripts/build_mission_pipeline_data.py
"""
from __future__ import annotations

import argparse
import json
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

try:
    from common import (
        compact_dict,
        non_mission_content_keys,
        read_bytes_cached,
        read_json,
        write_report_json,
        write_text_if_changed,
    )
    from story_builder.levelscript_binary import decode_levelscript_encounter_module_target
    from story_recovery.build_envtalk_attachment import (
        build_report as build_envtalk_attachment_report,
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
except ModuleNotFoundError:  # imported as ``scripts.build_mission_pipeline_data``
    from scripts.common import (
        compact_dict,
        non_mission_content_keys,
        read_bytes_cached,
        read_json,
        write_report_json,
        write_text_if_changed,
    )
    from scripts.story_builder.levelscript_binary import (
        decode_levelscript_encounter_module_target,
    )
    from scripts.story_recovery.build_envtalk_attachment import (
        build_report as build_envtalk_attachment_report,
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


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MISSION_ROOT = (
    ROOT / "export_full" / "structured" / "StreamingAssets" / "Data" / "Json" / "MissionRuntimeAsset"
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

# Shipped-Lua Story playback call sites with a literal Story id.
#
# Story playback owners are not confined to LevelScript and MissionRuntime: Lua
# phase/UI controllers call the native GameAction entry points through the XLua
# wrappers. The Lua VFS corpus is not on the export path, so these recovered
# call sites are pinned here with exact provenance, the same way recovered
# native tags and RVAs are.
#
# Admission rule: the Lua literal must match the Story key EXACTLY, including
# case. `Phase/GenderSelect/PhaseGenderSelect.lua` holds
# `EnterCutsceneId = "Cutscene_e0m0_1"` with a capital C; that spelling occurs
# zero times anywhere in export_full while `cutscene_e0m0_1` occurs once, so the
# binding depends on case-insensitive resolution that has NOT been proved. It is
# deliberately excluded until the native resolver's casing behaviour is decoded.
LUA_STORY_PLAYBACK_CALL_SITES = (
    {
        "storyKey": "cutscene_e1m10_1",
        "luaFile": "Lua/Data/LuaScripts/Phase/GenderChange/PhaseGenderChange.lua",
        "luaSymbol": "CUT_SCENE_ID",
        "luaCall": "GameAction.PlayCutscene",
        "nativeEntry": "Beyond.Gameplay.Actions.GameAction::PlayCutscene",
        "phase": "gender_change",
        "note": (
            "Exact-case literal in a shipped Lua phase controller; the phase "
            "owns playback and no mission or quest identity is serialized."
        ),
    },
)
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
DEFAULT_OUTPUT_ROOT = ROOT / "webui" / "data" / "mission_pipeline"
DEFAULT_STORY_DATA_ROOT = ROOT / "webui" / "data" / "lang"
DEFAULT_REPORT_ROOT = ROOT / "reports" / "story" / "build"
DEFAULT_ORDER_REPORT_ROOT = ROOT / "reports" / "mission_order"
DEFAULT_MISSION_GRAPH_REPORT_ROOT = ROOT / "reports" / "mission_graph"
MISSION_RUNTIME_TRACE_SCHEMA = "missionRuntimeTrace.v1"
# v3 added per-mission ``missionGraph`` and quest-tracked ambient lines. v4
# extends ``envTalkContext`` with exact atmospheric-switcher state context.
SCHEMA_VERSION = 4
PIPELINE_STORY_KINDS = {"dlg", "sns", "cutscene", "black", "remotecomm", "radio"}
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
            "WorldChallengeGame.SendQuit reads that exact field, resolves the LevelScript, "
            "calls LevelScriptRuntime.ManualEnd, and then sends the stop request. Audited "
            "concrete and shared OnStart paths do not read bindScriptId."
        ),
        "ownershipBoundary": (
            "No audited GameMechanics lifecycle packet carries missionId, questId, "
            "sceneNumId, or bindScriptId. The row has no questId or sceneNumId, so the "
            "operational script identity cannot by itself attach a Story file."
        ),
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
                "is not a successor mission id and must not create an order edge."
            ),
            "confidence": "native_proven",
        },
        {
            "id": "quest-start",
            "direction": "server_to_client",
            "message": "SC_QUEST_STATE_UPDATE { questId, questState = 2, bRollback, roleBaseInfo }",
            "handler": "MissionSystem.Handle_QuestStateUpdate -> MissionRuntime.StartQuest",
            "address": "0x1873bf0a0 -> 0x183a885d0",
            "effect": "Create/bind the active client quest and its objective callbacks.",
            "confidence": "native_proven",
        },
        {
            "id": "quest-succeed",
            "direction": "server_to_client",
            "message": "SC_QUEST_STATE_UPDATE { questId, questState = 3, bRollback, roleBaseInfo }",
            "handler": "MissionSystem.Handle_QuestStateUpdate -> MissionRuntime.SucceedQuest",
            "address": "0x1873bf0a0 -> 0x1873c32ac",
            "effect": "Mark the quest completed on the client.",
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
                "by scriptId. The server push carries no mission, quest, condition, or "
                "Story id, so event-name equality alone cannot attach it to a pipeline."
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
            "effect": "Trigger a server LevelScript event and await an empty acknowledgement; this does not itself prove quest completion.",
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
            "address": "0x187386320",
            "finding": (
                "Consumes SC_SCENE_TRIGGER_CLIENT_LEVEL_SCRIPT_EVENT, constructs the "
                "LevelScript receiver from scriptId, copies a non-empty ctxToken into "
                "EventParams/ParamBlackboard, and raises eventName through "
                "LevelEventManager. The token is opaque propagated context; the handler "
                "does not decode it as mission/quest identity, and the packet has no "
                "mission, quest, condition, or Story identity."
            ),
            "confidence": "native_proven",
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
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--story-data-root", type=Path, default=DEFAULT_STORY_DATA_ROOT)
    parser.add_argument("--story-language", default="CN")
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
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


def repo_path(path: Path) -> str:
    path = path.resolve()
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.as_posix()


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

    The relation is deliberately mission-shell context. It never attaches a
    quest or Story file, even when the bound script has native playback.
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
            "knownConsumer": "WorldChallengeGame.SendQuit",
            "knownConsumerAddress": "0x186f60cc8",
            "knownEffect": "LevelScriptManager.TryGetLevelScript -> LevelScriptRuntime.ManualEnd -> send stop request",
            "auditedOnStartConsumerFound": False,
        },
        "evidenceBoundary": (
            "Exact typed mission↔SubGame↔LevelScript shell only; no quest or Story "
            "attachment is inferred from co-membership. OCR, manual, and gameplay "
            "cross-references cannot promote this relation."
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
)


def _native_occurrence_rows(row: dict[str, Any]) -> list[dict[str, Any]]:
    occurrences: list[dict[str, Any]] = []
    seen: set[str] = set()
    for field in NATIVE_OCCURRENCE_FIELDS:
        for occurrence in row.get(field) or []:
            if not isinstance(occurrence, dict):
                continue
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
    if relation == "original_text_definition_without_consumer":
        causality = "definition_only"
    elif owner_status == "unresolved":
        causality = "playback_owner_unresolved"
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
        row.get("sourceFiles"),
        [path.get("sourceFile") for path in native_paths],
    )

    owner_step = {
        "kind": "ownership_gap" if owner_status == "unresolved" else scope,
        "id": quest_id if scope == "quest" and quest_id else mission_id,
        "phase": str(row.get("phase") or ""),
    }
    story_step = {"kind": "story", "id": key}
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
    if action_names:
        middle_steps.append({"kind": "native_action", "ids": action_names})
    if direction == "story_to_quest":
        steps = [story_step, *middle_steps, owner_step]
    else:
        steps = [owner_step, *middle_steps, story_step]

    return {
        "storyKey": key,
        "missionId": mission_id,
        "questId": quest_id or None,
        "scope": scope,
        "ownerStatus": owner_status,
        "relation": relation,
        "direction": direction,
        "phase": str(row.get("phase") or ""),
        "causality": causality,
        "confidence": str(row.get("confidence") or ""),
        "evidenceTier": str(row.get("evidenceTier") or ""),
        "eventNames": event_names,
        "eventSummaries": event_summaries,
        "actionNames": action_names,
        "scriptIds": script_ids,
        "controlPathCount": int(row.get("nativeControlPathCount") or len(native_paths)),
        "nativePaths": native_paths,
        "sourceFiles": source_files,
        "serverMessage": str(row.get("serverMessage") or ""),
        "serverFields": _unique_route_strings(row.get("serverFields")),
        "serverExchange": row.get("serverExchange"),
        "questTriggerStatus": str(row.get("questTriggerStatus") or ""),
        "steps": steps,
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
    all_story_rows: dict[str, dict[str, Any]] = {}
    story_rows: dict[str, dict[str, Any]] = {}
    for row in story_index.get("entries") or []:
        if not isinstance(row, dict):
            continue
        key = str(row.get("k") or "")
        kind = str(row.get("d") or "")
        mission_id = str(row.get("m") or "")
        if key and kind in PIPELINE_STORY_KINDS:
            normalized_row = {
                "key": key,
                "kind": kind,
                "missionId": mission_id,
                "preview": str(row.get("p") or ""),
            }
            all_story_rows[key] = normalized_row
            if mission_id in mission_ids:
                story_rows[key] = normalized_row

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
    story_trigger_routes: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    sidecars_read = 0

    def add_trigger_route(route: dict[str, Any] | None) -> None:
        if not route:
            return
        key = str(route.get("storyKey") or "")
        if not key:
            return
        signature = json.dumps(
            route,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        story_trigger_routes[key][signature] = route

    for call_site in LUA_STORY_PLAYBACK_CALL_SITES:
        add_trigger_route({
            "storyKey": call_site["storyKey"],
            "relation": "lua_controller_playback",
            "causality": "playback_owner_unresolved",
            "direction": "playback",
            "scope": "phase",
            "phase": call_site["phase"],
            "evidenceTier": "direct",
            "confidence": "shipped_lua_literal_plus_native_entry",
            "ownerStatus": "unresolved",
            "questTriggerStatus": "no_mission_or_quest_identity_serialized",
            "missionId": None,
            "questId": None,
            "serverExchange": False,
            "luaFile": call_site["luaFile"],
            "luaSymbol": call_site["luaSymbol"],
            "luaCall": call_site["luaCall"],
            "nativeEntry": call_site["nativeEntry"],
            "sourceFiles": [call_site["luaFile"]],
            "note": call_site["note"],
            "steps": [
                {
                    "kind": "luaController",
                    "id": call_site["luaFile"],
                    "phase": call_site["phase"],
                },
                {
                    "kind": "nativePlayback",
                    "id": call_site["nativeEntry"],
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
                    owner_status="unresolved",
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
                            source_file = str(occurrence.get("sourceFile") or "")
                            source_path = ROOT / source_file
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
                                "_localProducerRoutes": {},
                                "storyFiles": {},
                            },
                        )
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
        unresolved_dialog_rows = (
            flow.get("unresolvedDialogTreeNarrativeActions")
            if "unresolvedDialogTreeNarrativeActions" in flow
            else flow.get("unlinkedDialogTreeNarrativeActions")
        )
        for row in unresolved_dialog_rows or []:
            if isinstance(row, dict) and str(row.get("key") or "") in story_rows:
                unresolved_dialog_tree_containment.add(str(row["key"]))
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
        for row in flow.get("unlinkedDialogTreeLeftSubtitleActions") or []:
            if isinstance(row, dict) and str(row.get("key") or "") in story_rows:
                unlinked_dialog_tree_left_subtitle.add(str(row["key"]))
        for row in flow.get("unresolvedDialogTreeStoryPlaybackCarriers") or []:
            if isinstance(row, dict) and str(row.get("key") or "") in story_rows:
                unresolved_dialog_tree_story_playback.add(str(row["key"]))
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

    unlinked = [row for key, row in story_rows.items() if key not in connected_keys]
    unlinked.sort(key=lambda row: (natural_quest_key(row["missionId"]), row["kind"], natural_quest_key(row["key"])))
    definition_only_classification = classify_definition_only_current_build_consumers(
        unlinked_definition_only,
        text_vo_id_table_path,
    )
    definition_only_class_counts = definition_only_classification["counts"]
    # Story ids defined only by non-mission authored content tables. These are
    # per-speaker radio continuation voice and character SNS topics; no mission
    # can own them, so they are reported as their own class instead of sitting
    # in the unassigned-Story queue. Table contents admit a key, never filenames.
    non_mission_content = non_mission_content_keys(DEFAULT_TABLE_ROOT)
    unlinked_non_mission_content = {
        key: non_mission_content[key]
        for key in story_rows
        if key not in connected_keys and key in non_mission_content
    }
    story_trigger_manifest: dict[str, dict[str, Any]] = {}
    story_files_with_trigger_routes = 0
    unlinked_files_with_trigger_routes = 0
    trigger_route_count = 0
    for key, story in sorted(story_rows.items(), key=lambda item: natural_quest_key(item[0])):
        routes = list(story_trigger_routes.get(key, {}).values())
        routes.sort(key=lambda route: (
            natural_quest_key(str(route.get("missionId") or "")),
            natural_quest_key(str(route.get("questId") or "")),
            str(route.get("causality") or ""),
            str(route.get("relation") or ""),
        ))
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
        story_trigger_manifest[key] = {
            "key": key,
            "kind": story["kind"],
            "nominalMissionId": story["missionId"],
            "attachmentStatus": attachment_status,
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

    report = {
        "schemaVersion": 3,
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
            "unlinkedStoryFilesWithTriggerRoutes": unlinked_files_with_trigger_routes,
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
        f"- Table-proven non-mission content (speaker radio continuation, character SNS topics): `{counts['nonMissionContentFiles']}`",
        f"- Missionless SubGame runtime nodes with exact playback: `{counts['missionlessSubGameRows']}`",
        f"- Unique Story files attached to those missionless nodes: `{counts['missionlessSubGameStoryFiles']}`",
        f"- Missionless SubGame-to-Story placements: `{counts['missionlessSubGameStoryPlacements']}`",
        f"- Exact missionless native runtime receiver nodes: `{counts['missionlessNativeRuntimeRows']}`",
        f"- Unique Story files attached to exact runtime receivers: `{counts['missionlessNativeRuntimeStoryFiles']}`",
        f"- Exact runtime-receiver-to-Story placements: `{counts['missionlessNativeRuntimeStoryPlacements']}`",
        f"- Connected files with another unresolved DialogTree parent use: `{counts['partiallyConnectedDialogTreeNarrativeFiles']}`",
        "",
        "## By kind",
        "",
        "| kind | total | connected | unlinked |",
        "| --- | ---: | ---: | ---: |",
    ]
    for kind, values in kind_counts.items():
        lines.append(f"| `{kind}` | {values['total']} | {values['connected']} | {values['unlinked']} |")
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
    "_questId",
    "questId",
    "_targetQuestId",
    "_targetQuestState",
    "targetQuestState",
    "compareTarget",
    "_sceneId",
    "sceneId",
    "_scriptId",
    "scriptId",
    "_propertyKey",
    "_key",
    "_guideGroupId",
    "_completeType",
    "_areaId",
    "_mapId",
    "needAllKill",
)


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


def objective_row(objective: dict[str, Any], index: int) -> dict[str, Any]:
    condition = objective.get("condition")
    objects = condition_objects(condition)
    types = sorted({type_name(row.get("$type")) for row in objects if type_name(row.get("$type"))})
    dialog_finishes: list[dict[str, Any]] = []
    quest_state_refs: list[dict[str, Any]] = []
    level_scripts: set[str] = set()
    properties: set[str] = set()
    server_placeholder_condition_ids: set[str] = set()
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
        "questStateRefs": quest_state_refs,
        "levelScriptIds": sorted(level_scripts),
        "propertyKeys": sorted(properties),
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

    roots = [node["id"] for node in nodes if not node["prev"]]
    fanouts = [node["id"] for node in nodes if len(node["successors"]) > 1]
    multi_prev = [node["id"] for node in nodes if len(node["prev"]) > 1]
    mission_name = mission.get("missionName") or {}
    mission_desc = mission.get("missionDescription") or {}
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
        # Ambient envTalk lines configured on an NPC proxy that a quest of this
        # mission tracks. Navigation/configuration context only -- never
        # playback ownership. See build_envtalk_attachment.py.
        "envTalkContext": sorted(
            env_talk_contexts or [],
            key=lambda row: (natural_quest_key(row.get("questId") or ""), row.get("storyKey") or ""),
        ),
    }
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
        "externalDependencyCount": external_dependency_count,
        "nativeRuntimeBindingCount": len(native_runtime_bindings or []),
        "activityStageHostCount": sum(
            len(node.get("activityStageHosts") or []) for node in nodes
        ),
        "activityStageHostedQuestCount": sum(
            1 for node in nodes if node.get("activityStageHosts")
        ),
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
    index = {
        "schemaVersion": SCHEMA_VERSION,
        "generated": int(time.time()),
        "source": mission_root.relative_to(ROOT).as_posix() if mission_root.is_relative_to(ROOT) else mission_root.as_posix(),
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
            "nativeRuntimeBindings": subgame_registry["missionBindingCount"],
            "nativeRuntimeBoundMissions": subgame_registry["boundMissionCount"],
            "nativeRuntimeDistinctScriptIds": subgame_registry["distinctScriptCount"],
            "activityQuestLevelRows": activity_host_registry["rowCount"],
            "activityQuestLevelQuests": activity_host_registry["questCount"],
            "activityQuestLevelMissions": sum(
                1 for row in summaries if row["activityStageHostCount"]
            ),
        },
        "conditionTypeMissionCounts": dict(sorted(condition_counts.items())),
        "runtimeContract": RUNTIME_CONTRACT,
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
    report = build_source_story_partial_order_report(
        language,
        story_data_root=story_data_root,
    )
    report_root.mkdir(parents=True, exist_ok=True)
    report_json = report_root / f"source_story_partial_order_{language}.json"
    report_markdown = report_root / f"source_story_partial_order_{language}.md"
    write_report_json(report_json, report)
    write_text_if_changed(
        report_markdown,
        render_source_story_partial_order_markdown(report),
    )

    rows_by_mission = {
        str(row.get("mission") or ""): row
        for row in report.get("missions") or []
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
        payload["storyOrder"] = order_row
        write_json(mission_path, payload)
        order_summary = order_row.get("summary") or {}
        summary["storyOrderSceneCount"] = int(order_summary.get("sceneCount") or 0)
        summary["storyOrderStrongEdgeCount"] = int(order_summary.get("strongEdgeCount") or 0)
        summary["storyOrderCycleCount"] = int(order_summary.get("cycleCount") or 0)
        summary["storyOrderNativeBranchCount"] = int(
            order_summary.get("nativeControlBranchCount") or 0
        )
        summary["storyOrderNativeMergeCount"] = int(
            order_summary.get("nativeControlMergeCount") or 0
        )
        summary["storyOrderNativeNamedPredicateCount"] = int(
            order_summary.get("nativeNamedPredicateCount") or 0
        )
        summary["storyOrderNativeInlinePredicateCount"] = int(
            order_summary.get("nativeInlinePredicateCount") or 0
        )
        summary["storyOrderNativeSemanticPredicateCount"] = int(
            order_summary.get("nativeSemanticPredicateCount") or 0
        )
        summary["storyOrderNativeClassOnlyPredicateCount"] = int(
            order_summary.get("nativeClassOnlyPredicateCount") or 0
        )
        summary["storyOrderNativeUnresolvedPredicateCount"] = int(
            order_summary.get("nativeUnresolvedPredicateCount") or 0
        )
        summary["storyOrderQuestForkCount"] = int(order_summary.get("questForkCount") or 0)
        summary["storyOrderQuestMergeCount"] = int(order_summary.get("questMergeCount") or 0)

    order_summary = report.get("summary") or {}
    index["storyOrder"] = {
        "schema": report.get("_schema"),
        "language": language,
        "summary": order_summary,
        "evidencePolicy": report.get("evidencePolicy") or {},
        "reportJson": repo_path(report_json),
        "reportMarkdown": repo_path(report_markdown),
    }
    write_json(output_root / "index.json", index)
    return report


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
    order_report = publish_source_story_partial_order(
        index,
        output_root,
        args.story_data_root.resolve(),
        args.story_language,
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
    )
    node_attachment = None
    if coverage:
        report_stem = f"mission_pipeline_story_binding_coverage_{coverage['language']}"
        coverage_report = args.report_root.resolve() / f"{report_stem}.json"
        index["storyCoverage"] = {
            "language": coverage["language"],
            "policy": coverage["policy"],
            "counts": coverage["counts"],
            "nativePlaybackEventFamilies": coverage["nativePlaybackEventFamilies"],
            "storyTriggerManifest": coverage["storyTriggerManifest"],
            "nonMissionContentKeys": coverage.get("nonMissionContentKeys") or [],
            "missionlessSubGamePlaybackNodes": coverage["missionlessSubGamePlaybackNodes"],
            "missionlessNativeRuntimeNodes": coverage["missionlessNativeRuntimeNodes"],
            "reportJson": repo_path(coverage_report),
            "reportMarkdown": repo_path(args.report_root.resolve() / f"{report_stem}.md"),
        }
        activation_frontier = build_native_receiver_activation_frontier_report(
            index,
            read_json(NATIVE_RECEIVER_MANUAL_CONTROL_AUDIT) or {},
            mission_root=output_root / "missions",
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
        )
        node_attachment = publish_quest_objective_story_scope(
            index,
            output_root,
            args.story_data_root.resolve(),
            coverage["language"],
            coverage_report,
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
    else:
        print(f"Story binding coverage skipped: no {args.story_language.upper()} Story bundle")
    if order_report:
        summary = order_report.get("summary") or {}
        print(
            f"Story partial order: {summary.get('strongEdges', 0)} strong edges, "
            f"{summary.get('questForks', 0)} quest forks, "
            f"{summary.get('questMerges', 0)} quest merges, "
            f"{summary.get('nativeControlBranches', 0)} native branch groups, "
            f"{summary.get('nativeControlMerges', 0)} native convergences, "
            f"{summary.get('nativeNamedPredicates', 0)} named predicates, "
            f"{summary.get('nativeInlinePredicates', 0)} inline predicates, "
            f"{summary.get('nativeSemanticPredicates', 0)} semantic predicates, "
            f"{summary.get('nativeClassOnlyPredicates', 0)} class-only predicates, "
            f"{summary.get('nativeUnresolvedPredicates', 0)} unresolved predicates"
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

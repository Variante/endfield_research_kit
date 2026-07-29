#!/usr/bin/env python3
"""Census nested managed mission/quest and Story/runtime identity carriers.

The direct managed-field census deliberately stops at one object.  This audit
uses the installed MetadataRegistration runtime type table to resolve generic
container arguments and follows custom managed fields to depth three.  Every
candidate is then assigned to an already recovered context, a bounded negative,
an aggregate runtime manager, or a non-carrier registry/catalog.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import importlib.util
import json
import re
import struct
import subprocess
import sys
import tempfile
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from common import md_escape, write_report_json, write_text_if_changed  # noqa: E402
from story_builder.anime_assets import (  # noqa: E402
    recover_dialog_tree_open_ui_actions,
)
from story_builder.mission_assets import select_complete_mission_runtime_root  # noqa: E402


METADATA_HELPER = (
    ROOT / "tools" / "endfield-il2cpp" / "catalog_option_flow_metadata.py"
)
MAPPER_HELPER = (
    ROOT / "tools" / "endfield-il2cpp" / "map_body_targets_to_gameassembly.py"
)
PROTOCOL_AUDIT = (
    ROOT / "scripts" / "story_recovery" / "build_protocol_registry_audit.py"
)
DEFAULT_GAME_ROOT = Path(r"D:\Program Files\Endfield Game\Endfield_Data")
DEFAULT_GAME_ASSEMBLY = DEFAULT_GAME_ROOT.parent / "GameAssembly.dll"
DEFAULT_METADATA = DEFAULT_GAME_ROOT / "il2cpp_data" / "Metadata" / "global-metadata.dat"
DEFAULT_ANIMESTUDIO_CLI = (
    ROOT / "tools" / "AnimeStudio" / "AnimeStudio.CLI" / "bin" / "Release"
    / "net9.0-windows" / "AnimeStudio.CLI.exe"
)
DEFAULT_IFIX_AUDIT = (
    ROOT / "reports" / "story" / "recovery" / "current_ifix_mission_graph_audit.json"
)
DEFAULT_OUT = (
    ROOT / "reports" / "story" / "recovery"
    / "nested_managed_identity_carrier_census.json"
)
DEFAULT_MARKDOWN = (
    ROOT / "reports" / "story" / "recovery"
    / "nested_managed_identity_carrier_census.md"
)

EXPECTED_GAME_ASSEMBLY_SHA256 = (
    "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
)
EXPECTED_METADATA_SHA256 = (
    "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
)
EXPECTED_IFIX_SHA256 = (
    "737134081e06371f13c073988547e887037fccf2f57e1052be35dd255d27bc21"
)
SUBMIT_ITEM_LUA_LOGICAL_PATH = (
    "Data/LuaScripts/UI/Panels/SubmitItem/SubmitItemCtrl.lua"
)
PHASE_DIALOG_LUA_LOGICAL_PATH = (
    "Data/LuaScripts/Phase/Dialog/PhaseDialog.lua"
)
EXPECTED_SUBMIT_ITEM_LUA_SHA256 = (
    "1c2a81f42d5512fc0bcfa35b78820d6482af15e2a2c8189fe85d81199286128e"
)
EXPECTED_PHASE_DIALOG_LUA_SHA256 = (
    "59df40f905d038f8a0527d680eca612e7b2ed4e0e9b3f7cfc96bf97bbe882b13"
)
DEFAULT_MISSION_RUNTIME_ROOT = select_complete_mission_runtime_root(
    ROOT
    / "export_full"
    / "structured"
    / "StreamingAssets"
    / "Data"
    / "Json"
    / "MissionRuntimeAsset",
    ROOT
    / "export_full"
    / "structured"
    / "Persistent"
    / "Data"
    / "Json"
    / "MissionRuntimeAsset",
)
DEFAULT_SUBMIT_ITEM_TABLE = (
    ROOT / "export_full" / "structured" / "StreamingAssets" / "Table"
    / "SubmitItem.json"
)
SUBMIT_ITEM_PANEL_TYPE = 9
SUBMIT_ITEM_PLACEHOLDER_PARAM = {
    "submitId": "提交id",
    "questId": "任务questId",
    "objId": "可选参数",
}
EXPECTED_OPEN_UI_COUNTS = {
    "typedTerminalActions": 95,
    "submitItemActions": 13,
    "parameterizedSubmitItemActions": 3,
    "placeholderSubmitItemActions": 3,
    "concreteQuestIdActions": 0,
}
MAX_DEPTH = 3


CLASSIFICATIONS = {
    "Beyond.Gameplay.Actions.ParamSource": (
        "closed_implicit_current_mission_context",
        "CURRENT_MISSION_ID is absent from LevelScripts and occurs only in "
        "already-owned MissionRuntime self-property checks.",
    ),
    "Beyond.Gameplay.AirWallManager": (
        "recovered_airwall_state_gated_context",
        "Exact AirWall group mission checks, script identity, and pushback radio "
        "playback are already represented as bounded non-owning context.",
    ),
    "Beyond.Gameplay.AirWallManager+<>c__DisplayClass104_0": (
        "recovered_airwall_state_gated_context",
        "The closure carries the selected pushback radio for the already recovered "
        "AirWall manager route; it adds no second ownership relation.",
    ),
    "Beyond.Gameplay.CheckLevelScriptTaskFinished": (
        "closed_objective_progress_callback",
        "The nested parentQuestId belongs to a task condition; the proven callback "
        "updates MissionSystem objective progress and does not play Story.",
    ),
    "Beyond.Gameplay.Core.DialogManager": (
        "recovered_xlua_pending_item_submitter_bridge",
        "Shipped SubmitItemCtrl Lua constructs and registers the pending submitter. "
        "Current typed DialogTree actions expose no concrete quest id to join.",
    ),
    "Beyond.Gameplay.Core.DialogManager+<>c__DisplayClass674_0": (
        "closed_global_dialog_manager_closure",
        "The closure's current dialog id reaches the global DialogManager; unrelated "
        "manager caches do not become quest ownership.",
    ),
    "Beyond.Gameplay.Core.FocusGameMode": (
        "recovered_focus_mode_context",
        "The nested FocusModeInstanceData mission/radio pair is already emitted as "
        "non-owning focus-mode interaction context.",
    ),
    "Beyond.Gameplay.Core.FocusModeInstanceData": (
        "recovered_focus_mode_context",
        "Thirteen authored mission/radio rows are already represented with their "
        "bounded focus-mode semantics.",
    ),
    "Beyond.Gameplay.Core.NpcRuntimeProxyData": (
        "recovered_npc_proxy_context",
        "NpcProxyEx mission/dialog rows and the one exact lazy-destroy tracking "
        "context are already represented without promoting server-selected state.",
    ),
    "Beyond.Gameplay.Core.NpcRuntimeProxyExData": (
        "recovered_npc_proxy_context",
        "The mission and dialog fields have separate native consumers; authored "
        "non-empty mission rows are already represented on their mission shell.",
    ),
    "Beyond.Gameplay.Core.SubGameInstanceData": (
        "recovered_subgame_runtime_shell",
        "Twenty dungeonMissionId/bindScriptId rows are already represented as "
        "SubGame runtime shells with zero inferred Story edge.",
    ),
    "Beyond.Gameplay.DataManager": (
        "closed_global_table_registry",
        "DataManager holds independent global tables; a dialog table and a nested "
        "mission-bearing config table do not identify the same authored record.",
    ),
    "Beyond.Gameplay.DomainDepotSystem": (
        "recovered_domain_depot_context",
        "The exact f1m25 delivery-table and target-dialog route is already recovered; "
        "the system-wide wait dialog and nested unlock rows add no new owner.",
    ),
    "Beyond.Gameplay.LevelFunctionAreaData+RadioTriggerZoneData": (
        "recovered_radio_trigger_zone_context",
        "Four exact LevelData radio rows and their hide-before/after/complete mission "
        "roles are already represented as non-owning state/playback context.",
    ),
    "Beyond.Gameplay.LevelScriptData": (
        "closed_level_aggregate",
        "LevelScriptData aggregates many independent level subsystems; nested quest "
        "locks and NPC dialogs are not co-record ownership.",
    ),
    "Beyond.Gameplay.MissionOptionData": (
        "closed_mutually_exclusive_actions",
        "missionId and callDialogId select mutually exclusive native action branches, "
        "and the current authored-instance census is empty.",
    ),
    "Beyond.Gameplay.MissionRuntimeAsset": (
        "closed_mission_property_script_pointer",
        "The apparent propertyDic to ParamVariable.m_scriptPtr path has no authored "
        "script pointer and no native mission-to-LevelScript writer.",
    ),
    "Beyond.Gameplay.MissionSystem": (
        "closed_global_mission_manager",
        "MissionSystem combines mission state, HUD tracking, and synchronized "
        "properties; its nested caches are separate runtime concerns.",
    ),
    "Beyond.Gameplay.MissionSystem+<>c__DisplayClass70_0": (
        "closed_global_mission_manager_closure",
        "The closure captures a quest id while retaining the whole MissionSystem; "
        "the global SNS tracking cache is not that quest's Story owner.",
    ),
    "Beyond.Gameplay.MissionSystem+<>c__DisplayClass78_0": (
        "closed_global_mission_manager_closure",
        "The closure captures a mission id while retaining the whole MissionSystem; "
        "the global SNS tracking cache supplies HUD context only.",
    ),
    "Beyond.Gameplay.MissionSystem+MissionData": (
        "closed_mission_property_script_pointer",
        "The synchronized propertyDict uses ParamVariable values but no audited "
        "writer attaches it to a LevelScript.",
    ),
    "Beyond.Gameplay.TeleportParam": (
        "closed_unused_mission_field",
        "Current producers do not co-populate missionId and levelScriptId, and "
        "audited consumers do not read missionId.",
    ),
    "Beyond.IdPickerAttribute+StringIdType": (
        "not_a_carrier_enum",
        "The names are editor picker alternatives, not values resident on one "
        "serialized or runtime object.",
    ),
    "Beyond.MemoryPack.MemoryPackDeSerializerRegister": (
        "not_a_carrier_formatter_registry",
        "The fields are independent static formatter initialization flags, not "
        "mission/Story identity values.",
    ),
    "Beyond.PropertyKeys": (
        "not_a_carrier_static_key_catalog",
        "The fields are independent global property-key constants, not values "
        "resident on one object.",
    ),
}

ITEM_SUBMITTER_TARGETS = {
    "InventoryItemSubmitter..ctor": {
        "methodIndex": 20718,
        "token": "0x060050ef",
        "address": "0x1873b0234",
    },
    "InventoryItemSubmitter.TryGetSubmitMsg": {
        "methodIndex": 20719,
        "token": "0x060050f0",
        "address": "0x1873b0144",
    },
    "DialogManager.RegisterPendingSubmission": {
        "methodIndex": 63357,
        "token": "0x0600f77e",
        "address": "0x186e17bc8",
    },
}

DIALOG_OPEN_UI_TARGET = {
    "symbol": "Beyond.Gameplay.Actions.GameAction.DialogOpenUIPanel",
    "methodIndex": 32816,
    "token": "0x06008031",
    "address": "0x1875e0224",
}

DIALOG_OPEN_UI_CALLERS = [{
    "symbol": "Beyond.Gameplay.Core.DialogManager.OpenUI",
    "methodIndex": 63380,
    "token": "0x0600f795",
    "address": "0x186e145d8",
}, {
    "symbol": (
        "XLua.CSObjectWrap.BeyondGameplayActionsGameActionWrap."
        "_m_DialogOpenUIPanel_xlua_st_"
    ),
    "methodIndex": 111616,
    "token": "0x060033f2",
    "address": "0x18630c078",
}]
DIALOG_MANAGER_OPEN_UI_TARGET = {
    "symbol": "Beyond.Gameplay.Core.DialogManager.OpenUI",
    "methodIndex": 63380,
    "token": "0x0600f795",
    "address": "0x186e145d8",
}
DIALOG_MANAGER_OPEN_UI_EXPECTED_CALLER = {
    "symbol": "Beyond.Gameplay.DialogTreeOpenUINode.DoAction",
    "methodIndex": 15072,
    "token": "0x06003ae1",
    "address": "0x1872a5e1c",
}


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dump_target_lua(
    *,
    animestudio_cli: Path,
    game_root: Path,
    lua_source: Path | None,
    logical_path: str,
) -> tuple[bytes, dict[str, Any]]:
    """Read a supplied plaintext Lua file or target-dump it from installed VFS."""
    if lua_source is not None:
        raw = lua_source.read_bytes()
        return raw, {
            "mode": "supplied_plaintext",
            "path": str(lua_source.resolve()),
            "logicalPath": logical_path,
        }

    file_name = Path(logical_path).name
    streaming_assets = game_root / "StreamingAssets"
    if not animestudio_cli.is_file():
        raise FileNotFoundError(f"AnimeStudio CLI not found: {animestudio_cli}")
    if not streaming_assets.is_dir():
        raise FileNotFoundError(
            f"installed StreamingAssets not found: {streaming_assets}"
        )
    with tempfile.TemporaryDirectory(
        prefix=f"endfield-{file_name.lower().replace('.', '-')}-"
    ) as temp_name:
        output_root = Path(temp_name)
        command = [
            str(animestudio_cli),
            "dump",
            "--streaming-assets",
            str(streaming_assets),
            "--fallback-assets",
            str(game_root),
            "--output",
            str(output_root),
            "--block-type",
            "lua",
            "--file-regex",
            rf"{re.escape(file_name)}$",
        ]
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if completed.returncode:
            raise RuntimeError(
                "AnimeStudio targeted Lua dump failed "
                f"({completed.returncode}): {completed.stderr or completed.stdout}"
            )
        matches = list(output_root.rglob(file_name))
        if len(matches) != 1:
            raise RuntimeError(
                "AnimeStudio targeted Lua dump returned "
                f"{len(matches)} {file_name} files"
            )
        raw = matches[0].read_bytes()
    return raw, {
        "mode": "targeted_installed_vfs_dump",
        "logicalPath": logical_path,
        "animeStudioCli": str(animestudio_cli.resolve()),
        "animeStudioCliSha256": sha256_file(animestudio_cli),
        "streamingAssets": str(streaming_assets.resolve()),
    }


def lua_line_number(text: str, needle: str) -> int | None:
    for line_number, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return line_number
    return None


def audit_submit_item_lua(raw: bytes, source: dict[str, Any]) -> dict[str, Any]:
    text = raw.decode("utf-8-sig")
    constructor_call = (
        "GameWorld.dialogManager:RegisterPendingSubmission("
        "CS.Beyond.Gameplay.InventoryItemSubmitter("
    )
    direct_submit_call = "GameInstance.player.inventory:SubmitItem("
    argument_sequence = re.compile(
        r"InventoryItemSubmitter\(\s*"
        r"Utils\.getCurrentScope\(\),\s*"
        r"Utils\.getCurrentChapterId\(\),\s*"
        r"self\.m_info\.submitId,\s*"
        r"self\.m_info\.questId,\s*"
        r"self\.m_info\.objId,\s*"
        r"selectInstIds,\s*"
        r"selectItemIds\s*\)",
        re.MULTILINE,
    )
    return {
        "source": {
            **source,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        },
        "controller": "SubmitItemCtrl",
        "producerKind": "shipped_xlua_managed_constructor",
        "constructorAndRegistrationCalls": text.count(constructor_call),
        "directInventorySubmissionCalls": text.count(direct_submit_call),
        "orderedConstructorArgumentMatches": len(argument_sequence.findall(text)),
        "constructorArguments": [
            "scope",
            "chapterId",
            "submitId",
            "questId",
            "objId",
            "instItems",
            "itemIds",
        ],
        "branches": {
            "fromDialog": text.count("if self.m_info.fromDialog then"),
            "syncSubmitToServerImmediately": text.count(
                "self.m_info.actionData.syncSubmitToServerImmediately"
            ),
            "dialogManagerPlaying": text.count(
                "elseif GameWorld.dialogManager.isPlaying then"
            ),
        },
        "lines": {
            "fromDialog": lua_line_number(
                text, "if self.m_info.fromDialog then"
            ),
            "constructorAndRegistration": lua_line_number(
                text, constructor_call
            ),
            "directInventorySubmission": lua_line_number(
                text, direct_submit_call
            ),
        },
        "finding": (
            "The shipped SubmitItem controller constructs "
            "InventoryItemSubmitter through XLua and registers it on the active "
            "DialogManager when submission originated from a playing dialog and "
            "is not configured for immediate server submission."
        ),
    }


def audit_phase_dialog_lua(raw: bytes, source: dict[str, Any]) -> dict[str, Any]:
    text = raw.decode("utf-8-sig")
    patterns = {
        "unpackActionArguments": (
            "local panelIdStr, paramStr, actionData = unpack(arg)"
        ),
        "jsonDecodeParam": "Utils.stringJsonToTable(paramStr)",
        "markFromDialog": "param.fromDialog = true",
        "attachActionData": "param.actionData = actionData",
        "openPhase": "PhaseManager:OpenPhase(phaseId, param, nil, true)",
    }
    return {
        "source": {
            **source,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        },
        "patternCounts": {
            name: text.count(pattern) for name, pattern in patterns.items()
        },
        "lines": {
            name: lua_line_number(text, pattern)
            for name, pattern in patterns.items()
        },
        "finding": (
            "PhaseDialog.OpenUI unpacks the native panel id, parameter string, "
            "and original action object; JSON-decodes the parameter verbatim; "
            "then adds only fromDialog and actionData before opening the phase. "
            "It performs no mission or quest lookup and supplies no fallback "
            "submission identity."
        ),
    }


def type_name(value: Any) -> str:
    return str(value or "").split(",", 1)[0].rsplit(".", 1)[-1]


def const_value(value: Any) -> Any:
    if isinstance(value, dict) and "constValue" in value:
        return value.get("constValue")
    return value


def iter_condition_rows(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.get("subConditions") or []:
            yield from iter_condition_rows(child)


def audit_authored_submit_item_objectives(
    mission_root: Path,
    submit_item_table_path: Path,
    open_ui_actions: dict[str, Any],
) -> dict[str, Any]:
    table = json.loads(submit_item_table_path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    with_subgame_count = 0
    for path in sorted(mission_root.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        mission_id = str(payload.get("missionId") or path.stem)
        for quest_id, quest in (payload.get("questDic") or {}).items():
            if not isinstance(quest, dict):
                continue
            for objective_index, objective in enumerate(
                quest.get("objectiveList") or [], 1
            ):
                if not isinstance(objective, dict):
                    continue
                condition = objective.get("condition")
                condition_rows = list(iter_condition_rows(condition))
                with_subgame_count += sum(
                    type_name(row.get("$type"))
                    == "CheckQuestSubmitItemWithSubGame"
                    for row in condition_rows
                )
                for condition_row in condition_rows:
                    if (
                        type_name(condition_row.get("$type"))
                        != "CheckQuestSubmitItem"
                    ):
                        continue
                    submission_id = const_value(
                        condition_row.get("_submissionId")
                    )
                    table_row = (
                        table.get(submission_id)
                        if isinstance(submission_id, str)
                        else None
                    )
                    co_gates: list[dict[str, Any]] = []
                    for combine in condition_rows:
                        children = [
                            child
                            for child in combine.get("subConditions") or []
                            if isinstance(child, dict)
                        ]
                        if condition_row not in children or "and" not in str(
                            combine.get("conditionEvalString") or ""
                        ).lower():
                            continue
                        for sibling in children:
                            if type_name(sibling.get("$type")) != (
                                "CheckTalkOptionFinish"
                            ):
                                continue
                            co_gates.append({
                                "dialogId": const_value(
                                    sibling.get("_dialogId")
                                ),
                                "finishId": const_value(
                                    sibling.get("_finishId")
                                ),
                                "combineConditionId": str(
                                    combine.get("uniqueId") or ""
                                ),
                                "relation": "same_authored_and_objective",
                            })
                    requirements = []
                    if isinstance(table_row, dict):
                        for group in table_row.get("paramData") or []:
                            params = group.get("paramList") or []
                            item_ids = (
                                params[0].get("valueStringList") or []
                                if len(params) > 0
                                and isinstance(params[0], dict)
                                else []
                            )
                            counts = (
                                params[1].get("valueIntList") or []
                                if len(params) > 1
                                and isinstance(params[1], dict)
                                else []
                            )
                            requirements.append([{
                                "itemId": str(item_id),
                                "count": (
                                    counts[index]
                                    if index < len(counts)
                                    else counts[0] if counts else None
                                ),
                            } for index, item_id in enumerate(item_ids)])
                    rows.append({
                        "missionId": mission_id,
                        "questId": str(quest_id),
                        "objectiveIndex": objective_index,
                        "conditionId": str(
                            condition_row.get("uniqueId") or ""
                        ),
                        "submissionId": submission_id,
                        "tableDefined": isinstance(table_row, dict),
                        "requirements": requirements,
                        "dialogCoGates": co_gates,
                    })
    open_ui_dialogs = {
        str(row.get("dialogKey") or "")
        for row in open_ui_actions.get("actions") or []
        if row.get("dialogKey")
    }
    co_gate_dialogs = {
        str(gate.get("dialogId") or "")
        for row in rows
        for gate in row["dialogCoGates"]
        if gate.get("dialogId")
    }
    return {
        "source": {
            "missionRuntimeRoot": str(mission_root.resolve()),
            "submitItemTable": str(submit_item_table_path.resolve()),
        },
        "conditionCount": len(rows),
        "questCount": len({row["questId"] for row in rows}),
        "missionCount": len({row["missionId"] for row in rows}),
        "tableDefinedCount": sum(row["tableDefined"] for row in rows),
        "dialogCoGateCount": sum(len(row["dialogCoGates"]) for row in rows),
        "dialogCoGateOpenUiOverlap": len(co_gate_dialogs & open_ui_dialogs),
        "withSubGameConditionCount": with_subgame_count,
        "rows": rows,
        "finding": (
            "Three exact MissionRuntime objectives test a SubmitItem table id; "
            "all three table definitions resolve to exact item requirements. "
            "Two checks share an authored AND objective with a dialog-finish "
            "condition, but neither dialog occurs among the 13 typed SubmitItem "
            "OpenUI terminals. These are exact quest-to-submission requirements "
            "and bounded dialog co-gates, not quest-to-OpenUI ownership."
        ),
    }


def audit_authored_submit_item_actions() -> dict[str, Any]:
    rows = recover_dialog_tree_open_ui_actions()
    submit_rows = [
        row for row in rows if row.get("panelType") == SUBMIT_ITEM_PANEL_TYPE
    ]
    parameterized = [
        row for row in submit_rows if bool(row.get("paramData"))
    ]
    placeholders = [
        row
        for row in parameterized
        if row.get("paramData") == SUBMIT_ITEM_PLACEHOLDER_PARAM
    ]
    concrete = [
        row
        for row in parameterized
        if str((row.get("paramData") or {}).get("questId") or "").strip()
        not in {"", SUBMIT_ITEM_PLACEHOLDER_PARAM["questId"]}
    ]
    return {
        "source": (
            "typed DialogTreeOpenUINode -> DialogOpenUIAction terminals from "
            "exported AnimeStudio TextAssets"
        ),
        "panelType": SUBMIT_ITEM_PANEL_TYPE,
        "panelClassification": "SubmitItem_by_exact_parameter_template",
        "typedTerminalActions": len(rows),
        "submitItemActions": len(submit_rows),
        "parameterizedSubmitItemActions": len(parameterized),
        "placeholderSubmitItemActions": len(placeholders),
        "emptyParamSubmitItemActions": sum(
            not bool(row.get("paramData")) for row in submit_rows
        ),
        "concreteQuestIdActions": len(concrete),
        "placeholderParam": SUBMIT_ITEM_PLACEHOLDER_PARAM,
        "actions": [{
            "dialogKey": row.get("dialogKey"),
            "paramData": row.get("paramData"),
            "finishIds": row.get("finishIds"),
            "sourceFile": row.get("sourceFile"),
        } for row in submit_rows],
        "finding": (
            "Thirteen typed panelType 9 terminals exist. Three carry the exact "
            "DIALOG_OPEN_UI_PARAM_SUBMITITEM authoring placeholder and ten have "
            "empty params; none exports a concrete quest id."
        ),
    }


def scan_direct_callers(
    pe: Any,
    method_by_pointer: dict[int, list[dict[str, Any]]],
    method_pointers: list[int],
    targets: dict[int, str],
) -> dict[str, list[dict[str, Any]]]:
    callers = {name: [] for name in targets.values()}
    for section in pe.sections:
        if section["name"] not in {".text", "il2cpp"} or not section["rawSize"]:
            continue
        data = pe.buf[
            section["rawPointer"]:section["rawPointer"] + section["rawSize"]
        ]
        position = data.find(b"\xe8")
        while position >= 0:
            if position + 5 <= len(data):
                call_va = pe.image_base + section["virtualAddress"] + position
                relative = struct.unpack_from("<i", data, position + 1)[0]
                target_name = targets.get(call_va + 5 + relative)
                if target_name is not None:
                    pointer_pos = bisect.bisect_right(method_pointers, call_va) - 1
                    method_pointer = (
                        method_pointers[pointer_pos] if pointer_pos >= 0 else None
                    )
                    callers[target_name].append({
                        "callAddress": f"0x{call_va:x}",
                        "callerAddress": (
                            f"0x{method_pointer:x}"
                            if method_pointer is not None
                            else None
                        ),
                        "resolved": method_by_pointer.get(method_pointer, []),
                    })
            position = data.find(b"\xe8", position + 1)
    return callers


def build_report(
    *,
    game_assembly: Path,
    metadata_path: Path,
    ifix_audit_path: Path,
    game_root: Path,
    animestudio_cli: Path,
    lua_source: Path | None,
    phase_dialog_lua_source: Path | None,
    mission_root: Path = DEFAULT_MISSION_RUNTIME_ROOT,
    submit_item_table_path: Path = DEFAULT_SUBMIT_ITEM_TABLE,
) -> dict[str, Any]:
    metadata_module = load_module("nested_carrier_metadata", METADATA_HELPER)
    mapper = load_module("nested_carrier_mapper", MAPPER_HELPER)
    protocol = load_module("nested_carrier_protocol", PROTOCOL_AUDIT)
    metadata = metadata_module.Metadata(metadata_path)
    pe = mapper.PeImage(game_assembly)
    metadata_registration = mapper.find_metadata_registration(
        pe, mapper.DEFAULT_CODE_REGISTRATION
    )
    if metadata_registration is None:
        raise RuntimeError("could not derive MetadataRegistration")
    registration = mapper.metadata_registration_summary(pe, metadata_registration)
    runtime_types_va = int(registration["types"], 16)
    runtime_type_count = int(registration["typesCount"])

    type_names = {
        metadata.type_full_name(type_def): type_def
        for type_def in metadata.types
    }
    custom_type_names = {
        name
        for name in type_names
        if not name.startswith((
            "System.",
            "Microsoft.",
            "Google.",
            "UnityEngine.",
            "Unity.",
            "Proto.",
        ))
    }
    token_re = re.compile(r"[A-Za-z_][A-Za-z0-9_.+`]*")

    @lru_cache(maxsize=None)
    def runtime_field_type(type_index: int) -> str:
        if not 0 <= type_index < runtime_type_count:
            return f"<type-index:{type_index}>"
        type_va = pe.u64_at_va(runtime_types_va + type_index * 8)
        return protocol.runtime_type_name(pe, metadata, type_va)

    @lru_cache(maxsize=None)
    def dependencies(runtime_name: str) -> tuple[str, ...]:
        return tuple(sorted({
            token
            for token in token_re.findall(runtime_name)
            if token in custom_type_names
        }))

    fields_by_type: dict[str, list[dict[str, Any]]] = {}
    for type_name, type_def in type_names.items():
        if type_name.startswith("Proto."):
            continue
        fields_by_type[type_name] = [{
            "name": metadata.string(field.name_index),
            "token": f"0x{field.token:08x}",
            "runtimeType": runtime_field_type(field.type_index),
            "dependencies": list(dependencies(runtime_field_type(field.type_index))),
            "classes": sorted(
                protocol.protobuf_identity_field_classes(
                    metadata.string(field.name_index)
                )
            ),
        } for field in metadata.fields_for(type_def)]

    @lru_cache(maxsize=None)
    def evidence(
        type_name: str,
        identity_class: str,
        depth: int,
        trail: tuple[str, ...] = (),
    ) -> tuple[tuple[dict[str, Any], ...], bool]:
        if type_name in trail:
            return (), False
        found: list[dict[str, Any]] = []
        direct = False
        for field in fields_by_type.get(type_name, []):
            if identity_class in field["classes"]:
                direct = True
                found.append({
                    "path": f"{type_name}.{field['name']}",
                    "ownerType": type_name,
                    "field": field["name"],
                    "runtimeType": field["runtimeType"],
                    "depth": 0,
                })
            if depth <= 0:
                continue
            for dependency in field["dependencies"]:
                child_rows, _ = evidence(
                    dependency,
                    identity_class,
                    depth - 1,
                    (*trail, type_name),
                )
                for child in child_rows:
                    found.append({
                        **child,
                        "path": f"{type_name}.{field['name']} -> {child['path']}",
                        "depth": child["depth"] + 1,
                    })
        unique = {
            (row["path"], row["ownerType"], row["field"]): row
            for row in found
        }
        return tuple(unique.values()), direct

    candidates = []
    for type_name in sorted(fields_by_type):
        mission, mission_direct = evidence(
            type_name, "mission_or_quest", MAX_DEPTH
        )
        level_script, level_script_direct = evidence(
            type_name, "level_script", MAX_DEPTH
        )
        story, story_direct = evidence(type_name, "story", MAX_DEPTH)
        if not mission or not (level_script or story):
            continue
        if not (mission_direct or level_script_direct or story_direct):
            continue
        status, finding = CLASSIFICATIONS.get(
            type_name,
            ("unreviewed", "No current classification."),
        )
        candidates.append({
            "type": type_name,
            "image": metadata.image_name_by_type_index.get(
                type_names[type_name].index, ""
            ),
            "directClasses": sorted(
                identity_class
                for identity_class, present in (
                    ("mission_or_quest", mission_direct),
                    ("level_script", level_script_direct),
                    ("story", story_direct),
                )
                if present
            ),
            "minimumDepth": {
                "mission_or_quest": min(row["depth"] for row in mission),
                "level_script": (
                    min(row["depth"] for row in level_script)
                    if level_script
                    else None
                ),
                "story": (
                    min(row["depth"] for row in story)
                    if story
                    else None
                ),
            },
            "representativePaths": {
                "mission_or_quest": min(
                    mission, key=lambda row: (row["depth"], row["path"])
                )["path"],
                "level_script": (
                    min(
                        level_script,
                        key=lambda row: (row["depth"], row["path"]),
                    )["path"]
                    if level_script
                    else None
                ),
                "story": (
                    min(story, key=lambda row: (row["depth"], row["path"]))[
                        "path"
                    ]
                    if story
                    else None
                ),
            },
            "status": status,
            "finding": finding,
        })

    modules = mapper.parse_codegen_modules(pe, mapper.DEFAULT_CODE_REGISTRATION)
    ranges = mapper.image_method_ranges(metadata)
    pointers_by_image, method_by_pointer = mapper.build_pointer_indexes(
        pe, metadata, modules, ranges
    )
    generic_index = mapper.build_generic_method_index(
        pe,
        metadata,
        mapper.DEFAULT_CODE_REGISTRATION,
        metadata_registration,
    )
    for pointer, rows in generic_index.items():
        method_by_pointer.setdefault(pointer, rows)
    method_pointers = sorted(
        set(method_by_pointer)
        | {
            pointer
            for pointers in pointers_by_image.values()
            for pointer in pointers
            if pointer
        }
    )
    target_by_va = {
        int(row["address"], 16): name
        for name, row in ITEM_SUBMITTER_TARGETS.items()
    }
    target_by_va[int(DIALOG_OPEN_UI_TARGET["address"], 16)] = (
        DIALOG_OPEN_UI_TARGET["symbol"]
    )
    target_by_va[int(DIALOG_MANAGER_OPEN_UI_TARGET["address"], 16)] = (
        DIALOG_MANAGER_OPEN_UI_TARGET["symbol"]
    )
    direct_callers = scan_direct_callers(
        pe, method_by_pointer, method_pointers, target_by_va
    )
    lua_raw, lua_source_info = dump_target_lua(
        animestudio_cli=animestudio_cli,
        game_root=game_root,
        lua_source=lua_source,
        logical_path=SUBMIT_ITEM_LUA_LOGICAL_PATH,
    )
    lua_producer = audit_submit_item_lua(lua_raw, lua_source_info)
    phase_dialog_raw, phase_dialog_source_info = dump_target_lua(
        animestudio_cli=animestudio_cli,
        game_root=game_root,
        lua_source=phase_dialog_lua_source,
        logical_path=PHASE_DIALOG_LUA_LOGICAL_PATH,
    )
    phase_dialog_flow = audit_phase_dialog_lua(
        phase_dialog_raw, phase_dialog_source_info
    )
    authored_open_ui = audit_authored_submit_item_actions()
    authored_objectives = audit_authored_submit_item_objectives(
        mission_root,
        submit_item_table_path,
        authored_open_ui,
    )
    ifix_audit = json.loads(ifix_audit_path.read_text(encoding="utf-8"))
    fixed_signatures = [
        str(row.get("signature") or "")
        for row in ifix_audit.get("fixedMethods", [])
    ]
    submitter_ifix_matches = [
        signature
        for signature in fixed_signatures
        if "InventoryItemSubmitter" in signature
        or "RegisterPendingSubmission" in signature
        or "SendFinishDialog" in signature
    ]

    candidate_types = {row["type"] for row in candidates}
    expected_types = set(CLASSIFICATIONS)
    unreviewed = [
        row["type"] for row in candidates if row["status"] == "unreviewed"
    ]
    errors = []
    if candidate_types != expected_types:
        errors.append(
            "candidate type set changed: "
            f"missing={sorted(expected_types - candidate_types)} "
            f"added={sorted(candidate_types - expected_types)}"
        )
    if unreviewed:
        errors.append(f"unreviewed candidates: {unreviewed}")
    expected_caller_counts = {
        "InventoryItemSubmitter..ctor": 0,
        "InventoryItemSubmitter.TryGetSubmitMsg": 1,
        "DialogManager.RegisterPendingSubmission": 0,
    }
    caller_counts = {
        name: len(direct_callers[name]) for name in ITEM_SUBMITTER_TARGETS
    }
    if caller_counts != expected_caller_counts:
        errors.append(
            f"item submitter direct caller counts changed: {caller_counts}"
        )
    game_sha = sha256_file(game_assembly)
    metadata_sha = sha256_file(metadata_path)
    ifix_sha = str(ifix_audit.get("source", {}).get("patchSha256") or "")
    if game_sha != EXPECTED_GAME_ASSEMBLY_SHA256:
        errors.append("GameAssembly SHA256 changed")
    if metadata_sha != EXPECTED_METADATA_SHA256:
        errors.append("global-metadata SHA256 changed")
    if ifix_sha != EXPECTED_IFIX_SHA256:
        errors.append("IFix SHA256 changed")
    if submitter_ifix_matches:
        errors.append(
            f"item submitter IFix targets appeared: {submitter_ifix_matches}"
        )
    lua_sha = lua_producer["source"]["sha256"]
    if lua_sha != EXPECTED_SUBMIT_ITEM_LUA_SHA256:
        errors.append("SubmitItemCtrl.lua SHA256 changed")
    if lua_producer["constructorAndRegistrationCalls"] != 1:
        errors.append(
            "SubmitItemCtrl constructor/registration call count changed: "
            f"{lua_producer['constructorAndRegistrationCalls']}"
        )
    if lua_producer["orderedConstructorArgumentMatches"] != 1:
        errors.append(
            "SubmitItemCtrl ordered constructor arguments changed: "
            f"{lua_producer['orderedConstructorArgumentMatches']}"
        )
    if lua_producer["directInventorySubmissionCalls"] != 1:
        errors.append(
            "SubmitItemCtrl direct submission call count changed: "
            f"{lua_producer['directInventorySubmissionCalls']}"
        )
    if (
        phase_dialog_flow["source"]["sha256"]
        != EXPECTED_PHASE_DIALOG_LUA_SHA256
    ):
        errors.append("PhaseDialog.lua SHA256 changed")
    unexpected_phase_counts = {
        key: count
        for key, count in phase_dialog_flow["patternCounts"].items()
        if count != 1
    }
    if unexpected_phase_counts:
        errors.append(
            "PhaseDialog OpenUI pass-through patterns changed: "
            f"{unexpected_phase_counts}"
        )
    actual_open_ui_counts = {
        key: authored_open_ui[key] for key in EXPECTED_OPEN_UI_COUNTS
    }
    if actual_open_ui_counts != EXPECTED_OPEN_UI_COUNTS:
        errors.append(
            f"authored SubmitItem OpenUI counts changed: {actual_open_ui_counts}"
        )
    open_ui_callers = direct_callers[DIALOG_OPEN_UI_TARGET["symbol"]]
    if len(open_ui_callers) != 2:
        errors.append(
            "DialogOpenUIPanel native direct caller count changed: "
            f"{len(open_ui_callers)}"
        )
    else:
        resolved_open_ui_callers = {
            f"{row.get('type')}.{row.get('method')}"
            for caller in open_ui_callers
            for row in caller.get("resolved", [])
        }
        expected_open_ui_callers = {
            row["symbol"] for row in DIALOG_OPEN_UI_CALLERS
        }
        if resolved_open_ui_callers != expected_open_ui_callers:
            errors.append(
                "DialogOpenUIPanel direct callers changed: "
                f"{sorted(resolved_open_ui_callers)}"
            )
    dialog_manager_open_ui_callers = direct_callers[
        DIALOG_MANAGER_OPEN_UI_TARGET["symbol"]
    ]
    resolved_dialog_manager_open_ui_callers = {
        f"{row.get('type')}.{row.get('method')}"
        for caller in dialog_manager_open_ui_callers
        for row in caller.get("resolved", [])
    }
    if resolved_dialog_manager_open_ui_callers != {
        DIALOG_MANAGER_OPEN_UI_EXPECTED_CALLER["symbol"]
    }:
        errors.append(
            "DialogManager.OpenUI direct callers changed: "
            f"{sorted(resolved_dialog_manager_open_ui_callers)}"
        )
    expected_objective_counts = {
        "conditionCount": 3,
        "questCount": 3,
        "missionCount": 3,
        "tableDefinedCount": 3,
        "dialogCoGateCount": 2,
        "dialogCoGateOpenUiOverlap": 0,
        "withSubGameConditionCount": 0,
    }
    actual_objective_counts = {
        key: authored_objectives[key] for key in expected_objective_counts
    }
    if actual_objective_counts != expected_objective_counts:
        errors.append(
            "authored SubmitItem objective counts changed: "
            f"{actual_objective_counts}"
        )

    direct_exact_count = sum(
        "mission_or_quest" in row["directClasses"]
        and (
            "level_script" in row["directClasses"]
            or "story" in row["directClasses"]
        )
        for row in candidates
    )
    return {
        "schemaVersion": 3,
        "source": {
            "gameAssembly": str(game_assembly.resolve()),
            "gameAssemblySha256": game_sha,
            "metadata": str(metadata_path.resolve()),
            "metadataSha256": metadata_sha,
            "codeRegistration": f"0x{mapper.DEFAULT_CODE_REGISTRATION:x}",
            "metadataRegistration": f"0x{metadata_registration:x}",
            "runtimeTypesTable": f"0x{runtime_types_va:x}",
            "runtimeTypeCount": runtime_type_count,
            "ifixAudit": str(ifix_audit_path.resolve()),
            "ifixSha256": ifix_sha,
        },
        "census": {
            "maxDepth": MAX_DEPTH,
            "metadataTypeRecords": len(metadata.types),
            "uniqueTypeDefinitions": len(type_names),
            "customTypeDefinitions": len(custom_type_names),
            "candidateTypes": len(candidates),
            "directExactCandidateTypes": direct_exact_count,
            "nestedDependentCandidateTypes": len(candidates) - direct_exact_count,
            "reviewedCandidateTypes": len(candidates) - len(unreviewed),
            "unreviewedCandidateTypes": len(unreviewed),
            "classificationCounts": dict(sorted(
                Counter(row["status"] for row in candidates).items()
            )),
        },
        "candidates": candidates,
        "pendingItemSubmitterClosure": {
            "managedLayout": {
                "DialogManager.m_pendingItemSubmitter": {
                    "token": "0x0400b304",
                    "offset": "0x200",
                },
                "InventoryItemSubmitter.scope": {
                    "token": "0x04004754",
                    "offset": "0x10",
                },
                "InventoryItemSubmitter.chapterId": {
                    "token": "0x04004755",
                    "offset": "0x14",
                },
                "InventoryItemSubmitter.submitId": {
                    "token": "0x04004758",
                    "offset": "0x18",
                },
                "InventoryItemSubmitter.questId": {
                    "token": "0x04004759",
                    "offset": "0x20",
                },
                "InventoryItemSubmitter.objId": {
                    "token": "0x0400475a",
                    "offset": "0x28",
                },
            },
            "methods": {
                name: {
                    **row,
                    "nativeDirectCallerCount": caller_counts[name],
                    "nativeDirectCallers": direct_callers[name],
                }
                for name, row in ITEM_SUBMITTER_TARGETS.items()
            },
            "nativeOpenUiBridge": {
                "callers": DIALOG_OPEN_UI_CALLERS,
                "callee": {
                    **DIALOG_OPEN_UI_TARGET,
                    "nativeDirectCallerCount": len(open_ui_callers),
                    "nativeDirectCallers": open_ui_callers,
                },
                "finding": (
                    "DialogManager.OpenUI and the generated XLua wrapper both "
                    "directly call GameAction.DialogOpenUIPanel. The former "
                    "supplies the typed DialogOpenUIAction; the latter proves "
                    "the native method is exposed to Lua UI dispatch."
                ),
            },
            "shippedLuaProducer": lua_producer,
            "fallbackParamFlow": {
                "nativePath": [{
                    **DIALOG_MANAGER_OPEN_UI_EXPECTED_CALLER,
                    "directCallTarget": DIALOG_MANAGER_OPEN_UI_TARGET,
                    "matchingDirectCallCount": len(
                        dialog_manager_open_ui_callers
                    ),
                    "effect": "passes the original DialogOpenUIAction to DialogManager.OpenUI",
                }, {
                    **DIALOG_MANAGER_OPEN_UI_TARGET,
                    "effect": "passes the original action to GameAction.DialogOpenUIPanel",
                }, {
                    "symbol": "GameAction.DialogOpenUIPanel",
                    "token": "0x06008031",
                    "address": "0x1875e0224",
                    "effect": "forwards panelType, param string, and original action object",
                }],
                "shippedLuaConsumer": phase_dialog_flow,
                "finding": (
                    "The installed native fallback and shipped PhaseDialog Lua "
                    "forward and decode the authored parameter string without "
                    "substituting a mission, quest, submission, or objective id."
                ),
            },
            "authoredOpenUiActions": authored_open_ui,
            "authoredMissionObjectives": authored_objectives,
            "sendFinishDialog": {
                "symbol": "Beyond.Gameplay.CinematicSystem.SendFinishDialog",
                "token": "0x06004027",
                "address": "0x1872f0d88",
                "finding": (
                    "DialogManager._SendServer passes the current dialog id and "
                    "m_pendingItemSubmitter. SendFinishDialog is the sole direct "
                    "caller of TryGetSubmitMsg."
                ),
            },
            "installedPatchMatches": submitter_ifix_matches,
            "classification": (
                "active_shipped_xlua_producer_with_exact_submission_context_without_ui_join"
            ),
            "finding": (
                "The shipped SubmitItemCtrl Lua is the missing producer: it "
                "constructs InventoryItemSubmitter and calls "
                "RegisterPendingSubmission through XLua, so zero native direct "
                "callers never implied inactivity. The typed authored census finds "
                "13 SubmitItem OpenUI terminals, but three contain only the stock "
                "placeholder params, ten contain no params, and none exports a "
                "concrete quest id. Separately, three quest objectives resolve "
                "exact submission requirements and two bounded dialog co-gates, "
                "but those dialog ids do not overlap the SubmitItem OpenUI "
                "terminals. The fallback parameter flow supplies no missing id, "
                "so the active bridge adds no exact quest-to-dialog or order edge."
            ),
        },
        "finding": (
            "All 25 current managed identity candidates reachable through generic "
            "or custom typed fields to depth three are reviewed. Productive AirWall, "
            "FocusMode, NpcProxy, SubGame, DomainDepot, and RadioTriggerZone contexts "
            "were already recovered. The remaining joins are global aggregate "
            "managers, previously closed property/task paths, static registries, or "
            "the active XLua pending-submission bridge. That bridge now carries "
            "three exact quest-to-submission requirements, but no quest-to-OpenUI "
            "join or mission-order edge."
        ),
        "boundary": (
            "The exact shipped SubmitItem XLua producer, current fallback OpenUI "
            "parameter pass-through, and authored submission objectives are "
            "included. Dynamic mutation or reflection outside this path, native-"
            "only opaque objects, server-only state, paths deeper than three custom-"
            "type hops, unexported asset kinds, future IFix, and future builds "
            "remain outside the bound."
        ),
        "classification": "all_nested_managed_identity_carriers_reviewed",
        "storyBindingsAdded": 0,
        "missionOrderEdgesAdded": 0,
        "validationErrors": errors,
        "valid": not errors,
    }


def render_markdown(report: dict[str, Any]) -> str:
    census = report["census"]
    closure = report["pendingItemSubmitterClosure"]
    lua_producer = closure["shippedLuaProducer"]
    fallback = closure["fallbackParamFlow"]
    phase_dialog = fallback["shippedLuaConsumer"]
    authored = closure["authoredOpenUiActions"]
    objectives = closure["authoredMissionObjectives"]
    lines = [
        "# Nested managed identity carrier census",
        "",
        f"- Valid: `{report['valid']}`",
        f"- Metadata type records: `{census['metadataTypeRecords']}`",
        f"- Runtime type entries: `{report['source']['runtimeTypeCount']}`",
        f"- Candidate types: `{census['candidateTypes']}`",
        f"- Direct exact candidates: `{census['directExactCandidateTypes']}`",
        f"- Nested-dependent candidates: `{census['nestedDependentCandidateTypes']}`",
        f"- Unreviewed candidates: `{census['unreviewedCandidateTypes']}`",
        f"- Story bindings added: `{report['storyBindingsAdded']}`",
        f"- Mission-order edges added: `{report['missionOrderEdgesAdded']}`",
        "",
        "## Pending item submitter closure",
        "",
        closure["finding"],
        "",
        "### Shipped XLua producer",
        "",
        lua_producer["finding"],
        "",
        f"- Logical path: `{lua_producer['source']['logicalPath']}`",
        f"- SHA-256: `{lua_producer['source']['sha256']}`",
        "- Constructor/registration calls: "
        f"`{lua_producer['constructorAndRegistrationCalls']}`",
        "- Ordered constructor argument matches: "
        f"`{lua_producer['orderedConstructorArgumentMatches']}`",
        "",
        "### Fallback OpenUI parameter flow",
        "",
        fallback["finding"],
        "",
        f"- PhaseDialog path: `{phase_dialog['source']['logicalPath']}`",
        f"- PhaseDialog SHA-256: `{phase_dialog['source']['sha256']}`",
        "- Verified native path: "
        + " -> ".join(
            f"`{row['symbol']}`" for row in fallback["nativePath"]
        ),
        "",
        "### Typed authored OpenUI terminals",
        "",
        authored["finding"],
        "",
        f"- Typed terminal actions: `{authored['typedTerminalActions']}`",
        f"- SubmitItem panel actions: `{authored['submitItemActions']}`",
        "- Parameterized / placeholder / concrete quest-id actions: "
        f"`{authored['parameterizedSubmitItemActions']}` / "
        f"`{authored['placeholderSubmitItemActions']}` / "
        f"`{authored['concreteQuestIdActions']}`",
        "",
        "### Authored mission submission objectives",
        "",
        objectives["finding"],
        "",
        f"- Conditions / quests / missions: `{objectives['conditionCount']}` / "
        f"`{objectives['questCount']}` / `{objectives['missionCount']}`",
        f"- Table-defined requirements: `{objectives['tableDefinedCount']}`",
        f"- Same-AND dialog co-gates: `{objectives['dialogCoGateCount']}`",
        "- Co-gate overlap with SubmitItem OpenUI terminals: "
        f"`{objectives['dialogCoGateOpenUiOverlap']}`",
        "",
        "| Mission | Quest | Condition | Submission | Requirement | Dialog co-gate |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in objectives["rows"]:
        requirements = " or ".join(
            " + ".join(
                f"{item['itemId']} x{item['count']}"
                for item in group
            )
            for group in row["requirements"]
        )
        co_gates = ", ".join(
            f"{gate['dialogId']} finish {gate['finishId']}"
            for gate in row["dialogCoGates"]
        )
        lines.append(
            f"| `{md_escape(row['missionId'])}` | "
            f"`{md_escape(row['questId'])}` | "
            f"`{md_escape(row['conditionId'])}` | "
            f"`{md_escape(str(row['submissionId']))}` | "
            f"{md_escape(requirements)} | {md_escape(co_gates or '-')} |"
        )
    lines.extend([
        "",
        "### Native fallback path",
        "",
        "| Method | Token | Address | Native direct callers |",
        "| --- | --- | --- | ---: |",
    ])
    for name, row in closure["methods"].items():
        lines.append(
            f"| `{md_escape(name)}` | `{row['token']}` | `{row['address']}` | "
            f"{row['nativeDirectCallerCount']} |"
        )
    lines.extend([
        "",
        "## Candidate classifications",
        "",
        "| Type | Direct classes | Minimum depth M/L/S | Status |",
        "| --- | --- | --- | --- |",
    ])
    for row in report["candidates"]:
        depth = row["minimumDepth"]
        depths = "/".join(
            "-" if depth[key] is None else str(depth[key])
            for key in ("mission_or_quest", "level_script", "story")
        )
        lines.append(
            f"| `{md_escape(row['type'])}` | "
            f"`{md_escape(', '.join(row['directClasses']))}` | `{depths}` | "
            f"`{md_escape(row['status'])}` |"
        )
    lines.extend([
        "",
        "## Finding",
        "",
        report["finding"],
        "",
        "## Boundary",
        "",
        report["boundary"],
        "",
    ])
    if report["validationErrors"]:
        lines.extend([
            "## Validation errors",
            "",
            *[f"- {error}" for error in report["validationErrors"]],
            "",
        ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--ifix-audit", type=Path, default=DEFAULT_IFIX_AUDIT)
    parser.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
    parser.add_argument(
        "--animestudio-cli",
        type=Path,
        default=DEFAULT_ANIMESTUDIO_CLI,
    )
    parser.add_argument(
        "--lua-source",
        type=Path,
        help=(
            "Optional plaintext SubmitItemCtrl.lua override. By default the "
            "single file is target-dumped from the installed VFS."
        ),
    )
    parser.add_argument(
        "--phase-dialog-lua-source",
        type=Path,
        help=(
            "Optional plaintext PhaseDialog.lua override. By default the single "
            "file is target-dumped from the installed VFS."
        ),
    )
    parser.add_argument(
        "--mission-root",
        type=Path,
        default=DEFAULT_MISSION_RUNTIME_ROOT,
    )
    parser.add_argument(
        "--submit-item-table",
        type=Path,
        default=DEFAULT_SUBMIT_ITEM_TABLE,
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    report = build_report(
        game_assembly=args.gameassembly,
        metadata_path=args.metadata,
        ifix_audit_path=args.ifix_audit,
        game_root=args.game_root,
        animestudio_cli=args.animestudio_cli,
        lua_source=args.lua_source,
        phase_dialog_lua_source=args.phase_dialog_lua_source,
        mission_root=args.mission_root,
        submit_item_table_path=args.submit_item_table,
    )
    write_report_json(args.out, report)
    write_text_if_changed(args.markdown, render_markdown(report))
    print(
        "nested managed identity carrier census: "
        f"{report['census']['candidateTypes']} candidates, "
        f"{report['census']['nestedDependentCandidateTypes']} nested-dependent, "
        f"{report['census']['unreviewedCandidateTypes']} unreviewed, "
        f"valid={report['valid']}"
    )
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Dialog, radio, SNS, NPC-proxy, and non-mission content evidence."""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from common import (  # noqa: E402
    combined_non_mission_content_keys,
    md_escape,
    non_mission_content_keys,
    read_json,
    resolve_installed_native_inputs,
    safe_key,
    sha256_file,
    write_report_json,
    write_text_if_changed,
)
from story_builder.source_story_partial_order import (  # noqa: E402
    build_report as build_partial_order_report,
    load_mission_payload_with_variants,
)
from .contracts import (  # noqa: E402
    BUCKET_ORDER,
    FRONTIER_ORDER,
    LEVELDATA_INTERACTIVE_HORN_MAPPING_ID,
    LEVELDATA_INTERACTIVE_HORN_NATIVE_MAPPING_ID,
    LEVELDATA_INTERACTIVE_HORN_TEMPLATE_SHA256,
    LEVELDATA_INTERACTIVE_NARRATIVE_MAPPING_ID,
    LEVELSCRIPT_INTERACTIVE_NARRATIVE_MAPPING_ID,
    SCHEMA,
    SCORE_WEIGHTS,
    STORY_BINDING_COVERAGE_SCHEMA_VERSION,
    priority_bucket,
    target_set_sha256,
)
from story_builder.animestudio_story_objects import (
    CARRIER_REPORT_PATH,
    HIERARCHY_REPORT_PATH,
    REVERSE_REPORT_PATH,
)
from story_builder.level_bindings import (  # noqa: E402
    LEVELSCRIPT_NATIVE_ACTION_MAPPING_ID,
    LEVELSCRIPT_NATIVE_EXACT_CONTROL_PATH_STATUSES,
    _load_levelscript_binding_data,
    _levelscript_native_control_paths_to_record,
    build_levelscript_unhosted_reading_popup_receiver_index,
    decode_levelscript_native_action_topology,
    parse_leveldata_levelscript_brief_dictionary,
)
from story_builder.levelscript_binary import (  # noqa: E402
    decode_levelscript_binary_summary,
    decode_levelscript_record_payload,
    decode_levelscript_task_conditions,
    extract_levelscript_uid_records,
    levelscript_action_map_membership,
    levelscript_record_semantic_key,
)
from story_builder.anime_assets import (  # noqa: E402
    recover_dialog_tree_definition_evidence,
    recover_dialog_tree_prime_reachable_carriers_for_parent,
)
from story_builder.mission_recovery import natural_key  # noqa: E402
from story_builder.mission_assets import (  # noqa: E402
    mission_runtime_source_summary,
    select_complete_mission_runtime_root,
)


from .data import (
    CORE_STORY_NODE_KINDS,
    KNOWN_NON_PLAYBACK_ACTIONS,
    KNOWN_NON_PLAYBACK_MAPPING_ID,
    NPC_PROXY_DIALOG_SELECTION_MAPPING_ID,
    NON_OWNING_DIAGNOSTIC_QUEST_ATTACH_SOURCES,
    NPC_PROXY_DIALOG_SELECTION_GAMEASSEMBLY_SHA256,
    NPC_PROXY_TRACKING_INFO_TYPE,
    NPC_PROXY_TRACKING_INFO_FIELDS,
    DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID,
    DIALOG_TREE_TRUNK_GROUP_MAPPING_ID,
    DIALOG_TREE_TRUNK_NATIVE_CONSUMERS,
    OFFLINE_EXHAUSTION_MAPPING_ID,
    OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
    OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS,
    OFFLINE_EXHAUSTION_MISSION_BRANCH_CONTEXTS,
    OFFLINE_EXHAUSTION_MISSION_RELATED_ORIGINAL_DATA,
    OFFLINE_EXHAUSTION_MISSION_LINEAR_CONTEXTS,
    OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS,
    OFFLINE_EXHAUSTION_LEVELDATA_DIALOG_BRANCH_CONTEXTS,
    OFFLINE_EXHAUSTION_EMPTY_LEVELSCRIPT_CONTEXTS,
    OFFLINE_EXHAUSTION_LEVELSCRIPT_TASK_CONSUMERS,
    OFFLINE_EXHAUSTION_REVERSE_PPTR_MAPPING_ID,
    OFFLINE_EXHAUSTION_METADATA_SHA256,
    OFFLINE_EXHAUSTION_RADIO_TABLE_SHA256,
    OFFLINE_EXHAUSTION_AUDIO_DIALOG_SHA256,
    OFFLINE_EXHAUSTION_NUM_ID_STR_TABLE_SHA256,
    OFFLINE_EXHAUSTION_STR_ID_NUM_TABLE_SHA256,
    OFFLINE_EXHAUSTION_TEXT_TABLE_SHA256,
    OFFLINE_EXHAUSTION_DIALOG_TEXT_TABLE_SHA256,
    OFFLINE_EXHAUSTION_DIALOG_OPTION_TABLE_SHA256,
    OFFLINE_EXHAUSTION_DIALOG_SUMMARY_MAP_TABLE_SHA256,
    OFFLINE_EXHAUSTION_DIALOG_SUMMARY_TABLE_SHA256,
    OFFLINE_EXHAUSTION_READING_POPUP_TABLE_SHA256,
    OFFLINE_EXHAUSTION_RICH_CONTENT_TABLE_SHA256,
    OFFLINE_EXHAUSTION_PRTS_ALL_ITEM_TABLE_SHA256,
    OFFLINE_EXHAUSTION_PRTS_RECORD_TABLE_SHA256,
    OFFLINE_EXHAUSTION_PRTS_READING_TABLE_SHA256,
    OFFLINE_EXHAUSTION_SNS_DIALOG_TABLE_SHA256,
    OFFLINE_EXHAUSTION_SNS_OPTION_TABLE_SHA256,
    OFFLINE_EXHAUSTION_NPC_PROXY_EX_TABLE_SHA256,
    OFFLINE_EXHAUSTION_NPC_PROXY_TABLE_SHA256,
    OFFLINE_EXHAUSTION_SNS_CHAT_TABLE_SHA256,
    OFFLINE_EXHAUSTION_DIALOG_ID_SOURCE_SHA256,
    OFFLINE_EXHAUSTION_DIALOG_ID_INDEX_SHA256,
    OFFLINE_EXHAUSTION_TIMELINE_LINE_ORDERS_SHA256,
    QUEST_ATTACHMENT_DIAGNOSTIC_MAPPING_ID,
    QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS,
    QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_HASHES,
    QUEST_ATTACHMENT_DIAGNOSTIC_DECLARATIONS,
    OFFLINE_EXHAUSTION_E11M4_CUTSCENE,
    OFFLINE_EXHAUSTION_E11M1_TEXT_ONLY_CUTSCENE,
    OFFLINE_EXHAUSTION_TEXT_ONLY_CUTSCENES,
    OFFLINE_EXHAUSTION_SNS_DEFINITIONS,
    OFFLINE_EXHAUSTION_E11M1_PRESENTATION_CUTSCENES,
    OFFLINE_EXHAUSTION_CUTSCENES_BY_MISSION,
    OFFLINE_EXHAUSTION_REVERSE_HOST_COUNTS,
    OFFLINE_EXHAUSTION_CUTSCENE_DEFINITIONS,
    OFFLINE_EXHAUSTION_GAMEOBJECT_ROW_COUNTS,
    OFFLINE_EXHAUSTION_ROOT_PLAYBACK_ALIASES,
    OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS,
    OFFLINE_EXHAUSTION_POSITIVE_DIALOG_KEYS,
    OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS,
    OFFLINE_EXHAUSTION_DIALOG_ROW_FIELDS,
    OFFLINE_EXHAUSTION_E11M4_RADIOS,
    OFFLINE_EXHAUSTION_E10M4_RADIOS,
    OFFLINE_EXHAUSTION_E11M1_RADIOS,
    OFFLINE_EXHAUSTION_E11M6_RADIOS,
    OFFLINE_EXHAUSTION_E11M2_RADIOS,
    OFFLINE_EXHAUSTION_E11M5_RADIOS,
    OFFLINE_EXHAUSTION_E9M2_RADIOS,
    OFFLINE_EXHAUSTION_E9M3_RADIOS,
    OFFLINE_EXHAUSTION_E9M4_RADIOS,
    OFFLINE_EXHAUSTION_E6M3_RADIOS,
    OFFLINE_EXHAUSTION_E1M2_RADIOS,
    OFFLINE_EXHAUSTION_E1M3_RADIOS,
    OFFLINE_EXHAUSTION_E1M4_RADIOS,
    OFFLINE_EXHAUSTION_E1M5_RADIOS,
    OFFLINE_EXHAUSTION_E1M6_RADIOS,
    OFFLINE_EXHAUSTION_E1M10_RADIOS,
    OFFLINE_EXHAUSTION_E7M2_RADIOS,
    OFFLINE_EXHAUSTION_E6M4_RADIOS,
    OFFLINE_EXHAUSTION_E6M5_RADIOS,
    OFFLINE_EXHAUSTION_E7M3_RADIOS,
    OFFLINE_EXHAUSTION_E11M3_RADIOS,
    OFFLINE_EXHAUSTION_E11M8_RADIOS,
    OFFLINE_EXHAUSTION_E3M2_RADIOS,
    OFFLINE_EXHAUSTION_E3M1_RADIOS,
    OFFLINE_EXHAUSTION_E3M3_RADIOS,
    OFFLINE_EXHAUSTION_E0M0_RADIOS,
    OFFLINE_EXHAUSTION_E2M4_RADIOS,
    OFFLINE_EXHAUSTION_E2M5_RADIOS,
    OFFLINE_EXHAUSTION_E2M6_RADIOS,
    OFFLINE_EXHAUSTION_E2M7_RADIOS,
    OFFLINE_EXHAUSTION_E2M2_RADIOS,
    OFFLINE_EXHAUSTION_E2M3_RADIOS,
    OFFLINE_EXHAUSTION_E5M2_RADIOS,
    OFFLINE_EXHAUSTION_E5M3_RADIOS,
    OFFLINE_EXHAUSTION_E5M4_RADIOS,
    OFFLINE_EXHAUSTION_E5M1_RADIOS,
    OFFLINE_EXHAUSTION_E5M5_RADIOS,
    OFFLINE_EXHAUSTION_E6M1_RADIOS,
    OFFLINE_EXHAUSTION_E6M2_RADIOS,
    OFFLINE_EXHAUSTION_E3M4_RADIOS,
    OFFLINE_EXHAUSTION_E4M1_RADIOS,
    OFFLINE_EXHAUSTION_E4M1D5_RADIOS,
    OFFLINE_EXHAUSTION_E7M4_RADIOS,
    OFFLINE_EXHAUSTION_E8M2_RADIOS,
    OFFLINE_EXHAUSTION_E8M1_RADIOS,
    OFFLINE_EXHAUSTION_E8M3_RADIOS,
    OFFLINE_EXHAUSTION_E8M5_RADIOS,
    OFFLINE_EXHAUSTION_E10M1_RADIOS,
    OFFLINE_EXHAUSTION_E10M2_RADIOS,
    OFFLINE_EXHAUSTION_A1M6D1_RADIOS,
    OFFLINE_EXHAUSTION_A1M6D2_RADIOS,
    OFFLINE_EXHAUSTION_A1M6D3_RADIOS,
    OFFLINE_EXHAUSTION_A1M8D3_RADIOS,
    OFFLINE_EXHAUSTION_GM02M2_RADIOS,
    OFFLINE_EXHAUSTION_GM02M3_RADIOS,
    OFFLINE_EXHAUSTION_GM02M14_RADIOS,
    OFFLINE_EXHAUSTION_GM02M15_RADIOS,
    OFFLINE_EXHAUSTION_GM02M21_RADIOS,
    OFFLINE_EXHAUSTION_GM02M13_RADIOS,
    OFFLINE_EXHAUSTION_GM02M17_RADIOS,
    OFFLINE_EXHAUSTION_GM01M4_RADIOS,
    OFFLINE_EXHAUSTION_GM01M6_RADIOS,
    OFFLINE_EXHAUSTION_GM01M7_RADIOS,
    OFFLINE_EXHAUSTION_GM01M16_RADIOS,
    OFFLINE_EXHAUSTION_GM01M20_RADIOS,
    OFFLINE_EXHAUSTION_GM01M22_RADIOS,
    OFFLINE_EXHAUSTION_GM01M24_RADIOS,
    OFFLINE_EXHAUSTION_GM01M25_RADIOS,
    OFFLINE_EXHAUSTION_GM01M26_RADIOS,
    OFFLINE_EXHAUSTION_GM01M27_RADIOS,
    OFFLINE_EXHAUSTION_GM01M17_RADIOS,
    OFFLINE_EXHAUSTION_GM01M3_RADIOS,
    OFFLINE_EXHAUSTION_GM01M5_RADIOS,
    OFFLINE_EXHAUSTION_GM02M1_RADIOS,
    OFFLINE_EXHAUSTION_GM02M20_RADIOS,
    OFFLINE_EXHAUSTION_GM02M23_RADIOS,
    OFFLINE_EXHAUSTION_RADIOS_BY_MISSION,
    OFFLINE_EXHAUSTION_RADIO_CONTEXTS,
    OFFLINE_EXHAUSTION_RADIO_AUDIO_VARIANTS,
    OFFLINE_EXHAUSTION_RADIO_MISSING_AUDIO_IDS,
    OFFLINE_EXHAUSTION_RADIO_ROW_FIELDS,
    OFFLINE_EXHAUSTION_RADIO_LINE_FIELDS,
    READING_POPUP_ROW_FIELDS,
    RICH_CONTENT_ROW_FIELDS,
    RICH_CONTENT_ITEM_FIELDS,
    LOCALIZED_TEXT_FIELDS,
    DIALOG_OPTION_ROW_FIELDS,
)

from .providers import (
    DIRECT_OBJECTIVE_STORY_CONDITION_FIELDS,
    _build_mission_npc_proxy_tracking_index,
    _configured_game_assembly_path,
    _diagnostic_quest_attachments,
    _exact_levelscript_property_story_consumer,
    _flow,
    _flow_story_connections,
    _generic_mission_npc_proxy_tracking_contexts,
    _generic_registered_dialog_tree_definition_facts,
    _merge_exact_interaction_trigger_with_native_playback,
    _repo_source_path,
    _sha256_file,
    _strict_quest_attachments,
    _string_list,
    _timeline,
)

def _localized_text_id(value: Any) -> int | None:
    """Return an exact empty localized-text id, excluding bool-as-int."""
    if (
        not isinstance(value, dict)
        or set(value) != LOCALIZED_TEXT_FIELDS
        or not isinstance(value.get("id"), int)
        or isinstance(value.get("id"), bool)
        or value.get("text") != ""
    ):
        return None
    return value["id"]

def _generic_reading_popup_definition_facts(
    story_key: str,
    popup_rows: Any,
    rich_row: Any,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Validate a ReadingPopUp/RichContent definition without key lists."""
    if not isinstance(popup_rows, dict) or not popup_rows:
        return None, {
            "validator": "genericReadingPopupNegativeConsumer",
            "gate": "exactReadingPopupCarrierSet",
            "storyKey": story_key,
            "expected": {
                "nonemptyRows": True,
                "contentId": story_key,
                "fields": sorted(READING_POPUP_ROW_FIELDS),
            },
            "actual": {
                "type": type(popup_rows).__name__,
                "rowIds": sorted(popup_rows) if isinstance(popup_rows, dict) else [],
            },
        }
    popup_facts: list[dict[str, Any]] = []
    for row_id, row in sorted(popup_rows.items(), key=lambda item: natural_key(item[0])):
        title_id = _localized_text_id(row.get("title")) if isinstance(row, dict) else None
        valid = (
            isinstance(row, dict)
            and set(row) == READING_POPUP_ROW_FIELDS
            and safe_key(row_id)
            and safe_key(row.get("id")) == row_id
            and safe_key(row.get("contentId")) == story_key
            and isinstance(row.get("bgType"), int)
            and not isinstance(row.get("bgType"), bool)
            and isinstance(row.get("iconType"), int)
            and not isinstance(row.get("iconType"), bool)
            and row.get("overrideRadioId") == ""
            and title_id is not None
        )
        if not valid:
            return None, {
                "validator": "genericReadingPopupNegativeConsumer",
                "gate": "exactReadingPopupCarrierShape",
                "storyKey": story_key,
                "expected": {
                    "rowId": row_id,
                    "contentId": story_key,
                    "fields": sorted(READING_POPUP_ROW_FIELDS),
                    "integerBgAndIconTypes": True,
                    "emptyOverrideRadioId": True,
                    "emptyLocalizedTitle": True,
                },
                "actual": {
                    "type": type(row).__name__,
                    "fields": sorted(row) if isinstance(row, dict) else [],
                    "row": row,
                },
            }
        popup_facts.append({
            "rowId": row_id,
            "bgType": row["bgType"],
            "iconType": row["iconType"],
            "titleId": title_id,
        })

    title_id = _localized_text_id(
        rich_row.get("title") if isinstance(rich_row, dict) else None
    )
    content_list = rich_row.get("contentList") if isinstance(rich_row, dict) else None
    content_text_ids: list[int] = []
    rich_valid = (
        isinstance(rich_row, dict)
        and set(rich_row) == RICH_CONTENT_ROW_FIELDS
        and isinstance(content_list, list)
        and bool(content_list)
        and title_id is not None
    )
    if rich_valid:
        for item in content_list:
            content = item.get("content") if isinstance(item, dict) else None
            content_id = _localized_text_id(content)
            if (
                not isinstance(item, dict)
                or set(item) != RICH_CONTENT_ITEM_FIELDS
                or content_id is None
            ):
                rich_valid = False
                break
            content_text_ids.append(content_id)
    if not rich_valid:
        return None, {
            "validator": "genericReadingPopupNegativeConsumer",
            "gate": "exactRichContentDefinitionShape",
            "storyKey": story_key,
            "expected": {
                "fields": sorted(RICH_CONTENT_ROW_FIELDS),
                "nonemptyContentList": True,
                "itemFields": sorted(RICH_CONTENT_ITEM_FIELDS),
                "emptyLocalizedTextRecords": True,
            },
            "actual": {
                "type": type(rich_row).__name__,
                "fields": sorted(rich_row) if isinstance(rich_row, dict) else [],
                "row": rich_row,
            },
        }
    return {
        "readingPopupRows": popup_facts,
        "readingPopupRowIds": [row["rowId"] for row in popup_facts],
        "richContentTitleId": title_id,
        "contentTextIds": content_text_ids,
    }, None

def _generic_unregistered_dialog_definition_facts(
    story_key: str,
    dialog_text_table: Any,
    dialog_option_table: Any,
    audio_stems: set[str],
    *,
    definition_root_key: str | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Validate one exact table-only dialog root without declarations."""
    definition_root_key = definition_root_key or story_key
    if not isinstance(dialog_text_table, dict) or not isinstance(
        dialog_option_table,
        dict,
    ):
        return None, {
            "validator": "genericUnregisteredDialogNegativeConsumer",
            "gate": "sourceTableShape",
            "storyKey": story_key,
            "expected": {
                "dialogTextTable": "object",
                "dialogOptionTable": "object",
            },
            "actual": {
                "dialogTextTable": type(dialog_text_table).__name__,
                "dialogOptionTable": type(dialog_option_table).__name__,
            },
        }
    # The authored suffix width is not a schema boundary. Most dialogs use
    # three digits, while current BlackBox rows also use two. The anchored
    # root and all-digit terminal component preserve the exact group boundary
    # without encoding either content family in recovery logic.
    line_pattern = re.compile(
        rf"^{re.escape(definition_root_key)}_(\d+)$"
    )
    line_rows = sorted(
        (
            (line_id, match, row)
            for line_id, row in dialog_text_table.items()
            if (match := line_pattern.fullmatch(line_id)) is not None
        ),
        key=lambda item: int(item[1].group(1)),
    )
    if not line_rows:
        return None, {
            "validator": "genericUnregisteredDialogNegativeConsumer",
            "gate": "exactDialogTextRoot",
            "storyKey": story_key,
            "expected": {
                "lineIdPattern": f"{definition_root_key}_<digits>",
                "nonemptyLines": True,
            },
            "actual": {"lineIds": []},
        }
    line_ids: list[str] = []
    line_numbers: list[int] = []
    audio_ids: list[str] = []
    for line_id, match, row in line_rows:
        audio_id = safe_key(row.get("audioOverride")) if isinstance(row, dict) else ""
        if (
            not isinstance(row, dict)
            or set(row) != OFFLINE_EXHAUSTION_DIALOG_ROW_FIELDS
            or not audio_id
        ):
            return None, {
                "validator": "genericUnregisteredDialogNegativeConsumer",
                "gate": "exactDialogTextLineShape",
                "storyKey": story_key,
                "expected": {
                    "fields": sorted(OFFLINE_EXHAUSTION_DIALOG_ROW_FIELDS),
                    "nonemptyAudioOverride": True,
                },
                "actual": {
                    "lineId": line_id,
                    "type": type(row).__name__,
                    "fields": sorted(row) if isinstance(row, dict) else [],
                    "audioOverride": audio_id,
                },
            }
        line_ids.append(line_id)
        line_numbers.append(int(match.group(1)))
        audio_ids.append(audio_id)
    if len(set(line_numbers)) != len(line_numbers):
        return None, {
            "validator": "genericUnregisteredDialogNegativeConsumer",
            "gate": "uniqueDialogLineIdentity",
            "storyKey": story_key,
            "expected": {"uniqueLineNumbers": len(line_numbers)},
            "actual": {"uniqueLineNumbers": len(set(line_numbers))},
        }

    option_pattern = re.compile(
        rf"^option_{re.escape(definition_root_key)}_([^_]+)_(\d+)$"
    )
    option_rows = sorted(
        (
            (option_id, match, row)
            for option_id, row in dialog_option_table.items()
            if (match := option_pattern.fullmatch(option_id)) is not None
        ),
        key=lambda item: (
            natural_key(item[1].group(1)),
            int(item[1].group(2)),
        ),
    )
    option_ids: list[str] = []
    options_by_group: dict[str, list[str]] = defaultdict(list)
    for option_id, match, row in option_rows:
        option_text_id = _localized_text_id(
            row.get("optionText") if isinstance(row, dict) else None
        )
        if (
            not isinstance(row, dict)
            or set(row) != DIALOG_OPTION_ROW_FIELDS
            or not isinstance(row.get("iconType"), str)
            or not row.get("iconType")
            or option_text_id is None
        ):
            return None, {
                "validator": "genericUnregisteredDialogNegativeConsumer",
                "gate": "exactDialogOptionShape",
                "storyKey": story_key,
                "expected": {
                    "fields": sorted(DIALOG_OPTION_ROW_FIELDS),
                    "nonemptyStringIconType": True,
                    "emptyLocalizedOptionText": True,
                },
                "actual": {
                    "optionId": option_id,
                    "type": type(row).__name__,
                    "row": row,
                },
            }
        option_ids.append(option_id)
        options_by_group[match.group(1)].append(option_id)

    audio_membership = {
        audio_id: sorted(
            stem
            for stem in audio_stems
            if stem == audio_id or stem.startswith(f"{audio_id}_")
        )
        for audio_id in sorted(set(audio_ids), key=natural_key)
    }
    present_audio_ids = {
        audio_id for audio_id, matches in audio_membership.items() if matches
    }
    return {
        "definitionRootKey": definition_root_key,
        "lineIds": line_ids,
        "lineNumbers": line_numbers,
        "audioIds": sorted(set(audio_ids), key=natural_key),
        "audioMembership": audio_membership,
        "audioMembershipStatus": (
            "all_current_audio_dialog_ids_missing"
            if not present_audio_ids else (
                "all_current_audio_dialog_ids_present"
                if len(present_audio_ids) == len(audio_membership)
                else "partial_current_audio_dialog_missing_ids"
            )
        ),
        "optionIds": option_ids,
        "optionsByGroup": dict(options_by_group),
        "optionRouteStatus": (
            "definitions_present_route_unresolved"
            if option_ids else "no_current_option_definitions"
        ),
    }, None

def _memorypack_contains_exact_string(data: bytes, value: str) -> bool:
    encoded = value.encode("utf-8")
    return (
        len(encoded).to_bytes(4, "little", signed=True) + encoded
    ) in data

def _dialog_parent_level_candidate(
    parent_key: str,
    level_ids: set[str],
) -> tuple[str, str | None]:
    namespace = safe_key(parent_key)
    if namespace.startswith("dlg_"):
        namespace = namespace.removeprefix("dlg_")
    if namespace.startswith("gpl_"):
        namespace = namespace.removeprefix("gpl_")
    candidates = sorted(
        (
            level_id
            for level_id in level_ids
            if namespace == level_id
            or namespace.startswith(f"{level_id}_")
        ),
        key=lambda level_id: (-len(level_id), natural_key(level_id)),
    )
    if not candidates:
        return "", None
    longest = len(candidates[0])
    longest_candidates = [
        level_id for level_id in candidates if len(level_id) == longest
    ]
    if len(longest_candidates) != 1:
        return "", "ambiguousLongestLevelNamespace"
    return longest_candidates[0], None

def _blackbox_subgame_task_topology(
    level_id: str,
    bind_script_id: int,
    subgame_row: dict[str, Any],
    script_path: Path,
    script_task_extra_info_table: Any,
    script_task_extra_info_table_path: Path | None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Decode a complete BlackBox task map without inventing task order.

    The join is generic: SubGame lane IDs, the bound LevelScript task keys,
    and ScriptTaskExtraInfo keys must agree exactly. Unsupported condition
    unions stay visible as a bounded decoder diagnostic and publish no partial
    topology.
    """
    data = script_path.read_bytes()
    diagnostics: list[dict[str, Any]] = []
    decoded = decode_levelscript_task_conditions(
        data,
        bind_script_id,
        diagnostics=diagnostics,
    )
    summary = decode_levelscript_binary_summary(data, bind_script_id)
    task_map = decoded[0] if len(decoded) == 1 else None
    tasks = (
        task_map.get("tasks") or []
        if isinstance(task_map, dict)
        else []
    )
    lane_names = ("mainTasks", "extraTasks", "failTasks")
    lane_by_task: dict[str, str] = {}
    duplicate_lane_ids: list[str] = []
    for lane_name in lane_names:
        lane = lane_name.removesuffix("Tasks")
        for row in subgame_row.get(lane_name) or []:
            task_id = safe_key(row.get("taskId")) if isinstance(row, dict) else ""
            if task_id in lane_by_task:
                duplicate_lane_ids.append(task_id)
            elif task_id:
                lane_by_task[task_id] = lane

    task_ids = [safe_key(row.get("taskKey")) for row in tasks]
    task_id_set = set(task_ids)
    tracked_task_ids = {
        safe_key(row.get("taskKey"))
        for row in tasks
        if row.get("canBeTracked") is True
    }
    table_rows = (
        script_task_extra_info_table.get("dataTable")
        if isinstance(script_task_extra_info_table, dict)
        and isinstance(script_task_extra_info_table.get("dataTable"), dict)
        else script_task_extra_info_table
    )
    level_rows = (
        table_rows.get(level_id)
        if isinstance(table_rows, dict)
        else None
    )
    display_rows = (
        level_rows.get(str(bind_script_id))
        if isinstance(level_rows, dict)
        else None
    )
    display_rows = display_rows if isinstance(display_rows, dict) else {}
    display_task_ids = set(map(safe_key, display_rows))
    declared_task_count = summary.get("taskMapCount")
    if (
        summary.get("taskMapStatus") == "null"
        and not lane_by_task
        and not display_task_ids
        and isinstance(script_task_extra_info_table_path, Path)
        and script_task_extra_info_table_path.is_file()
    ):
        return {
            "schema": "blackBoxSubGameTaskTopology.v1",
            "status": "exact_null_task_map",
            "scriptId": str(bind_script_id),
            "startType": summary.get("startTypeName"),
            "taskMapBoundaryStatus": "exact_memorypack_null",
            "declaredTaskCount": None,
            "decodedTaskCount": 0,
            "registeredLaneTaskCount": 0,
            "trackedTaskCount": 0,
            "internalTaskCount": 0,
            "conditionCount": 0,
            "conditionTypeCounts": {},
            "combineExpressions": [],
            "tasks": [],
            "sourceFiles": [
                _repo_source_path(script_path),
                _repo_source_path(script_task_extra_info_table_path),
            ],
            "sourceSha256": {
                _repo_source_path(script_path): _sha256_file(script_path),
                _repo_source_path(script_task_extra_info_table_path): (
                    _sha256_file(script_task_extra_info_table_path)
                ),
            },
            "branchModel": "no serialized task map or registered task lanes",
            "storyConsumerBoundary": "no task conditions exist",
            "graphEffect": "none",
            "orderEvidence": False,
        }, None
    valid = (
        len(decoded) == 1
        and isinstance(declared_task_count, int)
        and declared_task_count == len(tasks)
        and len(task_ids) == len(task_id_set)
        and not duplicate_lane_ids
        and set(lane_by_task) <= task_id_set
        and display_task_ids == tracked_task_ids
        and isinstance(script_task_extra_info_table_path, Path)
        and script_task_extra_info_table_path.is_file()
    )
    if not valid:
        return {
            "schema": "blackBoxSubGameTaskTopology.v1",
            "status": "unavailable_fail_closed",
            "scriptId": str(bind_script_id),
            "declaredTaskCount": declared_task_count,
            "decodedTaskCount": len(tasks),
            "decoderDiagnostics": diagnostics,
            "orderEvidence": False,
        }, {
            "gate": "exactBlackBoxTaskMapAndDisplayJoin",
            "expected": {
                "decodedMapCount": 1,
                "decodedTaskCount": declared_task_count,
                "uniqueTaskIds": True,
                "registeredLaneTaskIdsSubsetOfDecodedTaskIds": True,
                "scriptTaskExtraInfoIdsEqualTrackedTaskIds": True,
            },
            "actual": {
                "decodedMapCount": len(decoded),
                "decodedTaskCount": len(tasks),
                "decodedTaskIds": task_ids,
                "registeredLaneTaskIds": sorted(lane_by_task, key=natural_key),
                "duplicateLaneTaskIds": sorted(
                    set(duplicate_lane_ids), key=natural_key
                ),
                "trackedTaskIds": sorted(tracked_task_ids, key=natural_key),
                "scriptTaskExtraInfoIds": sorted(
                    display_task_ids, key=natural_key
                ),
                "decoderDiagnostics": diagnostics,
            },
            "sourcePaths": [
                _repo_source_path(script_path),
                (
                    _repo_source_path(script_task_extra_info_table_path)
                    if isinstance(script_task_extra_info_table_path, Path)
                    else ""
                ),
            ],
            "sourceSha256": {
                "boundLevelScript": _sha256_file(script_path),
                "scriptTaskExtraInfoTable": (
                    _sha256_file(script_task_extra_info_table_path)
                    if isinstance(script_task_extra_info_table_path, Path)
                    and script_task_extra_info_table_path.is_file()
                    else ""
                ),
            },
        }

    condition_type_counts: Counter[str] = Counter()
    combine_expressions: list[dict[str, Any]] = []
    output_tasks: list[dict[str, Any]] = []
    for task in tasks:
        task_id = safe_key(task.get("taskKey"))
        conditions = task.get("conditions") or []
        for condition_row in conditions:
            condition = condition_row.get("condition") or {}
            condition_type = safe_key(condition.get("type"))
            if condition_type:
                condition_type_counts[condition_type] += 1
            expression = safe_key(condition.get("conditionEvalString"))
            if expression:
                combine_expressions.append({
                    "taskId": task_id,
                    "conditionKey": condition_row.get("conditionKey"),
                    "expression": expression,
                    "operandBindingStatus": "not_proven_from_serialized_map",
                })
        output_tasks.append({
            "taskId": task_id,
            "lane": lane_by_task.get(task_id, "internal"),
            "registeredInSubGame": task_id in lane_by_task,
            "canBeTracked": task.get("canBeTracked") is True,
            "needManualCheck": task.get("needManualCheck") is True,
            "taskType": task.get("taskType"),
            "conditionCount": len(conditions),
            "conditions": conditions,
            "displayInfo": display_rows.get(task_id),
        })
    return {
        "schema": "blackBoxSubGameTaskTopology.v1",
        "status": "exact_complete_task_map",
        "scriptId": str(bind_script_id),
        "startType": task_map.get("startType"),
        "taskMapBoundaryStatus": task_map.get("taskMapBoundaryStatus"),
        "declaredTaskCount": declared_task_count,
        "decodedTaskCount": len(tasks),
        "registeredLaneTaskCount": len(lane_by_task),
        "trackedTaskCount": len(tracked_task_ids),
        "internalTaskCount": sum(
            1 for task_id in task_ids if task_id not in lane_by_task
        ),
        "conditionCount": sum(condition_type_counts.values()),
        "conditionTypeCounts": dict(sorted(condition_type_counts.items())),
        "combineExpressions": combine_expressions,
        "tasks": output_tasks,
        "sourceFiles": [
            _repo_source_path(script_path),
            _repo_source_path(script_task_extra_info_table_path),
        ],
        "sourceSha256": {
            _repo_source_path(script_path): _sha256_file(script_path),
            _repo_source_path(script_task_extra_info_table_path): (
                _sha256_file(script_task_extra_info_table_path)
            ),
        },
        "branchModel": (
            "main/extra/fail are exact authored lane memberships; internal "
            "tasks and CombineCondition formulas are exact definitions, but "
            "the task dictionary serializes no successor edges or lane "
            "selection/exclusivity"
        ),
        "storyConsumerBoundary": (
            "condition operands describe task completion; absent exact dialog "
            "IDs cannot place table-only DialogText rows or order Story files"
        ),
        "graphEffect": "none",
        "orderEvidence": False,
    }, None

def _blackbox_subgame_action_topology(
    level_id: str,
    bind_script_id: int,
    script_path: Path,
    native_playback_index: dict[str, list[dict[str, Any]]] | None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Attach exact typed Story targets to a complete LevelScript graph.

    The graph decoder is object-agnostic. This BlackBox join adds only exact
    same-file native playback occurrences and requires every current action
    type to be named by the installed GameAssembly formatter mapping.
    """
    data = script_path.read_bytes()
    topology, diagnostic = decode_levelscript_native_action_topology(data)
    source_file = _repo_source_path(script_path)
    topology.update({
        "scriptId": str(bind_script_id),
        "levelId": level_id,
        "sourceFiles": [source_file],
        "sourceSha256": {source_file: _sha256_file(script_path)},
    })
    if diagnostic is not None:
        return topology, {
            **diagnostic,
            "levelId": level_id,
            "scriptId": str(bind_script_id),
            "sourcePath": source_file,
            "sourceSha256": _sha256_file(script_path),
        }

    unmapped = topology.get("unmappedActionTypeCounts") or {}
    if unmapped:
        failure = {
            "validator": "blackBoxSubGameActionTopology",
            "gate": "completeCurrentBuildActionTypeMapping",
            "levelId": level_id,
            "scriptId": str(bind_script_id),
            "sourcePath": source_file,
            "expected": {"unmappedActionTypeCounts": {}},
            "actual": {"unmappedActionTypeCounts": unmapped},
            "sourceSha256": _sha256_file(script_path),
            "nativeMappingId": LEVELSCRIPT_NATIVE_ACTION_MAPPING_ID,
        }
        return {
            **topology,
            "status": "unavailable_fail_closed",
            "validatorDiagnostic": failure,
            "actionControlFlowEvidence": False,
        }, failure

    occurrences: list[dict[str, Any]] = []
    for story_key, rows in (
        native_playback_index.items()
        if isinstance(native_playback_index, dict)
        else []
    ):
        for row in rows or []:
            if (
                isinstance(row, dict)
                and safe_key(row.get("levelId")) == level_id
                and safe_key(row.get("scriptId")) == str(bind_script_id)
                and safe_key(row.get("sourceFile")) == source_file
                and safe_key(row.get("actionName"))
                and safe_key(row.get("recordClass"))
                and safe_key(row.get("nativeMappingId"))
                == LEVELSCRIPT_NATIVE_ACTION_MAPPING_ID
                and isinstance(row.get("localId"), int)
            ):
                occurrences.append({
                    "storyKey": safe_key(story_key),
                    "actionLocalId": row.get("localId"),
                    "actionName": safe_key(row.get("actionName")),
                    "recordClass": safe_key(row.get("recordClass")),
                    "recordOffset": row.get("recordOffset"),
                    "nativeEventOwnerStatus": safe_key(
                        row.get("nativeEventOwnerStatus")
                    ),
                })
    occurrences.sort(key=lambda row: (
        row["actionLocalId"],
        natural_key(row["storyKey"]),
    ))
    occurrence_signatures = [
        (row["storyKey"], row["actionLocalId"])
        for row in occurrences
    ]
    actions_by_id = {
        row.get("localId"): row
        for row in topology.get("actions") or []
        if isinstance(row, dict) and isinstance(row.get("localId"), int)
    }
    mismatches = [
        row
        for row in occurrences
        if row["actionLocalId"] not in actions_by_id
        or row["actionName"]
        != safe_key(actions_by_id[row["actionLocalId"]].get("actionName"))
    ]
    if len(occurrence_signatures) != len(set(occurrence_signatures)) or mismatches:
        failure = {
            "validator": "blackBoxSubGameActionTopology",
            "gate": "exactNativeStoryTargetJoin",
            "levelId": level_id,
            "scriptId": str(bind_script_id),
            "sourcePath": source_file,
            "expected": {
                "uniqueStoryKeyActionLocalIdPairs": True,
                "everyStoryTargetActionExistsWithMatchingType": True,
            },
            "actual": {
                "storyTargetCount": len(occurrences),
                "uniqueStoryTargetCount": len(set(occurrence_signatures)),
                "mismatches": mismatches[:16],
            },
            "sourceSha256": _sha256_file(script_path),
            "nativeMappingId": LEVELSCRIPT_NATIVE_ACTION_MAPPING_ID,
        }
        return {
            **topology,
            "status": "unavailable_fail_closed",
            "validatorDiagnostic": failure,
            "actionControlFlowEvidence": False,
        }, failure

    targets_by_action: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for occurrence in occurrences:
        targets_by_action[occurrence["actionLocalId"]].append({
            key: value
            for key, value in occurrence.items()
            if key != "actionLocalId" and value not in (None, "")
        })
    for local_id, targets in targets_by_action.items():
        actions_by_id[local_id]["storyTargets"] = targets
    topology.update({
        "storyTargetCount": len(occurrences),
        "storyTargetActionCount": len(targets_by_action),
        "storyTargetKeys": sorted(
            {row["storyKey"] for row in occurrences},
            key=natural_key,
        ),
        "nativeStoryPlaybackBoundary": (
            "only typed same-script action targets are attached; tagged strings "
            "in other action types and table-only DialogText rows remain unrelated"
        ),
    })
    return topology, None

def _generic_parent_dialog_level_context_facts(
    parent_dialog_trees: list[dict[str, Any]],
    level_basic_info_table: Any,
    dungeon_table: Any,
    *,
    level_config_root: Path | None,
    level_data_root: Path | None,
    text_asset_root: Path | None,
    subgame_table: Any = None,
    subgame_table_path: Path | None = None,
    script_task_extra_info_table: Any = None,
    script_task_extra_info_table_path: Path | None = None,
    level_script_root: Path | None = None,
    native_playback_index: dict[str, list[dict[str, Any]]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Resolve parent DialogTrees to exact authored level/dungeon files.

    Dialog-root naming discovers candidates only. A context is published only
    when the longest namespace match is unique, LevelBasicInfo and DungeonTable
    agree on the exact scene id, and both MemoryPack level files contain that
    exact length-framed id. An optional AnimeStudio map TextAsset is accepted
    only when its decoded payload independently names the same level.

    When the optional SubGame registry and native playback index are supplied,
    the same generic resolver also requires an exact missionless BlackBox row,
    and its bound LevelScript file. Typed ``StartDialogAction`` occurrences are
    attached only for selected parents actually present in that script; absent
    parents remain explicitly definition-only in this runtime shell. Main,
    extra, and fail tasks remain separate authored SubGame lanes and are not
    promoted to Story chronology.
    """
    if (
        not isinstance(level_basic_info_table, dict)
        or not isinstance(dungeon_table, dict)
        or not isinstance(level_config_root, Path)
        or not isinstance(level_data_root, Path)
        or not isinstance(text_asset_root, Path)
    ):
        return [], None
    level_ids = {
        safe_key(level_id)
        for level_id, row in level_basic_info_table.items()
        if safe_key(level_id) and isinstance(row, dict)
    }
    parents_by_level: dict[str, list[str]] = defaultdict(list)
    for parent in parent_dialog_trees:
        parent_key = safe_key(parent.get("sceneKey"))
        level_id, exclusion = _dialog_parent_level_candidate(
            parent_key,
            level_ids,
        )
        if exclusion is not None:
            return [], {
                "gate": "uniqueLongestParentDialogLevelNamespace",
                "parentStoryKey": parent_key,
                "expected": {"uniqueLongestLevelId": True},
                "actual": {"status": exclusion},
            }
        if level_id:
            parents_by_level[level_id].append(parent_key)

    contexts: list[dict[str, Any]] = []
    for level_id, parent_keys in sorted(
        parents_by_level.items(),
        key=lambda item: natural_key(item[0]),
    ):
        basic_row = level_basic_info_table.get(level_id)
        dungeon_rows = [
            (safe_key(row_id), row)
            for row_id, row in dungeon_table.items()
            if isinstance(row, dict)
            and safe_key(row.get("sceneId")) == level_id
        ]
        config_relative = safe_key(
            basic_row.get("configPath")
            if isinstance(basic_row, dict)
            else ""
        )
        config_path = level_config_root / Path(config_relative).name
        level_data_path = (
            level_data_root / level_id / f"{level_id}_lv_data.json"
        )
        try:
            config_data = config_path.read_bytes()
            level_data = level_data_path.read_bytes()
        except OSError:
            config_data = b""
            level_data = b""
        valid = (
            isinstance(basic_row, dict)
            and safe_key(basic_row.get("id")) == level_id
            and config_relative
            == f"Data/Json/LevelConfig/{level_id}.json"
            and len(dungeon_rows) == 1
            and config_data
            and _memorypack_contains_exact_string(config_data, level_id)
            and level_data[:1] == b"\x2b"
            and _memorypack_contains_exact_string(level_data, level_id)
        )
        if not valid:
            return [], {
                "gate": "exactParentDialogLevelContext",
                "parentStoryKeys": sorted(parent_keys, key=natural_key),
                "expected": {
                    "levelId": level_id,
                    "levelBasicInfoId": level_id,
                    "configPath": f"Data/Json/LevelConfig/{level_id}.json",
                    "uniqueDungeonSceneRow": True,
                    "levelConfigContainsExactMemoryPackString": True,
                    "levelDataMemberCount": 43,
                    "levelDataContainsExactMemoryPackString": True,
                },
                "actual": {
                    "levelBasicInfoRow": basic_row,
                    "dungeonSceneRowIds": [row_id for row_id, _ in dungeon_rows],
                    "levelConfigPath": _repo_source_path(config_path),
                    "levelConfigExists": config_path.is_file(),
                    "levelConfigContainsExactMemoryPackString": (
                        _memorypack_contains_exact_string(config_data, level_id)
                        if config_data else False
                    ),
                    "levelDataPath": _repo_source_path(level_data_path),
                    "levelDataExists": level_data_path.is_file(),
                    "levelDataMemberCount": (
                        level_data[0] if level_data else None
                    ),
                    "levelDataContainsExactMemoryPackString": (
                        _memorypack_contains_exact_string(level_data, level_id)
                        if level_data else False
                    ),
                },
            }
        dungeon_id, dungeon_row = dungeon_rows[0]
        map_assets = sorted(text_asset_root.glob(f"{level_id}_p*.json"))
        map_asset_rows: list[dict[str, Any]] = []
        for map_asset in map_assets:
            payload = read_json(map_asset, {})
            try:
                decoded = json.loads(base64.b64decode(
                    payload.get("m_Script", ""),
                    validate=True,
                ).decode("utf-8-sig"))
            except (ValueError, UnicodeDecodeError, binascii.Error):
                decoded = None
            if (
                not isinstance(payload, dict)
                or safe_key(payload.get("m_Name")) != level_id
                or safe_key(payload.get("Name")) != level_id
                or not isinstance(decoded, dict)
                or safe_key(decoded.get("mapIdStr")) != level_id
                or level_id not in _string_list(decoded.get("levelStrIds"))
            ):
                return [], {
                    "gate": "exactParentDialogLevelMapTextAsset",
                    "parentStoryKeys": sorted(parent_keys, key=natural_key),
                    "expected": {
                        "levelId": level_id,
                        "mName": level_id,
                        "mapIdStr": level_id,
                        "levelStrIdsContainsLevelId": True,
                    },
                    "actual": {
                        "sourceFile": _repo_source_path(map_asset),
                        "payloadName": (
                            payload.get("m_Name")
                            if isinstance(payload, dict) else None
                        ),
                        "decodedMapIdStr": (
                            decoded.get("mapIdStr")
                            if isinstance(decoded, dict) else None
                        ),
                        "decodedLevelStrIds": (
                            decoded.get("levelStrIds")
                            if isinstance(decoded, dict) else None
                        ),
                    },
                }
            map_asset_rows.append({
                "sourceFile": _repo_source_path(map_asset),
                "sourcePathId": (
                    map_asset.stem.rsplit("_p", 1)[-1]
                    if "_p" in map_asset.stem else ""
                ),
                "sourceSha256": _sha256_file(map_asset),
                "mapIdStr": level_id,
                "levelStrIds": _string_list(decoded.get("levelStrIds")),
                "artScenePaths": _string_list(decoded.get("artScenePaths")),
            })
        level_data_files = sorted(
            (level_data_root / level_id).glob("*.json"),
            key=lambda path: natural_key(path.name),
        )
        source_files = [config_path, *level_data_files]
        context = {
            "levelId": level_id,
            "parentDialogTreeIds": sorted(set(parent_keys), key=natural_key),
            "dungeonId": dungeon_id,
            "dungeonDomainId": safe_key(dungeon_row.get("domainId")),
            "dungeonSortId": dungeon_row.get("sortId"),
            "levelBasicInfo": {
                "id": level_id,
                "configPath": config_relative,
                "domainName": safe_key(basic_row.get("domainName")),
            },
            "sourceFiles": [_repo_source_path(path) for path in source_files],
            "sourceSha256": {
                _repo_source_path(path): _sha256_file(path)
                for path in source_files
            },
            "mapTextAssets": map_asset_rows,
            "relation": "exact_parent_dialog_level_asset_shell",
            "graphEffect": "none",
            "orderEvidence": False,
        }
        if (
            subgame_table is not None
            or subgame_table_path is not None
            or level_script_root is not None
            or native_playback_index is not None
        ):
            table_rows = (
                subgame_table.get("dataTable")
                if isinstance(subgame_table, dict)
                and isinstance(subgame_table.get("dataTable"), dict)
                else subgame_table
            )
            subgame_row = (
                table_rows.get(dungeon_id)
                if isinstance(table_rows, dict)
                else None
            )
            bind_script_id = (
                subgame_row.get("bindScriptId")
                if isinstance(subgame_row, dict)
                else None
            )
            script_path = (
                level_script_root / level_id / f"{bind_script_id}.json"
                if isinstance(level_script_root, Path)
                and isinstance(bind_script_id, int)
                and not isinstance(bind_script_id, bool)
                and bind_script_id > 0
                else None
            )
            script_source = (
                _repo_source_path(script_path)
                if isinstance(script_path, Path)
                else ""
            )
            expected_parent_keys = sorted(set(parent_keys), key=natural_key)
            parent_playback: list[dict[str, Any]] = []
            missing_parent_keys: list[str] = []
            mismatched_parent_occurrences: dict[str, list[dict[str, Any]]] = {}
            for parent_key in expected_parent_keys:
                candidates = (
                    native_playback_index.get(parent_key) or []
                    if isinstance(native_playback_index, dict)
                    else []
                )
                matches = [
                    row for row in candidates
                    if safe_key(row.get("levelId")) == level_id
                    and safe_key(row.get("scriptId")) == str(bind_script_id)
                    and safe_key(row.get("actionName")) == "StartDialogAction"
                    and safe_key(row.get("sourceFile")) == script_source
                    and safe_key(row.get("nativeMappingId")).startswith(
                        "gameassembly-"
                    )
                    and safe_key(row.get("nativeEventOwnerStatus"))
                    == "exact_serialized_control_path"
                    and isinstance(row.get("nativeEventOwners"), list)
                    and bool(row.get("nativeEventOwners"))
                    and all(
                        isinstance(owner, dict)
                        and safe_key(owner.get("status"))
                        == "exact_serialized_control_path"
                        for owner in row.get("nativeEventOwners")
                    )
                ]
                if len(matches) != 1:
                    if not candidates:
                        missing_parent_keys.append(parent_key)
                    else:
                        mismatched_parent_occurrences[parent_key] = [
                            {
                                "levelId": row.get("levelId"),
                                "scriptId": row.get("scriptId"),
                                "actionName": row.get("actionName"),
                                "sourceFile": row.get("sourceFile"),
                            }
                            for row in candidates[:5]
                        ]
                    continue
                match = matches[0]
                parent_playback.append({
                    "parentDialogTreeId": parent_key,
                    "actionName": "StartDialogAction",
                    "actionLocalId": match.get("localId"),
                    "recordOffset": match.get("recordOffset"),
                    "nativeEventOwners": match.get("nativeEventOwners") or [],
                    "sourceFile": script_source,
                    "relation": "exact_levelscript_parent_dialog_playback",
                    "orderEvidence": False,
                })
            task_lanes_valid = all(
                isinstance(subgame_row.get(lane_name), list)
                and all(
                    isinstance(task, dict)
                    and bool(safe_key(task.get("taskId")))
                    for task in subgame_row.get(lane_name)
                )
                for lane_name in ("mainTasks", "extraTasks", "failTasks")
            ) if isinstance(subgame_row, dict) else False
            valid_subgame = (
                isinstance(subgame_table_path, Path)
                and subgame_table_path.is_file()
                and isinstance(subgame_row, dict)
                and safe_key(subgame_row.get("$type"))
                == "Beyond.Gameplay.Core.BlackBoxSubGameData, Gameplay.Beyond"
                and safe_key(subgame_row.get("id")) == dungeon_id
                and safe_key(subgame_row.get("modeId")) == "blackbox"
                and isinstance(bind_script_id, int)
                and not isinstance(bind_script_id, bool)
                and bind_script_id > 0
                and isinstance(script_path, Path)
                and script_path.is_file()
                and task_lanes_valid
                and not mismatched_parent_occurrences
            )
            if not valid_subgame:
                return [], {
                    "gate": "exactBlackBoxSubGameParentPlayback",
                    "parentStoryKeys": expected_parent_keys,
                    "expected": {
                        "subGameId": dungeon_id,
                        "runtimeType": (
                            "Beyond.Gameplay.Core.BlackBoxSubGameData, "
                            "Gameplay.Beyond"
                        ),
                        "modeId": "blackbox",
                        "positiveIntegerBindScriptId": True,
                        "boundLevelScriptExists": True,
                        "taskLanes": (
                            "mainTasks/extraTasks/failTasks are arrays of "
                            "objects with non-empty taskId"
                        ),
                        "parentPlaybackMustResolveInThisScriptOrBeAbsent": (
                            expected_parent_keys
                        ),
                    },
                    "actual": {
                        "subGameTablePath": (
                            _repo_source_path(subgame_table_path)
                            if isinstance(subgame_table_path, Path) else ""
                        ),
                        "subGameTableExists": (
                            subgame_table_path.is_file()
                            if isinstance(subgame_table_path, Path) else False
                        ),
                        "subGameRow": subgame_row,
                        "boundLevelScriptPath": script_source,
                        "boundLevelScriptExists": (
                            script_path.is_file()
                            if isinstance(script_path, Path) else False
                        ),
                        "taskLanesValid": task_lanes_valid,
                        "matchedParentKeys": [
                            row["parentDialogTreeId"] for row in parent_playback
                        ],
                        "missingParentKeys": missing_parent_keys,
                        "mismatchedParentOccurrences": (
                            mismatched_parent_occurrences
                        ),
                    },
                    "sourceSha256": {
                        "subGameTable": (
                            _sha256_file(subgame_table_path)
                            if isinstance(subgame_table_path, Path)
                            and subgame_table_path.is_file() else ""
                        ),
                        "boundLevelScript": (
                            _sha256_file(script_path)
                            if isinstance(script_path, Path)
                            and script_path.is_file() else ""
                        ),
                    },
                }

            def task_lane(name: str) -> list[dict[str, Any]]:
                rows = subgame_row.get(name) or []
                return [
                    {
                        key: value for key, value in row.items()
                        if key in {"taskId", "levelScriptId", "failInfo"}
                    }
                    for row in rows
                    if isinstance(row, dict) and safe_key(row.get("taskId"))
                ]

            task_topology, task_topology_failure = (
                _blackbox_subgame_task_topology(
                    level_id,
                    bind_script_id,
                    subgame_row,
                    script_path,
                    script_task_extra_info_table,
                    script_task_extra_info_table_path,
                )
            )
            if task_topology_failure is not None:
                task_topology["validatorDiagnostic"] = task_topology_failure
            action_topology, action_topology_failure = (
                _blackbox_subgame_action_topology(
                    level_id,
                    bind_script_id,
                    script_path,
                    native_playback_index,
                )
            )
            if action_topology_failure is not None:
                # The owning carrier validator propagates this structured
                # failure into both the report and the bounded CLI summary.
                # Do not publish a partially decoded runtime shell.
                return [], action_topology_failure
            subgame_sources = [
                path
                for path in (
                    subgame_table_path,
                    script_path,
                    script_task_extra_info_table_path,
                )
                if isinstance(path, Path)
            ]
            context["subGameRuntime"] = {
                "subGameId": dungeon_id,
                "runtimeType": safe_key(subgame_row.get("$type")),
                "modeId": "blackbox",
                "subDataParentId": subgame_row.get("subDataParentId"),
                "bindScriptId": bind_script_id,
                "mainTasks": task_lane("mainTasks"),
                "extraTasks": task_lane("extraTasks"),
                "failTasks": task_lane("failTasks"),
                "taskTopology": task_topology,
                "actionTopology": action_topology,
                "parentDialogPlayback": parent_playback,
                "definitionOnlyParentDialogTreeIds": missing_parent_keys,
                "parentPlaybackCoverage": (
                    "complete"
                    if len(parent_playback) == len(expected_parent_keys)
                    else "partial"
                    if parent_playback
                    else "none"
                ),
                "sourceFiles": [
                    _repo_source_path(path) for path in subgame_sources
                ],
                "sourceSha256": {
                    _repo_source_path(path): _sha256_file(path)
                    for path in subgame_sources
                },
                "relation": "exact_blackbox_subgame_parent_dialog_playback",
                "taskLaneBoundary": (
                    "main, extra, and fail tasks are authored SubGame lanes, "
                    "not Story file chronology"
                ),
                "parentPlaybackBoundary": (
                    "selected parents absent from the bound script remain "
                    "definition-only in this runtime shell; shared level and "
                    "SubGame context does not invent their activation"
                ),
                "graphEffect": "none",
                "orderEvidence": False,
            }
            context["sourceFiles"].extend(
                context["subGameRuntime"]["sourceFiles"]
            )
            context["sourceSha256"].update(
                context["subGameRuntime"]["sourceSha256"]
            )
        contexts.append(context)
    return contexts, None

def _dialog_text_partition_fragment_facts(
    line_ids: list[str],
    covered_line_ids: list[str],
    missing_line_ids: list[str],
) -> list[dict[str, Any]]:
    """Describe numbered table-only fragments without promoting suffix order."""
    pattern = re.compile(r"^(?P<namespace>.+)_(?P<number>[0-9]+)$")
    parsed: dict[str, tuple[str, int]] = {}
    for line_id in line_ids:
        match = pattern.fullmatch(safe_key(line_id))
        if match is None:
            return []
        parsed[line_id] = (
            match.group("namespace"),
            int(match.group("number")),
        )
    covered_set = set(covered_line_ids)
    rows: list[dict[str, Any]] = []
    for line_id in missing_line_ids:
        namespace, number = parsed[line_id]
        covered_peers = sorted(
            (
                (peer_number, peer_id)
                for peer_id, (peer_namespace, peer_number) in parsed.items()
                if peer_id in covered_set and peer_namespace == namespace
            ),
        )
        lower = [row for row in covered_peers if row[0] < number]
        upper = [row for row in covered_peers if row[0] > number]
        if not covered_peers:
            position = "separate_numbered_namespace"
        elif not lower:
            position = "before_covered_numeric_range"
        elif not upper:
            position = "after_covered_numeric_range"
        else:
            position = "inside_covered_numeric_range"
        rows.append({
            "lineId": line_id,
            "numberedNamespace": namespace,
            "numericSuffix": number,
            "numericPosition": position,
            "nearestLowerCoveredLineId": lower[-1][1] if lower else "",
            "nearestUpperCoveredLineId": upper[0][1] if upper else "",
            "evidenceStatus": "original_row_id_cross_reference_only",
            "graphEffect": "none",
            "orderEvidence": False,
        })
    return rows

def _generic_registered_dialog_tree_trunk_group_facts(
    story_key: str,
    dialog_text_table: Any,
    dialog_id_index: Any,
    definitions_by_root: dict[str, dict[str, Any]],
    *,
    level_basic_info_table: Any = None,
    dungeon_table: Any = None,
    level_config_root: Path | None = None,
    level_data_root: Path | None = None,
    text_asset_root: Path | None = None,
    subgame_table: Any = None,
    subgame_table_path: Path | None = None,
    script_task_extra_info_table: Any = None,
    script_task_extra_info_table_path: Path | None = None,
    level_script_root: Path | None = None,
    native_playback_index: dict[str, list[dict[str, Any]]] | None = None,
) -> tuple[
    dict[str, Any] | None,
    dict[str, Any] | None,
    str | None,
]:
    """Resolve one emitted non-root line group to exact registered trees.

    The emitted key is candidate discovery only. ``misc_*`` aggregates select
    their complete authored namespace, while direct unregistered ``dlg_*``
    scene buckets select only exact numbered rows (``<scene>_<digits>``), so a
    nested scene cannot be absorbed by a shorter prefix. Qualification is an
    exact, non-overlapping set partition across the rows actually carried by
    registered, hash-validated DialogTree definitions; each selected tree may
    contain no line outside the emitted row set. A complete partition can
    close the carrier search. A partial partition is retained as graph-neutral
    evidence while its unmatched rows remain an actionable recovery gap. Tree
    edges prove only internal parent-dialog order in either case.
    """
    if story_key.startswith("misc_"):
        definition_root = story_key.removeprefix("misc_")
        emitted_group_kind = "mechanical_namespace_aggregate"
        line_selection_method = "authored_namespace_prefix"

        def is_target_line(line_id: Any) -> bool:
            return safe_key(line_id).startswith(f"{definition_root}_")
    elif story_key.startswith("dlg_"):
        definition_root = story_key
        emitted_group_kind = "direct_numbered_dialog_scene"
        line_selection_method = "exact_numbered_scene_rows"
        numbered_line_pattern = re.compile(
            rf"^{re.escape(definition_root)}_[0-9]+$"
        )

        def is_target_line(line_id: Any) -> bool:
            return numbered_line_pattern.fullmatch(safe_key(line_id)) is not None
    else:
        return None, None, "notSupportedEmittedDialogGroup"
    if not definition_root or not isinstance(dialog_text_table, dict):
        return None, None, "missingDialogTextTable"
    if isinstance(dialog_id_index, dict) and definition_root in dialog_id_index:
        return None, None, "groupIsRegisteredDialogRoot"
    target_line_ids = sorted(
        (
            line_id
            for line_id in dialog_text_table
            if is_target_line(line_id)
        ),
        key=natural_key,
    )
    if not target_line_ids:
        return None, None, "noExactDialogTextRows"
    malformed_rows = {
        line_id: dialog_text_table.get(line_id)
        for line_id in target_line_ids
        if not isinstance(dialog_text_table.get(line_id), dict)
    }
    if malformed_rows:
        return None, {
            "validator": "genericRegisteredDialogTreeTrunkGroup",
            "gate": "exactDialogTextRows",
            "storyKey": story_key,
            "expected": {"rowType": "object"},
            "actual": malformed_rows,
        }, None
    target_set = set(target_line_ids)
    selected: list[dict[str, Any]] = []
    selected_parent_keys: list[str] = []
    coverage: dict[str, list[str]] = defaultdict(list)
    for parent_key, definition in definitions_by_root.items():
        parent_line_ids = _string_list(definition.get("lineIds"))
        parent_set = set(parent_line_ids)
        if not parent_set or not parent_set <= target_set:
            continue
        dialog_id_row = (
            dialog_id_index.get(parent_key)
            if isinstance(dialog_id_index, dict)
            else None
        )
        facts, failure = _generic_registered_dialog_tree_definition_facts(
            parent_key,
            dialog_id_row,
            definition,
        )
        if failure is not None:
            failure.update({
                "validator": "genericRegisteredDialogTreeTrunkGroup",
                "gate": "exactRegisteredParentDialogTree",
                "storyKey": story_key,
                "parentStoryKey": parent_key,
            })
            return None, failure, None
        for line_id in parent_line_ids:
            coverage[line_id].append(parent_key)
        selected.append(facts or {})
        selected_parent_keys.append(parent_key)
    missing = [
        line_id for line_id in target_line_ids
        if not coverage.get(line_id)
    ]
    duplicated = {
        line_id: parents
        for line_id, parents in coverage.items()
        if len(parents) > 1
    }
    selection_method = "exact_registered_line_partition"
    if duplicated:
        # Authored trunk IDs and their owning DialogTree roots use a stable
        # namespace convention: ``timeline_<family>`` -> ``dlg_<family>``.
        # Use it only as a tie-breaker between already hash-validated exact
        # content matches. It cannot fill an absent row or relax containment.
        dialog_namespace = (
            definition_root
            if definition_root.startswith("dlg_")
            else (
                f"dlg_{definition_root.removeprefix('timeline_')}"
                if definition_root.startswith("timeline_")
                else f"dlg_{definition_root}"
            )
        )
        namespace_parent_keys = {
            parent_key
            for parent_key in selected_parent_keys
            if parent_key == dialog_namespace
            or parent_key.startswith(f"{dialog_namespace}_")
        }
        namespace_selected = [
            row for parent_key, row in zip(selected_parent_keys, selected)
            if parent_key in namespace_parent_keys
        ]
        namespace_coverage: dict[str, list[str]] = defaultdict(list)
        for parent_key in namespace_parent_keys:
            for line_id in _string_list(
                definitions_by_root[parent_key].get("lineIds")
            ):
                namespace_coverage[line_id].append(parent_key)
        namespace_missing = [
            line_id for line_id in target_line_ids
            if not namespace_coverage.get(line_id)
        ]
        namespace_duplicated = {
            line_id: parents
            for line_id, parents in namespace_coverage.items()
            if len(parents) > 1
        }
        if namespace_selected and not namespace_duplicated:
            selected = namespace_selected
            coverage = namespace_coverage
            missing = namespace_missing
            duplicated = {}
            selection_method = "exact_registered_line_partition_namespace_tiebreak"
    if duplicated:
        return None, None, "ambiguousParentTreePartition"
    if not selected:
        return None, None, "noRegisteredParentTreePartition"
    selected.sort(key=lambda row: natural_key(safe_key(row.get("sceneKey"))))
    parent_level_contexts, level_context_failure = (
        _generic_parent_dialog_level_context_facts(
            selected,
            level_basic_info_table,
            dungeon_table,
            level_config_root=level_config_root,
            level_data_root=level_data_root,
            text_asset_root=text_asset_root,
            subgame_table=subgame_table,
            subgame_table_path=subgame_table_path,
            script_task_extra_info_table=script_task_extra_info_table,
            script_task_extra_info_table_path=(
                script_task_extra_info_table_path
            ),
            level_script_root=level_script_root,
            native_playback_index=native_playback_index,
        )
    )
    if level_context_failure is not None:
        level_context_failure.update({
            "validator": "genericRegisteredDialogTreeTrunkGroup",
            "storyKey": story_key,
        })
        return None, level_context_failure, None
    facts = {
        "emittedStoryKey": story_key,
        "definitionRootKey": definition_root,
        "emittedGroupKind": emitted_group_kind,
        "lineSelectionMethod": line_selection_method,
        "partitionStatus": "partial" if missing else "complete",
        "lineIds": target_line_ids,
        "lineCount": len(target_line_ids),
        "coveredLineIds": sorted(coverage, key=natural_key),
        "coveredLineCount": len(coverage),
        "missingLineIds": missing,
        "missingLineCount": len(missing),
        "parentDialogTrees": selected,
        "parentDialogTreeCount": len(selected),
        "parentLevelContexts": parent_level_contexts,
        "parentLevelContextCount": len(parent_level_contexts),
        "branchingParentDialogTreeCount": sum(
            1 for row in selected
            if int(row.get("branchingOptionGroupCount") or 0) > 0
        ),
        "parentSelectionMethod": selection_method,
        "exactLinePartition": {
            line_id: parents[0]
            for line_id, parents in sorted(
                coverage.items(),
                key=lambda item: natural_key(item[0]),
            )
        },
        "definitionSourceFiles": sorted({
            safe_key(row.get("sourceFile"))
            for row in selected
            if safe_key(row.get("sourceFile"))
        }),
        "sourceSha256": {
            safe_key(row.get("sourceFile")): safe_key(
                row.get("sourceSha256")
            )
            for row in selected
            if safe_key(row.get("sourceFile"))
        },
        "missingLineFragments": _dialog_text_partition_fragment_facts(
            target_line_ids,
            sorted(coverage, key=natural_key),
            missing,
        ),
    }
    return facts, None, (
        "incompleteParentTreePartition" if missing else None
    )

def _generic_partial_dialog_row_consumer_exhaustion_facts(
    story_key: str,
    facts: dict[str, Any],
    definitions_by_root: dict[str, dict[str, Any]],
    level_script_census: dict[str, Any],
    binary_census: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str | None]:
    """Close unmatched table rows only after a typed runtime census.

    This is intentionally content-identity agnostic. It recognizes a partial
    registered DialogTree partition, verifies that every recovered parent is
    accounted for by exact BlackBox SubGame playback or definition-only rows,
    and then requires the unmatched line ids to be absent from every decoded
    DialogTree, every exported LevelScript, and both original game binaries.
    The result classifies the unmatched rows as surviving definitions without
    a current consumer; it never appends them to a neighboring parent tree.
    """
    missing = _string_list(facts.get("missingLineIds"))
    if facts.get("partitionStatus") != "partial" or not missing:
        return None, None, "notPartialPartition"
    missing_set = set(missing)
    alternate_carriers = sorted(
        (
            {
                "sceneKey": parent_key,
                "lineIds": sorted(
                    missing_set & set(_string_list(definition.get("lineIds"))),
                    key=natural_key,
                ),
                "sourceFile": safe_key(definition.get("sourceFile")),
            }
            for parent_key, definition in definitions_by_root.items()
            if missing_set & set(_string_list(definition.get("lineIds")))
        ),
        key=lambda row: natural_key(row["sceneKey"]),
    )
    if alternate_carriers:
        return None, None, "missingRowsHaveDecodedDialogTreeCarrier"

    parent_keys = {
        safe_key(row.get("sceneKey"))
        for row in facts.get("parentDialogTrees") or []
        if isinstance(row, dict) and safe_key(row.get("sceneKey"))
    }
    contexts = [
        row for row in facts.get("parentLevelContexts") or []
        if isinstance(row, dict)
    ]
    accounted_parent_keys: set[str] = set()
    context_failures: list[dict[str, Any]] = []
    for context in contexts:
        runtime = context.get("subGameRuntime")
        topology = runtime.get("taskTopology") if isinstance(runtime, dict) else None
        context_parent_keys = set(_string_list(context.get("parentDialogTreeIds")))
        playback_keys = {
            safe_key(
                row.get("parentDialogTreeId")
                or row.get("dialogTreeId")
                or row.get("storyKey")
            )
            for row in (runtime.get("parentDialogPlayback") or [])
            if isinstance(row, dict)
        } if isinstance(runtime, dict) else set()
        definition_only_keys = set(
            _string_list(
                runtime.get("definitionOnlyParentDialogTreeIds")
                if isinstance(runtime, dict) else None
            )
        )
        context_valid = (
            isinstance(runtime, dict)
            and runtime.get("runtimeType")
            == "Beyond.Gameplay.Core.BlackBoxSubGameData, Gameplay.Beyond"
            and safe_key(runtime.get("bindScriptId"))
            and isinstance(topology, dict)
            and topology.get("status") in {
                "exact_complete_task_map",
                "exact_null_task_map",
            }
            and context_parent_keys
            and context_parent_keys == playback_keys | definition_only_keys
        )
        if context_valid:
            accounted_parent_keys.update(context_parent_keys)
        else:
            context_failures.append({
                "levelId": safe_key(context.get("levelId")),
                "parentDialogTreeIds": sorted(context_parent_keys, key=natural_key),
                "runtimeType": (
                    safe_key(runtime.get("runtimeType"))
                    if isinstance(runtime, dict) else ""
                ),
                "bindScriptId": (
                    safe_key(runtime.get("bindScriptId"))
                    if isinstance(runtime, dict) else ""
                ),
                "taskTopologyStatus": (
                    safe_key(topology.get("status"))
                    if isinstance(topology, dict) else ""
                ),
                "playedParentDialogTreeIds": sorted(playback_keys, key=natural_key),
                "definitionOnlyParentDialogTreeIds": sorted(
                    definition_only_keys,
                    key=natural_key,
                ),
            })
    if context_failures or accounted_parent_keys != parent_keys:
        return None, {
            "validator": "genericPartialDialogRowConsumerExhaustion",
            "gate": "exactTypedParentRuntimeCoverage",
            "storyKey": story_key,
            "expected": {
                "parentDialogTreeIds": sorted(parent_keys, key=natural_key),
                "everyParentHasExactBlackBoxRuntimeDisposition": True,
                "taskTopologyStatuses": [
                    "exact_complete_task_map",
                    "exact_null_task_map",
                ],
            },
            "actual": {
                "accountedParentDialogTreeIds": sorted(
                    accounted_parent_keys,
                    key=natural_key,
                ),
                "contextFailures": context_failures,
            },
        }, None

    expected_literals = sorted(missing, key=natural_key)
    expected_literal_set = set(expected_literals)
    level_census_literal_set = set(
        _string_list(level_script_census.get("literalIds"))
    )
    binary_census_literal_set = set(
        _string_list(binary_census.get("literalIds"))
    )
    census_valid = (
        expected_literal_set <= level_census_literal_set
        and int(level_script_census.get("sourceFileCount") or 0) > 0
        and safe_key(level_script_census.get("sourceSetSha256"))
        and expected_literal_set <= binary_census_literal_set
        and int(binary_census.get("sourceFileCount") or 0) == 2
        and safe_key(binary_census.get("sourceSetSha256"))
    )
    if not census_valid:
        return None, {
            "validator": "genericPartialDialogRowConsumerExhaustion",
            "gate": "completeConsumerCorpusCensus",
            "storyKey": story_key,
            "expected": {
                "literalIds": expected_literals,
                "nonemptyLevelScriptCorpus": True,
                "originalGameBinaryCount": 2,
                "nonemptySourceSetHashes": True,
            },
            "actual": {
                "levelScriptLiteralIds": _string_list(
                    level_script_census.get("literalIds")
                ),
                "levelScriptSourceFileCount": level_script_census.get(
                    "sourceFileCount"
                ),
                "levelScriptSourceSetSha256": safe_key(
                    level_script_census.get("sourceSetSha256")
                ),
                "binaryLiteralIds": _string_list(
                    binary_census.get("literalIds")
                ),
                "binarySourceFileCount": binary_census.get("sourceFileCount"),
                "binarySourceSetSha256": safe_key(
                    binary_census.get("sourceSetSha256")
                ),
            },
        }, None

    level_matches = level_script_census.get("matchesByLiteral") or {}
    binary_matches = binary_census.get("matchesByLiteral") or {}
    if any(level_matches.get(line_id) for line_id in missing):
        return None, None, "missingRowsOccurInExportedLevelScript"
    if any(binary_matches.get(line_id) for line_id in missing):
        return None, None, "missingRowsOccurInOriginalBinary"
    return {
        "unmatchedRowStatus": "definition_rows_without_current_consumer",
        "unmatchedRowConsumerCensus": {
            "dialogTreeCorpus": {
                "decodedDefinitionCount": len(definitions_by_root),
                "matchingDefinitions": alternate_carriers,
            },
            "levelScriptCorpus": level_script_census,
            "originalGameBinaries": binary_census,
        },
        "consumerBoundary": (
            "registered parent DialogTrees retain their exact internal lines and "
            "typed BlackBox SubGame playback disposition; the unmatched "
            "DialogText rows occur in no decoded DialogTree, exported "
            "LevelScript, GameAssembly, or global metadata, so the current "
            "original-data surface exposes definitions but no consumer"
        ),
        "orderBoundary": (
            "unmatched row ids are not appended to a neighboring parent; "
            "numeric position, table order, OCR, and manual overrides remain "
            "cross-reference only and establish no playback or chronology"
        ),
    }, None, None

def _generic_registered_table_dialog_definition_facts(
    story_key: str,
    definition_root_key: str,
    dialog_id_row: Any,
    dialog_text_table: Any,
    dialog_option_table: Any,
    audio_stems: set[str],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Validate a registered table-only dialog exposed through an alias."""
    if (
        not story_key.startswith("misc_dlg_")
        or definition_root_key != story_key.removeprefix("misc_")
    ):
        return None, {
            "validator": "genericRegisteredTableDialogNegativeConsumer",
            "gate": "mechanicalEmittedToAuthoredDialogAlias",
            "storyKey": story_key,
            "expected": {"definitionRootKey": story_key.removeprefix("misc_")},
            "actual": {"definitionRootKey": definition_root_key},
        }
    if (
        not isinstance(dialog_id_row, dict)
        or dialog_id_row.get("registered") is not True
        or dialog_id_row.get("memoryPackRecordKey") is not True
        or dialog_id_row.get("hasRootKey") is not True
    ):
        return None, {
            "validator": "genericRegisteredTableDialogNegativeConsumer",
            "gate": "exactCurrentDialogIdRegistration",
            "storyKey": story_key,
            "expected": {
                "registryKey": definition_root_key,
                "registered": True,
                "memoryPackRecordKey": True,
                "hasRootKey": True,
            },
            "actual": dialog_id_row,
        }
    facts, failure = _generic_unregistered_dialog_definition_facts(
        definition_root_key,
        dialog_text_table,
        dialog_option_table,
        audio_stems,
    )
    if failure is not None:
        failure["validator"] = "genericRegisteredTableDialogNegativeConsumer"
        failure["storyKey"] = story_key
        failure["definitionRootKey"] = definition_root_key
        return None, failure
    return {
        **(facts or {}),
        "emittedStoryKey": story_key,
        "definitionRootKey": definition_root_key,
        "runtimeRegistryKey": definition_root_key,
    }, None

def _generic_text_table_only_cutscene_definition_facts(
    story_key: str,
    text_table: Any,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Validate an exact localized cutscene row group without an asset root."""
    if not isinstance(text_table, dict):
        return None, {
            "validator": "genericTextTableOnlyCutsceneNegativeConsumer",
            "gate": "sourceTableShape",
            "storyKey": story_key,
            "expected": {"textTable": "object"},
            "actual": {"textTable": type(text_table).__name__},
        }
    row_pattern = re.compile(rf"^{re.escape(story_key)}_(\d{{2}})$")
    rows = sorted(
        (
            (row_key, match, row)
            for row_key, row in text_table.items()
            if (match := row_pattern.fullmatch(row_key)) is not None
        ),
        key=lambda item: int(item[1].group(1)),
    )
    if not rows:
        return None, {
            "validator": "genericTextTableOnlyCutsceneNegativeConsumer",
            "gate": "exactTextTableRoot",
            "storyKey": story_key,
            "expected": {
                "rowIdPattern": f"{story_key}_NN",
                "nonemptyRows": True,
            },
            "actual": {"rowIds": []},
        }
    row_ids: list[str] = []
    text_ids: list[int] = []
    for row_id, _match, row in rows:
        if (
            not isinstance(row, dict)
            or set(row) != {"id", "text"}
            or not isinstance(row.get("id"), int)
            or isinstance(row.get("id"), bool)
            or not isinstance(row.get("text"), str)
        ):
            return None, {
                "validator": "genericTextTableOnlyCutsceneNegativeConsumer",
                "gate": "exactLocalizedTextRowShape",
                "storyKey": story_key,
                "expected": {
                    "fields": ["id", "text"],
                    "integerNonBooleanId": True,
                    "stringText": True,
                },
                "actual": {
                    "rowId": row_id,
                    "type": type(row).__name__,
                    "row": row,
                },
            }
        row_ids.append(row_id)
        text_ids.append(row["id"])
    return {
        "definitionRootKey": story_key,
        "definitionRowKeys": row_ids,
        "localizedTextIds": text_ids,
    }, None

def _generic_dialog_timeline_definition_facts(
    story_key: str,
    timeline_row: Any,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Validate optional internal dialog-Timeline evidence for one root."""
    if timeline_row is None:
        return None, None
    source_roots = (
        timeline_row.get("sourceRoots")
        if isinstance(timeline_row, dict) else None
    )
    source_paths = [
        ROOT / safe_key(value)
        for value in source_roots or []
        if safe_key(value)
    ]
    valid = (
        isinstance(timeline_row, dict)
        and safe_key(timeline_row.get("dialogKey")) == story_key
        and safe_key(timeline_row.get("timeline")).startswith("dlgtl_")
        and isinstance(timeline_row.get("lineIds"), list)
        and all(isinstance(value, str) for value in timeline_row["lineIds"])
        and isinstance(timeline_row.get("trackCount"), int)
        and timeline_row["trackCount"] >= 0
        and isinstance(timeline_row.get("duplicateClipCount"), int)
        and timeline_row["duplicateClipCount"] >= 0
        and isinstance(timeline_row.get("runtimeJumpClips"), list)
        and isinstance(source_roots, list)
        and bool(source_roots)
        and len(source_paths) == len(source_roots)
        and all(path.is_file() for path in source_paths)
    )
    if not valid:
        return None, {
            "validator": "genericRegisteredDialogTreeNegativeConsumer",
            "gate": "exactInternalDialogTimelineDefinition",
            "storyKey": story_key,
            "expected": {
                "dialogKey": story_key,
                "timelinePrefix": "dlgtl_",
                "lineIds": "string[]",
                "nonnegativeTrackCounts": True,
                "nonemptyExistingSourceRoots": True,
            },
            "actual": {
                "type": type(timeline_row).__name__,
                "dialogKey": (
                    timeline_row.get("dialogKey")
                    if isinstance(timeline_row, dict) else None
                ),
                "timeline": (
                    timeline_row.get("timeline")
                    if isinstance(timeline_row, dict) else None
                ),
                "lineIdsType": type(
                    timeline_row.get("lineIds")
                    if isinstance(timeline_row, dict) else None
                ).__name__,
                "sourceRoots": source_roots,
                "existingSourceRoots": sum(path.is_file() for path in source_paths),
            },
        }
    return {
        "timeline": timeline_row["timeline"],
        "dialogKey": timeline_row["dialogKey"],
        "lineIds": list(timeline_row["lineIds"]),
        "trackCount": timeline_row["trackCount"],
        "duplicateClipCount": timeline_row["duplicateClipCount"],
        "runtimeJumpClips": list(timeline_row["runtimeJumpClips"]),
        "source": safe_key(timeline_row.get("source")),
        "sourceRoots": list(source_roots),
        "evidenceKind": "exact_internal_dialog_timeline_definition",
        "activationEvidence": False,
        "crossFileOrderEvidence": False,
    }, None

def _generic_radio_definition_facts(
    story_key: str,
    row: Any,
    audio_stems: set[str],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Validate one current RadioTable definition without key declarations."""
    lines = row.get("radioSingleDataList") if isinstance(row, dict) else None
    if (
        not isinstance(row, dict)
        or set(row) != OFFLINE_EXHAUSTION_RADIO_ROW_FIELDS
        or not isinstance(lines, list)
        or not lines
    ):
        return None, {
            "validator": "genericRadioNegativeConsumer",
            "gate": "exactRadioTableShape",
            "storyKey": story_key,
            "expected": {
                "fields": sorted(OFFLINE_EXHAUSTION_RADIO_ROW_FIELDS),
                "nonemptyRadioSingleDataList": True,
            },
            "actual": {
                "type": type(row).__name__,
                "fields": sorted(row) if isinstance(row, dict) else [],
                "radioSingleDataCount": len(lines or []),
            },
        }
    line_ids: list[str] = []
    audio_ids: list[str] = []
    indices: list[int] = []
    for line in lines:
        line_id = safe_key(line.get("id")) if isinstance(line, dict) else ""
        audio_id = (
            safe_key(line.get("audioOverride"))
            if isinstance(line, dict) else ""
        )
        index = line.get("index") if isinstance(line, dict) else None
        if (
            not isinstance(line, dict)
            or set(line) != OFFLINE_EXHAUSTION_RADIO_LINE_FIELDS
            or not line_id.startswith(f"{story_key}_")
            or not audio_id
            or not isinstance(index, int)
            or isinstance(index, bool)
            or index <= 0
        ):
            return None, {
                "validator": "genericRadioNegativeConsumer",
                "gate": "exactRadioLineShape",
                "storyKey": story_key,
                "expected": {
                    "fields": sorted(OFFLINE_EXHAUSTION_RADIO_LINE_FIELDS),
                    "lineIdPrefix": f"{story_key}_",
                    "nonemptyAudioOverride": True,
                    "positiveIntegerIndex": True,
                },
                "actual": {
                    "type": type(line).__name__,
                    "fields": sorted(line) if isinstance(line, dict) else [],
                    "lineId": line_id,
                    "audioOverride": audio_id,
                    "index": index,
                },
            }
        line_ids.append(line_id)
        audio_ids.append(audio_id)
        indices.append(index)
    if len(set(line_ids)) != len(line_ids) or len(set(indices)) != len(indices):
        return None, {
            "validator": "genericRadioNegativeConsumer",
            "gate": "uniqueRadioLineIdentity",
            "storyKey": story_key,
            "expected": {
                "uniqueLineIds": len(line_ids),
                "uniqueIndices": len(indices),
            },
            "actual": {
                "uniqueLineIds": len(set(line_ids)),
                "uniqueIndices": len(set(indices)),
            },
        }
    audio_membership = {
        audio_id: sorted(
            stem
            for stem in audio_stems
            if stem == audio_id or stem.startswith(f"{audio_id}_")
        )
        for audio_id in sorted(set(audio_ids), key=natural_key)
    }
    present_audio_ids = {
        audio_id for audio_id, matches in audio_membership.items() if matches
    }
    return {
        "lineIds": line_ids,
        "lineIndices": indices,
        "audioIds": sorted(set(audio_ids), key=natural_key),
        "audioMembership": audio_membership,
        "audioMembershipStatus": (
            "all_current_audio_dialog_ids_missing"
            if not present_audio_ids else (
                "all_current_audio_dialog_ids_present"
                if len(present_audio_ids) == len(audio_membership)
                else "partial_current_audio_dialog_missing_ids"
            )
        ),
    }, None

NPC_PROXY_EX_ROW_FIELDS = frozenset({
    "addDialogExOption",
    "dialogExOptionData",
    "dialogId",
    "envTalkData",
    "missionId",
})

NPC_PROXY_EX_LEGACY_ROW_FIELDS = NPC_PROXY_EX_ROW_FIELDS - {"missionId"}

NPC_PROXY_INFO_FIELDS = frozenset({
    "mapId",
    "npcId",
    "npcNameId",
    "npcProxyType",
})

SNS_DIALOG_ROW_FIELDS = frozenset({
    "chatId",
    "dialogContentData",
    "dialogId",
    "dialogType",
    "noticeType",
    "relatedMissionId",
    "skipToFirstOption",
    "topicId",
})

SNS_CONTENT_ROW_FIELDS = frozenset({
    "content",
    "contentId",
    "contentParam",
    "contentParams",
    "contentType",
    "dialogOptionIds",
    "isEnd",
    "linkMissionId",
    "linkRewardId",
    "nextContentId",
    "optionType",
    "preContentId",
    "speaker",
})

SNS_CHAT_ROW_FIELDS = frozenset({
    "charGender",
    "chatId",
    "chatType",
    "icon",
    "isSettlementChannel",
    "name",
    "owner",
    "tagType",
})

SNS_OPTION_ROW_FIELDS = frozenset({
    "optionDesc",
    "optionId",
    "optionNPCCount",
    "optionNPCIds",
    "optionNextContentId",
    "optionResPath",
})

def _generic_missionless_npc_proxy_dialog_facts(
    story_key: str,
    npc_proxy_ex_table: Any,
    npc_proxy_table: Any,
    dialog_id_index: Any,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Recover exact native-selectable proxy rows without assigning order."""
    definition_root_key = (
        story_key.removeprefix("misc_")
        if story_key.startswith("misc_dlg_")
        else story_key
    )
    ex_data = (
        npc_proxy_ex_table.get("data")
        if isinstance(npc_proxy_ex_table, dict) else None
    )
    proxy_info_data = (
        npc_proxy_ex_table.get("proxyInfoData")
        if isinstance(npc_proxy_ex_table, dict) else None
    )
    proxy_rows = (
        npc_proxy_table.get("dataTable")
        if isinstance(npc_proxy_table, dict) else None
    )
    registry = (
        dialog_id_index.get(definition_root_key)
        if isinstance(dialog_id_index, dict) else None
    )
    if not all(isinstance(value, dict) for value in (
        ex_data,
        proxy_info_data,
        proxy_rows,
        dialog_id_index,
    )):
        return None, {
            "validator": "genericMissionlessNpcProxyDialogConsumer",
            "gate": "sourceTableShape",
            "storyKey": story_key,
            "expected": "NpcProxyEx data/proxyInfoData, NpcProxy dataTable, and DialogId index objects",
            "actual": {
                "npcProxyExData": type(ex_data).__name__,
                "npcProxyInfoData": type(proxy_info_data).__name__,
                "npcProxyDataTable": type(proxy_rows).__name__,
                "dialogIdIndex": type(dialog_id_index).__name__,
            },
        }
    consumers: list[dict[str, Any]] = []
    for proxy_id, rows in sorted(ex_data.items(), key=lambda item: natural_key(item[0])):
        if not isinstance(rows, list):
            continue
        for active_row_index, row in enumerate(rows):
            if (
                not isinstance(row, dict)
                or safe_key(row.get("dialogId")) != definition_root_key
            ):
                continue
            if safe_key(row.get("missionId")):
                continue
            info = proxy_info_data.get(proxy_id)
            proxy = proxy_rows.get(proxy_id)
            row_fields = set(row)
            valid_row_fields = row_fields in {
                NPC_PROXY_EX_ROW_FIELDS,
                NPC_PROXY_EX_LEGACY_ROW_FIELDS,
            }
            valid_registry = (
                isinstance(registry, dict)
                and registry.get("registered") is True
                and registry.get("memoryPackRecordKey") is True
                and registry.get("hasRootKey") is True
            )
            if (
                not valid_row_fields
                or row.get("addDialogExOption") not in (True, False)
                or not isinstance(row.get("dialogExOptionData"), list)
                or not isinstance(row.get("envTalkData"), dict)
            ):
                return None, {
                    "validator": "genericMissionlessNpcProxyDialogConsumer",
                    "gate": "exactNpcProxyExConsumerRow",
                    "storyKey": story_key,
                    "npcProxyId": proxy_id,
                    "activeRowIndex": active_row_index,
                    "expected": {
                        "rowFields": [
                            sorted(NPC_PROXY_EX_LEGACY_ROW_FIELDS),
                            sorted(NPC_PROXY_EX_ROW_FIELDS),
                        ],
                        "emptyMissionId": True,
                    },
                    "actual": {
                        "rowFields": sorted(row_fields),
                        "missionId": safe_key(row.get("missionId")),
                        "proxyId": safe_key(proxy.get("proxyId")) if isinstance(proxy, dict) else "",
                        "levelId": safe_key(proxy.get("levelId")) if isinstance(proxy, dict) else "",
                        "proxyInfo": info if isinstance(info, dict) else info,
                        "dialogRegistry": registry if isinstance(registry, dict) else registry,
                    },
                }
            if (
                not isinstance(info, dict)
                or set(info) != NPC_PROXY_INFO_FIELDS
                or not all(safe_key(info.get(field)) for field in (
                    "npcId", "npcNameId", "mapId"
                ))
                or not isinstance(info.get("npcProxyType"), int)
                or isinstance(info.get("npcProxyType"), bool)
                or not isinstance(proxy, dict)
                or safe_key(proxy.get("proxyId")) != proxy_id
                or not safe_key(proxy.get("levelId"))
                or not valid_registry
            ):
                return None, {
                    "validator": "genericMissionlessNpcProxyDialogConsumer",
                    "gate": "exactNpcProxyConsumerIdentity",
                    "storyKey": story_key,
                    "definitionRootKey": definition_root_key,
                    "npcProxyId": proxy_id,
                    "activeRowIndex": active_row_index,
                    "expected": {
                        "proxyInfoFields": sorted(NPC_PROXY_INFO_FIELDS),
                        "nonEmptyProxyInfoFields": [
                            "npcId", "npcNameId", "mapId",
                        ],
                        "npcProxyType": "integer",
                        "proxyId": proxy_id,
                        "nonEmptyLevelId": True,
                        "dialogRegistry": {
                            "registered": True,
                            "memoryPackRecordKey": True,
                            "hasRootKey": True,
                        },
                    },
                    "actual": {
                        "proxyInfo": info,
                        "proxy": proxy,
                        "dialogRegistry": registry,
                    },
                }
            consumers.append({
                "npcProxyId": proxy_id,
                "activeRowIndex": active_row_index,
                "dialogId": definition_root_key,
                "levelId": safe_key(proxy.get("levelId")),
                "subDataParentId": proxy.get("subDataParentId"),
                "npcId": safe_key(info.get("npcId")),
                "npcNameId": safe_key(info.get("npcNameId")),
                "mapId": safe_key(info.get("mapId")),
                "missionId": "",
            })
    if not consumers:
        return None, None
    return {
        "emittedStoryKey": story_key,
        "definitionRootKey": definition_root_key,
        "npcProxyConsumers": consumers,
        "dialogIdRegistrationStatus": "memorypack_root_registered",
        "consumerCount": len(consumers),
    }, None

def _compose_registered_dialog_tree_npc_proxy_evidence(
    tree_evidence: Any,
    npc_proxy_evidence: Any,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Attach an exact NpcProxy consumer to its recovered DialogTree graph."""
    validator = "registeredDialogTreeNpcProxyConsumerComposition"
    expected_kind = "registered_dialog_tree_definition_binary_consumer_surface_exhausted"
    consumer_kinds = {
        "missionless_npc_proxy_dialog_native_consumer",
        "mission_tracked_npc_proxy_dialog_context_without_playback_owner",
    }
    tree_key = safe_key(tree_evidence.get("sceneKey")) if isinstance(
        tree_evidence, dict
    ) else ""
    consumer_key = safe_key(npc_proxy_evidence.get("sceneKey")) if isinstance(
        npc_proxy_evidence, dict
    ) else ""
    expected = {
        "sameNonEmptySceneKey": True,
        "sameNonEmptyMissionId": True,
        "sameNonEmptyDefinitionRootKey": True,
        "treeEvidenceKind": expected_kind,
        "consumerEvidenceKinds": sorted(consumer_kinds),
        "nonEmptyNpcProxyConsumers": True,
    }
    actual = {
        "treeSceneKey": tree_key,
        "consumerSceneKey": consumer_key,
        "treeMissionId": safe_key(tree_evidence.get("missionId"))
        if isinstance(tree_evidence, dict) else "",
        "consumerMissionId": safe_key(npc_proxy_evidence.get("missionId"))
        if isinstance(npc_proxy_evidence, dict) else "",
        "treeDefinitionRootKey": safe_key(
            tree_evidence.get("definitionRootKey")
        ) if isinstance(tree_evidence, dict) else "",
        "consumerDefinitionRootKey": safe_key(
            npc_proxy_evidence.get("definitionRootKey")
        ) if isinstance(npc_proxy_evidence, dict) else "",
        "treeEvidenceKind": safe_key(tree_evidence.get("evidenceKind"))
        if isinstance(tree_evidence, dict) else "",
        "consumerEvidenceKind": safe_key(
            npc_proxy_evidence.get("evidenceKind")
        ) if isinstance(npc_proxy_evidence, dict) else "",
        "consumerCount": len(npc_proxy_evidence.get("npcProxyConsumers") or [])
        if isinstance(npc_proxy_evidence, dict) else 0,
    }
    if (
        not tree_key
        or tree_key != consumer_key
        or not actual["treeMissionId"]
        or actual["treeMissionId"] != actual["consumerMissionId"]
        or not actual["treeDefinitionRootKey"]
        or actual["treeDefinitionRootKey"]
        != actual["consumerDefinitionRootKey"]
        or actual["treeEvidenceKind"] != expected_kind
        or actual["consumerEvidenceKind"] not in consumer_kinds
        or actual["consumerCount"] <= 0
    ):
        return None, {
            "validator": validator,
            "gate": "exactDefinitionConsumerIdentity",
            "storyKey": consumer_key or tree_key,
            "expected": expected,
            "actual": actual,
        }

    definition_source_files = list(dict.fromkeys([
        *_string_list(tree_evidence.get("definitionSourceFiles")),
        *_string_list(npc_proxy_evidence.get("definitionSourceFiles")),
    ]))
    source_files = list(dict.fromkeys([
        *_string_list(tree_evidence.get("sourceFiles")),
        *_string_list(npc_proxy_evidence.get("sourceFiles")),
    ]))
    original_binary_files = list(dict.fromkeys([
        *_string_list(tree_evidence.get("originalBinaryFiles")),
        *_string_list(npc_proxy_evidence.get("originalBinaryFiles")),
    ]))
    searched_consumer_kinds = list(dict.fromkeys([
        *_string_list(tree_evidence.get("searchedConsumerKinds")),
        *_string_list(npc_proxy_evidence.get("searchedConsumerKinds")),
    ]))
    return {
        **tree_evidence,
        **npc_proxy_evidence,
        "definitionRecoveryMethod": "pattern_discovered_current_original_data",
        "definitionTable": "DialogTree TextAsset",
        "consumerTable": "NpcProxyExDataTable",
        "definitionSourceFiles": definition_source_files,
        "consumerSourceFiles": _string_list(
            npc_proxy_evidence.get("definitionSourceFiles")
        ),
        "sourceFiles": source_files,
        "originalBinaryFiles": original_binary_files,
        "searchedConsumerKinds": searched_consumer_kinds,
        "dialogTreeDefinitionStatus": "exact_current_dialog_tree",
        "npcProxyConsumerStatus": "exact_current_native_selected_rows",
        "definitionNegativeConsumerMappingId": safe_key(
            tree_evidence.get("nativeMappingId")
        ),
        "nativeMappingId": safe_key(npc_proxy_evidence.get("nativeMappingId")),
        "consumerBoundary": (
            "the exact current DialogTree TextAsset proves the internal authored "
            "graph, and the hash-locked native NPC interaction selector consumes "
            "every listed missionless NpcProxyEx row; the rows expose no mission "
            "activator or quest owner"
        ),
        "orderBoundary": (
            "DialogTree nodes and options order content only inside this file, "
            "while activeCondIndex selects one proxy row; neither table order, "
            "row index, filename suffix, OCR, nor manual display order establishes "
            "cross-file mission chronology"
        ),
    }, None

def _generic_unlinked_sns_definition_facts(
    story_key: str,
    row: Any,
    sns_option_table: Any,
    sns_chat_table: Any,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str | None]:
    """Validate an SNS definition and distinguish authored mission links."""
    content = row.get("dialogContentData") if isinstance(row, dict) else None
    chat_id = safe_key(row.get("chatId")) if isinstance(row, dict) else ""
    chat = sns_chat_table.get(chat_id) if isinstance(sns_chat_table, dict) else None
    if (
        not isinstance(row, dict)
        or set(row) != SNS_DIALOG_ROW_FIELDS
        or safe_key(row.get("dialogId")) != story_key
        or not chat_id
        or not isinstance(content, dict)
        or not content
        or not isinstance(row.get("dialogType"), int)
        or isinstance(row.get("dialogType"), bool)
        or not isinstance(row.get("noticeType"), int)
        or isinstance(row.get("noticeType"), bool)
        or row.get("skipToFirstOption") not in (True, False)
        or not isinstance(sns_option_table, dict)
        or not isinstance(chat, dict)
        or set(chat) != SNS_CHAT_ROW_FIELDS
        or safe_key(chat.get("chatId")) != chat_id
    ):
        return None, {
            "validator": "genericSnsNegativeConsumer",
            "gate": "exactDialogAndChatShape",
            "storyKey": story_key,
            "expected": {
                "dialogFields": sorted(SNS_DIALOG_ROW_FIELDS),
                "nonemptyContent": True,
                "registeredChatRow": True,
                "chatFields": sorted(SNS_CHAT_ROW_FIELDS),
            },
            "actual": {
                "dialogType": type(row).__name__,
                "dialogFields": sorted(row) if isinstance(row, dict) else [],
                "chatId": chat_id,
                "chatType": type(chat).__name__,
                "chatFields": sorted(chat) if isinstance(chat, dict) else [],
            },
        }, None
    related_mission_id = safe_key(row.get("relatedMissionId"))
    content_ids: set[int] = set()
    next_ids: set[int] = set()
    pre_ids: set[int] = set()
    option_ids: set[str] = set()
    option_target_ids: set[int] = set()
    link_mission_ids: set[str] = set()
    content_params: set[str] = set()
    link_mission_ids_by_content_id: dict[str, str] = {}
    content_params_by_content_id: dict[str, list[str]] = {}
    authored_mission_link_content_ids: list[str] = []
    for serialized_id, node in content.items():
        content_id = node.get("contentId") if isinstance(node, dict) else None
        if (
            not isinstance(node, dict)
            or set(node) != SNS_CONTENT_ROW_FIELDS
            or not isinstance(content_id, int)
            or isinstance(content_id, bool)
            or str(content_id) != serialized_id
            or not isinstance(node.get("preContentId"), int)
            or isinstance(node.get("preContentId"), bool)
            or not isinstance(node.get("nextContentId"), int)
            or isinstance(node.get("nextContentId"), bool)
            or not isinstance(node.get("dialogOptionIds"), list)
            or not all(isinstance(value, str) and value for value in node["dialogOptionIds"])
            or not isinstance(node.get("contentParam"), list)
            or not all(isinstance(value, str) and value for value in node["contentParam"])
            or not isinstance(node.get("content"), dict)
            or set(node["content"]) != {"id", "text"}
            or not isinstance(node["content"].get("id"), int)
            or isinstance(node["content"].get("id"), bool)
            or not isinstance(node["content"].get("text"), str)
            or not isinstance(node.get("contentType"), int)
            or isinstance(node.get("contentType"), bool)
            or not isinstance(node.get("optionType"), int)
            or isinstance(node.get("optionType"), bool)
            or not isinstance(node.get("speaker"), str)
            or node.get("isEnd") is not (content_id < 0)
        ):
            return None, {
                "validator": "genericSnsNegativeConsumer",
                "gate": "exactContentNodeShape",
                "storyKey": story_key,
                "contentId": serialized_id,
                "expected": {
                    "fields": sorted(SNS_CONTENT_ROW_FIELDS),
                    "serializedIdMatchesContentId": True,
                    "typedReferences": True,
                },
                "actual": node if isinstance(node, dict) else node,
            }, None
        content_ids.add(content_id)
        next_ids.add(node["nextContentId"])
        pre_ids.add(node["preContentId"])
        option_ids.update(node["dialogOptionIds"])
        link_mission_id = safe_key(node.get("linkMissionId"))
        link_mission_ids.add(link_mission_id)
        content_params.update(node["contentParam"])
        if link_mission_id:
            link_mission_ids_by_content_id[serialized_id] = (
                link_mission_id
            )
        if node["contentParam"]:
            content_params_by_content_id[serialized_id] = list(
                node["contentParam"]
            )
        if (
            related_mission_id
            and node.get("contentType") == 12
            and link_mission_id == related_mission_id
            and related_mission_id in node["contentParam"]
        ):
            authored_mission_link_content_ids.append(serialized_id)
    invalid_options: list[str] = []
    for option_id in sorted(option_ids, key=natural_key):
        option = sns_option_table.get(option_id)
        if (
            not isinstance(option, dict)
            or set(option) != SNS_OPTION_ROW_FIELDS
            or safe_key(option.get("optionId")) != option_id
            or not isinstance(option.get("optionNextContentId"), int)
            or isinstance(option.get("optionNextContentId"), bool)
            or not isinstance(option.get("optionDesc"), dict)
            or set(option["optionDesc"]) != {"id", "text"}
        ):
            invalid_options.append(option_id)
            continue
        option_target_ids.add(option["optionNextContentId"])
    invalid_refs = sorted((next_ids | pre_ids) - content_ids - {0})
    invalid_option_targets = sorted(option_target_ids - content_ids)
    if (
        not any(content_id < 0 for content_id in content_ids)
        or invalid_refs
        or invalid_options
        or invalid_option_targets
    ):
        return None, {
            "validator": "genericSnsNegativeConsumer",
            "gate": "closedContentGraphAndOptions",
            "storyKey": story_key,
            "expected": {
                "negativeTerminalContentId": True,
                "allReferencesResolve": True,
                "allOptionsResolve": True,
            },
            "actual": {
                "contentIds": sorted(content_ids),
                "invalidContentReferences": invalid_refs,
                "invalidOptionIds": invalid_options,
                "invalidOptionTargetIds": invalid_option_targets,
            },
        }, None
    nonempty_links = sorted(
        ({related_mission_id} | link_mission_ids) - {""},
        key=natural_key,
    )
    if nonempty_links:
        if (
            not related_mission_id
            or set(nonempty_links) != {related_mission_id}
            or not authored_mission_link_content_ids
        ):
            return None, {
                "validator": "genericSnsNegativeConsumer",
                "gate": "coherentAuthoredMissionLink",
                "storyKey": story_key,
                "expected": {
                    "oneRelatedMissionId": True,
                    "type12LinkMissionIdMatchesRelatedMissionId": True,
                    "contentParamContainsRelatedMissionId": True,
                },
                "actual": {
                    "relatedMissionId": related_mission_id,
                    "linkMissionIdsByContentId": (
                        link_mission_ids_by_content_id
                    ),
                    "contentParamsByContentId": (
                        content_params_by_content_id
                    ),
                    "matchingContentIds": (
                        authored_mission_link_content_ids
                    ),
                },
            }, None
        return {
            "chatId": chat_id,
            "chatType": chat.get("chatType"),
            "contentIds": sorted(content_ids),
            "contentCount": len(content_ids),
            "optionIds": sorted(option_ids, key=natural_key),
            "contentParams": sorted(content_params, key=natural_key),
            "contentParamsByContentId": content_params_by_content_id,
            "relatedMissionId": related_mission_id,
            "linkMissionIdsByContentId": link_mission_ids_by_content_id,
            "snsContentIds": sorted(
                authored_mission_link_content_ids,
                key=natural_key,
            ),
            "authoredMissionLinkStatus": (
                "exact_related_type12_link_and_content_param"
            ),
        }, None, "authoredMissionLink"
    return {
        "chatId": chat_id,
        "chatType": chat.get("chatType"),
        "contentIds": sorted(content_ids),
        "contentCount": len(content_ids),
        "optionIds": sorted(option_ids, key=natural_key),
        "contentParams": sorted(content_params, key=natural_key),
        "authoredMissionLinkStatus": "absent",
    }, None, None

def _offline_radio_definition_validation_failure(
    story_key: str,
    row: Any,
    audio_stems: set[str],
) -> dict[str, Any] | None:
    """Return one bounded fail-closed RadioTable/AudioDialog diagnostic."""
    if (
        not isinstance(row, dict)
        or set(row) != OFFLINE_EXHAUSTION_RADIO_ROW_FIELDS
        or not isinstance(row.get("radioSingleDataList"), list)
        or not row["radioSingleDataList"]
    ):
        return {
            "validator": "offlineRadioDefinition",
            "gate": "exactRadioTableShape",
            "storyKey": story_key,
            "sourcePaths": ["RadioTable"],
            "expected": {
                "fields": sorted(OFFLINE_EXHAUSTION_RADIO_ROW_FIELDS),
                "nonemptyRadioSingleDataList": True,
            },
            "actual": {
                "type": type(row).__name__,
                "fields": sorted(row) if isinstance(row, dict) else [],
                "radioSingleDataCount": (
                    len(row.get("radioSingleDataList") or [])
                    if isinstance(row, dict) else 0
                ),
            },
        }
    row_audio_ids = {
        safe_key(line.get("audioOverride"))
        for line in row["radioSingleDataList"]
        if isinstance(line, dict) and safe_key(line.get("audioOverride"))
    }
    if len(row_audio_ids) != len(row["radioSingleDataList"]):
        return {
            "validator": "offlineRadioDefinition",
            "gate": "everyLineHasExactAudioOverride",
            "storyKey": story_key,
            "sourcePaths": ["RadioTable"],
            "expected": {"audioOverrideCount": len(row["radioSingleDataList"])},
            "actual": {"audioOverrideIds": sorted(row_audio_ids)},
        }
    expected_variants = {
        safe_key(audio_id): tuple(safe_key(value) for value in variants)
        for audio_id, variants in (
            OFFLINE_EXHAUSTION_RADIO_AUDIO_VARIANTS.get(story_key, {})
        ).items()
    }
    expected_missing = set(
        OFFLINE_EXHAUSTION_RADIO_MISSING_AUDIO_IDS.get(story_key, ())
    )
    actual_base_absent = row_audio_ids - audio_stems
    actual_variants = {
        audio_id: sorted(
            stem for stem in audio_stems if stem.startswith(f"{audio_id}_")
        )
        for audio_id in expected_variants
    }
    if (
        set(expected_variants) & expected_missing
        or actual_base_absent != set(expected_variants) | expected_missing
        or any(
            not variants
            or any(not value.startswith(f"{audio_id}_") for value in variants)
            or set(variants) != set(actual_variants[audio_id])
            for audio_id, variants in expected_variants.items()
        )
        or any(
            any(stem.startswith(f"{audio_id}_") for stem in audio_stems)
            for audio_id in expected_missing
        )
    ):
        return {
            "validator": "offlineRadioDefinition",
            "gate": "exactAudioDialogMembership",
            "storyKey": story_key,
            "sourcePaths": ["RadioTable", "AudioDialog"],
            "expected": {
                "baseAbsentAudioIds": sorted(
                    set(expected_variants) | expected_missing
                ),
                "missingAudioIds": sorted(expected_missing),
                "audioVariants": {
                    key: list(values) for key, values in expected_variants.items()
                },
            },
            "actual": {
                "rowAudioIds": sorted(row_audio_ids),
                "baseAbsentAudioIds": sorted(actual_base_absent),
                "audioVariants": actual_variants,
            },
        }
    return None

def project_authored_story_content_keys(
    index_payload: Any,
    conversation_dir: Path,
    *,
    source_root: Path = ROOT,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Validate explicit project-authored Story provenance, without key lists.

    Classification requires the index and generated conversation to carry the
    same provenance record and requires its repository source file to exist.
    A malformed marker fails closed: it remains outside this exclusion map and
    is reported with bounded expected/actual diagnostics.
    """
    entries = (
        index_payload.get("entries")
        if isinstance(index_payload, dict) else None
    )
    found: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        provenance = entry.get("provenance")
        if (
            not isinstance(provenance, dict)
            or safe_key(provenance.get("scope")) != "project_authored"
        ):
            continue
        story_key = safe_key(entry.get("k"))
        mission_id = safe_key(entry.get("m"))
        story_kind = safe_key(entry.get("d"))
        source_file = safe_key(provenance.get("sourceFile"))
        source_path = Path(source_file) if source_file else Path()
        resolved_source = source_root / source_path
        conversation_path = conversation_dir / f"{story_key}.json"
        conversation = read_json(conversation_path, {})
        conversation_provenance = (
            conversation.get("provenance")
            if isinstance(conversation, dict) else None
        )
        valid_relative_source = bool(
            source_file
            and not source_path.is_absolute()
            and ".." not in source_path.parts
        )
        valid = (
            bool(story_key)
            and bool(mission_id)
            and bool(story_kind)
            and safe_key(provenance.get("purpose"))
            and safe_key(provenance.get("producer"))
            and provenance.get("gameDataEvidence") is False
            and valid_relative_source
            and resolved_source.is_file()
            and conversation_path.is_file()
            and safe_key(conversation.get("key")) == story_key
            and safe_key(conversation.get("mission")) == mission_id
            and conversation_provenance == provenance
        )
        if not valid:
            failures.append({
                "validator": "projectAuthoredStoryProvenance",
                "gate": "matchingGeneratedEntryAndExistingSource",
                "storyKey": story_key,
                "missionId": mission_id,
                "sourcePaths": [
                    source_file,
                    conversation_path.as_posix(),
                ],
                "expected": {
                    "nonemptyStoryAndMission": True,
                    "nonemptyStoryKind": True,
                    "scope": "project_authored",
                    "nonemptyPurposeAndProducer": True,
                    "gameDataEvidence": False,
                    "safeExistingRepositorySource": True,
                    "matchingConversationProvenance": True,
                },
                "actual": {
                    "storyKey": story_key,
                    "missionId": mission_id,
                    "storyKind": story_kind,
                    "provenance": provenance,
                    "validRelativeSource": valid_relative_source,
                    "sourceExists": resolved_source.is_file(),
                    "conversationExists": conversation_path.is_file(),
                    "conversationKey": safe_key(
                        conversation.get("key")
                        if isinstance(conversation, dict) else ""
                    ),
                    "conversationMission": safe_key(
                        conversation.get("mission")
                        if isinstance(conversation, dict) else ""
                    ),
                    "conversationProvenance": conversation_provenance,
                },
            })
            continue
        found[story_key] = {
            "evidenceKind": "project_authored_story_content",
            "content": safe_key(provenance.get("purpose")),
            "storyKind": story_kind,
            "sourceScope": "project_authored",
            "producer": safe_key(provenance.get("producer")),
            "sourceFiles": [source_file],
            "sourceSha256": {
                source_file: _sha256_file(resolved_source),
            },
        }
    return found, {
        "validator": "project_authored_story_provenance_v1",
        "status": "validation_failed" if failures else "validated",
        "qualifiedStoryKeys": sorted(found, key=natural_key),
        "validationFailures": failures,
        "graphEffect": "none",
    }

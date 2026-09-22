"""Audit every current JsonData logical file against the authenticated VFS ledger.

This is the family registry for the JsonData block.  It proves that the
structured export is a byte-for-byte view of every current logical file, then
routes only the families with maintained readers.  A path or MemoryPack member
count never promotes an otherwise unknown payload.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import tempfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from scripts.game_data.animation_config_binary import (
    AnimationConfigFramingError,
    frame_animation_config,
)
from scripts.game_data.aether_energy_lock_binary import (
    AetherEnergyLockDecodeError,
    decode_aether_energy_lock_table,
)
from scripts.game_data.atmospheric_npc_binary import (
    AtmosphericNpcFramingError,
    frame_atmospheric_npc_table,
)
from scripts.game_data.char_interact_perform_binary import (
    CharInteractPerformDecodeError,
    decode_char_interact_complete_frame,
    frame_char_interact_prefix,
)
from scripts.game_data.interactive_binary import (
    InteractiveBinaryDecodeError,
    decode_interactive_table,
    decode_model_view_state_controller,
)
from scripts.game_data.leveldata_binary import (
    LevelDataTopLevelFramingError,
    frame_leveldata_airwalls_prefix,
    frame_leveldata_empty_tail,
    frame_leveldata_named_prefix,
    frame_leveldata_terminal_suffix,
)
from scripts.game_data.levelconfig_binary import LevelConfigDecodeError, decode_level_config
from scripts.game_data.levelscript_binary import (
    LevelScriptTopLevelFramingError,
    frame_levelscript_action_map_named_prefix,
    frame_levelscript_current_action_sequence_leader_enter,
    frame_levelscript_single_call_server_leader_enter,
    frame_levelscript_empty_action_map_sequential,
    frame_levelscript_null_action_map_sequential,
    frame_levelscript_empty_action_map_prefix,
    frame_levelscript_empty_action_map_top_level,
    frame_levelscript_terminal_suffix,
)
from scripts.game_data.levelscript_template_binary import (
    LevelScriptTemplateFramingError,
    frame_levelscript_template,
)
from scripts.game_data.gpu_ui_binary import (
    GpuUiFramingError,
    decode_gpu_ui_root16,
    decode_damage_text,
    frame_damage_text,
    frame_gpu_ui_root16_prefix,
)
from scripts.game_data.gameplay_compact_binary import (
    GameplayCompactDecodeError,
    decode_mission_area_table,
    frame_subgame_table,
    frame_world_entity_registry,
)
from scripts.game_data.gold_coin_config_json import (
    GoldCoinConfigDecodeError,
    decode_gold_coin_config,
    is_gold_coin_config_path,
)
from scripts.game_data.gameplay_config_json import (
    GameplayConfigJsonDecodeError,
    decode_compact_gameplay_config_json,
    is_compact_gameplay_config_json_path,
)
from scripts.game_data.gameplay_config_polymorphic import (
    GameplayConfigPolymorphicDecodeError,
    decode_polymorphic_gameplay_config,
    is_polymorphic_gameplay_config_path,
)
from scripts.game_data.jsondata_text_schema import (
    JsonDataTextSchemaDecodeError,
    decode_named_jsondata_text,
    is_named_jsondata_text_path,
)
from scripts.game_data.level_mount_point_json import (
    LevelMountPointJsonDecodeError,
    decode_level_mount_points,
    is_level_mount_point_path,
)
from scripts.game_data.matrix_shockwave_binary import (
    MatrixShockWaveDecodeError,
    decode_matrix_shockwave_table,
)
from scripts.game_data.map_config_json import (
    MapConfigDecodeError,
    decode_map_config,
    is_map_config_path,
)
from scripts.game_data.mission_runtime_meta import (
    MissionRuntimeMetaDecodeError,
    decode_mission_runtime_meta,
    is_mission_runtime_meta_path,
)
from scripts.game_data.mission_runtime_main import (
    MissionRuntimeMainDecodeError,
    decode_mission_runtime_main,
    is_mission_runtime_main_path,
)
from scripts.game_data.memorypack.corpus_gate import (
    DEFAULT_LEDGER,
    DEFAULT_OUTER,
    CensusGateError,
    _guard_output_path,
    _read_outer_and_ledger,
)
from scripts.game_data.memorypack.lipsync import (
    LipSyncDecodeError,
    decode_lipsync_memorypack,
)
from scripts.game_data.memorypack.interactive import (
    decode_interactive_template_memorypack,
)
from scripts.game_data.memorypack.tables import (
    BAMBOO_RAFT_TASK_TABLE_REL,
    DAMAGE_TEXT_REL,
    DIALOG_ID_TABLE_REL,
    decode_bamboo_raft_task_table_memorypack,
    decode_dialog_id_table_memorypack,
)
from scripts.game_data.navmesh_binary import (
    NavMeshDecodeError,
    decode_luna_area,
    decode_navmesh_state_container,
)
from scripts.game_data.npc_prefab_info import (
    NpcPrefabInfoDecodeError,
    decode_npc_prefab_info,
    is_npc_prefab_info_path,
)
from scripts.game_data.npc_catalog_json import (
    NpcCatalogDecodeError,
    decode_npc_catalog,
    is_npc_catalog_path,
)
from scripts.game_data.ui_level_map_load_config import (
    UiLevelMapLoadConfigDecodeError,
    decode_ui_level_map_load_config,
    is_ui_level_map_load_config_path,
)
from scripts.game_data.memorypack.npc_montage import (
    NpcMontageFramingError,
    frame_npc_montage,
)
from scripts.game_data.spawner_binary import (
    SpawnerEnemyLibraryDecodeError,
    SpawnerWaveDecodeError,
    decode_spawner_enemy_library,
    decode_spawner_named_prefix,
    decode_spawner_wave_map,
    decode_spawner_wave_map_sequential,
)
from scripts.game_data.teleport_validation_binary import (
    TeleportValidationDecodeError,
    decode_teleport_validation_table,
)
from scripts.common import canonical_json_sha256
from scripts.repo_paths import REPO_ROOT


REPORT_FORMAT = "endfield-jsondata-current-corpus-v1"
DEFAULT_EXPORT = REPO_ROOT / "export_full/game/Json"
DEFAULT_JSON = REPO_ROOT / "reports/animestudio/jsondata_current_latest.json"
DEFAULT_MD = REPO_ROOT / "reports/animestudio/jsondata_current_latest.md"
DEFAULT_FILES = REPO_ROOT / "reports/animestudio/jsondata_current_files_latest.jsonl.gz"
DEFAULT_BUFF_REPORT = REPO_ROOT / "reports/animestudio/buffdata_current_latest.json"
DEFAULT_SKILL_REPORT = REPO_ROOT / "reports/animestudio/skilldata_current_latest.json"
JSONDATA_PREFIX = PurePosixPath("Data/Json")

FAMILY_REPORTS = {
    "BuffData": {
        "format": "animestudio-buffdata-current-vfs-corpus",
        "reader": "scripts.game_data.memorypack.buff_corpus",
        "status": "bounded_partial",
    },
    "SkillData": {
        "format": "animestudio-skilldata-current-vfs-corpus",
        "reader": "scripts.game_data.memorypack.skill_corpus",
        "status": "bounded_partial",
    },
}


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _safe_export_path(export_root: Path, virtual_path: str) -> tuple[Path, str, str]:
    logical = PurePosixPath(virtual_path)
    if logical.is_absolute() or ".." in logical.parts or logical.parts[:2] != JSONDATA_PREFIX.parts:
        raise ValueError(f"unsafe JsonData virtual path: {virtual_path!r}")
    relative = PurePosixPath(*logical.parts[2:])
    if not relative.parts:
        raise ValueError(f"empty JsonData relative path: {virtual_path!r}")
    candidate = (export_root / Path(*relative.parts)).resolve()
    if not candidate.is_relative_to(export_root):
        raise ValueError(f"JsonData export path escapes root: {virtual_path!r}")
    family = relative.parts[0] if len(relative.parts) > 1 else relative.name
    return candidate, relative.as_posix(), family


def _classify_json(data: bytes) -> tuple[bool, str | None]:
    stripped = data.lstrip()
    if stripped[:1] not in (b"{", b"["):
        return False, None
    try:
        decoded = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False, None
    return True, "object" if isinstance(decoded, dict) else "array" if isinstance(decoded, list) else "scalar"


def _load_family_evidence(
    path: Path,
    *,
    family: str,
    expected_input_set_sha256: str,
    expected_paths: set[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    contract = FAMILY_REPORTS[family]
    with path.open("r", encoding="utf-8") as handle:
        report = json.load(handle)
    if (
        report.get("format") != contract["format"]
        or report.get("schemaVersion") != 1
        or report.get("status") != "complete"
        or report.get("publicationEligible") is not True
        or report.get("inputSetSha256") != expected_input_set_sha256
        or report.get("wholeSchemaExact") is not False
    ):
        raise ValueError(f"{family} evidence report is incomplete, stale, or has an unsupported contract")
    rows = report.get("files")
    if not isinstance(rows, list):
        raise ValueError(f"{family} evidence report has no file rows")
    if family == "BuffData":
        identity_rows = [
            {"identity": row.get("identity"), "logicalSha256": row.get("logicalSha256")}
            for row in rows
        ]
    else:
        identity_fields = (
            "virtualPath", "blockTypeValue", "length", "logicalMd5", "logicalSha256",
            "physicalChunkPath", "physicalChunkSource", "metadataProvenance", "overlayState",
            "chunkOverlayState", "physicalOffset", "encrypted",
        )
        try:
            identity_rows = [{key: row[key] for key in identity_fields} for row in rows]
        except KeyError as exc:
            raise ValueError(f"SkillData evidence identity is incomplete: {exc}") from exc
    if canonical_json_sha256(identity_rows) != report.get("identitySetSha256"):
        raise ValueError(f"{family} evidence identity-set digest does not match its file rows")

    evidence: dict[str, dict[str, Any]] = {}
    for row in rows:
        identity = row.get("identity") if family == "BuffData" else row
        if not isinstance(identity, dict):
            raise ValueError(f"{family} evidence row has no identity")
        virtual_path = identity.get("virtualPath")
        if not isinstance(virtual_path, str) or virtual_path in evidence:
            raise ValueError(f"{family} evidence has an invalid or duplicate path: {virtual_path!r}")
        if (
            identity.get("inputSetSha256") != expected_input_set_sha256
            or identity.get("blockName") != "JsonData"
            or identity.get("blockTypeValue") != 19
            or (
                row.get("wholeSchemaExact") is not False
                and not (
                    family == "SkillData"
                    and row.get("wholeSchemaExact") is True
                    and row.get("boundaryClass") == "exact-closed"
                    and row.get("coverageStatus")
                    in (
                        "verified-whole-schema-exact-empty-action-group-profile",
                        "verified-whole-schema-exact-timeline-play-animation-profile",
                        "verified-whole-schema-exact-timeline-play-animation-step-profile",
                        "verified-whole-schema-exact-timeline-create-buff-profile",
                        "verified-whole-schema-exact-timeline-shared-sequence-profile",
                    )
                )
            )
        ):
            raise ValueError(f"{family} evidence row is not current bounded JsonData: {virtual_path!r}")
        if family == "BuffData":
            if (
                identity.get("status") != "verified"
                or identity.get("boundaryStatus") != "boundary_verified"
                or row.get("eventPrefixStatus") != "success"
                or row.get("coverageStatus") != "unique"
            ):
                raise ValueError(f"BuffData evidence row lacks its proven event prefix: {virtual_path!r}")
            logical_md5 = identity.get("recomputedFileDataMd5")
            detail = {
                "boundaryClass": row.get("boundaryClass"),
                "coverageStatus": row.get("coverageStatus"),
                "eventPrefixStatus": row.get("eventPrefixStatus"),
                "rootContinuationStatus": row.get("rootContinuationStatus"),
                "namedOuterFrameStatus": row.get("namedOuterFrameStatus"),
            }
        else:
            prefix_ok = bool(row.get("commonPrefixFraming", {}).get("provenPrefixByteLength"))
            ambiguous = (
                row.get("boundaryClass") == "ambiguous"
                and row.get("coverageStatus") == "ambiguous-disjoint-independent-ranges"
            )
            selected = (
                row.get("boundaryClass") == "structural-prefix"
                and row.get("coverageStatus")
                == "verified-terminal-selection-disjoint-independent-ranges"
                and row.get("terminalSelection", {}).get("status")
                == "verified-native-reader-alignment"
                and row.get("terminalSelection", {}).get("encoding")
                == "one-member-wrapper"
                and row.get("terminalSelection", {}).get("fieldStartIndex") == 43
                and row.get("terminalSelection", {}).get("fieldEndIndex") == 47
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is False
            )
            exact_empty = (
                row.get("boundaryClass") == "exact-closed"
                and row.get("coverageStatus")
                == "verified-whole-schema-exact-empty-action-group-profile"
                and row.get("wholeSchemaExact") is True
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is True
                and row.get("emptyActionGroupProfile", {}).get("status")
                == "verified-exact-through-field-42"
                and not row.get("opaqueByteRanges")
            )
            exact_timeline = (
                row.get("boundaryClass") == "exact-closed"
                and row.get("coverageStatus")
                == "verified-whole-schema-exact-timeline-play-animation-profile"
                and row.get("wholeSchemaExact") is True
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is True
                and (row.get("timelinePlayAnimationProfile") or {}).get("status")
                == "verified-exact-first-timeline-play-animation-record"
                and (row.get("timelinePlayAnimationProfile") or {})
                .get("topLevelContinuation", {}).get("status")
                == "verified-exact-through-field-42"
                and not row.get("opaqueByteRanges")
            )
            partial_empty = (
                row.get("boundaryClass") == "structural-prefix"
                and row.get("coverageStatus")
                == "verified-empty-action-group-named-prefix-and-terminal"
                and row.get("wholeSchemaExact") is False
                and row.get("emptyActionGroupProfile", {}).get("status")
                == "verified-exact-through-field-41"
            )
            action_group = row.get("actionGroupPrefix", {})
            named_action_group = (
                row.get("boundaryClass") == "structural-prefix"
                and row.get("coverageStatus")
                == "verified-action-group-named-prefix-and-terminal"
                and row.get("wholeSchemaExact") is False
                and row.get("terminalSelection", {}).get("status")
                == "verified-native-reader-alignment"
                and row.get("terminalSelection", {}).get("encoding")
                == "one-member-wrapper"
                and row.get("terminalSelection", {}).get("fieldStartIndex") == 43
                and row.get("terminalSelection", {}).get("fieldEndIndex") == 47
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is False
                and action_group.get("status") == "verified-named-prefix"
                and action_group.get("fieldIndex") == 0
                and action_group.get("fieldName") == "actionGroupData"
                and action_group.get("memberOrder")
                == ["passiveEventActions", "timelineActions"]
                and action_group.get("parserCursor") in (6, 10)
                and action_group.get("byteLength") == action_group.get("parserCursor") - 1
                and action_group.get("openChildList")
                in ("passiveEventActions", "timelineActions")
                and action_group.get("wholeFieldExact") is False
            )
            timeline_play_animation = row.get("timelinePlayAnimationProfile") or {}
            named_timeline_play_animation = (
                row.get("boundaryClass") == "structural-prefix"
                and row.get("coverageStatus")
                == "verified-timeline-play-animation-named-prefix-and-terminal"
                and row.get("wholeSchemaExact") is False
                and row.get("terminalSelection", {}).get("status")
                == "verified-native-reader-alignment"
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is False
                and timeline_play_animation.get("status")
                == "verified-exact-first-timeline-play-animation-record"
                and type(timeline_play_animation.get("parserCursor")) is int
                and timeline_play_animation.get("parserCursor") > 10
                and timeline_play_animation.get("newNamedBytesAfterPriorPrefix")
                == timeline_play_animation.get("parserCursor") - 10
                and timeline_play_animation.get("wholeTimelineListExact") is False
            )
            timeline_play_animation_step = (
                row.get("timelinePlayAnimationStepProfile") or {}
            )
            step_record = timeline_play_animation_step.get("firstTimelineAction") or {}
            step_sequence = step_record.get("sequenceActionData") or {}
            step_actions = step_sequence.get("actionData") or []
            step_profile_exact = (
                timeline_play_animation_step.get("status")
                == "verified-exact-first-timeline-play-animation-step-record"
                and type(timeline_play_animation_step.get("parserCursor")) is int
                and timeline_play_animation_step.get("parserCursor") > 10
                and timeline_play_animation_step.get("newNamedBytesAfterPriorPrefix")
                == timeline_play_animation_step.get("parserCursor") - 10
                and step_record.get("wholeRecordExact") is True
                and step_sequence.get("actionDataCount") == 1
                and isinstance(step_actions, list)
                and len(step_actions) == 1
                and step_actions[0].get("tag") == 0x0116
                and step_actions[0].get("memberCount") == 30
                and step_actions[0].get("wholeActionExact") is True
            )
            named_timeline_play_animation_step = (
                row.get("boundaryClass") == "structural-prefix"
                and row.get("coverageStatus")
                == "verified-timeline-play-animation-step-named-prefix-and-terminal"
                and row.get("wholeSchemaExact") is False
                and row.get("terminalSelection", {}).get("status")
                == "verified-native-reader-alignment"
                and row.get("terminalSelection", {}).get("encoding")
                == "one-member-wrapper"
                and row.get("terminalSelection", {}).get("fieldStartIndex") == 43
                and row.get("terminalSelection", {}).get("fieldEndIndex") == 47
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is False
                and row.get("parserCursor")
                == timeline_play_animation_step.get("parserCursor")
                and timeline_play_animation_step.get("wholeTimelineListExact") is False
                and timeline_play_animation_step.get("wholeActionGroupDataExact") is False
                and step_profile_exact
            )
            exact_timeline_play_animation_step = (
                row.get("boundaryClass") == "exact-closed"
                and row.get("coverageStatus")
                == "verified-whole-schema-exact-timeline-play-animation-step-profile"
                and row.get("wholeSchemaExact") is True
                and row.get("terminalSelection", {}).get("status")
                == "verified-native-reader-alignment"
                and row.get("terminalSelection", {}).get("encoding")
                == "one-member-wrapper"
                and row.get("terminalSelection", {}).get("fieldStartIndex") == 43
                and row.get("terminalSelection", {}).get("fieldEndIndex") == 47
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is True
                and timeline_play_animation_step.get("wholeTimelineListExact") is True
                and timeline_play_animation_step.get("wholeActionGroupDataExact") is True
                and timeline_play_animation_step.get("topLevelContinuation", {}).get(
                    "status"
                ) == "verified-exact-through-field-42"
                and step_profile_exact
                and not row.get("opaqueByteRanges")
            )
            timeline_create_buff = row.get("timelineCreateBuffProfile") or {}
            create_buff_record = timeline_create_buff.get("firstTimelineAction") or {}
            create_buff_sequence = create_buff_record.get("sequenceActionData") or {}
            create_buff_actions = create_buff_sequence.get("actionData") or []
            create_buff_action_exact = (
                type(timeline_create_buff.get("parserCursor")) is int
                and timeline_create_buff.get("parserCursor") > 10
                and timeline_create_buff.get("newNamedBytesAfterPriorPrefix")
                == timeline_create_buff.get("parserCursor") - 10
                and isinstance(create_buff_actions, list)
                and len(create_buff_actions) == 1
                and create_buff_actions[0].get("tag") == 0x0092
                and create_buff_actions[0].get("memberCount") == 19
                and create_buff_actions[0].get("wholeActionExact") is True
            )
            named_timeline_create_buff_action = (
                row.get("boundaryClass") == "structural-prefix"
                and row.get("coverageStatus")
                == "verified-timeline-create-buff-first-action-named-prefix-and-terminal"
                and row.get("wholeSchemaExact") is False
                and row.get("terminalSelection", {}).get("status")
                == "verified-native-reader-alignment"
                and row.get("terminalSelection", {}).get("encoding")
                == "one-member-wrapper"
                and row.get("terminalSelection", {}).get("fieldStartIndex") == 43
                and row.get("terminalSelection", {}).get("fieldEndIndex") == 47
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is False
                and row.get("parserCursor") == timeline_create_buff.get("parserCursor")
                and timeline_create_buff.get("status")
                == "verified-exact-first-timeline-create-buff-action"
                and create_buff_sequence.get("actionDataCount", 0) > 1
                and create_buff_sequence.get("wholeListExact") is False
                and create_buff_record.get("wholeRecordExact") is False
                and timeline_create_buff.get("wholeFirstTimelineActionExact") is False
                and timeline_create_buff.get("wholeTimelineListExact") is False
                and timeline_create_buff.get("wholeActionGroupDataExact") is False
                and create_buff_action_exact
            )
            named_timeline_create_buff_record = (
                row.get("boundaryClass") == "structural-prefix"
                and row.get("coverageStatus")
                == "verified-timeline-create-buff-first-record-named-prefix-and-terminal"
                and row.get("wholeSchemaExact") is False
                and row.get("terminalSelection", {}).get("status")
                == "verified-native-reader-alignment"
                and row.get("terminalSelection", {}).get("encoding")
                == "one-member-wrapper"
                and row.get("terminalSelection", {}).get("fieldStartIndex") == 43
                and row.get("terminalSelection", {}).get("fieldEndIndex") == 47
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is False
                and row.get("parserCursor") == timeline_create_buff.get("parserCursor")
                and timeline_create_buff.get("status")
                == "verified-exact-first-timeline-create-buff-record"
                and create_buff_sequence.get("actionDataCount") == 1
                and create_buff_sequence.get("wholeListExact") is True
                and create_buff_record.get("wholeRecordExact") is True
                and timeline_create_buff.get("wholeFirstTimelineActionExact") is True
                and timeline_create_buff.get("wholeTimelineListExact") is False
                and timeline_create_buff.get("wholeActionGroupDataExact") is False
                and create_buff_action_exact
            )
            exact_timeline_create_buff = (
                row.get("boundaryClass") == "exact-closed"
                and row.get("coverageStatus")
                == "verified-whole-schema-exact-timeline-create-buff-profile"
                and row.get("wholeSchemaExact") is True
                and row.get("terminalSelection", {}).get("status")
                == "verified-native-reader-alignment"
                and row.get("terminalSelection", {}).get("encoding")
                == "one-member-wrapper"
                and row.get("terminalSelection", {}).get("fieldStartIndex") == 43
                and row.get("terminalSelection", {}).get("fieldEndIndex") == 47
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is True
                and timeline_create_buff.get("status")
                == "verified-exact-first-timeline-create-buff-record"
                and create_buff_sequence.get("actionDataCount") == 1
                and create_buff_sequence.get("wholeListExact") is True
                and create_buff_record.get("wholeRecordExact") is True
                and timeline_create_buff.get("wholeFirstTimelineActionExact") is True
                and timeline_create_buff.get("wholeTimelineListExact") is True
                and timeline_create_buff.get("wholeActionGroupDataExact") is True
                and timeline_create_buff.get("topLevelContinuation", {}).get("status")
                == "verified-exact-through-field-42"
                and create_buff_action_exact
                and not row.get("opaqueByteRanges")
            )
            timeline_find_target = row.get("timelineFindTargetProfile") or {}
            find_target_record = timeline_find_target.get("firstTimelineAction") or {}
            find_target_sequence = find_target_record.get("sequenceActionData") or {}
            find_target_actions = find_target_sequence.get("actionData") or []
            named_timeline_find_target = (
                row.get("boundaryClass") == "structural-prefix"
                and row.get("coverageStatus")
                == "verified-timeline-find-target-named-prefix-and-terminal"
                and row.get("wholeSchemaExact") is False
                and row.get("terminalSelection", {}).get("status")
                == "verified-native-reader-alignment"
                and row.get("terminalSelection", {}).get("encoding")
                == "one-member-wrapper"
                and row.get("terminalSelection", {}).get("fieldStartIndex") == 43
                and row.get("terminalSelection", {}).get("fieldEndIndex") == 47
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is False
                and timeline_find_target.get("status")
                == "verified-exact-first-timeline-find-target-record"
                and type(timeline_find_target.get("parserCursor")) is int
                and timeline_find_target.get("parserCursor") > 10
                and row.get("parserCursor") == timeline_find_target.get("parserCursor")
                and timeline_find_target.get("newNamedBytesAfterPriorPrefix")
                == timeline_find_target.get("parserCursor") - 10
                and timeline_find_target.get("wholeTimelineListExact") is False
                and find_target_record.get("wholeRecordExact") is True
                and find_target_sequence.get("actionDataCount") == 1
                and isinstance(find_target_actions, list)
                and len(find_target_actions) == 1
                and find_target_actions[0].get("tag") == 0x00B2
                and find_target_actions[0].get("memberCount") == 18
                and find_target_actions[0].get("wholeActionExact") is True
            )
            timeline_continuous_find_target = (
                row.get("timelineContinuousFindTargetProfile") or {}
            )
            continuous_record = timeline_continuous_find_target.get(
                "firstTimelineAction"
            ) or {}
            continuous_sequence = continuous_record.get("sequenceActionData") or {}
            continuous_actions = continuous_sequence.get("actionData") or []
            named_timeline_continuous_find_target = (
                row.get("boundaryClass") == "structural-prefix"
                and row.get("coverageStatus")
                == "verified-timeline-continuous-find-target-named-prefix-and-terminal"
                and row.get("wholeSchemaExact") is False
                and row.get("terminalSelection", {}).get("status")
                == "verified-native-reader-alignment"
                and row.get("terminalSelection", {}).get("encoding")
                == "one-member-wrapper"
                and row.get("terminalSelection", {}).get("fieldStartIndex") == 43
                and row.get("terminalSelection", {}).get("fieldEndIndex") == 47
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is False
                and timeline_continuous_find_target.get("status")
                == "verified-exact-first-timeline-continuous-find-target-record"
                and type(timeline_continuous_find_target.get("parserCursor")) is int
                and timeline_continuous_find_target.get("parserCursor") > 10
                and row.get("parserCursor")
                == timeline_continuous_find_target.get("parserCursor")
                and timeline_continuous_find_target.get("newNamedBytesAfterPriorPrefix")
                == timeline_continuous_find_target.get("parserCursor") - 10
                and timeline_continuous_find_target.get("wholeTimelineListExact") is False
                and continuous_record.get("wholeRecordExact") is True
                and continuous_sequence.get("actionDataCount") == 1
                and isinstance(continuous_actions, list)
                and len(continuous_actions) == 1
                and continuous_actions[0].get("tag") == 0x008A
                and continuous_actions[0].get("memberCount") == 19
                and continuous_actions[0].get("wholeActionExact") is True
            )
            timeline_shared_sequence = row.get("timelineSharedSequenceProfile") or {}
            shared_record = timeline_shared_sequence.get("firstTimelineAction") or {}
            shared_actions = shared_record.get("actionData") or []
            shared_profile_exact = (
                timeline_shared_sequence.get("status")
                == "verified-exact-first-timeline-shared-sequence-record"
                and type(timeline_shared_sequence.get("parserCursor")) is int
                and timeline_shared_sequence.get("parserCursor") > 10
                and timeline_shared_sequence.get("newNamedBytesAfterPriorPrefix")
                == timeline_shared_sequence.get("parserCursor") - 10
                and shared_record.get("wholeRecordExact") is True
                and isinstance(shared_actions, list)
                and bool(shared_actions)
                and all(
                    type(action.get("tag")) is int
                    and isinstance(action.get("typeName"), str)
                    and action.get("typeName")
                    and type(action.get("memberCount")) is int
                    and action.get("structurallyExact") is True
                    and type(action.get("start")) is int
                    and type(action.get("end")) is int
                    and action["end"] > action["start"]
                    for action in shared_actions
                )
            )
            named_timeline_shared_sequence = (
                row.get("boundaryClass") == "structural-prefix"
                and row.get("coverageStatus")
                == "verified-timeline-shared-sequence-named-prefix-and-terminal"
                and row.get("wholeSchemaExact") is False
                and row.get("terminalSelection", {}).get("status")
                == "verified-native-reader-alignment"
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is False
                and row.get("parserCursor")
                == timeline_shared_sequence.get("parserCursor")
                and timeline_shared_sequence.get("wholeTimelineListExact") is False
                and timeline_shared_sequence.get("wholeActionGroupDataExact") is False
                and shared_profile_exact
            )
            exact_timeline_shared_sequence = (
                row.get("boundaryClass") == "exact-closed"
                and row.get("coverageStatus")
                == "verified-whole-schema-exact-timeline-shared-sequence-profile"
                and row.get("wholeSchemaExact") is True
                and row.get("terminalSelection", {}).get("status")
                == "verified-native-reader-alignment"
                and row.get("terminalSelection", {}).get("wholeSchemaExact") is True
                and timeline_shared_sequence.get("wholeTimelineListExact") is True
                and timeline_shared_sequence.get("wholeActionGroupDataExact") is True
                and timeline_shared_sequence.get("topLevelContinuation", {}).get(
                    "status"
                ) == "verified-exact-through-field-42"
                and shared_profile_exact
                and not row.get("opaqueByteRanges")
            )
            if not prefix_ok or not (
                ambiguous
                or selected
                or exact_empty
                or exact_timeline
                or partial_empty
                or named_action_group
                or named_timeline_play_animation
                or named_timeline_play_animation_step
                or exact_timeline_play_animation_step
                or named_timeline_create_buff_action
                or named_timeline_create_buff_record
                or exact_timeline_create_buff
                or named_timeline_find_target
                or named_timeline_continuous_find_target
                or named_timeline_shared_sequence
                or exact_timeline_shared_sequence
            ):
                raise ValueError(f"SkillData evidence row lacks its bounded structural contract: {virtual_path!r}")
            logical_md5 = row.get("logicalMd5")
            detail = {
                "boundaryClass": row.get("boundaryClass"),
                "coverageStatus": row.get("coverageStatus"),
                "provenPrefixByteLength": row["commonPrefixFraming"]["provenPrefixByteLength"],
                "terminalCandidateCount": len(row.get("candidateCoverage", [])),
                "terminalSelection": row.get("terminalSelection"),
                "wholeSchemaExact": row.get("wholeSchemaExact"),
                "emptyActionGroupProfileStatus": row.get("emptyActionGroupProfile", {}).get("status"),
                "actionGroupPrefix": action_group if named_action_group else None,
                "timelinePlayAnimationProfile": (
                    timeline_play_animation
                    if named_timeline_play_animation or exact_timeline
                    else None
                ),
                "timelinePlayAnimationStepProfile": (
                    timeline_play_animation_step
                    if named_timeline_play_animation_step
                    or exact_timeline_play_animation_step
                    else None
                ),
                "timelineCreateBuffProfile": (
                    timeline_create_buff
                    if named_timeline_create_buff_action
                    or named_timeline_create_buff_record
                    or exact_timeline_create_buff
                    else None
                ),
                "timelineFindTargetProfile": (
                    timeline_find_target if named_timeline_find_target else None
                ),
                "timelineContinuousFindTargetProfile": (
                    timeline_continuous_find_target
                    if named_timeline_continuous_find_target
                    else None
                ),
                "timelineSharedSequenceProfile": (
                    timeline_shared_sequence
                    if named_timeline_shared_sequence
                    or exact_timeline_shared_sequence
                    else None
                ),
            }
        evidence[virtual_path] = {
            "length": identity.get("length"),
            "logicalMd5": logical_md5,
            "logicalSha256": row.get("logicalSha256"),
            "detail": detail,
        }

    if set(evidence) != expected_paths:
        missing = sorted(expected_paths - set(evidence))
        extra = sorted(set(evidence) - expected_paths)
        raise ValueError(
            f"{family} evidence paths do not match the current ledger; "
            f"missing={missing[:1]!r}; extra={extra[:1]!r}"
        )
    summary = report.get("summary", {})
    if summary.get("filesSelected") != len(expected_paths) or summary.get("filesSucceeded") != len(expected_paths):
        raise ValueError(f"{family} evidence summary does not match its file rows")
    metadata = {
        "path": path.resolve().as_posix(),
        "length": path.stat().st_size,
        "sha256": _sha256_path(path),
        "format": report["format"],
        "identitySetSha256": report.get("identitySetSha256"),
    }
    return evidence, metadata


def _run_reader(
    reader: Callable[[bytes], Any],
    data: bytes,
    errors: tuple[type[Exception], ...],
) -> tuple[bool, dict[str, Any] | None, str | None]:
    try:
        result = reader(data)
    except errors as exc:
        return False, None, str(exc)
    summary: dict[str, Any] = {}
    if isinstance(result, dict):
        for key in (
            "status", "schemaStatus", "bytesConsumed", "waveCount", "actionCount",
            "configId", "enemyLibraryCount", "enemyLibraryEndOffset", "routeMapCount",
            "waveMapOffset", "entryCount",
            "levelCount", "trackingRouteCount", "npcIdLutCount", "npcProxyCount",
            "worldEntityBriefCount", "worldEntityConfigCount", "opaqueRemainderOffset",
            "opaqueRemainderLength", "barCount", "envVfxCount", "veinCount",
            "midpointCount", "intervalCount", "activeTagCount", "collectionCount",
            "propertyCount", "atomCount", "taskCount",
            "missionId", "questCount", "typedSchemaCount", "dynamicDictionaryCount",
            "objectCount", "taggedObjectCount", "arrayCount", "scalarCount", "maxDepth",
        ):
            if key in result:
                summary[key] = result[key]
    return True, summary, None


def _classify_binary(relative: str, family: str, data: bytes) -> dict[str, Any]:
    if family == "LipSync":
        ok, detail, diagnostic = _run_reader(
            decode_lipsync_memorypack, data, (LipSyncDecodeError, ValueError)
        )
        return {
            "status": "schema_decoded" if ok else "unsupported",
            "reader": "scripts.game_data.memorypack.lipsync",
            "detail": detail,
            "diagnostic": diagnostic,
        }
    if relative.startswith("NPC/MontageJson/MontageNew/"):
        ok, detail, diagnostic = _run_reader(
            frame_npc_montage, data, (NpcMontageFramingError, ValueError)
        )
        return {
            "status": (
                "schema_decoded"
                if ok and detail and detail.get("schemaStatus") == "named_exact"
                else "format_framed" if ok else "unsupported"
            ),
            "reader": "scripts.game_data.memorypack.npc_montage",
            "detail": detail,
            "diagnostic": diagnostic,
        }
    if family == "CharInteractPerformCfgs":
        ok, detail, diagnostic = _run_reader(
            decode_char_interact_complete_frame,
            data,
            (CharInteractPerformDecodeError, ValueError),
        )
        if ok:
            return {
                "status": (
                    "schema_decoded"
                    if detail and detail.get("schemaStatus") == "named_exact"
                    else "format_framed"
                ),
                "reader": "scripts.game_data.char_interact_perform_binary.decode_char_interact_complete_frame",
                "detail": detail,
                "diagnostic": None,
            }
        prefix_ok, prefix_detail, prefix_diagnostic = _run_reader(
            frame_char_interact_prefix,
            data,
            (CharInteractPerformDecodeError, ValueError),
        )
        return {
            "status": "bounded_partial" if prefix_ok else "unsupported",
            "reader": "scripts.game_data.char_interact_perform_binary.frame_char_interact_prefix" if prefix_ok else None,
            "detail": prefix_detail,
            "diagnostic": prefix_diagnostic or diagnostic,
        }
    if family == "SpawnerConfig":
        prefix_ok, prefix_detail, prefix_diagnostic = _run_reader(
            decode_spawner_named_prefix,
            data,
            (SpawnerEnemyLibraryDecodeError, ValueError),
        )
        if prefix_ok:
            assert prefix_detail is not None
            try:
                wave_detail = decode_spawner_wave_map_sequential(
                    data,
                    wave_map_offset=int(prefix_detail["waveMapOffset"]),
                )
                action_tags: dict[str, int] = {}
                for wave in wave_detail["waves"]:
                    for group in wave["groupMap"]:
                        for action in group["actionMap"]:
                            key = str(action["unionTag"])
                            action_tags[key] = action_tags.get(key, 0) + 1
                return {
                    "status": "schema_decoded",
                    "reader": (
                        "scripts.game_data.spawner_binary.decode_spawner_named_prefix+"
                        "decode_spawner_wave_map_sequential"
                    ),
                    "detail": {
                        "configId": prefix_detail["configId"],
                        "enemyLibraryCount": prefix_detail["enemyLibraryCount"],
                        "routeMapCount": prefix_detail["routeMapCount"],
                        "waveMapOffset": prefix_detail["waveMapOffset"],
                        "waveCount": wave_detail["waveCount"],
                        "actionUnionTagCounts": action_tags,
                        "schemaStatus": wave_detail["schemaStatus"],
                    },
                    "diagnostic": None,
                }
            except (SpawnerWaveDecodeError, ValueError) as exc:
                return {
                    "status": "bounded_partial",
                    "reader": "scripts.game_data.spawner_binary.decode_spawner_named_prefix",
                    "detail": {
                        "configId": prefix_detail["configId"],
                        "enemyLibraryCount": prefix_detail["enemyLibraryCount"],
                        "routeMapCount": prefix_detail["routeMapCount"],
                        "waveMapOffset": prefix_detail["waveMapOffset"],
                        "schemaStatus": prefix_detail["schemaStatus"],
                    },
                    "diagnostic": str(exc),
                }
        wave_ok, wave_detail, wave_diagnostic = _run_reader(
            decode_spawner_wave_map, data, (SpawnerWaveDecodeError, ValueError)
        )
        if wave_ok:
            return {
                "status": "schema_decoded",
                "reader": "scripts.game_data.spawner_binary.decode_spawner_wave_map",
                "detail": wave_detail,
                "diagnostic": None,
            }
        enemy_ok, enemy_detail, enemy_diagnostic = _run_reader(
            decode_spawner_enemy_library,
            data,
            (SpawnerEnemyLibraryDecodeError, ValueError),
        )
        return {
            "status": "bounded_partial" if enemy_ok else "unclassified_binary",
            "reader": (
                "scripts.game_data.spawner_binary.decode_spawner_enemy_library"
                if enemy_ok else None
            ),
            "detail": enemy_detail,
            "diagnostic": enemy_diagnostic or prefix_diagnostic or wave_diagnostic,
        }
    if family == "AnimationConfig":
        ok, detail, diagnostic = _run_reader(
            frame_animation_config, data, (AnimationConfigFramingError, ValueError)
        )
        status = "unclassified_binary"
        if ok and detail and detail.get("schemaStatus") == "named_exact":
            status = "schema_decoded"
        elif ok and detail and detail.get("schemaStatus") == "anonymous_exact_frame":
            status = "format_framed_anonymous"
        elif ok:
            status = "bounded_partial"
        return {
            "status": status,
            "reader": "scripts.game_data.animation_config_binary" if ok else None,
            "detail": detail,
            "diagnostic": diagnostic,
        }
    if family == "LevelScriptData":
        for reader in (
            frame_levelscript_empty_action_map_sequential,
            frame_levelscript_null_action_map_sequential,
            frame_levelscript_single_call_server_leader_enter,
            frame_levelscript_current_action_sequence_leader_enter,
            frame_levelscript_terminal_suffix,
            frame_levelscript_empty_action_map_top_level,
            frame_levelscript_action_map_named_prefix,
            frame_levelscript_empty_action_map_prefix,
        ):
            ok, detail, diagnostic = _run_reader(
                reader, data, (LevelScriptTopLevelFramingError, ValueError)
            )
            if ok:
                return {
                    "status": (
                        "schema_decoded"
                        if detail and detail.get("schemaStatus") == "named_exact"
                        else "bounded_partial"
                    ),
                    "reader": f"scripts.game_data.levelscript_binary.{reader.__name__}",
                    "detail": detail,
                    "diagnostic": None,
                }
        return {
            "status": "unclassified_binary",
            "reader": None,
            "detail": None,
            "diagnostic": diagnostic,
        }
    if family == "LevelData":
        ok, detail, diagnostic = _run_reader(
            frame_leveldata_named_prefix,
            data,
            (LevelDataTopLevelFramingError, ValueError),
        )
        if ok:
            return {
                "status": (
                    "schema_decoded"
                    if detail and detail.get("schemaStatus") == "named_exact"
                    else "format_framed"
                    if detail and detail.get("schemaStatus") == "named_exact_frame"
                    else "bounded_partial"
                ),
                "reader": "scripts.game_data.leveldata_binary.frame_leveldata_named_prefix",
                "detail": detail,
                "diagnostic": None,
            }
        for reader in (
            frame_leveldata_empty_tail,
            frame_leveldata_terminal_suffix,
            frame_leveldata_airwalls_prefix,
        ):
            ok, detail, diagnostic = _run_reader(
                reader, data, (LevelDataTopLevelFramingError, ValueError)
            )
            if ok:
                return {
                    "status": "bounded_partial",
                    "reader": f"scripts.game_data.leveldata_binary.{reader.__name__}",
                    "detail": detail,
                    "diagnostic": None,
                }
        return {
            "status": "unclassified_binary",
            "reader": None,
            "detail": None,
            "diagnostic": diagnostic,
        }
    if family == "LevelConfig":
        ok, detail, diagnostic = _run_reader(
            decode_level_config, data, (LevelConfigDecodeError, ValueError)
        )
        return {
            "status": "schema_decoded" if ok else "unclassified_binary",
            "reader": "scripts.game_data.levelconfig_binary" if ok else None,
            "detail": detail,
            "diagnostic": diagnostic,
        }
    if family == "LevelScriptTemplateData":
        ok, detail, diagnostic = _run_reader(
            frame_levelscript_template,
            data,
            (LevelScriptTemplateFramingError, ValueError),
        )
        return {
            "status": (
                "schema_decoded"
                if ok and detail and detail.get("schemaStatus") == "named_exact"
                else "bounded_partial" if ok else "unclassified_binary"
            ),
            "reader": "scripts.game_data.levelscript_template_binary" if ok else None,
            "detail": detail,
            "diagnostic": diagnostic,
        }
    if family == "AtmosphericNpcData":
        ok, detail, diagnostic = _run_reader(
            frame_atmospheric_npc_table,
            data,
            (AtmosphericNpcFramingError, ValueError),
        )
        status = "unclassified_binary"
        if ok and detail and detail.get("schemaStatus") in ("exact", "named_exact"):
            status = "schema_decoded"
        elif ok and detail and detail.get("schemaStatus") == "named_exact_frame":
            status = "format_framed"
        elif ok:
            status = "format_framed_anonymous"
        return {
            "status": status,
            "reader": "scripts.game_data.atmospheric_npc_binary" if ok else None,
            "detail": detail,
            "diagnostic": diagnostic,
        }
    if relative == "NonGeneratedConfigs/BambooRaftTaskTable.json":
        decoded = decode_bamboo_raft_task_table_memorypack(
            BAMBOO_RAFT_TASK_TABLE_REL, data, len(data)
        )
        return {
            "status": "schema_decoded" if decoded is not None else "unclassified_binary",
            "reader": "scripts.game_data.memorypack.tables" if decoded is not None else None,
            "detail": (
                {
                    "subtype": decoded.get("subtype"),
                    "rows": decoded.get("rows"),
                    "exactLength": decoded.get("decoded", {}).get("exactLength"),
                }
                if decoded is not None else None
            ),
            "diagnostic": None if decoded is not None else "current exact table reader rejected payload",
        }
    if relative == "NonGeneratedConfigs/MatrixShockWaveBeatConfigTable.json":
        ok, detail, diagnostic = _run_reader(
            decode_matrix_shockwave_table,
            data,
            (MatrixShockWaveDecodeError, ValueError),
        )
        return {
            "status": "schema_decoded" if ok else "unclassified_binary",
            "reader": "scripts.game_data.matrix_shockwave_binary" if ok else None,
            "detail": detail,
            "diagnostic": diagnostic,
        }
    if relative == "GameplayConfig/AetherEnergyLockConfigTable.json":
        ok, detail, diagnostic = _run_reader(
            decode_aether_energy_lock_table,
            data,
            (AetherEnergyLockDecodeError, ValueError),
        )
        return {
            "status": "schema_decoded" if ok else "unclassified_binary",
            "reader": "scripts.game_data.aether_energy_lock_binary" if ok else None,
            "detail": detail,
            "diagnostic": diagnostic,
        }
    if relative in {
        "GPUISystemConfig/buff_icon.json",
        "GPUISystemConfig/buff_icon_main.json",
        "GPUISystemConfig/outscreen_target.json",
    }:
        ok, detail, diagnostic = _run_reader(
            decode_gpu_ui_root16, data, (GpuUiFramingError, ValueError)
        )
        reader = "scripts.game_data.gpu_ui_binary.decode_gpu_ui_root16"
        if not ok:
            ok, detail, diagnostic = _run_reader(
                frame_gpu_ui_root16_prefix, data, (GpuUiFramingError, ValueError)
            )
            reader = "scripts.game_data.gpu_ui_binary.frame_gpu_ui_root16_prefix"
        return {
            "status": (
                "schema_decoded"
                if ok and detail and detail.get("schemaStatus") == "named_exact"
                else "bounded_partial" if ok else "unclassified_binary"
            ),
            "reader": reader if ok else None,
            "detail": detail,
            "diagnostic": diagnostic,
        }
    if relative == DAMAGE_TEXT_REL.removeprefix("Json/"):
        ok, detail, diagnostic = _run_reader(
            decode_damage_text, data, (GpuUiFramingError, ValueError)
        )
        reader = "scripts.game_data.gpu_ui_binary.decode_damage_text"
        schema_exact = ok
        if not ok:
            ok, detail, framing_diagnostic = _run_reader(
                frame_damage_text, data, (GpuUiFramingError, ValueError)
            )
            reader = "scripts.game_data.gpu_ui_binary.frame_damage_text"
            if not ok:
                diagnostic = framing_diagnostic
        return {
            "status": "schema_decoded" if schema_exact else "format_framed" if ok else "unclassified_binary",
            "reader": reader if ok else None,
            "detail": detail,
            "diagnostic": diagnostic,
        }
    if relative == DIALOG_ID_TABLE_REL.removeprefix("Json/"):
        decoded = decode_dialog_id_table_memorypack(DIALOG_ID_TABLE_REL, data, len(data))
        return {
            "status": "schema_decoded" if decoded is not None else "unclassified_binary",
            "reader": "scripts.game_data.memorypack.tables.decode_dialog_id_table_memorypack" if decoded is not None else None,
            "detail": (
                {"subtype": decoded.get("subtype"), "rows": decoded.get("rows"), "exactLength": True}
                if decoded is not None else None
            ),
            "diagnostic": None if decoded is not None else "current exact table reader rejected payload",
        }
    compact_readers = {
        "GameplayConfigMissionAreaTable.json": (decode_mission_area_table, "schema_decoded"),
        "GameplayConfigSubGameInstanceDataTable.json": (frame_subgame_table, "schema_decoded"),
        "GameplayConfigWorldEntityRegistry.json": (frame_world_entity_registry, "schema_decoded"),
    }
    if relative in compact_readers:
        reader, success_status = compact_readers[relative]
        ok, detail, diagnostic = _run_reader(
            reader, data, (GameplayCompactDecodeError, ValueError)
        )
        return {
            "status": success_status if ok else "unclassified_binary",
            "reader": f"scripts.game_data.gameplay_compact_binary.{reader.__name__}" if ok else None,
            "detail": detail,
            "diagnostic": diagnostic,
        }
    if family == "NavMesh":
        reader = (
            decode_luna_area if relative.endswith("/LunaArea.json")
            else decode_navmesh_state_container
            if relative.endswith("/NavMeshStateContainer.json") else None
        )
        if reader is not None:
            ok, detail, diagnostic = _run_reader(
                reader, data, (NavMeshDecodeError, ValueError)
            )
            return {
                "status": "schema_decoded" if ok else "unclassified_binary",
                "reader": f"scripts.game_data.navmesh_binary.{reader.__name__}" if ok else None,
                "detail": detail,
                "diagnostic": diagnostic,
            }
    if family == "GameplayConfig" and relative.endswith("TeleportValidationDataTable.json"):
        ok, detail, diagnostic = _run_reader(
            decode_teleport_validation_table,
            data,
            (TeleportValidationDecodeError, ValueError),
        )
        return {
            "status": "schema_decoded" if ok else "unclassified_binary",
            "reader": "scripts.game_data.teleport_validation_binary" if ok else None,
            "detail": detail,
            "diagnostic": diagnostic,
        }
    if relative.startswith("Interactive/ModelViewStateControllerData/"):
        ok, detail, diagnostic = _run_reader(
            decode_model_view_state_controller,
            data,
            (InteractiveBinaryDecodeError, ValueError),
        )
        return {
            "status": "schema_decoded" if ok else "unsupported",
            "reader": "scripts.game_data.interactive_binary" if ok else None,
            "detail": detail,
            "diagnostic": diagnostic,
        }
    if relative == "Interactive/InteractiveTable.json":
        ok, detail, diagnostic = _run_reader(
            decode_interactive_table,
            data,
            (InteractiveBinaryDecodeError, ValueError),
        )
        return {
            "status": "schema_decoded" if ok else "unclassified_binary",
            "reader": "scripts.game_data.interactive_binary.decode_interactive_table" if ok else None,
            "detail": detail,
            "diagnostic": diagnostic,
        }
    if relative.startswith("Interactive/InteractiveData/"):
        try:
            decoded = decode_interactive_template_memorypack(
                Path(relative), data, len(data)
            )
            diagnostic = None
        except (ValueError, TypeError) as exc:
            decoded = None
            diagnostic = str(exc)
        return {
            "status": (
                "schema_decoded"
                if decoded is not None
                and decoded.get("decoded", {}).get("schemaStatus") == "named_exact"
                else "bounded_partial" if decoded is not None else "unclassified_binary"
            ),
            "reader": "scripts.game_data.memorypack.interactive" if decoded is not None else None,
            "detail": (
                {
                    "kind": decoded.get("kind"),
                    "subtype": decoded.get("subtype"),
                    "exactLength": decoded.get("decoded", {}).get("exactLength"),
                    "schemaStatus": decoded.get("decoded", {}).get("schemaStatus"),
                }
                if decoded is not None
                else None
            ),
            "diagnostic": diagnostic,
        }
    return {
        "status": "unclassified_binary",
        "reader": None,
        "detail": None,
        "diagnostic": None,
    }


def build_report(
    *,
    outer_path: Path,
    ledger_path: Path,
    export_root: Path,
    expected_input_set_sha256: str,
    buff_report_path: Path = DEFAULT_BUFF_REPORT,
    skill_report_path: Path = DEFAULT_SKILL_REPORT,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    expected = expected_input_set_sha256.upper()
    export_root = export_root.resolve()
    outer, _header, ledger_rows, provenance = _read_outer_and_ledger(
        outer_path, ledger_path, expected_input_set_sha256=expected
    )
    selected = [
        row for row in ledger_rows
        if row.get("blockName") == "JsonData"
        and row.get("blockTypeValue") == 19
        and row.get("boundaryStatus") == "boundary_verified"
    ]
    selected.sort(key=lambda row: str(row["virtualPath"]))
    if not selected:
        raise ValueError("authenticated ledger has no JsonData rows")
    for row in selected:
        if row.get("inputSetSha256") != expected or row.get("status") != "verified":
            raise ValueError(
                f"JsonData ledger row is not current and verified: {row.get('virtualPath')!r}"
            )

    ledger_family_paths = {
        family: {
            str(row["virtualPath"])
            for row in selected
            if str(row["virtualPath"]).startswith(f"Data/Json/{family}/")
        }
        for family in FAMILY_REPORTS
    }
    family_evidence: dict[str, dict[str, dict[str, Any]]] = {}
    family_report_provenance: dict[str, dict[str, Any]] = {}
    for family, report_path in (
        ("BuffData", buff_report_path),
        ("SkillData", skill_report_path),
    ):
        evidence, metadata = _load_family_evidence(
            report_path,
            family=family,
            expected_input_set_sha256=expected,
            expected_paths=ledger_family_paths[family],
        )
        family_evidence[family] = evidence
        family_report_provenance[family] = metadata

    seen_paths: set[str] = set()
    results: list[dict[str, Any]] = []
    for ledger in selected:
        virtual_path = str(ledger["virtualPath"])
        path, relative, family = _safe_export_path(export_root, virtual_path)
        if relative.casefold() in seen_paths:
            raise ValueError(f"case-insensitive duplicate JsonData export path: {relative}")
        seen_paths.add(relative.casefold())
        if not path.is_file():
            raise ValueError(f"missing JsonData export file: {relative}")
        data = path.read_bytes()
        expected_length = int(ledger["length"])
        expected_md5 = str(ledger["recomputedFileDataMd5"]).upper()
        actual_md5 = hashlib.md5(data).hexdigest().upper()
        if len(data) != expected_length or actual_md5 != expected_md5:
            raise ValueError(
                f"JsonData export differs from VFS ledger: {relative}; "
                f"length={len(data)}/{expected_length}; md5={actual_md5}/{expected_md5}"
            )

        is_json, json_root = _classify_json(data)
        logical_sha256 = hashlib.sha256(data).hexdigest().upper()
        if is_json and is_npc_prefab_info_path(relative):
            ok, detail, diagnostic = _run_reader(
                lambda payload: decode_npc_prefab_info(payload, source=relative),
                data,
                (NpcPrefabInfoDecodeError, ValueError),
            )
            classification = {
                "status": "schema_decoded" if ok else "unsupported",
                "reader": "scripts.game_data.npc_prefab_info" if ok else None,
                "detail": detail,
                "diagnostic": diagnostic,
            }
        elif is_json and is_npc_catalog_path(relative):
            ok, detail, diagnostic = _run_reader(
                lambda payload: decode_npc_catalog(payload, source=relative),
                data,
                (NpcCatalogDecodeError, ValueError),
            )
            classification = {
                "status": "schema_decoded" if ok else "unsupported",
                "reader": "scripts.game_data.npc_catalog_json" if ok else None,
                "detail": detail,
                "diagnostic": diagnostic,
            }
        elif is_json and is_mission_runtime_main_path(relative):
            ok, detail, diagnostic = _run_reader(
                lambda payload: decode_mission_runtime_main(payload, source=relative),
                data,
                (MissionRuntimeMainDecodeError, ValueError),
            )
            classification = {
                "status": "schema_decoded" if ok else "unsupported",
                "reader": "scripts.game_data.mission_runtime_main" if ok else None,
                "detail": detail,
                "diagnostic": diagnostic,
            }
        elif is_json and is_mission_runtime_meta_path(relative):
            ok, detail, diagnostic = _run_reader(
                lambda payload: decode_mission_runtime_meta(payload, source=relative),
                data,
                (MissionRuntimeMetaDecodeError, ValueError),
            )
            classification = {
                "status": "schema_decoded" if ok else "unsupported",
                "reader": "scripts.game_data.mission_runtime_meta" if ok else None,
                "detail": detail,
                "diagnostic": diagnostic,
            }
        elif is_json and is_map_config_path(relative):
            ok, detail, diagnostic = _run_reader(
                lambda payload: decode_map_config(payload, source=relative),
                data,
                (MapConfigDecodeError, ValueError),
            )
            classification = {
                "status": "schema_decoded" if ok else "unsupported",
                "reader": "scripts.game_data.map_config_json" if ok else None,
                "detail": detail,
                "diagnostic": diagnostic,
            }
        elif is_json and is_ui_level_map_load_config_path(relative):
            ok, detail, diagnostic = _run_reader(
                lambda payload: decode_ui_level_map_load_config(payload, source=relative),
                data,
                (UiLevelMapLoadConfigDecodeError, ValueError),
            )
            classification = {
                "status": "schema_decoded" if ok else "unsupported",
                "reader": "scripts.game_data.ui_level_map_load_config" if ok else None,
                "detail": detail,
                "diagnostic": diagnostic,
            }
        elif is_json and is_gold_coin_config_path(relative):
            ok, detail, diagnostic = _run_reader(
                lambda payload: decode_gold_coin_config(payload, source=relative),
                data,
                (GoldCoinConfigDecodeError, ValueError),
            )
            classification = {
                "status": "schema_decoded" if ok else "unsupported",
                "reader": "scripts.game_data.gold_coin_config_json" if ok else None,
                "detail": detail,
                "diagnostic": diagnostic,
            }
        elif is_json and is_named_jsondata_text_path(relative):
            ok, detail, diagnostic = _run_reader(
                lambda payload: decode_named_jsondata_text(
                    payload, source=relative
                ),
                data,
                (JsonDataTextSchemaDecodeError, ValueError),
            )
            classification = {
                "status": "schema_decoded" if ok else "unsupported",
                "reader": "scripts.game_data.jsondata_text_schema" if ok else None,
                "detail": detail,
                "diagnostic": diagnostic,
            }
        elif is_json and is_level_mount_point_path(relative):
            ok, detail, diagnostic = _run_reader(
                lambda payload: decode_level_mount_points(
                    payload, source=relative
                ),
                data,
                (LevelMountPointJsonDecodeError, ValueError),
            )
            classification = {
                "status": "schema_decoded" if ok else "unsupported",
                "reader": "scripts.game_data.level_mount_point_json" if ok else None,
                "detail": detail,
                "diagnostic": diagnostic,
            }
        elif is_json and is_compact_gameplay_config_json_path(relative):
            ok, detail, diagnostic = _run_reader(
                lambda payload: decode_compact_gameplay_config_json(
                    payload, source=relative
                ),
                data,
                (GameplayConfigJsonDecodeError, ValueError),
            )
            classification = {
                "status": "schema_decoded" if ok else "unsupported",
                "reader": "scripts.game_data.gameplay_config_json" if ok else None,
                "detail": detail,
                "diagnostic": diagnostic,
            }
        elif is_json and is_polymorphic_gameplay_config_path(relative):
            ok, detail, diagnostic = _run_reader(
                lambda payload: decode_polymorphic_gameplay_config(
                    payload, source=relative
                ),
                data,
                (GameplayConfigPolymorphicDecodeError, ValueError),
            )
            classification = {
                "status": "schema_decoded" if ok else "unsupported",
                "reader": "scripts.game_data.gameplay_config_polymorphic" if ok else None,
                "detail": detail,
                "diagnostic": diagnostic,
            }
        else:
            classification = (
            {
                "status": "format_framed_json",
                "reader": "python.json",
                "detail": {"rootType": json_root},
                "diagnostic": None,
            }
            if is_json
            else _classify_binary(relative, family, data)
            )
        if not is_json and family in family_evidence:
            evidence = family_evidence[family][virtual_path]
            if (
                evidence["length"] != len(data)
                or evidence["logicalMd5"] != actual_md5
                or evidence["logicalSha256"] != logical_sha256
            ):
                raise ValueError(f"{family} evidence differs from current export bytes: {virtual_path!r}")
            contract = FAMILY_REPORTS[family]
            classification = {
                "status": (
                    "schema_decoded"
                    if family == "SkillData"
                    and evidence["detail"].get("wholeSchemaExact") is True
                    else "format_framed"
                    if family == "BuffData"
                    and evidence["detail"].get("namedOuterFrameStatus") == "named_exact_frame"
                    else "bounded_partial_ambiguous"
                    if family == "SkillData"
                    and evidence["detail"].get("boundaryClass") == "ambiguous"
                    else contract["status"]
                ),
                "reader": contract["reader"],
                "detail": evidence["detail"],
                "diagnostic": None,
            }
        results.append({
            "virtualPath": virtual_path,
            "exportRelativePath": relative,
            "family": family,
            "length": len(data),
            "logicalMd5": actual_md5,
            "logicalSha256": logical_sha256,
            "firstByte": data[:1].hex().upper(),
            **classification,
        })

    actual_files = {
        path.relative_to(export_root).as_posix().casefold()
        for path in export_root.rglob("*") if path.is_file()
    }
    extras = sorted(actual_files - seen_paths)
    if extras:
        raise ValueError(f"JsonData export contains unowned files; first={extras[0]!r}")

    family_counts: dict[str, Counter[str]] = defaultdict(Counter)
    status_counts: Counter[str] = Counter()
    for row in results:
        family_counts[row["family"]]["files"] += 1
        family_counts[row["family"]]["bytes"] += row["length"]
        family_counts[row["family"]][row["status"]] += 1
        status_counts[row["status"]] += 1
    families = {
        family: dict(sorted(counts.items()))
        for family, counts in sorted(
            family_counts.items(), key=lambda item: (-item[1]["files"], item[0])
        )
    }
    report = {
        "format": REPORT_FORMAT,
        "schemaVersion": 1,
        "status": "complete",
        "inputSetSha256": expected,
        "exportRoot": export_root.as_posix(),
        "provenance": {
            **provenance,
            "registry": {
                "path": Path(__file__).resolve().as_posix(),
                "length": Path(__file__).stat().st_size,
                "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper(),
            },
            "familyReports": family_report_provenance,
        },
        "summary": {
            "filesSelected": len(selected),
            "filesJoined": len(results),
            "logicalBytes": sum(row["length"] for row in results),
            "statusCounts": dict(sorted(status_counts.items())),
            "familyCount": len(families),
            "families": families,
        },
        "evidenceBoundary": (
            "Every current JsonData logical identity is joined to the structured export "
            "by safe relative path, exact length, and logical MD5. JSON syntax, exact "
            "reader closures, bounded partial frames, bounded ambiguous frames, unsupported variants, and "
            "unclassified binary payloads remain separate terminal states. A path, "
            "filename extension, or leading member count never supplies a schema."
        ),
    }
    return report, results


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# JsonData current corpus registry",
        "",
        f"Status: `{report['status']}`; inputSetSha256: `{report['inputSetSha256']}`.",
        "",
        f"Joined `{summary['filesJoined']}` of `{summary['filesSelected']}` files; "
        f"logical bytes: `{summary['logicalBytes']}`; families: `{summary['familyCount']}`.",
        "",
        "## Terminal states",
        "",
        "| State | Files |",
        "|---|---:|",
    ]
    lines.extend(
        f"| `{status}` | {count} |"
        for status, count in summary["statusCounts"].items()
    )
    lines.extend((
        "",
        "## Families",
        "",
        "| Family | Files | Bytes | JSON | Schema decoded | Framed | Partial | Ambiguous partial | Unsupported | Unclassified |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ))
    for family, counts in summary["families"].items():
        framed = counts.get("format_framed", 0) + counts.get("format_framed_anonymous", 0)
        lines.append(
            f"| `{family}` | {counts['files']} | {counts['bytes']} | "
            f"{counts.get('format_framed_json', 0)} | {counts.get('schema_decoded', 0)} | "
            f"{framed} | {counts.get('bounded_partial', 0)} | "
            f"{counts.get('bounded_partial_ambiguous', 0)} | "
            f"{counts.get('unsupported', 0)} | {counts.get('unclassified_binary', 0)} |"
        )
    lines.extend(("", report["evidenceBoundary"], ""))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outer-summary", type=Path, default=DEFAULT_OUTER)
    parser.add_argument("--outer-ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--export-root", type=Path, default=DEFAULT_EXPORT)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--buff-report", type=Path, default=DEFAULT_BUFF_REPORT)
    parser.add_argument("--skill-report", type=Path, default=DEFAULT_SKILL_REPORT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MD)
    parser.add_argument("--output-files", type=Path, default=DEFAULT_FILES)
    args = parser.parse_args(argv)
    try:
        outputs = [args.output_json, args.output_md, args.output_files]
        for output in outputs:
            _guard_output_path(
                output,
                [args.outer_summary, args.outer_ledger, args.export_root, args.buff_report, args.skill_report]
                + [other for other in outputs if other != output],
            )
        report, rows = build_report(
            outer_path=args.outer_summary,
            ledger_path=args.outer_ledger,
            export_root=args.export_root,
            expected_input_set_sha256=args.expected_input_set_sha256,
            buff_report_path=args.buff_report,
            skill_report_path=args.skill_report,
        )
        json_bytes = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        md_bytes = render_markdown(report).encode("utf-8")
        lines = b"".join(
            (json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
            for row in rows
        )
        files_bytes = gzip.compress(lines, mtime=0)
        _atomic_write(args.output_json, json_bytes)
        _atomic_write(args.output_md, md_bytes)
        _atomic_write(args.output_files, files_bytes)
    except (CensusGateError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "failed", "diagnostic": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": report["status"], "summary": report["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

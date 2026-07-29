#!/usr/bin/env python3
"""Rank source-only Story recovery gaps without inventing scene order.

The queue reuses the strict partial-order builder, then measures where original
game data could still improve coverage: isolated/weak scenes, source cycles,
untyped multi-scene LevelScript contexts, quests without strict Story
attachment, unresolved source nodes, and unverified option groups.  Main-story
(``e``) missions sort before the other established priority buckets.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    combined_non_mission_content_keys,
    md_escape,
    non_mission_content_keys,
    read_json,
    safe_key,
    write_report_json,
    write_text_if_changed,
)
from build_priority_story_order_audit import priority_bucket  # noqa: E402
from build_source_story_partial_order import (  # noqa: E402
    build_report as build_partial_order_report,
    load_mission_payload_with_variants,
)
from build_animestudio_story_carrier_audit import (  # noqa: E402
    target_set_sha256,
)
from story_builder.mission_recovery import natural_key  # noqa: E402


SCHEMA = "sourceStoryGapQueue.v22"
LEVELSCRIPT_INTERACTIVE_NARRATIVE_MAPPING_ID = (
    "levelscript-interactive-narrative-config-v1"
)
LEVELDATA_INTERACTIVE_NARRATIVE_MAPPING_ID = (
    "leveldata-interactive-narrative-config-v5"
)
LEVELDATA_INTERACTIVE_HORN_MAPPING_ID = (
    "leveldata-interactive-horn-dialog-config-v1"
)
LEVELDATA_INTERACTIVE_HORN_NATIVE_MAPPING_ID = (
    "gameassembly-2026-07-29-interactive-horn-dialog-v1"
)
LEVELDATA_INTERACTIVE_HORN_TEMPLATE_SHA256 = (
    "1200acb7208de5e4b9e861dc511cc3a3d4f1f5c56dd4b59f1dcb0ef7ab2ea33e"
)
BUCKET_ORDER = ("main", "event", "major", "character", "other")

# The score is a triage aid, not recovered chronology. Every contribution is
# emitted per mission so a reviewer can change the policy without losing facts.
SCORE_WEIGHTS = {
    "missingMissionBundle": 100,
    "sourceCycles": 20,
    "cycleScenes": 8,
    "untypedMultiSceneLevelscriptContexts": 10,
    "actionableCoreIsolatedScenes": 5,
    "actionableWeakOnlyScenes": 4,
    "unresolvedSourceNodes": 4,
    "questIdsWithoutStrictStoryAttachment": 3,
    "actionableNoExplicitOptionRouteGroups": 2,
    "actionableExcludedOptionEvidenceGroups": 2,
}

CORE_STORY_NODE_KINDS = frozenset({
    "black",
    "cutscene",
    "dlg",
    "misc",
    "radio",
    "remotecomm",
    "runtimeDialog",
    "sns",
    "text",
})

FRONTIER_ORDER = (
    "missing-mission-runtime-bundle",
    "levelscript-control-flow",
    "source-cycle-review",
    "quest-scene-attachment",
    "dialog-option-runtime",
    "unresolved-source-node",
    "isolated-scene-source-link",
)

# Exact current-build ActionBase formatter classifications that are useful to
# this queue but deliberately excluded from the playback-oriented mapping in
# ``story_builder.level_bindings``.  These tags carry Story-looking ids while
# configuring, removing, overriding, or stopping presentation; they cannot
# establish that the referenced Story file plays at that point.
KNOWN_NON_PLAYBACK_ACTIONS = {
    ("0x0344", "0x0a"): ("OverrideNPCDialog", "override_dialog"),
    ("0x0377", "0x0b"): ("PreloadDialogAction", "preload_dialog"),
    ("0x0389", "0x0a"): ("RemoveNPCDialog", "remove_dialog"),
    ("0x04b5", "0x09"): ("StopRadio", "stop_radio"),
}
KNOWN_NON_PLAYBACK_MAPPING_ID = (
    "gameassembly-2026-07-11-cr-0x18b9217d0-actionbase-formatter-table"
)
NPC_PROXY_DIALOG_SELECTION_MAPPING_ID = (
    "npc-proxy-dialog-selection-native-v1"
)
NPC_PROXY_DIALOG_SELECTION_GAMEASSEMBLY_SHA256 = (
    "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
)
DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID = (
    "dialog-tree-narrative-mask-connection-native-v1"
)
OFFLINE_EXHAUSTION_MAPPING_ID = (
    "current-build-offline-story-carrier-exhaustion-v2"
)
OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256 = (
    "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
)
OFFLINE_EXHAUSTION_REVERSE_PPTR_MAPPING_ID = (
    "gameassembly-2026-07-28-cutscene-root-director-playback-v1"
)
OFFLINE_EXHAUSTION_METADATA_SHA256 = (
    "90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E"
)
OFFLINE_EXHAUSTION_RADIO_TABLE_SHA256 = (
    "78E0974495915D1F126EA9FE2923DC44DFD260D8358702A01504147BFABBD1D1"
)
OFFLINE_EXHAUSTION_AUDIO_DIALOG_SHA256 = (
    "1433BCAFCD12A30ABCC22A0D5754ABA3D0F2C403789F27C6E7250B5491ED074D"
)
OFFLINE_EXHAUSTION_NUM_ID_STR_TABLE_SHA256 = (
    "13FE790D69B0B3CDD4B64CCA53BB41DA8BD0D45D31975004FA074B0EDBB73BDE"
)
OFFLINE_EXHAUSTION_TEXT_TABLE_SHA256 = (
    "78CECB42561D80255AB2C38DD24F6699DDC6226D2DFF058FABC5E1EE50223CF3"
)
OFFLINE_EXHAUSTION_E11M4_CUTSCENE_SHA256 = (
    "EF073ADA194D047E28500ECEF71E2B370587905C83DFEFA1CAE5E9E591A0EA99"
)
OFFLINE_EXHAUSTION_E11M4_CUTSCENE = (
    "cutscene_e11m4_rift_camera_state1to2"
)
OFFLINE_EXHAUSTION_E11M1_TEXT_ONLY_CUTSCENE = "cutscene_e11m1_2"
OFFLINE_EXHAUSTION_E11M1_PRESENTATION_CUTSCENES = frozenset({
    "cutscene_e11m1_fire_end",
    "cutscene_e11m1_gatebattleend",
    "cutscene_e11m1_jsspsi_ground_cast",
    "cutscene_e11m1_shenjiaoe",
})
OFFLINE_EXHAUSTION_CUTSCENES_BY_MISSION = {
    "e11m1": frozenset({
        OFFLINE_EXHAUSTION_E11M1_TEXT_ONLY_CUTSCENE,
        *OFFLINE_EXHAUSTION_E11M1_PRESENTATION_CUTSCENES,
    }),
    "e11m4": frozenset({OFFLINE_EXHAUSTION_E11M4_CUTSCENE}),
}
OFFLINE_EXHAUSTION_REVERSE_HOST_COUNTS = {
    "cutscene_e11m1_fire_end": 2,
    "cutscene_e11m1_gatebattleend": 1,
    "cutscene_e11m1_jsspsi_ground_cast": 1,
    "cutscene_e11m1_shenjiaoe": 2,
    OFFLINE_EXHAUSTION_E11M4_CUTSCENE: 1,
}
OFFLINE_EXHAUSTION_E11M4_RADIOS = frozenset({
    "radio_e11m4_7",
    "radio_e11m4_8",
    *{
        f"radio_e11m4_{number}"
        for number in range(29, 56)
    },
    *{
        f"radio_e11m4_{number}"
        for number in range(57, 62)
    },
})
OFFLINE_EXHAUSTION_E10M4_RADIOS = frozenset({
    "radio_e10m4_2",
    "radio_e10m4_4",
    "radio_e10m4_5",
    "radio_e10m4_11",
    "radio_e10m4_20",
    "radio_e10m4_21",
    "radio_e10m4_22",
    "radio_e10m4_24",
    "radio_e10m4_26",
    "radio_e10m4_27",
    "radio_e10m4_28",
    "radio_e10m4_31",
    "radio_e10m4_32",
    "radio_e10m4_33",
    "radio_e10m4_34",
    "radio_e10m4_35",
    "radio_e10m4_38",
    "radio_e10m4_57",
    "radio_e10m4_63",
    "radio_e10m4_65",
    "radio_e10m4_66",
})
OFFLINE_EXHAUSTION_E11M1_RADIOS = frozenset({
    "radio_e11m1_7",
    "radio_e11m1_15",
    "radio_e11m1_16",
    "radio_e11m1_18",
    "radio_e11m1_28",
    "radio_e11m1_37",
    "radio_e11m1_48",
    "radio_e11m1_61",
    "radio_e11m1_71",
    "radio_e11m1_74",
    "radio_e11m1_79",
    "radio_e11m1_87",
    "radio_e11m1_89",
    "radio_e11m1_93",
    "radio_e11m1_94",
    "radio_e11m1_95",
    "radio_e11m1_96",
    "radio_e11m1_97",
    "radio_e11m1_98",
    "radio_e11m1_99",
    "radio_e11m1_100",
    "radio_e11m1_101",
    "radio_e11m1_104",
})
OFFLINE_EXHAUSTION_RADIOS_BY_MISSION = {
    "e10m4": OFFLINE_EXHAUSTION_E10M4_RADIOS,
    "e11m1": OFFLINE_EXHAUSTION_E11M1_RADIOS,
    "e11m4": OFFLINE_EXHAUSTION_E11M4_RADIOS,
}
OFFLINE_EXHAUSTION_MISSING_AUDIO_IDS = {
    "radio_e10m4_11": frozenset({"au_radio_e10m4_11_001"}),
    "radio_e10m4_38": frozenset({"au_radio_e10m4_38_001"}),
}
OFFLINE_EXHAUSTION_RADIO_ROW_FIELDS = frozenset({
    "continueAfterDialog",
    "continueAfterRadio",
    "priority",
    "radioSingleDataList",
    "radioType",
})


def _bucket(mission: str) -> str:
    return priority_bucket(mission) or "other"


def _string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for value in values:
        text = safe_key(value)
        if text and text not in out:
            out.append(text)
    return out


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _configured_game_assembly_path() -> Path | None:
    game_root = os.environ.get("ENDFIELD_GAME_ROOT", "").strip()
    if not game_root:
        config_path = ROOT / "endfield_paths.bat"
        if config_path.is_file():
            match = re.search(
                r'(?im)^\s*set\s+"ENDFIELD_GAME_ROOT=([^"]+)"\s*$',
                config_path.read_text(encoding="utf-8", errors="replace"),
            )
            if match:
                game_root = match.group(1).strip()
    if not game_root:
        return None
    root = Path(game_root)
    return root.parent / "GameAssembly.dll" if root.name == "Endfield_Data" else root / "GameAssembly.dll"


def _core_isolated_target_missions(
    partial_report: dict[str, Any],
) -> dict[str, set[str]]:
    targets: dict[str, set[str]] = defaultdict(set)
    for row in partial_report.get("missions") or []:
        if not isinstance(row, dict):
            continue
        mission = safe_key(row.get("mission"))
        if not mission:
            continue
        node_kind_by_key = {
            safe_key(node.get("key")): safe_key(node.get("kind"))
            for node in row.get("nodes") or []
            if isinstance(node, dict) and safe_key(node.get("key"))
        }
        isolated_keys = _string_list(row.get("isolatedSceneKeys"))
        if not isolated_keys:
            isolated_keys = [
                safe_key(node.get("key"))
                for node in row.get("nodes") or []
                if (
                    isinstance(node, dict)
                    and safe_key(node.get("key"))
                    and safe_key(node.get("relationStatus")) == "isolated"
                )
            ]
        for story_key in isolated_keys:
            if node_kind_by_key.get(story_key) not in CORE_STORY_NODE_KINDS:
                continue
            targets[story_key].add(mission)
    return dict(targets)


def _audit_sources_match_current_indexes(report: dict[str, Any]) -> bool:
    reported = {
        safe_key(row.get("source")): safe_key(
            row.get("stageSignatureSha256")
        ).lower()
        for row in report.get("sources") or []
        if isinstance(row, dict) and safe_key(row.get("source"))
    }
    for source in ("StreamingAssets", "Persistent"):
        summary_path = (
            ROOT
            / "export_full"
            / "recovered"
            / "AnimeStudio-cli"
            / source
            / "object_index"
            / "summary.json"
        )
        summary = read_json(summary_path, {})
        if not isinstance(summary, dict) or summary.get("complete") is not True:
            return False
        signature = safe_key(
            (summary.get("stageSignature") or {}).get("sha256")
        ).lower()
        if not signature or reported.get(source) != signature:
            return False
    return True


def build_offline_exhaustion_index(
    partial_report: dict[str, Any],
    table_root: Path,
    *,
    game_assembly_path: Path | None = None,
    carrier_audit_path: Path | None = None,
    gameobject_audit_path: Path | None = None,
    reverse_pptr_audit_path: Path | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Build hash-locked current-build deferrals for exhausted offline rows.

    A deferral changes queue priority only. It never creates Story ownership,
    playback, or chronology. Every source gate must match the audited build;
    otherwise the complete set reopens automatically.
    """
    carrier_audit_path = carrier_audit_path or (
        ROOT
        / "reports"
        / "story"
        / "recovery"
        / "animestudio_story_carrier_audit.json"
    )
    gameobject_audit_path = gameobject_audit_path or (
        ROOT
        / "reports"
        / "story"
        / "recovery"
        / "animestudio_story_gameobject_audit.json"
    )
    reverse_pptr_audit_path = reverse_pptr_audit_path or (
        ROOT
        / "reports"
        / "story"
        / "recovery"
        / "animestudio_story_reverse_pptr_audit.json"
    )
    game_assembly_path = game_assembly_path or _configured_game_assembly_path()
    source_paths = {
        "radioTable": table_root / "RadioTable.json",
        "audioDialog": table_root / "AudioDialog.json",
        "numIdStrTable": table_root / "NumIdStrTable.json",
        "textTable": table_root / "TextTable.json",
        "cutsceneDefinition": (
            ROOT
            / "export_full"
            / "recovered"
            / "AnimeStudio-cli"
            / "StreamingAssets"
            / "json_by_type"
            / "TextAsset"
            / (
                "cutscene_e11m4_rift_camera_state1to2_"
                "p86E71A990775EC2D.json"
            )
        ),
        "gameAssembly": game_assembly_path,
        "carrierAudit": carrier_audit_path,
        "gameObjectAudit": gameobject_audit_path,
        "reversePptrAudit": reverse_pptr_audit_path,
    }
    expected_hashes = {
        "radioTable": OFFLINE_EXHAUSTION_RADIO_TABLE_SHA256,
        "audioDialog": OFFLINE_EXHAUSTION_AUDIO_DIALOG_SHA256,
        "numIdStrTable": OFFLINE_EXHAUSTION_NUM_ID_STR_TABLE_SHA256,
        "textTable": OFFLINE_EXHAUSTION_TEXT_TABLE_SHA256,
        "cutsceneDefinition":
            OFFLINE_EXHAUSTION_E11M4_CUTSCENE_SHA256,
        "gameAssembly": OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
    }
    actual_hashes = {
        name: _sha256_file(path) if isinstance(path, Path) else ""
        for name, path in source_paths.items()
        if name in expected_hashes
    }
    mismatches = sorted(
        name
        for name, expected in expected_hashes.items()
        if actual_hashes.get(name) != expected
    )
    status: dict[str, Any] = {
        "mappingId": OFFLINE_EXHAUSTION_MAPPING_ID,
        "status": "inactive_source_validation_failed" if mismatches else "validating",
        "sourceHashes": actual_hashes,
        "expectedSourceHashes": expected_hashes,
        "sourceHashMismatches": mismatches,
        "graphEffect": "none",
        "queueEffect": "defer only while every exact current-build gate matches",
    }
    if mismatches:
        return {}, status

    carrier_audit = read_json(carrier_audit_path, {})
    core_targets = _core_isolated_target_missions(partial_report)
    core_target_digest = target_set_sha256(core_targets)
    no_candidate_keys = set(_string_list(
        carrier_audit.get("noCandidateStoryKeys")
        if isinstance(carrier_audit, dict)
        else []
    ))
    radio_mission_by_key = {
        story_key: mission
        for mission, story_keys in OFFLINE_EXHAUSTION_RADIOS_BY_MISSION.items()
        for story_key in story_keys
    }
    all_radio_keys = set(radio_mission_by_key)
    cutscene_mission_by_key = {
        story_key: mission
        for mission, story_keys
        in OFFLINE_EXHAUSTION_CUTSCENES_BY_MISSION.items()
        for story_key in story_keys
    }
    all_cutscene_keys = set(cutscene_mission_by_key)
    required_key_missions = {
        **radio_mission_by_key,
        **cutscene_mission_by_key,
    }
    required_keys = set(required_key_missions)
    if (
        not isinstance(carrier_audit, dict)
        or carrier_audit.get("_schema") != "animestudioStoryCarrierAudit.v3"
        or safe_key(carrier_audit.get("targetField"))
        != "coreIsolatedSceneKeys"
        or safe_key(carrier_audit.get("targetSetSha256")).lower()
        != core_target_digest.lower()
        or not required_keys <= no_candidate_keys
        or any(
            core_targets.get(story_key) != {mission}
            for story_key, mission in required_key_missions.items()
        )
        or not _audit_sources_match_current_indexes(carrier_audit)
    ):
        status.update({
            "status": "inactive_carrier_audit_stale_or_incomplete",
            "coreTargetSetSha256": core_target_digest,
        })
        return {}, status

    radio_table = read_json(source_paths["radioTable"], {})
    audio_dialog = read_json(source_paths["audioDialog"], {})
    audio_stems = {
        Path(safe_key(row.get("path"))).stem
        for row in (
            audio_dialog.values()
            if isinstance(audio_dialog, dict)
            else []
        )
        if isinstance(row, dict) and safe_key(row.get("path"))
    }
    radio_audio_ids: set[str] = set()
    missing_audio_ids_by_story: dict[str, set[str]] = {}
    radio_rows_valid = isinstance(radio_table, dict)
    for story_key in all_radio_keys:
        row = radio_table.get(story_key) if isinstance(radio_table, dict) else None
        if (
            not isinstance(row, dict)
            or set(row) != OFFLINE_EXHAUSTION_RADIO_ROW_FIELDS
            or not isinstance(row.get("radioSingleDataList"), list)
            or not row["radioSingleDataList"]
        ):
            radio_rows_valid = False
            break
        row_audio_ids: set[str] = set()
        for line in row["radioSingleDataList"]:
            audio_id = (
                safe_key(line.get("audioOverride"))
                if isinstance(line, dict)
                else ""
            )
            if not audio_id:
                radio_rows_valid = False
                break
            radio_audio_ids.add(audio_id)
            row_audio_ids.add(audio_id)
        if not radio_rows_valid:
            break
        missing_audio_ids = row_audio_ids - audio_stems
        if missing_audio_ids:
            missing_audio_ids_by_story[story_key] = missing_audio_ids
    if (
        not radio_rows_valid
        or missing_audio_ids_by_story
        != {
            story_key: set(audio_ids)
            for story_key, audio_ids
            in OFFLINE_EXHAUSTION_MISSING_AUDIO_IDS.items()
        }
        or not (
            radio_audio_ids
            - {
                audio_id
                for audio_ids in missing_audio_ids_by_story.values()
                for audio_id in audio_ids
            }
        ) <= audio_stems
    ):
        status["status"] = "inactive_radio_definition_validation_failed"
        return {}, status

    num_id_table = read_json(source_paths["numIdStrTable"], {})
    timeline_ids = (
        ((num_id_table.get("timelines_id") or {}).get("dic") or {})
        if isinstance(num_id_table, dict)
        else {}
    )
    text_table = read_json(source_paths["textTable"], {})
    cutscene_definition = read_json(source_paths["cutsceneDefinition"], {})
    gameobject_audit = read_json(gameobject_audit_path, {})
    reverse_pptr_audit = read_json(reverse_pptr_audit_path, {})
    gameobject_audit_valid = (
        isinstance(gameobject_audit, dict)
        and gameobject_audit.get("_schema")
        == "animestudioStoryGameObjectAudit.v3"
        and _audit_sources_match_current_indexes(gameobject_audit)
    )
    reverse_native = (
        reverse_pptr_audit.get("nativeEvidence")
        if isinstance(reverse_pptr_audit, dict)
        else {}
    )
    reverse_pptr_audit_valid = (
        isinstance(reverse_pptr_audit, dict)
        and reverse_pptr_audit.get("_schema")
        == "animestudioStoryReversePPtrAudit.v3"
        and _audit_sources_match_current_indexes(reverse_pptr_audit)
        and safe_key(reverse_native.get("mappingId"))
        == OFFLINE_EXHAUSTION_REVERSE_PPTR_MAPPING_ID
        and safe_key(reverse_native.get("gameAssemblySha256"))
        == OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256
        and safe_key(reverse_native.get("metadataSha256"))
        == OFFLINE_EXHAUSTION_METADATA_SHA256
    )
    if (
        not gameobject_audit_valid
        or not reverse_pptr_audit_valid
    ):
        status["status"] = "inactive_cutscene_audit_stale_or_incomplete"
        return {}, status

    gameobject_rows_by_key: dict[str, list[dict[str, Any]]] = {}
    reverse_hosts_by_key: dict[str, list[dict[str, Any]]] = {}
    presentation_cutscene_valid = True
    for story_key, expected_host_count in (
        OFFLINE_EXHAUSTION_REVERSE_HOST_COUNTS.items()
    ):
        object_rows = [
            row
            for row in gameobject_audit.get("gameObjects") or []
            if (
                isinstance(row, dict)
                and story_key in _string_list(row.get("storyKeys"))
            )
        ]
        director_hosts = [
            row
            for row in reverse_pptr_audit.get("directorHosts") or []
            if (
                isinstance(row, dict)
                and story_key in _string_list(row.get("storyKeys"))
            )
        ]
        gameobject_rows_by_key[story_key] = object_rows
        reverse_hosts_by_key[story_key] = director_hosts
        expected_mission = cutscene_mission_by_key[story_key]
        if (
            not object_rows
            or any(
                set(_string_list(row.get("storyKeys"))) != {story_key}
                or row.get("candidateStatus")
                != "no_typed_owner_or_runtime_sibling_or_descendant"
                or row.get("edgeStatus") != "no_edge_candidate_only"
                or row.get("candidateSiblingComponents")
                or row.get("candidateDescendantComponents")
                for row in object_rows
            )
            or len(director_hosts) != expected_host_count
            or any(
                set(_string_list(row.get("storyKeys"))) != {story_key}
                or set(_string_list(row.get("expectedGapMissions")))
                != {expected_mission}
                or safe_key(row.get("pointerPath"))
                != "$.m_PlayableAsset"
                or row.get("candidateComponents")
                or row.get("crossStoryContainments")
                for row in director_hosts
            )
        ):
            presentation_cutscene_valid = False
            break

    text_only_key = OFFLINE_EXHAUSTION_E11M1_TEXT_ONLY_CUTSCENE
    text_only_row_keys = {
        key
        for key in (
            text_table
            if isinstance(text_table, dict)
            else {}
        )
        if key.startswith(f"{text_only_key}_")
    }
    expected_text_only_row_keys = {
        f"{text_only_key}_{number:02d}"
        for number in range(1, 5)
    }
    text_only_cutscene_valid = (
        text_only_row_keys == expected_text_only_row_keys
        and all(
            isinstance(text_table.get(key), dict)
            and set(text_table[key]) == {"id", "text"}
            and isinstance(text_table[key].get("id"), int)
            and not isinstance(text_table[key].get("id"), bool)
            for key in expected_text_only_row_keys
        )
        and text_only_key not in {
            safe_key(value)
            for value in (
                timeline_ids.values()
                if isinstance(timeline_ids, dict)
                else []
            )
        }
        and not any(
            text_only_key in _string_list(row.get("storyKeys"))
            for row in gameobject_audit.get("gameObjects") or []
            if isinstance(row, dict)
        )
        and not any(
            text_only_key in _string_list(row.get("targetStoryKeys"))
            for row in reverse_pptr_audit.get("relations") or []
            if isinstance(row, dict)
        )
        and not any(
            text_only_key in _string_list(row.get("storyKeys"))
            for row in reverse_pptr_audit.get("directorHosts") or []
            if isinstance(row, dict)
        )
    )
    if (
        safe_key(timeline_ids.get("484"))
        != OFFLINE_EXHAUSTION_E11M4_CUTSCENE
        or not isinstance(cutscene_definition, dict)
        or safe_key(cutscene_definition.get("m_Name"))
        != OFFLINE_EXHAUSTION_E11M4_CUTSCENE
        or safe_key(cutscene_definition.get("Name"))
        != OFFLINE_EXHAUSTION_E11M4_CUTSCENE
        or not presentation_cutscene_valid
        or not text_only_cutscene_valid
    ):
        status["status"] = "inactive_cutscene_definition_validation_failed"
        return {}, status

    index: dict[str, dict[str, Any]] = {}
    for story_key in sorted(
        all_radio_keys,
        key=natural_key,
    ):
        index[story_key] = {
            "sceneKey": story_key,
            "missionId": radio_mission_by_key[story_key],
            "recoveryStatus":
                "deferred_current_build_offline_surface_exhausted",
            "evidenceKind": "radio_definition_without_recovered_consumer",
            "definitionTable": "RadioTable",
            "audioMembershipTable": "AudioDialog",
            "audioMembershipStatus": (
                "partial_current_audio_dialog_missing_ids"
                if story_key in missing_audio_ids_by_story
                else "present_current_audio_dialog"
            ),
            "missingAudioIds": sorted(
                missing_audio_ids_by_story.get(story_key) or set(),
                key=natural_key,
            ),
            "nativeMappingId": OFFLINE_EXHAUSTION_MAPPING_ID,
            "gameAssemblySha256":
                OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
            "consumerBoundary": (
                "exact ids occur only in current RadioTable definitions and "
                "AudioDialog membership where present across the audited "
                "MissionRuntime, LevelScript, "
                "GameplayConfig, Table, Lua, object-index, and direct native "
                "playback-caller surfaces"
            ),
            "reopenWhen": (
                "installed binary, exported tables, object index, Lua corpus, "
                "or another typed producer/consumer registry changes"
            ),
            "graphEffect": "none",
        }
    for story_key in sorted(
        OFFLINE_EXHAUSTION_REVERSE_HOST_COUNTS,
        key=natural_key,
    ):
        object_rows = gameobject_rows_by_key[story_key]
        director_hosts = reverse_hosts_by_key[story_key]
        index[story_key] = {
            "sceneKey": story_key,
            "missionId": cutscene_mission_by_key[story_key],
            "recoveryStatus":
                "deferred_current_build_offline_surface_exhausted",
            "evidenceKind": "cutscene_root_without_recovered_activator",
            "timelineRegistryId": (
                484
                if story_key == OFFLINE_EXHAUSTION_E11M4_CUTSCENE
                else None
            ),
            "directorHostCount": len(director_hosts),
            "nativeMappingId": OFFLINE_EXHAUSTION_MAPPING_ID,
            "playbackMappingId":
                OFFLINE_EXHAUSTION_REVERSE_PPTR_MAPPING_ID,
            "gameAssemblySha256":
                OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
            "logicalBundles": [
                row.get("logicalBundle") or {}
                for row in object_rows
            ],
            "candidateStatus":
                "no_typed_owner_or_runtime_sibling_or_descendant",
            "consumerBoundary": (
                "exact root Timeline assets resolve through PlayableDirector "
                "hosts and complete GameObject descendant hierarchies, but "
                "no typed owner/runtime component, structured action, Lua "
                "consumer, or direct native cutscene caller exposes an exact "
                "activator"
            ),
            "reopenWhen": (
                "installed binary, Timeline registry, object index, Lua "
                "corpus, or another typed producer/consumer registry changes"
            ),
            "graphEffect": "none",
        }
    index[text_only_key] = {
        "sceneKey": text_only_key,
        "missionId": "e11m1",
        "recoveryStatus":
            "deferred_current_build_offline_surface_exhausted",
        "evidenceKind":
            "text_table_only_cutscene_without_recovered_asset_or_consumer",
        "definitionTable": "TextTable",
        "definitionRowKeys": sorted(
            expected_text_only_row_keys,
            key=natural_key,
        ),
        "nativeMappingId": OFFLINE_EXHAUSTION_MAPPING_ID,
        "gameAssemblySha256": OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
        "consumerBoundary": (
            "the exact four-row TextTable group has no Timeline registry "
            "entry, indexed cutscene root, reverse PPtr relation, "
            "PlayableDirector host, structured action, Lua consumer, or "
            "direct native cutscene caller in the audited build"
        ),
        "reopenWhen": (
            "installed binary, TextTable, Timeline registry, object index, "
            "Lua corpus, or another typed producer/consumer registry changes"
        ),
        "graphEffect": "none",
    }
    status.update({
        "status": "active",
        "coreTargetSetSha256": core_target_digest,
        "deferredStoryKeys": len(index),
        "deferredMissions": sorted({
            row["missionId"]
            for row in index.values()
        }, key=natural_key),
        "deferredRadioStoryKeysByMission": {
            mission: sorted(story_keys, key=natural_key)
            for mission, story_keys in OFFLINE_EXHAUSTION_RADIOS_BY_MISSION.items()
        },
        "deferredCutsceneStoryKeysByMission": {
            mission: sorted(story_keys, key=natural_key)
            for mission, story_keys
            in OFFLINE_EXHAUSTION_CUTSCENES_BY_MISSION.items()
        },
    })
    return index, status


def _timeline(mission_payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(mission_payload, dict):
        return {}
    value = mission_payload.get("timelineRecovery")
    return value if isinstance(value, dict) else {}


def _flow(mission_payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(mission_payload, dict):
        return {}
    value = mission_payload.get("flow")
    return value if isinstance(value, dict) else {}


def _strict_quest_attachments(
    partial_row: dict[str, Any],
    flow: dict[str, Any] | None = None,
) -> tuple[set[str], set[str]]:
    quest_ids: set[str] = set()
    scene_keys: set[str] = set()
    for edge in partial_row.get("directEdges") or []:
        if not isinstance(edge, dict) or safe_key(edge.get("tier")) != "strong":
            continue
        edge_quest_ids = _string_list(edge.get("questIds"))
        if not edge_quest_ids:
            continue
        quest_ids.update(edge_quest_ids)
        for field in ("from", "to"):
            scene_key = safe_key(edge.get(field))
            if scene_key:
                scene_keys.add(scene_key)
    for row in _flow_story_connections(flow or {}):
        scene_key = safe_key(row.get("key"))
        occurrences = [
            occurrence
            for occurrence in row.get("levelScriptOccurrences") or []
            if isinstance(occurrence, dict)
        ]
        if (
            not scene_key
            or safe_key(row.get("relation")) != "levelscript_mission_context"
            or safe_key(row.get("confidence")) != "scoped_script"
            or row.get("hasUnscopedOrOtherMissionOccurrences") is not False
            or not occurrences
            or "mission_condition_checks_script"
            not in _string_list(row.get("scopeEvidenceKinds"))
        ):
            continue
        occurrence_quest_ids: set[str] = set()
        complete = True
        for occurrence in occurrences:
            conditions = [
                condition
                for condition in occurrence.get("missionConditions") or []
                if isinstance(condition, dict)
            ]
            if (
                not conditions
                or "mission_condition_checks_script"
                not in _string_list(occurrence.get("scopeEvidenceKinds"))
            ):
                complete = False
                break
            occurrence_quest_ids.update(
                safe_key(condition.get("questId"))
                for condition in conditions
                if safe_key(condition.get("questId"))
            )
        if complete and len(occurrence_quest_ids) == 1:
            quest_ids.update(occurrence_quest_ids)
            scene_keys.add(scene_key)
    return quest_ids, scene_keys


def _diagnostic_quest_attachments(
    timeline: dict[str, Any],
    candidate_scene_keys: set[str],
) -> tuple[set[str], set[str], Counter[str]]:
    quest_ids: set[str] = set()
    scene_keys: set[str] = set()
    source_counts: Counter[str] = Counter()
    placements = timeline.get("scenePlacement")
    if not isinstance(placements, dict):
        return quest_ids, scene_keys, source_counts
    for placement in placements.values():
        if not isinstance(placement, dict):
            continue
        scene_key = safe_key(placement.get("sceneKey"))
        if scene_key not in candidate_scene_keys:
            continue
        attached_ids = _string_list(placement.get("questIds"))
        if not attached_ids:
            continue
        quest_ids.update(attached_ids)
        scene_keys.add(scene_key)
        for source in placement.get("questAttachSources") or []:
            if isinstance(source, dict):
                source_counts[safe_key(source.get("source")) or "unknown"] += 1
    return quest_ids, scene_keys, source_counts


def _levelscript_context_gaps(
    timeline: dict[str, Any],
    flow: dict[str, Any],
    native_playback_index: dict[str, list[dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    """Return multi-scene contexts missing exact typed playback records.

    ``sourceBackedSceneSequences`` is intentionally not used here. Those
    generic UID/nextId chains include preload, remove, override, and stop
    actions and can cross physical ActionSerializedMap roots. A scene counts as
    typed only when the current-build formatter mapping resolves an actionList
    record to an actual playback class in this exact source file.
    """
    typed_by_file: dict[str, set[str]] = defaultdict(set)
    connections = list(flow.get("missionStoryConnections") or [])
    connections.extend(
        connection
        for quest in flow.get("quests") or []
        if isinstance(quest, dict)
        for connection in quest.get("storyConnections") or []
    )
    connections.extend(
        connection
        for connection in flow.get("unlinkedNativePlayback") or []
        if isinstance(connection, dict)
    )
    for connection in connections:
        if not isinstance(connection, dict):
            continue
        scene_key = safe_key(connection.get("key"))
        if not scene_key:
            continue
        exact_native_connection = (
            safe_key(connection.get("confidence"))
            in {"native_typed_direct", "native_typed_direct_unscoped"}
            and safe_key(connection.get("nativeMappingId")).startswith("gameassembly-")
        )
        occurrences = list(connection.get("levelScriptOccurrences") or [])
        if exact_native_connection:
            for field in ("occurrences", "nativeOccurrences", "nativeBlackActionOccurrences"):
                occurrences.extend(connection.get(field) or [])
        for occurrence in occurrences:
            if not isinstance(occurrence, dict):
                continue
            source_file = safe_key(occurrence.get("sourceFile"))
            action_map_role = safe_key(occurrence.get("actionMapRole"))
            record_class = safe_key(occurrence.get("recordClass"))
            if (
                source_file
                and action_map_role.startswith("actionList#")
                and record_class.startswith("play_")
                and safe_key(occurrence.get("actionName"))
            ):
                typed_by_file[source_file].add(scene_key)
        if (
            safe_key(connection.get("relation"))
            in {
                "levelscript_quest_completed_action",
                "levelscript_quest_processing_action",
            }
            and safe_key(connection.get("confidence")) == "native_typed_direct"
            and safe_key(connection.get("event")) == "LevelEvent_OnQuestStateChanged"
            and safe_key(connection.get("nativeMappingId")).startswith("gameassembly-")
            and safe_key(connection.get("actionName"))
            and safe_key(connection.get("sourceFile"))
        ):
            typed_by_file[safe_key(connection.get("sourceFile"))].add(scene_key)
        # Some exact native playback rows are represented by a stronger
        # mission-context relation rather than by the lower-level occurrence
        # list. Accept that form only when one exact LevelScript source file and
        # one typed playback step are both explicit.
        levelscript_source_files = [
            source_file
            for source_file in _string_list(connection.get("sourceFiles"))
            if "/LevelScriptData/" in ("/" + source_file.replace("\\", "/"))
        ]
        native_actions = set(_string_list(connection.get("nativeActions")))
        exact_playback_actions = {
            safe_key(step.get("actionName"))
            for owner in connection.get("nativeEventOwners") or []
            if (
                isinstance(owner, dict)
                and safe_key(owner.get("status")).startswith(
                    "exact_serialized_control_path"
                )
            )
            for step in owner.get("path") or []
            if (
                isinstance(step, dict)
                and safe_key(step.get("recordClass")).startswith("play_")
                and safe_key(step.get("actionName"))
            )
        }
        if (
            len(levelscript_source_files) == 1
            and native_actions & exact_playback_actions
        ):
            typed_by_file[levelscript_source_files[0]].add(scene_key)

    # A weaker mission/quest context can cause the Story bundle assembler to
    # omit a redundant unlinked-native row.  That omission must not make the
    # recovery queue call an already decoded ActionBase playback record
    # "untyped."  Consult the current-build binary index directly, while still
    # requiring the exact source file, actionList membership, playback class,
    # Story identity, and GameAssembly mapping.  This proves record type only;
    # it creates neither mission ownership nor chronology.
    for scene_key, occurrences in (native_playback_index or {}).items():
        for occurrence in occurrences or []:
            if not isinstance(occurrence, dict):
                continue
            source_file = safe_key(occurrence.get("sourceFile"))
            if (
                source_file
                and safe_key(occurrence.get("actionMapRole")).startswith(
                    "actionList#"
                )
                and safe_key(occurrence.get("recordClass")).startswith("play_")
                and safe_key(occurrence.get("actionName"))
                and safe_key(occurrence.get("nativeMappingId")).startswith(
                    "gameassembly-"
                )
                and scene_key in {
                    safe_key(value)
                    for value in occurrence.get("allStoryKeysInRecord") or []
                }
            ):
                typed_by_file[source_file].add(scene_key)

    rows: list[dict[str, Any]] = []
    for context in timeline.get("sourceBackedStoryCallContexts") or []:
        if not isinstance(context, dict):
            continue
        scene_keys = _string_list(context.get("sceneKeys"))
        if len(scene_keys) < 2:
            continue
        source_file = safe_key(context.get("sourceFile"))
        typed_scene_keys = typed_by_file.get(source_file, set())
        unresolved = [key for key in scene_keys if key not in typed_scene_keys]
        if len(typed_scene_keys & set(scene_keys)) >= len(scene_keys):
            continue
        rows.append({
            "sourceFile": source_file,
            "levelId": safe_key(context.get("levelId")),
            "sceneKeys": scene_keys,
            "typedSceneKeys": sorted(typed_scene_keys & set(scene_keys), key=natural_key),
            "unresolvedSceneKeys": unresolved,
        })
    rows.sort(key=lambda row: (natural_key(row["sourceFile"]), natural_key(row["sceneKeys"][0])))
    return rows


def _classify_levelscript_context_gaps(
    context_gaps: list[dict[str, Any]],
    action_story_occurrences: dict[str, list[dict[str, Any]]] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Separate actionable ActionBase gaps from exact binary-negative rows.

    ``None`` means that no exhaustive action occurrence scan was supplied, so
    every row stays actionable.  An explicit mapping is treated as the complete
    current-build actionList census.  A Story key with no same-file actionList
    occurrence is therefore a non-action serialized reference for this
    context, while a fully mapped preload/override/remove/stop occurrence is a
    known non-playback action.  Both remain visible, but neither is a missing
    typed-playback decoder.
    """
    if action_story_occurrences is None:
        return context_gaps, []

    actionable: list[dict[str, Any]] = []
    closed: list[dict[str, Any]] = []
    closed_statuses = {
        "known_non_playback_action_only",
        "non_action_story_reference",
    }
    for raw_context in context_gaps:
        context = dict(raw_context)
        source_file = safe_key(context.get("sourceFile"))
        classifications: list[dict[str, Any]] = []
        for scene_key in _string_list(context.get("unresolvedSceneKeys")):
            occurrences = [
                occurrence
                for occurrence in action_story_occurrences.get(scene_key, [])
                if (
                    isinstance(occurrence, dict)
                    and safe_key(occurrence.get("sourceFile")) == source_file
                    and safe_key(occurrence.get("actionMapRole")).startswith(
                        "actionList#"
                    )
                )
            ]
            evidence: list[dict[str, Any]] = []
            has_unmapped_action = False
            for occurrence in occurrences:
                action_code = safe_key(occurrence.get("actionCode")).lower()
                action_kind = safe_key(occurrence.get("actionKind")).lower()
                action_name = safe_key(occurrence.get("actionName"))
                record_class = safe_key(occurrence.get("recordClass"))
                mapping_id = safe_key(occurrence.get("nativeMappingId"))
                if not action_name or not record_class:
                    mapped = KNOWN_NON_PLAYBACK_ACTIONS.get(
                        (action_code, action_kind)
                    )
                    if mapped:
                        action_name, record_class = mapped
                        mapping_id = KNOWN_NON_PLAYBACK_MAPPING_ID
                    else:
                        has_unmapped_action = True
                evidence.append({
                    key: value
                    for key, value in {
                        "actionCode": action_code,
                        "actionKind": action_kind,
                        "actionName": action_name,
                        "recordClass": record_class,
                        "actionMapRole": safe_key(
                            occurrence.get("actionMapRole")
                        ),
                        "localId": occurrence.get("localId"),
                        "recordOffset": occurrence.get("recordOffset"),
                        "nativeMappingId": mapping_id,
                    }.items()
                    if value not in ("", None)
                })

            if not occurrences:
                status = "non_action_story_reference"
            elif (
                not has_unmapped_action
                and evidence
                and all(
                    safe_key(row.get("recordClass"))
                    and not safe_key(row.get("recordClass")).startswith("play_")
                    for row in evidence
                )
            ):
                status = "known_non_playback_action_only"
            else:
                status = "unmapped_action_record"
            classifications.append({
                "sceneKey": scene_key,
                "status": status,
                "actionOccurrences": evidence,
            })

        context["unresolvedBinaryClassifications"] = classifications
        context["recoveryStatus"] = (
            "closed_no_typed_playback_order_evidence"
            if classifications
            and all(row["status"] in closed_statuses for row in classifications)
            else "actionable_typed_playback_decoder_gap"
        )
        if context["recoveryStatus"].startswith("closed_"):
            closed.append(context)
        else:
            actionable.append(context)
    return actionable, closed


def _frontier_contributions(metrics: dict[str, int]) -> dict[str, int]:
    return {
        "missing-mission-runtime-bundle": metrics["missingMissionBundle"] * 100,
        "levelscript-control-flow": (
            metrics["untypedMultiSceneLevelscriptContexts"] * 10
            + metrics["actionableWeakOnlyScenes"] * 4
        ),
        "source-cycle-review": metrics["sourceCycles"] * 20 + metrics["cycleScenes"] * 8,
        "quest-scene-attachment": metrics["questIdsWithoutStrictStoryAttachment"] * 3,
        "dialog-option-runtime": (
            metrics["actionableNoExplicitOptionRouteGroups"] * 2
            + metrics["actionableExcludedOptionEvidenceGroups"] * 2
        ),
        "unresolved-source-node": metrics["unresolvedSourceNodes"] * 4,
        "isolated-scene-source-link":
            metrics["actionableCoreIsolatedScenes"] * 5,
    }


def _flow_story_connections(flow: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        row
        for row in flow.get("missionStoryConnections") or []
        if isinstance(row, dict)
    ]
    rows.extend(
        row
        for quest in flow.get("quests") or []
        if isinstance(quest, dict)
        for row in quest.get("storyConnections") or []
        if isinstance(row, dict)
    )
    for field in ("unlinkedNativePlayback", "unlinkedDefinitionOnly"):
        rows.extend(
            row
            for row in flow.get(field) or []
            if isinstance(row, dict)
        )
    return rows


def _connection_native_occurrences(
    connection: dict[str, Any],
    scene_key: str,
    occurrence_fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    occurrences = [
        occurrence
        for field in occurrence_fields
        for occurrence in connection.get(field) or []
        if isinstance(occurrence, dict)
    ]
    if occurrences:
        return occurrences

    # Some stronger context rows compact one exact native path directly onto
    # the connection instead of repeating its lower-level occurrence record.
    # Reconstruct only the minimum occurrence shape needed by the closure
    # classifier, and only when the playback step itself carries this exact
    # Story key.
    level_ids = _string_list(connection.get("levelIds"))
    script_ids = _string_list(connection.get("scriptIds"))
    source_files = [
        source_file
        for source_file in _string_list(connection.get("sourceFiles"))
        if "/LevelScriptData/" in ("/" + source_file.replace("\\", "/"))
    ]
    if len(level_ids) != 1 or len(script_ids) != 1 or len(source_files) != 1:
        return []
    synthetic: list[dict[str, Any]] = []
    for owner in connection.get("nativeEventOwners") or []:
        if not isinstance(owner, dict):
            continue
        for step in owner.get("path") or []:
            if (
                not isinstance(step, dict)
                or not safe_key(step.get("recordClass")).startswith("play_")
                or not safe_key(step.get("actionName"))
                or scene_key not in _string_list(step.get("texts"))
                or not isinstance(step.get("localId"), int)
            ):
                continue
            synthetic.append({
                "levelId": level_ids[0],
                "scriptId": script_ids[0],
                "sourceFile": source_files[0],
                "actionMapRole": "actionList#exact-native-owner-path",
                "allStoryKeysInRecord": [scene_key],
                "localId": step["localId"],
                "actionName": safe_key(step.get("actionName")),
                "recordClass": safe_key(step.get("recordClass")),
                "nativeEventOwners": [owner],
            })
    return synthetic


def _closed_exact_native_unordered_scenes(
    flow: dict[str, Any],
    weak_only_scene_keys: set[str],
    native_playback_index: dict[str, list[dict[str, Any]]] | None = None,
    incident_levelscript_files: dict[str, set[str]] | None = None,
) -> tuple[list[dict[str, Any]], set[str]]:
    """Return unordered scenes whose native playback route is already exact.

    These rows do not lack LevelScript control-flow recovery. Their typed
    playback action is reached by a complete serialized event-to-action path,
    but that event supplies no prefix-comparable second Story action. File
    order, trigger-slot numbers, and OCR cannot fill that absence.
    """
    occurrence_fields = (
        "levelScriptOccurrences",
        "nativeOccurrences",
        "occurrences",
        "nativeBlackActionOccurrences",
        "parentDialogNativeOccurrences",
    )
    occurrences_by_scene: dict[str, dict[tuple[Any, ...], dict[str, Any]]] = (
        defaultdict(dict)
    )
    exact_stub_scopes: dict[str, set[tuple[str, str, str]]] = defaultdict(set)
    exact_control_path_statuses = {
        "exact_serialized_control_path",
        "exact_serialized_control_path_equivalent_duplicates",
    }
    for connection in _flow_story_connections(flow):
        scene_key = safe_key(connection.get("key"))
        if scene_key not in weak_only_scene_keys:
            continue
        for occurrence in _connection_native_occurrences(
            connection,
            scene_key,
            occurrence_fields,
        ):
            level_id = safe_key(occurrence.get("levelId"))
            script_id = safe_key(occurrence.get("scriptId"))
            source_file = safe_key(occurrence.get("sourceFile"))
            if any(
                isinstance(owner, dict)
                and owner.get("status") in exact_control_path_statuses
                for owner in occurrence.get("nativeEventOwners") or []
            ):
                exact_stub_scopes[scene_key].add(
                    (level_id, script_id, source_file)
                )
            if (
                not safe_key(occurrence.get("actionMapRole")).startswith(
                    "actionList#"
                )
                or not safe_key(occurrence.get("recordClass")).startswith(
                    "play_"
                )
                or not safe_key(occurrence.get("actionName"))
            ):
                continue
            record_story_keys = _string_list(
                occurrence.get("allStoryKeysInRecord")
            )
            if record_story_keys and scene_key not in record_story_keys:
                continue
            signature = (
                level_id,
                script_id,
                source_file,
                occurrence.get("recordOffset"),
                occurrence.get("localId"),
            )
            occurrences_by_scene[scene_key][signature] = occurrence

    incident_levelscript_files = incident_levelscript_files or {}
    for scene_key in weak_only_scene_keys:
        accepted_files = incident_levelscript_files.get(scene_key) or set()
        accepted_scopes = exact_stub_scopes.get(scene_key) or set()
        for occurrence in (native_playback_index or {}).get(scene_key) or []:
            if not isinstance(occurrence, dict):
                continue
            scope = (
                safe_key(occurrence.get("levelId")),
                safe_key(occurrence.get("scriptId")),
                safe_key(occurrence.get("sourceFile")),
            )
            if scope not in accepted_scopes and scope[2] not in accepted_files:
                continue
            signature = (
                *scope,
                occurrence.get("recordOffset"),
                occurrence.get("localId"),
            )
            occurrences_by_scene[scene_key][signature] = occurrence

    closed: list[dict[str, Any]] = []
    incomplete: set[str] = set()
    for scene_key in sorted(weak_only_scene_keys, key=natural_key):
        occurrences = list(occurrences_by_scene.get(scene_key, {}).values())
        if not occurrences:
            continue
        evidence: list[dict[str, Any]] = []
        complete = True
        for occurrence in occurrences:
            action_local_id = occurrence.get("localId")
            exact_owners = []
            for owner in occurrence.get("nativeEventOwners") or []:
                if (
                    not isinstance(owner, dict)
                    or owner.get("status") not in exact_control_path_statuses
                    or not isinstance(owner.get("headerLocalId"), int)
                ):
                    continue
                path_local_ids = [
                    step.get("localId")
                    for step in owner.get("path") or []
                    if isinstance(step, dict)
                    and isinstance(step.get("localId"), int)
                ]
                if (
                    not path_local_ids
                    or not isinstance(action_local_id, int)
                    or action_local_id not in path_local_ids
                ):
                    continue
                exact_owners.append((owner, path_local_ids))
            if not exact_owners:
                complete = False
                incomplete.add(scene_key)
                break
            for owner, path_local_ids in exact_owners:
                event_detail = (
                    owner.get("eventDetail")
                    if isinstance(owner.get("eventDetail"), dict)
                    else {}
                )
                evidence.append({
                    "levelId": safe_key(occurrence.get("levelId")),
                    "scriptId": safe_key(occurrence.get("scriptId")),
                    "sourceFile": safe_key(occurrence.get("sourceFile")),
                    "headerName": safe_key(owner.get("headerName")),
                    "headerLocalId": owner.get("headerLocalId"),
                    "controlPathStatus": safe_key(owner.get("status")),
                    "eventSummary": safe_key(event_detail.get("summary")),
                    "actionName": safe_key(occurrence.get("actionName")),
                    "actionLocalId": action_local_id,
                    "pathLocalIds": path_local_ids,
                })
        if complete and evidence:
            closed.append({
                "sceneKey": scene_key,
                "recoveryStatus":
                    "closed_exact_native_event_path_no_relative_order",
                "nativeEventPaths": evidence,
            })
            incomplete.discard(scene_key)
    return closed, incomplete


def _closed_non_mission_content_isolated_scenes(
    isolated_scene_keys: set[str],
    non_mission_content: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Keep exact authored non-mission content out of the narrative queue."""
    closed: list[dict[str, Any]] = []
    for scene_key in sorted(isolated_scene_keys, key=natural_key):
        row = non_mission_content.get(scene_key)
        if row is None:
            continue
        if row.get("evidenceKind") == "guide_runtime_asset":
            closed.append({
                "sceneKey": scene_key,
                "recoveryStatus":
                    "closed_exact_guide_runtime_non_mission_content",
                "evidenceKind": "guide_runtime_asset",
                "contentClass": row.get("content"),
                "assetType": row.get("assetType"),
                "consumerClass": row.get("consumerClass"),
                "assetCount": row.get("assetCount"),
                "actionCount": row.get("actionCount"),
                "assetNames": row.get("assetNames") or [],
                "guideLevelIds": row.get("guideLevelIds") or [],
                "nativeMappingId": row.get("nativeMappingId"),
                "nativeMethod": row.get("nativeMethod") or {},
                "orderBoundary": row.get("orderBoundary"),
                "evidenceReport": row.get("evidenceReport"),
            })
        else:
            closed.append({
                "sceneKey": scene_key,
                "recoveryStatus": "closed_table_backed_non_mission_content",
                "evidenceKind": "authored_table",
                "definitionTable": row["table"],
                "definitionField": row["field"],
                "tableKeyedBy": row["keyedBy"],
                "contentClass": row["content"],
            })
    return closed


def _closed_definition_only_isolated_scenes(
    flow: dict[str, Any],
    isolated_scene_keys: set[str],
) -> list[dict[str, Any]]:
    """Keep exact current-build no-consumer classifications out of the queue."""
    closed: list[dict[str, Any]] = []
    for row in flow.get("unlinkedDefinitionOnly") or []:
        if not isinstance(row, dict):
            continue
        scene_key = safe_key(row.get("key"))
        if (
            scene_key not in isolated_scene_keys
            or safe_key(row.get("relation"))
            != "original_text_definition_without_consumer"
            or safe_key(row.get("phase")) != "definition_only"
            or safe_key(row.get("confidence"))
            != "current_build_no_consumer"
            or safe_key(row.get("consumerSearchStatus"))
            != "no_current_original_game_consumer_recovered"
            or safe_key(row.get("bindingStatus"))
            != "definition_only_unlinked"
        ):
            continue
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_current_build_definition_without_consumer",
            "source": safe_key(row.get("source")),
            "searchedConsumerKinds": _string_list(
                row.get("searchedConsumerKinds")
            ),
            "serverEvidenceStatus": safe_key(
                row.get("serverEvidenceStatus")
            ),
        })
    return sorted(closed, key=lambda row: natural_key(row["sceneKey"]))


def _deferred_offline_exhausted_isolated_scenes(
    flow: dict[str, Any],
    isolated_scene_keys: set[str],
    owner_mission: str,
    offline_exhaustion_index: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Defer exact-build exhausted rows without asserting a graph fact."""
    unlinked_keys = set(_string_list(flow.get("unlinked")))
    routed_keys = {
        safe_key(row.get("key"))
        for row in _flow_story_connections(flow)
        if isinstance(row, dict) and safe_key(row.get("key"))
    }
    deferred: list[dict[str, Any]] = []
    for scene_key in sorted(isolated_scene_keys, key=natural_key):
        evidence = offline_exhaustion_index.get(scene_key)
        if (
            not isinstance(evidence, dict)
            or safe_key(evidence.get("missionId")) != owner_mission
            or scene_key not in unlinked_keys
            or scene_key in routed_keys
            or evidence.get("graphEffect") != "none"
            or evidence.get("recoveryStatus")
            != "deferred_current_build_offline_surface_exhausted"
        ):
            continue
        deferred.append(dict(evidence))
    return deferred


def _closed_exact_dialog_tree_embedded_isolated_scenes(
    flow: dict[str, Any],
    isolated_scene_keys: set[str],
    owner_mission: str,
) -> list[dict[str, Any]]:
    """Close exact nested DialogTree text placement without a file edge.

    A narrative-mask Story file can be embedded between two trunk lines of
    its parent DialogTree. The typed serialized connection edges establish
    that line-level placement, but the parent file contains content both
    before and after the nested file. Treating that as ``parent -> child`` or
    ``child -> parent`` would therefore be false at scene-file granularity.
    """
    allowed_confidences = {
        "native_exact_parent_quest",
        "native_derived_exact_parent_quest",
        "native_derived_exact_parent_mission_area_shell",
        "native_derived_exact_parent_shell",
        "native_exact_parent_context",
    }
    allowed_evidence_tiers = {
        "native_direct",
        "derived_exact_quest",
        "derived_exact_shell",
        "native_direct_mission_context",
    }
    rows_by_scene: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        if (
            scene_key in isolated_scene_keys
            and safe_key(row.get("relation"))
            == "dialog_tree_narrative_action"
        ):
            rows_by_scene[scene_key].append(row)

    closed: list[dict[str, Any]] = []
    for scene_key, rows in rows_by_scene.items():
        exact_rows: list[dict[str, Any]] = []
        complete = True
        for row in rows:
            parent_story_key = safe_key(row.get("parentStoryKey"))
            occurrence_rows = [
                occurrence
                for occurrence in row.get("dialogTreeNarrativeActions") or []
                if isinstance(occurrence, dict)
            ]
            all_parent_story_keys = set(
                _string_list(row.get("allParentStoryKeys"))
            )
            if (
                not parent_story_key
                or safe_key(row.get("storyOwnerMission")) != owner_mission
                or safe_key(row.get("confidence")) not in allowed_confidences
                or safe_key(row.get("evidenceTier"))
                not in allowed_evidence_tiers
                or safe_key(row.get("scopeCompleteness")) != "complete"
                or row.get("unscopedParentStoryKeys")
                or parent_story_key not in all_parent_story_keys
                or safe_key(row.get("embeddedLinePlacementStatus"))
                != "exact_complete_connection_neighbors"
                or safe_key(row.get("nativeMappingId"))
                != DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID
                or not _string_list(row.get("embeddedAfterLineIds"))
                or not _string_list(row.get("embeddedBeforeLineIds"))
                or not occurrence_rows
                or int(row.get("occurrenceCount") or 0)
                != len(occurrence_rows)
            ):
                complete = False
                break
            for occurrence in occurrence_rows:
                if (
                    safe_key(occurrence.get("dialogKey"))
                    != parent_story_key
                    or safe_key(
                        occurrence.get(
                            "dialogTreeConnectionPlacementStatus"
                        )
                    )
                    != "exact_unique_adjacent_parent_trunks"
                    or safe_key(occurrence.get("nativeMappingId"))
                    != DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID
                    or occurrence.get("reachableFromPrimeNode") is not True
                    or not _string_list(
                        occurrence.get("primeToActionNodePath")
                    )
                    or not safe_key(occurrence.get("textId"))
                    or not safe_key(occurrence.get("actionPath"))
                    or not safe_key(occurrence.get("nodeId"))
                    or not safe_key(occurrence.get("sourceFile"))
                    or not _string_list(
                        occurrence.get("embeddedAfterLineIds")
                    )
                    or not _string_list(
                        occurrence.get("embeddedBeforeLineIds")
                    )
                ):
                    complete = False
                    break
            if not complete:
                break
            exact_rows.append(row)
        if not complete or not exact_rows:
            continue
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_native_embedded_line_context_no_file_order",
            "relation": "dialog_tree_narrative_action",
            "parentStoryKeys": sorted({
                safe_key(row.get("parentStoryKey"))
                for row in exact_rows
                if safe_key(row.get("parentStoryKey"))
            }, key=natural_key),
            "embeddedAfterLineIds": sorted({
                line_id
                for row in exact_rows
                for line_id in _string_list(
                    row.get("embeddedAfterLineIds")
                )
            }, key=natural_key),
            "embeddedBeforeLineIds": sorted({
                line_id
                for row in exact_rows
                for line_id in _string_list(
                    row.get("embeddedBeforeLineIds")
                )
            }, key=natural_key),
            "sourceFiles": sorted({
                source_file
                for row in exact_rows
                for source_file in _string_list(row.get("sourceFiles"))
            }),
            "sourcePathIds": sorted({
                path_id
                for row in exact_rows
                for path_id in _string_list(row.get("sourcePathIds"))
            }),
            "nativeMappingId":
                DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID,
            "orderBoundary": (
                "exact serialized line neighbors are retained, but the "
                "parent Story file has content on both sides and cannot be "
                "placed wholly before or after the nested file"
            ),
        })
    return sorted(closed, key=lambda row: natural_key(row["sceneKey"]))


def _closed_exact_dialog_tree_embedded_context_isolated_scenes(
    flow: dict[str, Any],
    isolated_scene_keys: set[str],
    owner_mission: str,
) -> list[dict[str, Any]]:
    """Close an exact nested playback consumer with unresolved line position.

    This is narrower than a recovered embedded line placement. Every serialized
    narrative action, source object, prime-node path, and parent Story scope
    must be exact and complete, but one or both adjacent parent trunk lines are
    still unavailable. That resolves the source-link/consumer gap only. It does
    not create a Story-file edge or claim an exact line position.
    """
    allowed_confidences = {
        "native_exact_parent_quest",
        "native_derived_exact_parent_quest",
        "native_derived_exact_parent_mission_area_shell",
        "native_derived_exact_parent_shell",
        "native_exact_parent_context",
    }
    allowed_evidence_tiers = {
        "native_direct",
        "derived_exact_quest",
        "derived_exact_shell",
        "native_direct_mission_context",
    }
    allowed_action_types = {
        "Beyond.Gameplay.DialogComplexNarrativeMaskActionData",
        "Beyond.Gameplay.DialogNarrativeMaskActionData",
    }
    allowed_action_kinds = {"complex_narrative", "narrative"}
    allowed_occurrence_placements = {
        "exact_unique_adjacent_parent_trunks",
        "no_exact_unique_adjacent_parent_trunks",
    }
    allowed_row_placements = {
        "exact_complete_connection_neighbors",
        "not_exact_complete_connection_neighbors",
    }
    rows_by_scene: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        if (
            scene_key in isolated_scene_keys
            and safe_key(row.get("relation"))
            == "dialog_tree_narrative_action"
        ):
            rows_by_scene[scene_key].append(row)

    closed: list[dict[str, Any]] = []
    for scene_key, rows in rows_by_scene.items():
        exact_rows: list[dict[str, Any]] = []
        unresolved_placements: list[dict[str, Any]] = []
        complete = True
        saw_unresolved_placement = False
        for row in rows:
            parent_story_key = safe_key(row.get("parentStoryKey"))
            occurrence_rows = [
                occurrence
                for occurrence in row.get("dialogTreeNarrativeActions") or []
                if isinstance(occurrence, dict)
            ]
            all_parent_story_keys = set(
                _string_list(row.get("allParentStoryKeys"))
            )
            row_placement = safe_key(
                row.get("embeddedLinePlacementStatus")
            )
            if (
                not parent_story_key
                or safe_key(row.get("storyOwnerMission")) != owner_mission
                or safe_key(row.get("confidence")) not in allowed_confidences
                or safe_key(row.get("evidenceTier"))
                not in allowed_evidence_tiers
                or safe_key(row.get("scopeCompleteness")) != "complete"
                or row.get("unscopedParentStoryKeys")
                or parent_story_key not in all_parent_story_keys
                or row_placement not in allowed_row_placements
                or safe_key(row.get("nativeMappingId"))
                != DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID
                or not _string_list(row.get("sourceFiles"))
                or not _string_list(row.get("sourcePathIds"))
                or not occurrence_rows
                or int(row.get("occurrenceCount") or 0)
                != len(occurrence_rows)
            ):
                complete = False
                break
            if row_placement == "not_exact_complete_connection_neighbors":
                saw_unresolved_placement = True
            for occurrence in occurrence_rows:
                placement = safe_key(
                    occurrence.get(
                        "dialogTreeConnectionPlacementStatus"
                    )
                )
                if (
                    safe_key(occurrence.get("dialogKey"))
                    != parent_story_key
                    or safe_key(occurrence.get("actionType"))
                    not in allowed_action_types
                    or safe_key(occurrence.get("actionKind"))
                    not in allowed_action_kinds
                    or placement not in allowed_occurrence_placements
                    or safe_key(occurrence.get("nativeMappingId"))
                    != DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID
                    or occurrence.get("reachableFromPrimeNode") is not True
                    or not _string_list(
                        occurrence.get("primeToActionNodePath")
                    )
                    or not safe_key(occurrence.get("textId"))
                    or not safe_key(occurrence.get("actionPath"))
                    or not safe_key(occurrence.get("nodeId"))
                    or not safe_key(occurrence.get("sourceFile"))
                    or not safe_key(occurrence.get("sourcePathId"))
                ):
                    complete = False
                    break
                if placement == "no_exact_unique_adjacent_parent_trunks":
                    saw_unresolved_placement = True
                    unresolved_placements.append({
                        "parentStoryKey": parent_story_key,
                        "textId": safe_key(occurrence.get("textId")),
                        "actionType": safe_key(
                            occurrence.get("actionType")
                        ),
                        "actionPath": safe_key(
                            occurrence.get("actionPath")
                        ),
                        "nodeId": safe_key(occurrence.get("nodeId")),
                        "incomingNodeIds": _string_list(
                            occurrence.get("incomingNodeIds")
                        ),
                        "outgoingNodeIds": _string_list(
                            occurrence.get("outgoingNodeIds")
                        ),
                        "immediatelyPrecedingTrunkIds": _string_list(
                            occurrence.get(
                                "immediatelyPrecedingTrunkIds"
                            )
                        ),
                        "immediatelyFollowingTrunkIds": _string_list(
                            occurrence.get(
                                "immediatelyFollowingTrunkIds"
                            )
                        ),
                        "sourceFile": safe_key(
                            occurrence.get("sourceFile")
                        ),
                        "sourcePathId": safe_key(
                            occurrence.get("sourcePathId")
                        ),
                        "placementStatus": placement,
                    })
            if not complete:
                break
            exact_rows.append(row)
        if (
            not complete
            or not exact_rows
            or not saw_unresolved_placement
            or not unresolved_placements
        ):
            continue
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus": (
                "closed_exact_native_embedded_playback_context_"
                "line_position_unresolved_no_file_order"
            ),
            "relation": "dialog_tree_narrative_action",
            "parentStoryKeys": sorted({
                safe_key(row.get("parentStoryKey"))
                for row in exact_rows
                if safe_key(row.get("parentStoryKey"))
            }, key=natural_key),
            "sourceFiles": sorted({
                source_file
                for row in exact_rows
                for source_file in _string_list(row.get("sourceFiles"))
            }),
            "sourcePathIds": sorted({
                path_id
                for row in exact_rows
                for path_id in _string_list(row.get("sourcePathIds"))
            }),
            "unresolvedLinePlacements": sorted(
                unresolved_placements,
                key=lambda row: (
                    natural_key(row["parentStoryKey"]),
                    natural_key(row["textId"]),
                    natural_key(row["nodeId"]),
                ),
            ),
            "nativeMappingId":
                DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID,
            "linePlacementStatus":
                "exact_parent_playback_line_position_unresolved",
            "orderBoundary": (
                "the exact typed serialized playback consumer, source "
                "object, prime-node path, and parent Story scope are "
                "recovered; one or both adjacent parent trunk lines remain "
                "unknown, and no Story-file edge is emitted"
            ),
        })
    return sorted(closed, key=lambda row: natural_key(row["sceneKey"]))


def _closed_exact_timeline_dialog_embedded_isolated_scenes(
    flow: dict[str, Any],
    isolated_scene_keys: set[str],
    mission: str,
) -> list[dict[str, Any]]:
    """Close exact Timeline-embedded Story playback with content on both sides."""
    accepted_host_missions = {
        mission,
        *_string_list(flow.get("_sourceVariantMissionIds")),
    }
    closed: list[dict[str, Any]] = []
    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        parent_story_key = safe_key(row.get("parentStoryKey"))
        text_ids = set(_string_list(row.get("textIds")))
        timeline_ids = set(_string_list(row.get("timelines")))
        source_files = set(_string_list(row.get("sourceFiles")))
        attachments = [
            attachment
            for attachment in row.get("timelineAttachments") or []
            if isinstance(attachment, dict)
        ]
        parent_occurrences = [
            occurrence
            for occurrence in row.get("parentDialogNativeOccurrences") or []
            if isinstance(occurrence, dict)
        ]
        if (
            scene_key not in isolated_scene_keys
            or safe_key(row.get("relation"))
            != "timeline_dialog_contains_black"
            or safe_key(row.get("confidence")) != "native_exact_host"
            or safe_key(row.get("storyOwnerMission")) != mission
            or not parent_story_key
            or not text_ids
            or not timeline_ids
            or not source_files
            or len(attachments) != len(text_ids)
            or int(row.get("occurrenceCount") or 0) != len(text_ids)
            or not parent_occurrences
        ):
            continue
        if any(
            safe_key(attachment.get("key")) != scene_key
            or safe_key(attachment.get("textId")) not in text_ids
            or safe_key(attachment.get("dialogKey")) != parent_story_key
            or safe_key(attachment.get("timeline")) not in timeline_ids
            or safe_key(attachment.get("sourceFile")) not in source_files
            or safe_key(attachment.get("dialogJoin"))
            != "dialog_id_table_used_timeline"
            or not safe_key(attachment.get("assetPath"))
            or not safe_key(attachment.get("trackPath"))
            or not safe_key(attachment.get("rootPath"))
            for attachment in attachments
        ):
            continue
        native_paths: list[dict[str, Any]] = []
        valid = True
        for occurrence in parent_occurrences:
            action_local_id = occurrence.get("localId")
            if (
                safe_key(occurrence.get("recordClass")) != "play_dialog"
                or not safe_key(occurrence.get("actionName"))
                or parent_story_key
                not in _string_list(occurrence.get("allStoryKeysInRecord"))
                or not isinstance(action_local_id, int)
            ):
                valid = False
                break
            level_data_hosts = [
                host
                for host in occurrence.get("levelDataHosts") or []
                if isinstance(host, dict)
            ]
            if (
                not level_data_hosts
                or any(
                    safe_key(host.get("missionId"))
                    not in accepted_host_missions
                    or not safe_key(host.get("levelDataFile"))
                    for host in level_data_hosts
                )
            ):
                valid = False
                break
            exact_owners = [
                owner
                for owner in occurrence.get("nativeEventOwners") or []
                if (
                    isinstance(owner, dict)
                    and safe_key(owner.get("status"))
                    in {
                        "exact_serialized_control_path",
                        "exact_serialized_control_path_equivalent_duplicates",
                    }
                    and action_local_id
                    in {
                        step.get("localId")
                        for step in owner.get("path") or []
                        if isinstance(step, dict)
                    }
                )
            ]
            if not exact_owners:
                valid = False
                break
            native_paths.extend({
                "levelId": safe_key(occurrence.get("levelId")),
                "scriptId": safe_key(occurrence.get("scriptId")),
                "sourceFile": safe_key(occurrence.get("sourceFile")),
                "headerName": safe_key(owner.get("headerName")),
                "headerLocalId": owner.get("headerLocalId"),
                "actionName": safe_key(occurrence.get("actionName")),
                "actionLocalId": action_local_id,
            } for owner in exact_owners)
        if not valid:
            continue
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_native_timeline_embedded_playback_context_"
                "no_file_order",
            "relation": "timeline_dialog_contains_black",
            "parentStoryKey": parent_story_key,
            "timelineIds": sorted(timeline_ids, key=natural_key),
            "textIds": sorted(text_ids, key=natural_key),
            "nativeEventPaths": native_paths,
            "placementBoundary": (
                "the exact parent playback path and Timeline clips establish "
                "embedded playback; parent dialog content occurs on both "
                "sides, so no scene-file edge is created"
            ),
            "graphEffect": "none",
        })
    return sorted(closed, key=lambda row: natural_key(row["sceneKey"]))


def _closed_exact_runtime_config_isolated_scenes(
    flow: dict[str, Any],
    isolated_scene_keys: set[str],
    owner_mission: str,
) -> list[dict[str, Any]]:
    """Close exact executable Story configs that encode no chronology.

    ``NpcProxyEx`` rows are executable configuration, not loose name matches:
    the installed client selects ``exDatas[activeCondIndex - 1]`` and
    ``NpcInteractComponent`` reads that row's ``dialogId``.  The adjacent
    ``missionId`` is consumed separately by the paused-mission deactivation
    guard.  This establishes a mission-scoped, selectable interaction dialog,
    but the server-selected row index and proxy/table ordering do not establish
    relative Story order.

    Counted LevelScript interactive maps are similarly exact: a typed
    ``LevelInteractiveData`` record's component-94 ``type_id`` selects one
    dialog or ReadingPopUp Story file. This recovers the source script and
    interactive identity, but neither map/local-id order nor object placement
    establishes activation timing or relative Story order.
    """
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        mission_id = safe_key(row.get("npcProxyMissionId"))
        context_mission_bundle = safe_key(
            row.get("contextMissionBundle")
        )
        if (
            scene_key not in isolated_scene_keys
            or safe_key(row.get("relation"))
            != "npc_proxy_ex_mission_context"
            or safe_key(row.get("confidence")) != "direct_mission_scope"
            or safe_key(row.get("source"))
            != "NpcProxyExDataTable.data[*].missionId + dialogId"
            or not safe_key(row.get("npcProxyId"))
            or not mission_id
            or safe_key(row.get("storyOwnerMission")) != owner_mission
            or (
                mission_id != owner_mission
                and context_mission_bundle != mission_id
            )
            or safe_key(row.get("nativeMappingId"))
            != NPC_PROXY_DIALOG_SELECTION_MAPPING_ID
            or safe_key(row.get("gameAssemblySha256"))
            != NPC_PROXY_DIALOG_SELECTION_GAMEASSEMBLY_SHA256
            or safe_key(row.get("selectionOrderStatus"))
            != (
                "one_based_active_row_selection_only_no_cross_row_"
                "chronology"
            )
        ):
            continue
        grouped[scene_key].append(row)

    closed: list[dict[str, Any]] = []
    for scene_key, rows in grouped.items():
        mission_ids = {
            safe_key(row.get("npcProxyMissionId"))
            for row in rows
            if safe_key(row.get("npcProxyMissionId"))
        }
        mapping_ids = {
            safe_key(row.get("nativeMappingId"))
            for row in rows
            if safe_key(row.get("nativeMappingId"))
        }
        hashes = {
            safe_key(row.get("gameAssemblySha256"))
            for row in rows
            if safe_key(row.get("gameAssemblySha256"))
        }
        if (
            len(mission_ids) != 1
            or mapping_ids != {NPC_PROXY_DIALOG_SELECTION_MAPPING_ID}
            or hashes
            != {NPC_PROXY_DIALOG_SELECTION_GAMEASSEMBLY_SHA256}
        ):
            continue
        context_mission = next(iter(mission_ids))
        cross_mission_context = context_mission != owner_mission
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                (
                    "closed_exact_cross_mission_runtime_config_"
                    "no_relative_order"
                    if cross_mission_context
                    else "closed_exact_runtime_config_no_relative_order"
                ),
            "relation": "npc_proxy_ex_mission_context",
            "missionId": context_mission,
            "nominalStoryMissionId": owner_mission,
            "contextMissionMismatch": cross_mission_context,
            "contextMissionBundles": sorted({
                safe_key(row.get("contextMissionBundle"))
                for row in rows
                if safe_key(row.get("contextMissionBundle"))
            }, key=natural_key),
            "npcProxyIds": sorted({
                safe_key(row.get("npcProxyId"))
                for row in rows
                if safe_key(row.get("npcProxyId"))
            }, key=natural_key),
            "selectionSemantics":
                "exDatas[activeCondIndex - 1].dialogId",
            "orderBoundary": (
                "activeCondIndex selects one proxy row; neither row index, "
                "proxy suffix, table order, nor adjacent missionId orders "
                "Story files"
            ),
            "contextBoundary": (
                "the exact proxy row makes this nominal Story file selectable "
                f"while mission {context_mission} is active; it does not move "
                "the file into that mission's chronology or establish a "
                "relative Story edge"
            ),
            "upstreamServerStateSources": [
                "SC_NPC_ENTER_MAP_RESYNC",
                "SC_NPC_ACTIVE_CHANGE_NTF",
            ],
            "serverFields": [
                "proxyNumId",
                "metaKvs",
                "activeCondIndex",
            ],
            "nativeConsumers": [{
                "method":
                    "NpcInteractComponent._TryGetNpcProxyInteractDialogId",
                "token": "0x06011381",
                "address": "0x183564080",
            }, {
                "method": "NpcProxy._IsMissionConflict",
                "token": "0x060131f4",
                "address": "0x18706ac74",
            }],
            "nativeMappingId": next(iter(mapping_ids)),
            "gameAssemblySha256": next(iter(hashes)),
        })
    already_closed = {row["sceneKey"] for row in closed}
    interactive_grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    expected_source = (
        "exact counted LevelScriptData interactive map -> 25-member "
        "LevelInteractiveData -> componentProperties[94].type_id; "
        "ReadingPopUpTable is joined only when TYPE_ID names a popup row"
    )
    expected_order_boundary = (
        "interactive-map order, local interactive id, object position, "
        "and Story suffix do not establish relative Story chronology"
    )
    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        level_ids = _string_list(row.get("levelIds"))
        script_ids = _string_list(row.get("scriptIds"))
        entity_details = _string_list(row.get("entityDetailIds"))
        template_ids = _string_list(row.get("entityTemplateIds"))
        local_id = row.get("localInteractiveId")
        if (
            scene_key in already_closed
            or scene_key not in isolated_scene_keys
            or safe_key(row.get("relation"))
            != "levelscript_interactive_narrative_config"
            or safe_key(row.get("confidence"))
            != "native_exact_serialized_config"
            or safe_key(row.get("source")) != expected_source
            or safe_key(row.get("storyOwnerMission")) != owner_mission
            or row.get("storyBinding") is not True
            or row.get("ownership") is not False
            or safe_key(row.get("nativeMappingId"))
            != LEVELSCRIPT_INTERACTIVE_NARRATIVE_MAPPING_ID
            or safe_key(row.get("orderBoundary"))
            != expected_order_boundary
            or len(level_ids) != 1
            or len(script_ids) != 1
            or len(entity_details) != 1
            or len(template_ids) != 1
            or not template_ids[0].startswith("int_narrative")
            or not isinstance(local_id, int)
            or isinstance(local_id, bool)
            or local_id <= 0
            or row.get("narrativeComponentKey") != 94
            or not isinstance(row.get("interactiveMapCount"), int)
            or int(row.get("interactiveMapCount") or 0) <= 0
        ):
            continue
        interactive_grouped[scene_key].append(row)

    for scene_key, rows in interactive_grouped.items():
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_runtime_config_no_relative_order",
            "relation": "levelscript_interactive_narrative_config",
            "missionId": owner_mission,
            "levelIds": sorted({
                level_id
                for row in rows
                for level_id in _string_list(row.get("levelIds"))
            }, key=natural_key),
            "scriptIds": sorted({
                script_id
                for row in rows
                for script_id in _string_list(row.get("scriptIds"))
            }, key=natural_key),
            "localInteractiveIds": sorted({
                int(row["localInteractiveId"])
                for row in rows
            }),
            "entityDetailIds": sorted({
                detail
                for row in rows
                for detail in _string_list(row.get("entityDetailIds"))
            }, key=natural_key),
            "entityTemplateIds": sorted({
                template
                for row in rows
                for template in _string_list(row.get("entityTemplateIds"))
            }, key=natural_key),
            "rawTypeIds": sorted({
                safe_key(row.get("rawTypeId"))
                for row in rows
                if safe_key(row.get("rawTypeId"))
            }, key=natural_key),
            "storyKeyResolutions": sorted({
                safe_key(row.get("storyKeyResolution"))
                for row in rows
                if safe_key(row.get("storyKeyResolution"))
            }),
            "questContextIds": sorted({
                quest_id
                for row in rows
                for quest_id in _string_list(row.get("questContextIds"))
            }, key=natural_key),
            "sourceFiles": sorted({
                source_file
                for row in rows
                for source_file in _string_list(row.get("sourceFiles"))
            }),
            "nativeConsumer": (
                "NarrativeComponent.ClientCollectNarrative -> "
                "_CollectNarrative -> dialog/reading-popup dispatch"
            ),
            "nativeMappingId":
                LEVELSCRIPT_INTERACTIVE_NARRATIVE_MAPPING_ID,
            "activationBoundary": (
                "the source LevelScript and local interactive are exact; "
                "serialized data does not establish when the script becomes "
                "active or when the player performs the interaction"
            ),
            "orderBoundary": expected_order_boundary,
        })
    already_closed.update(row["sceneKey"] for row in closed)
    leveldata_grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    leveldata_component_source = (
        "exact counted LevelData interactive list -> 25-member "
        "LevelInteractiveData bounded by the next record or validated "
        "member-21 suffix (nonempty BriefData dictionary or complete "
        "empty-script suffix), including an exact null or decoded "
        "mission/quest-state progress lock -> "
        "componentProperties[94].type_id"
    )
    leveldata_horn_source = (
        "exact counted LevelData interactive list -> 25-member "
        "LevelInteractiveData bounded by the next record or validated "
        "member-21 suffix (nonempty BriefData dictionary or complete "
        "empty-script suffix), including an exact null or decoded "
        "mission/quest-state progress lock -> "
        "int_horn.properties.dialog_id; the byte-identical authored "
        "Horn template and current native Horn flow validate the "
        "dialog consumer"
    )
    leveldata_order_boundary = (
        "interactive-list order, record index, entity logic id, object "
        "position, and Story suffix do not establish relative Story chronology"
    )

    def progress_tree_leaves(
        node: object,
        depth: int = 0,
    ) -> list[dict[str, Any]] | None:
        if not isinstance(node, dict) or depth > 8:
            return None
        condition_type = safe_key(node.get("conditionType"))
        if condition_type == "CombinedConditionRuntime":
            children = node.get("conditions")
            if (
                node.get("unionTag") != 0
                or node.get("serializedMemberCount") != 3
                or node.get("conditionOperator") not in (0, 1)
                or not isinstance(node.get("serializedRuntimeFlag"), bool)
                or not isinstance(children, list)
                or not 1 <= len(children) <= 64
            ):
                return None
            leaves: list[dict[str, Any]] = []
            for child in children:
                child_leaves = progress_tree_leaves(child, depth + 1)
                if child_leaves is None:
                    return None
                leaves.extend(child_leaves)
            return leaves
        if (
            condition_type not in {
                "SimpleConditionCheckMissionState",
                "SimpleConditionCheckQuestState",
            }
            or node.get("unionTag") not in (0x0C, 0x10)
            or node.get("serializedMemberCount") != 3
            or safe_key(node.get("ownerKind")) not in {"mission", "quest"}
            or not safe_key(node.get("ownerId"))
            or node.get("compareOperator") not in (0, 1)
            or not isinstance(node.get("compareTarget"), int)
            or isinstance(node.get("compareTarget"), bool)
            or not 0 <= int(node.get("compareTarget")) <= 5
        ):
            return None
        return [node]

    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        level_ids = _string_list(row.get("levelIds"))
        asset_ids = _string_list(row.get("levelDataAssets"))
        entity_details = _string_list(row.get("entityDetailIds"))
        template_ids = _string_list(row.get("entityTemplateIds"))
        record_index = row.get("interactiveRecordIndex")
        record_offset = row.get("interactiveRecordOffset")
        record_end = row.get("interactiveRecordEndOffset")
        list_count = row.get("interactiveListCount")
        entity_logic_id = row.get("entityLogicId")
        consumer_kind = safe_key(
            row.get("narrativeConsumerKind")
        ) or "narrative_component"
        if consumer_kind == "horn_dialog_property":
            exact_consumer_valid = (
                safe_key(row.get("source")) == leveldata_horn_source
                and safe_key(row.get("nativeMappingId"))
                == LEVELDATA_INTERACTIVE_HORN_MAPPING_ID
                and entity_details == ["int_horn"]
                and template_ids == ["int_horn"]
                and safe_key(row.get("interactiveHornNativeMappingId"))
                == LEVELDATA_INTERACTIVE_HORN_NATIVE_MAPPING_ID
                and safe_key(row.get("interactiveHornTemplateSha256"))
                == LEVELDATA_INTERACTIVE_HORN_TEMPLATE_SHA256
                and isinstance(row.get("dialogIdEntryOffset"), int)
                and not isinstance(row.get("dialogIdEntryOffset"), bool)
                and isinstance(record_offset, int)
                and row.get("dialogIdEntryOffset") > record_offset
                and isinstance(record_end, int)
                and row.get("dialogIdEntryOffset") < record_end
                and row.get("narrativeComponentKey") is None
            )
        else:
            exact_consumer_valid = (
                consumer_kind == "narrative_component"
                and safe_key(row.get("source"))
                == leveldata_component_source
                and safe_key(row.get("nativeMappingId"))
                == LEVELDATA_INTERACTIVE_NARRATIVE_MAPPING_ID
                and template_ids[0].startswith("int_narrative")
                if len(template_ids) == 1
                else False
            )
        boundary_source = safe_key(
            row.get("interactiveRecordBoundarySource")
        )
        final_record = (
            isinstance(record_index, int)
            and not isinstance(record_index, bool)
            and isinstance(list_count, int)
            and not isinstance(list_count, bool)
            and record_index == list_count - 1
        )
        nonempty_final_boundary_valid = (
            final_record
            and boundary_source == "leveldata_member21_start"
            and isinstance(record_end, int)
            and not isinstance(record_end, bool)
            and row.get("levelDataMember21Offset") == record_end
            and row.get("levelScriptBriefDictionaryCountOffset")
            == record_end + 4
            and isinstance(row.get("levelIdNum"), int)
            and not isinstance(row.get("levelIdNum"), bool)
            and int(row.get("levelIdNum")) >= 0
            and isinstance(
                row.get("levelScriptBriefDictionaryCount"),
                int,
            )
            and not isinstance(
                row.get("levelScriptBriefDictionaryCount"),
                bool,
            )
            and int(row.get("levelScriptBriefDictionaryCount")) > 0
            and safe_key(row.get("levelDataFinalBoundaryValidation"))
            == "nonempty_levelscript_brief_dictionary"
        )
        empty_final_boundary_valid = (
            final_record
            and boundary_source == "leveldata_member21_start"
            and isinstance(record_end, int)
            and row.get("levelDataMember21Offset") == record_end
            and row.get("levelScriptBriefDictionaryCountOffset")
            == record_end + 4
            and row.get("levelScriptBriefDictionaryCount") == 0
            and row.get("levelScriptDataPathDictionaryCountOffset")
            == record_end + 8
            and row.get("levelScriptDataPathDictionaryCount") == 0
            and row.get("levelDataSafeZoneOffset") == record_end + 60
            and safe_key(row.get("levelDataSceneId"))
            == next(iter(level_ids), "")
            and isinstance(row.get("levelDataSpecificDataOffset"), int)
            and row.get("levelDataSpecificDataOffset")
            > row.get("levelDataSafeZoneOffset")
            and isinstance(row.get("levelDataEmptySuffixEndOffset"), int)
            and row.get("levelDataEmptySuffixEndOffset")
            > row.get("levelDataSpecificDataOffset")
            and safe_key(row.get("levelDataFinalBoundaryValidation"))
            == "complete_empty_script_suffix_to_eof"
        )
        nonfinal_boundary_valid = (
            isinstance(record_index, int)
            and not isinstance(record_index, bool)
            and isinstance(list_count, int)
            and not isinstance(list_count, bool)
            and 0 <= record_index < list_count - 1
            and boundary_source == "next_record"
        )
        progress_status = safe_key(
            row.get("progressLockConditionStatus")
        )
        progress_conditions = row.get("progressLockConditions")
        tree_leaves = progress_tree_leaves(
            row.get("progressLockConditionTree")
        )
        decoded_progress_valid = (
            progress_status == "decoded"
            and safe_key(row.get("progressLockConditionType")) in {
                "CombinedConditionRuntime",
                "SimpleConditionCheckMissionState",
                "SimpleConditionCheckQuestState",
            }
            and isinstance(progress_conditions, list)
            and bool(progress_conditions)
            and all(
                isinstance(condition, dict)
                and condition.get("serializedMemberCount") == 3
                and condition.get("unionTag") in (0x0C, 0x10)
                and safe_key(condition.get("conditionType")) in {
                    "SimpleConditionCheckMissionState",
                    "SimpleConditionCheckQuestState",
                }
                and safe_key(condition.get("ownerKind"))
                in {"mission", "quest"}
                and bool(safe_key(condition.get("ownerId")))
                and condition.get("compareOperator") in (0, 1)
                and isinstance(condition.get("compareTarget"), int)
                and not isinstance(condition.get("compareTarget"), bool)
                and 0 <= int(condition.get("compareTarget")) <= 5
                for condition in progress_conditions
            )
            and tree_leaves is not None
            and len(tree_leaves) == len(progress_conditions)
            and all(
                (
                    safe_key(tree.get("conditionType")),
                    safe_key(tree.get("ownerKind")),
                    safe_key(tree.get("ownerId")),
                    tree.get("compareOperator"),
                    tree.get("compareTarget"),
                ) == (
                    safe_key(flat.get("conditionType")),
                    safe_key(flat.get("ownerKind")),
                    safe_key(flat.get("ownerId")),
                    flat.get("compareOperator"),
                    flat.get("compareTarget"),
                )
                for tree, flat in zip(tree_leaves, progress_conditions)
            )
        )
        progress_type = safe_key(row.get("progressLockConditionType"))
        if progress_type == "CombinedConditionRuntime":
            decoded_progress_valid = (
                decoded_progress_valid
                and row.get("progressLockConditionUnionTag") == 0
                and row.get(
                    "progressLockConditionSerializedMemberCount"
                ) == 3
                and row.get("progressLockConditionOperator") in (0, 1)
                and isinstance(
                    row.get("progressLockSerializedRuntimeFlag"),
                    bool,
                )
            )
        elif progress_type in {
            "SimpleConditionCheckMissionState",
            "SimpleConditionCheckQuestState",
        }:
            decoded_progress_valid = (
                decoded_progress_valid
                and row.get("progressLockConditionUnionTag") in (0x0C, 0x10)
                and row.get(
                    "progressLockConditionSerializedMemberCount"
                ) == 3
                and len(progress_conditions) == 1
                and progress_conditions[0].get("unionTag")
                == row.get("progressLockConditionUnionTag")
                and progress_conditions[0].get("conditionType")
                == row.get("progressLockConditionType")
            )
        progress_lock_valid = (
            (
                progress_status == "null"
                and not progress_conditions
            )
            or decoded_progress_valid
        )
        if (
            scene_key in already_closed
            or scene_key not in isolated_scene_keys
            or safe_key(row.get("relation"))
            != "leveldata_interactive_narrative_config"
            or safe_key(row.get("confidence"))
            != "native_exact_serialized_config"
            or not exact_consumer_valid
            or safe_key(row.get("storyOwnerMission")) != owner_mission
            or row.get("storyBinding") is not True
            or row.get("ownership") is not False
            or safe_key(row.get("orderBoundary"))
            != leveldata_order_boundary
            or len(level_ids) != 1
            or len(asset_ids) != 1
            or len(entity_details) != 1
            or len(template_ids) != 1
            or not isinstance(record_index, int)
            or isinstance(record_index, bool)
            or record_index < 0
            or not isinstance(list_count, int)
            or isinstance(list_count, bool)
            or not (
                nonfinal_boundary_valid
                or nonempty_final_boundary_valid
                or empty_final_boundary_valid
            )
            or not progress_lock_valid
            or not isinstance(record_offset, int)
            or not isinstance(record_end, int)
            or record_offset < 0
            or record_end <= record_offset
            or not isinstance(entity_logic_id, int)
            or isinstance(entity_logic_id, bool)
            or entity_logic_id <= 0
            or (
                consumer_kind == "narrative_component"
                and row.get("narrativeComponentKey") != 94
            )
        ):
            continue
        leveldata_grouped[scene_key].append(row)

    for scene_key, rows in leveldata_grouped.items():
        progress_locks = []
        for row in rows:
            progress_locks.append({
                "levelDataAsset": next(
                    iter(_string_list(row.get("levelDataAssets"))),
                    "",
                ),
                "interactiveRecordIndex":
                    row.get("interactiveRecordIndex"),
                "status": safe_key(
                    row.get("progressLockConditionStatus")
                ),
                "conditionType": safe_key(
                    row.get("progressLockConditionType")
                ),
                "conditionOperator":
                    row.get("progressLockConditionOperator"),
                "serializedRuntimeFlag":
                    row.get("progressLockSerializedRuntimeFlag"),
                "conditionTree":
                    row.get("progressLockConditionTree"),
                "conditions": [{
                    key: condition.get(key)
                    for key in (
                        "unionTag",
                        "serializedMemberCount",
                        "conditionType",
                        "ownerKind",
                        "ownerId",
                        "compareOperator",
                        "compareTarget",
                    )
                } for condition in row.get("progressLockConditions") or []],
            })
        progress_locks.sort(key=lambda row: (
            natural_key(safe_key(row.get("levelDataAsset"))),
            int(row.get("interactiveRecordIndex") or 0),
        ))
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_runtime_config_no_relative_order",
            "relation": "leveldata_interactive_narrative_config",
            "missionId": owner_mission,
            "levelIds": sorted({
                value
                for row in rows
                for value in _string_list(row.get("levelIds"))
            }, key=natural_key),
            "levelDataAssets": sorted({
                value
                for row in rows
                for value in _string_list(row.get("levelDataAssets"))
            }, key=natural_key),
            "interactiveRecordIndexes": sorted({
                int(row["interactiveRecordIndex"])
                for row in rows
            }),
            "interactiveRecordBoundarySources": sorted({
                safe_key(row.get("interactiveRecordBoundarySource"))
                for row in rows
                if safe_key(row.get("interactiveRecordBoundarySource"))
            }),
            "levelDataFinalBoundaryValidations": sorted({
                safe_key(row.get("levelDataFinalBoundaryValidation"))
                for row in rows
                if safe_key(row.get("levelDataFinalBoundaryValidation"))
            }),
            "levelDataSceneIds": sorted({
                safe_key(row.get("levelDataSceneId"))
                for row in rows
                if safe_key(row.get("levelDataSceneId"))
            }, key=natural_key),
            "entityLogicIds": sorted({
                int(row["entityLogicId"])
                for row in rows
            }),
            "entityDetailIds": sorted({
                value
                for row in rows
                for value in _string_list(row.get("entityDetailIds"))
            }, key=natural_key),
            "entityTemplateIds": sorted({
                value
                for row in rows
                for value in _string_list(row.get("entityTemplateIds"))
            }, key=natural_key),
            "rawTypeIds": sorted({
                safe_key(row.get("rawTypeId"))
                for row in rows
                if safe_key(row.get("rawTypeId"))
            }, key=natural_key),
            "storyKeyResolutions": sorted({
                safe_key(row.get("storyKeyResolution"))
                for row in rows
                if safe_key(row.get("storyKeyResolution"))
            }),
            "narrativeConsumerKinds": sorted({
                safe_key(row.get("narrativeConsumerKind"))
                or "narrative_component"
                for row in rows
            }),
            "progressLocks": progress_locks,
            "sourceFiles": sorted({
                source_file
                for row in rows
                for source_file in _string_list(row.get("sourceFiles"))
            }),
            "nativeConsumers": sorted({
                safe_key(row.get("nativeConsumer"))
                for row in rows
                if safe_key(row.get("nativeConsumer"))
            }),
            "nativeMappingIds": sorted({
                safe_key(row.get("nativeMappingId"))
                for row in rows
                if safe_key(row.get("nativeMappingId"))
            }),
            "activationBoundary": (
                "the LevelData asset and narrative interactive are exact; "
                "an exact progress lock constrains interactive availability "
                "when present, but does not establish object instantiation, "
                "player interaction timing, Story ownership, or chronology"
            ),
            "orderBoundary": leveldata_order_boundary,
        })
    return sorted(closed, key=lambda row: natural_key(row["sceneKey"]))


def build_gap_row(
    partial_row: dict[str, Any],
    mission_payload: dict[str, Any] | None,
    *,
    mission_bundle_exists: bool,
    native_playback_index: dict[str, list[dict[str, Any]]] | None = None,
    action_story_occurrences: dict[str, list[dict[str, Any]]] | None = None,
    non_mission_content: dict[str, dict[str, Any]] | None = None,
    offline_exhaustion_index: dict[str, dict[str, Any]] | None = None,
    cross_owner_story_connections: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    non_mission_content = non_mission_content or {}
    offline_exhaustion_index = offline_exhaustion_index or {}
    mission = safe_key(partial_row.get("mission"))
    summary = partial_row.get("summary") if isinstance(partial_row.get("summary"), dict) else {}
    timeline = _timeline(mission_payload)
    flow = _flow(mission_payload)
    candidate_scene_keys = {
        safe_key(node.get("key"))
        for node in partial_row.get("nodes") or []
        if isinstance(node, dict) and safe_key(node.get("key"))
    }

    quest_ids = {
        safe_key(row.get("questId"))
        for row in timeline.get("quests") or []
        if isinstance(row, dict) and safe_key(row.get("questId"))
    }
    strict_quest_ids, strict_quest_scenes = _strict_quest_attachments(
        partial_row,
        flow,
    )
    diagnostic_quest_ids, diagnostic_quest_scenes, diagnostic_source_counts = (
        _diagnostic_quest_attachments(timeline, candidate_scene_keys)
    )
    missing_strict_quest_ids = sorted(
        (quest_ids & diagnostic_quest_ids) - strict_quest_ids,
        key=natural_key,
    )
    quest_ids_without_story_evidence = sorted(
        quest_ids - strict_quest_ids - diagnostic_quest_ids,
        key=natural_key,
    )
    raw_context_gaps = _levelscript_context_gaps(
        timeline,
        flow,
        native_playback_index,
    )
    context_gaps, closed_context_gaps = _classify_levelscript_context_gaps(
        raw_context_gaps,
        action_story_occurrences,
    )
    cycle_scenes = sorted({
        scene_key
        for cycle in partial_row.get("cycles") or []
        if isinstance(cycle, dict)
        for scene_key in _string_list(cycle.get("sceneKeys"))
    }, key=natural_key)
    unresolved_kinds = Counter(
        safe_key(row.get("kind")) or "unknown"
        for row in timeline.get("unresolved") or []
        if isinstance(row, dict)
    )
    node_kind_by_key = {
        safe_key(node.get("key")): safe_key(node.get("kind")) or "unknown"
        for node in partial_row.get("nodes") or []
        if isinstance(node, dict) and safe_key(node.get("key"))
    }
    isolated_scene_keys = _string_list(partial_row.get("isolatedSceneKeys"))
    if not isolated_scene_keys:
        isolated_scene_keys = [
            safe_key(node.get("key"))
            for node in partial_row.get("nodes") or []
            if isinstance(node, dict) and safe_key(node.get("relationStatus")) == "isolated"
        ]
    isolated_kinds = Counter(node_kind_by_key.get(key, "unknown") for key in isolated_scene_keys)
    core_isolated_scene_keys = [
        key
        for key in isolated_scene_keys
        if node_kind_by_key.get(key, "unknown") in CORE_STORY_NODE_KINDS
    ]
    (
        closed_exact_native_isolated,
        _incomplete_native_isolated_keys,
    ) = _closed_exact_native_unordered_scenes(
        flow,
        set(isolated_scene_keys),
        native_playback_index,
    )
    closed_exact_native_isolated_by_key = {
        row["sceneKey"]: row
        for row in closed_exact_native_isolated
    }
    for row in _closed_exact_dialog_tree_embedded_isolated_scenes(
        flow,
        set(isolated_scene_keys),
        safe_key(partial_row.get("mission")),
    ):
        closed_exact_native_isolated_by_key.setdefault(
            row["sceneKey"],
            row,
        )
    for row in _closed_exact_dialog_tree_embedded_context_isolated_scenes(
        flow,
        set(isolated_scene_keys),
        safe_key(partial_row.get("mission")),
    ):
        closed_exact_native_isolated_by_key.setdefault(
            row["sceneKey"],
            row,
        )
    for row in _closed_exact_timeline_dialog_embedded_isolated_scenes(
        flow,
        set(isolated_scene_keys),
        safe_key(partial_row.get("mission")),
    ):
        closed_exact_native_isolated_by_key.setdefault(
            row["sceneKey"],
            row,
        )
    closed_exact_native_isolated = sorted(
        closed_exact_native_isolated_by_key.values(),
        key=lambda row: natural_key(row["sceneKey"]),
    )
    closed_exact_native_isolated_keys = {
        row["sceneKey"]
        for row in closed_exact_native_isolated
    }
    runtime_config_flow = flow
    if cross_owner_story_connections:
        runtime_config_flow = dict(flow)
        runtime_config_flow["missionStoryConnections"] = [
            *(
                flow.get("missionStoryConnections")
                if isinstance(flow.get("missionStoryConnections"), list)
                else []
            ),
            *cross_owner_story_connections,
        ]
    closed_exact_runtime_config_isolated = (
        _closed_exact_runtime_config_isolated_scenes(
            runtime_config_flow,
            set(isolated_scene_keys),
            safe_key(partial_row.get("mission")),
        )
    )
    closed_exact_runtime_config_isolated_keys = {
        row["sceneKey"]
        for row in closed_exact_runtime_config_isolated
    }
    closed_definition_only_isolated = (
        _closed_definition_only_isolated_scenes(
            flow,
            set(isolated_scene_keys),
        )
    )
    closed_definition_only_isolated_keys = {
        row["sceneKey"]
        for row in closed_definition_only_isolated
    }
    closed_non_mission_content_isolated = (
        _closed_non_mission_content_isolated_scenes(
            set(isolated_scene_keys),
            non_mission_content,
        )
    )
    closed_non_mission_content_isolated_keys = {
        row["sceneKey"]
        for row in closed_non_mission_content_isolated
    }
    deferred_offline_exhausted_isolated = (
        _deferred_offline_exhausted_isolated_scenes(
            flow,
            set(isolated_scene_keys),
            safe_key(partial_row.get("mission")),
            offline_exhaustion_index,
        )
    )
    deferred_offline_exhausted_isolated_keys = {
        row["sceneKey"]
        for row in deferred_offline_exhausted_isolated
    }
    actionable_core_isolated_scene_keys = [
        key
        for key in core_isolated_scene_keys
        if key not in closed_exact_native_isolated_keys
        and key not in closed_exact_runtime_config_isolated_keys
        and key not in closed_definition_only_isolated_keys
        and key not in closed_non_mission_content_isolated_keys
        and key not in deferred_offline_exhausted_isolated_keys
    ]
    weak_only_scene_keys = set(
        _string_list(partial_row.get("weakOnlySceneKeys"))
    )
    incident_levelscript_files: dict[str, set[str]] = defaultdict(set)
    for edge in partial_row.get("directEdges") or []:
        if (
            not isinstance(edge, dict)
            or not safe_key(edge.get("kind")).startswith("levelscript")
        ):
            continue
        source_files = set(_string_list(edge.get("sourceFiles")))
        for field in ("from", "to"):
            scene_key = safe_key(edge.get(field))
            if scene_key in weak_only_scene_keys:
                incident_levelscript_files[scene_key].update(source_files)
    (
        closed_exact_native_weak_only,
        incomplete_native_weak_only_keys,
    ) = _closed_exact_native_unordered_scenes(
        flow,
        weak_only_scene_keys,
        native_playback_index,
        incident_levelscript_files,
    )
    closed_exact_native_weak_only_keys = {
        row["sceneKey"]
        for row in closed_exact_native_weak_only
    }
    actionable_weak_only_keys = set(incomplete_native_weak_only_keys)
    for scene_key in weak_only_scene_keys - closed_exact_native_weak_only_keys:
        accepted_files = incident_levelscript_files.get(scene_key) or set()
        for occurrence in (action_story_occurrences or {}).get(scene_key) or []:
            if not isinstance(occurrence, dict):
                continue
            source_file = safe_key(occurrence.get("sourceFile"))
            if not accepted_files or source_file not in accepted_files:
                continue
            if not safe_key(occurrence.get("actionMapRole")).startswith(
                "actionList#"
            ):
                continue
            record_class = safe_key(occurrence.get("recordClass"))
            action_name = safe_key(occurrence.get("actionName"))
            if not record_class or not action_name:
                mapped = KNOWN_NON_PLAYBACK_ACTIONS.get((
                    safe_key(occurrence.get("actionCode")).lower(),
                    safe_key(occurrence.get("actionKind")).lower(),
                ))
                if mapped:
                    action_name, record_class = mapped
            if record_class and action_name and not record_class.startswith(
                "play_"
            ):
                continue
            actionable_weak_only_keys.add(scene_key)
            break
    actionable_weak_only_scene_keys = sorted(
        actionable_weak_only_keys,
        key=natural_key,
    )
    non_actionable_weak_only_scene_keys = sorted(
        weak_only_scene_keys
        - closed_exact_native_weak_only_keys
        - actionable_weak_only_keys,
        key=natural_key,
    )

    metrics = {
        "missingMissionBundle": 0 if mission_bundle_exists else 1,
        "sceneCount": int(summary.get("sceneCount") or 0),
        "strongEdgeCount": int(summary.get("strongEdgeCount") or 0),
        "reducedComponentEdgeCount": int(summary.get("reducedComponentEdgeCount") or 0),
        "comparableScenePairs": int(summary.get("comparableScenePairs") or 0),
        "totalScenePairs": int(summary.get("totalScenePairs") or 0),
        "isolatedScenes": int(summary.get("isolatedSceneCount") or 0),
        "coreIsolatedScenes": len(core_isolated_scene_keys),
        "actionableCoreIsolatedScenes": len(
            actionable_core_isolated_scene_keys
        ),
        "closedExactNativeIsolatedScenes": len(
            closed_exact_native_isolated_keys
        ),
        "closedExactRuntimeConfigIsolatedScenes": len(
            closed_exact_runtime_config_isolated_keys
        ),
        "closedDefinitionOnlyIsolatedScenes": len(
            closed_definition_only_isolated_keys
        ),
        "closedNonMissionContentIsolatedScenes": len(
            closed_non_mission_content_isolated_keys
        ),
        "deferredOfflineExhaustedIsolatedScenes": len(
            deferred_offline_exhausted_isolated_keys
        ),
        "weakOnlyScenes": int(summary.get("weakOnlySceneCount") or 0),
        "actionableWeakOnlyScenes": len(actionable_weak_only_scene_keys),
        "closedExactNativeWeakOnlyScenes": len(
            closed_exact_native_weak_only_keys
        ),
        "nonActionableWeakOnlyScenes": len(
            non_actionable_weak_only_scene_keys
        ),
        "sourceCycles": int(summary.get("cycleCount") or 0),
        "cycleScenes": len(cycle_scenes),
        "unresolvedSourceNodes": len(partial_row.get("unresolvedSourceNodes") or []),
        "untypedMultiSceneLevelscriptContexts": len(context_gaps),
        "closedNonPlaybackLevelscriptContexts": len(closed_context_gaps),
        "questCount": len(quest_ids),
        "strictQuestAttachedSceneCount": len(strict_quest_scenes),
        "strictQuestIdsWithStoryAttachment": len(quest_ids & strict_quest_ids),
        "questIdsWithoutStrictStoryAttachment": len(missing_strict_quest_ids),
        "questIdsWithoutAnyStoryEvidence": len(quest_ids_without_story_evidence),
        "diagnosticQuestAttachedSceneCount": len(diagnostic_quest_scenes),
        "diagnosticQuestIdsWithStoryAttachment": len(quest_ids & diagnostic_quest_ids),
        "questForks": int(summary.get("questForkCount") or 0),
        "questMerges": int(summary.get("questMergeCount") or 0),
        "strictDialogOptionGroups": int(summary.get("dialogLineOptionGroupCount") or 0),
        "noExplicitOptionRouteGroups": int(
            summary.get("noExplicitRouteGroupCount") or 0
        ),
        "actionableNoExplicitOptionRouteGroups": int(
            summary.get(
                "branchingNoExplicitRouteGroupCount",
                summary.get("noExplicitRouteGroupCount"),
            )
            or 0
        ),
        "singleOptionNoExplicitRouteGroups": int(
            summary.get("singleOptionNoExplicitRouteGroupCount") or 0
        ),
        "excludedOptionEvidenceGroups": int(
            summary.get("excludedDialogLineOptionGroupCount") or 0
        ),
        "actionableExcludedOptionEvidenceGroups": int(
            summary.get(
                "actionableExcludedDialogLineOptionGroupCount",
                summary.get("excludedDialogLineOptionGroupCount"),
            )
            or 0
        ),
        "closedExcludedOptionEvidenceGroups": int(
            summary.get("closedExcludedDialogLineOptionGroupCount") or 0
        ),
        "timelineUnresolvedRecords": sum(unresolved_kinds.values()),
    }
    score_contributions = {
        key: metrics[key] * weight
        for key, weight in SCORE_WEIGHTS.items()
    }
    frontier_contributions = _frontier_contributions(metrics)
    active_frontiers = [
        frontier
        for frontier in FRONTIER_ORDER
        if frontier_contributions.get(frontier, 0) > 0
    ]
    primary_frontier = min(
        active_frontiers,
        key=lambda frontier: (
            -frontier_contributions[frontier],
            FRONTIER_ORDER.index(frontier),
        ),
        default="none",
    )

    return {
        "mission": mission,
        "bucket": _bucket(mission),
        "score": sum(score_contributions.values()),
        "scoreContributions": score_contributions,
        "frontierContributions": frontier_contributions,
        "primaryFrontier": primary_frontier,
        "activeFrontiers": active_frontiers,
        "metrics": metrics,
        "cycleSceneKeys": cycle_scenes,
        "coreIsolatedSceneKeys": core_isolated_scene_keys,
        "actionableCoreIsolatedSceneKeys":
            actionable_core_isolated_scene_keys,
        "closedExactNativeIsolatedScenes":
            closed_exact_native_isolated,
        "closedExactRuntimeConfigIsolatedScenes":
            closed_exact_runtime_config_isolated,
        "closedDefinitionOnlyIsolatedScenes":
            closed_definition_only_isolated,
        "closedNonMissionContentIsolatedScenes":
            closed_non_mission_content_isolated,
        "deferredOfflineExhaustedIsolatedScenes":
            deferred_offline_exhausted_isolated,
        "actionableWeakOnlySceneKeys": actionable_weak_only_scene_keys,
        "closedExactNativeWeakOnlyScenes": closed_exact_native_weak_only,
        "nonActionableWeakOnlySceneKeys":
            non_actionable_weak_only_scene_keys,
        "isolatedSceneKinds": dict(sorted(isolated_kinds.items())),
        "questIdsWithoutStrictStoryAttachment": missing_strict_quest_ids,
        "questIdsWithoutAnyStoryEvidence": quest_ids_without_story_evidence,
        "untypedMultiSceneLevelscriptContexts": context_gaps,
        "closedNonPlaybackLevelscriptContexts": closed_context_gaps,
        "timelineUnresolvedKinds": dict(sorted(unresolved_kinds.items())),
        "diagnosticQuestAttachmentSources": dict(sorted(diagnostic_source_counts.items())),
        "unresolvedSourceNodes": partial_row.get("unresolvedSourceNodes") or [],
    }


def build_gap_report(
    partial_report: dict[str, Any],
    mission_payloads: dict[str, dict[str, Any]],
    mission_bundle_presence: set[str],
    native_playback_index: dict[str, list[dict[str, Any]]] | None = None,
    action_story_occurrences: dict[str, list[dict[str, Any]]] | None = None,
    table_root: Path | None = None,
    offline_exhaustion_index: dict[str, dict[str, Any]] | None = None,
    offline_exhaustion_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    non_mission_content = (
        combined_non_mission_content_keys(table_root)
        if table_root is not None
        else {}
    )
    cross_owner_connections: dict[str, list[dict[str, Any]]] = defaultdict(
        list
    )
    for context_mission, payload in mission_payloads.items():
        flow = _flow(payload)
        for connection in _flow_story_connections(flow):
            owner_mission = safe_key(connection.get("storyOwnerMission"))
            proxy_mission = safe_key(connection.get("npcProxyMissionId"))
            if (
                safe_key(connection.get("relation"))
                != "npc_proxy_ex_mission_context"
                or not owner_mission
                or owner_mission == context_mission
                or proxy_mission != context_mission
                or owner_mission not in mission_payloads
            ):
                continue
            cross_owner_connections[owner_mission].append({
                **connection,
                "contextMissionBundle": context_mission,
            })
    for mission in cross_owner_connections:
        cross_owner_connections[mission].sort(key=lambda row: (
            natural_key(safe_key(row.get("key"))),
            natural_key(safe_key(row.get("npcProxyMissionId"))),
            natural_key(safe_key(row.get("npcProxyId"))),
        ))
    rows = [
        build_gap_row(
            row,
            mission_payloads.get(safe_key(row.get("mission"))),
            mission_bundle_exists=safe_key(row.get("mission")) in mission_bundle_presence,
            native_playback_index=native_playback_index,
            action_story_occurrences=action_story_occurrences,
            non_mission_content=non_mission_content,
            offline_exhaustion_index=offline_exhaustion_index,
            cross_owner_story_connections=cross_owner_connections.get(
                safe_key(row.get("mission"))
            ),
        )
        for row in partial_report.get("missions") or []
        if isinstance(row, dict)
    ]
    rows.sort(key=lambda row: (
        BUCKET_ORDER.index(row["bucket"]),
        -row["score"],
        -row["metrics"]["sceneCount"],
        natural_key(row["mission"]),
    ))
    bucket_ranks: Counter[str] = Counter()
    for global_rank, row in enumerate(rows, start=1):
        bucket_ranks[row["bucket"]] += 1
        row["rank"] = global_rank
        row["bucketRank"] = bucket_ranks[row["bucket"]]

    bucket_totals: dict[str, Counter[str]] = {bucket: Counter() for bucket in BUCKET_ORDER}
    frontier_totals: dict[str, Counter[str]] = {bucket: Counter() for bucket in BUCKET_ORDER}
    for row in rows:
        bucket = row["bucket"]
        bucket_totals[bucket]["missions"] += 1
        bucket_totals[bucket]["score"] += row["score"]
        for key, value in row["metrics"].items():
            bucket_totals[bucket][key] += int(value)
        frontier_totals[bucket].update(row["frontierContributions"])

    return {
        "_schema": SCHEMA,
        "_generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "language": partial_report.get("language") or "",
        "sourcePartialOrderSchema": partial_report.get("_schema") or "",
        "rankingPolicy": {
            "bucketOrder": list(BUCKET_ORDER),
            "scoreWeights": SCORE_WEIGHTS,
            "frontierOrder": list(FRONTIER_ORDER),
            "note": "Triage score only; it does not assert scene chronology or evidence strength.",
        },
        "offlineExhaustionEvidence": offline_exhaustion_status or {
            "status": "not_supplied",
            "graphEffect": "none",
        },
        "summary": {
            "missions": len(rows),
            "buckets": [
                {"bucket": bucket, **dict(bucket_totals[bucket])}
                for bucket in BUCKET_ORDER
            ],
            "frontierContributionsByBucket": {
                bucket: dict(frontier_totals[bucket])
                for bucket in BUCKET_ORDER
            },
        },
        "missions": rows,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Source-only Story Recovery Gap Queue",
        "",
        f"Generated: `{report['_generatedAt']}`",
        "",
        "This is a recovery-work queue, not a proposed Story order. Main-story (`e`)",
        "missions sort first. Every score contribution is preserved in the JSON.",
        "",
        "## Ranking Policy",
        "",
        "Bucket order: " + ", ".join(f"`{bucket}`" for bucket in BUCKET_ORDER) + ".",
        "",
        "Score weights: " + ", ".join(
            f"`{key}` x {weight}" for key, weight in SCORE_WEIGHTS.items()
        ) + ".",
        "",
        (
            "Current-build offline-exhaustion evidence: "
            f"`{safe_key((report.get('offlineExhaustionEvidence') or {}).get('status')) or 'unknown'}`. "
            "These rows are deferred from triage only; they create no graph edge "
            "and reopen when a hash or audit target set changes."
        ),
        "",
        "## Bucket Summary",
        "",
        "| bucket | missions | score | scenes | isolated (core: actionable / native-closed / runtime-config-closed / definition-closed / non-mission-closed / offline-exhausted) | weak-only (actionable / exact-closed) | cycles | actionable LS gaps | closed LS negatives | actionable quest gaps | option gaps |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["summary"]["buckets"]:
        option_gaps = int(
            row.get("actionableNoExplicitOptionRouteGroups") or 0
        ) + int(
            row.get("actionableExcludedOptionEvidenceGroups") or 0
        )
        lines.append(
            f"| `{row['bucket']}` | {row.get('missions', 0)} | {row.get('score', 0)} | "
            f"{row.get('sceneCount', 0)} | {row.get('isolatedScenes', 0)} "
            f"({row.get('actionableCoreIsolatedScenes', 0)} / "
            f"{row.get('closedExactNativeIsolatedScenes', 0)} / "
            f"{row.get('closedExactRuntimeConfigIsolatedScenes', 0)} / "
            f"{row.get('closedDefinitionOnlyIsolatedScenes', 0)} / "
            f"{row.get('closedNonMissionContentIsolatedScenes', 0)} / "
            f"{row.get('deferredOfflineExhaustedIsolatedScenes', 0)}) | "
            f"{row.get('weakOnlyScenes', 0)} "
            f"({row.get('actionableWeakOnlyScenes', 0)} / "
            f"{row.get('closedExactNativeWeakOnlyScenes', 0)}) | "
            f"{row.get('sourceCycles', 0)} | "
            f"{row.get('untypedMultiSceneLevelscriptContexts', 0)} | "
            f"{row.get('closedNonPlaybackLevelscriptContexts', 0)} | "
            f"{row.get('questIdsWithoutStrictStoryAttachment', 0)} | {option_gaps} |"
        )

    lines.extend([
        "",
        "## Ranked Missions",
        "",
        "| rank | mission | bucket rank | score | scenes | isolated (core: actionable / native-closed / runtime-config-closed / definition-closed / non-mission-closed / offline-exhausted) | weak-only (actionable / exact-closed) | cycles | LS gaps | quest gaps | option gaps | primary frontier |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ])
    for row in report["missions"][:100]:
        metrics = row["metrics"]
        option_gaps = (
            metrics["actionableNoExplicitOptionRouteGroups"]
            + metrics["actionableExcludedOptionEvidenceGroups"]
        )
        lines.append(
            f"| {row['rank']} | `{md_escape(row['mission'])}` | {row['bucketRank']} | {row['score']} | "
            f"{metrics['sceneCount']} | {metrics['isolatedScenes']} "
            f"({metrics['actionableCoreIsolatedScenes']} / "
            f"{metrics['closedExactNativeIsolatedScenes']} / "
            f"{metrics['closedExactRuntimeConfigIsolatedScenes']} / "
            f"{metrics['closedDefinitionOnlyIsolatedScenes']} / "
            f"{metrics['closedNonMissionContentIsolatedScenes']} / "
            f"{metrics['deferredOfflineExhaustedIsolatedScenes']}) | "
            f"{metrics['weakOnlyScenes']} "
            f"({metrics['actionableWeakOnlyScenes']} / "
            f"{metrics['closedExactNativeWeakOnlyScenes']}) | "
            f"{metrics['sourceCycles']} | {metrics['untypedMultiSceneLevelscriptContexts']} | "
            f"{metrics['questIdsWithoutStrictStoryAttachment']} | {option_gaps} | "
            f"`{row['primaryFrontier']}` |"
        )

    main_rows = [row for row in report["missions"] if row["bucket"] == "main"][:25]
    lines.extend([
        "",
        "## Main-story Frontier Detail",
        "",
    ])
    for row in main_rows:
        metrics = row["metrics"]
        lines.extend([
            f"### {row['bucketRank']}. `{md_escape(row['mission'])}`",
            "",
            f"Score `{row['score']}`; primary frontier `{row['primaryFrontier']}`. "
            f"Scenes `{metrics['sceneCount']}`, isolated `{metrics['isolatedScenes']}` "
            f"(`{metrics['actionableCoreIsolatedScenes']}` actionable core, "
            f"`{metrics['closedExactNativeIsolatedScenes']}` exact-native closed, "
            f"`{metrics['closedExactRuntimeConfigIsolatedScenes']}` "
            "exact runtime-config closed, "
            f"`{metrics['closedDefinitionOnlyIsolatedScenes']}` definition-only closed, "
            f"`{metrics['closedNonMissionContentIsolatedScenes']}` non-mission content closed, "
            f"`{metrics['deferredOfflineExhaustedIsolatedScenes']}` current-build offline-exhausted), "
            f"weak-only `{metrics['weakOnlyScenes']}` "
            f"(`{metrics['actionableWeakOnlyScenes']}` actionable, "
            f"`{metrics['closedExactNativeWeakOnlyScenes']}` exact-native closed), "
            f"cycles `{metrics['sourceCycles']}`.",
            "",
            f"Quest ids without strict Story attachment: "
            f"`{metrics['questIdsWithoutStrictStoryAttachment']}`; untyped multi-scene "
            f"LevelScript contexts: `{metrics['untypedMultiSceneLevelscriptContexts']}`; "
            f"closed binary-negative contexts: "
            f"`{metrics['closedNonPlaybackLevelscriptContexts']}`; "
            f"actionable option gap groups: "
            f"`{metrics['actionableNoExplicitOptionRouteGroups'] + metrics['actionableExcludedOptionEvidenceGroups']}` "
            f"(`{metrics['singleOptionNoExplicitRouteGroups']}` single-option "
            f"acknowledgements and `{metrics['closedExcludedOptionEvidenceGroups']}` "
            "shared/cosmetic exclusions are retained but not scored).",
            "",
        ])
        contexts = row.get("untypedMultiSceneLevelscriptContexts") or []
        if contexts:
            lines.append("Top untyped LevelScript contexts:")
            lines.append("")
            for context in contexts[:5]:
                scenes = ", ".join(f"`{md_escape(key)}`" for key in context["sceneKeys"])
                lines.append(f"- `{md_escape(context['sourceFile'])}`: {scenes}")
            lines.append("")
        closed_contexts = row.get("closedNonPlaybackLevelscriptContexts") or []
        if closed_contexts:
            lines.append("Closed binary-negative LevelScript contexts:")
            lines.append("")
            for context in closed_contexts[:5]:
                classifications = ", ".join(
                    f"`{md_escape(item['sceneKey'])}` "
                    f"({md_escape(item['status'])})"
                    for item in context.get("unresolvedBinaryClassifications") or []
                )
                lines.append(
                    f"- `{md_escape(context['sourceFile'])}`: {classifications}"
                )
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", default="CN")
    parser.add_argument("--reports-dir", type=Path, default=ROOT / "reports" / "mission_order")
    parser.add_argument(
        "--table-root",
        type=Path,
        default=ROOT / "export_full" / "structured" / "StreamingAssets" / "Table",
        help="Authored table directory used to classify non-mission content "
             "keys out of the narrative queue.",
    )
    parser.add_argument(
        "--game-assembly",
        type=Path,
        default=None,
        help=(
            "Optional current GameAssembly.dll used to validate build-locked "
            "offline-exhaustion evidence. Defaults to endfield_paths.bat."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    partial_report = build_partial_order_report(args.language)
    from story_builder.level_bindings import (  # noqa: PLC0415
        build_levelscript_action_story_occurrences,
        build_levelscript_native_story_playback_index,
    )

    action_story_occurrences = build_levelscript_action_story_occurrences()
    native_playback_index = build_levelscript_native_story_playback_index()
    mission_dir = ROOT / "webui" / "data" / "lang" / args.language / "mission"
    mission_payloads: dict[str, dict[str, Any]] = {}
    mission_bundle_presence: set[str] = set()
    for partial_row in partial_report.get("missions") or []:
        mission = safe_key(partial_row.get("mission"))
        path = mission_dir / f"{mission}.json"
        if not path.is_file():
            continue
        mission_payloads[mission] = load_mission_payload_with_variants(
            mission_dir,
            mission,
        )
        mission_bundle_presence.add(mission)

    offline_exhaustion_index, offline_exhaustion_status = (
        build_offline_exhaustion_index(
            partial_report,
            args.table_root,
            game_assembly_path=args.game_assembly,
        )
    )
    report = build_gap_report(
        partial_report,
        mission_payloads,
        mission_bundle_presence,
        native_playback_index,
        action_story_occurrences,
        table_root=args.table_root,
        offline_exhaustion_index=offline_exhaustion_index,
        offline_exhaustion_status=offline_exhaustion_status,
    )
    out_json = args.reports_dir / f"source_story_gap_queue_{args.language}.json"
    out_md = args.reports_dir / f"source_story_gap_queue_{args.language}.md"
    write_report_json(out_json, report)
    write_text_if_changed(out_md, render_markdown(report))
    main_rows = [row for row in report["missions"] if row["bucket"] == "main"]
    print(f"Source-only Story gap queue: {out_md.relative_to(ROOT)}")
    print(f"Source-only Story gap data: {out_json.relative_to(ROOT)}")
    if main_rows:
        print(
            f"Top main-story mission: {main_rows[0]['mission']} "
            f"score={main_rows[0]['score']} frontier={main_rows[0]['primaryFrontier']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

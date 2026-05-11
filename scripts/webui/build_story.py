"""Preprocess Endfield exported tables into per-conversation JSON files for the WebUI.

Reads:
  export_full/structured/StreamingAssets/Table/I18nTextTable_*.json      (localized string dictionaries)
  export_full/structured/StreamingAssets/Table/TextTable.json            (named text keys -> i18n ids)
  export_full/structured/StreamingAssets/Table/DialogTextTable.json      (story dialog lines)
  export_full/structured/StreamingAssets/Table/SNSDialogTable.json       (in-game phone chats)
  export_full/structured/StreamingAssets/Table/SNSDialogOptionTable.json (chat reply choices)
  export_full/structured/StreamingAssets/Table/SNSChatTable.json         (SNS chat metadata / icons)
  export_full/structured/StreamingAssets/Table/DialogOptionTable.json    (dialog choices)
  export_full/structured/StreamingAssets/Table/DialogSummaryTable.json   (dialog recaps)
  export_full/structured/StreamingAssets/Table/MailSenderTable.json      (mail sender icon -> actor mapping)
  export_full/structured/StreamingAssets/Table/RadioTable.json           (radio text)
  export_full/structured/StreamingAssets/Table/RemoteCommonTable.json    (remote comm story calls)
  export_full/structured/StreamingAssets/Table/EnvTalkTable.json         (ambient / environment talk)

Falls back to the legacy top-level export_full/StreamingAssets/... layout when needed.

Writes:
  webui/data/manifest.json                 (available language bundles)
  webui/data/lang/<code>/index.json        (lightweight conversation list)
  webui/data/lang/<code>/conv/<key>.json
  webui/data/lang/<code>/mission/<id>.json (lazy mission context/flow)
  webui/data/lang/<code>/reference/...     (raw localized table reference)

Run from the repo root:
    python scripts/webui/build_story.py
    python scripts/webui/build_story.py --profile full
"""
from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
import re
import shutil
import sys
import time
from collections import Counter, defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from build_story_asset_index import build_asset_index as shared_build_asset_index
from build_story_paths import _existing_unique_paths, _resolve_recovered_dir, _resolve_structured_source_dir
from build_story_reports import (
    build_scene_order_gap_summary as shared_build_scene_order_gap_summary,
    collect_scene_order_gap_rows as shared_collect_scene_order_gap_rows,
    write_inferred_option_anchors_report as shared_write_inferred_option_anchors_report,
    write_scene_order_gap_reports as shared_write_scene_order_gap_reports,
)
from build_story_source_links import build_source_links as build_story_source_links
from recover_timeline_line_orders import (
    TimelineRecoveryConfig,
    default_order_out as timeline_recovery_order_out,
    discover_asset_maps as discover_timeline_asset_maps,
    recover_timeline_line_orders,
    timeline_order_is_current,
)
from recover_mission_timelines import (
    EVIDENCE_POLICY as MISSION_TIMELINE_EVIDENCE_POLICY,
    canonical_cutscene_key as mission_canonical_cutscene_key,
    load_timeline_index as load_mission_timeline_index,
    mission_files as mission_timeline_files,
    recover_mission as recover_source_mission_timeline,
    render_markdown as render_mission_timeline_markdown,
    source_backed_scene_edges_from_scene_graph,
    summarize as summarize_mission_timeline_recovery,
    write_json as write_mission_timeline_recovery_json,
)
from scene_order_gap_shared import (
    build_runtime_registry_debug as shared_build_runtime_registry_debug,
    build_scene_order_disorder_warning as shared_build_scene_order_disorder_warning,
    load_dialog_id_registry as shared_load_dialog_id_registry,
)


REPORTS_DIR = ROOT / "reports"
EXPORT_ROOT = ROOT / "export_full"
STORY_SOURCE_LINKS_PATH = EXPORT_ROOT / "recovered" / "story_source_links.json"


STREAMING_ASSETS_DIR = _resolve_structured_source_dir(EXPORT_ROOT, "StreamingAssets")
PERSISTENT_ASSETS_DIR = _resolve_structured_source_dir(EXPORT_ROOT, "Persistent")
STREAMING_TABLE_DIR = STREAMING_ASSETS_DIR / "Table"
PERSISTENT_TABLE_DIR = PERSISTENT_ASSETS_DIR / "Table"
TABLE_DIR = STREAMING_TABLE_DIR
DATA_JSON_DIR = STREAMING_ASSETS_DIR / "Data" / "Json"
LEVELDATA_DIR = DATA_JSON_DIR / "LevelData"
LEVELSCRIPT_DIR = DATA_JSON_DIR / "LevelScriptData"
GAMEPLAY_CONFIG_DIR = DATA_JSON_DIR / "GameplayConfig"
MRA_DIR = DATA_JSON_DIR / "MissionRuntimeAsset"
NPC_PROXY_EX_PATH = GAMEPLAY_CONFIG_DIR / "NpcProxyExDataTable.json"
NPC_PROXY_TABLE_PATH = GAMEPLAY_CONFIG_DIR / "NpcProxyTable.json"
ATMOS_CLUSTER_TABLE_PATH = GAMEPLAY_CONFIG_DIR / "AtmosphericNpcClusterDataTable.json"
ANIME_TREE_DIRS = [
    _resolve_recovered_dir(
        EXPORT_ROOT,
        ("recovered", "AnimeStudio-net9-extracted"),
        ("AnimeStudio-net9-extracted",),
    ),
    _resolve_recovered_dir(
        EXPORT_ROOT,
        ("recovered", "AnimeStudio", "main", "TextAsset"),
        ("AnimeStudio", "main", "TextAsset"),
    ),
]
ANIME_RESOURCE_DIRS = _existing_unique_paths([
    *ANIME_TREE_DIRS,
    EXPORT_ROOT / "recovered" / "AnimeStudio-cli" / "StreamingAssets" / "json_by_type" / "TextAsset",
    EXPORT_ROOT / "recovered" / "AnimeStudio-cli" / "Persistent" / "json_by_type" / "TextAsset",
    EXPORT_ROOT / "recovered" / "AnimeStudio-cli" / "StreamingAssets" / "json_by_type" / "MonoBehaviour",
    EXPORT_ROOT / "recovered" / "AnimeStudio-cli" / "Persistent" / "json_by_type" / "MonoBehaviour",
])
EXPORTED_DIR = EXPORT_ROOT
OUT_DIR = ROOT / "webui" / "data"
LANG_DIR = OUT_DIR / "lang"
ASSET_DIR = OUT_DIR / "assets"
DEFAULT_LANGUAGE = "CN"
BUILD_PROFILES = ("lean", "full")
DEFAULT_BUILD_PROFILE = "lean"
TIMELINE_RECOVERY_MODES = ("auto", "always", "never")
I18N_FILE_RE = re.compile(r"^I18nTextTable_([A-Z]+)\.json$")
I18N_HOTFIX_TABLE = "I18nHotFix.json"
I18N_HOTFIX_LANGUAGE_TYPES = {
    "EN": 1,
    "JP": 2,
    "KR": 3,
    "TC": 4,
    "MX": 5,
    "BR": 6,
    "FR": 7,
    "DE": 8,
    "RU": 9,
    "IT": 10,
    "ID": 11,
    "TH": 12,
    "VN": 13,
}
LANGUAGE_INFO = {
    "BR": {
        "label": "Portuguese (Brazil)",
        "nativeLabel": "Português (Brasil)",
        "htmlLang": "pt-BR",
        "uiLocale": "en",
    },
    "CN": {
        "label": "Chinese (Simplified)",
        "nativeLabel": "简体中文",
        "htmlLang": "zh-CN",
        "uiLocale": "zh",
    },
    "DE": {
        "label": "German",
        "nativeLabel": "Deutsch",
        "htmlLang": "de-DE",
        "uiLocale": "en",
    },
    "EN": {
        "label": "English",
        "nativeLabel": "English",
        "htmlLang": "en",
        "uiLocale": "en",
    },
    "FR": {
        "label": "French",
        "nativeLabel": "Français",
        "htmlLang": "fr-FR",
        "uiLocale": "en",
    },
    "ID": {
        "label": "Indonesian",
        "nativeLabel": "Bahasa Indonesia",
        "htmlLang": "id-ID",
        "uiLocale": "en",
    },
    "IT": {
        "label": "Italian",
        "nativeLabel": "Italiano",
        "htmlLang": "it-IT",
        "uiLocale": "en",
    },
    "JP": {
        "label": "Japanese",
        "nativeLabel": "日本語",
        "htmlLang": "ja-JP",
        "uiLocale": "en",
    },
    "KR": {
        "label": "Korean",
        "nativeLabel": "한국어",
        "htmlLang": "ko-KR",
        "uiLocale": "en",
    },
    "MX": {
        "label": "Spanish (Latin America)",
        "nativeLabel": "Español (Latinoamérica)",
        "htmlLang": "es-419",
        "uiLocale": "en",
    },
    "RU": {
        "label": "Russian",
        "nativeLabel": "Русский",
        "htmlLang": "ru-RU",
        "uiLocale": "en",
    },
    "TC": {
        "label": "Chinese (Traditional)",
        "nativeLabel": "繁體中文",
        "htmlLang": "zh-TW",
        "uiLocale": "zh",
    },
    "TH": {
        "label": "Thai",
        "nativeLabel": "ไทย",
        "htmlLang": "th-TH",
        "uiLocale": "en",
    },
    "VN": {
        "label": "Vietnamese",
        "nativeLabel": "Tiếng Việt",
        "htmlLang": "vi-VN",
        "uiLocale": "en",
    },
}

DLG_RE = re.compile(r"^dlg_(.+)_(\d+)_(\d+)$")
SNS_RE = re.compile(r"^sns_(.+)_(\d+)$")
TYPE_RE = re.compile(r"^([a-z]+)(\d+)?")
MISSION_STORY_TYPES = {"e", "a", "gm", "c", "sm", "m", "f", "db", "dm"}
ADMIN_ACTOR_IDS = {"endmin", "endminf", "endminm"}
# After stripping the trailing line index, a misc bucket key like
# `dlg_c13m3_3d5` decomposes into mission `c13m3` and scene `3d5`.
MISC_BUCKET_RE = re.compile(r"^(.+)_(\d+(?:d\d+)?)$")
# Scene tokens may be pure digits (`1`) or have a sub-scene suffix (`4d5`).
SCENE_TOK = r"\d+(?:d\d+)?"
SUMMARY_RE = re.compile(rf"^summary_(.+)_({SCENE_TOK})_(\d+)$")
OPTION_RE = re.compile(rf"^option_dlg_(.+)_({SCENE_TOK})_(\d+)_(\d+)$")
RADIO_RE = re.compile(rf"^radio_(.+)_({SCENE_TOK})$")
BLACK_RE = re.compile(rf"^black_(.+)_({SCENE_TOK})_(\d+)$")
REMOTECOMM_RE = re.compile(rf"^remotecomm_(.+?)(?:_({SCENE_TOK}))?$")
HEX_UID_RE = re.compile(rb"[0-9a-f]{8}")
LT_BINDING_RE = re.compile(r"^lt:(?P<kind>p|mp):(?P<uid1>[0-9a-f]{8}):(?P<uid2>[0-9a-f]{8})$")
CUTSCENE_TEXT_ROW_RE = re.compile(
    r"^(?P<group>cutscene_.+)_(?P<line>\d+)(?P<sub>d\d+)?(?P<gender>_[fm])?$",
    re.IGNORECASE,
)
PRINTABLE_ASCII_MIN = 32
PRINTABLE_ASCII_MAX = 126
NARRATIVE_VIDEO_EXTENSIONS = {
    ".mp4",
    ".webm",
    ".mov",
    ".avi",
    ".m4v",
    ".ogv",
    ".usm",
}


_MISSION_FLOW_CACHE: dict[str, dict | None] = {}
_DIALOG_TREE_CACHE: dict[str, dict | None] = {}
_DIALOG_TREE_SOURCE_CACHE: dict[str, dict | None] = {}
_DIALOG_TREE_FILE_CACHE: dict[str, dict | None] = {}
_RELATED_DIALOG_TREE_FILE_CACHE: dict[tuple[str, tuple[str, ...]], list[dict]] = {}
_ANIME_TREE_PATH_INDEX: dict[str, Path] | None = None
_ANIME_TREE_SORTED_STEMS: list[str] | None = None
_DIALOG_TREE_FRAGMENT_TARGETS_CACHE: dict[str, list[dict]] | None = None
_DIALOG_TREE_SCENE_LINKS_CACHE: dict[str, list[dict]] | None = None
_DIALOG_TREE_EXTRA_CONFIG_CACHE: dict[str, dict | None] = {}
_DIALOG_TIMELINE_LINE_ORDER_CACHE: dict[str, list[dict]] | None = None
_NPC_PROXY_EX_CACHE: dict | None = None
_MISSION_LEVELSCRIPT_CACHE: dict[tuple[str, tuple[str, ...]], list[dict]] = {}
_LEVELSCRIPT_BINDING_CACHE: dict[str, dict] = {}
_LEVELDATA_NAMED_TABLE_CACHE: dict[str, list[dict]] = {}
_JSON_FILE_CACHE: dict[str, dict] = {}
_MISSION_AREA_CACHE: dict[str, dict] | None = None
_NPC_PROXY_TABLE_CACHE: dict[str, dict] | None = None
_CUTSCENE_ASSET_CACHE: dict[str, dict] | None = None
_NARRATIVE_VIDEO_CACHE: list[dict] | None = None
_DIALOG_REF_FIELDS = ("_dialogId", "snsDialogId")
_CUTSCENE_REF_FIELDS = ("_cutsceneId",)
_REMOTECOMM_REF_FIELDS = ("_remoteCommId",)
_RADIO_REF_FIELDS = ("_radioId",)
MISSION_SCENE_ENTRY_KINDS = ("dlg", "sns", "cutscene", "black", "remotecomm", "radio")
SCENE_BINDING_TARGET_KINDS = ("dlg", "misc", "cutscene", "black", "remotecomm", "radio")
AUTHORED_LINE_ORDER_MODES = {
    "authoredBlend",
    "dialogTimeline",
    "dialogTree",
    "dialogTreeExtraConfig",
    "dialogTreeFragment",
}
TIMELINE_LINE_ORDER_PATHS = [
    timeline_recovery_order_out(EXPORT_ROOT),
]


def _find_anime_tree_path(filename: str) -> Path:
    for base in ANIME_RESOURCE_DIRS:
        candidate = base / filename
        if candidate.exists():
            return candidate
    return ANIME_RESOURCE_DIRS[0] / filename if ANIME_RESOURCE_DIRS else ANIME_TREE_DIRS[0] / filename


def _iter_anime_tree_files(pattern: str):
    seen: set[str] = set()
    for base in ANIME_RESOURCE_DIRS:
        if not base.exists():
            continue
        for path in sorted(base.glob(pattern)):
            if path.name in seen:
                continue
            seen.add(path.name)
            yield path


def _get_anime_tree_path_index() -> dict[str, Path]:
    global _ANIME_TREE_PATH_INDEX, _ANIME_TREE_SORTED_STEMS
    if _ANIME_TREE_PATH_INDEX is None:
        index: dict[str, Path] = {}
        for path in _iter_anime_tree_files("*.json"):
            if path.name.endswith("_extra_config.json"):
                continue
            index.setdefault(path.stem, path)
        _ANIME_TREE_PATH_INDEX = index
        _ANIME_TREE_SORTED_STEMS = sorted(index.keys())
    return _ANIME_TREE_PATH_INDEX


def _iter_related_dialog_tree_paths(conv_key: str):
    seen: set[str] = set()
    exact_stems = [conv_key]
    prefix_stems = [conv_key]
    if conv_key.startswith("dlg_"):
        bare = conv_key[4:]
        if bare not in exact_stems:
            exact_stems.append(bare)
        if bare not in prefix_stems:
            prefix_stems.append(bare)
        if bare.startswith("blackbox_"):
            gpl = f"dlg_gpl_{bare}"
            if gpl not in exact_stems:
                exact_stems.append(gpl)
            if gpl not in prefix_stems:
                prefix_stems.append(gpl)

    path_index = _get_anime_tree_path_index()
    for stem in exact_stems:
        path = path_index.get(stem)
        if path is None:
            continue
        key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        yield path
    all_stems = _ANIME_TREE_SORTED_STEMS or sorted(path_index.keys())
    for stem in prefix_stems:
        prefix = f"{stem}_"
        for candidate_stem in all_stems:
            if not candidate_stem.startswith(prefix):
                continue
            path = path_index[candidate_stem]
            key = str(path).lower()
            if key in seen:
                continue
            seen.add(key)
            yield path


def _load_anime_resource_payload(path: Path):
    try:
        with path.open(encoding="utf-8-sig") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return payload

    script = payload.get("m_Script")
    if not isinstance(script, str) or not script:
        return payload

    try:
        decoded = base64.b64decode(script)
        decoded_text = decoded.decode("utf-8-sig")
        decoded_payload = json.loads(decoded_text)
    except (ValueError, binascii.Error, UnicodeDecodeError, json.JSONDecodeError):
        return payload

    return decoded_payload


def _walk_const_values(node, field_name):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == field_name:
                if isinstance(v, dict) and "constValue" in v:
                    yield v["constValue"]
                elif isinstance(v, str):
                    yield v
            else:
                yield from _walk_const_values(v, field_name)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_const_values(item, field_name)


def _extract_dialog_refs(quest) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for field in _DIALOG_REF_FIELDS:
        for val in _walk_const_values(quest, field):
            if isinstance(val, str) and val and val not in seen:
                seen.add(val)
                out.append(val)
    return out


def _extract_cutscene_refs(quest) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for field in _CUTSCENE_REF_FIELDS:
        for val in _walk_const_values(quest, field):
            if isinstance(val, str) and val and val not in seen:
                seen.add(val)
                out.append(val)
    return out


def _extract_remotecomm_refs(quest) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for field in _REMOTECOMM_REF_FIELDS:
        for val in _walk_const_values(quest, field):
            if isinstance(val, str) and val and val not in seen:
                seen.add(val)
                out.append(val)
    return out


def _extract_radio_refs(quest) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for field in _RADIO_REF_FIELDS:
        for val in _walk_const_values(quest, field):
            if isinstance(val, str) and val and val not in seen:
                seen.add(val)
                out.append(val)
    return out


def _extract_client_action_refs(raw: dict, field_names: tuple[str, ...]) -> dict[str, list[str]]:
    action_list = (((raw.get("actionMapRaw") or {}).get("dataMap") or {}).get("actionList") or [])
    refs_by_action_id: dict[int, list[str]] = {}
    for action in action_list:
        action_id = action.get("_ID")
        if not isinstance(action_id, int):
            continue
        refs: list[str] = []
        seen: set[str] = set()
        for field_name in field_names:
            for val in _walk_const_values(action, field_name):
                if isinstance(val, str) and val and val not in seen:
                    seen.add(val)
                    refs.append(val)
        if refs:
            refs_by_action_id[action_id] = refs

    out: dict[str, list[str]] = {}
    for key_row, action_id in zip(raw.get("clientActionMapKey") or [], raw.get("clientActionMapValue") or []):
        if not isinstance(key_row, dict) or not isinstance(action_id, int):
            continue
        quest_id = key_row.get("questId")
        if not isinstance(quest_id, str) or not quest_id:
            continue
        refs = refs_by_action_id.get(action_id)
        if not refs:
            continue
        bucket = out.setdefault(quest_id, [])
        for ref in refs:
            if ref not in bucket:
                bucket.append(ref)
    return out


def _condition_short_type(full_type: str) -> str:
    # "Beyond.Gameplay.CheckMissionIntProperty, Gameplay.Beyond" -> "CheckMissionIntProperty"
    head = full_type.split(",", 1)[0]
    return head.rsplit(".", 1)[-1] if head else ""


def _extract_branch_flags(cond) -> list[dict]:
    if not isinstance(cond, dict):
        return []
    out: list[dict] = []
    t = cond.get("$type", "")
    short = _condition_short_type(t)
    if short == "CombineCondition":
        for sub in cond.get("subConditions", []) or []:
            out.extend(_extract_branch_flags(sub))
        return out
    if short == "CheckMissionIntProperty":
        out.append({
            "type": short,
            "key": (cond.get("_key") or {}).get("constValue"),
            "cmp": (cond.get("_comparer") or {}).get("constValue"),
            "val": (cond.get("_compareValue") or {}).get("constValue"),
        })
        return out
    if short == "CheckQuestState":
        out.append({
            "type": short,
            "key": (cond.get("_questId") or {}).get("constValue"),
            "cmp": (cond.get("_comparer") or {}).get("constValue"),
            "val": (cond.get("_targetQuestState") or {}).get("constValue"),
        })
        return out
    if short:
        # Unknown leaf — surface the type so the UI can still hint at it.
        out.append({"type": short})
    return out


def _combine_eval_string(cond) -> str:
    if not isinstance(cond, dict):
        return ""
    if _condition_short_type(cond.get("$type", "")) == "CombineCondition":
        return cond.get("conditionEvalString", "") or ""
    return ""


def _natural_key(value: str) -> tuple:
    parts = re.findall(r"\d+|\D+", value or "")
    out = []
    for part in parts:
        if part.isdigit():
            out.append((0, int(part)))
        else:
            out.append((1, part))
    return tuple(out)


def _quest_sort_key(q: dict) -> tuple:
    tail = (q.get("id") or "").split("#")[-1]
    return (q.get("flowIndex", 10**9), _natural_key(tail), q.get("id") or "")


def _extract_tracking_hints(quest) -> list[dict]:
    out: list[dict] = []
    seen: set[tuple] = set()
    for obj in (quest.get("objectiveList") or []):
        for info in (obj.get("trackingInfoList") or []):
            if not isinstance(info, dict):
                continue
            hint: dict = {}
            typ = _condition_short_type(info.get("$type", ""))
            if typ:
                hint["type"] = typ
            scene_id = info.get("sceneId")
            if isinstance(scene_id, str) and scene_id:
                hint["scene"] = scene_id
            npc_proxy_id = info.get("npcProxyId")
            if isinstance(npc_proxy_id, str) and npc_proxy_id:
                hint["npcProxyId"] = npc_proxy_id
            mission_area_id = info.get("missionAreaId")
            if isinstance(mission_area_id, str) and mission_area_id:
                hint["missionAreaId"] = mission_area_id
            jump_id = info.get("jumpId")
            if isinstance(jump_id, str) and jump_id:
                hint["jumpId"] = jump_id
            tracking_pos = info.get("trackingPos")
            if isinstance(tracking_pos, dict):
                try:
                    hint["trackingPos"] = {
                        "x": float(tracking_pos.get("x", 0.0)),
                        "y": float(tracking_pos.get("y", 0.0)),
                        "z": float(tracking_pos.get("z", 0.0)),
                    }
                except (TypeError, ValueError):
                    pass
            if not hint:
                continue
            key = (
                hint.get("type", ""),
                hint.get("scene", ""),
                hint.get("npcProxyId", ""),
                hint.get("missionAreaId", ""),
                hint.get("jumpId", ""),
                tuple(
                    round(float(hint["trackingPos"][axis]), 3)
                    for axis in ("x", "y", "z")
                ) if hint.get("trackingPos") else (),
            )
            if key in seen:
                continue
            seen.add(key)
            out.append(hint)
    return out


def _extract_objective_tracking_hints(obj: dict) -> list[dict]:
    quest_like = {"objectiveList": [obj]}
    return _extract_tracking_hints(quest_like)


def _walk_field_values(node, field_name):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == field_name:
                if isinstance(v, dict) and "constValue" in v:
                    yield v["constValue"]
                else:
                    yield v
            else:
                yield from _walk_field_values(v, field_name)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_field_values(item, field_name)


def _extract_condition_anchor_leaves(cond) -> list[dict]:
    if not isinstance(cond, dict):
        return []
    short = _condition_short_type(cond.get("$type", ""))
    if short == "CombineCondition":
        out: list[dict] = []
        for sub in cond.get("subConditions") or []:
            out.extend(_extract_condition_anchor_leaves(sub))
        return out

    leaf: dict = {"type": short or "Unknown"}
    story_refs: list[str] = []
    for field_name in (*_DIALOG_REF_FIELDS, *_CUTSCENE_REF_FIELDS, *_REMOTECOMM_REF_FIELDS, *_RADIO_REF_FIELDS):
        for value in _walk_field_values(cond, field_name):
            if isinstance(value, str) and value and value not in story_refs:
                story_refs.append(value)
    if story_refs:
        leaf["storyRefs"] = story_refs

    level_ids: list[str] = []
    for field_name in ("_sceneId", "_levelId"):
        for value in _walk_field_values(cond, field_name):
            if isinstance(value, str) and value and value not in level_ids:
                level_ids.append(value)
    if level_ids:
        leaf["sceneIds"] = level_ids

    script_ids: list[int] = []
    for value in _walk_field_values(cond, "_scriptId"):
        if isinstance(value, dict):
            script_id = value.get("scriptId")
            if isinstance(script_id, int) and script_id not in script_ids:
                script_ids.append(script_id)
        elif isinstance(value, int) and value not in script_ids:
            script_ids.append(value)
    if script_ids:
        leaf["scriptIds"] = script_ids

    logic_ids: list[int] = []
    for value in _walk_field_values(cond, "_entityId"):
        if isinstance(value, dict):
            logic_id = value.get("logicId")
            if isinstance(logic_id, int) and logic_id not in logic_ids:
                logic_ids.append(logic_id)
    if logic_ids:
        leaf["logicIds"] = logic_ids

    quest_refs: list[dict] = []
    quest_ids = [
        value for value in _walk_field_values(cond, "_questId")
        if isinstance(value, str) and value
    ]
    target_states = list(_walk_field_values(cond, "_targetQuestState"))
    target_state = target_states[0] if target_states else None
    for quest_id in _unique_preserve(quest_ids):
        quest_ref = {"questId": quest_id}
        if isinstance(target_state, (int, float, str)):
            quest_ref["targetState"] = target_state
        quest_refs.append(quest_ref)
    if quest_refs:
        leaf["questStateRefs"] = quest_refs

    compare_keys = [
        value for value in _walk_field_values(cond, "_key")
        if isinstance(value, str) and value
    ]
    if compare_keys:
        leaf["keys"] = _unique_preserve(compare_keys)
    compare_values = list(_walk_field_values(cond, "_compareValue"))
    if compare_values:
        leaf["compareValues"] = _unique_preserve(compare_values)
    finish_ids = list(_walk_field_values(cond, "_finishId"))
    if finish_ids:
        leaf["finishIds"] = _unique_preserve(finish_ids)
    trigger_slot_ids = list(_walk_field_values(cond, "_triggerSlotIdOutput"))
    if trigger_slot_ids:
        leaf["triggerSlotIds"] = _unique_preserve(trigger_slot_ids)
    succeed_ids = list(_walk_field_values(cond, "_succeedId"))
    if succeed_ids:
        leaf["succeedIds"] = _unique_preserve(succeed_ids)
    new_states = list(_walk_field_values(cond, "_newState"))
    if new_states:
        leaf["newStates"] = _unique_preserve(new_states)
    old_states = list(_walk_field_values(cond, "_oldState"))
    if old_states:
        leaf["oldStates"] = _unique_preserve(old_states)
    event_trigger_ids = list(_walk_field_values(cond, "level_event_id_trigger"))
    if event_trigger_ids:
        leaf["eventTriggerIds"] = _unique_preserve(event_trigger_ids)

    return [leaf]


def _extract_objective_anchors(quest: dict) -> list[dict]:
    out: list[dict] = []
    for index, obj in enumerate(quest.get("objectiveList") or [], start=1):
        if not isinstance(obj, dict):
            continue
        tracking = [_resolve_tracking_hint(hint) for hint in _extract_objective_tracking_hints(obj)]
        leaves = _extract_condition_anchor_leaves(obj.get("condition"))

        anchor: dict = {
            "index": index,
            "tracking": tracking,
            "conditionLeaves": leaves,
        }
        description = obj.get("description")
        if isinstance(description, dict) and description.get("key"):
            anchor["descriptionKey"] = str(description["key"])
        if obj.get("muteTrack"):
            anchor["muteTrack"] = True
        if obj.get("isBlockObjective"):
            anchor["isBlockObjective"] = True

        condition_types = _unique_preserve([
            str(leaf.get("type") or "")
            for leaf in leaves
            if leaf.get("type")
        ])
        if condition_types:
            anchor["conditionTypes"] = condition_types

        tracking_types = _unique_preserve([
            str(hint.get("type") or "")
            for hint in tracking
            if hint.get("type")
        ])
        if tracking_types:
            anchor["trackingTypes"] = tracking_types

        story_refs = _unique_preserve([
            str(ref)
            for leaf in leaves
            for ref in (leaf.get("storyRefs") or [])
            if ref
        ])
        if story_refs:
            anchor["storyRefs"] = story_refs

        scene_ids = _unique_preserve([
            str(scene_id)
            for value in (
                [scene_id for leaf in leaves for scene_id in (leaf.get("sceneIds") or [])]
                + [hint.get("scene") for hint in tracking if hint.get("scene")]
            )
            if value
            for scene_id in [value]
        ])
        if scene_ids:
            anchor["sceneIds"] = scene_ids

        mission_area_ids = _unique_preserve([
            str(value)
            for value in ([hint.get("missionAreaId") for hint in tracking if hint.get("missionAreaId")])
            if value
        ])
        if mission_area_ids:
            anchor["missionAreaIds"] = mission_area_ids

        npc_proxy_ids = _unique_preserve([
            str(value)
            for value in ([hint.get("npcProxyId") for hint in tracking if hint.get("npcProxyId")])
            if value
        ])
        if npc_proxy_ids:
            anchor["npcProxyIds"] = npc_proxy_ids

        jump_ids = _unique_preserve([
            str(value)
            for value in ([hint.get("jumpId") for hint in tracking if hint.get("jumpId")])
            if value
        ])
        if jump_ids:
            anchor["jumpIds"] = jump_ids

        script_ids = _unique_preserve([
            int(value)
            for leaf in leaves
            for value in (leaf.get("scriptIds") or [])
            if isinstance(value, int)
        ])
        if script_ids:
            anchor["scriptIds"] = script_ids

        logic_ids = _unique_preserve([
            int(value)
            for leaf in leaves
            for value in (leaf.get("logicIds") or [])
            if isinstance(value, int)
        ])
        if logic_ids:
            anchor["logicIds"] = logic_ids

        quest_state_refs = []
        seen_quest_state_refs: set[tuple[str, str]] = set()
        for leaf in leaves:
            for row in (leaf.get("questStateRefs") or []):
                quest_id = str(row.get("questId") or "")
                if not quest_id:
                    continue
                state_value = row.get("targetState")
                dedup = (quest_id, str(state_value))
                if dedup in seen_quest_state_refs:
                    continue
                seen_quest_state_refs.add(dedup)
                quest_ref = {"questId": quest_id}
                if state_value is not None:
                    quest_ref["targetState"] = state_value
                quest_state_refs.append(quest_ref)
        if quest_state_refs:
            anchor["questStateRefs"] = quest_state_refs

        if (
            anchor.get("tracking")
            or anchor.get("conditionTypes")
            or anchor.get("storyRefs")
            or anchor.get("sceneIds")
            or anchor.get("missionAreaIds")
            or anchor.get("npcProxyIds")
            or anchor.get("jumpIds")
            or anchor.get("scriptIds")
            or anchor.get("logicIds")
            or anchor.get("questStateRefs")
        ):
            out.append(anchor)
    return out


def _load_mission_areas() -> dict[str, dict]:
    global _MISSION_AREA_CACHE
    if _MISSION_AREA_CACHE is not None:
        return _MISSION_AREA_CACHE
    out: dict[str, dict] = {}
    path = GAMEPLAY_CONFIG_DIR / "MissionAreaTable.json"
    try:
        with path.open(encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        _MISSION_AREA_CACHE = out
        return out

    def walk(node) -> None:
        if isinstance(node, dict):
            mission_area_id = node.get("missionAreaId")
            if isinstance(mission_area_id, str) and mission_area_id and mission_area_id not in out:
                out[mission_area_id] = node
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(raw.get("m_areas") if isinstance(raw, dict) else raw)
    _MISSION_AREA_CACHE = out
    return out


def _load_npc_proxy_table() -> dict[str, dict]:
    global _NPC_PROXY_TABLE_CACHE
    if _NPC_PROXY_TABLE_CACHE is not None:
        return _NPC_PROXY_TABLE_CACHE
    path = NPC_PROXY_TABLE_PATH
    try:
        with path.open(encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        _NPC_PROXY_TABLE_CACHE = {}
        return {}
    table = raw.get("dataTable") if isinstance(raw, dict) else None
    _NPC_PROXY_TABLE_CACHE = table if isinstance(table, dict) else {}
    return _NPC_PROXY_TABLE_CACHE


def _canonical_cutscene_key(name: str) -> str:
    return mission_canonical_cutscene_key(name)


def _scene_ref_alias_candidates(name: str) -> list[str]:
    value = str(name or "").strip()
    if not value:
        return []

    aliases: list[str] = []

    def add(candidate: str) -> None:
        if candidate and candidate != value and candidate not in aliases:
            aliases.append(candidate)

    bases = [value]
    if match := re.match(r"^(?:f|m|fm)_(.+)$", value, re.IGNORECASE):
        bases.append(match.group(1))

    for base in bases:
        if base.startswith("cs_video_"):
            add(f"cutscene_{base[len('cs_video_'):]}")

        if not base.startswith((
            "dlg_",
            "sns_",
            "misc_dlg_",
            "cutscene_",
            "black_",
            "remotecomm_",
            "radio_",
        )):
            continue

        parent = base
        while parent.count("_") >= 3:
            stem, suffix = parent.rsplit("_", 1)
            if not suffix.isdigit():
                break
            add(stem)
            parent = stem

    return aliases


def _scene_key_matches_mission(scene_key: str, mission_id: str) -> bool:
    return not mission_id or f"_{mission_id}_" in f"_{scene_key}_"


def _resolve_payload_scene_key(payload_text: str, mission_id: str, dialog_key_resolver) -> str:
    candidates = _unique_preserve([
        str(payload_text or "").strip(),
        *_scene_ref_alias_candidates(payload_text),
    ])
    for candidate in candidates:
        if not candidate:
            continue
        scene_key = dialog_key_resolver(candidate) or ""
        if scene_key and _scene_key_matches_mission(scene_key, mission_id):
            return scene_key
        canonical_cutscene = _canonical_cutscene_key(candidate) or ""
        if canonical_cutscene and _scene_key_matches_mission(canonical_cutscene, mission_id):
            scene_key = dialog_key_resolver(canonical_cutscene) or canonical_cutscene
            if _scene_key_matches_mission(scene_key, mission_id):
                return scene_key
    return ""


def _cutscene_asset_name_without_prefix(name: str) -> str:
    value = str(name or "").strip()
    if match := re.match(r"^(?:f|m|fm)_(cutscene_.+)$", value, re.IGNORECASE):
        return match.group(1)
    return value


def _cutscene_variant_part(name: str, canonical_key: str) -> str:
    value = _cutscene_asset_name_without_prefix(name)
    value = re.sub(r"_p[0-9A-Fa-f]{8,16}$", "", value)
    if canonical_key and value.startswith(canonical_key):
        remainder = value[len(canonical_key):].strip("_")
    else:
        remainder = ""
    if not remainder:
        return "root"
    first = remainder.split("_", 1)[0]
    if first in {"Actor", "Audio", "Effect", "Light", "Others"}:
        return first
    if first in {"CHI", "CN", "EN", "ENG", "JP", "KO", "KR", "ENV"}:
        return f"locale:{first}"
    return "variant"


def _decode_anime_text_asset_payload(raw: dict) -> dict:
    script = raw.get("m_Script") if isinstance(raw, dict) else None
    if not isinstance(script, str) or not script.strip():
        return {}
    try:
        decoded = base64.b64decode(script, validate=True).decode("utf-8-sig")
        payload = json.loads(decoded)
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _infer_cutscene_mission_and_scene(
    canonical_key: str,
    known_missions: list[str],
) -> tuple[str, str]:
    prefix = "cutscene_"
    rest = canonical_key[len(prefix):] if canonical_key.startswith(prefix) else canonical_key
    mission = ""
    for candidate in known_missions:
        pattern = rf"(^|_){re.escape(candidate)}($|_)"
        if re.search(pattern, rest):
            mission = candidate
            break

    if mission:
        idx = rest.find(mission)
        before = rest[:idx].strip("_")
        after = rest[idx + len(mission):].strip("_")
        scene = "_".join(part for part in (before, after) if part) or "0"
        return mission, scene

    parts = [part for part in rest.split("_") if part]
    if len(parts) >= 2 and parts[0].startswith("map") and parts[1].startswith("lv"):
        mission = "_".join(parts[:2])
        return mission, "_".join(parts[2:]) or "0"
    if len(parts) >= 2 and parts[0].startswith(("dung", "indie", "blackbox")):
        mission = "_".join(parts[:2])
        return mission, "_".join(parts[2:]) or "0"
    if parts:
        mission = parts[0]
        return mission, "_".join(parts[1:]) or "0"
    return canonical_key, "0"


def _relative_asset_ref(label: str, source_root: Path, path: Path) -> str:
    try:
        rel_suffix = path.relative_to(source_root).as_posix()
    except ValueError:
        rel_suffix = path.name
    return f"{label}/{rel_suffix}" if rel_suffix else label


def _iter_narrative_video_roots(kind_dir: str):
    structured_roots = (
        ("StreamingAssets-structured", STREAMING_ASSETS_DIR),
        ("Persistent-structured", PERSISTENT_ASSETS_DIR),
    )
    for label, source_root in structured_roots:
        video_dir = source_root / "Data" / "Video" / "PC" / "Narrative" / kind_dir
        if video_dir.exists():
            yield label, source_root, video_dir

    raw_vfs_root = EXPORT_ROOT / "raw_vfs"
    for source in ("StreamingAssets", "Persistent"):
        files_root = raw_vfs_root / source / "files"
        if not files_root.exists():
            continue
        for bucket_dir in sorted(files_root.iterdir()):
            if not bucket_dir.is_dir():
                continue
            video_dir = bucket_dir / "Data" / "Video" / "PC" / "Narrative" / kind_dir
            if video_dir.exists():
                yield "raw_vfs", raw_vfs_root, video_dir


def _strip_gender_video_prefix(stem: str) -> tuple[str, str]:
    value = str(stem or "").strip()
    if match := re.match(r"^(?P<gender>f|m)_(?P<rest>.+)$", value, re.IGNORECASE):
        return match.group("gender").lower(), match.group("rest")
    return "", value


def _narrative_video_key_candidates(kind: str, stem: str) -> list[str]:
    _, base = _strip_gender_video_prefix(stem)
    candidates: list[str] = []

    def add(candidate: str) -> None:
        candidate = str(candidate or "").strip()
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    def letter_suffix_alias(value: str) -> str:
        match = re.match(r"^(.+_\d+)[a-z]+$", str(value or ""), re.IGNORECASE)
        return match.group(1) if match else ""

    if kind == "cutscene":
        raw = base
        if raw.startswith("cs_video_"):
            raw = raw[len("cs_video_"):]
        raw_alias = letter_suffix_alias(raw)
        if raw.startswith("dlg_"):
            add(raw)
            add(raw_alias)
            add(f"misc_{raw}")
            if raw_alias:
                add(f"misc_{raw_alias}")
        if raw.startswith("cutscene_"):
            add(_canonical_cutscene_key(raw) or raw)
            if raw_alias:
                add(_canonical_cutscene_key(raw_alias) or raw_alias)
        else:
            add(_canonical_cutscene_key(f"cutscene_{raw}") or f"cutscene_{raw}")
            if raw_alias:
                add(_canonical_cutscene_key(f"cutscene_{raw_alias}") or f"cutscene_{raw_alias}")
            if not raw.startswith("dlg_"):
                add(f"dlg_{raw}")
                if raw_alias:
                    add(f"dlg_{raw_alias}")
        add(raw)
        add(raw_alias)
    elif kind == "remotecomm":
        add(base)
        if not base.startswith("remotecomm_"):
            add(f"remotecomm_{base}")
    return candidates


def _load_narrative_video_assets() -> list[dict]:
    global _NARRATIVE_VIDEO_CACHE
    if _NARRATIVE_VIDEO_CACHE is not None:
        return _NARRATIVE_VIDEO_CACHE

    out: list[dict] = []
    for kind, kind_dir in (("cutscene", "Cutscene"), ("remotecomm", "RemoteComm")):
        for label, source_root, video_dir in _iter_narrative_video_roots(kind_dir):
            for path in sorted(video_dir.iterdir()):
                if not path.is_file() or path.suffix.lower() not in NARRATIVE_VIDEO_EXTENSIONS:
                    continue
                gender, base_stem = _strip_gender_video_prefix(path.stem)
                candidates = _narrative_video_key_candidates(kind, path.stem)
                if not candidates:
                    continue
                try:
                    size = path.stat().st_size
                except OSError:
                    size = 0
                out.append({
                    "kind": kind,
                    "name": path.name,
                    "stem": path.stem,
                    "baseStem": base_stem,
                    "gender": gender,
                    "format": path.suffix.lower().lstrip("."),
                    "size": size,
                    "source": label,
                    "rel": _relative_asset_ref(label, source_root, path),
                    "keyCandidates": candidates,
                })

    out.sort(key=lambda ref: (
        str(ref.get("kind") or ""),
        str((ref.get("keyCandidates") or [""])[0]),
        str(ref.get("baseStem") or ""),
        str(ref.get("gender") or ""),
        str(ref.get("source") or ""),
        str(ref.get("name") or ""),
    ))
    _NARRATIVE_VIDEO_CACHE = out
    return out


def _load_cutscene_assets() -> dict[str, dict]:
    global _CUTSCENE_ASSET_CACHE
    if _CUTSCENE_ASSET_CACHE is not None:
        return _CUTSCENE_ASSET_CACHE

    out: dict[str, dict] = {}
    for path in _iter_anime_tree_files("*cutscene*.json"):
        canonical_key = _canonical_cutscene_key(path.stem)
        if not canonical_key:
            continue
        try:
            with path.open(encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue

        entry = out.setdefault(
            canonical_key,
            {
                "variants": [],
                "componentCounts": Counter(),
                "levels": set(),
                "actorLabels": [],
                "paths": [],
                "versions": [],
                "audioEvents": [],
                "tags": [],
                "metadata": defaultdict(list),
                "keepCameraPaths": [],
                "useBlackScreen": False,
                "isTransition": False,
                "hasSubtitleTrack": False,
            },
        )
        payload = _decode_anime_text_asset_payload(raw) or raw
        part = _cutscene_variant_part(path.stem, canonical_key)
        entry["componentCounts"][part] += 1
        entry["variants"].append({
            "name": path.stem,
            "part": part,
            "file": str(path.relative_to(ROOT)).replace("\\", "/"),
            "path": str(payload.get("path") or ""),
            "version": str(payload.get("version") or raw.get("m_Version") or ""),
        })
        if payload.get("path"):
            entry["paths"].append(str(payload["path"]))
        if payload.get("version"):
            entry["versions"].append(str(payload["version"]))
        elif raw.get("m_Version") not in (None, ""):
            entry["versions"].append(str(raw["m_Version"]))
        audio_events = payload.get("audioEvents") or []
        if isinstance(audio_events, list):
            entry["audioEvents"].extend(str(event) for event in audio_events if event)
        tag_group = payload.get("tagGroup") if isinstance(payload, dict) else None
        if isinstance(tag_group, dict):
            tags = tag_group.get("tags") or []
            if isinstance(tags, list):
                entry["tags"].extend(str(tag) for tag in tags if tag)
            if tag_group.get("narrativeTypeTag") not in (None, ""):
                entry["metadata"]["narrativeTypeTag"].append(tag_group["narrativeTypeTag"])
        for meta_key in (
            "targetFrameRate",
            "skipType",
            "hideSquad",
            "useBlackScreen",
            "isTransition",
            "disableKeepCameras",
            "farCameraPosition",
            "noUIDispatch",
            "npcVisibleRuleType",
        ):
            if meta_key in payload and payload.get(meta_key) not in (None, "", [], {}):
                entry["metadata"][meta_key].append(payload[meta_key])
        keep_camera_path = str(payload.get("keepCameraPath") or "")
        if keep_camera_path:
            entry["keepCameraPaths"].append(keep_camera_path)
        entry["useBlackScreen"] = entry["useBlackScreen"] or bool(payload.get("useBlackScreen"))
        path_text = str(payload.get("path") or "")
        entry["isTransition"] = entry["isTransition"] or bool(payload.get("isTransition")) or ("CutsceneTransition/" in path_text)

        for track in payload.get("trackData") or []:
            for sub_track in track.get("subTracks") or []:
                if "SubtitleTrackData" in str(sub_track.get("$type") or ""):
                    entry["hasSubtitleTrack"] = True

        for actor in payload.get("actors") or []:
            descriptor = actor.get("descriptor") or {}
            level_id = str(descriptor.get("levelId") or "")
            if level_id:
                entry["levels"].add(level_id)
            label = (
                str(descriptor.get("entityId") or "")
                or str(descriptor.get("interactiveTemplateId") or "")
                or str(descriptor.get("name") or "")
            ).strip()
            if label and label not in entry["actorLabels"]:
                entry["actorLabels"].append(label)

    for entry in out.values():
        entry["variants"].sort(key=lambda item: item["name"])
        entry["paths"] = _unique_preserve(entry["paths"])
        entry["versions"] = _unique_preserve(entry["versions"])
        entry["audioEvents"] = _unique_preserve(entry["audioEvents"])
        entry["tags"] = _unique_preserve(entry["tags"])
        entry["metadata"] = {
            key: _unique_preserve(values)
            for key, values in sorted(entry["metadata"].items())
            if values
        }
        entry["keepCameraPaths"] = _unique_preserve(entry["keepCameraPaths"])
        entry["componentCounts"] = {
            key: entry["componentCounts"][key]
            for key in sorted(entry["componentCounts"], key=lambda item: (item != "root", item))
        }
        entry["levels"] = sorted(entry["levels"])
    _CUTSCENE_ASSET_CACHE = out
    return out


def _cutscene_component_summary(cutscene: dict, *, limit: int = 8) -> str:
    counts = cutscene.get("componentCounts") or {}
    if not isinstance(counts, dict) or not counts:
        variant_count = len(cutscene.get("variants") or [])
        return f"{variant_count} file{'s' if variant_count != 1 else ''}" if variant_count else ""
    parts = [
        f"{key} {count}"
        for key, count in counts.items()
        if count
    ]
    if len(parts) > limit:
        hidden = len(parts) - limit
        parts = [*parts[:limit], f"+{hidden} more"]
    return ", ".join(parts)


def _resolve_tracking_hint(hint: dict) -> dict:
    resolved = dict(hint)
    tracking_pos = hint.get("trackingPos")
    if isinstance(tracking_pos, dict):
        resolved["position"] = tracking_pos
        resolved["sourceType"] = "trackingPos"
        return resolved

    mission_area_id = str(hint.get("missionAreaId") or "")
    if mission_area_id:
        area = _load_mission_areas().get(mission_area_id) or {}
        shape = area.get("shape") or {}
        position = shape.get("position")
        if isinstance(position, dict):
            resolved["position"] = {
                "x": float(position.get("x", 0.0)),
                "y": float(position.get("y", 0.0)),
                "z": float(position.get("z", 0.0)),
            }
            resolved["sourceType"] = "missionArea"
            resolved["shapeType"] = shape.get("type")
            resolved["radius"] = shape.get("radius")
            route_points = (((area.get("trackingRouteInfo") or {}).get("points")) or [])
            if route_points:
                resolved["routePointCount"] = len(route_points)
            return resolved

    npc_proxy_id = str(hint.get("npcProxyId") or "")
    if npc_proxy_id:
        proxy = _load_npc_proxy_table().get(npc_proxy_id) or {}
        position = proxy.get("position")
        if isinstance(position, dict):
            resolved["position"] = {
                "x": float(position.get("x", 0.0)),
                "y": float(position.get("y", 0.0)),
                "z": float(position.get("z", 0.0)),
            }
            resolved["sourceType"] = "npcProxy"
            rotation = proxy.get("rotation")
            if isinstance(rotation, dict):
                resolved["rotation"] = {
                    "x": float(rotation.get("x", 0.0)),
                    "y": float(rotation.get("y", 0.0)),
                    "z": float(rotation.get("z", 0.0)),
                }
            return resolved

    return resolved


def _tracking_hint_pin(hint: dict) -> dict | None:
    position = hint.get("position")
    if not isinstance(position, dict):
        return None
    return {
        "scene": str(hint.get("scene") or ""),
        "trackingType": str(hint.get("type") or ""),
        "sourceType": str(hint.get("sourceType") or ""),
        "position": {
            "x": float(position.get("x", 0.0)),
            "y": float(position.get("y", 0.0)),
            "z": float(position.get("z", 0.0)),
        },
        **({"missionAreaId": hint["missionAreaId"]} if hint.get("missionAreaId") else {}),
        **({"npcProxyId": hint["npcProxyId"]} if hint.get("npcProxyId") else {}),
        **({"radius": hint["radius"]} if hint.get("radius") is not None else {}),
        **({"routePointCount": hint["routePointCount"]} if hint.get("routePointCount") is not None else {}),
    }


def _topo_sort_quests(quests_out: list[dict]) -> list[dict]:
    by_id = {q["id"]: q for q in quests_out if q.get("id")}
    indegree = {qid: 0 for qid in by_id}
    succs: dict[str, set[str]] = defaultdict(set)

    def has_path(src: str, dst: str) -> bool:
        if src == dst:
            return True
        seen: set[str] = set()
        stack = list(succs.get(src) or [])
        while stack:
            cur = stack.pop()
            if cur == dst:
                return True
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(succs.get(cur) or [])
        return False

    def add_edge(src: str, dst: str) -> None:
        if not src or not dst or src == dst:
            return
        if src not in by_id or dst not in by_id or dst in succs[src]:
            return
        succs[src].add(dst)
        indegree[dst] += 1

    for q in by_id.values():
        for prev in q.get("prev") or []:
            add_edge(prev, q["id"])

    story_ref_owners: dict[str, list[str]] = defaultdict(list)
    for q in by_id.values():
        qid = q["id"]
        for field_name in ("dialogs", "cutscenes", "remotecomms", "radios"):
            for ref in q.get(field_name) or []:
                if ref and qid not in story_ref_owners[ref]:
                    story_ref_owners[ref].append(qid)

    # A failedCondition story ref is an authored "this branch closes when that
    # scene happens" guard. Use it as a weak chronology edge when it does not
    # contradict the explicit prevQuestIdList graph.
    for q in by_id.values():
        qid = q["id"]
        for ref in q.get("failStoryRefs") or []:
            for owner_id in story_ref_owners.get(ref) or []:
                if owner_id == qid or has_path(owner_id, qid):
                    continue
                add_edge(qid, owner_id)

    ready = [by_id[qid] for qid, deg in indegree.items() if deg == 0]
    ready.sort(key=_quest_sort_key)

    out: list[dict] = []
    emitted: set[str] = set()
    while ready:
        cur = ready.pop(0)
        qid = cur["id"]
        if qid in emitted:
            continue
        emitted.add(qid)
        out.append(cur)
        for nxt in sorted(succs.get(qid, []), key=lambda next_id: _quest_sort_key(by_id[next_id])):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                ready.append(by_id[nxt])
        ready.sort(key=_quest_sort_key)

    if len(out) < len(by_id):
        for q in sorted(by_id.values(), key=_quest_sort_key):
            if q["id"] not in emitted:
                out.append(q)
    return out


def _load_npc_proxy_ex() -> dict:
    global _NPC_PROXY_EX_CACHE
    if _NPC_PROXY_EX_CACHE is not None:
        return _NPC_PROXY_EX_CACHE
    if not NPC_PROXY_EX_PATH.exists():
        _NPC_PROXY_EX_CACHE = {}
        return _NPC_PROXY_EX_CACHE
    try:
        with NPC_PROXY_EX_PATH.open(encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        _NPC_PROXY_EX_CACHE = {}
        return _NPC_PROXY_EX_CACHE
    _NPC_PROXY_EX_CACHE = raw if isinstance(raw, dict) else {}
    return _NPC_PROXY_EX_CACHE


def _levelscript_file_sort_key(path: Path) -> tuple:
    stem = path.stem
    if stem.isdigit():
        return (0, int(stem), stem)
    return (1, stem)


def _load_mission_levelscript_dialogs(mission_id: str, level_ids: list[str]) -> list[dict]:
    cache_key = (mission_id, tuple(dict.fromkeys(level_ids)))
    if cache_key in _MISSION_LEVELSCRIPT_CACHE:
        return _MISSION_LEVELSCRIPT_CACHE[cache_key]

    prefix = f"dlg_{mission_id}_".encode("ascii")
    hints: list[dict] = []
    for level_id in cache_key[1]:
        if not level_id:
            continue
        level_dir = LEVELSCRIPT_DIR / level_id
        if not level_dir.is_dir():
            continue
        for path in sorted(level_dir.glob("*.json"), key=_levelscript_file_sort_key):
            try:
                blob = path.read_bytes()
            except OSError:
                continue
            if prefix not in blob:
                continue
            dialogs: list[str] = []
            for token in re.findall(rb"[ -~]{4,}", blob):
                text = token.decode("ascii", "ignore")
                for dialog_id in re.findall(rf"dlg_{re.escape(mission_id)}_\d+", text):
                    if dialog_id not in dialogs:
                        dialogs.append(dialog_id)
            if dialogs:
                hints.append({
                    "levelId": level_id,
                    "file": path.relative_to(ROOT).as_posix(),
                    "fileOrder": _levelscript_file_sort_key(path),
                    "dialogs": dialogs,
                })
    _MISSION_LEVELSCRIPT_CACHE[cache_key] = hints
    return hints


def _u16(data: bytes, off: int) -> int:
    return int.from_bytes(data[off : off + 2], "little", signed=False)


def _u32(data: bytes, off: int) -> int:
    return int.from_bytes(data[off : off + 4], "little", signed=False)


def _i32(data: bytes, off: int) -> int:
    return int.from_bytes(data[off : off + 4], "little", signed=True)


def _is_printable_ascii(blob: bytes) -> bool:
    return all(PRINTABLE_ASCII_MIN <= b <= PRINTABLE_ASCII_MAX for b in blob)


def _extract_tagged_ascii_strings(
    data: bytes,
    tag: int,
    *,
    max_len: int = 120,
) -> list[dict]:
    hits: list[dict] = []
    end = len(data) - 5
    i = 0
    while i < end:
        if data[i] != tag:
            i += 1
            continue
        size = int.from_bytes(data[i + 1 : i + 5], "little", signed=False)
        if size <= 0 or size > max_len or i + 5 + size > len(data):
            i += 1
            continue
        raw = data[i + 5 : i + 5 + size]
        if not _is_printable_ascii(raw):
            i += 1
            continue
        try:
            text = raw.decode("ascii")
        except UnicodeDecodeError:
            i += 1
            continue
        hits.append({
            "offset": i,
            "text": text,
        })
        i += 5 + size
    return hits


def _decode_uid_record(data: bytes, uid_off: int, uid: str) -> dict | None:
    if uid_off >= 14:
        start = uid_off - 14
        if start + 32 <= len(data):
            if (
                data[start] == 0xFA
                and data[start + 4] == 0
                and data[start + 9] == 0
                and _u32(data, start + 10) == 8
            ):
                local_id = _u32(data, start + 5)
                if local_id <= 0x1000:
                    return {
                        "start": start,
                        "layout": "fa",
                        "code": _u16(data, start + 1),
                        "kind": data[start + 3],
                        "localId": local_id,
                        "uid": uid,
                        "nextId": _i32(data, start + 28),
                        "payloadStart": start + 32,
                        "strings": [],
                    }

    if uid_off >= 12:
        start = uid_off - 12
        if start + 30 <= len(data):
            code = _u16(data, start)
            kind = data[start + 2]
            local_id = _u32(data, start + 3)
            if (
                code <= 0x1FFF
                and kind <= 0x10
                and local_id <= 0x1000
                and data[start + 7] == 0
                and _u32(data, start + 8) == 8
            ):
                return {
                    "start": start,
                    "layout": "plain",
                    "code": code,
                    "kind": kind,
                    "localId": local_id,
                    "uid": uid,
                    "nextId": _i32(data, start + 26),
                    "payloadStart": start + 30,
                    "strings": [],
                }

    return None


def _extract_uid_records(data: bytes, string_hits: list[dict]) -> list[dict]:
    records: list[dict] = []
    seen_starts: set[int] = set()
    sorted_hits = sorted(string_hits, key=lambda hit: hit["offset"])

    for match in HEX_UID_RE.finditer(data):
        uid_off = match.start()
        uid = match.group().decode("ascii")
        record = _decode_uid_record(data, uid_off, uid)
        if record is None or record["start"] in seen_starts:
            continue
        seen_starts.add(record["start"])
        records.append(record)

    records.sort(key=lambda record: record["start"])
    if not records:
        return records

    hit_idx = 0
    for idx, record in enumerate(records):
        next_start = records[idx + 1]["start"] if idx + 1 < len(records) else len(data)
        while hit_idx < len(sorted_hits) and sorted_hits[hit_idx]["offset"] < record["payloadStart"]:
            hit_idx += 1
        scan_idx = hit_idx
        while scan_idx < len(sorted_hits) and sorted_hits[scan_idx]["offset"] < next_start:
            record["strings"].append(sorted_hits[scan_idx])
            scan_idx += 1

    return records


def _build_unique_record_target_map(records: list[dict]) -> dict[int, dict]:
    by_local_id: dict[int, list[dict]] = defaultdict(list)
    for record in records:
        by_local_id[record["localId"]].append(record)
    return {
        local_id: bucket[0]
        for local_id, bucket in by_local_id.items()
        if len(bucket) == 1
    }


def _build_uid_record_chains(records: list[dict]) -> list[list[dict]]:
    if not records:
        return []

    unique_targets = _build_unique_record_target_map(records)
    by_start = {record["start"]: record for record in records}
    target_starts = {
        target["start"]
        for record in records
        if (target := unique_targets.get(record["nextId"])) is not None
    }
    entry_starts = [record["start"] for record in records if record["start"] not in target_starts]
    chains: list[list[dict]] = []
    seen: set[int] = set()

    for entry_start in entry_starts:
        chain: list[dict] = []
        current = entry_start
        while current in by_start and current not in seen:
            record = by_start[current]
            chain.append(record)
            seen.add(record["start"])
            target = unique_targets.get(record["nextId"])
            if target is None:
                break
            current = target["start"]
        if chain:
            chains.append(chain)

    for record in records:
        if record["start"] not in seen:
            chains.append([record])
    return chains


def _extract_named_entry_tables(
    data: bytes,
    *,
    min_entries: int = 3,
    max_string_len: int = 120,
) -> list[list[dict]]:
    tables: list[list[dict]] = []
    limit = len(data) - 4
    for start in range(limit):
        count = int.from_bytes(data[start : start + 4], "little", signed=False)
        if count < min_entries or count > 64:
            continue
        pos = start + 4
        entries: list[dict] = []
        ok = True
        for _ in range(count):
            if pos + 8 > len(data):
                ok = False
                break
            key = int.from_bytes(data[pos : pos + 4], "little", signed=False)
            size = int.from_bytes(data[pos + 4 : pos + 8], "little", signed=False)
            pos += 8
            if size <= 0 or size > max_string_len or pos + size > len(data):
                ok = False
                break
            raw = data[pos : pos + size]
            pos += size
            if not _is_printable_ascii(raw):
                ok = False
                break
            entries.append({
                "key": key,
                "text": raw.decode("ascii"),
            })
        if ok:
            tables.append(entries)
    return tables


def _choose_best_named_entry_table(data: bytes) -> list[dict]:
    tables = _extract_named_entry_tables(data)
    if not tables:
        return []

    def score(entries: list[dict]) -> tuple[int, int]:
        lt_count = sum(1 for entry in entries if LT_BINDING_RE.match(entry["text"]))
        return (lt_count, len(entries))

    return max(tables, key=score)


def _load_leveldata_named_entries(path: Path) -> list[dict]:
    cache_key = str(path)
    if cache_key in _LEVELDATA_NAMED_TABLE_CACHE:
        return _LEVELDATA_NAMED_TABLE_CACHE[cache_key]

    try:
        data = path.read_bytes()
    except OSError:
        entries: list[dict] = []
    else:
        entries = _choose_best_named_entry_table(data)

    _LEVELDATA_NAMED_TABLE_CACHE[cache_key] = entries
    return entries


def _load_levelscript_binding_data(level_id: str) -> dict:
    if level_id in _LEVELSCRIPT_BINDING_CACHE:
        return _LEVELSCRIPT_BINDING_CACHE[level_id]

    out = {
        "uidPayloads": {},
        "files": [],
    }
    level_dir = LEVELSCRIPT_DIR / level_id
    if not level_dir.is_dir():
        _LEVELSCRIPT_BINDING_CACHE[level_id] = out
        return out

    def add_payload(uid: str, payload: str) -> None:
        bucket = out["uidPayloads"].setdefault(uid, [])
        if payload not in bucket:
            bucket.append(payload)

    for path in sorted(level_dir.glob("*.json"), key=_levelscript_file_sort_key):
        try:
            data = path.read_bytes()
        except OSError:
            continue

        string_hits = _extract_tagged_ascii_strings(data, 0x04)
        records = _extract_uid_records(data, string_hits)
        if not records and not string_hits:
            continue

        sorted_hits = sorted(string_hits, key=lambda hit: hit["offset"])
        for record in records:
            for hit in record["strings"]:
                add_payload(record["uid"], hit["text"])

        for match in HEX_UID_RE.finditer(data):
            uid_off = match.start()
            uid = match.group().decode("ascii")
            for hit in sorted_hits:
                if hit["offset"] <= uid_off:
                    continue
                if hit["offset"] - uid_off > 80:
                    break
                add_payload(uid, hit["text"])
                break

        out["files"].append({
            "file": path.relative_to(ROOT).as_posix(),
            "records": records,
        })

    _LEVELSCRIPT_BINDING_CACHE[level_id] = out
    return out


def _annotate_binding_payloads(
    payloads: list[str],
    dialog_key_resolver,
    mission_id: str = "",
) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for payload in payloads:
        if not payload or payload in seen:
            continue
        seen.add(payload)
        ref = {"text": payload}
        node_key = ""
        node_kind = ""
        scene_key = _resolve_payload_scene_key(payload, mission_id, dialog_key_resolver)
        if scene_key:
            node_key = scene_key
            node_kind = _scene_graph_node_kind(scene_key)
            ref["sceneKey"] = scene_key
        elif (node_key := _scene_graph_runtime_payload_key(payload, mission_id, dialog_key_resolver)):
            node_kind = _scene_graph_node_kind(node_key)
        if node_key:
            ref["nodeKey"] = node_key
        if node_kind:
            ref["kind"] = node_kind
        out.append(ref)
    return out


def _build_level_binding_groups(
    named_entries: list[dict],
    uid_payloads: dict[str, list[str]],
    dialog_key_resolver,
    mission_id: str = "",
) -> list[dict]:
    groups: list[dict] = []
    current: dict | None = None
    for entry in named_entries:
        match = LT_BINDING_RE.match(entry["text"])
        if match:
            if current is None:
                current = {"label": "Ungrouped", "rows": []}
                groups.append(current)
            payloads: list[str] = []
            for uid in (match.group("uid1"), match.group("uid2")):
                for payload in uid_payloads.get(uid, []):
                    if payload not in payloads:
                        payloads.append(payload)
            current["rows"].append({
                "key": entry["key"],
                "text": entry["text"],
                "kind": match.group("kind"),
                "payloads": _annotate_binding_payloads(payloads, dialog_key_resolver, mission_id),
                "_debug": {
                    "source": {
                        "key": entry["key"],
                        "text": entry["text"],
                        "uids": [match.group("uid1"), match.group("uid2")],
                    },
                },
            })
            continue
        if entry["text"].endswith("ID"):
            continue
        current = {"label": entry["text"], "rows": []}
        groups.append(current)
    return [group for group in groups if group["rows"]]


def _make_levelscript_chain_step(record: dict, dialog_key_resolver, mission_id: str = "") -> dict:
    payloads = _annotate_binding_payloads(
        [hit["text"] for hit in record["strings"]],
        dialog_key_resolver,
        mission_id,
    )
    return {
        "localId": record["localId"],
        "nextId": record["nextId"],
        "payloads": payloads,
        "_debug": {
            "source": {
                "layout": record["layout"],
                "code": f"0x{record['code']:04x}",
                "kind": f"0x{record['kind']:02x}",
                "uid": record["uid"],
                "start": record["start"],
            },
        },
    }


def _build_levelscript_scene_chain_map(
    level_id: str,
    dialog_key_resolver,
    mission_id: str = "",
) -> dict[str, list[dict]]:
    info = _load_levelscript_binding_data(level_id)
    scene_chains: dict[str, list[dict]] = defaultdict(list)
    seen_signatures: set[tuple] = set()

    for file_info in info["files"]:
        for chain in _build_uid_record_chains(file_info["records"]):
            if len(chain) < 2:
                continue
            steps = [_make_levelscript_chain_step(record, dialog_key_resolver, mission_id) for record in chain]
            scene_keys: list[str] = []
            seen_scene_keys: set[str] = set()
            for step in steps:
                for payload in step["payloads"]:
                    scene_key = payload.get("sceneKey")
                    if scene_key and scene_key not in seen_scene_keys:
                        seen_scene_keys.add(scene_key)
                        scene_keys.append(scene_key)
            if not scene_keys:
                continue

            signature = (
                file_info["file"],
                tuple(
                    (
                        step["localId"],
                        tuple(payload["text"] for payload in step["payloads"]),
                    )
                    for step in steps
                ),
            )
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)

            chain_entry = {
                "levelId": level_id,
                "file": file_info["file"],
                "steps": steps,
                "_debug": {
                    "source": {
                        "file": file_info["file"],
                        "levelId": level_id,
                    },
                },
            }
            for scene_key in scene_keys:
                scene_chains[scene_key].append(chain_entry)

    return scene_chains


def _scene_binding_search_text(binding_entry: dict) -> str:
    parts: list[str] = []
    for group in binding_entry.get("groups") or []:
        if group.get("label"):
            parts.append(group["label"])
        for row in group.get("rows") or []:
            if row.get("text"):
                parts.append(row["text"])
            for payload in row.get("payloads") or []:
                if payload.get("text"):
                    parts.append(payload["text"])
    for chain in binding_entry.get("chains") or []:
        if chain.get("levelId"):
            parts.append(chain["levelId"])
        for step in chain.get("steps") or []:
            for payload in step.get("payloads") or []:
                if payload.get("text"):
                    parts.append(payload["text"])
    return " ".join(part for part in parts if part)


def infer_mission_dialog_order(
    mission_id: str,
    mission_entries: list[dict],
    mission_flow: dict | None,
    mission_level_refs: list[dict] | None = None,
) -> dict[str, int]:
    entries_by_key = {
        entry["k"]: entry
        for entry in mission_entries
        if entry.get("d") in MISSION_SCENE_ENTRY_KINDS and entry.get("k")
    }
    if not entries_by_key:
        return {}
    dialog_entries_by_key = {
        key: entry
        for key, entry in entries_by_key.items()
        if entry.get("d") in ("dlg", "sns")
    }

    npc_proxy_ex = _load_npc_proxy_ex()
    proxy_rows = npc_proxy_ex.get("data") or {}
    proxy_info = npc_proxy_ex.get("proxyInfoData") or {}

    level_ids: list[str] = []
    if mission_flow:
        if mission_flow.get("level"):
            level_ids.append(mission_flow["level"])
        for quest in mission_flow.get("quests") or []:
            for scene_id in quest.get("scenes") or []:
                if scene_id and scene_id not in level_ids:
                    level_ids.append(scene_id)
    for ref in mission_level_refs or []:
        level_id = ref.get("levelId") or ""
        if level_id and level_id not in level_ids:
            level_ids.append(level_id)

    levelscript_hints = _load_mission_levelscript_dialogs(mission_id, level_ids)
    dialogs_by_level: dict[str, list[str]] = defaultdict(list)
    for hint in levelscript_hints:
        for dialog_id in hint.get("dialogs") or []:
            if dialog_id in dialog_entries_by_key and dialog_id not in dialogs_by_level[hint["levelId"]]:
                dialogs_by_level[hint["levelId"]].append(dialog_id)

    actor_sets = {
        key: set(entry.get("c") or [])
        for key, entry in dialog_entries_by_key.items()
    }
    kind_order = {"sns": 0, "cutscene": 1, "dlg": 2, "black": 3, "remotecomm": 4, "radio": 5, "env": 6, "misc": 7}

    ordered_keys: list[str] = []
    seen: set[str] = set()

    def push(dialog_id: str) -> None:
        if dialog_id in entries_by_key and dialog_id not in seen:
            seen.add(dialog_id)
            ordered_keys.append(dialog_id)

    def resolve_entry_scene_ref(raw_ref: str) -> str:
        candidates = _unique_preserve([
            str(raw_ref or "").strip(),
            *_scene_ref_alias_candidates(raw_ref),
        ])
        for candidate in candidates:
            if not candidate:
                continue
            if candidate in entries_by_key:
                return candidate
            canonical_cutscene = _canonical_cutscene_key(candidate) or ""
            if canonical_cutscene in entries_by_key:
                return canonical_cutscene
        return ""

    script_scene_ref_cache: dict[tuple[str, str], list[str]] = {}

    def levelscript_scene_refs_for_script(level_id: str, script_id) -> list[str]:
        if not level_id or script_id is None:
            return []
        script_stem = str(script_id)
        cache_key = (level_id, script_stem)
        if cache_key in script_scene_ref_cache:
            return script_scene_ref_cache[cache_key]
        hits: list[tuple[int, int, str]] = []
        for file_info in _load_levelscript_binding_data(level_id).get("files") or []:
            if Path(file_info.get("file") or "").stem != script_stem:
                continue
            for record in file_info.get("records") or []:
                record_start = int(record.get("start") or 0)
                for hit in record.get("strings") or []:
                    scene_ref = resolve_entry_scene_ref(hit.get("text") or "")
                    if not scene_ref:
                        continue
                    hits.append((record_start, int(hit.get("offset") or record_start), scene_ref))
        refs = _unique_preserve([scene_ref for _, __, scene_ref in sorted(hits)])
        script_scene_ref_cache[cache_key] = refs
        return refs

    def normalized_script_ids(values) -> list[str]:
        out: list[str] = []
        for value in values or []:
            script_id = value
            if isinstance(value, dict):
                script_id = value.get("scriptId") or value.get("value")
                if isinstance(script_id, dict):
                    script_id = script_id.get("scriptId")
            if script_id is None:
                continue
            script_id_text = str(script_id)
            if script_id_text and script_id_text not in out:
                out.append(script_id_text)
        return out

    def quest_condition_script_scene_refs(quest: dict) -> list[str]:
        refs: list[str] = []
        default_scene_ids = list(quest.get("scenes") or [])
        for anchor in quest.get("objectiveAnchors") or []:
            anchor_scene_ids = list(anchor.get("sceneIds") or default_scene_ids)
            script_ids = normalized_script_ids(anchor.get("scriptIds"))
            for script_id in script_ids:
                for scene_id in anchor_scene_ids:
                    for scene_ref in levelscript_scene_refs_for_script(scene_id, script_id):
                        if scene_ref not in refs:
                            refs.append(scene_ref)
            for leaf in anchor.get("conditionLeaves") or []:
                leaf_scene_ids = list(leaf.get("sceneIds") or anchor_scene_ids)
                for script_id in normalized_script_ids(leaf.get("scriptIds")):
                    for scene_id in leaf_scene_ids:
                        for scene_ref in levelscript_scene_refs_for_script(scene_id, script_id):
                            if scene_ref not in refs:
                                refs.append(scene_ref)
        return refs

    def has_unplaced_prior_levelscript_dialog(level_id: str, dialog_id: str) -> bool:
        dialogs = dialogs_by_level.get(level_id) or []
        if dialog_id not in dialogs:
            return False
        for prior_dialog_id in dialogs[:dialogs.index(dialog_id)]:
            if prior_dialog_id in entries_by_key and prior_dialog_id not in seen:
                return True
        return False

    def push_unplaced_levelscript_dialogs_before(scene_ids, stop_dialog_ids) -> None:
        stop_dialog_ids = set(stop_dialog_ids or [])
        for scene_id in scene_ids or []:
            for dialog_id in dialogs_by_level.get(scene_id) or []:
                if dialog_id in seen:
                    continue
                if dialog_id in stop_dialog_ids:
                    break
                push(dialog_id)
                break

    if mission_flow:
        visited_quest_levels: set[str] = set()
        for quest in mission_flow.get("quests") or []:
            explicit = [dialog_id for dialog_id in (quest.get("dialogs") or []) if dialog_id in entries_by_key]
            explicit_cutscenes = [cutscene_id for cutscene_id in (quest.get("cutscenes") or []) if cutscene_id in entries_by_key]
            explicit_remotecomms = [remote_id for remote_id in (quest.get("remotecomms") or []) if remote_id in entries_by_key]
            explicit_radios = [radio_id for radio_id in (quest.get("radios") or []) if radio_id in entries_by_key]
            for scene_ref in quest_condition_script_scene_refs(quest):
                push(scene_ref)
            if explicit or explicit_cutscenes or explicit_remotecomms:
                push_unplaced_levelscript_dialogs_before(quest.get("scenes") or [], explicit)
            for dialog_id in explicit:
                push(dialog_id)
            for cutscene_id in explicit_cutscenes:
                push(cutscene_id)
            for remote_id in explicit_remotecomms:
                push(remote_id)
            for radio_id in explicit_radios:
                push(radio_id)

            for proxy_id in quest.get("proxies") or []:
                for row in proxy_rows.get(proxy_id, []):
                    if not isinstance(row, dict):
                        continue
                    dialog_id = row.get("dialogId") or ""
                    row_mission = row.get("missionId") or ""
                    if dialog_id and (not row_mission or row_mission == mission_id):
                        push(dialog_id)

            if explicit or explicit_cutscenes or explicit_remotecomms:
                continue

            best_dialog = ""
            best_level = ""
            best_score = -1
            for proxy_id in quest.get("proxies") or []:
                actor_id = str((proxy_info.get(proxy_id) or {}).get("npcNameId") or "")
                for scene_id in quest.get("scenes") or []:
                    for dialog_id in dialogs_by_level.get(scene_id, []):
                        if dialog_id in seen:
                            continue
                        score = 2
                        if actor_id and actor_id in actor_sets.get(dialog_id, set()):
                            score += 4
                        if score > best_score:
                            best_score = score
                            best_dialog = dialog_id
                            best_level = scene_id
            if (
                best_dialog
                and best_score >= 5
                and not has_unplaced_prior_levelscript_dialog(best_level, best_dialog)
            ):
                push(best_dialog)

            for scene_id in quest.get("scenes") or []:
                if not scene_id or scene_id in visited_quest_levels:
                    continue
                visited_quest_levels.add(scene_id)
                dialogs = dialogs_by_level.get(scene_id) or []
                if dialogs and dialogs[0] not in seen:
                    push(dialogs[0])

    for level_id in level_ids:
        for dialog_id in dialogs_by_level.get(level_id, []):
            push(dialog_id)

    for entry in sorted(
        entries_by_key.values(),
        key=lambda e: (
            e.get("s", 10**9),
            kind_order.get(e.get("d"), 99),
            e.get("k") or "",
        ),
    ):
        push(entry["k"])

    return {dialog_id: order for order, dialog_id in enumerate(ordered_keys)}


def load_mission_flow(mission_id: str) -> dict | None:
    """Parse MissionRuntimeAsset/<mission>.json into a compact flow payload.

    Returns None when the asset is missing. Cached — the flow data is
    language-independent, so one parse serves every language bundle.
    """
    if mission_id in _MISSION_FLOW_CACHE:
        return _MISSION_FLOW_CACHE[mission_id]
    path = MRA_DIR / f"{mission_id}.json"
    if not path.exists():
        _MISSION_FLOW_CACHE[mission_id] = None
        return None
    try:
        with path.open(encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        _MISSION_FLOW_CACHE[mission_id] = None
        return None

    quests_out: list[dict] = []
    quest_entries_by_id: dict[str, dict] = {}
    for quest in (raw.get("questDic") or {}).values():
        qid = quest.get("questId")
        if not qid:
            continue
        entry: dict = {
            "id": qid,
            "flowIndex": quest.get("flowIndex", 0),
            "prev": list(quest.get("prevQuestIdList") or []),
        }
        quest_story_node = dict(quest)
        quest_story_node.pop("failedCondition", None)
        dialogs = _extract_dialog_refs(quest_story_node)
        if dialogs:
            entry["dialogs"] = dialogs
        cutscenes = [
            canonical
            for cutscene_id in _extract_cutscene_refs(quest_story_node)
            if (canonical := _canonical_cutscene_key(cutscene_id))
        ]
        if cutscenes:
            entry["cutscenes"] = _unique_preserve(cutscenes)
        remotecomms = _extract_remotecomm_refs(quest_story_node)
        if remotecomms:
            entry["remotecomms"] = _unique_preserve(remotecomms)
        radios = _extract_radio_refs(quest_story_node)
        if radios:
            entry["radios"] = _unique_preserve(radios)
        tracking = _extract_tracking_hints(quest)
        if tracking:
            resolved_tracking = [_resolve_tracking_hint(hint) for hint in tracking]
            entry["tracking"] = resolved_tracking
            scenes = _unique_preserve(
                [hint["scene"] for hint in resolved_tracking if hint.get("scene")]
            )
            proxies = _unique_preserve(
                [hint["npcProxyId"] for hint in resolved_tracking if hint.get("npcProxyId")]
            )
            if scenes:
                entry["scenes"] = scenes
            if proxies:
                entry["proxies"] = proxies
            pins: list[dict] = []
            seen_pins: set[tuple] = set()
            for hint in resolved_tracking:
                pin = _tracking_hint_pin(hint)
                if not pin:
                    continue
                key = (
                    pin.get("scene", ""),
                    pin.get("sourceType", ""),
                    pin.get("trackingType", ""),
                    pin.get("missionAreaId", ""),
                    pin.get("npcProxyId", ""),
                    round(float(pin["position"]["x"]), 3),
                    round(float(pin["position"]["y"]), 3),
                    round(float(pin["position"]["z"]), 3),
                )
                if key in seen_pins:
                    continue
                seen_pins.add(key)
                pins.append(pin)
            if pins:
                entry["pins"] = pins
        objective_anchors = _extract_objective_anchors(quest)
        if objective_anchors:
            entry["objectiveAnchors"] = objective_anchors
        fc = quest.get("failedCondition")
        if fc:
            flags = _extract_branch_flags(fc)
            eval_str = _combine_eval_string(fc)
            fail_story_refs: list[str] = []
            for field_name in (*_DIALOG_REF_FIELDS, *_CUTSCENE_REF_FIELDS, *_REMOTECOMM_REF_FIELDS, *_RADIO_REF_FIELDS):
                for value in _walk_field_values(fc, field_name):
                    if not isinstance(value, str) or not value:
                        continue
                    if field_name in _CUTSCENE_REF_FIELDS:
                        value = _canonical_cutscene_key(value) or value
                    if value not in fail_story_refs:
                        fail_story_refs.append(value)
            if fail_story_refs:
                entry["failStoryRefs"] = fail_story_refs
            if flags or eval_str or fail_story_refs:
                fail_entry: dict = {"flags": flags}
                if eval_str:
                    fail_entry["eval"] = eval_str
                if fail_story_refs:
                    fail_entry["storyRefs"] = fail_story_refs
                entry["fail"] = fail_entry
        quests_out.append(entry)
        quest_entries_by_id[qid] = entry

    radio_actions_by_quest = _extract_client_action_refs(raw, _RADIO_REF_FIELDS)
    for quest_id, radio_ids in radio_actions_by_quest.items():
        entry = quest_entries_by_id.get(quest_id)
        if not entry:
            continue
        entry["radios"] = _unique_preserve([
            *(entry.get("radios") or []),
            *radio_ids,
        ])

    quests_out = _topo_sort_quests(quests_out)

    payload = {
        "level": raw.get("levelId", ""),
        "quests": quests_out,
    }
    _MISSION_FLOW_CACHE[mission_id] = payload
    return payload


def _node_short_type(node: dict) -> str:
    t = node.get("$type", "")
    return t.split(",", 1)[0].rsplit(".", 1)[-1]


def _first_string_field(obj, field_name) -> str | None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == field_name and isinstance(v, str):
                return v
            found = _first_string_field(v, field_name)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for it in obj:
            found = _first_string_field(it, field_name)
            if found is not None:
                return found
    return None


def _all_string_fields(obj, field_name):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == field_name and isinstance(v, str):
                yield v
            else:
                yield from _all_string_fields(v, field_name)
    elif isinstance(obj, list):
        for it in obj:
            yield from _all_string_fields(it, field_name)


def _unique_preserve(seq):
    out = []
    seen = set()
    for item in seq:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _scene_graph_runtime_payload_key(
    payload_text: str,
    mission_id: str,
    dialog_key_resolver,
) -> str:
    if not payload_text:
        return ""
    if scene_key := _resolve_payload_scene_key(payload_text, mission_id, dialog_key_resolver):
        return scene_key
    if payload_text.startswith(f"remotecomm_{mission_id}_"):
        return payload_text
    if payload_text.startswith(f"radio_{mission_id}_"):
        return payload_text
    if payload_text.startswith(f"black_{mission_id}_"):
        return payload_text
    if payload_text.startswith(f"cutscene_{mission_id}_"):
        return payload_text
    if canonical_cutscene := _canonical_cutscene_key(payload_text):
        if f"_{mission_id}_" in f"_{canonical_cutscene}_":
            return canonical_cutscene
    if payload_text.startswith((f"dlg_{mission_id}_", f"sns_{mission_id}_", f"misc_dlg_{mission_id}_")):
        return payload_text
    if re.match(r"^[A-Za-z0-9]+_q#.+$", payload_text):
        return payload_text
    if payload_text.startswith("TpForLs_"):
        return payload_text
    if payload_text.startswith("cs_video_"):
        return payload_text
    if re.match(r"^#[0-9a-fA-F]{8}$", payload_text):
        return payload_text
    if re.match(r"^(?:map|dung|indie|main)[0-9A-Za-z_]*$", payload_text):
        return payload_text
    if (
        payload_text.endswith("_default")
        or "_map" in payload_text
        or "_dung" in payload_text
        or "_indie" in payload_text
        or "_main" in payload_text
    ):
        return payload_text
    return payload_text


def _scene_graph_node_kind(node_key: str, available_keys: set[str] | None = None) -> str:
    available_keys = available_keys or set()
    if node_key.startswith("ui:"):
        return "ui"
    if node_key.startswith("remotecomm_"):
        return "remotecomm"
    if node_key.startswith("radio_"):
        return "radio"
    if node_key.startswith("black_"):
        return "black"
    if node_key.startswith("cutscene_") or _canonical_cutscene_key(node_key):
        return "cutscene"
    if node_key.startswith("sns_"):
        return "sns"
    if node_key.startswith("misc_"):
        return "misc"
    if node_key.startswith("dlg_"):
        return "dlg" if node_key in available_keys else "runtimeDialog"
    if re.match(r"^[A-Za-z0-9]+_q#.+$", node_key):
        return "levelscriptQuest"
    if node_key.startswith("TpForLs_"):
        return "levelscriptTeleport"
    if node_key.startswith("cs_video_"):
        return "levelscriptVideo"
    if re.match(r"^#[0-9a-fA-F]{8}$", node_key):
        return "levelscriptHash"
    if re.match(r"^(?:map|dung|indie|main)[0-9A-Za-z_]*$", node_key):
        return "levelscriptLevel"
    if (
        node_key.endswith("_default")
        or "_map" in node_key
        or "_dung" in node_key
        or "_indie" in node_key
        or "_main" in node_key
    ):
        return "levelscriptProxy"
    if node_key:
        return "levelscriptSymbol"
    return "runtime"


def _is_story_scene_graph_kind(kind: str) -> bool:
    return kind in MISSION_SCENE_ENTRY_KINDS


def _is_story_scene_graph_key(node_key: str, available_keys: set[str] | None = None) -> bool:
    return _is_story_scene_graph_kind(_scene_graph_node_kind(node_key, available_keys))


def _compact_scene_graph_sequence(
    sequence: list[str],
    available_keys: set[str] | None = None,
) -> list[str]:
    out: list[str] = []
    for node_key in sequence:
        if not _is_story_scene_graph_key(node_key, available_keys):
            continue
        if not out or out[-1] != node_key:
            out.append(node_key)
    return out


def _refine_scene_graph_order(
    node_keys: set[str],
    edges: list[dict],
    base_order_map: dict[str, int],
    available_keys: set[str] | None = None,
) -> dict[str, int]:
    available_keys = available_keys or set()
    succs: dict[str, list[str]] = defaultdict(list)
    edge_specs: list[tuple[str, str, str]] = []
    for edge in edges:
        src = edge.get("from") or ""
        dst = edge.get("to") or ""
        kind = edge.get("kind") or ""
        if not src or not dst or src == dst:
            continue
        if src not in node_keys or dst not in node_keys:
            continue
        succs[src].append(dst)
        edge_specs.append((src, dst, kind))
    for key in node_keys:
        succs.setdefault(key, [])

    tight_edge_kinds = {
        "questSequence",
        "questFailGuard",
        "authoredDirect",
        "authoredMenu",
        "levelscriptSceneChain",
    }
    order_hints: dict[str, float] = {
        key: float(order)
        for key, order in base_order_map.items()
        if key in node_keys
    }
    for _ in range(max(1, len(node_keys))):
        changed = False
        for src, dst, kind in edge_specs:
            is_tight = kind in tight_edge_kinds
            if src in order_hints and (is_tight or dst not in base_order_map):
                candidate = order_hints[src] + 0.25
                current = order_hints.get(dst)
                if current is None or candidate < current:
                    order_hints[dst] = candidate
                    changed = True
            if dst in order_hints and (is_tight or src not in base_order_map):
                candidate = order_hints[dst] - 0.25
                current = order_hints.get(src)
                if current is None or candidate < current:
                    order_hints[src] = candidate
                    changed = True
        if not changed:
            break

    def base_sort_key(key: str) -> tuple:
        return (
            order_hints.get(key, 10**9),
            _scene_graph_node_kind(key, available_keys),
            key,
        )

    index_counter = 0
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[list[str]] = []

    def strongconnect(node_key: str) -> None:
        nonlocal index_counter
        indices[node_key] = index_counter
        lowlinks[node_key] = index_counter
        index_counter += 1
        stack.append(node_key)
        on_stack.add(node_key)

        for next_key in succs.get(node_key, []):
            if next_key not in indices:
                strongconnect(next_key)
                lowlinks[node_key] = min(lowlinks[node_key], lowlinks[next_key])
            elif next_key in on_stack:
                lowlinks[node_key] = min(lowlinks[node_key], indices[next_key])

        if lowlinks[node_key] != indices[node_key]:
            return

        component: list[str] = []
        while stack:
            cur = stack.pop()
            on_stack.remove(cur)
            component.append(cur)
            if cur == node_key:
                break
        component.sort(key=base_sort_key)
        components.append(component)

    for key in sorted(node_keys, key=base_sort_key):
        if key not in indices:
            strongconnect(key)

    component_index_by_key: dict[str, int] = {}
    for idx, component in enumerate(components):
        for key in component:
            component_index_by_key[key] = idx

    comp_succs: dict[int, set[int]] = defaultdict(set)
    indegree: dict[int, int] = {idx: 0 for idx in range(len(components))}
    for src, dsts in succs.items():
        src_idx = component_index_by_key[src]
        for dst in dsts:
            dst_idx = component_index_by_key[dst]
            if src_idx == dst_idx or dst_idx in comp_succs[src_idx]:
                continue
            comp_succs[src_idx].add(dst_idx)
            indegree[dst_idx] += 1

    ready = sorted(
        (idx for idx, degree in indegree.items() if degree == 0),
        key=lambda idx: tuple(base_sort_key(key) for key in components[idx]),
    )
    ordered: list[str] = []
    while ready:
        comp_idx = ready.pop(0)
        ordered.extend(components[comp_idx])
        for next_idx in sorted(comp_succs.get(comp_idx, set())):
            indegree[next_idx] -= 1
            if indegree[next_idx] == 0:
                ready.append(next_idx)
        ready.sort(key=lambda idx: tuple(base_sort_key(key) for key in components[idx]))

    if len(ordered) < len(node_keys):
        emitted = set(ordered)
        for component in sorted(components, key=lambda comp: tuple(base_sort_key(key) for key in comp)):
            for key in component:
                if key not in emitted:
                    emitted.add(key)
                    ordered.append(key)

    return {
        key: order
        for order, key in enumerate(ordered)
    }


def _detect_scene_graph_entries(
    nodes: list[dict],
    edges: list[dict],
    quest_scene_meta: dict[str, dict],
    chain_start_meta: dict[str, dict],
    order_map: dict[str, int],
    graph_order_map: dict[str, int],
    available_keys: set[str] | None = None,
) -> dict | None:
    available_keys = available_keys or set()
    scene_nodes = [
        node for node in nodes
        if _is_story_scene_graph_kind(str(node.get("kind") or ""))
    ]
    if not scene_nodes:
        return None

    entry_edge_kinds = {
        "questSequence",
        "questPrev",
        "questFailGuard",
        "authoredDirect",
        "authoredMenu",
        "levelscriptSceneChain",
    }
    incoming_kinds: dict[str, set[str]] = defaultdict(set)
    outgoing_kinds: dict[str, set[str]] = defaultdict(set)
    incoming_count: Counter = Counter()
    outgoing_count: Counter = Counter()
    for edge in edges:
        src = edge.get("from") or ""
        dst = edge.get("to") or ""
        kind = edge.get("kind") or ""
        if kind not in entry_edge_kinds:
            continue
        if not _is_story_scene_graph_key(src, available_keys):
            continue
        if not _is_story_scene_graph_key(dst, available_keys):
            continue
        incoming_count[dst] += 1
        outgoing_count[src] += 1
        incoming_kinds[dst].add(kind)
        outgoing_kinds[src].add(kind)

    scene_node_keys = [
        str(node.get("key") or "")
        for node in scene_nodes
        if str(node.get("key") or "")
    ]
    connected_scene_keys = [
        key
        for key in scene_node_keys
        if incoming_count.get(key, 0) or outgoing_count.get(key, 0)
    ]
    graph_order_first_key = (
        min(
            connected_scene_keys,
            key=lambda key: (
                graph_order_map.get(key, 10**9),
                order_map.get(key, 10**9),
                key,
            ),
        )
        if connected_scene_keys
        else ""
    )

    candidates: list[dict] = []
    for node in scene_nodes:
        key = str(node.get("key") or "")
        if not key:
            continue
        quest_meta = quest_scene_meta.get(key) or {}
        chain_meta = chain_start_meta.get(key) or {}
        root_quest_ids = list(quest_meta.get("rootQuestIds") or [])
        quest_ids = list(quest_meta.get("questIds") or [])
        flow_indices = sorted({
            int(idx)
            for idx in (quest_meta.get("flowIndices") or [])
            if isinstance(idx, int | float) or (isinstance(idx, str) and idx.isdigit())
        })
        chain_files = list(chain_meta.get("sourceFiles") or [])
        chain_levels = list(chain_meta.get("levelIds") or [])
        chain_positions = sorted({
            int(pos)
            for pos in (chain_meta.get("positions") or [])
            if isinstance(pos, int | float) or (isinstance(pos, str) and str(pos).isdigit())
        })
        zero_incoming = incoming_count.get(key, 0) == 0
        reasons: list[str] = []
        if root_quest_ids:
            reasons.append("rootQuest")
        if quest_ids and not reasons:
            reasons.append("questStart")
        if key == graph_order_first_key:
            reasons.append("graphOrderFirst")
        if chain_files:
            reasons.append("levelscriptStart")
        if zero_incoming:
            reasons.append("zeroIncoming")
        if not reasons:
            continue

        if root_quest_ids:
            confidence = "high"
        elif quest_ids or (chain_files and zero_incoming):
            confidence = "medium"
        elif key == graph_order_first_key and (
            incoming_kinds.get(key) or outgoing_kinds.get(key)
        ):
            confidence = "medium"
        else:
            confidence = "low"

        candidates.append({
            "key": key,
            "kind": node.get("kind") or _scene_graph_node_kind(key, available_keys),
            "confidence": confidence,
            "reasons": reasons,
            "rootQuestIds": root_quest_ids,
            "questIds": quest_ids,
            "flowIndices": flow_indices,
            "sourceFiles": chain_files,
            "levelIds": chain_levels,
            "incomingKinds": sorted(incoming_kinds.get(key, set())),
            "outgoingKinds": sorted(outgoing_kinds.get(key, set())),
            "zeroIncoming": zero_incoming,
            "_rank": (
                0 if root_quest_ids else 1,
                flow_indices[0] if flow_indices else 10**9,
                0 if quest_ids else 1,
                0 if key == graph_order_first_key else 1,
                0 if zero_incoming else 1,
                0 if chain_files else 1,
                chain_positions[0] if chain_positions else 10**9,
                graph_order_map.get(key, 10**9),
                order_map.get(key, 10**9),
                key,
            ),
        })

    if not candidates:
        fallback = min(
            scene_nodes,
            key=lambda node: (
                graph_order_map.get(str(node.get("key") or ""), 10**9),
                order_map.get(str(node.get("key") or ""), 10**9),
                str(node.get("key") or ""),
            ),
        )
        fallback_key = str(fallback.get("key") or "")
        if not fallback_key:
            return None
        return {
            "primaryEntryKey": fallback_key,
            "entryNodes": [{
                "key": fallback_key,
                "kind": fallback.get("kind") or _scene_graph_node_kind(fallback_key, available_keys),
                "confidence": "low",
                "reasons": ["graphOrderFallback"],
                "incomingKinds": sorted(incoming_kinds.get(fallback_key, set())),
                "outgoingKinds": sorted(outgoing_kinds.get(fallback_key, set())),
                "zeroIncoming": incoming_count.get(fallback_key, 0) == 0,
            }],
        }

    candidates.sort(key=lambda item: item["_rank"])
    entry_nodes = []
    for rank, item in enumerate(candidates):
        payload = {k: v for k, v in item.items() if not k.startswith("_")}
        payload["rank"] = rank
        entry_nodes.append(payload)
    return {
        "primaryEntryKey": entry_nodes[0]["key"],
        "entryNodes": entry_nodes,
    }


def _dialog_tree_scene_prefix(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    match = re.search(r"_(\d+)$", value)
    if not match:
        return None
    prefix = value[:match.start()]
    if prefix.startswith(("dlg_", "env_", "misc_", "sns_")):
        return prefix
    return None


def _dialog_tree_option_prefix(option_id: str) -> str | None:
    if not isinstance(option_id, str) or not option_id.startswith("option_"):
        return None
    stem = option_id[len("option_") :]
    match = re.match(rf"(.+)_({SCENE_TOK})_(\d+)$", stem)
    if not match:
        return None
    prefix = match.group(1)
    if prefix.startswith(("dlg_", "env_", "misc_", "sns_")):
        return prefix
    return None


def _dialog_tree_node_position(node: dict, fallback_index: int = 0) -> tuple[float, float, int]:
    pos = node.get("_position") or {}
    try:
        x = float(pos.get("x", 0.0))
    except (TypeError, ValueError):
        x = 0.0
    try:
        y = float(pos.get("y", 0.0))
    except (TypeError, ValueError):
        y = 0.0
    return (x, y, fallback_index)


def _dialog_tree_node_line_id(node: dict) -> str:
    return _first_string_field(node, "_trunkId") or ""


def _dialog_tree_node_option_ids(node: dict) -> list[str]:
    option_ids: list[str] = []
    for entry in node.get("_normalOptions") or []:
        if not isinstance(entry, dict):
            continue
        option_id = str(entry.get("_optionId") or "").strip()
        if option_id and option_id not in option_ids:
            option_ids.append(option_id)
    return option_ids


def _dialog_tree_connection_refs(conn: dict) -> tuple[str, str]:
    if not isinstance(conn, dict):
        return ("", "")
    src = (conn.get("_sourceNode") or {}).get("$ref")
    dst = (conn.get("_targetNode") or {}).get("$ref")
    return (str(src or ""), str(dst or ""))


def _normalize_dialog_tree_line_graph(nodes: list[dict], conns: list[dict]) -> dict:
    graph_nodes: list[dict] = []
    by_id: dict[str, dict] = {}
    for idx, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("$id") or "").strip()
        if not node_id:
            continue
        x, y, _ = _dialog_tree_node_position(node, idx)
        record = {
            "id": node_id,
            "type": _node_short_type(node),
            "x": round(x, 4),
            "y": round(y, 4),
        }
        if line_id := _dialog_tree_node_line_id(node):
            record["lineId"] = line_id
        if option_ids := _dialog_tree_node_option_ids(node):
            record["optionIds"] = option_ids
        graph_nodes.append(record)
        by_id[node_id] = record

    graph_edges: list[dict] = []
    edge_by_pair: dict[tuple[str, str], dict] = {}
    for conn in conns:
        src, dst = _dialog_tree_connection_refs(conn)
        if not src or not dst or src not in by_id or dst not in by_id:
            continue
        key = (src, dst)
        edge = edge_by_pair.get(key)
        if edge is None:
            edge = {
                "from": src,
                "to": dst,
            }
            if from_line := by_id[src].get("lineId"):
                edge["fromLineId"] = from_line
            if to_line := by_id[dst].get("lineId"):
                edge["toLineId"] = to_line
            edge_by_pair[key] = edge
            graph_edges.append(edge)
        else:
            edge["count"] = int(edge.get("count") or 1) + 1

    return {
        "nodes": graph_nodes,
        "edges": graph_edges,
    }


def _ordered_dialog_tree_trunk_ids(nodes: list[dict], conns: list[dict]) -> tuple[list[str], dict]:
    by_id: dict[str, dict] = {}
    node_index: dict[str, int] = {}
    for idx, node in enumerate(nodes):
        node_id = node.get("$id")
        if node_id:
            by_id[node_id] = node
            node_index[node_id] = idx

    preds: dict[str, list[str]] = defaultdict(list)
    succs: dict[str, list[str]] = defaultdict(list)
    for conn in conns:
        src, dst = _dialog_tree_connection_refs(conn)
        if src in by_id and dst in by_id:
            if src not in preds[dst]:
                preds[dst].append(src)
            if dst not in succs[src]:
                succs[src].append(dst)

    def node_sort_key(node_id: str) -> tuple[float, float, int]:
        return _dialog_tree_node_position(by_id[node_id], node_index.get(node_id, 0))

    # Treat visual return edges as loop backs only when the graph also proves
    # they close a cycle. This keeps legitimate authored leftward edges, such
    # as long scenes wrapping to a lower canvas row, in the forward flow.
    back_edge_x_tolerance = 80.0
    row_wrap_y_tolerance = 120.0
    cycle_cache: dict[tuple[str, str], bool] = {}

    def edge_closes_cycle(src: str, dst: str) -> bool:
        cache_key = (src, dst)
        if cache_key in cycle_cache:
            return cycle_cache[cache_key]
        if src == dst:
            cycle_cache[cache_key] = True
            return True
        seen: set[str] = set()
        stack: list[str] = [dst]
        while stack:
            cur = stack.pop()
            if cur == src:
                cycle_cache[cache_key] = True
                return True
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(nxt for nxt in succs.get(cur, []) if nxt not in seen)
        cycle_cache[cache_key] = False
        return False

    def edge_is_visual_return(src: str, dst: str) -> bool:
        src_x, src_y, _ = node_sort_key(src)
        dst_x, dst_y, _ = node_sort_key(dst)
        if dst_y >= src_y + row_wrap_y_tolerance:
            return False
        return src_x > dst_x + back_edge_x_tolerance or dst_y < src_y - row_wrap_y_tolerance

    def is_forward_pred(pred: str, node_id: str) -> bool:
        if not edge_closes_cycle(pred, node_id):
            return True
        return not edge_is_visual_return(pred, node_id)

    def upstream_preds(node_id: str) -> list[str]:
        return [
            pred
            for pred in preds.get(node_id, [])
            if pred in by_id and is_forward_pred(pred, node_id)
        ]

    effective_preds = {node_id: upstream_preds(node_id) for node_id in by_id}
    roots = sorted(
        (node_id for node_id in by_id if not effective_preds.get(node_id)),
        key=node_sort_key,
    )

    ordered_line_ids: list[str] = []
    seen_line_ids: set[str] = set()
    visited: set[str] = set()
    # Use a stack, seeded in reverse, so authored connection order is preserved
    # at option splits and each branch is traversed as a readable block. Join
    # prerequisites above still prevent a merge from being visited before all
    # upstream branches have arrived.
    ready: list[str] = list(reversed(roots))
    queued: set[str] = set(roots)
    appended_node_ids: list[str] = []

    def visit(node_id: str) -> None:
        if node_id in visited:
            return
        visited.add(node_id)
        trunk_id = _dialog_tree_node_line_id(by_id[node_id])
        if trunk_id and trunk_id not in seen_line_ids:
            seen_line_ids.add(trunk_id)
            ordered_line_ids.append(trunk_id)
        next_nodes = [
            nxt
            for nxt in succs.get(node_id, [])
            if nxt not in visited and nxt not in queued
        ]
        for nxt in reversed(next_nodes):
            if nxt in visited or nxt in queued:
                continue
            if all(pred in visited for pred in effective_preds.get(nxt, [])):
                ready.append(nxt)
                queued.add(nxt)

    def drain_ready() -> None:
        while ready:
            node_id = ready.pop()
            queued.discard(node_id)
            if node_id in visited:
                continue
            if not all(pred in visited for pred in effective_preds.get(node_id, [])):
                continue
            visit(node_id)

    drain_ready()
    while len(visited) < len(by_id):
        remaining = sorted(
            (node_id for node_id in by_id if node_id not in visited),
            key=node_sort_key,
        )
        if not remaining:
            break
        node_id = remaining[0]
        appended_node_ids.append(node_id)
        queued.discard(node_id)
        visit(node_id)
        drain_ready()

    # Some trees include trunk-bearing nodes without a `$id`. They cannot
    # participate in graph traversal (connections can't reference them), but
    # their trunk IDs are still authored lines. Append by canvas position so
    # they land in the most plausible order.
    orphan_entries: list[tuple[tuple[float, float, int], str]] = []
    for idx, node in enumerate(nodes):
        if node.get("$id"):
            continue
        trunk_id = _dialog_tree_node_line_id(node)
        if not trunk_id or trunk_id in seen_line_ids:
            continue
        orphan_entries.append((_dialog_tree_node_position(node, idx), trunk_id))
    orphan_entries.sort(key=lambda item: item[0])
    orphan_trunk_ids: list[str] = []
    for _key, trunk_id in orphan_entries:
        if trunk_id in seen_line_ids:
            continue
        seen_line_ids.add(trunk_id)
        ordered_line_ids.append(trunk_id)
        orphan_trunk_ids.append(trunk_id)

    debug: dict = {
        "rootNodeIds": roots,
        "appendedNodeIds": appended_node_ids,
        "nodeCount": len(by_id),
    }
    deferred_back_edge_count = sum(
        1
        for node_id in by_id
        for pred in preds.get(node_id, [])
        if pred in by_id and pred not in effective_preds.get(node_id, [])
    )
    if deferred_back_edge_count:
        debug["deferredBackEdgeCount"] = deferred_back_edge_count
    if orphan_trunk_ids:
        debug["orphanTrunkIds"] = orphan_trunk_ids
    return ordered_line_ids, debug


def _load_dialog_tree_extra_config(tree_key: str) -> dict | None:
    if tree_key in _DIALOG_TREE_EXTRA_CONFIG_CACHE:
        return _DIALOG_TREE_EXTRA_CONFIG_CACHE[tree_key]
    prefix = f"{tree_key}_"

    result = None
    for base in ANIME_RESOURCE_DIRS:
        path = base / f"{tree_key}_extra_config.json"
        if not path.exists():
            continue
        payload = _load_anime_resource_payload(path)
        if payload is None:
            continue

        configured_line_ids = payload.get("lineIds") if isinstance(payload, dict) else None
        if isinstance(configured_line_ids, list):
            line_ids = [
                line_id
                for line_id in configured_line_ids
                if isinstance(line_id, str) and line_id.startswith(prefix)
            ]
        elif isinstance(payload, dict):
            line_ids = [
                key
                for key in payload.keys()
                if isinstance(key, str) and key.startswith(prefix)
            ]
        else:
            line_ids = []

        if not line_ids:
            continue
        result = {
            "sourceKey": tree_key,
            "file": path.relative_to(ROOT).as_posix(),
            "lineIds": line_ids,
        }
    _DIALOG_TREE_EXTRA_CONFIG_CACHE[tree_key] = result
    return result


def _line_order_stems(line_id: str) -> list[str]:
    value = str(line_id or "").strip()
    if not value:
        return []
    stems: list[str] = []
    if re.search(r"_\d+$", value):
        stems.append(re.sub(r"_\d+$", "", value))
    if not value.startswith("dlg_") and re.search(r"_\d+_\d+$", value):
        stem = re.sub(r"_\d+_\d+$", "", value)
        if stem not in stems:
            stems.append(stem)
    return stems


def _option_id_scene_key(option_id: str) -> str:
    value = str(option_id or "").strip()
    if not value.startswith("option_dlg_"):
        return ""
    parts = value.rsplit("_", 2)
    if len(parts) != 3:
        return ""
    return parts[0][len("option_"):]


def _option_id_group_parts(option_id: str) -> tuple[str, int, int] | None:
    value = str(option_id or "").strip()
    match = OPTION_RE.match(value)
    if not match:
        return None
    return (f"dlg_{match.group(1)}_{match.group(2)}", int(match.group(3)), int(match.group(4)))


def _option_text_signature(text: str) -> str:
    return re.sub(r"\s+", "", str(text or "").strip())


def _timeline_stem_to_dialog_key(timeline: str) -> str:
    value = str(timeline or "")
    for prefix in ("f_dlgtl_", "m_dlgtl_", "dlgtl_"):
        if value.startswith(prefix):
            value = value[len(prefix):]
            break
    value = re.sub(r"_sub_\d+$", "", value)
    return f"dlg_{value}" if value else ""


def _normalize_line_order_ids(values) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        line_id = str(value or "").strip()
        if not line_id or line_id in seen:
            continue
        seen.add(line_id)
        out.append(line_id)
    return out


def _normalize_dialog_timeline_option_anchors(value) -> dict[str, dict]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, dict] = {}
    for raw_option_id, raw_anchor in value.items():
        option_id = str(raw_option_id or "").strip()
        if not _option_id_scene_key(option_id):
            continue
        if isinstance(raw_anchor, dict):
            after = str(raw_anchor.get("after") or "").strip()
            position = str(raw_anchor.get("position") or "").strip()
            mode = str(raw_anchor.get("mode") or "").strip()
            source = str(raw_anchor.get("sourceFile") or "").strip()
            track = str(raw_anchor.get("track") or "").strip().replace("\\", "/")
        else:
            after = str(raw_anchor or "").strip()
            position = ""
            mode = "timeline"
            source = ""
            track = ""
        anchor = {
            "mode": mode or ("timelinePreviousLine" if after else "timelinePre"),
        }
        if after:
            anchor["after"] = after
        elif position == "pre":
            anchor["position"] = "pre"
        else:
            continue
        if source:
            anchor["sourceFile"] = source
        if track:
            anchor["track"] = track
        out[option_id] = anchor
    return out


def _normalize_dialog_timeline_file(entry: dict) -> str:
    for key in ("source", "file"):
        value = str(entry.get(key) or "").strip()
        if value:
            return value.replace("\\", "/")
    roots = entry.get("sourceRoots")
    if isinstance(roots, list) and roots:
        return str(roots[0] or "").replace("\\", "/")
    return ""


def _iter_dialog_timeline_payload_entries(raw_key: str, payload):
    if not isinstance(payload, dict):
        return
    variants = payload.get("variants")
    if isinstance(variants, list) and variants:
        for variant in variants:
            if isinstance(variant, dict):
                yield variant
        return
    yield payload


def _add_dialog_timeline_alias(aliases: set[str], key: str) -> None:
    key = str(key or "").strip()
    if not key or key.startswith("_"):
        return
    aliases.add(key)
    if key.startswith("misc_"):
        aliases.add(key[len("misc_"):])


def _dialog_timeline_aliases(raw_key: str, entry: dict, line_ids: list[str], option_ids: list[str]) -> set[str]:
    aliases: set[str] = set()
    _add_dialog_timeline_alias(aliases, raw_key)
    _add_dialog_timeline_alias(aliases, str(entry.get("dialogKey") or ""))
    timeline = str(entry.get("timeline") or raw_key or "")
    if timeline:
        _add_dialog_timeline_alias(aliases, _timeline_stem_to_dialog_key(timeline))
    for line_id in line_ids:
        for stem in _line_order_stems(line_id):
            _add_dialog_timeline_alias(aliases, stem)
    for option_id in option_ids:
        _add_dialog_timeline_alias(aliases, _option_id_scene_key(option_id))
    return aliases


def _normalize_dialog_timeline_lines(value, line_ids: list[str]) -> list[dict]:
    if not isinstance(value, list):
        return []
    valid = set(line_ids)
    out: list[dict] = []
    seen: set[str] = set()
    for raw in value:
        if not isinstance(raw, dict):
            continue
        line_id = str(raw.get("id") or "").strip()
        if not line_id or line_id not in valid or line_id in seen:
            continue
        seen.add(line_id)
        try:
            start = float(raw.get("start", 0.0))
        except (TypeError, ValueError):
            start = 0.0
        try:
            duration = float(raw.get("duration", 0.0))
        except (TypeError, ValueError):
            duration = 0.0
        record = {
            "id": line_id,
            "start": round(start, 3),
            "duration": round(duration, 3),
        }
        actor = str(raw.get("actor") or "").strip()
        if actor:
            record["actor"] = actor
        out.append(record)
    out.sort(key=lambda item: (item["start"], item["id"]))
    return out


def _normalize_dialog_timeline_option_positions(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    out: list[dict] = []
    for raw in value:
        if not isinstance(raw, dict):
            continue
        try:
            start = round(float(raw.get("start", 0.0)), 3)
        except (TypeError, ValueError):
            continue
        try:
            duration = round(float(raw.get("duration", 0.0)), 3)
        except (TypeError, ValueError):
            duration = 0.0
        scenes = [str(s).strip() for s in (raw.get("scenes") or []) if str(s).strip()]
        option_ids = [str(s).strip() for s in (raw.get("optionIds") or []) if str(s).strip()]
        out.append({
            "start": start,
            "duration": duration,
            "scenes": scenes,
            "optionIds": option_ids,
        })
    out.sort(key=lambda item: item["start"])
    return out


def _normalize_dialog_timeline_option_rows(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    out: list[dict] = []
    for raw in value:
        if not isinstance(raw, dict):
            continue
        option_id = str(raw.get("id") or "").strip()
        if not option_id:
            continue
        record: dict = {"id": option_id}
        for field in (
            "groupKey",
            "anchorMode",
            "anchorLineId",
            "track",
            "trackName",
            "assetName",
            "assetTrack",
        ):
            value_for_field = str(raw.get(field) or "").strip()
            if value_for_field:
                record[field] = value_for_field
        for field in ("index", "optionIndex", "clipOptionIndex", "assetPathId"):
            value_for_field = raw.get(field)
            if isinstance(value_for_field, int):
                record[field] = value_for_field
        for field in ("start", "duration"):
            value_for_field = raw.get(field)
            if isinstance(value_for_field, (int, float)):
                record[field] = round(float(value_for_field), 3)
        out.append(record)
    out.sort(key=lambda item: (
        item.get("start", 0.0),
        item.get("optionIndex") if item.get("optionIndex") is not None else 10**9,
        item.get("id") or "",
        item.get("anchorMode") or "",
    ))
    return out


def _index_dialog_timeline_entry(index: dict[str, list[dict]], raw_key: str, entry: dict) -> None:
    line_ids = _normalize_line_order_ids(entry.get("lineIds"))
    option_ids = _normalize_line_order_ids(entry.get("optionIds"))
    option_anchors = _normalize_dialog_timeline_option_anchors(entry.get("optionAnchors"))
    for option_id in option_anchors:
        if option_id not in option_ids:
            option_ids.append(option_id)
    if not line_ids and not option_ids:
        return
    timeline = str(entry.get("timeline") or raw_key or "")
    source_file = _normalize_dialog_timeline_file(entry)
    line_timings = _normalize_dialog_timeline_lines(entry.get("lines"), line_ids)
    timed_line_ids = [str(item.get("id") or "") for item in line_timings if item.get("id")]
    ordered_line_ids = [
        *timed_line_ids,
        *(line_id for line_id in line_ids if line_id not in timed_line_ids),
    ] if timed_line_ids else line_ids
    option_positions = _normalize_dialog_timeline_option_positions(entry.get("optionPositions"))
    option_rows = _normalize_dialog_timeline_option_rows(entry.get("options"))
    normalized = {
        "sourceKey": timeline or raw_key,
        "timeline": timeline,
        "file": source_file,
        "lineIds": ordered_line_ids,
        "optionIds": option_ids,
        "optionAnchors": option_anchors,
        "lineTimings": line_timings,
        "optionPositions": option_positions,
        "optionRows": option_rows,
    }
    identity = (
        normalized["sourceKey"],
        normalized["file"],
        tuple(ordered_line_ids),
        tuple(option_ids),
        json.dumps(option_anchors, sort_keys=True, ensure_ascii=False),
        json.dumps(option_rows, sort_keys=True, ensure_ascii=False),
    )
    for alias in _dialog_timeline_aliases(raw_key, entry, ordered_line_ids, option_ids):
        bucket = index.setdefault(alias, [])
        if any(item.get("_identity") == identity for item in bucket):
            continue
        bucket.append({**normalized, "_identity": identity})


def _load_dialog_timeline_line_order_index() -> dict[str, list[dict]]:
    global _DIALOG_TIMELINE_LINE_ORDER_CACHE
    if _DIALOG_TIMELINE_LINE_ORDER_CACHE is not None:
        return _DIALOG_TIMELINE_LINE_ORDER_CACHE

    index: dict[str, list[dict]] = defaultdict(list)
    for path in TIMELINE_LINE_ORDER_PATHS:
        if not path.exists():
            continue
        try:
            with path.open(encoding="utf-8-sig") as f:
                payload = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue

        if isinstance(payload.get("lineIds"), list):
            _index_dialog_timeline_entry(index, path.stem, payload)

        by_dialog = payload.get("byDialogKey")
        if isinstance(by_dialog, dict):
            for raw_key, raw_entry in by_dialog.items():
                for entry in _iter_dialog_timeline_payload_entries(str(raw_key), raw_entry):
                    _index_dialog_timeline_entry(index, str(raw_key), entry)

        for raw_key, raw_entry in payload.items():
            if str(raw_key).startswith("_") or raw_key == "byDialogKey":
                continue
            for entry in _iter_dialog_timeline_payload_entries(str(raw_key), raw_entry):
                _index_dialog_timeline_entry(index, str(raw_key), entry)

    cleaned: dict[str, list[dict]] = {}
    for key, entries in index.items():
        public_entries: list[dict] = []
        for entry in entries:
            public = {field: entry[field] for field in ("sourceKey", "timeline", "file", "lineIds")}
            if entry.get("optionIds"):
                public["optionIds"] = entry["optionIds"]
            if entry.get("optionAnchors"):
                public["optionAnchors"] = entry["optionAnchors"]
            if entry.get("lineTimings"):
                public["lineTimings"] = entry["lineTimings"]
            if entry.get("optionPositions"):
                public["optionPositions"] = entry["optionPositions"]
            if entry.get("optionRows"):
                public["optionRows"] = entry["optionRows"]
            public_entries.append(public)
        public_entries.sort(key=lambda item: (-len(item["lineIds"]), item["sourceKey"], item["file"]))
        cleaned[key] = public_entries
    _DIALOG_TIMELINE_LINE_ORDER_CACHE = cleaned
    return _DIALOG_TIMELINE_LINE_ORDER_CACHE


def load_dialog_timeline_line_orders(conv_key: str) -> list[dict]:
    return list(_load_dialog_timeline_line_order_index().get(conv_key, []))


def load_dialog_timeline_option_anchors(conv_key: str) -> list[dict]:
    return [
        entry
        for entry in _load_dialog_timeline_line_order_index().get(conv_key, [])
        if entry.get("optionAnchors")
    ]


_TIMELINE_TO_DIALOG_KEYS_CACHE: dict[str, list[str]] | None = None


def _load_timeline_to_dialog_keys() -> dict[str, list[str]]:
    """Return {timeline_name: [dialog_key, ...]} reverse index across all timelines.

    Built once from the dialog-timeline index so that we can show "this scene
    shares its Unity timeline with X, Y" cross-links in the conv view.
    """
    global _TIMELINE_TO_DIALOG_KEYS_CACHE
    if _TIMELINE_TO_DIALOG_KEYS_CACHE is not None:
        return _TIMELINE_TO_DIALOG_KEYS_CACHE
    out: dict[str, set[str]] = defaultdict(set)
    for alias, entries in _load_dialog_timeline_line_order_index().items():
        if not isinstance(alias, str) or not alias.startswith("dlg_"):
            continue
        for entry in entries:
            timeline = str(entry.get("timeline") or entry.get("sourceKey") or "")
            if timeline:
                out[timeline].add(alias)
    _TIMELINE_TO_DIALOG_KEYS_CACHE = {tl: sorted(keys) for tl, keys in out.items()}
    return _TIMELINE_TO_DIALOG_KEYS_CACHE


def collect_related_scenes(conv_key: str) -> list[dict]:
    """For each timeline this scene appears in, list the OTHER dialog keys that
    also reference it. Returned dicts carry timeline name + line counts so the
    UI can show "shared timeline with X (3 lines overlap)".
    """
    if not conv_key:
        return []
    timeline_to_keys = _load_timeline_to_dialog_keys()
    own_entries = load_dialog_timeline_line_orders(conv_key)
    if not own_entries:
        return []
    own_line_ids: dict[str, set[str]] = {}
    for entry in own_entries:
        timeline = str(entry.get("timeline") or entry.get("sourceKey") or "")
        if not timeline:
            continue
        own_line_ids.setdefault(timeline, set()).update(
            str(line_id) for line_id in (entry.get("lineIds") or []) if str(line_id).startswith(f"{conv_key}_")
        )
    related: list[dict] = []
    seen_keys: set[str] = set()
    for timeline, line_set in own_line_ids.items():
        for sibling in timeline_to_keys.get(timeline, []):
            if sibling == conv_key or sibling in seen_keys:
                continue
            seen_keys.add(sibling)
            sibling_entries = load_dialog_timeline_line_orders(sibling)
            sibling_line_ids: set[str] = set()
            for entry in sibling_entries:
                if str(entry.get("timeline") or entry.get("sourceKey") or "") != timeline:
                    continue
                sibling_line_ids.update(
                    str(line_id)
                    for line_id in (entry.get("lineIds") or [])
                    if str(line_id).startswith(f"{sibling}_")
                )
            related.append({
                "key": sibling,
                "timeline": timeline,
                "ownLineCount": len(line_set),
                "siblingLineCount": len(sibling_line_ids),
            })
    related.sort(key=lambda item: (item["key"], item["timeline"]))
    return related


def collect_option_position_anchors(conv_key: str) -> list[dict]:
    """For each option clip on a timeline this conv participates in, locate the
    line in this conv (by id prefix) whose `start` is the immediate predecessor
    of the option clip's start. Returns one record per option clip in
    chronological order, so caller can map nth optionGroup to nth position.
    """
    if not conv_key:
        return []
    out: list[dict] = []
    for entry in load_dialog_timeline_line_orders(conv_key):
        positions = entry.get("optionPositions") or []
        line_timings = entry.get("lineTimings") or []
        if not positions or not line_timings:
            continue
        own_line_timings = sorted(
            (
                (float(item.get("start", 0.0)), str(item.get("id") or ""))
                for item in line_timings
                if str(item.get("id") or "").startswith(f"{conv_key}_")
            ),
            key=lambda pair: pair[0],
        )
        if not own_line_timings:
            continue
        timeline_name = str(entry.get("timeline") or entry.get("sourceKey") or "")
        for position in positions:
            try:
                pos_start = float(position.get("start", 0.0))
            except (TypeError, ValueError):
                continue
            before = ""
            for start, line_id in own_line_timings:
                if start <= pos_start + 1e-6:
                    before = line_id
                else:
                    break
            sibling_scenes = [s for s in (position.get("scenes") or []) if s and s != conv_key]
            out.append({
                "start": pos_start,
                "afterLineId": before,
                "siblingScenes": sibling_scenes,
                "timeline": timeline_name,
            })
    out.sort(key=lambda item: item["start"])
    return out


def collect_line_timings(conv_key: str) -> dict[str, dict]:
    """Return {line_id: {start, duration, timeline}} for lines in this conv
    that have recovered Unity Timeline timestamps.
    """
    if not conv_key:
        return {}
    out: dict[str, dict] = {}
    for entry in load_dialog_timeline_line_orders(conv_key):
        timeline = str(entry.get("timeline") or entry.get("sourceKey") or "")
        for record in entry.get("lineTimings") or []:
            line_id = str(record.get("id") or "")
            if not line_id.startswith(f"{conv_key}_"):
                continue
            existing = out.get(line_id)
            new_record = {
                "start": record.get("start"),
                "duration": record.get("duration"),
                "timeline": timeline,
            }
            if existing is None or (
                # Prefer the entry whose timeline this line ID actually belongs to.
                str(existing.get("timeline") or "").lower() != timeline.lower()
                and timeline.startswith(f"dlgtl_{conv_key[len('dlg_'):]}_")
            ):
                out[line_id] = new_record
    return out


def _nearest_visible_timeline_anchor(anchor_id: str, timeline_line_ids: list[str], valid_line_ids: set[str]) -> str:
    anchor_id = str(anchor_id or "").strip()
    if not anchor_id:
        return ""
    if anchor_id in valid_line_ids:
        return anchor_id
    if not timeline_line_ids:
        return ""
    try:
        anchor_index = timeline_line_ids.index(anchor_id)
    except ValueError:
        return ""
    for line_id in reversed(timeline_line_ids[: anchor_index + 1]):
        if line_id in valid_line_ids:
            return line_id
    return ""


def _load_dialog_tree_source(tree_key: str) -> dict | None:
    """Parse one AnimeStudio DialogTree file, preserving per-target slices."""
    if tree_key in _DIALOG_TREE_SOURCE_CACHE:
        return _DIALOG_TREE_SOURCE_CACHE[tree_key]
    tree_path = _find_anime_tree_path(f"{tree_key}.json")
    if not tree_path.exists():
        _DIALOG_TREE_SOURCE_CACHE[tree_key] = None
        return None
    tree = _load_anime_resource_payload(tree_path)
    if not isinstance(tree, dict):
        _DIALOG_TREE_SOURCE_CACHE[tree_key] = None
        return None

    nodes = [
        dict(node) if isinstance(node, dict) else node
        for node in (tree.get("nodes") or [])
    ]
    existing_node_ids = {
        str(node.get("$id"))
        for node in nodes
        if isinstance(node, dict) and node.get("$id") is not None
    }
    for idx, node in enumerate(nodes):
        if not isinstance(node, dict) or node.get("$id") is not None:
            continue
        synthetic_id = str(idx)
        if synthetic_id in existing_node_ids:
            synthetic_id = f"__idx_{idx}"
        node["$id"] = synthetic_id
        existing_node_ids.add(synthetic_id)
    conns = tree.get("connections") or []
    by_id: dict[str, dict] = {}
    for n in nodes:
        nid = n.get("$id")
        if nid:
            by_id[nid] = n

    line_graph = _normalize_dialog_tree_line_graph(nodes, conns)
    option_nodes = [
        n for n in nodes
        if _node_short_type(n) == "DialogTreeOptionNode" and n.get("$id")
    ]
    action_assets: list[dict[str, str]] = []
    seen_action_assets: set[tuple[str, str]] = set()
    for node in nodes:
        if not isinstance(node, dict):
            continue
        action = node.get("_actionData") or {}
        if not isinstance(action, dict):
            continue
        action_name = str(action.get("name") or "").strip()
        if not action_name:
            continue
        candidate_names = [action_name]
        if not action_name.startswith(("f_", "m_")):
            candidate_names.extend([f"f_{action_name}", f"m_{action_name}"])
        for candidate_name in candidate_names:
            action_path = _find_anime_tree_path(f"{candidate_name}.json")
            if not action_path.exists():
                continue
            rel_path = action_path.relative_to(ROOT).as_posix()
            dedup = (action_name, rel_path)
            if dedup in seen_action_assets:
                continue
            seen_action_assets.add(dedup)
            asset = {
                "name": action_name,
                "file": rel_path,
            }
            if candidate_name != action_name:
                asset["resolvedName"] = candidate_name
            action_assets.append(asset)
    line_ids, line_order_debug = _ordered_dialog_tree_trunk_ids(nodes, conns)
    option_ids = _unique_preserve([
        entry["_optionId"]
        for node in option_nodes
        for entry in (node.get("_normalOptions") or [])
        if isinstance(entry, dict) and entry.get("_optionId")
    ])
    terminal_counts = {
        "openUi": sum(1 for n in nodes if _node_short_type(n) == "DialogTreeOpenUINode"),
        "finish": sum(1 for n in nodes if _node_short_type(n) == "DialogTreeFinishNode"),
    }

    preds: dict[str, list[str]] = defaultdict(list)
    succs: dict[str, list[str]] = defaultdict(list)
    for c in conns:
        s = (c.get("_sourceNode") or {}).get("$ref")
        t = (c.get("_targetNode") or {}).get("$ref")
        if s and t:
            preds[t].append(s)
            succs[s].append(t)

    def node_type(node_id: str) -> str:
        node = by_id.get(node_id)
        return _node_short_type(node) if node else ""

    def node_trunk_id(node_id: str) -> str | None:
        node = by_id.get(node_id)
        return _first_string_field(node, "_trunkId") if node else None

    def nearest_trunk_id(start_id: str, prefix: str | None = None) -> str | None:
        seen: set[str] = {start_id}
        stack = list(preds.get(start_id, []))
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            node = by_id.get(cur)
            if node is None:
                continue
            if _node_short_type(node) == "DialogTreeTrunkNode":
                trunk_id = _first_string_field(node, "_trunkId")
                if trunk_id and (not prefix or _dialog_tree_scene_prefix(trunk_id) == prefix):
                    return trunk_id
            stack.extend(preds.get(cur, []))
        return None

    def nearest_option_anchor_trunk_id(
        start_id: str,
        *,
        prefix: str | None = None,
        excluded_trunks: set[str] | None = None,
    ) -> str | None:
        """Find the nearest upstream trunk that is not one of this menu's branches.

        Option hubs often have loop-return predecessors from branch endings.
        Those are graph predecessors, but they are not the line after which the
        menu first appears. Walk predecessors in connection order and skip any
        trunk already seen on the option group's forward paths.
        """
        excluded = {str(value) for value in (excluded_trunks or set()) if str(value)}
        seen: set[str] = {start_id}
        queue = deque(preds.get(start_id, []))
        while queue:
            cur = queue.popleft()
            if cur in seen:
                continue
            seen.add(cur)
            node = by_id.get(cur)
            if node is None:
                continue
            if _node_short_type(node) == "DialogTreeTrunkNode":
                trunk_id = _first_string_field(node, "_trunkId")
                if trunk_id and (not prefix or _dialog_tree_scene_prefix(trunk_id) == prefix):
                    if trunk_id not in excluded:
                        return trunk_id
            queue.extend(preds.get(cur, []))
        return None

    def nearest_layout_trunk_id(start_id: str, prefix: str | None = None) -> str | None:
        node = by_id.get(start_id)
        if not isinstance(node, dict):
            return None
        pos = node.get("_position") or {}
        if not isinstance(pos, dict):
            return None
        try:
            x = float(pos.get("x"))
            y = float(pos.get("y"))
        except (TypeError, ValueError):
            return None
        candidates: list[tuple[float, float, float, str]] = []
        for candidate in by_id.values():
            if _node_short_type(candidate) != "DialogTreeTrunkNode":
                continue
            trunk_id = _first_string_field(candidate, "_trunkId")
            if not trunk_id or (prefix and _dialog_tree_scene_prefix(trunk_id) != prefix):
                continue
            candidate_pos = candidate.get("_position") or {}
            if not isinstance(candidate_pos, dict):
                continue
            try:
                cx = float(candidate_pos.get("x"))
                cy = float(candidate_pos.get("y"))
            except (TypeError, ValueError):
                continue
            candidates.append((abs(cx - x), abs(cy - y), -cx, trunk_id))
        if not candidates:
            return None
        candidates.sort()
        return candidates[0][3]

    def walk_linear_path(start_id: str | None) -> list[str]:
        if not start_id:
            return []
        out: list[str] = []
        seen: set[str] = set()
        cur = start_id
        while cur and cur not in seen:
            seen.add(cur)
            out.append(cur)
            typ = node_type(cur)
            if typ in ("DialogTreeFinishNode", "DialogTreeOpenUINode", "DialogTreeOptionNode"):
                break
            nxts = _unique_preserve(succs.get(cur, []))
            if len(nxts) != 1:
                break
            cur = nxts[0]
        return out

    def first_common_node(paths: list[list[str]]) -> str | None:
        non_empty = [path for path in paths if path]
        if len(non_empty) < 2:
            return None
        common = set(non_empty[0])
        for path in non_empty[1:]:
            common &= set(path)
        if not common:
            return None
        for node_id in non_empty[0]:
            if node_id in common:
                return node_id
        return None

    def first_trunk_on_path(start_id: str | None, prefix: str | None = None) -> str | None:
        for node_id in walk_linear_path(start_id):
            trunk_id = node_trunk_id(node_id)
            if trunk_id and (not prefix or _dialog_tree_scene_prefix(trunk_id) == prefix):
                return trunk_id
        return None

    after_map: dict[str, str] = {}
    branch_map: dict[str, list[str]] = {}
    merge_map: dict[str, str] = {}
    converge_map: dict[str, str] = {}
    pre_option_ids: list[str] = []
    scene_line_ids_by_prefix: dict[str, list[str]] = defaultdict(list)
    for line_id in line_ids:
        if prefix := _dialog_tree_scene_prefix(line_id):
            scene_line_ids_by_prefix[prefix].append(line_id)

    fragment_builders: dict[str, dict] = {}
    scene_link_builders: dict[str, list[dict]] = defaultdict(list)

    def option_node_scene_prefixes(node_id: str) -> list[str]:
        node = by_id.get(node_id) or {}
        return _unique_preserve([
            prefix
            for prefix in (
                _dialog_tree_option_prefix(entry["_optionId"])
                for entry in (node.get("_normalOptions") or [])
                if isinstance(entry, dict) and entry.get("_optionId")
            )
            if prefix
        ])

    def option_node_option_ids(node_id: str) -> list[str]:
        node = by_id.get(node_id) or {}
        return _unique_preserve([
            str(entry["_optionId"])
            for entry in (node.get("_normalOptions") or [])
            if isinstance(entry, dict) and entry.get("_optionId")
        ])

    def summarize_option_target(start_id: str | None) -> dict:
        path = walk_linear_path(start_id)
        line_path = _unique_preserve([
            trunk_id
            for node_id in path
            if (trunk_id := node_trunk_id(node_id))
        ])
        scene_path = _unique_preserve([
            prefix
            for prefix in (_dialog_tree_scene_prefix(line_id) for line_id in line_path)
            if prefix
        ])
        summary: dict = {
            "pathLineIds": line_path,
            "sceneKeys": scene_path,
        }
        debug: dict[str, object] = {}
        if start_id:
            debug["startNodeId"] = start_id
        if path:
            debug["pathNodeIds"] = path
        if line_path:
            summary["firstLineId"] = line_path[0]
        if scene_path:
            summary["firstSceneKey"] = scene_path[0]
        if path:
            last_id = path[-1]
            last_type = node_type(last_id)
            if last_id:
                debug["endNodeId"] = last_id
            if last_type:
                debug["endNodeType"] = last_type
            if last_type == "DialogTreeOptionNode":
                submenu_scene_keys = option_node_scene_prefixes(last_id)
                if submenu_scene_keys:
                    summary["submenuSceneKeys"] = submenu_scene_keys
                return_option_ids = option_node_option_ids(last_id)
                if return_option_ids:
                    debug["returnOptionIds"] = return_option_ids
            elif last_type == "DialogTreeFinishNode":
                summary["terminal"] = "finish"
            elif last_type == "DialogTreeOpenUINode":
                summary["terminal"] = "openUi"
        elif start_id:
            start_type = node_type(start_id)
            if start_id:
                debug["endNodeId"] = start_id
            if start_type:
                debug["endNodeType"] = start_type
            if start_type == "DialogTreeOptionNode":
                submenu_scene_keys = option_node_scene_prefixes(start_id)
                if submenu_scene_keys:
                    summary["submenuSceneKeys"] = submenu_scene_keys
                return_option_ids = option_node_option_ids(start_id)
                if return_option_ids:
                    debug["returnOptionIds"] = return_option_ids
            elif start_type == "DialogTreeFinishNode":
                summary["terminal"] = "finish"
            elif start_type == "DialogTreeOpenUINode":
                summary["terminal"] = "openUi"
        if debug:
            summary["_debug"] = debug
        return summary

    source_scene_keys = sorted(scene_line_ids_by_prefix)

    cinematic_timeline_anchors: list[dict] = []
    seen_cinematic_timeline_anchors: set[tuple[str, str]] = set()
    for node in nodes:
        if not isinstance(node, dict) or _node_short_type(node) != "DialogTreeCinematicNode":
            continue
        node_id = str(node.get("$id") or "")
        action = node.get("_actionData") or {}
        if not node_id or not isinstance(action, dict):
            continue
        action_name = str(action.get("name") or "").strip()
        if not action_name:
            continue
        identity = (node_id, action_name)
        if identity in seen_cinematic_timeline_anchors:
            continue
        seen_cinematic_timeline_anchors.add(identity)
        anchor: dict[str, object] = {
            "sourceKey": tree_key,
            "file": tree_path.relative_to(ROOT).as_posix(),
            "nodeId": node_id,
            "timeline": action_name,
        }
        target_node_ids = [
            str(target_id)
            for target_id in _unique_preserve(succs.get(node_id, []))
            if target_id
        ]
        if target_node_ids:
            anchor["targetNodeIds"] = target_node_ids
            anchor["targetCount"] = len(target_node_ids)
            if before := first_trunk_on_path(target_node_ids[0]):
                anchor["before"] = before
        if after := nearest_trunk_id(node_id):
            anchor["after"] = after
        cinematic_timeline_anchors.append(anchor)

    cinematic_finish_groups: list[dict] = []
    for node in nodes:
        if not isinstance(node, dict) or _node_short_type(node) != "DialogTreeCinematicNode":
            continue
        node_id = str(node.get("$id") or "")
        action = node.get("_actionData") or {}
        if not node_id or not isinstance(action, dict):
            continue
        action_name = str(action.get("name") or "").strip()
        finish_nums_raw = action.get("timelineFinishNums") or []
        if (
            not action_name
            or not action.get("useTimelineFinishNumBranch")
            or not isinstance(finish_nums_raw, list)
            or len(finish_nums_raw) < 2
        ):
            continue
        finish_nums: list[object] = []
        for value in finish_nums_raw:
            if isinstance(value, bool):
                finish_nums.append(int(value))
            elif isinstance(value, int):
                finish_nums.append(value)
            elif isinstance(value, float) and value.is_integer():
                finish_nums.append(int(value))
            else:
                finish_nums.append(value)
        finish_group: dict[str, object] = {
            "sourceKey": tree_key,
            "file": tree_path.relative_to(ROOT).as_posix(),
            "nodeId": node_id,
            "timeline": action_name,
            "finishNums": finish_nums,
        }
        target_node_ids = [
            str(target_id)
            for target_id in _unique_preserve(succs.get(node_id, []))
            if target_id
        ]
        if target_node_ids:
            finish_group["targetNodeIds"] = target_node_ids
            finish_group["targetCount"] = len(target_node_ids)
        if after := nearest_trunk_id(node_id):
            finish_group["after"] = after
        cinematic_finish_groups.append(finish_group)

    def classify_option_target_summary(summary: dict, target_key: str, source_option_node_id: str) -> dict:
        scene_keys = _unique_preserve([
            str(scene_key)
            for scene_key in (summary.get("sceneKeys") or [])
            if scene_key
        ])
        submenu_scene_keys = _unique_preserve([
            str(scene_key)
            for scene_key in (summary.get("submenuSceneKeys") or [])
            if scene_key
        ])
        terminal = str(summary.get("terminal") or "")
        first_scene_key = str(summary.get("firstSceneKey") or "")
        debug = dict(summary.get("_debug") or {})
        end_node_id = str(debug.get("endNodeId") or "")
        end_node_type = str(debug.get("endNodeType") or "")
        same_scene_path = bool(scene_keys) and all(scene_key == target_key for scene_key in scene_keys)
        returns_to_target_menu = bool(target_key) and target_key in submenu_scene_keys
        returns_to_other_menu = any(
            scene_key != target_key
            for scene_key in submenu_scene_keys
        )
        returns_to_source_option_node = (
            end_node_type == "DialogTreeOptionNode"
            and end_node_id == source_option_node_id
        )

        outcome_kind = "unknown"
        loop: dict[str, object] | None = None

        if end_node_type == "DialogTreeOptionNode":
            if returns_to_target_menu:
                outcome_kind = "sameSceneMenuLoop"
            elif returns_to_other_menu or any(scene_key != target_key for scene_key in scene_keys):
                outcome_kind = "crossSceneMenuReturn"
            else:
                outcome_kind = "menuReturn"
            loop = {
                "kind": "sameOptionMenuReturn" if returns_to_source_option_node else "menuReturn",
                "returnsToSourceOptionNode": returns_to_source_option_node,
            }
            if submenu_scene_keys:
                loop["sceneKeys"] = submenu_scene_keys
            if len(source_scene_keys) > 1:
                loop["sourceSceneKeys"] = source_scene_keys
        elif terminal:
            if same_scene_path:
                outcome_kind = "sameSceneTerminal"
            elif scene_keys:
                outcome_kind = "crossSceneTerminal"
            else:
                outcome_kind = "terminalOnly"
        elif same_scene_path:
            outcome_kind = "sameScenePath"
        elif scene_keys:
            outcome_kind = "crossScenePath"
        elif submenu_scene_keys:
            outcome_kind = "menuReturn"

        debug["targetSceneKey"] = target_key
        debug["sourceOptionNodeId"] = source_option_node_id
        if end_node_type == "DialogTreeOptionNode":
            debug["returnsToSourceOptionNode"] = returns_to_source_option_node
        summary["outcomeKind"] = outcome_kind
        summary["_debug"] = debug
        if loop:
            summary["loop"] = loop
        return summary

    def ensure_fragment(target_key: str) -> dict:
        fragment = fragment_builders.get(target_key)
        if fragment is None:
            fragment = {
                "sourceKey": tree_key,
                "targetKey": target_key,
                "file": tree_path.relative_to(ROOT).as_posix(),
                "lineIds": list(scene_line_ids_by_prefix.get(target_key, [])),
                "optionGroups": [],
                "terminalCounts": {"openUi": 0, "finish": 0},
                "after": {},
                "branches": {},
                "merge": {},
                "pre": [],
                "sceneSpan": len(scene_line_ids_by_prefix) > 1,
                "sourceSceneKeys": sorted(scene_line_ids_by_prefix),
            }
            fragment_builders[target_key] = fragment
        return fragment

    for opt_node in option_nodes:
        opt_entries = [
            entry for entry in (opt_node.get("_normalOptions") or [])
            if isinstance(entry, dict) and entry.get("_optionId")
        ]
        if not opt_entries:
            continue

        targets = list(succs.get(opt_node["$id"], []))
        if len(targets) == 1 and len(opt_entries) > 1:
            targets = targets * len(opt_entries)

        paths_by_option: dict[str, list[str]] = {}
        first_trunk_by_option: dict[str, str | None] = {}
        terminal_kind_by_option: dict[str, str] = {}
        for idx, entry in enumerate(opt_entries):
            opt_id = entry["_optionId"]
            target = targets[idx] if idx < len(targets) else None
            option_path = walk_linear_path(target)
            paths_by_option[opt_id] = option_path
            first_trunk_by_option[opt_id] = first_trunk_on_path(target)
            if option_path:
                last_type = node_type(option_path[-1])
                if last_type in ("DialogTreeFinishNode", "DialogTreeOpenUINode"):
                    terminal_kind_by_option[opt_id] = last_type

        unique_paths = {tuple(path) for path in paths_by_option.values()}
        local_group_details: dict[str, dict] = {}
        if len(unique_paths) < 2:
            common_node = None
            merge_trunk = None
            if len(opt_entries) >= 2 and targets:
                common_trunk = first_trunk_on_path(targets[0])
                if common_trunk:
                    for entry in opt_entries:
                        converge_map[entry["_optionId"]] = common_trunk
        else:
            common_node = first_common_node(list(paths_by_option.values()))
            merge_trunk = first_trunk_on_path(common_node) if common_node else None
            for opt_id, option_path in paths_by_option.items():
                exclusive_trunks: list[str] = []
                for node_id in option_path:
                    if common_node and node_id == common_node:
                        break
                    trunk_id = node_trunk_id(node_id)
                    if trunk_id:
                        exclusive_trunks.append(trunk_id)
                if exclusive_trunks:
                    branch_map[opt_id] = exclusive_trunks
                    if merge_trunk:
                        merge_map[opt_id] = merge_trunk

        scene_option_prefixes = _unique_preserve([
            prefix
            for prefix in (_dialog_tree_option_prefix(entry["_optionId"]) for entry in opt_entries)
            if prefix
        ])

        target_prefixes = _unique_preserve([
            prefix
            for prefix in (
                _dialog_tree_scene_prefix(first_trunk_by_option.get(entry["_optionId"]) or "")
                for entry in opt_entries
            )
            if prefix
        ])

        per_target_options: dict[str, list[str]] = defaultdict(list)
        for entry in opt_entries:
            opt_id = entry["_optionId"]
            if prefix := _dialog_tree_option_prefix(opt_id):
                per_target_options[prefix].append(opt_id)

        # Precompute per-target summaries and "interesting"/"pre" flags once
        # so both the scene-link and fragment loops read the correct values.
        # The original code built `option_summaries` inside the scene-link
        # loop and the fragment loop then read the stale final-iteration
        # value — misclassifying most fragment groups.
        per_target_summaries: dict[str, list[dict]] = {}
        per_target_has_interesting: dict[str, bool] = {}
        per_target_is_pre: dict[str, bool] = {}
        per_target_after: dict[str, str | None] = {}
        for target_key, target_opt_ids in per_target_options.items():
            forward_option_ids = [
                opt_id
                for opt_id in target_opt_ids
                if _dialog_tree_scene_prefix(first_trunk_by_option.get(opt_id) or "") == target_key
            ]
            forward_trunk_ids = {
                trunk_id
                for opt_id in forward_option_ids
                for node_id in paths_by_option.get(opt_id, [])
                if (trunk_id := node_trunk_id(node_id))
            }
            backward_trunk = (
                nearest_option_anchor_trunk_id(
                    opt_node["$id"],
                    prefix=target_key,
                    excluded_trunks=forward_trunk_ids,
                )
                or nearest_layout_trunk_id(opt_node["$id"], prefix=target_key)
            )
            # Hub-loop detection: in hub-spoke trees (e.g. dlg_a1m3_10 feeding
            # a1m3_3/4/5), the option's backward predecessors include the last
            # trunk of each spoke scene via loop-return DialogTransitionNodes.
            # That trunk is NOT a semantic "after" anchor — the option
            # introduces the scene. Suppress it only when the backward trunk
            # is actually on one of this option group's own forward paths.
            group_after = backward_trunk
            if backward_trunk and backward_trunk in forward_trunk_ids:
                group_after = None
            summaries: list[dict] = []
            has_interesting_target = False
            for idx, entry in enumerate(opt_entries):
                opt_id = entry["_optionId"]
                if opt_id not in target_opt_ids:
                    continue
                target = targets[idx] if idx < len(targets) else None
                summary = summarize_option_target(target)
                summary = classify_option_target_summary(summary, target_key, opt_node["$id"])
                option_summary = {
                    "optionId": opt_id,
                    **summary,
                }
                summaries.append(option_summary)
                if summary.get("loop"):
                    has_interesting_target = True
                if summary.get("terminal"):
                    has_interesting_target = True
                if summary.get("firstSceneKey") and summary.get("firstSceneKey") != target_key:
                    has_interesting_target = True
                if any(
                    scene_key != target_key
                    for scene_key in (summary.get("submenuSceneKeys") or [])
                ):
                    has_interesting_target = True
                if any(scene_key != target_key for scene_key in (summary.get("sceneKeys") or [])):
                    has_interesting_target = True
            group_is_pre = False
            if not group_after:
                group_is_pre = any(
                    summary.get("firstSceneKey") == target_key
                    or target_key in (summary.get("sceneKeys") or [])
                    or bool(summary.get("terminal"))
                    for summary in summaries
                )
            per_target_summaries[target_key] = summaries
            per_target_has_interesting[target_key] = has_interesting_target
            per_target_is_pre[target_key] = group_is_pre
            per_target_after[target_key] = group_after

        for target_key, target_opt_ids in per_target_options.items():
            group_after = per_target_after[target_key]
            option_summaries = per_target_summaries[target_key]
            has_interesting_target = per_target_has_interesting[target_key]
            group_is_pre = per_target_is_pre[target_key]
            if group_after:
                for opt_id in target_opt_ids:
                    after_map[opt_id] = group_after
            if group_is_pre:
                for opt_id in target_opt_ids:
                    if opt_id not in pre_option_ids:
                        pre_option_ids.append(opt_id)
            if not has_interesting_target:
                continue
            scene_link_builders[target_key].append({
                "sourceKey": tree_key,
                "sceneKey": target_key,
                "file": tree_path.relative_to(ROOT).as_posix(),
                "after": group_after or "",
                "options": option_summaries,
                **({"position": "pre"} if group_is_pre else {}),
                "sceneSpan": len(scene_line_ids_by_prefix) > 1,
                "sourceSceneKeys": sorted(scene_line_ids_by_prefix),
                "_debug": {
                    "sourceOptionNodeId": opt_node["$id"],
                    "groupSceneKeys": scene_option_prefixes,
                    "targetSceneKeys": target_prefixes,
                },
            })

        for target_key, target_opt_ids in per_target_options.items():
            if target_key == tree_key:
                continue
            fragment = ensure_fragment(target_key)
            relevant_targets = _unique_preserve([
                prefix
                for opt_id in target_opt_ids
                if (prefix := _dialog_tree_scene_prefix(first_trunk_by_option.get(opt_id) or ""))
            ])
            group_mode = "sceneLocal"
            for opt_id in target_opt_ids:
                first_scene_key = _dialog_tree_scene_prefix(first_trunk_by_option.get(opt_id) or "")
                local_branch_lines = [
                    line_id
                    for line_id in (branch_map.get(opt_id) or [])
                    if _dialog_tree_scene_prefix(line_id) == target_key
                ]
                has_local_evidence = bool(
                    local_branch_lines
                    or first_scene_key == target_key
                    or terminal_kind_by_option.get(opt_id)
                )
                has_foreign_evidence = bool(
                    first_scene_key and first_scene_key != target_key
                ) or any(
                    _dialog_tree_scene_prefix(line_id) not in (None, target_key)
                    for line_id in (branch_map.get(opt_id) or [])
                )
                if has_foreign_evidence or not has_local_evidence:
                    group_mode = "crossScene"
                    break
            group_after = per_target_after[target_key] if group_mode == "sceneLocal" else None
            option_summaries = per_target_summaries[target_key]
            group_is_pre = False
            if group_mode == "sceneLocal" and not group_after:
                group_is_pre = any(
                    summary.get("firstSceneKey") == target_key
                    or target_key in (summary.get("sceneKeys") or [])
                    or bool(summary.get("terminal"))
                    for summary in option_summaries
                )
            group = {
                "mode": group_mode,
                "optionIds": list(target_opt_ids),
                "_debug": {
                    "groupSceneKeys": scene_option_prefixes,
                    "targetSceneKeys": relevant_targets,
                    "sourceOptionNodeId": opt_node["$id"],
                },
            }
            if group_after:
                group["after"] = group_after
            elif group_is_pre:
                group["position"] = "pre"

            group_branches: dict[str, list[str]] = {}
            group_merge: dict[str, str] = {}
            for opt_id in target_opt_ids:
                local_branch_lines = [
                    line_id
                    for line_id in (branch_map.get(opt_id) or [])
                    if _dialog_tree_scene_prefix(line_id) == target_key
                ]
                if local_branch_lines:
                    group_branches[opt_id] = local_branch_lines
                    if group_mode == "sceneLocal":
                        fragment["branches"][opt_id] = local_branch_lines
                if group_mode == "sceneLocal" and group_after:
                    fragment["after"][opt_id] = group_after
                elif group_mode == "sceneLocal" and group_is_pre:
                    if opt_id not in fragment["pre"]:
                        fragment["pre"].append(opt_id)
                    if opt_id not in pre_option_ids:
                        pre_option_ids.append(opt_id)
                local_merge = merge_map.get(opt_id)
                if local_merge and _dialog_tree_scene_prefix(local_merge) == target_key:
                    group_merge[opt_id] = local_merge
                    if group_mode == "sceneLocal":
                        fragment["merge"][opt_id] = local_merge
                terminal_kind = terminal_kind_by_option.get(opt_id, "")
                if terminal_kind == "DialogTreeOpenUINode":
                    fragment["terminalCounts"]["openUi"] += 1
                elif terminal_kind == "DialogTreeFinishNode":
                    fragment["terminalCounts"]["finish"] += 1
            if group_branches:
                group["branches"] = group_branches
            if group_merge:
                group["merge"] = group_merge
            fragment["optionGroups"].append(group)

    target_fragments: list[dict] = []
    for target_key, fragment in fragment_builders.items():
        if not fragment["optionGroups"] and len(scene_line_ids_by_prefix) == 1:
            fragment["terminalCounts"] = dict(terminal_counts)
        if not fragment["lineIds"] and not fragment["optionGroups"] and not any(fragment["terminalCounts"].values()):
            continue
        target_fragments.append(fragment)
    scene_links = [
        link
        for scene_key in sorted(scene_link_builders)
        for link in scene_link_builders[scene_key]
    ]

    source = {
        "sourceKey": tree_key,
        "file": tree_path.relative_to(ROOT).as_posix(),
        "lineIds": line_ids,
        "lineGraph": line_graph,
        "lineOrder": {
            "mode": "graphTraversal",
            **line_order_debug,
        },
        "optionIds": option_ids,
        "terminalCounts": terminal_counts,
        "after": after_map,
        "branches": branch_map,
        "merge": merge_map,
        "converge": converge_map,
        "pre": pre_option_ids,
        "actionAssets": action_assets,
        "cinematicOnly": bool(action_assets) and not line_ids,
        "cinematicTimelineAnchors": cinematic_timeline_anchors,
        "cinematicFinishGroups": cinematic_finish_groups,
        "targetFragments": target_fragments,
        "sceneLinks": scene_links,
    }
    has_signal = bool(
        line_ids
        or option_ids
        or any(terminal_counts.values())
        or cinematic_finish_groups
        or target_fragments
        or scene_links
    )
    _DIALOG_TREE_SOURCE_CACHE[tree_key] = source if has_signal else None
    return _DIALOG_TREE_SOURCE_CACHE[tree_key]


def _load_dialog_tree_file(tree_key: str) -> dict | None:
    """Return compact whole-tree metadata for one AnimeStudio DialogTree file."""
    if tree_key in _DIALOG_TREE_FILE_CACHE:
        return _DIALOG_TREE_FILE_CACHE[tree_key]
    source = _load_dialog_tree_source(tree_key)
    if not source:
        _DIALOG_TREE_FILE_CACHE[tree_key] = None
        return None
    result = {
        "sourceKey": source.get("sourceKey") or tree_key,
        "file": source.get("file") or "",
        "lineIds": source.get("lineIds") or [],
        "lineGraph": source.get("lineGraph") or {},
        "lineOrder": source.get("lineOrder") or {},
        "optionIds": source.get("optionIds") or [],
        "terminalCounts": source.get("terminalCounts") or {},
        "after": source.get("after") or {},
        "branches": source.get("branches") or {},
        "merge": source.get("merge") or {},
        "converge": source.get("converge") or {},
        "pre": source.get("pre") or [],
        "actionAssets": source.get("actionAssets") or [],
        "cinematicOnly": bool(source.get("cinematicOnly")),
        "cinematicTimelineAnchors": source.get("cinematicTimelineAnchors") or [],
        "cinematicFinishGroups": source.get("cinematicFinishGroups") or [],
    }
    _DIALOG_TREE_FILE_CACHE[tree_key] = result
    return result


def _load_related_dialog_tree_files(conv_key: str, original_line_ids: list[str] | None = None) -> list[dict]:
    cache_key = (conv_key, tuple(original_line_ids or ()))
    if cache_key in _RELATED_DIALOG_TREE_FILE_CACHE:
        return list(_RELATED_DIALOG_TREE_FILE_CACHE[cache_key])
    available_line_ids = set(original_line_ids or [])
    related: list[dict] = []
    seen_source_keys: set[str] = set()

    for path in _iter_related_dialog_tree_paths(conv_key):
        source_key = path.stem
        if source_key == conv_key or source_key in seen_source_keys:
            continue
        source = _load_dialog_tree_source(source_key)
        if not source:
            continue
        line_ids = source.get("lineIds") or []
        source_scene_keys = set(source.get("sourceSceneKeys") or [])
        line_matches = [
            line_id
            for line_id in line_ids
            if line_id.startswith(f"{conv_key}_")
            or (available_line_ids and line_id in available_line_ids)
        ]
        if not line_matches and conv_key not in source_scene_keys:
            continue
        seen_source_keys.add(source_key)
        related.append({
            "sourceKey": source.get("sourceKey") or source_key,
            "file": source.get("file") or "",
            "lineIds": line_ids,
            "lineGraph": source.get("lineGraph") or {},
            "lineOrder": source.get("lineOrder") or {},
            "optionIds": source.get("optionIds") or [],
            "terminalCounts": source.get("terminalCounts") or {},
            "after": source.get("after") or {},
            "branches": source.get("branches") or {},
            "merge": source.get("merge") or {},
            "pre": source.get("pre") or [],
            "actionAssets": source.get("actionAssets") or [],
            "cinematicOnly": bool(source.get("cinematicOnly")),
            "cinematicTimelineAnchors": source.get("cinematicTimelineAnchors") or [],
            "cinematicFinishGroups": source.get("cinematicFinishGroups") or [],
        })

    _RELATED_DIALOG_TREE_FILE_CACHE[cache_key] = list(related)
    return list(related)


def load_dialog_tree_fragments(conv_key: str) -> list[dict]:
    """Return authored tree fragments that target a different base scene."""
    global _DIALOG_TREE_FRAGMENT_TARGETS_CACHE
    if _DIALOG_TREE_FRAGMENT_TARGETS_CACHE is None:
        targets: dict[str, list[dict]] = defaultdict(list)
        for path in _iter_anime_tree_files("dlg_*.json"):
            if path.name.endswith("_extra_config.json"):
                continue
            source_key = path.stem
            source = _load_dialog_tree_source(source_key)
            if not source:
                continue
            for fragment in source.get("targetFragments") or []:
                target_key = fragment.get("targetKey") or ""
                if not target_key or target_key == source_key:
                    continue
                targets[target_key].append(fragment)
        for bucket in targets.values():
            bucket.sort(key=lambda item: item["sourceKey"])
        _DIALOG_TREE_FRAGMENT_TARGETS_CACHE = dict(targets)
    return list((_DIALOG_TREE_FRAGMENT_TARGETS_CACHE or {}).get(conv_key, []))


def load_dialog_tree_scene_links(conv_key: str) -> list[dict]:
    """Return authored outgoing scene/menu links for one scene key."""
    global _DIALOG_TREE_SCENE_LINKS_CACHE
    if _DIALOG_TREE_SCENE_LINKS_CACHE is None:
        scene_links: dict[str, list[dict]] = defaultdict(list)
        for path in _iter_anime_tree_files("dlg_*.json"):
            if path.name.endswith("_extra_config.json"):
                continue
            source = _load_dialog_tree_source(path.stem)
            if not source:
                continue
            for link in source.get("sceneLinks") or []:
                scene_key = link.get("sceneKey") or ""
                if scene_key:
                    scene_links[scene_key].append(link)
        for bucket in scene_links.values():
            bucket.sort(key=lambda item: ((item.get("sourceKey") or ""), (item.get("after") or "")))
        _DIALOG_TREE_SCENE_LINKS_CACHE = dict(scene_links)
    return list((_DIALOG_TREE_SCENE_LINKS_CACHE or {}).get(conv_key, []))


def load_dialog_tree(conv_key: str) -> dict | None:
    """Return compact branch metadata from AnimeStudio DialogTree.

    Payload shape:
      {
        "after": {option_id: after_trunk_id},
        "branches": {option_id: [exclusive_trunk_id, ...]},
        "merge": {option_id: merge_trunk_id},
        "cinematicFinishGroups": [
          {"timeline": timeline_asset_name, "finishNums": [...], ...},
        ],
      }

    `after` answers where the option group should render.
    `branches` captures per-option exclusive trunk ids until the first merge.
    `merge` names the first shared trunk after the branch split, when one
    exists inside the current linear path.
    """
    if conv_key in _DIALOG_TREE_CACHE:
        return _DIALOG_TREE_CACHE[conv_key]
    combined = {
        "after": {},
        "afterSources": {},
        "branches": {},
        "merge": {},
        "converge": {},
        "pre": [],
        "preSources": {},
        "lineIds": [],
        "sources": [],
        "cinematicFinishGroups": [],
    }
    tree_sources: list[dict] = []
    if meta := _load_dialog_tree_file(conv_key):
        tree_sources.append(meta)
    if not tree_sources or not any(
        (meta.get("lineIds") or [])
        or (meta.get("optionIds") or [])
        or (meta.get("pre") or [])
        or (meta.get("cinematicFinishGroups") or [])
        for meta in tree_sources
    ):
        for meta in _load_related_dialog_tree_files(conv_key):
            if any(existing.get("file") == meta.get("file") for existing in tree_sources):
                continue
            tree_sources.append(meta)
    tree_sources.extend(load_dialog_tree_fragments(conv_key))
    if extra_config := _load_dialog_tree_extra_config(conv_key):
        tree_sources.append(extra_config)

    seen_line_ids: set[str] = set()
    seen_cinematic_finish_groups: set[tuple[str, str, str]] = set()
    for meta in tree_sources:
        source_key = meta.get("sourceKey") or ""
        source_label = source_key or meta.get("file") or ""
        if source_key and source_key not in combined["sources"]:
            combined["sources"].append(source_key)
        for line_id in (meta.get("lineIds") or []):
            if line_id and line_id not in seen_line_ids:
                seen_line_ids.add(line_id)
                combined["lineIds"].append(line_id)
        for opt_id, after in (meta.get("after") or {}).items():
            combined["after"].setdefault(opt_id, after)
            if source_label:
                source_bucket = combined["afterSources"].setdefault(opt_id, [])
                if source_label not in source_bucket:
                    source_bucket.append(source_label)
        for opt_id, branch_lines in (meta.get("branches") or {}).items():
            combined["branches"].setdefault(opt_id, branch_lines)
        for opt_id, merge_id in (meta.get("merge") or {}).items():
            combined["merge"].setdefault(opt_id, merge_id)
        for opt_id, converge_trunk in (meta.get("converge") or {}).items():
            combined["converge"].setdefault(opt_id, converge_trunk)
        for opt_id in (meta.get("pre") or []):
            if opt_id and opt_id not in combined["pre"]:
                combined["pre"].append(opt_id)
            if opt_id and source_label:
                source_bucket = combined["preSources"].setdefault(opt_id, [])
                if source_label not in source_bucket:
                    source_bucket.append(source_label)
        for finish_group in (meta.get("cinematicFinishGroups") or []):
            if not isinstance(finish_group, dict):
                continue
            identity = (
                str(finish_group.get("sourceKey") or source_key),
                str(finish_group.get("timeline") or ""),
                str(finish_group.get("nodeId") or ""),
            )
            if identity in seen_cinematic_finish_groups:
                continue
            seen_cinematic_finish_groups.add(identity)
            combined["cinematicFinishGroups"].append(finish_group)

    _DIALOG_TREE_CACHE[conv_key] = combined if any(
        combined[key] for key in ("after", "branches", "merge", "converge")
    ) or combined["pre"] or combined["lineIds"] or combined["cinematicFinishGroups"] else None
    return _DIALOG_TREE_CACHE[conv_key]


def resolve_scene_line_order(conv_key: str, original_line_ids: list[str]) -> tuple[list[str], dict | None]:
    available_line_ids = [line_id for line_id in original_line_ids if line_id]
    available_set = set(available_line_ids)
    if not conv_key or not available_line_ids:
        return available_line_ids, None

    candidates: list[dict] = []
    tree_file = _load_dialog_tree_file(conv_key)

    def add_candidate(kind: str, source_key: str, file: str, line_ids: list[str], priority: int) -> None:
        matched = [line_id for line_id in line_ids if line_id in available_set]
        if not matched:
            return
        candidates.append({
            "kind": kind,
            "sourceKey": source_key,
            "file": file,
            "matchedLineIds": matched,
            "coverage": len(matched),
            "priority": priority,
        })

    if tree_file:
        add_candidate(
            "dialogTree",
            tree_file.get("sourceKey") or conv_key,
            tree_file.get("file") or "",
            tree_file.get("lineIds") or [],
            0,
        )
    direct_tree_coverage = max(
        (candidate["coverage"] for candidate in candidates if candidate["kind"] == "dialogTree"),
        default=0,
    )
    if not candidates or direct_tree_coverage < len(available_set):
        seen_candidate_files = {
            (candidate["sourceKey"], candidate["file"])
            for candidate in candidates
        }
        for meta in _load_related_dialog_tree_files(conv_key, available_line_ids):
            identity = (meta.get("sourceKey") or conv_key, meta.get("file") or "")
            if identity in seen_candidate_files:
                continue
            add_candidate(
                "dialogTree",
                meta.get("sourceKey") or conv_key,
                meta.get("file") or "",
                meta.get("lineIds") or [],
                0,
            )
            seen_candidate_files.add(identity)

    timeline_entries = load_dialog_timeline_line_orders(conv_key)
    for timeline in timeline_entries:
        add_candidate(
            "dialogTimeline",
            timeline.get("sourceKey") or timeline.get("timeline") or conv_key,
            timeline.get("file") or "",
            timeline.get("lineIds") or [],
            1,
        )

    def resolve_cinematic_timeline_stitch() -> tuple[list[str], dict] | None:
        if not tree_file:
            return None
        anchors = [
            anchor
            for anchor in (tree_file.get("cinematicTimelineAnchors") or [])
            if isinstance(anchor, dict) and anchor.get("timeline")
        ]
        if not anchors or not timeline_entries:
            return None
        tree_line_ids = [
            line_id
            for line_id in (tree_file.get("lineIds") or [])
            if line_id in available_set
        ]
        if not tree_line_ids:
            return None

        timeline_by_name: dict[str, list[dict]] = defaultdict(list)
        for entry in timeline_entries:
            for name in (
                str(entry.get("timeline") or ""),
                str(entry.get("sourceKey") or ""),
            ):
                if name and entry not in timeline_by_name[name]:
                    timeline_by_name[name].append(entry)

        inserted_by_after: dict[str, list[str]] = defaultdict(list)
        contributing_sources: list[dict] = [{
            "kind": "dialogTree",
            "sourceKey": tree_file.get("sourceKey") or conv_key,
            "file": tree_file.get("file") or "",
            "coverage": len(tree_line_ids),
            "matchedLineIds": tree_line_ids,
            "addedLineIds": list(tree_line_ids),
        }]
        used_anchor_details: list[dict] = []
        seen_line_ids: set[str] = set(tree_line_ids)
        for anchor in anchors:
            timeline_name = str(anchor.get("timeline") or "")
            after_line_id = str(anchor.get("after") or "")
            if not timeline_name or after_line_id not in tree_line_ids:
                continue
            for entry in timeline_by_name.get(timeline_name, []):
                matched = [
                    line_id
                    for line_id in (entry.get("lineIds") or [])
                    if line_id in available_set
                ]
                added = [line_id for line_id in matched if line_id not in seen_line_ids]
                if not added:
                    continue
                seen_line_ids.update(added)
                inserted_by_after[after_line_id].extend(added)
                contributing_sources.append({
                    "kind": "dialogTimeline",
                    "sourceKey": entry.get("sourceKey") or entry.get("timeline") or timeline_name,
                    "file": entry.get("file") or "",
                    "coverage": len(matched),
                    "matchedLineIds": matched,
                    "addedLineIds": added,
                })
                used_anchor_details.append({
                    "timeline": timeline_name,
                    "nodeId": str(anchor.get("nodeId") or ""),
                    "after": after_line_id,
                    "before": str(anchor.get("before") or ""),
                    "addedLineIds": added,
                })

        if not used_anchor_details:
            return None
        ordered: list[str] = []
        for line_id in tree_line_ids:
            if line_id not in ordered:
                ordered.append(line_id)
            for inserted_id in inserted_by_after.get(line_id, []):
                if inserted_id not in ordered:
                    ordered.append(inserted_id)
        if set(ordered) != available_set or len(ordered) != len(available_set):
            return None
        return ordered, {
            "mode": "dialogTreeCinematicTimeline",
            "originalLineIds": available_line_ids,
            "orderedLineIds": ordered,
            "sources": contributing_sources,
            "stitch": "dialogTreeCinematicAnchors",
            "cinematicTimelineAnchors": used_anchor_details,
        }

    if cinematic_stitch := resolve_cinematic_timeline_stitch():
        return cinematic_stitch

    for fragment in load_dialog_tree_fragments(conv_key):
        add_candidate(
            "dialogTreeFragment",
            fragment.get("sourceKey") or conv_key,
            fragment.get("file") or "",
            fragment.get("lineIds") or [],
            2,
        )

    if extra_config := _load_dialog_tree_extra_config(conv_key):
        add_candidate(
            "dialogTreeExtraConfig",
            extra_config.get("sourceKey") or conv_key,
            extra_config.get("file") or "",
            extra_config.get("lineIds") or [],
            3,
        )

    if not candidates:
        # Final fallback: if every line id ends in a unique numeric suffix
        # (the standard <conv_key>_<NNN> convention), use that ordering. This
        # covers cinematic scenes with no local DialogTree or Timeline asset
        # in the installed VFS, which otherwise leave the natural line order
        # undocumented.
        suffix_pairs: list[tuple[int, str]] = []
        for line_id in available_line_ids:
            match = re.search(r"_(\d+)$", line_id)
            if not match:
                suffix_pairs = []
                break
            suffix_pairs.append((int(match.group(1)), line_id))
        if suffix_pairs and len({pair[0] for pair in suffix_pairs}) == len(suffix_pairs):
            suffix_pairs.sort(key=lambda pair: pair[0])
            ordered = [line_id for _, line_id in suffix_pairs]
            return ordered, {
                "mode": "lineIdSuffix",
                "originalLineIds": available_line_ids,
                "orderedLineIds": ordered,
                "sources": [
                    {
                        "kind": "lineIdSuffix",
                        "sourceKey": conv_key,
                        "file": "",
                        "coverage": len(ordered),
                        "matchedLineIds": ordered,
                        "addedLineIds": ordered,
                    }
                ],
            }
        compound_suffix_pairs: list[tuple[int, int, str]] = []
        for line_id in available_line_ids:
            if not line_id.startswith("timeline_blackbox_"):
                compound_suffix_pairs = []
                break
            match = re.search(r"_(\d+)_(\d+)$", line_id)
            if not match:
                compound_suffix_pairs = []
                break
            compound_suffix_pairs.append((int(match.group(1)), int(match.group(2)), line_id))
        if (
            compound_suffix_pairs
            and len({(pair[0], pair[1]) for pair in compound_suffix_pairs}) == len(compound_suffix_pairs)
        ):
            compound_suffix_pairs.sort(key=lambda pair: (pair[0], pair[1], pair[2]))
            ordered = [line_id for _group, _step, line_id in compound_suffix_pairs]
            return ordered, {
                "mode": "compoundNumericSuffix",
                "originalLineIds": available_line_ids,
                "orderedLineIds": ordered,
                "sources": [
                    {
                        "kind": "compoundNumericSuffix",
                        "sourceKey": conv_key,
                        "file": "DialogTextTable.rowId",
                        "coverage": len(ordered),
                        "matchedLineIds": ordered,
                        "addedLineIds": ordered,
                    }
                ],
            }
        return available_line_ids, None

    candidates.sort(
        key=lambda item: (
            -item["coverage"],
            item["priority"],
            item["sourceKey"],
            item["file"],
        )
    )

    def line_suffix(line_id: str) -> int | None:
        match = re.search(r"_(\d+)$", line_id)
        return int(match.group(1)) if match else None

    def suffixes_are_strictly_monotonic(line_ids: list[str]) -> bool:
        suffixes = [line_suffix(line_id) for line_id in line_ids]
        if len(suffixes) < 2 or any(suffix is None for suffix in suffixes):
            return False
        numeric_suffixes = [int(suffix) for suffix in suffixes if suffix is not None]
        return len(set(numeric_suffixes)) == len(numeric_suffixes) and numeric_suffixes == sorted(numeric_suffixes)

    def all_available_line_suffixes_unique() -> bool:
        suffixes = [line_suffix(line_id) for line_id in available_line_ids]
        return (
            bool(suffixes)
            and all(suffix is not None for suffix in suffixes)
            and len(set(suffixes)) == len(suffixes)
        )

    def suffix_sorted_available_line_ids() -> list[str]:
        return [
            line_id
            for _suffix, line_id in sorted(
                ((line_suffix(line_id), line_id) for line_id in available_line_ids),
                key=lambda item: (item[0], item[1]),
            )
        ]

    def merge_uncovered_line_ids(ordered_ids: list[str], uncovered_ids: list[str]) -> list[str]:
        if not uncovered_ids:
            return ordered_ids
        suffixes = [line_suffix(line_id) for line_id in ordered_ids]
        numeric_suffixes = [suffix for suffix in suffixes if suffix is not None]
        if not numeric_suffixes:
            return [*ordered_ids, *uncovered_ids]

        min_suffix = min(numeric_suffixes)
        max_suffix = max(numeric_suffixes)
        prefix: list[tuple[int, str]] = []
        suffix: list[tuple[int, str]] = []
        unresolved: list[str] = []
        for line_id in uncovered_ids:
            suffix_num = line_suffix(line_id)
            if suffix_num is None:
                unresolved.append(line_id)
            elif suffix_num < min_suffix:
                prefix.append((suffix_num, line_id))
            elif suffix_num > max_suffix:
                suffix.append((suffix_num, line_id))
            else:
                # In-range holes are ambiguous once an authored source has
                # reordered the scene, so keep the old conservative tail
                # behavior for those.
                unresolved.append(line_id)
        prefix.sort(key=lambda item: item[0])
        suffix.sort(key=lambda item: item[0])
        return [
            *(line_id for _suffix, line_id in prefix),
            *ordered_ids,
            *unresolved,
            *(line_id for _suffix, line_id in suffix),
        ]

    ordered_line_ids: list[str] = []
    seen_line_ids: set[str] = set()
    contributing_sources: list[dict] = []
    for candidate in candidates:
        added_line_ids: list[str] = []
        for line_id in candidate["matchedLineIds"]:
            if line_id not in seen_line_ids:
                seen_line_ids.add(line_id)
                ordered_line_ids.append(line_id)
                added_line_ids.append(line_id)
        if added_line_ids:
            contributing_sources.append({
                **candidate,
                "addedLineIds": added_line_ids,
            })
    uncovered_line_ids = [
        line_id for line_id in available_line_ids
        if line_id not in seen_line_ids
    ]
    ordered_line_ids = merge_uncovered_line_ids(ordered_line_ids, uncovered_line_ids)
    numeric_stitch = False
    if (
        contributing_sources
        and contributing_sources[0]["kind"] == "dialogTree"
        and contributing_sources[0]["coverage"] < len(available_set)
        and suffixes_are_strictly_monotonic(contributing_sources[0]["matchedLineIds"])
        and all_available_line_suffixes_unique()
    ):
        stitched_ids = suffix_sorted_available_line_ids()
        if set(stitched_ids) == available_set:
            ordered_line_ids = stitched_ids
            numeric_stitch = True

    debug = {
        "mode": (
            "authoredNumericStitch"
            if numeric_stitch
            else ("authoredBlend" if len(contributing_sources) > 1 else contributing_sources[0]["kind"])
        ),
        "originalLineIds": available_line_ids,
        "orderedLineIds": ordered_line_ids,
        "sources": [
            {
                "kind": candidate["kind"],
                "sourceKey": candidate["sourceKey"],
                "file": candidate["file"],
                "coverage": candidate["coverage"],
                "matchedLineIds": candidate["matchedLineIds"],
                "addedLineIds": candidate["addedLineIds"],
            }
            for candidate in contributing_sources
        ],
    }
    if numeric_stitch:
        debug["stitch"] = "lineIdSuffixGaps"
    return ordered_line_ids, debug


def _filter_dialog_tree_line_graph_for_scene(graph: dict, conv_key: str, available_line_ids: set[str]) -> dict:
    nodes = [node for node in (graph.get("nodes") or []) if isinstance(node, dict) and node.get("id")]
    edges = [edge for edge in (graph.get("edges") or []) if isinstance(edge, dict)]
    if not nodes:
        return {}
    by_id = {str(node.get("id")): node for node in nodes}

    def node_scene_signal(node: dict) -> bool:
        line_id = str(node.get("lineId") or "")
        if line_id and (line_id in available_line_ids or _dialog_tree_scene_prefix(line_id) == conv_key):
            return True
        for option_id in node.get("optionIds") or []:
            if _dialog_tree_option_prefix(str(option_id or "")) == conv_key:
                return True
        return False

    included = {node_id for node_id, node in by_id.items() if node_scene_signal(node)}
    if not included:
        return {
            "nodes": nodes,
            "edges": edges,
        }

    def is_connector(node_id: str) -> bool:
        node = by_id.get(node_id) or {}
        return not node.get("lineId") and not node.get("optionIds")

    changed = True
    while changed:
        changed = False
        for edge in edges:
            src = str(edge.get("from") or "")
            dst = str(edge.get("to") or "")
            if not src or not dst:
                continue
            if src in included and dst not in included and is_connector(dst):
                included.add(dst)
                changed = True
            if dst in included and src not in included and is_connector(src):
                included.add(src)
                changed = True

    return {
        "nodes": [node for node in nodes if str(node.get("id") or "") in included],
        "edges": [
            edge
            for edge in edges
            if str(edge.get("from") or "") in included and str(edge.get("to") or "") in included
        ],
    }


def build_dialog_tree_line_graph_payload(conv_key: str, original_line_ids: list[str]) -> dict | None:
    available_line_ids = {line_id for line_id in original_line_ids if line_id}
    sources: list[dict] = []
    seen_sources: set[tuple[str, str, str]] = set()
    covered_line_ids: set[str] = set()
    covered_option_ids: set[str] = set()

    def add_source(meta: dict | None, kind: str, require_new_signal: bool = False) -> bool:
        if not meta:
            return False
        graph = meta.get("lineGraph") or {}
        if not graph.get("nodes"):
            return False
        source_key = meta.get("sourceKey") or ""
        file = meta.get("file") or ""
        identity = (kind, source_key, file)
        if identity in seen_sources:
            return False
        filtered_graph = _filter_dialog_tree_line_graph_for_scene(graph, conv_key, available_line_ids)
        if not filtered_graph.get("nodes"):
            return False
        scene_line_ids = _unique_preserve([
            str(node.get("lineId") or "")
            for node in filtered_graph.get("nodes") or []
            if str(node.get("lineId") or "") in available_line_ids
            or _dialog_tree_scene_prefix(str(node.get("lineId") or "")) == conv_key
        ])
        scene_option_ids = _unique_preserve([
            str(option_id or "")
            for node in filtered_graph.get("nodes") or []
            for option_id in (node.get("optionIds") or [])
            if _dialog_tree_option_prefix(str(option_id or "")) == conv_key
        ])
        if not scene_line_ids and not scene_option_ids and source_key != conv_key:
            return False
        if require_new_signal and not (
            any(line_id not in covered_line_ids for line_id in scene_line_ids)
            or any(option_id not in covered_option_ids for option_id in scene_option_ids)
        ):
            return False
        seen_sources.add(identity)
        covered_line_ids.update(scene_line_ids)
        covered_option_ids.update(scene_option_ids)
        source_payload = {
            "kind": kind,
            "sourceKey": source_key,
            "file": file,
            "nodes": filtered_graph.get("nodes") or [],
            "edges": filtered_graph.get("edges") or [],
        }
        if scene_line_ids:
            source_payload["lineIds"] = scene_line_ids
        if scene_option_ids:
            source_payload["optionIds"] = scene_option_ids
        sources.append(source_payload)
        return True

    direct_added = add_source(_load_dialog_tree_file(conv_key), "dialogTree")
    if direct_added and (not available_line_ids or available_line_ids.issubset(covered_line_ids)):
        return {"sources": sources}
    for meta in _load_related_dialog_tree_files(conv_key, original_line_ids):
        add_source(meta, "dialogTree", require_new_signal=True)
    for fragment in load_dialog_tree_fragments(conv_key):
        source_key = fragment.get("sourceKey") or ""
        if source_key:
            add_source(_load_dialog_tree_source(source_key), "dialogTreeFragment", require_new_signal=True)

    if not sources:
        return None
    return {"sources": sources}


def build_dialog_tree_fragment_payload(conv_key: str) -> list[dict]:
    fragments = load_dialog_tree_fragments(conv_key)
    out: list[dict] = []
    for fragment in fragments:
        option_groups: list[dict] = []
        if fragment.get("optionGroups"):
            for raw_group in fragment.get("optionGroups") or []:
                group = {
                    "optionIds": raw_group.get("optionIds") or [],
                }
                if raw_group.get("after"):
                    group["after"] = raw_group["after"]
                if raw_group.get("mode"):
                    group["mode"] = raw_group["mode"]
                if raw_group.get("branches"):
                    group["branches"] = raw_group["branches"]
                if raw_group.get("merge"):
                    group["merge"] = raw_group["merge"]
                if raw_group.get("position"):
                    group["position"] = raw_group["position"]
                if raw_group.get("_debug"):
                    group["_debug"] = raw_group["_debug"]
                option_groups.append(group)
        else:
            grouped_option_ids: dict[str, list[str]] = defaultdict(list)
            for opt_id, after in (fragment.get("after") or {}).items():
                if after:
                    grouped_option_ids[after].append(opt_id)
            for after in sorted(grouped_option_ids):
                opt_ids = _unique_preserve(grouped_option_ids[after])
                group = {
                    "after": after,
                    "optionIds": opt_ids,
                }
                branch_map = {
                    opt_id: fragment["branches"][opt_id]
                    for opt_id in opt_ids
                    if opt_id in (fragment.get("branches") or {})
                }
                if branch_map:
                    group["branches"] = branch_map
                merge_map = {
                    opt_id: fragment["merge"][opt_id]
                    for opt_id in opt_ids
                    if opt_id in (fragment.get("merge") or {})
                }
                if merge_map:
                    group["merge"] = merge_map
                option_groups.append(group)

            pre_opt_ids = [
                opt_id
                for opt_id in (fragment.get("pre") or [])
                if opt_id and opt_id not in (fragment.get("after") or {})
            ]
            if pre_opt_ids:
                option_groups.append({
                    "position": "pre",
                    "optionIds": _unique_preserve(pre_opt_ids),
                })

        out.append({
            "sourceKey": fragment.get("sourceKey") or "",
            "file": fragment.get("file") or "",
            "lineIds": fragment.get("lineIds") or [],
            "optionGroups": option_groups,
            "terminalCounts": fragment.get("terminalCounts") or {},
            "sceneSpan": bool(fragment.get("sceneSpan")),
            "sourceSceneKeys": fragment.get("sourceSceneKeys") or [],
            "_debug": {
                "source": {
                    "targetKey": conv_key,
                    "sourceKey": fragment.get("sourceKey") or "",
                    "file": fragment.get("file") or "",
                },
            },
        })
    return out


def build_dialog_tree_scene_link_payload(conv_key: str) -> list[dict]:
    links = load_dialog_tree_scene_links(conv_key)
    out: list[dict] = []
    for link in links:
        options: list[dict] = []
        seen_option_entries: set[str] = set()
        for opt in link.get("options") or []:
            entry = {
                "optionId": opt.get("optionId") or "",
            }
            for key in ("firstLineId", "firstSceneKey", "terminal"):
                if opt.get(key):
                    entry[key] = opt[key]
            for key in ("pathLineIds", "sceneKeys", "submenuSceneKeys"):
                if opt.get(key):
                    entry[key] = opt[key]
            if opt.get("outcomeKind"):
                entry["outcomeKind"] = opt["outcomeKind"]
            if opt.get("loop"):
                entry["loop"] = opt["loop"]
            if opt.get("_debug"):
                entry["_debug"] = opt["_debug"]
            signature = json.dumps(entry, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
            if signature in seen_option_entries:
                continue
            seen_option_entries.add(signature)
            options.append(entry)
        out.append({
            "sourceKey": link.get("sourceKey") or "",
            "file": link.get("file") or "",
            "after": link.get("after") or "",
            "options": options,
            "sceneSpan": bool(link.get("sceneSpan")),
            "sourceSceneKeys": link.get("sourceSceneKeys") or [],
            "_debug": {
                "source": {
                    "targetKey": conv_key,
                    "sourceKey": link.get("sourceKey") or "",
                    "file": link.get("file") or "",
                },
                "link": link.get("_debug") or {},
            },
        })
    return out


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build localized webui data bundles from exported tables."
    )
    parser.add_argument(
        "--languages",
        nargs="*",
        help=(
            "Language codes to build. Accepts space- or comma-separated values. "
            f"Defaults to {DEFAULT_LANGUAGE} only."
        ),
    )
    parser.add_argument(
        "--default-language",
        default=DEFAULT_LANGUAGE,
        help=f"Default language for the web UI manifest (default: {DEFAULT_LANGUAGE}).",
    )
    parser.add_argument(
        "--profile",
        choices=BUILD_PROFILES,
        default=DEFAULT_BUILD_PROFILE,
        help=(
            "`lean` keeps generic table translations out of the story index and "
            "writes them to reference/ instead. `full` preserves the older "
            "story-index collection pages."
        ),
    )
    parser.add_argument(
        "--skip-reference",
        action="store_true",
        help="Do not write the raw localized table reference bundle.",
    )
    parser.add_argument(
        "--timeline-recovery",
        choices=TIMELINE_RECOVERY_MODES,
        default="auto",
        help=(
            "`auto` runs Timeline line-order recovery only when the recovered "
            "index is missing or stale; `always` treats recovery failures as "
            "fatal; `never` skips the recovery step."
        ),
    )
    parser.add_argument(
        "--force-timeline-recovery",
        action="store_true",
        help="Re-extract Timeline assets even if the recovered line-order index is current.",
    )
    return parser.parse_args(argv)


def discover_languages() -> list[str]:
    found: list[str] = []
    for table_dir in _existing_unique_paths([STREAMING_TABLE_DIR, PERSISTENT_TABLE_DIR]):
        for path in table_dir.glob("I18nTextTable_*.json"):
            match = I18N_FILE_RE.match(path.name)
            if match:
                found.append(match.group(1))
    return sorted(set(found))


def normalize_language_selection(raw_values: list[str] | None, available: list[str]) -> list[str]:
    if not raw_values:
        if DEFAULT_LANGUAGE in available:
            return [DEFAULT_LANGUAGE]
        return available

    selected: list[str] = []
    for raw in raw_values:
        for part in raw.split(","):
            code = part.strip().upper()
            if not code or code in selected:
                continue
            selected.append(code)

    unknown = [code for code in selected if code not in available]
    if unknown:
        raise SystemExit(
            "Unknown language code(s): "
            + ", ".join(unknown)
            + "\nAvailable: "
            + ", ".join(available)
        )
    return selected


def language_info(code: str) -> dict:
    info = LANGUAGE_INFO.get(code, {})
    return {
        "code": code,
        "label": info.get("label", code),
        "nativeLabel": info.get("nativeLabel", info.get("label", code)),
        "htmlLang": info.get("htmlLang", code.lower()),
        "uiLocale": info.get("uiLocale", "en"),
    }


def load(name: str) -> dict:
    path = TABLE_DIR / name
    print(f"  loading {name} ({path.stat().st_size/1024/1024:.1f} MB)")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_optional_table_json(table_dir: Path, name: str, label: str | None = None) -> dict:
    path = table_dir / name
    if not path.exists():
        return {}
    return load_json_path(path, label or name)


def load_json_path(path: Path, label: str | None = None) -> dict:
    cache_key = str(path)
    if cache_key in _JSON_FILE_CACHE:
        return _JSON_FILE_CACHE[cache_key]
    name = label or path.name
    print(f"  loading {name} ({path.stat().st_size/1024/1024:.1f} MB)")
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    _JSON_FILE_CACHE[cache_key] = data if isinstance(data, dict) else {}
    return _JSON_FILE_CACHE[cache_key]


def load_json_path_uncached(path: Path, label: str | None = None) -> dict:
    name = label or path.name
    print(f"  loading {name} ({path.stat().st_size/1024/1024:.1f} MB)")
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def load_story_source_links() -> dict[str, list[dict]]:
    """Load or build the language-independent story source-link index."""
    if not STORY_SOURCE_LINKS_PATH.exists():
        print("  building story source links")
        build_story_source_links(output=STORY_SOURCE_LINKS_PATH)
    if not STORY_SOURCE_LINKS_PATH.exists():
        return {}
    try:
        payload = load_json_path_uncached(STORY_SOURCE_LINKS_PATH, "story_source_links.json")
    except (OSError, json.JSONDecodeError):
        return {}
    links = payload.get("links") if isinstance(payload, dict) else {}
    if not isinstance(links, dict):
        return {}
    return {
        str(key): rows
        for key, rows in links.items()
        if key and isinstance(rows, list)
    }


def parse_mission(mission: str) -> tuple[str, int]:
    """Split 'a1m6d1' -> ('a', 1); 'c13m2d5' -> ('c', 13)."""
    if mission.startswith("blackbox"):
        return ("timeline", 0)
    if mission.startswith("sr_"):
        return ("f", 0)
    m = TYPE_RE.match(mission)
    if not m:
        return ("?", 0)
    return (m.group(1), int(m.group(2)) if m.group(2) else 0)


def scene_sort_value(scene: str | int) -> int:
    if isinstance(scene, int):
        return scene
    lead = re.match(r"\d+", str(scene or ""))
    return int(lead.group()) if lead else 0


# Map misc export buckets into browser mission nodes. Mission-shaped `dlg_*`
# buckets are slotted back into their real story missions/scenes, while broad
# utility buckets like `sim_*` and `timeline_*` are promoted to their own
# top-level tags with coarse mission labels underneath.
def slot_misc(bucket: str) -> tuple[str, int, str, int]:
    """Slot a misc bucket key into the mission timeline.

    Returns (type, act, mission, scene_num) used by the index. Many "misc"
    dialogs (e.g. `dlg_c13m3_3d5_001`) actually belong to a real story mission
    — they fail the strict DLG_RE only because the scene token contains a
    sub-scene like `3d5`. Slot them next to the regular dialogs/SNS so the
    user finds them in context. KIND_ORDER in app.js keeps them visually after
    sns/dlg within the same scene.

    Broad utility buckets are promoted to their own top-level tags. `sim_*`
    buckets become the "帝江号" tag with coarse child groups like `gift` and
    `talk`, while `timeline_*` buckets become the "模拟空间" tag and keep the
    remainder of the bucket key as their mission label.
    """
    if bucket.startswith("sim_"):
        rest = bucket[len("sim_"):]
        family = rest.split("_", 1)[0] if rest else "sim"
        return ("sim", 0, family, 0)
    if bucket.startswith("timeline_"):
        rest = bucket[len("timeline_"):]
        return ("timeline", 0, rest or "timeline", 0)
    if bucket.startswith("sr_"):
        return ("f", 0, bucket, 0)
    if bucket.startswith("dlg_"):
        rest = bucket[len("dlg_"):]
        m = MISC_BUCKET_RE.match(rest)
        if m:
            mission, scene_str = m.group(1), m.group(2)
            type_, act = parse_mission(mission)
            if type_ != "?":
                return (type_, act, mission, scene_sort_value(scene_str))
        type_, act = parse_mission(rest)
        if type_ != "?":
            return (type_, act, rest, 0)
    return ("x", 0, bucket, 0)


def preview(text: str, n: int = 60) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:n]


def build_language_bundle(
    language_code: str,
    out_dir: Path,
    *,
    profile: str = DEFAULT_BUILD_PROFILE,
    write_reference: bool = True,
) -> dict:
    if profile not in BUILD_PROFILES:
        raise ValueError(f"unknown build profile: {profile}")
    include_reference_in_story_index = profile == "full"
    i18n_table_name = f"I18nTextTable_{language_code}.json"
    i18n_table_key = i18n_table_name.removesuffix(".json")
    t0 = time.time()
    conv_dir = out_dir / "conv"
    reference_dir = out_dir / "reference"
    mission_dir = out_dir / "mission"
    out_dir.mkdir(parents=True, exist_ok=True)
    conv_dir.mkdir(parents=True, exist_ok=True)
    dialog_id_registry = shared_load_dialog_id_registry()
    story_source_links = load_story_source_links()
    narrative_video_assets = _load_narrative_video_assets()

    # Wipe old conv files so renamed/removed groups don't linger.
    for old in conv_dir.glob("*.json"):
        old.unlink()
    shutil.rmtree(reference_dir, ignore_errors=True)
    shutil.rmtree(mission_dir, ignore_errors=True)

    print(f"\n[{language_code}] Loading tables...")
    i18n_by_source = {
        "streaming": load(i18n_table_name),
        "persistent": load_optional_table_json(
            PERSISTENT_TABLE_DIR,
            i18n_table_name,
            f"Persistent/{i18n_table_name}",
        ),
    }

    def apply_i18n_hotfixes() -> dict[str, dict[str, int]]:
        hotfix_type = I18N_HOTFIX_LANGUAGE_TYPES.get(language_code)
        stats: dict[str, dict[str, int]] = {}
        if hotfix_type is None:
            return stats

        for source_name, table_dir in (
            ("streaming", STREAMING_TABLE_DIR),
            ("persistent", PERSISTENT_TABLE_DIR),
        ):
            target = i18n_by_source.get(source_name)
            if not isinstance(target, dict):
                continue
            hotfix_rows = load_optional_table_json(
                table_dir,
                I18N_HOTFIX_TABLE,
                f"{source_name}/{I18N_HOTFIX_TABLE}",
            )
            patched = 0
            added = 0
            for row_id, row in hotfix_rows.items():
                if not isinstance(row, dict):
                    continue
                for item in row.get("list") or []:
                    if not isinstance(item, dict):
                        continue
                    if item.get("type") != hotfix_type:
                        continue
                    text = item.get("text")
                    if text is None:
                        continue
                    text_id = str(item.get("id") or row_id)
                    if not text_id:
                        continue
                    if text_id not in target:
                        added += 1
                    target[text_id] = str(text)
                    patched += 1
            if patched or added:
                stats[source_name] = {"patched": patched, "added": added}
        return stats

    hotfix_stats = apply_i18n_hotfixes()
    if hotfix_stats:
        summary = ", ".join(
            f"{source}: {row['patched']} patched ({row['added']} new)"
            for source, row in sorted(hotfix_stats.items())
        )
        print(f"  applied {I18N_HOTFIX_TABLE}: {summary}")

    text_table = load("TextTable.json")
    dialogs = load("DialogTextTable.json")
    sns = load("SNSDialogTable.json")
    sns_chats = load("SNSChatTable.json")
    sns_opts = load("SNSDialogOptionTable.json")
    sns_topics = load("SNSDialogTopicTable.json")
    dlg_opts = load("DialogOptionTable.json")
    summaries = load("DialogSummaryTable.json")
    mission_extra_info = load("MissionExtraInfoTable.json")
    dungeons = load("DungeonTable.json")
    skill_patches = load("SkillPatchTable.json")
    char_growth = load("CharGrowthTable.json")
    game_mechanics = load("GameMechanicTable.json")
    loading_tips = load("LoadingTipsTable.json")
    error_codes = load("ErrorCodeTable.json")
    achievements = load("AchievementTable.json")
    achievement_types = load("AchievementTypeTable.json")
    mail_senders = load("MailSenderTable.json")
    mail_templates = load("MailTemplateTable.json")
    character_rows = load("CharacterTable.json")
    item_rows = load("ItemTable.json")
    weapon_basic = load("WeaponBasicTable.json")
    enemy_display_info = load("EnemyDisplayInfoTable.json")
    enemy_template_display = load("EnemyTemplateDisplayInfoTable.json")
    enemy_ability_desc = load("EnemyAbilityDescTable.json")
    npc_rows = load("NpcTable.json")
    npc_templates = load("NpcTemplateGroupTable.json")
    npc_proxy_rows = load_json_path(NPC_PROXY_TABLE_PATH, "NpcProxyTable.json").get("dataTable") or {}
    npc_proxy_ex = _load_npc_proxy_ex()
    npc_proxy_info = npc_proxy_ex.get("proxyInfoData") or {}
    npc_proxy_info = npc_proxy_info if isinstance(npc_proxy_info, dict) else {}
    atmos_cluster_rows = load_json_path(
        ATMOS_CLUSTER_TABLE_PATH, "AtmosphericNpcClusterDataTable.json"
    ).get("dataTable") or {}
    radios = load("RadioTable.json")
    remote_common = load("RemoteCommonTable.json")
    env_talks = load("EnvTalkTable.json")
    ai_bark_text = load("AIBarkText.json")
    audio_dialog = load("AudioDialog.json")
    responsive_dialog = load("ResponsiveDialog.json")
    rich_content = load("RichContentTable.json")
    prts_all_items = load("PrtsAllItem.json")
    prts_first_lv = load("PrtsFirstLv.json")
    prts_page = load("PrtsPage.json")
    prts_notes = load("PrtsNote.json")
    prts_categories = load("PrtsCategory.json")
    prts_investigate_categories = load("PrtsInvestigateCategory.json")
    wiki_categories = load("WikiCategoryTable.json")
    wiki_groups = load("WikiGroupTable.json")
    wiki_entry_data = load("WikiEntryDataTable.json")
    wiki_tutorial_pages = load("WikiTutorialPageTable.json")
    wiki_tutorial_pages_by_entry = load("WikiTutorialPageByEntryTable.json")
    wiki_craft_jump = load("WikiCraftJumpTable.json")
    wiki_default_craft = load("WikiDefaultCraftTable.json")

    def norm_id(id_value) -> str:
        if id_value is None:
            return ""
        s = str(id_value)
        return "" if s == "0" else s

    def t(id_value, preferred_source: str = "streaming") -> str:
        s = norm_id(id_value)
        if not s:
            return ""
        lookup_order = [preferred_source]
        for source_name in ("streaming", "persistent"):
            if source_name not in lookup_order:
                lookup_order.append(source_name)
        for source_name in lookup_order:
            text = (i18n_by_source.get(source_name) or {}).get(s, "")
            if text:
                return text
        return ""

    def pick_fields(obj: dict | None, *keys: str) -> dict:
        if not obj:
            return {}
        return {k: obj.get(k) for k in keys if k in obj}

    referenced_texttable_row_ids: set[str] = set()

    def remember_texttable_row_usage(row_id) -> None:
        row_key = str(row_id or "").strip()
        if row_key:
            referenced_texttable_row_ids.add(row_key)

    def text_trace(
        table: str,
        row_id: str,
        field: str,
        raw_value,
        *,
        preferred_source: str = "streaming",
        transform: str = "",
    ) -> dict:
        i18n_id = norm_id(raw_value.get("id") if isinstance(raw_value, dict) else raw_value)
        resolved = t(i18n_id, preferred_source=preferred_source)
        trace = {
            "table": table,
            "rowId": row_id,
            "field": field,
            "raw": raw_value,
            "lookup": [],
            "text": resolved,
        }
        if preferred_source != "streaming":
            trace["preferredSource"] = preferred_source
        if i18n_id:
            trace["lookup"].append({
                "from": f"{table}[{row_id}].{field}",
                "value": i18n_id,
            })
            trace["lookup"].append({
                "from": f"{i18n_table_key}[{i18n_id}]",
                "value": resolved,
            })
        if transform:
            trace["transform"] = transform
        return trace

    def named_text_trace(table: str, row_id: str, field: str, raw_value) -> dict:
        trace = text_trace(table, row_id, field, raw_value)
        trace["braceText"] = brace_text(trace["text"])
        if trace["text"]:
            trace["lookup"].append({
                "from": f"brace_text({field})",
                "value": trace["braceText"],
            })
        return trace

    def source_ref(table: str, row_id: str, source: dict, **extra) -> dict:
        out = {
            "table": table,
            "rowId": row_id,
            "source": source,
        }
        for k, v in extra.items():
            if v not in (None, "", [], {}):
                out[k] = v
        return out

    def rich_content_trace(row_id: str, field: str, raw_value) -> dict:
        return text_trace("RichContentTable", row_id, field, raw_value)

    def rich_content_title_text(content_id: str) -> str:
        row = rich_content.get(content_id)
        if not isinstance(row, dict):
            return ""
        return t((row.get("title") or {}).get("id"))

    def rich_content_lines(content_id: str) -> list[dict]:
        row = rich_content.get(content_id)
        if not isinstance(row, dict):
            return []
        out: list[dict] = []
        for idx, item in enumerate(row.get("contentList") or [], start=1):
            content = (item or {}).get("content") or {}
            text = t(content.get("id"))
            out.append({
                "id": f"{content_id}_{idx}",
                "text": text,
                "_debug": {
                    **source_ref(
                        "RichContentTable.contentList",
                        content_id,
                        pick_fields(item, "content"),
                        nodeId=idx,
                    ),
                    "fields": {
                        "text": rich_content_trace(content_id, "content", content),
                    },
                },
            })
        return out

    def inline_image_tag(image_id: str) -> str:
        clean = str(image_id or "").strip()
        return f'<image="{clean}">' if clean else ""

    def sns_media_text_from_params(params) -> str:
        image_ids = [
            str(value or "").strip()
            for value in (params or [])
            if str(value or "").strip()
        ]
        if not image_ids:
            return ""

        if len(image_ids) == 2:
            by_gender: dict[str, str] = {}
            for image_id in image_ids:
                lower = image_id.lower()
                if lower.endswith("_m"):
                    by_gender["M"] = image_id
                elif lower.endswith("_f"):
                    by_gender["F"] = image_id
            if by_gender.get("M") and by_gender.get("F"):
                return (
                    f'{{M}}{inline_image_tag(by_gender["M"])}'
                    f'{{F}}{inline_image_tag(by_gender["F"])}'
                )

        return " ".join(inline_image_tag(image_id) for image_id in image_ids)

    def sns_content_text(node: dict) -> str:
        text = t(node.get("content", {}).get("id"))
        if text:
            return text
        if node.get("contentType") == 2:
            return sns_media_text_from_params(node.get("contentParam"))
        return ""

    def sns_option_display_text(opt: dict) -> str:
        text = t(opt.get("optionDesc", {}).get("id"))
        if text:
            return text
        res_path = str(opt.get("optionResPath") or "").strip()
        if res_path:
            return inline_image_tag(res_path)
        return ""

    def text_sequence_fingerprint(nodes: list[dict]) -> tuple[str, ...]:
        rows: list[str] = []
        for node in nodes:
            text = re.sub(r"\s+", " ", str(node.get("text") or "")).strip()
            if text:
                rows.append(text)
        return tuple(rows)

    def brace_text(text: str) -> str:
        """Return the content inside the first {...} when present."""
        if not text:
            return ""
        m = re.search(r"\{([^{}]+)\}", text)
        return m.group(1) if m else text

    def sns_raw_title(out_key: str) -> str:
        """Show `foo_...` instead of the stored `sns_foo_...` key."""
        return out_key[4:] if out_key.startswith("sns_") else out_key

    mission_name_cache: dict[str, str] = {}
    chat_name_cache: dict[str, str] = {}
    topic_name_cache: dict[str, str] = {}
    topic_id_cache: dict[str, str] = {}
    blackbox_title_cache: dict[str, str] = {}
    topic_base_index: dict[str, list[str]] = defaultdict(list)
    blackbox_base_titles: dict[str, list[dict]] = defaultdict(list)
    blackbox_exact_titles: dict[str, dict] = {}
    for topic_key in sns_topics:
        base_key = re.sub(r"_\d+$", "", topic_key)
        topic_base_index[base_key].append(topic_key)
    for topic_ids in topic_base_index.values():
        topic_ids.sort(key=lambda key: [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", key)])

    def normalize_blackbox_id(value: str) -> str:
        mission_id = re.sub(r"\s+", "", value or "")
        alias_prefixes = {
            "blackbox_storage": "blackbox_storager",
            "blackbox_xiranite_oven": "blackbox_xiraniteoven",
        }
        for src, dst in alias_prefixes.items():
            if mission_id == src or mission_id.startswith(f"{src}_"):
                return f"{dst}{mission_id[len(src):]}"
        return mission_id

    for dungeon_id, row in dungeons.items():
        scene_id = normalize_blackbox_id(str(row.get("sceneId") or ""))
        if not scene_id.startswith("blackbox_"):
            continue
        title = brace_text(t((row.get("dungeonName") or {}).get("id")))
        if not title:
            continue
        info = {
            "dungeonId": dungeon_id,
            "sceneId": scene_id,
            "title": title,
            "row": row,
        }
        blackbox_exact_titles[scene_id] = info
        blackbox_base_titles[re.sub(r"_\d+$", "", scene_id)].append(info)

    def mission_name(mission_id: str) -> str:
        """Resolve a mission id like `a1m6d3` to a localized display name."""
        if not mission_id:
            return ""
        if mission_id in mission_name_cache:
            return mission_name_cache[mission_id]
        if mission_id.startswith("topic_"):
            chat_id = mission_chat_id(mission_id)
            if chat_id:
                name = chat_name(chat_id)
                mission_name_cache[mission_id] = name
                return name
        row = text_table.get(f"{mission_id}_name")
        if row:
            remember_texttable_row_usage(f"{mission_id}_name")
            name = brace_text(t(row.get("id")))
            mission_name_cache[mission_id] = name
            return name
        normalized_blackbox_id = normalize_blackbox_id(mission_id)
        if normalized_blackbox_id.startswith("blackbox_"):
            if normalized_blackbox_id in blackbox_title_cache:
                name = blackbox_title_cache[normalized_blackbox_id]
                mission_name_cache[mission_id] = name
                return name
            if exact := blackbox_exact_titles.get(normalized_blackbox_id):
                name = exact["title"]
                blackbox_title_cache[normalized_blackbox_id] = name
                mission_name_cache[mission_id] = name
                return name
            titles = [info["title"] for info in blackbox_base_titles.get(normalized_blackbox_id, [])]
            if titles:
                name = " / ".join(dict.fromkeys(titles))
                blackbox_title_cache[normalized_blackbox_id] = name
                mission_name_cache[mission_id] = name
                return name
        mission_name_cache[mission_id] = ""
        return ""

    def mission_name_trace(mission_id: str) -> dict | None:
        if not mission_id:
            return None
        if mission_id.startswith("topic_"):
            chat_id = mission_chat_id(mission_id)
            if chat_id:
                trace = chat_name_trace(chat_id)
                if trace:
                    trace = dict(trace)
                    trace["source"] = dict(trace.get("source") or {})
                    trace["source"]["derivedMissionId"] = mission_id
                    return trace
        row_id = f"{mission_id}_name"
        row = text_table.get(row_id)
        if row:
            remember_texttable_row_usage(row_id)
            return {
                **source_ref("TextTable", row_id, pick_fields(row, "id")),
                "value": brace_text(t(row.get("id"))),
                "trace": named_text_trace("TextTable", row_id, "id", row.get("id")),
            }
        normalized_blackbox_id = normalize_blackbox_id(mission_id)
        if not normalized_blackbox_id.startswith("blackbox_"):
            return None
        if exact := blackbox_exact_titles.get(normalized_blackbox_id):
            return {
                **source_ref(
                    "DungeonTable",
                    exact["dungeonId"],
                    pick_fields(exact["row"], "sceneId", "dungeonName"),
                    normalizedMissionId=normalized_blackbox_id,
                ),
                "value": exact["title"],
                "trace": named_text_trace(
                    "DungeonTable",
                    exact["dungeonId"],
                    "dungeonName",
                    (exact["row"].get("dungeonName") or {}),
                ),
            }
        infos = blackbox_base_titles.get(normalized_blackbox_id, [])
        if not infos:
            return None
        titles = [info["title"] for info in infos]
        return {
            "table": "DungeonTable",
            "rowId": normalized_blackbox_id,
            "source": {
                "normalizedMissionId": normalized_blackbox_id,
                "variants": [
                    {
                        "dungeonId": info["dungeonId"],
                        "sceneId": info["sceneId"],
                        "title": info["title"],
                    }
                    for info in infos
                ],
            },
            "value": " / ".join(dict.fromkeys(titles)),
            "trace": {
                "raw": titles,
                "lookup": [
                    {
                        "from": f"DungeonTable[{info['dungeonId']}].dungeonName",
                        "value": info["title"],
                    }
                    for info in infos
                ],
            },
        }

    def resolve_topic_id(topic_id: str) -> str:
        """Resolve base SNS topic ids like `topic_chr_0004_pelica` to a table row."""
        if not topic_id:
            return ""
        if topic_id in topic_id_cache:
            return topic_id_cache[topic_id]
        if topic_id in sns_topics:
            topic_id_cache[topic_id] = topic_id
            return topic_id
        matches = topic_base_index.get(topic_id, [])
        resolved = matches[0] if matches else ""
        topic_id_cache[topic_id] = resolved
        return resolved

    def mission_chat_id(mission_id: str) -> str:
        if not mission_id.startswith("topic_"):
            return ""
        chat_id = mission_id.removeprefix("topic_")
        if not chat_id:
            return ""
        if chat_id in sns_chats:
            return chat_id
        prefixed = f"sns_{chat_id}"
        return prefixed if prefixed in sns_chats else ""

    def chat_name(chat_id: str) -> str:
        if not chat_id:
            return ""
        if chat_id in chat_name_cache:
            return chat_name_cache[chat_id]
        row = sns_chats.get(chat_id)
        if not row:
            chat_name_cache[chat_id] = ""
            return ""
        name = brace_text(t((row.get("name") or {}).get("id")))
        chat_name_cache[chat_id] = name
        return name

    def chat_name_trace(chat_id: str) -> dict | None:
        if not chat_id:
            return None
        row = sns_chats.get(chat_id)
        if not row:
            return None
        return {
            **source_ref("SNSChatTable", chat_id, pick_fields(row, "chatId", "name", "owner", "chatType")),
            "value": brace_text(t((row.get("name") or {}).get("id"))),
            "trace": named_text_trace("SNSChatTable", chat_id, "name", row.get("name")),
        }

    def topic_name(topic_id: str) -> str:
        """Resolve an SNS topic id like `topic_chr_0004_pelica` to its localized title."""
        if not topic_id:
            return ""
        if topic_id in topic_name_cache:
            return topic_name_cache[topic_id]
        resolved_topic_id = resolve_topic_id(topic_id)
        row = sns_topics.get(resolved_topic_id)
        if not row:
            topic_name_cache[topic_id] = ""
            return ""
        name = brace_text(t(row.get("topicName", {}).get("id")))
        topic_name_cache[topic_id] = name
        return name

    def topic_name_trace(topic_id: str) -> dict | None:
        if not topic_id:
            return None
        resolved_topic_id = resolve_topic_id(topic_id)
        row = sns_topics.get(resolved_topic_id)
        if not row:
            return None
        return {
            **source_ref(
                "SNSDialogTopicTable", resolved_topic_id, pick_fields(row, "topicName")
            ),
            "value": brace_text(t(row.get("topicName", {}).get("id"))),
            "trace": named_text_trace(
                "SNSDialogTopicTable", resolved_topic_id, "topicName", row.get("topicName")
            ),
        }

    def named_text(name_key: str) -> str:
        if not name_key:
            return ""
        row = text_table.get(name_key)
        if not row:
            return ""
        remember_texttable_row_usage(name_key)
        return t(row.get("id"))

    def named_text_key_trace(name_key: str) -> dict | None:
        if not name_key:
            return None
        row = text_table.get(name_key)
        if not row:
            return None
        return {
            **source_ref("TextTable", name_key, pick_fields(row, "id")),
            "value": named_text(name_key),
            "trace": text_trace("TextTable", name_key, "id", row.get("id")),
        }

    def norm_template_id(value: str) -> str:
        if value.startswith("npc_tpl_"):
            return value[len("npc_tpl_"):]
        return value

    npc_templates_by_template_id: dict[str, list[str]] = defaultdict(list)
    for template_row_id, row in npc_templates.items():
        template_id = str(row.get("templateId") or "")
        for candidate in {template_row_id, template_id, norm_template_id(template_id)}:
            if candidate:
                npc_templates_by_template_id[candidate].append(template_row_id)

    def resolve_npc_template_row(row_id: str, row: dict) -> tuple[str, dict | None]:
        candidates: list[str] = []

        def add_candidate(value: str) -> None:
            if not value or value in candidates:
                return
            candidates.append(value)
            norm = norm_template_id(value)
            if norm and norm not in candidates:
                candidates.append(norm)

        add_candidate(row_id)
        for key in ("npcId", "dataKey", "npcGroupId", "normalCfg"):
            value = str(row.get(key) or "")
            add_candidate(value)
            group_base = re.sub(r"_g\d+$", "", value)
            add_candidate(group_base)

        for candidate in candidates:
            if candidate in npc_templates:
                return (candidate, npc_templates[candidate])
            if candidate in npc_templates_by_template_id:
                template_row_id = npc_templates_by_template_id[candidate][0]
                return (template_row_id, npc_templates[template_row_id])
        return ("", None)

    env_npc_meta: dict[str, dict] = {}
    for npc_row_id, row in npc_rows.items():
        env_ids = row.get("envTalkIds") or []
        if not env_ids:
            continue

        template_row_id, template_row = resolve_npc_template_row(npc_row_id, row)
        template_name_key = str((template_row or {}).get("name") or "")
        template_title_key = str((template_row or {}).get("title") or "")

        direct_name = t((row.get("name") or {}).get("id")) if isinstance(row.get("name"), dict) else ""
        direct_title = t((row.get("title") or {}).get("id")) if isinstance(row.get("title"), dict) else ""
        name = direct_name or named_text(template_name_key)
        title = direct_title or named_text(template_title_key)

        meta = {
            "npcId": row.get("npcId") or npc_row_id,
            "npcGroupId": row.get("npcGroupId") or "",
            "dataKey": row.get("dataKey") or "",
            "name": name,
            "title": title,
            "dialogSelector": row.get("dialogSelector") or "",
            "_debug": {
                **source_ref(
                    "NpcTable",
                    npc_row_id,
                    pick_fields(
                        row,
                        "npcId",
                        "npcGroupId",
                        "dataKey",
                        "dialogSelector",
                        "envTalkIds",
                        "name",
                        "title",
                    ),
                ),
                "fields": {
                    "name": text_trace("NpcTable", npc_row_id, "name", row.get("name")),
                    "title": text_trace("NpcTable", npc_row_id, "title", row.get("title")),
                },
            },
        }
        if template_row:
            meta["_debug"]["template"] = source_ref(
                "NpcTemplateGroupTable",
                template_row_id,
                pick_fields(template_row, "npcNameId", "templateId", "name", "title"),
            )
            if template_name_key:
                meta["_debug"]["fields"]["templateName"] = named_text_key_trace(template_name_key)
            if template_title_key:
                meta["_debug"]["fields"]["templateTitle"] = named_text_key_trace(template_title_key)

        for env_id in env_ids:
            env_npc_meta.setdefault(env_id, meta)

    env_story_binding_hints: dict[str, dict[str, set[str] | list[dict]]] = defaultdict(
        lambda: {"levels": set(), "proxies": set(), "sources": []}
    )

    def add_env_story_binding_hint(
        env_id: str,
        *,
        level_id: str = "",
        proxy_id: str = "",
        source: dict | None = None,
    ) -> None:
        env_id = (env_id or "").strip()
        if not env_id:
            return
        hints = env_story_binding_hints[env_id]
        if level_id:
            hints["levels"].add(level_id)
        if proxy_id:
            hints["proxies"].add(proxy_id)
        if source:
            hints["sources"].append(source)

    for row_id, row in npc_proxy_rows.items():
        if not isinstance(row, dict):
            continue
        level_id = str(row.get("levelId") or "")
        proxy_id = str(row.get("proxyId") or row_id or "")
        for env_id in row.get("envTalkIds") or []:
            add_env_story_binding_hint(
                env_id,
                level_id=level_id,
                proxy_id=proxy_id,
                source={
                    "table": "NpcProxyTable",
                    "rowId": row_id,
                    "proxyId": proxy_id,
                    "levelId": level_id,
                },
            )

    for row_id, row in atmos_cluster_rows.items():
        if not isinstance(row, dict):
            continue
        env_id = str(row.get("envTalkId") or "").strip()
        if not env_id:
            continue
        level_id = str(row.get("levelId") or "")
        proxy_id = str(row.get("clusterId") or row_id or "")
        add_env_story_binding_hint(
            env_id,
            level_id=level_id,
            proxy_id=proxy_id,
            source={
                "table": "AtmosphericNpcClusterDataTable",
                "rowId": row_id,
                "clusterId": proxy_id,
                "levelId": level_id,
            },
        )

    # ---------- Story dialog groups ----------
    groups: dict[str, list[tuple[int, str, dict]]] = defaultdict(list)
    misc: list[tuple[str, dict]] = []
    for dlg_id, entry in dialogs.items():
        m = DLG_RE.match(dlg_id)
        if not m:
            misc.append((dlg_id, entry))
            continue
        mission, scene, line = m.group(1), int(m.group(2)), int(m.group(3))
        groups[f"dlg__{mission}__{scene}"].append((line, dlg_id, entry))

    # Build actor display name table.
    # Each actorNameId may have multiple variant names across the game
    # (alias, masked persona, "前缀{真名}", etc.). Keep all distinct ones,
    # but drop the "？？？" / "???" placeholder used for unrevealed identities.
    PLACEHOLDER_NAMES = {"？？？", "???"}
    actor_name_sets: dict[str, set[str]] = defaultdict(set)

    def add_actor_text(aid: str, name: str) -> None:
        if not aid or not name or name in PLACEHOLDER_NAMES:
            return
        actor_name_sets[aid].add(name)

    def add_actor_name(aid: str, name_id) -> None:
        if not aid:
            return
        add_actor_text(aid, t(name_id))

    def scoped_actor_base_candidates(actor_id: str) -> list[str]:
        """Return canonical actor-id candidates from map/base-scoped ids.

        EnvTalk actor ids sometimes encode the speaker as a scoped proxy such
        as `chen_map01_e2m5`. The prefix is still the real speaker id, while
        the suffix only tells us which map/mission proxy emitted the bark.
        """
        raw = str(actor_id or "").strip()
        if not raw:
            return []
        out: list[str] = []
        for marker in ("_map", "_base"):
            idx = raw.find(marker)
            if idx > 0:
                out.append(raw[:idx])
        return _unique_preserve(out)

    def npc_proxy_actor_candidates(proxy_id: str) -> list[str]:
        raw = str(proxy_id or "").strip()
        if not raw:
            return []
        out: list[str] = []
        info = npc_proxy_info.get(raw)
        if isinstance(info, dict):
            for field in ("npcNameId", "npcId"):
                value = str(info.get(field) or "").strip()
                if not value:
                    continue
                out.append(value)
                out.extend(scoped_actor_base_candidates(value))
        out.extend(scoped_actor_base_candidates(raw))
        return _unique_preserve(out)

    def add_actor_template_name(aid: str) -> None:
        if not aid:
            return
        row = npc_templates.get(aid)
        if not isinstance(row, dict):
            return
        add_actor_text(aid, named_text(str(row.get("name") or "")))
        add_actor_text(aid, named_text(str(row.get("title") or "")))

    for entry in dialogs.values():
        add_actor_name(entry.get("actorNameId") or "", entry.get("actorName", {}).get("id"))

    for radio in radios.values():
        for item in radio.get("radioSingleDataList", []) or []:
            aid = item.get("actorNameId") or ""
            add_actor_name(aid, item.get("actorName", {}).get("id"))
            add_actor_name(aid, item.get("infoActorName", {}).get("id"))

    # Mail senders cover characters that only surface in inbox/SNS data, so
    # seed the canonical actor table from them before expanding SNS aliases.
    for sender_id, row in mail_senders.items():
        if not isinstance(row, dict):
            continue
        add_actor_name(sender_id, row.get("senderName", {}).get("id"))

    # SNS chat rows provide the visible display name for synthetic ids like
    # `sns_chat_daniel` and a small number of non-`sns_` chat owners that do
    # not correspond to a regular story actor id.
    for sns_id, row in sns_chats.items():
        if not isinstance(row, dict):
            continue
        add_actor_name(sns_id, row.get("name", {}).get("id"))

    def icon_basename(icon_path: str) -> str:
        if not icon_path:
            return ""
        return icon_path.rsplit("/", 1)[-1]

    # Reuse exported icon metadata instead of guessing SNS aliases from the raw
    # chat id alone. Mail sender data already maps icon asset -> canonical
    # actor key like `pelica` / `andrew`, and SNS chat rows reuse those icons.
    sns_related_ids: dict[str, list[str]] = {}
    icon_to_actor_id: dict[str, str] = {}
    for sender_id, row in mail_senders.items():
        if not isinstance(row, dict):
            continue
        icon = icon_basename(str(row.get("senderIcon") or ""))
        if icon and sender_id:
            icon_to_actor_id.setdefault(icon, sender_id)

    for sns_id, row in sns_chats.items():
        if not sns_id.startswith("sns_") or not isinstance(row, dict):
            continue
        related: list[str] = []

        for icon_field in ("icon", "listIcon"):
            icon = icon_basename(str(row.get(icon_field) or ""))
            mapped = icon_to_actor_id.get(icon)
            if mapped and mapped not in related:
                related.append(mapped)

        core = sns_id[len("sns_"):]
        if core.startswith("chr_"):
            parts = core.split("_")
            if parts and parts[-1] not in related:
                related.append(parts[-1])
        elif core.startswith("npc_"):
            npc_name = core[len("npc_"):]
            if npc_name and npc_name not in related:
                related.append(npc_name)
        elif core and core not in related:
            related.append(core)

        if related:
            sns_related_ids[sns_id] = related

    for sns_id, related_ids in sns_related_ids.items():
        for related_id in related_ids:
            names = actor_name_sets.get(related_id)
            if names:
                actor_name_sets[sns_id].update(names)
                break

    # The generic player/admin id and the female presentation id should share
    # the same resolved display name in the browser data.
    if actor_name_sets.get("endminf"):
        actor_name_sets["endmin"].update(actor_name_sets["endminf"])

    npc_proxy_rows_by_proxy_id: dict[str, tuple[str, dict]] = {}
    env_talk_proxy_ids_by_env: dict[str, list[str]] = defaultdict(list)
    for row_id, row in npc_proxy_rows.items():
        if not isinstance(row, dict):
            continue
        proxy_id = str(row.get("proxyId") or row_id or "").strip()
        if not proxy_id:
            continue
        npc_proxy_rows_by_proxy_id[proxy_id] = (str(row_id), row)
        env_ids = [
            str(env_id).strip()
            for env_id in (row.get("envTalkIds") or [])
            if env_id is not None and str(env_id).strip()
        ]
        if not env_ids:
            continue

        override_name_key = str(((row.get("overrideNpcNameId") or {}).get("key")) or "")
        if row.get("ifOverrideNpcName") and override_name_key:
            add_actor_text(proxy_id, named_text(override_name_key))

        for base_actor_id in npc_proxy_actor_candidates(proxy_id):
            add_actor_template_name(base_actor_id)
            if actor_name_sets.get(base_actor_id):
                actor_name_sets[proxy_id].update(actor_name_sets[base_actor_id])
                break

        for env_id in env_ids:
            env_talk_proxy_ids_by_env[env_id].append(proxy_id)

    for entry in env_talks.values():
        for item in entry.get("envTalkDataList", []) or []:
            scoped_actor_id = str(item.get("actorId") or "")
            for base_actor_id in npc_proxy_actor_candidates(scoped_actor_id):
                add_actor_template_name(base_actor_id)
                if actor_name_sets.get(base_actor_id):
                    actor_name_sets[scoped_actor_id].update(actor_name_sets[base_actor_id])
                    break

    actor_names: dict[str, list[str]] = {
        aid: sorted(names) for aid, names in actor_name_sets.items()
    }

    def speaker_display_name(speaker_id: str) -> str:
        """Best-effort display name for dialog/SNS speaker ids."""
        if not speaker_id:
            return ""

        candidates: list[str] = [speaker_id]
        if speaker_id.startswith("sns_"):
            candidates.append(speaker_id[len("sns_"):])

        core = candidates[-1]
        candidates.extend(npc_proxy_actor_candidates(core))
        if core.startswith("npc_"):
            candidates.append(core[len("npc_"):])
        if core.startswith("chr_"):
            candidates.append(core)
            parts = core.split("_")
            if parts:
                candidates.append(parts[-1])
        elif "_" in core:
            candidates.append(core.split("_")[-1])

        seen: set[str] = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            names = actor_names.get(candidate)
            if names:
                return names[0]

        return ""

    def speaker_actor_id(speaker_id: str) -> str:
        """Resolve a speaker/channel id back to the browser's actor id when possible."""
        if not speaker_id:
            return ""

        candidates: list[str] = [speaker_id]
        if speaker_id.startswith("sns_"):
            candidates.append(speaker_id[len("sns_"):])

        core = candidates[-1]
        candidates.extend(npc_proxy_actor_candidates(core))
        if core.startswith("npc_"):
            candidates.append(core[len("npc_"):])
        if core.startswith("chr_"):
            candidates.append(core)
            parts = core.split("_", 2)
            if len(parts) >= 3:
                candidates.append(parts[2])
        elif "_" in core:
            candidates.append(core.split("_")[-1])

        seen: set[str] = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            if candidate in actor_names or re.fullmatch(r"endmin[fm]?", candidate):
                return candidate
        return ""

    def env_group(env_id: str) -> str:
        """Bucket ambient-talk ids into browser groups."""
        if env_id.startswith("greetEnvTalk"):
            return "greetEnvTalk"
        if env_id.startswith("envEmoji"):
            return "envEmoji"
        if env_id.startswith("charGiftTalkid"):
            return "charGiftTalkid"
        m = re.match(r"^envTalk_([^_]+(?:_lv\d+(?:_env)?)?)(?:_|$)", env_id)
        if m:
            token = m.group(1)
            if token.startswith("base") and re.match(r"^base\d+_lv\d+(?:_env)?$", token):
                return "map" + token[len("base"):]
            return token
        return "envTalk"

    def env_story_mission(env_id: str, known_missions: set[str]) -> str:
        """Return the mission bucket encoded by an env-talk id when possible.

        Supports both story-shaped ids like `envTalk_e0m2_7` and map/base ids
        like `envTalk_map01_lv001_env_11` or `envTalk_base01_lv001_env_11`.
        """
        direct = re.match(r"^envTalk_([^_]+)(?:_|$)", env_id)
        if direct:
            mission = direct.group(1)
            if mission in known_missions:
                return mission

        map_like = re.match(r"^envTalk_((?:map|base)\d+_lv\d+(?:_env)?)_\d+$", env_id)
        if not map_like:
            return ""

        mission = map_like.group(1)
        if mission in known_missions:
            return mission
        if mission.startswith("base"):
            mapped = "map" + mission[len("base"):]
            if mapped in known_missions:
                return mapped
        return ""

    def env_index_slot(env_id: str) -> tuple[str, str, str, list[str]]:
        """Return browser slot info for an env-talk entry.

        Most env talks are browsed with the open-world text bucket, while
        operator greeting lines (`greetEnvTalk*`) stay alongside other
        operator-interaction content.
        """
        if env_id.startswith("greetEnvTalk"):
            return ("misc", "greet", "sim", ["envTalk"])
        mission = env_group(env_id)
        return ("env", mission, "worldtext", ["envTalk"])

    def line_haystack(lines: list[dict], *fields: str) -> str:
        parts: list[str] = []
        for line in lines:
            for field in fields:
                value = line.get(field)
                if value:
                    parts.append(str(value))
        return " ".join(parts)

    # ---------- SNS dialogs ----------
    sns_groups: dict[str, dict] = {}
    for sns_id, entry in sns.items():
        sns_groups[sns_id] = entry

    # ---------- Extras: summary / options + standalone radio ----------
    # Each attaches to a conversation out_key. Regular dialog scenes emit as
    # `dlg_<mission>_<scene>` (scene is int). Sub-scene dialogs like
    # `dlg_c16m1_4d5_001` end up in misc bucket `misc_dlg_<mission>_<scene>`.
    # We build both possible target keys so extras route correctly.
    dlg_out_keys: set[str] = set()
    for key in groups:
        _, mission, scene_str = key.split("__")
        dlg_out_keys.add(f"dlg_{mission}_{int(scene_str)}")
    sns_out_keys: set[str] = set(sns_groups)
    radio_out_keys: set[str] = set()
    black_out_keys: set[str] = set()
    remotecomm_out_keys: set[str] = set()
    cutscene_out_keys: set[str] = set()
    misc_bucket_keys: set[str] = set()
    for did, _ in misc:
        bkey = re.sub(r"_\d+(_\d+)?$", "", did) or "_misc"
        misc_bucket_keys.add(f"misc_{bkey}")
    known_missions: set[str] = {key.split("__")[1] for key in groups}
    known_missions.update(m.group(1) for sid in sns_groups if (m := SNS_RE.match(sid)))
    for did, _ in misc:
        type_, _act, mission, _scene = slot_misc(re.sub(r"_\d+(_\d+)?$", "", did) or "_misc")
        if type_ != "x" and mission:
            known_missions.add(mission)

    env_story_missions: dict[str, str] = {}
    for env_id in env_talks:
        if story_mission := env_story_mission(env_id, known_missions):
            env_story_missions[env_id] = story_mission

    mission_note_by_mission: dict[str, list[dict]] = defaultdict(list)
    for mission_id, row in mission_extra_info.items():
        text = t((row.get("extraInfoDesc") or {}).get("id"))
        if not text:
            continue
        mission_note_by_mission[mission_id].append({
            "missionId": mission_id,
            "type": row.get("extraInfoType", 0),
            "text": text,
            "_debug": {
                **source_ref(
                    "MissionExtraInfoTable",
                    mission_id,
                    pick_fields(row, "missionId", "extraInfoType", "extraInfoDesc"),
                ),
                "fields": {
                    "text": text_trace(
                        "MissionExtraInfoTable",
                        mission_id,
                        "extraInfoDesc",
                        row.get("extraInfoDesc"),
                    ),
                },
            },
        })

    def parse_level_ref_name(name: str) -> dict | None:
        if not name.endswith(".json"):
            return None
        stem = name[:-5]
        marker = "_lv_data_sub_"
        if marker not in stem:
            return None
        level_id, rest = stem.split(marker, 1)
        kind = "plain"
        if rest.startswith("mission_"):
            kind = "mission"
            rest = rest[len("mission_") :]
        rest = rest.lstrip("_")
        if not level_id or not rest:
            return None
        token = re.sub(r"_v[0-9A-Za-z]+$", "", rest)
        return {
            "level": level_id,
            "kind": kind,
            "token": token,
        }

    def level_host_type(level_id: str) -> str:
        if level_id.startswith(("map", "base")):
            return "map"
        if level_id.startswith("dung"):
            return "dungeon"
        if level_id.startswith("indie"):
            return "indie"
        if level_id.startswith("blackbox"):
            return "blackbox"
        return "other"

    mission_level_refs: dict[str, list[dict]] = defaultdict(list)
    if LEVELDATA_DIR.is_dir():
        for path in LEVELDATA_DIR.rglob("*.json"):
            ref_meta = parse_level_ref_name(path.name)
            if not ref_meta:
                continue
            mission_id = ref_meta["token"]
            if mission_id not in known_missions:
                continue
            level_id = ref_meta["level"]
            mission_level_refs[mission_id].append({
                "levelId": level_id,
                "hostType": level_host_type(level_id),
                "kind": ref_meta["kind"],
                "file": path.relative_to(ROOT).as_posix(),
                "_debug": {
                    "source": {
                        "file": path.relative_to(ROOT).as_posix(),
                        "levelId": level_id,
                        "kind": ref_meta["kind"],
                        "missionId": mission_id,
                    },
                },
            })
    for refs in mission_level_refs.values():
        refs.sort(key=lambda ref: (ref["hostType"], ref["levelId"], ref["kind"], ref["file"]))

    def mission_context_text(mission_id: str) -> str:
        if not mission_id:
            return ""
        parts: list[str] = []
        for note in mission_note_by_mission.get(mission_id, []):
            if note.get("text"):
                parts.append(note["text"])
        for ref in mission_level_refs.get(mission_id, []):
            if ref.get("levelId"):
                parts.append(ref["levelId"])
        return " ".join(parts)

    def merge_search_text(base: str, extra: str) -> str:
        base = base.strip()
        extra = extra.strip()
        if not base:
            return extra
        if not extra:
            return base
        return f"{base} {extra}"

    extra_mission_names: dict[str, str] = {}

    def entry_tags(out_key: str, mission: str = "") -> list[str]:
        tags: list[str] = []
        if out_key in summary_by_key:
            tags.append("summary")
        return tags

    def attach_target(mission: str, scene: str, *, allow_sns: bool = False) -> str | None:
        """Pick the out_key that owns (mission, scene), or None if orphan."""
        if re.fullmatch(r"\d+", scene):
            cand = f"dlg_{mission}_{int(scene)}"
            if cand in dlg_out_keys:
                return cand
            if allow_sns:
                cand = f"sns_{mission}_{int(scene)}"
                if cand in sns_out_keys:
                    return cand
        cand = f"misc_dlg_{mission}_{scene}"
        if cand in misc_bucket_keys:
            return cand
        return None

    def dialog_scene_out_key(dialog_id: str) -> str | None:
        if dialog_id in sns_out_keys:
            return dialog_id
        if dialog_id in radio_out_keys:
            return dialog_id
        if dialog_id in black_out_keys or dialog_id in remotecomm_out_keys:
            return dialog_id
        if canonical_cutscene := _canonical_cutscene_key(dialog_id):
            if canonical_cutscene in cutscene_out_keys:
                return canonical_cutscene
        m = re.match(rf"^dlg_(.+)_({SCENE_TOK})$", dialog_id)
        if not m:
            if dialog_id.startswith("dlg_"):
                payload = dialog_id[4:]
                if "_" in payload:
                    mission, scene = payload.split("_", 1)
                    return attach_target(mission, scene)
            return None
        return attach_target(m.group(1), m.group(2))

    summary_by_key: dict[str, list[dict]] = defaultdict(list)
    summary_orphans = 0
    for sid, entry in summaries.items():
        m = SUMMARY_RE.match(sid)
        if not m:
            summary_orphans += 1
            continue
        mission, scene, _idx = m.group(1), m.group(2), m.group(3)
        target = attach_target(mission, scene)
        text = t(entry.get("id"))
        if not text:
            continue
        if target is None:
            summary_orphans += 1
            continue
        summary_by_key[target].append({
            "text": text,
            "_debug": {
                **source_ref("DialogSummaryTable", sid, pick_fields(entry, "id")),
                "fields": {
                    "text": text_trace("DialogSummaryTable", sid, "id", entry.get("id")),
                },
            },
        })

    options_by_key: dict[str, dict[int, list[dict]]] = defaultdict(lambda: defaultdict(list))
    dialog_option_signature_by_id: dict[str, tuple[str, str]] = {}
    dialog_option_ids_by_scene_group: dict[tuple[str, int], list[tuple[int, str]]] = defaultdict(list)
    option_orphans = 0
    for oid, entry in dlg_opts.items():
        m = OPTION_RE.match(oid)
        if not m:
            # `dlg_spaceship_*` UI options have no scene; skip.
            continue
        mission, scene, grp, idx = m.group(1), m.group(2), int(m.group(3)), int(m.group(4))
        option_text = t(entry.get("optionText", {}).get("id"))
        option_icon = entry.get("iconType", "") or ""
        option_scene_key = f"dlg_{mission}_{scene}"
        dialog_option_signature_by_id[oid] = (_option_text_signature(option_text), option_icon)
        dialog_option_ids_by_scene_group[(option_scene_key, grp)].append((idx, oid))
        target = attach_target(mission, scene)
        if target is None:
            option_orphans += 1
            continue
        options_by_key[target][grp].append({
            "id": oid,
            "i": idx,
            "text": option_text,
            "icon": option_icon,
            "_debug": {
                **source_ref(
                    "DialogOptionTable",
                    oid,
                    pick_fields(entry, "optionText", "iconType"),
                ),
                "fields": {
                    "text": text_trace(
                        "DialogOptionTable", oid, "optionText", entry.get("optionText")
                    ),
                },
            },
        })
    dialog_option_group_ids_by_key: dict[tuple[str, int], list[str]] = {
        key: [oid for _idx, oid in sorted(entries)]
        for key, entries in dialog_option_ids_by_scene_group.items()
    }

    radio_rows: list[dict] = []
    radio_orphans = 0
    radio_targets_seen: set[str] = set()
    for rid, entry in radios.items():
        m = RADIO_RE.match(rid)
        if not m:
            radio_orphans += 1
            continue
        mission, scene = m.group(1), m.group(2)
        target = attach_target(mission, scene, allow_sns=True)
        if target is None:
            radio_orphans += 1
        items = []
        actors: set[str] = set()
        prev_text = ""
        for item in entry.get("radioSingleDataList", []) or []:
            actor_id = item.get("actorNameId", "") or ""
            actor = t(item.get("actorName", {}).get("id"))
            text = t(item.get("radioText", {}).get("id"))
            if actor_id:
                actors.add(actor_id)
            if not prev_text and text:
                prev_text = text
            items.append({
                "id": item.get("id", "") or "",
                "aid": actor_id,
                "actor": actor,
                "text": text,
                "audio": item.get("audioOverride", "") or "",
                "emo": item.get("emotionType", 0),
                "_debug": {
                    **source_ref(
                        "RadioTable.radioSingleDataList",
                        item.get("id", "") or "",
                        pick_fields(
                            item,
                            "id",
                            "actorNameId",
                            "actorName",
                            "infoActorName",
                            "radioText",
                            "audioOverride",
                            "emotionType",
                        ),
                    ),
                    "fields": {
                        "actor": text_trace(
                            "RadioTable.radioSingleDataList",
                            item.get("id", "") or "",
                            "actorName",
                            item.get("actorName"),
                        ),
                        "text": text_trace(
                            "RadioTable.radioSingleDataList",
                            item.get("id", "") or "",
                            "radioText",
                            item.get("radioText"),
                        ),
                    },
                },
            })
        if target:
            radio_targets_seen.add(target)
        type_, act = parse_mission(mission)
        radio_rows.append({
            "k": rid,
            "m": mission,
            "scene": scene,
            "s": scene_sort_value(scene),
            "t": type_,
            "a": act,
            "c": sorted(actors),
            "p": preview(prev_text),
            "lines": items,
            "radioType": entry.get("radioType", 0),
            "target": target or "",
            "_debug": source_ref(
                "RadioTable",
                rid,
                pick_fields(entry, "radioType"),
            ),
        })

    def pack_options(
        groups_map: dict[int, list[dict]],
        lines: list[dict] | None = None,
        conv_key: str | None = None,
    ) -> dict:
        """Return option groups sorted by group number, each annotated with an
        `after` field naming the line id after which it should render.

        Primary signal (when available): the AnimeStudio DialogTree graph at
        `exported/AnimeStudio/main/TextAsset/<conv_key>.json`, which stores
        the authoritative option→trunk wiring. Falls back to a gap heuristic:
        DialogTextTable lines are numbered sparsely — slots are reserved for
        player-response audio that isn't stored as dialog text — so a line
        sequence like `_001..006, _008..013, _016..025, _030..041` has three
        gaps where choices happen, and option groups `g=1`, `g=2`, `g=3`
        attach to those gaps in order.
        """
        tree_meta: dict = {}
        tree_after: dict[str, str] = {}
        tree_after_sources: dict[str, list[str]] = {}
        tree_branches: dict[str, list[str]] = {}
        tree_merge: dict[str, str] = {}
        tree_converge: dict[str, str] = {}
        tree_pre: set[str] = set()
        tree_pre_sources: dict[str, list[str]] = {}
        scene_link_after: dict[str, str] = {}
        scene_link_authored_option_ids: set[str] = set()
        scene_link_sources: set[str] = set()
        cinematic_finish_groups: list[dict] = []
        cinematic_after_by_group: dict[int, str] = {}
        cinematic_sources_by_group: dict[int, list[str]] = {}
        cinematic_authored_option_ids: set[str] = set()
        cinematic_sources: set[str] = set()
        text_alias_after_by_group: dict[int, str] = {}
        text_alias_pre_by_group: set[int] = set()
        text_alias_sources_by_group: dict[int, list[str]] = {}
        text_alias_foreign_option_ids_by_group: dict[int, list[str]] = {}
        text_alias_authored_option_ids: set[str] = set()
        text_alias_sources: set[str] = set()
        timeline_entries: list[dict] = []
        timeline_after: dict[str, str] = {}
        timeline_after_line_ids: dict[str, list[str]] = {}
        timeline_option_rows: dict[str, list[dict]] = defaultdict(list)
        timeline_pre: set[str] = set()
        timeline_authored_option_ids: set[str] = set()
        timeline_sources: set[str] = set()
        if conv_key:
            tree_meta = load_dialog_tree(conv_key) or {}
            tree_after = tree_meta.get("after", {}) or {}
            tree_after_sources = tree_meta.get("afterSources", {}) or {}
            tree_branches = tree_meta.get("branches", {}) or {}
            tree_merge = tree_meta.get("merge", {}) or {}
            tree_converge = tree_meta.get("converge", {}) or {}
            tree_pre_sources = tree_meta.get("preSources", {}) or {}
            cinematic_finish_groups = [
                group
                for group in (tree_meta.get("cinematicFinishGroups") or [])
                if isinstance(group, dict)
            ]
            tree_pre = {
                opt_id
                for opt_id in (tree_meta.get("pre") or [])
                if isinstance(opt_id, str) and opt_id
            }
            for link in load_dialog_tree_scene_links(conv_key) or []:
                source_key = link.get("sourceKey") or ""
                if source_key:
                    scene_link_sources.add(source_key)
                group_after = link.get("after") or ""
                for opt in link.get("options") or []:
                    opt_id = opt.get("optionId") or ""
                    if not opt_id:
                        continue
                    if group_after:
                        scene_link_authored_option_ids.add(opt_id)
                        if opt_id not in scene_link_after:
                            scene_link_after[opt_id] = group_after
            timeline_entries = load_dialog_timeline_line_orders(conv_key)
            for timeline in timeline_entries:
                if not timeline.get("optionAnchors"):
                    continue
                source_key = timeline.get("sourceKey") or timeline.get("timeline") or ""
                file_path = timeline.get("file") or ""
                timeline_line_ids = [
                    str(line_id)
                    for line_id in (timeline.get("lineIds") or [])
                    if str(line_id).strip()
                ]
                if source_key:
                    timeline_sources.add(source_key)
                if file_path:
                    timeline_sources.add(file_path)
                for row in timeline.get("optionRows") or []:
                    if not isinstance(row, dict):
                        continue
                    opt_id = str(row.get("id") or "")
                    if _dialog_tree_option_prefix(opt_id) != conv_key:
                        continue
                    timeline_option_rows[opt_id].append(row)
                for opt_id, anchor in (timeline.get("optionAnchors") or {}).items():
                    if _dialog_tree_option_prefix(opt_id) != conv_key:
                        continue
                    if not isinstance(anchor, dict):
                        continue
                    after_id = str(anchor.get("after") or "")
                    if after_id:
                        timeline_authored_option_ids.add(opt_id)
                        timeline_after.setdefault(opt_id, after_id)
                        if timeline_line_ids and opt_id not in timeline_after_line_ids:
                            timeline_after_line_ids[opt_id] = timeline_line_ids
                    elif anchor.get("position") == "pre":
                        timeline_authored_option_ids.add(opt_id)
                        timeline_pre.add(opt_id)

        line_idxs: list[tuple[int, str]] = []
        valid_line_ids: set[str] = set()
        if lines:
            for ln in lines:
                lid = ln.get("id") or ""
                if lid:
                    valid_line_ids.add(lid)
                m = re.search(r"_(\d+)$", lid)
                if m:
                    line_idxs.append((int(m.group(1)), lid))
        line_idxs.sort()

        # Fallback anchors when DialogTree/timeline data leaves option groups
        # unanchored. Three signals, in priority order:
        #   1. sparse-gap boundaries — between two contiguous numbering runs,
        #      the player choice plays during the missing slot.
        #   2. timeline option-clip positions — when this conv shares a Unity
        #      Timeline with another scene (e.g. dlg_e2m6_11 + dlg_e2m6_19),
        #      the option clip's start time tells us which of THIS conv's
        #      lines plays just before the choice. We surface that even when
        #      the recorded `_optionId` belongs to the sibling scene.
        #   3. exact group/line number — in contiguous table-only scenes,
        #      option group g=1 usually follows line _001.
        #   4. dialog last line — for cinematic-finish patterns where one
        #      option clip drives end-of-arc finish-num branches.
        # All three write to optionGroups[].after; `inferredAnchorMode` in the
        # warning's groupDetails records which signal won.
        fallback_after_ids: list[str] = []
        fallback_group_line_ids: dict[int, str] = {}
        last_line_fallback_id = ""
        if line_idxs:
            fallback_group_line_ids = {
                idx: line_id
                for idx, line_id in line_idxs
            }
            runs: list[list[tuple[int, str]]] = [[line_idxs[0]]]
            for prev, nxt in zip(line_idxs, line_idxs[1:]):
                if nxt[0] == prev[0] + 1:
                    runs[-1].append(nxt)
                else:
                    runs.append([nxt])
            gap_after_ids: list[str] = []
            for run_idx, run in enumerate(runs):
                if run_idx > 0:
                    prev_run = runs[run_idx - 1]
                    if prev_run:
                        gap_after_ids.append(prev_run[-1][1])
            fallback_after_ids.extend(gap_after_ids)
            last_line_fallback_id = line_idxs[-1][1]

        sibling_position_anchors = collect_option_position_anchors(conv_key) if conv_key else []

        group_option_ids_by_group: dict[int, list[str]] = {
            group_id: [
                opt.get("id") or ""
                for opt in sorted(group_opts, key=lambda o: o.get("i", 0))
                if isinstance(opt, dict) and opt.get("id")
            ]
            for group_id, group_opts in groups_map.items()
        }
        option_count_hist = Counter(
            len(group_opt_ids)
            for group_opt_ids in group_option_ids_by_group.values()
            if group_opt_ids
        )

        def cinematic_finish_anchor(finish_group: dict, option_count: int) -> tuple[str, list[str]]:
            finish_nums = finish_group.get("finishNums") or []
            if not isinstance(finish_nums, list) or len(finish_nums) != option_count:
                return "", []
            target_count = finish_group.get("targetCount")
            if isinstance(target_count, int) and target_count and target_count != option_count:
                return "", []
            timeline_name = str(finish_group.get("timeline") or "").strip()
            if not timeline_name:
                return "", []
            source_bits = [
                str(value)
                for value in (
                    finish_group.get("sourceKey"),
                    finish_group.get("file"),
                    timeline_name,
                )
                if str(value or "").strip()
            ]
            for timeline in timeline_entries:
                entry_names = {
                    str(timeline.get("sourceKey") or "").strip(),
                    str(timeline.get("timeline") or "").strip(),
                }
                if timeline_name not in entry_names:
                    continue
                timeline_line_ids = [
                    str(line_id)
                    for line_id in (timeline.get("lineIds") or [])
                    if str(line_id).strip()
                ]
                for line_id in reversed(timeline_line_ids):
                    if line_id in valid_line_ids:
                        if file_path := str(timeline.get("file") or "").strip():
                            source_bits.append(file_path)
                        return line_id, _unique_preserve(source_bits)
            after_id = str(finish_group.get("after") or "").strip()
            if after_id in valid_line_ids:
                return after_id, _unique_preserve(source_bits)
            return "", []

        # Cinematic finish-number branches describe timeline outcomes, not
        # explicit option UI placement. Keep them out of authored option
        # anchoring unless an extracted option clip/node names the current
        # option ids directly.

        def option_signature_sequence(option_ids: list[str]) -> list[tuple[str, str]]:
            signatures: list[tuple[str, str]] = []
            for opt_id in option_ids:
                signature = dialog_option_signature_by_id.get(opt_id)
                if not signature or not signature[0]:
                    return []
                signatures.append(signature)
            return signatures

        def source_bits_for_options(option_ids: list[str], source_map: dict[str, object]) -> list[str]:
            source_bits: list[str] = []
            for opt_id in option_ids:
                raw_sources = source_map.get(opt_id) if isinstance(source_map, dict) else None
                if isinstance(raw_sources, list):
                    source_bits.extend(str(source) for source in raw_sources if str(source or "").strip())
                elif raw_sources:
                    source_bits.append(str(raw_sources))
            return _unique_preserve(source_bits)

        def complete_foreign_option_group(
            group_key: tuple[str, int],
            raw_entries: list[tuple[int, str]],
        ) -> list[str]:
            foreign_ids = [
                opt_id
                for _idx, opt_id in sorted(raw_entries, key=lambda item: item[0])
                if opt_id
            ]
            if not foreign_ids or len(set(foreign_ids)) != len(foreign_ids):
                return []
            full_foreign_ids = dialog_option_group_ids_by_key.get(group_key) or []
            if not full_foreign_ids or foreign_ids != full_foreign_ids:
                return []
            return foreign_ids

        foreign_after_groups: dict[tuple[str, int], list[tuple[int, str, str]]] = defaultdict(list)
        for foreign_opt_id, raw_after in tree_after.items():
            parts = _option_id_group_parts(foreign_opt_id)
            candidate_after = str(raw_after or "")
            if not parts or not candidate_after or candidate_after not in valid_line_ids:
                continue
            scene_key, foreign_group_id, foreign_index = parts
            if scene_key == conv_key:
                continue
            foreign_after_groups[(scene_key, foreign_group_id)].append(
                (foreign_index, foreign_opt_id, candidate_after)
            )

        foreign_pre_groups: dict[tuple[str, int], list[tuple[int, str]]] = defaultdict(list)
        for foreign_opt_id in tree_pre:
            parts = _option_id_group_parts(foreign_opt_id)
            if not parts:
                continue
            scene_key, foreign_group_id, foreign_index = parts
            if scene_key == conv_key:
                continue
            foreign_pre_groups[(scene_key, foreign_group_id)].append((foreign_index, foreign_opt_id))

        for group_id, group_opt_ids in group_option_ids_by_group.items():
            local_signature = option_signature_sequence(group_opt_ids)
            if not local_signature:
                continue

            after_matches: list[tuple[str, list[str], list[str]]] = []
            for foreign_group_key, raw_entries in foreign_after_groups.items():
                ordered_entries = sorted(raw_entries, key=lambda item: item[0])
                foreign_ids = complete_foreign_option_group(
                    foreign_group_key,
                    [(idx, opt_id) for idx, opt_id, _after in ordered_entries],
                )
                if len(foreign_ids) != len(group_opt_ids):
                    continue
                anchors = {after for _idx, _opt_id, after in ordered_entries}
                if len(anchors) != 1:
                    continue
                if option_signature_sequence(foreign_ids) != local_signature:
                    continue
                source_bits = source_bits_for_options(foreign_ids, tree_after_sources)
                after_matches.append((next(iter(anchors)), foreign_ids, source_bits))

            # Exact text/icon aliases are useful investigation hints, but they
            # are not firm authored placement for the current option ids.
            # Only direct extracted references may anchor options.
            if len(after_matches) == 1:
                continue

            pre_matches: list[tuple[list[str], list[str]]] = []
            for foreign_group_key, raw_entries in foreign_pre_groups.items():
                foreign_ids = complete_foreign_option_group(foreign_group_key, raw_entries)
                if len(foreign_ids) != len(group_opt_ids):
                    continue
                if option_signature_sequence(foreign_ids) != local_signature:
                    continue
                source_bits = source_bits_for_options(foreign_ids, tree_pre_sources)
                pre_matches.append((foreign_ids, source_bits))

            if len(pre_matches) == 1:
                continue

        out: list[dict] = []
        used_fallback_layout = False
        used_any_fallback_option_layout = False
        authored_option_ids = (
            set(tree_after)
            | set(tree_branches)
            | set(tree_merge)
            | tree_pre
            | scene_link_authored_option_ids
            | timeline_authored_option_ids
        )
        authored_group_count = 0
        pre_group_count = 0
        fallback_group_count = 0
        unanchored_group_count = 0
        fallback_group_labels: list[str] = []
        group_details: list[dict] = []

        def preferred_timeline_option_row(opt_id: str) -> dict:
            rows = timeline_option_rows.get(opt_id) or []
            if not rows:
                return {}
            return min(
                rows,
                key=lambda row: (
                    0 if row.get("anchorMode") == "trunkBinding" else 1,
                    float(row.get("start") or 0.0),
                    row.get("optionIndex") if row.get("optionIndex") is not None else 10**9,
                    row.get("assetTrack") or "",
                ),
            )

        def following_line_risk_for_group(group_opt_ids: list[str], after_id: str) -> dict:
            if len(group_opt_ids) < 2 or not after_id:
                return {}
            if any(tree_branches.get(opt_id) for opt_id in group_opt_ids):
                return {}
            anchors = [timeline_after.get(opt_id) or "" for opt_id in group_opt_ids]
            if not all(anchor == after_id for anchor in anchors):
                return {}
            # Dialog tree shows all options converge to the same response trunk.
            # Only emit cosmeticChoice when Timeline anchors already matched (so this
            # is a group that would otherwise have become inferredFollowingLines).
            if all(opt_id in tree_converge for opt_id in group_opt_ids):
                trunk_ids = {tree_converge[opt_id] for opt_id in group_opt_ids}
                if len(trunk_ids) == 1:
                    common_trunk = next(iter(trunk_ids))
                    if common_trunk in valid_line_ids:
                        return {
                            "code": "cosmeticChoice",
                            "reason": "treeSourcedConvergence",
                            "detail": (
                                "Dialog tree shows all options in this group lead to the "
                                "same response trunk; the choice affects only the player's "
                                "displayed text, not which line plays next."
                            ),
                            "after": after_id,
                            "optionIds": group_opt_ids,
                            "candidateLineIds": [],
                            "commonContinuationLineId": common_trunk,
                            "source": "dialogTree",
                        }
            timeline_line_ids: list[str] = []
            for opt_id in group_opt_ids:
                candidate_order = timeline_after_line_ids.get(opt_id) or []
                if after_id in candidate_order:
                    timeline_line_ids = candidate_order
                    break
            if not timeline_line_ids or after_id not in timeline_line_ids:
                return {}
            after_index = timeline_line_ids.index(after_id)
            candidate_line_ids = [
                line_id
                for line_id in timeline_line_ids[after_index + 1 : after_index + 1 + len(group_opt_ids)]
                if line_id in valid_line_ids
            ]
            if len(candidate_line_ids) != len(group_opt_ids):
                return {}
            common_continuation_id = ""
            for line_id in timeline_line_ids[after_index + 1 + len(group_opt_ids) :]:
                if line_id in valid_line_ids:
                    common_continuation_id = line_id
                    break
            preferred_rows = [preferred_timeline_option_row(opt_id) for opt_id in group_opt_ids]
            return {
                "code": "inferredFollowingLines",
                "reason": "optionTargetsMissing",
                "detail": (
                    "Timeline option metadata anchors this group to a trunk line, "
                    "but the option entries do not name explicit target trunk ids; "
                    "the following line candidates are inferred from Timeline order."
                ),
                "after": after_id,
                "optionIds": group_opt_ids,
                "candidateLineIds": candidate_line_ids,
                "commonContinuationLineId": common_continuation_id,
                "source": "dialogTimeline",
                "optionIndex": [
                    row.get("optionIndex")
                    for row in preferred_rows
                ],
                "assetTracks": _unique_preserve([
                    str(row.get("assetTrack") or "")
                    for row in preferred_rows
                    if row.get("assetTrack")
                ]),
            }

        for order, g in enumerate(sorted(groups_map), start=1):
            opts = sorted(groups_map[g], key=lambda o: o["i"])
            group_opt_ids = group_option_ids_by_group.get(g, [])
            cinematic_after_candidate = cinematic_after_by_group.get(g, "")
            cinematic_group_sources = cinematic_sources_by_group.get(g, [])
            text_alias_after_candidate = text_alias_after_by_group.get(g, "")
            text_alias_group_sources = text_alias_sources_by_group.get(g, [])
            text_alias_foreign_option_ids = text_alias_foreign_option_ids_by_group.get(g, [])
            group = {"g": g, "options": opts}
            rendered_branch_paths: list[tuple[str, ...]] = []
            after = None
            tree_after_option_ids: list[str] = []
            scene_link_after_option_ids: list[str] = []
            timeline_after_option_ids: list[str] = []
            cinematic_after_option_ids: list[str] = []
            text_alias_after_option_ids: list[str] = []
            for opt in opts:
                opt_id = opt.get("id") or ""
                tree_after_candidate = tree_after.get(opt_id) or ""
                scene_link_after_candidate = scene_link_after.get(opt_id) or ""
                timeline_after_candidate = timeline_after.get(opt_id) or ""
                if timeline_after_candidate and timeline_after_candidate not in valid_line_ids:
                    timeline_after_candidate = _nearest_visible_timeline_anchor(
                        timeline_after_candidate,
                        timeline_after_line_ids.get(opt_id) or [],
                        valid_line_ids,
                    )
                if tree_after_candidate and tree_after_candidate in valid_line_ids:
                    tree_after_option_ids.append(opt_id)
                if scene_link_after_candidate and scene_link_after_candidate in valid_line_ids:
                    scene_link_after_option_ids.append(opt_id)
                if timeline_after_candidate and timeline_after_candidate in valid_line_ids:
                    timeline_after_option_ids.append(opt_id)
                if cinematic_after_candidate and cinematic_after_candidate in valid_line_ids:
                    cinematic_after_option_ids.append(opt_id)
                if text_alias_after_candidate and text_alias_after_candidate in valid_line_ids:
                    text_alias_after_option_ids.append(opt_id)
                authored_after_candidates = [
                    tree_after_candidate,
                    scene_link_after_candidate,
                    timeline_after_candidate,
                ]
                after = next(
                    (
                        candidate_after
                        for candidate_after in authored_after_candidates
                        if candidate_after and candidate_after in valid_line_ids
                    ),
                    None,
                )
                if after:
                    break
            if (
                after == cinematic_after_candidate
                and cinematic_after_candidate
                and cinematic_after_candidate in valid_line_ids
            ):
                cinematic_after_option_ids = list(group_opt_ids)
            if (
                after == text_alias_after_candidate
                and text_alias_after_candidate
                and text_alias_after_candidate in valid_line_ids
            ):
                text_alias_after_option_ids = list(group_opt_ids)
            after_is_authored = bool(after)
            for opt in opts:
                opt_id = opt.get("id") or ""
                branch_lines = [
                    lid for lid in (tree_branches.get(opt_id) or [])
                    if lid in valid_line_ids
                ]
                if branch_lines:
                    opt["branchLines"] = branch_lines
                rendered_branch_paths.append(tuple(branch_lines))
            pre_option_ids = [opt_id for opt_id in group_opt_ids if opt_id in tree_pre]
            timeline_pre_option_ids = [opt_id for opt_id in group_opt_ids if opt_id in timeline_pre]
            text_alias_pre_option_ids = list(group_opt_ids) if g in text_alias_pre_by_group else []
            authored_group_option_ids = [
                opt_id for opt_id in group_opt_ids if opt_id in authored_option_ids
            ]
            unauthored_group_option_ids = [
                opt_id for opt_id in group_opt_ids if opt_id and opt_id not in authored_option_ids
            ]
            group_is_authored_pre = bool(group_opt_ids) and all(
                opt_id in tree_pre or opt_id in timeline_pre
                for opt_id in group_opt_ids
            )
            used_group_fallback = False
            group_status = "unanchored"
            fallback_anchor_id = ""
            inferred_anchor_mode = ""
            sibling_anchor_record: dict | None = None
            if after_is_authored:
                authored_group_count += 1
                group_status = "authoredAfter"
            elif group_is_authored_pre:
                group["position"] = "pre"
                pre_group_count += 1
                group_status = "authoredPre"
            elif order - 1 < len(fallback_after_ids):
                fallback_anchor_id = fallback_after_ids[order - 1]
                used_fallback_layout = True
                used_group_fallback = True
                used_any_fallback_option_layout = True
                fallback_group_count += 1
                fallback_group_labels.append(f"g{g}")
                group_status = "fallbackAfter"
                inferred_anchor_mode = "sparseGap"
            elif (
                order - 1 < len(sibling_position_anchors)
                and sibling_position_anchors[order - 1].get("afterLineId") in valid_line_ids
            ):
                sibling_anchor_record = sibling_position_anchors[order - 1]
                fallback_anchor_id = sibling_anchor_record["afterLineId"]
                used_fallback_layout = True
                used_group_fallback = True
                used_any_fallback_option_layout = True
                fallback_group_count += 1
                fallback_group_labels.append(f"g{g}")
                group_status = "fallbackAfter"
                inferred_anchor_mode = "siblingTimelinePosition"
            elif g in fallback_group_line_ids:
                fallback_anchor_id = fallback_group_line_ids[g]
                used_fallback_layout = True
                used_group_fallback = True
                used_any_fallback_option_layout = True
                fallback_group_count += 1
                fallback_group_labels.append(f"g{g}")
                group_status = "fallbackAfter"
                inferred_anchor_mode = "lineNumber"
            elif last_line_fallback_id:
                fallback_anchor_id = last_line_fallback_id
                used_fallback_layout = True
                used_group_fallback = True
                used_any_fallback_option_layout = True
                fallback_group_count += 1
                fallback_group_labels.append(f"g{g}")
                group_status = "fallbackAfter"
                inferred_anchor_mode = "lastLine"
            else:
                unanchored_group_count += 1
            if after_is_authored and after:
                group["after"] = after
            elif used_group_fallback and fallback_anchor_id:
                group["after"] = fallback_anchor_id
            following_line_risk = following_line_risk_for_group(group_opt_ids, group.get("after") or "")
            if following_line_risk:
                group["optionBranchRisk"] = following_line_risk
                for opt, line_id in zip(opts, following_line_risk.get("candidateLineIds") or []):
                    opt.setdefault("riskTags", []).append({
                        "code": "inferredFollowingLine",
                        "lineId": line_id,
                        "reason": following_line_risk["reason"],
                    })
            if sibling_anchor_record and sibling_anchor_record.get("siblingScenes"):
                group["branchHint"] = {
                    "scenes": sibling_anchor_record["siblingScenes"],
                    "timeline": sibling_anchor_record.get("timeline") or "",
                }
            distinct_paths = set(rendered_branch_paths)
            if len(distinct_paths) >= 2:
                for opt in opts:
                    merge_id = tree_merge.get(opt.get("id") or "")
                    if merge_id and merge_id in valid_line_ids:
                        group["branchMerge"] = merge_id
                        break
            if used_group_fallback:
                group_has_authored_coverage = bool(group_opt_ids) and all(
                    opt_id in authored_option_ids for opt_id in group_opt_ids
                )
                if not group_has_authored_coverage:
                    used_any_fallback_option_layout = True
            group_details.append({
                "group": g,
                "status": group_status,
                "after": after or fallback_anchor_id or "",
                "position": group.get("position") or "",
                "inferredAnchorMode": inferred_anchor_mode,
                "optionIds": group_opt_ids,
                "authoredOptionIds": authored_group_option_ids,
                "unauthoredOptionIds": unauthored_group_option_ids,
                "treeAfterOptionIds": tree_after_option_ids,
                "sceneLinkAfterOptionIds": scene_link_after_option_ids,
                "timelineAfterOptionIds": timeline_after_option_ids,
                "cinematicAfterOptionIds": cinematic_after_option_ids,
                "textAliasAfterOptionIds": text_alias_after_option_ids,
                "textAliasPreOptionIds": text_alias_pre_option_ids,
                "textAliasSourceOptionIds": text_alias_foreign_option_ids,
                "preOptionIds": pre_option_ids,
                "timelinePreOptionIds": timeline_pre_option_ids,
                "fallbackAnchorId": fallback_anchor_id,
                "cinematicSources": cinematic_group_sources,
                "textAliasSources": text_alias_group_sources,
            })
            out.append(group)
        warnings: list[dict] = []
        if used_any_fallback_option_layout or (used_fallback_layout and not authored_option_ids):
            total_groups = len(out)
            if not authored_option_ids:
                reason_short = "noTreeReference"
                reason_text = (
                    "no AnimeStudio tree references any option for this scene; "
                    "group positions are unanchored and fallback candidates are diagnostic only"
                )
            elif authored_group_count + pre_group_count == 0:
                reason_short = "noAuthoredGroupAnchor"
                reason_text = (
                    "tree data exists for this scene's options but no group "
                    "received an authored anchor; fallback candidates are "
                    "diagnostic only"
                )
            else:
                reason_short = "partialAuthoredCoverage"
                reason_text = (
                    f"{authored_group_count + pre_group_count} of {total_groups} option "
                    f"groups anchored from tree data; {fallback_group_count} only have "
                    f"diagnostic fallback candidates ({', '.join(fallback_group_labels)})"
                )
            warnings.append({
                "code": "inferredOptionLayout",
                "reason": reason_short,
                "detail": reason_text,
                "groupBreakdown": {
                    "total": total_groups,
                    "authoredAfter": authored_group_count,
                    "authoredPre": pre_group_count,
                    "fallbackAfter": fallback_group_count,
                    "unanchored": unanchored_group_count,
                },
                "fallbackGroups": fallback_group_labels,
                "fallbackAnchorIds": fallback_after_ids,
                "groupDetails": group_details,
                "treeSources": tree_meta.get("sources") or [],
                "sceneLinkSources": sorted(scene_link_sources),
                "timelineSources": sorted(timeline_sources),
                "cinematicSources": sorted(cinematic_sources),
                "textAliasSources": sorted(text_alias_sources),
                "authoredOptionCount": len(authored_option_ids),
            })
        return {
            "groups": out,
            "warnings": warnings,
        }

    def attach_runtime_registry_debug(payload: dict) -> None:
        debug = payload.setdefault("_debug", {})
        if not isinstance(debug, dict):
            debug = {}
            payload["_debug"] = debug
        block = shared_build_runtime_registry_debug(
            payload, dialog_id_registry=dialog_id_registry
        )
        if block is None:
            debug.pop("runtimeRegistry", None)
            return
        debug["runtimeRegistry"] = block

    def attach_scene_order_warning(payload: dict) -> None:
        warning = shared_build_scene_order_disorder_warning(
            payload, dialog_id_registry=dialog_id_registry
        )
        if warning is None:
            return
        existing_warnings = [
            existing
            for existing in (payload.get("warnings") or [])
            if isinstance(existing, dict) and existing.get("code") != "sceneOrderDisorder"
        ]
        payload["warnings"] = [warning, *existing_warnings]

    def format_webui_timeline_seconds(value: float) -> str:
        seconds = max(0.0, float(value))
        minutes = int(seconds // 60)
        remaining = seconds - minutes * 60
        return f"{minutes}:{remaining:04.1f}"

    def build_duplicate_timestamp_warning(payload: dict) -> dict | None:
        buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for line in payload.get("lines") or []:
            if not isinstance(line, dict):
                continue
            ts = line.get("ts")
            if not isinstance(ts, (int, float)):
                continue
            debug = line.get("_debug") if isinstance(line.get("_debug"), dict) else {}
            timing_debug = debug.get("timelineTiming") if isinstance(debug, dict) else {}
            timeline = str(timing_debug.get("timeline") or "") if isinstance(timing_debug, dict) else ""
            buckets[(timeline, format_webui_timeline_seconds(ts))].append(line)

        groups: list[dict] = []
        for (timeline, label), lines_for_ts in sorted(
            buckets.items(),
            key=lambda item: min(float(line.get("ts") or 0.0) for line in item[1]),
        ):
            if len(lines_for_ts) < 2:
                continue
            group = {
                "timestamp": label,
                "lineIds": [str(line.get("id") or "") for line in lines_for_ts if line.get("id")],
                "lines": [
                    {
                        "id": str(line.get("id") or ""),
                        "actor": str(line.get("actor") or line.get("aid") or ""),
                        "ts": line.get("ts"),
                        "dur": line.get("dur"),
                    }
                    for line in lines_for_ts
                    if line.get("id")
                ],
            }
            if timeline:
                group["timeline"] = timeline
            groups.append(group)
        if not groups:
            return None
        line_ids: list[str] = []
        for group in groups:
            for line_id in group["lineIds"]:
                if line_id not in line_ids:
                    line_ids.append(line_id)
        return {
            "code": "duplicateTimestamps",
            "reason": "duplicateDisplayTimestamp",
            "detail": "two or more lines share the same WebUI timeline timestamp label within one timeline segment",
            "groups": groups,
            "lineIds": line_ids,
        }

    def attach_duplicate_timestamp_warning(payload: dict) -> None:
        warning = build_duplicate_timestamp_warning(payload)
        existing_warnings = [
            existing
            for existing in (payload.get("warnings") or [])
            if isinstance(existing, dict) and existing.get("code") != "duplicateTimestamps"
        ]
        if warning is None:
            if existing_warnings:
                payload["warnings"] = existing_warnings
            else:
                payload.pop("warnings", None)
            return
        payload["warnings"] = [*existing_warnings, warning]

    def extras_text(out_key: str) -> str:
        """Concatenate all extras text for an out_key so the index entry's
        search haystack covers summaries / dialog options."""
        parts: list[str] = []
        if out_key in summary_by_key:
            parts.extend(s["text"] for s in summary_by_key[out_key] if s.get("text"))
        if out_key in options_by_key:
            for opts in options_by_key[out_key].values():
                for o in opts:
                    if o["text"]:
                        parts.append(o["text"])
        return " ".join(parts)

    def graph_fragments_text(fragments: list[dict]) -> str:
        parts: list[str] = []
        for fragment in fragments or []:
            if fragment.get("sourceKey"):
                parts.append(str(fragment["sourceKey"]))
            if fragment.get("lineIds"):
                parts.extend(str(line_id) for line_id in fragment["lineIds"] if line_id)
            terminals = fragment.get("terminalCounts") or {}
            for label, count in terminals.items():
                if count:
                    parts.append(f"{label}:{count}")
            for group in fragment.get("optionGroups") or []:
                if group.get("after"):
                    parts.append(str(group["after"]))
                parts.extend(str(opt_id) for opt_id in group.get("optionIds") or [] if opt_id)
                for branch_lines in (group.get("branches") or {}).values():
                    parts.extend(str(line_id) for line_id in branch_lines if line_id)
                parts.extend(
                    str(line_id)
                    for line_id in (group.get("merge") or {}).values()
                    if line_id
                )
        return " ".join(parts)

    def scene_links_text(links: list[dict]) -> str:
        parts: list[str] = []
        for link in links or []:
            if link.get("sourceKey"):
                parts.append(str(link["sourceKey"]))
            if link.get("after"):
                parts.append(str(link["after"]))
            for opt in link.get("options") or []:
                if opt.get("optionId"):
                    parts.append(str(opt["optionId"]))
                if opt.get("firstLineId"):
                    parts.append(str(opt["firstLineId"]))
                if opt.get("firstSceneKey"):
                    parts.append(str(opt["firstSceneKey"]))
                if opt.get("terminal"):
                    parts.append(str(opt["terminal"]))
                if opt.get("outcomeKind"):
                    parts.append(str(opt["outcomeKind"]))
                loop = opt.get("loop") or {}
                if isinstance(loop, dict):
                    if loop.get("kind"):
                        parts.append(str(loop["kind"]))
                    parts.extend(str(scene_key) for scene_key in (loop.get("sceneKeys") or []) if scene_key)
                parts.extend(str(line_id) for line_id in (opt.get("pathLineIds") or []) if line_id)
                parts.extend(str(scene_key) for scene_key in (opt.get("sceneKeys") or []) if scene_key)
                parts.extend(str(scene_key) for scene_key in (opt.get("submenuSceneKeys") or []) if scene_key)
        return " ".join(parts)

    def dialog_story_issue_codes(payload: dict) -> list[str]:
        codes: list[str] = []
        warning = next(
            (
                item
                for item in (payload.get("warnings") or [])
                if isinstance(item, dict) and item.get("code") == "sceneOrderDisorder"
            ),
            None,
        )
        if isinstance(warning, dict):
            line_order = warning.get("lineOrder") if isinstance(warning.get("lineOrder"), dict) else {}
            option_layout = warning.get("optionLayout") if isinstance(warning.get("optionLayout"), dict) else {}

            line_order_status = str(line_order.get("status") or "")
            if line_order_status == "missing":
                codes.append("missingLineOrder")
            elif line_order_status == "partial":
                codes.append("partialLineOrder")
            elif line_order_status == "fallback":
                codes.append("fallbackLineOrder")
            if int(line_order.get("uncoveredLineCount") or 0) > 0:
                codes.append("uncoveredLines")
            if str(option_layout.get("status") or "") == "inferred":
                codes.append("inferredOptionLayout")
        if any(
            isinstance(item, dict) and item.get("code") == "duplicateTimestamps"
            for item in (payload.get("warnings") or [])
        ):
            codes.append("duplicateTimestamps")
        return codes

    print(
        f"Extras: summary={len(summary_by_key)} scenes ({summary_orphans} orphans), "
        f"options={len(options_by_key)} scenes ({option_orphans} orphans), "
        f"radioTargets={len(radio_targets_seen)} scenes, "
        f"radioStandalone={len(radio_rows)} conversations ({radio_orphans} orphans)"
    )

    index_entries: list[dict] = []
    story_env_entries_by_mission: dict[str, list[dict]] = defaultdict(list)
    scene_graph_links_by_key: dict[str, list[dict]] = {}

    # Emit dialog conversations
    print(f"Writing {len(groups)} dialog conversations...")
    for key, items in groups.items():
        items.sort(key=lambda x: x[0])
        _, mission, scene_str = key.split("__")
        scene = int(scene_str)
        type_, act = parse_mission(mission)

        lines = []
        actors: set[str] = set()
        for _line, dlg_id, e in items:
            actor_id = e.get("actorNameId") or ""
            actor = t(e.get("actorName", {}).get("id"))
            text = t(e.get("dialogText", {}).get("id"))
            hint = t(e.get("hint", {}).get("id"))
            audio = e.get("audioOverride") or ""
            emo = e.get("emotionType", 0)
            if actor_id:
                actors.add(actor_id)
            lines.append({
                "id": dlg_id,
                "aid": actor_id,
                "actor": actor,
                "text": text,
                "hint": hint,
                "audio": audio,
                "emo": emo,
                "_debug": {
                    **source_ref(
                        "DialogTextTable",
                        dlg_id,
                        pick_fields(
                            e,
                            "actorNameId",
                            "actorName",
                            "dialogText",
                            "hint",
                            "audioOverride",
                            "emotionType",
                        ),
                    ),
                    "fields": {
                        "actor": text_trace("DialogTextTable", dlg_id, "actorName", e.get("actorName")),
                        "text": text_trace("DialogTextTable", dlg_id, "dialogText", e.get("dialogText")),
                        "hint": text_trace("DialogTextTable", dlg_id, "hint", e.get("hint")),
                    },
                },
            })

        out_key = f"dlg_{mission}_{scene}"
        ordered_line_ids, line_order_debug = resolve_scene_line_order(
            out_key,
            [line.get("id") or "" for line in lines],
        )
        if ordered_line_ids:
            line_order_index = {line_id: idx for idx, line_id in enumerate(ordered_line_ids)}
            lines = [
                line
                for _idx, line in sorted(
                    enumerate(lines),
                    key=lambda item: (
                        line_order_index.get(item[1].get("id") or "", len(ordered_line_ids) + item[0]),
                        item[0],
                    ),
                )
            ]
        prev_text = next((line.get("text") or "" for line in lines if line.get("text")), "")
        payload = {
            "key": out_key,
            "kind": "dlg",
            "mission": mission,
            "scene": scene,
            "lines": lines,
            "_debug": {
                "title": mission_name_trace(mission),
            },
        }
        if line_order_debug:
            payload["_debug"]["lineOrder"] = line_order_debug
        # Attach Unity Timeline timing per line so the conv view can render a
        # 00:54-style gutter alongside each line. Only sets "ts" / "dur" when
        # the recovery JSON actually has a timestamp for the line.
        line_timings = collect_line_timings(out_key)
        if line_timings:
            for line in lines:
                timing = line_timings.get(line.get("id") or "")
                if not timing:
                    continue
                if isinstance(timing.get("start"), (int, float)):
                    line["ts"] = timing["start"]
                if isinstance(timing.get("duration"), (int, float)):
                    line["dur"] = timing["duration"]
                timing_debug = {
                    key: timing[key]
                    for key in ("timeline", "start", "duration")
                    if timing.get(key) not in (None, "")
                }
                if timing_debug:
                    line.setdefault("_debug", {})["timelineTiming"] = timing_debug
        # Cross-link with other dialog scenes that share this scene's Unity
        # Timeline. Surfaces cases like dlg_e2m6_11 + dlg_e2m6_19 where a single
        # cinematic recording is split into two DialogTextTable scenes.
        related = collect_related_scenes(out_key)
        if related:
            payload["relatedScenes"] = related
        if out_key in summary_by_key:
            payload["summary"] = summary_by_key[out_key]
        if out_key in options_by_key:
            packed_options = pack_options(options_by_key[out_key], lines, out_key)
            payload["optionGroups"] = packed_options["groups"]
            if packed_options["warnings"]:
                payload["warnings"] = packed_options["warnings"]
        line_graph = build_dialog_tree_line_graph_payload(
            out_key,
            [line.get("id") or "" for line in lines],
        )
        if line_graph:
            payload["lineGraph"] = line_graph
        graph_fragments = build_dialog_tree_fragment_payload(out_key)
        if graph_fragments:
            payload["graphFragments"] = graph_fragments
        scene_graph_links = build_dialog_tree_scene_link_payload(out_key)
        if scene_graph_links:
            payload["sceneGraphLinks"] = scene_graph_links
            scene_graph_links_by_key[out_key] = scene_graph_links
        attach_runtime_registry_debug(payload)
        attach_scene_order_warning(payload)
        attach_duplicate_timestamp_warning(payload)
        story_issue_codes = dialog_story_issue_codes(payload)
        with (conv_dir / f"{out_key}.json").open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

        entry = {
            "k": out_key,                # key
            "d": "dlg",                  # kind
            "m": mission,                # mission id
            "s": scene,                  # scene number
            "t": type_,                  # type prefix (a/c/e/f/m)
            "a": act,                    # act number
            "c": sorted(actors),         # actor ids
            "n": len(lines),             # line count
            "p": preview(prev_text),     # text preview
        }
        if (tags := entry_tags(out_key, mission)):
            entry["tags"] = tags
        entry["x"] = merge_search_text(
            line_haystack(lines, "text", "actor", "aid", "hint"),
            extras_text(out_key),
        )
        entry["x"] = merge_search_text(entry.get("x", ""), mission_context_text(mission))
        entry["x"] = merge_search_text(entry.get("x", ""), graph_fragments_text(graph_fragments))
        entry["x"] = merge_search_text(entry.get("x", ""), scene_links_text(scene_graph_links))
        if graph_fragments:
            tags = entry.setdefault("tags", [])
            if "graphFragment" not in tags:
                tags.append("graphFragment")
        if scene_graph_links:
            tags = entry.setdefault("tags", [])
            if "sceneGraph" not in tags:
                tags.append("sceneGraph")
        if story_issue_codes:
            entry["storyIssues"] = story_issue_codes
        if not entry["x"]:
            entry.pop("x")
        index_entries.append(entry)

    # Emit SNS conversations
    print(f"Writing {len(sns_groups)} SNS conversations...")
    for sns_id, entry in sns_groups.items():
        m = SNS_RE.match(sns_id)
        mission = m.group(1) if m else sns_id
        scene = int(m.group(2)) if m else 0
        is_topic_chat = sns_id.startswith("sns_topic_") and bool(entry.get("chatId"))
        if is_topic_chat:
            mission = f"topic_{entry.get('chatId')}"
        type_, act = parse_mission(mission)

        # Reconstruct order by following nextContentId from -1's preContentId backwards,
        # then forwards from the first node whose preContentId == 0.
        cdata = entry.get("dialogContentData", {})
        # The "-1" sentinel marks the end; its preContentId is the last real node.
        # Find the start: the node whose preContentId == 0 (or 1 if absent).
        start = None
        for cid, node in cdata.items():
            if node.get("preContentId") == 0 and cid != "-1":
                start = cid
                break
        ordered = []
        seen = set()
        cur = start or "1"
        while cur and cur in cdata and cur not in seen:
            seen.add(cur)
            node = cdata[cur]
            if str(node.get("contentId")) == "-1":
                break
            ordered.append((cur, node))
            nxt = node.get("nextContentId")
            cur = str(nxt) if nxt not in (None, 0, -1) else None

        # Fallback: if traversal looks incomplete, append remaining numeric nodes by id.
        if len(ordered) < sum(1 for cid in cdata if cid not in ("-1",)):
            for cid in sorted((c for c in cdata if c not in ("-1",)), key=lambda x: int(x)):
                if cid not in seen:
                    seen.add(cid)
                    ordered.append((cid, cdata[cid]))

        lines = []
        speakers: list[str] = []
        seen_speakers: set[str] = set()
        prev_text = ""
        for order_idx, (cid, node) in enumerate(ordered, start=1):
            speaker = node.get("speaker") or ""
            text = sns_content_text(node)
            options = []
            for opt_id in node.get("dialogOptionIds", []) or []:
                opt = sns_opts.get(opt_id)
                if not opt:
                    continue
                option_text = sns_option_display_text(opt)
                option_res_path = str(opt.get("optionResPath") or "").strip()
                option_entry = {
                    "id": opt_id,
                    "text": option_text,
                    "next": opt.get("optionNextContentId"),
                    "_debug": {
                        **source_ref(
                            "SNSDialogOptionTable",
                            opt_id,
                            pick_fields(
                                opt,
                                "optionDesc",
                                "optionNextContentId",
                                "optionResPath",
                            ),
                        ),
                        "fields": {
                            "text": text_trace(
                                "SNSDialogOptionTable", opt_id, "optionDesc", opt.get("optionDesc")
                            ),
                        },
                    },
                }
                if option_res_path:
                    option_entry["image"] = option_res_path
                    option_entry["emoji"] = option_res_path
                    option_entry["_debug"]["fields"]["image"] = {
                        "table": "SNSDialogOptionTable",
                        "rowId": opt_id,
                        "field": "optionResPath",
                        "raw": option_res_path,
                        "lookup": [
                            {
                                "from": f"SNSDialogOptionTable[{opt_id}].optionResPath",
                                "value": option_res_path,
                            }
                        ],
                        "text": option_text,
                    }
                options.append(option_entry)
            if speaker and speaker not in seen_speakers:
                seen_speakers.add(speaker)
                speakers.append(speaker)
            line_entry = {
                "cid": int(cid),
                "speaker": speaker,
                "text": text,
                "type": node.get("contentType", 1),
                "options": options,
                "linkMission": node.get("linkMissionId") or "",
                "_debug": {
                    **source_ref(
                        "SNSDialogTable.dialogContentData",
                        sns_id,
                        pick_fields(
                            node,
                            "contentId",
                            "preContentId",
                            "nextContentId",
                            "speaker",
                            "content",
                            "contentParam",
                            "contentParams",
                            "contentType",
                            "dialogOptionIds",
                            "linkMissionId",
                            "optionType",
                        ),
                        nodeId=cid,
                        order=order_idx,
                    ),
                    "fields": {
                        "text": text_trace(
                            "SNSDialogTable.dialogContentData", sns_id, "content", node.get("content")
                        ),
                    },
                },
            }
            if node.get("contentType") == 2:
                image_ids = [
                    str(value or "").strip()
                    for value in (node.get("contentParam") or [])
                    if str(value or "").strip()
                ]
                if image_ids:
                    line_entry["images"] = image_ids
                    line_entry["_debug"]["fields"]["images"] = {
                        "table": "SNSDialogTable.dialogContentData",
                        "rowId": sns_id,
                        "field": "contentParam",
                        "raw": node.get("contentParam"),
                        "lookup": [
                            {
                                "from": f"SNSDialogTable.dialogContentData[{sns_id}].contentParam",
                                "value": image_ids,
                            }
                        ],
                        "text": text,
                    }
            lines.append(line_entry)
            if not prev_text and text:
                prev_text = text

        # Keep each SNS conversation keyed by its original table row id so
        # topic chats can share a chat-based mission bucket without colliding
        # in the index or overwriting each other's conv JSON files.
        out_key = sns_id
        title_topic_id = entry.get("topicId") or mission.removeprefix("topic_")
        topic_title_trace = topic_name_trace(title_topic_id)
        chat_title_trace = chat_name_trace(entry.get("chatId", "")) if is_topic_chat else None
        mission_title_trace = mission_name_trace(mission)
        chat_title = chat_name(entry.get("chatId", "")) if is_topic_chat else ""
        mission_title = mission_name(mission)
        topic_title = topic_name(title_topic_id)
        display_title = topic_title or chat_title or mission_title or sns_raw_title(out_key)
        display_title_debug = (
            topic_title_trace
            or chat_title_trace
            or mission_title_trace
            or {"source": sns_raw_title(out_key)}
        )
        def is_admin_sns_speaker(speaker_id: str) -> bool:
            return (speaker_actor_id(speaker_id) or speaker_id).lower() in ADMIN_ACTOR_IDS

        chat_id = str(entry.get("chatId") or "")
        primary_speaker = speakers[0] if speakers else ""
        if primary_speaker and is_admin_sns_speaker(primary_speaker):
            primary_speaker = speakers[1] if len(speakers) > 1 else ""
        if primary_speaker and is_admin_sns_speaker(primary_speaker):
            primary_speaker = next(
                (speaker for speaker in speakers if not is_admin_sns_speaker(speaker)),
                "",
            )
        if not primary_speaker and chat_id and not is_admin_sns_speaker(chat_id):
            primary_speaker = chat_id
        index_speakers = (
            [primary_speaker] + [speaker for speaker in speakers if speaker != primary_speaker]
            if primary_speaker else speakers
        )

        sns_payload = {
            "key": out_key,
            "kind": "sns",
            "mission": mission,
            "scene": scene,
            "title": display_title,
            "chatId": chat_id,
            "chatGroupSpeaker": primary_speaker,
            "relatedMissionId": entry.get("relatedMissionId", ""),
            "lines": lines,
            "_debug": {
                "source": source_ref(
                    "SNSDialogTable",
                    sns_id,
                    pick_fields(entry, "chatId", "relatedMissionId", "topicId", "dialogContentData"),
                ),
                "title": display_title_debug,
            },
        }
        with (conv_dir / f"{out_key}.json").open("w", encoding="utf-8") as f:
            json.dump(sns_payload, f, ensure_ascii=False, separators=(",", ":"))

        entry = {
            "k": out_key,
            "d": "sns",
            "m": mission,
            "s": scene,
            "t": type_,
            "a": act,
            "title": display_title,
            "chatId": chat_id,
            "chatGroupSpeaker": primary_speaker,
            "c": index_speakers,
            "n": len(lines),
            "p": preview(prev_text),
        }
        if (tags := entry_tags(out_key, mission)):
            entry["tags"] = tags
        sns_line_text = line_haystack(lines, "text", "speaker", "linkMission")
        sns_option_text = " ".join(
            str(option.get("text") or "")
            for line in lines
            for option in (line.get("options") or [])
            if option.get("text")
        )
        entry["x"] = merge_search_text(
            display_title,
            sns_line_text,
        )
        entry["x"] = merge_search_text(
            entry["x"],
            sns_option_text,
        )
        entry["x"] = merge_search_text(
            entry["x"],
            extras_text(out_key),
        )
        entry["x"] = merge_search_text(
            entry["x"],
            mission_context_text(mission),
        )
        if not entry["x"]:
            entry.pop("x")
        index_entries.append(entry)

    # Emit radio conversations as standalone entries. Radio is no longer
    # embedded into dlg/sns/misc pages; the browser should navigate to the
    # explicit radio scene instead.
    print(f"Writing {len(radio_rows)} radio conversations...")
    for radio in sorted(
        radio_rows,
        key=lambda item: (item["t"], item["a"], item["m"], item["s"], item["k"]),
    ):
        out_key = radio["k"]
        payload = {
            "key": out_key,
            "kind": "radio",
            "mission": radio["m"],
            "scene": radio["scene"],
            "radioType": radio["radioType"],
            "lines": radio["lines"],
            "_debug": {
                "source": radio["_debug"],
                "title": mission_name_trace(radio["m"]),
            },
        }
        if radio["target"]:
            payload["_debug"]["attachedTo"] = {
                "source": {
                    "key": radio["target"],
                }
            }
        with (conv_dir / f"{out_key}.json").open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        radio_out_keys.add(out_key)

        entry = {
            "k": out_key,
            "d": "radio",
            "m": radio["m"],
            "s": radio["s"],
            "t": radio["t"],
            "a": radio["a"],
            "c": radio["c"],
            "n": len(radio["lines"]),
            "p": radio["p"],
            "tags": ["radio"],
        }
        if (xt := line_haystack(radio["lines"], "text", "actor", "aid")):
            entry["x"] = xt
        entry["x"] = merge_search_text(entry.get("x", ""), mission_context_text(radio["m"]))
        if not entry["x"]:
            entry.pop("x")
        index_entries.append(entry)

    radio_row_lookup = {row["k"]: row for row in radio_rows}

    black_groups: dict[str, dict] = {}
    for text_id, text_entry in text_table.items():
        m = BLACK_RE.match(text_id)
        if not m:
            continue
        mission, scene, line_str = m.group(1), m.group(2), m.group(3)
        out_key = f"black_{mission}_{scene}"
        bucket = black_groups.setdefault(
            out_key,
            {
                "mission": mission,
                "scene": scene,
                "items": [],
            },
        )
        bucket["items"].append((int(line_str), text_id, text_entry))

    print(f"Writing {len(black_groups)} black-screen conversations...")
    for out_key, bucket in sorted(
        black_groups.items(),
        key=lambda item: (
            parse_mission(item[1]["mission"])[0],
            parse_mission(item[1]["mission"])[1],
            item[1]["mission"],
            scene_sort_value(item[1]["scene"]),
            item[0],
        ),
    ):
        mission = bucket["mission"]
        scene = bucket["scene"]
        type_, act = parse_mission(mission)
        lines = []
        prev_text = ""
        for _order, text_id, text_entry in sorted(bucket["items"], key=lambda item: (item[0], item[1])):
            text = t(text_entry.get("id") if isinstance(text_entry, dict) else text_entry)
            lines.append({
                "id": text_id,
                "text": text,
                "_debug": {
                    **source_ref(
                        "TextTable",
                        text_id,
                        pick_fields(text_entry, "id", "text") if isinstance(text_entry, dict) else {"value": text_entry},
                    ),
                    "fields": {
                        "text": text_trace("TextTable", text_id, "id", text_entry),
                    },
                },
            })
            if not prev_text and text:
                prev_text = text

        payload = {
            "key": out_key,
            "kind": "black",
            "mission": mission,
            "scene": scene,
            "lines": lines,
            "_debug": {
                "title": mission_name_trace(mission),
            },
        }
        with (conv_dir / f"{out_key}.json").open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        black_out_keys.add(out_key)

        entry = {
            "k": out_key,
            "d": "black",
            "m": mission,
            "s": scene_sort_value(scene),
            "t": type_,
            "a": act,
            "c": [],
            "n": len(lines),
            "p": preview(prev_text),
        }
        if (xt := line_haystack(lines, "text")):
            entry["x"] = xt
        entry["x"] = merge_search_text(entry.get("x", ""), mission_context_text(mission))
        if not entry["x"]:
            entry.pop("x")
        index_entries.append(entry)

    remote_rows: list[dict] = []
    for remote_id, remote_entry in remote_common.items():
        m = REMOTECOMM_RE.match(remote_id)
        if not m:
            continue
        mission = m.group(1)
        scene = m.group(2) or "0"
        type_, act = parse_mission(mission)
        lines = []
        actors: set[str] = set()
        prev_text = ""

        for item in sorted(
            remote_entry.get("remoteCommSingleDataList", []) or [],
            key=lambda row: row.get("index", 0),
        ):
            actor_list = [str(actor_id) for actor_id in (item.get("actorList") or []) if actor_id]
            actor_id = str(item.get("middleId") or (actor_list[0] if actor_list else ""))
            actor = t(item.get("actorName", {}).get("id"))
            text = t(item.get("remoteCommText", {}).get("id"))
            hint = t(item.get("hint", {}).get("id"))
            if actor_id:
                actors.add(actor_id)
            lines.append({
                "id": item.get("singleId") or remote_id,
                "cid": item.get("index"),
                "aid": actor_id,
                "actor": actor,
                "text": text,
                "hint": hint,
                "audio": item.get("audioId") or "",
                "voice": item.get("voiceId") or "",
                "_debug": {
                    **source_ref(
                        "RemoteCommonTable.remoteCommSingleDataList",
                        item.get("singleId") or remote_id,
                        pick_fields(
                            item,
                            "actorList",
                            "actorName",
                            "audioId",
                            "hint",
                            "imageList",
                            "index",
                            "isVideoLoop",
                            "middleId",
                            "musicId",
                            "remoteCommText",
                            "singleId",
                            "voiceId",
                        ),
                        rowId=remote_id,
                    ),
                    "fields": {
                        "actor": text_trace(
                            "RemoteCommonTable.remoteCommSingleDataList",
                            item.get("singleId") or remote_id,
                            "actorName",
                            item.get("actorName"),
                        ),
                        "text": text_trace(
                            "RemoteCommonTable.remoteCommSingleDataList",
                            item.get("singleId") or remote_id,
                            "remoteCommText",
                            item.get("remoteCommText"),
                        ),
                        "hint": text_trace(
                            "RemoteCommonTable.remoteCommSingleDataList",
                            item.get("singleId") or remote_id,
                            "hint",
                            item.get("hint"),
                        ),
                    },
                },
            })
            if not prev_text and text:
                prev_text = text

        remote_rows.append({
            "key": remote_id,
            "mission": mission,
            "scene": scene,
            "type": type_,
            "act": act,
            "actors": sorted(actors),
            "lines": lines,
            "preview": prev_text,
            "source": remote_entry,
        })

    print(f"Writing {len(remote_rows)} remote communication conversations...")
    for remote in sorted(
        remote_rows,
        key=lambda item: (
            item["type"],
            item["act"],
            item["mission"],
            scene_sort_value(item["scene"]),
            item["key"],
        ),
    ):
        payload = {
            "key": remote["key"],
            "kind": "remotecomm",
            "mission": remote["mission"],
            "scene": remote["scene"],
            "lines": remote["lines"],
            "_debug": {
                "source": source_ref(
                    "RemoteCommonTable",
                    remote["key"],
                    pick_fields(remote["source"], "autoPlay", "endAudioEvent", "remoteCommSingleDataList"),
                ),
                "title": mission_name_trace(remote["mission"]),
            },
        }
        with (conv_dir / f"{remote['key']}.json").open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        remotecomm_out_keys.add(remote["key"])

        entry = {
            "k": remote["key"],
            "d": "remotecomm",
            "m": remote["mission"],
            "s": scene_sort_value(remote["scene"]),
            "t": remote["type"],
            "a": remote["act"],
            "c": remote["actors"],
            "n": len(remote["lines"]),
            "p": preview(remote["preview"]),
        }
        if (xt := line_haystack(remote["lines"], "text", "actor", "aid", "hint")):
            entry["x"] = xt
        entry["x"] = merge_search_text(entry.get("x", ""), mission_context_text(remote["mission"]))
        if not entry["x"]:
            entry.pop("x")
        index_entries.append(entry)

    known_cutscene_missions = sorted(
        {
            path.stem
            for path in MRA_DIR.glob("*.json")
            if path.stem and not path.stem.endswith("_meta")
        }
        | {
            entry["m"]
            for entry in index_entries
            if entry.get("m")
        },
        key=lambda mission: (-len(mission), mission),
    )

    def normalize_cutscene_text_group(group: str) -> str:
        match = re.match(r"^(.*_)(0+)(\d+)$", group)
        if not match:
            return group
        return f"{match.group(1)}{int(match.group(3))}"

    def resolve_cutscene_text_group(group: str, asset_keys: set[str], raw_groups: set[str]) -> str:
        if group in asset_keys:
            return group
        normalized = normalize_cutscene_text_group(group)
        if normalized != group:
            if normalized in asset_keys:
                return normalized
            if normalized in raw_groups:
                return group
        if normalized in asset_keys:
            return normalized
        for candidate in sorted(asset_keys, key=lambda key: (-len(key), key)):
            if not group.startswith(candidate):
                continue
            rest = group[len(candidate):]
            if rest and re.fullmatch(r"d\d+(?:_.*)?", rest):
                return candidate
        return normalized

    def merge_duplicate_cutscene_rows(rows: list[tuple[tuple[int, int, int, str, str], dict]]) -> list[dict]:
        merged: list[dict] = []
        seen: dict[tuple[str, str, str], dict] = {}
        for _sort_key, line in sorted(rows, key=lambda item: item[0]):
            dedupe_key = (
                str(line.get("cid") or ""),
                str(line.get("gender") or ""),
                str(line.get("text") or ""),
            )
            existing = seen.get(dedupe_key)
            if existing is None:
                seen[dedupe_key] = line
                merged.append(line)
                continue

            duplicate = {"id": line.get("id") or ""}
            if line.get("textGroup"):
                duplicate["textGroup"] = line["textGroup"]
            if line.get("sub"):
                duplicate["sub"] = line["sub"]
            if line.get("gender"):
                duplicate["gender"] = line["gender"]
            existing.setdefault("mergedDuplicateRows", []).append(duplicate)
            existing_debug = existing.setdefault("_debug", {})
            existing_debug.setdefault("mergedDuplicateRows", []).append(duplicate)
            existing_source = existing_debug.setdefault("source", {})
            merged_row_ids = existing_source.setdefault("mergedDuplicateRowIds", [])
            if duplicate["id"] and duplicate["id"] not in merged_row_ids:
                merged_row_ids.append(duplicate["id"])
            if duplicate.get("textGroup"):
                merged_groups = existing_source.setdefault("mergedDuplicateTextGroups", [])
                if duplicate["textGroup"] not in merged_groups:
                    merged_groups.append(duplicate["textGroup"])
        return merged

    def cutscene_line_text_groups(cutscene_key: str, lines: list[dict]) -> list[str]:
        groups: list[str] = []
        for line in lines:
            for group in [
                str(line.get("textGroup") or cutscene_key),
                *[
                    str(duplicate.get("textGroup") or "")
                    for duplicate in (line.get("mergedDuplicateRows") or [])
                    if isinstance(duplicate, dict)
                ],
            ]:
                if group and group not in groups:
                    groups.append(group)
        return groups

    def cutscene_text_lines(asset_keys: set[str]) -> dict[str, list[dict]]:
        raw_groups: set[str] = set()
        matched_rows: list[tuple[str, dict, re.Match[str]]] = []
        for row_id, text_entry in text_table.items():
            row_key = str(row_id or "")
            if not row_key.startswith("cutscene_"):
                continue
            match = CUTSCENE_TEXT_ROW_RE.match(row_key)
            if not match:
                continue
            raw_groups.add(match.group("group"))
            matched_rows.append((row_key, text_entry, match))

        grouped: dict[str, list[tuple[tuple[int, int, str, str], dict]]] = defaultdict(list)
        for row_key, text_entry, match in matched_rows:
            raw_group = match.group("group")
            cutscene_key = resolve_cutscene_text_group(raw_group, asset_keys, raw_groups)
            line_num = int(match.group("line"))
            sub = match.group("sub") or ""
            gender = (match.group("gender") or "").strip("_").upper()
            cid = f"{match.group('line')}{sub}{('_' + gender.lower()) if gender else ''}"
            text = t(text_entry.get("id") if isinstance(text_entry, dict) else text_entry)
            remember_texttable_row_usage(row_key)
            line = {
                "id": row_key,
                "cid": cid,
                "text": text,
                "_debug": {
                    **source_ref(
                        "TextTable",
                        row_key,
                        pick_fields(text_entry, "id", "text") if isinstance(text_entry, dict) else {"value": text_entry},
                        cutsceneKey=cutscene_key,
                        textGroup=raw_group,
                        line=line_num,
                    ),
                    "fields": {
                        "text": text_trace("TextTable", row_key, "id", text_entry),
                    },
                },
            }
            if raw_group != cutscene_key:
                line["textGroup"] = raw_group
            if sub:
                line["sub"] = sub
                line["_debug"]["source"]["sub"] = sub
            if gender:
                line["gender"] = gender
                line["_debug"]["source"]["gender"] = gender
            sub_order = int(sub[1:]) if sub else -1
            alias_order = 1 if raw_group != cutscene_key else 0
            grouped[cutscene_key].append(((line_num, sub_order, alias_order, gender, row_key), line))
        return {
            key: merge_duplicate_cutscene_rows(rows)
            for key, rows in grouped.items()
        }

    def ensure_cutscene_asset(cutscene_key: str) -> dict:
        return cutscene_assets.setdefault(
            cutscene_key,
            {
                "variants": [],
                "componentCounts": {},
                "levels": [],
                "actorLabels": [],
                "paths": [],
                "versions": [],
                "audioEvents": [],
                "tags": [],
                "metadata": {},
                "keepCameraPaths": [],
                "useBlackScreen": False,
                "isTransition": False,
                "hasSubtitleTrack": False,
                "textOnly": True,
            },
        )

    cutscene_assets = _load_cutscene_assets()
    cutscene_text_by_key = cutscene_text_lines(set(cutscene_assets))
    for cutscene_key in cutscene_text_by_key:
        ensure_cutscene_asset(cutscene_key)
    print(f"Writing {len(cutscene_assets)} cutscene conversations...")
    for cutscene_key, cutscene in sorted(cutscene_assets.items()):
        mission, scene = _infer_cutscene_mission_and_scene(cutscene_key, known_cutscene_missions)
        type_, act = parse_mission(mission)
        if type_ not in MISSION_STORY_TYPES:
            type_, act = "x", 0
        lines = cutscene_text_by_key.get(cutscene_key, [])
        text_groups = cutscene_line_text_groups(cutscene_key, lines)
        summary_rows: list[dict] = []
        if cutscene.get("paths"):
            summary_rows.append({"text": f"AnimeStudio path: {cutscene['paths'][0]}"})
        if cutscene.get("levels"):
            summary_rows.append({"text": f"Levels: {', '.join(cutscene['levels'])}"})
        if cutscene.get("audioEvents"):
            summary_rows.append({"text": "Audio events: " + ", ".join(cutscene["audioEvents"][:8])})
        if cutscene.get("tags"):
            summary_rows.append({"text": "Tags: " + ", ".join(cutscene["tags"][:8])})
        metadata = cutscene.get("metadata") or {}
        if isinstance(metadata, dict) and metadata:
            metadata_parts = []
            for meta_key, values in list(metadata.items())[:8]:
                if isinstance(values, list):
                    metadata_parts.append(f"{meta_key}={', '.join(str(value) for value in values[:3])}")
                else:
                    metadata_parts.append(f"{meta_key}={values}")
            if metadata_parts:
                summary_rows.append({"text": "Metadata: " + "; ".join(metadata_parts)})
        component_summary = _cutscene_component_summary(cutscene)
        if component_summary:
            summary_rows.append({"text": f"Components: {component_summary}"})
        if cutscene.get("variants"):
            summary_rows.append({"text": f"Files: {len(cutscene['variants'])} exported asset(s)"})
        if cutscene.get("actorLabels"):
            summary_rows.append({
                "text": "Actors: " + ", ".join(cutscene["actorLabels"][:8]),
            })
        flags: list[str] = []
        if cutscene.get("isTransition"):
            flags.append("transition")
        if cutscene.get("useBlackScreen"):
            flags.append("black-screen")
        if cutscene.get("hasSubtitleTrack"):
            flags.append("subtitle-track")
        if cutscene.get("keepCameraPaths"):
            flags.append("keep-camera")
        if flags:
            summary_rows.append({"text": "Flags: " + ", ".join(flags)})
        if lines:
            summary_rows.append({"text": f"TextTable rows: {len(lines)} localized cutscene text row(s)"})
        if len(text_groups) > 1:
            summary_rows.append({"text": "Text groups: " + ", ".join(text_groups[:8])})

        payload = {
            "key": cutscene_key,
            "kind": "cutscene",
            "mission": mission,
            "scene": scene,
            "lines": lines,
            "summary": summary_rows,
            "cutscene": {
                "variants": cutscene.get("variants") or [],
                "levels": cutscene.get("levels") or [],
                "actorLabels": cutscene.get("actorLabels") or [],
                "paths": cutscene.get("paths") or [],
                "versions": cutscene.get("versions") or [],
                "audioEvents": cutscene.get("audioEvents") or [],
                "tags": cutscene.get("tags") or [],
                "textGroups": text_groups,
                "metadata": cutscene.get("metadata") or {},
                "componentCounts": cutscene.get("componentCounts") or {},
                "variantCount": len(cutscene.get("variants") or []),
                "keepCameraPaths": cutscene.get("keepCameraPaths") or [],
                "useBlackScreen": bool(cutscene.get("useBlackScreen")),
                "isTransition": bool(cutscene.get("isTransition")),
                "hasSubtitleTrack": bool(cutscene.get("hasSubtitleTrack")),
            },
            "_debug": {
                "title": mission_name_trace(mission),
                "source": {
                    "canonicalKey": cutscene_key,
                    "variants": cutscene.get("variants") or [],
                },
            },
        }
        with (conv_dir / f"{cutscene_key}.json").open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        cutscene_out_keys.add(cutscene_key)

        search_text = " ".join(part for part in [
            cutscene_key,
            mission,
            scene,
            " ".join(cutscene.get("levels") or []),
            " ".join(cutscene.get("actorLabels") or []),
            " ".join(cutscene.get("paths") or []),
            " ".join(cutscene.get("audioEvents") or []),
            " ".join(cutscene.get("tags") or []),
            " ".join(text_groups),
            line_haystack(lines, "text"),
            component_summary,
            " ".join(variant["name"] for variant in (cutscene.get("variants") or [])),
            " ".join(cutscene.get("keepCameraPaths") or []),
        ] if part)
        line_preview = next((line.get("text") or "" for line in lines if line.get("sub")), "")
        if not line_preview:
            line_preview = next((line.get("text") or "" for line in lines if line.get("text")), "")
        entry = {
            "k": cutscene_key,
            "d": "cutscene",
            "m": mission,
            "s": scene_sort_value(scene),
            "t": type_,
            "a": act,
            "c": [],
            "n": len(lines),
            "p": preview(line_preview or " | ".join(part for part in (
                component_summary,
                (cutscene.get("paths") or [""])[0] if cutscene.get("paths") else "",
                (", ".join(cutscene.get("levels") or []) if cutscene.get("levels") else ""),
                (", ".join(cutscene.get("actorLabels")[:3]) if cutscene.get("actorLabels") else ""),
            ) if part)),
            "tags": ["cutscene", *(["cutsceneText"] if lines else [])],
        }
        if search_text:
            entry["x"] = search_text
        entry["x"] = merge_search_text(entry.get("x", ""), mission_context_text(mission))
        if not entry["x"]:
            entry.pop("x")
        index_entries.append(entry)

    env_talk_speaker_hints_by_env: dict[str, list[dict]] = defaultdict(list)
    for env_id, proxy_ids in env_talk_proxy_ids_by_env.items():
        seen_hint_keys: set[tuple[str, str]] = set()
        for proxy_id in proxy_ids:
            row_id, proxy_row = npc_proxy_rows_by_proxy_id.get(proxy_id, ("", {}))
            proxy_info = npc_proxy_info.get(proxy_id) if isinstance(npc_proxy_info, dict) else None
            candidates = [*npc_proxy_actor_candidates(proxy_id), proxy_id]
            actor_id = ""
            speaker_name = ""
            for candidate in _unique_preserve(candidates):
                actor_id = speaker_actor_id(candidate) or (candidate if candidate in actor_names else "")
                speaker_name = speaker_display_name(candidate)
                if speaker_name:
                    break

            if not speaker_name and isinstance(proxy_row, dict):
                override_name_key = str(((proxy_row.get("overrideNpcNameId") or {}).get("key")) or "")
                if proxy_row.get("ifOverrideNpcName") and override_name_key:
                    speaker_name = named_text(override_name_key)
                    actor_id = actor_id or proxy_id

            if not speaker_name:
                continue
            hint_key = (actor_id or proxy_id, speaker_name)
            if hint_key in seen_hint_keys:
                continue
            seen_hint_keys.add(hint_key)
            env_talk_speaker_hints_by_env[env_id].append({
                "actorId": actor_id or proxy_id,
                "speakerName": speaker_name,
                "proxyId": proxy_id,
                "source": {
                    "table": "NpcProxyTable",
                    "rowId": row_id or proxy_id,
                    "fields": pick_fields(
                        proxy_row if isinstance(proxy_row, dict) else {},
                        "proxyId",
                        "levelId",
                        "envTalkIds",
                        "ifOverrideNpcName",
                        "overrideNpcNameId",
                    ),
                    "proxyInfoData": pick_fields(
                        proxy_info if isinstance(proxy_info, dict) else {},
                        "npcId",
                        "npcNameId",
                        "mapId",
                        "npcProxyType",
                    ),
                },
            })

    # Emit environment conversations
    print(f"Writing {len(env_talks)} environment conversations...")
    for env_id in sorted(env_talks):
        entry = env_talks[env_id]
        env_npc = env_npc_meta.get(env_id)
        env_speaker_hints = env_talk_speaker_hints_by_env.get(env_id) or []
        lines = []
        actors: set[str] = set()
        prev_text = ""
        for item in sorted(entry.get("envTalkDataList", []) or [], key=lambda x: x.get("index", 0)):
            raw_actor_id = str(item.get("actorId") or "").strip()
            raw_actor_name = speaker_display_name(raw_actor_id)
            speaker_hint = env_speaker_hints[0] if env_speaker_hints and not raw_actor_name else None
            actor_id = (
                (raw_actor_id if raw_actor_name or not speaker_hint else "")
                or ((speaker_hint or {}).get("actorId") if speaker_hint else "")
                or raw_actor_id
                or (env_npc.get("npcId") if env_npc else "")
                or ""
            )
            actor = (
                raw_actor_name
                or ((speaker_hint or {}).get("speakerName") if speaker_hint else "")
                or speaker_display_name(actor_id)
                or (env_npc.get("name") if env_npc else "")
                or (env_npc.get("title") if env_npc else "")
            )
            text = t(item.get("text", {}).get("id"))
            audio = item.get("audio") or ""
            emoji = item.get("emojiId") or ""
            duration = item.get("duration")
            slot = item.get("slotId")
            index = item.get("index")
            if actor_id:
                actors.add(actor_id)
            lines.append({
                "id": item.get("envTalkId") or env_id,
                "cid": index,
                "aid": actor_id,
                "actor": actor,
                "text": text,
                "audio": audio,
                "emoji": emoji,
                "duration": duration,
                "slot": slot,
                "_debug": {
                    **source_ref(
                        "EnvTalkTable.envTalkDataList",
                        item.get("envTalkId") or env_id,
                        pick_fields(
                            item,
                            "actorId",
                            "audio",
                            "duration",
                            "emojiId",
                            "envTalkId",
                            "index",
                            "slotId",
                            "text",
                        ),
                        nodeId=index,
                    ),
                    "fields": {
                        "text": text_trace(
                            "EnvTalkTable.envTalkDataList",
                            item.get("envTalkId") or env_id,
                            "text",
                            item.get("text"),
                        ),
                    },
                },
            })
            if speaker_hint:
                lines[-1]["_debug"]["speakerHint"] = speaker_hint
            if not prev_text and text:
                prev_text = text

        out_key = f"env_{env_id}"
        kind, mission, mission_type, index_tags = env_index_slot(env_id)
        env_payload = {
            "key": out_key,
            "kind": kind,
            "mission": mission,
            "title": env_id,
            "cooldown": entry.get("envTalkCd"),
            "lines": lines,
            "_debug": {
                "source": source_ref(
                    "EnvTalkTable",
                    env_id,
                    pick_fields(entry, "envTalkCd", "envTalkDataList", "envTalkId"),
                ),
            },
        }
        if env_speaker_hints:
            env_payload["_debug"]["speakerHints"] = env_speaker_hints
        if env_npc:
            env_payload["npc"] = env_npc
            env_payload["_debug"]["npc"] = env_npc["_debug"]
        with (conv_dir / f"{out_key}.json").open("w", encoding="utf-8") as f:
            json.dump(env_payload, f, ensure_ascii=False, separators=(",", ":"))

        index_entry = {
            "k": out_key,
            "d": kind,
            "m": mission,
            "s": 0,
            "t": mission_type,
            "a": 0,
            "title": env_id,
            "c": sorted(actors),
            "n": len(lines),
            "p": preview(prev_text),
            "tags": index_tags,
        }
        if (xt := line_haystack(lines, "text", "actor", "aid", "emoji")):
            index_entry["x"] = xt
        index_entry["x"] = merge_search_text(index_entry.get("x", ""), mission_context_text(mission))
        if not index_entry["x"]:
            index_entry.pop("x")
        index_entries.append(index_entry)

        if story_mission := env_story_missions.get(env_id):
            env_entry = {
                "key": out_key,
                "id": env_id,
                "cooldown": entry.get("envTalkCd"),
                "lines": lines,
                "_debug": {
                    "source": source_ref(
                        "EnvTalkTable",
                        env_id,
                        pick_fields(entry, "envTalkCd", "envTalkDataList", "envTalkId"),
                    ),
                },
            }
            if env_speaker_hints:
                env_entry["_debug"]["speakerHints"] = env_speaker_hints
            if env_npc:
                env_entry["npc"] = env_npc
                env_entry["_debug"]["npc"] = env_npc["_debug"]
            if hints := env_story_binding_hints.get(env_id):
                levels = sorted(hints["levels"])
                proxies = sorted(hints["proxies"])
                if levels or proxies:
                    env_entry["_attachHints"] = {
                        "levels": levels,
                        "proxies": proxies,
                    }
                    env_entry["_debug"]["bindingHints"] = {
                        "source": {
                            "levels": levels,
                            "proxyIds": proxies,
                            "refs": hints["sources"],
                        }
                    }
            story_env_entries_by_mission[story_mission].append(env_entry)

    wiki_category_names: dict[str, str] = {}
    wiki_group_names: dict[str, str] = {}
    wiki_group_to_category: dict[str, str] = {}
    for category_id, category_row in sorted(
        wiki_categories.items(),
        key=lambda item: (int((item[1] or {}).get("categoryPriority") or 0), item[0]),
    ):
        if not isinstance(category_row, dict):
            continue
        category_name = brace_text(t((category_row.get("categoryName") or {}).get("id"))) or category_id
        wiki_category_names[category_id] = category_name
        extra_mission_names.setdefault(category_id, category_name)
        group_rows = ((wiki_groups.get(category_id) or {}).get("list") or [])
        for group_row in group_rows:
            if not isinstance(group_row, dict):
                continue
            group_id = str(group_row.get("groupId") or "")
            if not group_id:
                continue
            group_name = brace_text(t((group_row.get("groupName") or {}).get("id"))) or group_id
            wiki_group_names[group_id] = group_name
            wiki_group_to_category[group_id] = category_id
            extra_mission_names.setdefault(group_id, group_name)

    def wiki_category_id(row_id: str, row: dict) -> str:
        group_id = str(row.get("groupId") or "")
        if group_id in wiki_group_to_category:
            return wiki_group_to_category[group_id]
        if row_id.startswith("wiki_tut_"):
            return "wiki_type_tutorial"
        if str(row.get("refMonsterTemplateId") or ""):
            return "wiki_type_monster"
        ref_item_id = str(row.get("refItemId") or "")
        if ref_item_id.startswith("wpn_"):
            return "wiki_type_weapon"
        if group_id.startswith("wiki_group_building_"):
            return "wiki_type_building"
        if group_id.startswith("wiki_group_weapon_"):
            return "wiki_type_weapon"
        if group_id.startswith("wiki_group_monster_"):
            return "wiki_type_monster"
        if group_id.startswith("wiki_group_tutorial_"):
            return "wiki_type_tutorial"
        if group_id.startswith("wiki_group_equip_") or group_id.startswith("suit_") or group_id.startswith("domain_"):
            return "wiki_type_equip"
        return "wiki_type_item"

    wiki_text_fingerprints: set[tuple[str, ...]] = set()

    print(f"Writing {len(wiki_entry_data)} wiki entries...")
    for row_id, row in sorted(
        wiki_entry_data.items(),
        key=lambda item: (
            wiki_category_id(item[0], item[1] if isinstance(item[1], dict) else {}),
            str((item[1] or {}).get("groupId") or ""),
            int((item[1] or {}).get("order") or 0),
            item[0],
        ),
    ):
        if not isinstance(row, dict):
            continue
        group_id = str(row.get("groupId") or "")
        category_id = wiki_category_id(row_id, row)
        category_name = wiki_category_names.get(category_id, category_id)
        group_name = wiki_group_names.get(group_id, group_id or category_name)
        mission_id = group_id or category_id
        if mission_id:
            extra_mission_names.setdefault(mission_id, group_name if group_id else category_name)

        row_desc = t((row.get("desc") or {}).get("id"))
        ref_item_id = str(row.get("refItemId") or "")
        ref_monster_id = str(row.get("refMonsterTemplateId") or "")
        prts_id = str(row.get("prtsId") or "")
        item_row = item_rows.get(ref_item_id) if isinstance(item_rows.get(ref_item_id), dict) else {}
        weapon_row = weapon_basic.get(ref_item_id) if isinstance(weapon_basic.get(ref_item_id), dict) else {}
        enemy_row = (
            enemy_template_display.get(ref_monster_id)
            if isinstance(enemy_template_display.get(ref_monster_id), dict)
            else enemy_display_info.get(ref_monster_id)
            if isinstance(enemy_display_info.get(ref_monster_id), dict)
            else {}
        )

        title = row_id
        lines: list[dict] = []
        summary_rows: list[dict] = []
        seen_texts: set[tuple[str, str]] = set()

        def add_line(line_id: str, text: str, *, hint: str = "", debug: dict | None = None) -> None:
            normalized = (text or "").strip()
            if not normalized:
                return
            key = (hint, normalized)
            if key in seen_texts:
                return
            seen_texts.add(key)
            line = {"id": line_id, "text": normalized}
            if hint:
                line["hint"] = hint
            if debug:
                line["_debug"] = debug
            lines.append(line)

        if category_id in {"wiki_type_item", "wiki_type_equip", "wiki_type_building", "wiki_type_weapon"}:
            title = brace_text(t((item_row.get("name") or {}).get("id"))) or title
            item_desc = t((item_row.get("desc") or {}).get("id"))
            deco_desc = t((item_row.get("decoDesc") or {}).get("id"))
            add_line(
                f"{row_id}_desc",
                item_desc,
                debug={
                    **source_ref("ItemTable", ref_item_id, pick_fields(item_row, "desc", "decoDesc", "id", "name", "obtainWayIds", "rarity", "type")),
                    "fields": {
                        "text": text_trace("ItemTable", ref_item_id, "desc", item_row.get("desc")),
                    },
                } if item_row else None,
            )
            add_line(
                f"{row_id}_deco",
                deco_desc,
                hint="Flavor",
                debug={
                    **source_ref("ItemTable", ref_item_id, pick_fields(item_row, "desc", "decoDesc", "id", "name")),
                    "fields": {
                        "text": text_trace("ItemTable", ref_item_id, "decoDesc", item_row.get("decoDesc")),
                    },
                } if item_row else None,
            )
            if category_id == "wiki_type_weapon":
                weapon_desc = t((weapon_row.get("weaponDesc") or {}).get("id"))
                add_line(
                    f"{row_id}_weapon",
                    weapon_desc,
                    hint="Weapon",
                    debug={
                        **source_ref("WeaponBasicTable", ref_item_id, pick_fields(weapon_row, "rarity", "weaponDesc", "weaponId", "weaponSkillList", "weaponType")),
                        "fields": {
                            "text": text_trace("WeaponBasicTable", ref_item_id, "weaponDesc", weapon_row.get("weaponDesc")),
                        },
                    } if weapon_row else None,
                )
                if weapon_row.get("weaponSkillList"):
                    summary_rows.append({"text": "Skills: " + ", ".join(str(skill_id) for skill_id in weapon_row.get("weaponSkillList") or [])})
            if item_row.get("rarity") is not None:
                summary_rows.append({"text": f"Rarity: {item_row['rarity']}"})
            if craft_row := (wiki_craft_jump.get(ref_item_id) if isinstance(wiki_craft_jump.get(ref_item_id), dict) else {}):
                if craft_row.get("blueprintId"):
                    summary_rows.append({"text": f"Blueprint: {craft_row['blueprintId']}"})
                if craft_row.get("blackboxId"):
                    summary_rows.append({"text": f"Blackbox: {craft_row['blackboxId']}"})
            if default_craft := str(wiki_default_craft.get(ref_item_id) or ""):
                summary_rows.append({"text": f"Default craft: {default_craft}"})
        elif category_id == "wiki_type_monster":
            title = (
                brace_text(t((enemy_row.get("name") or {}).get("id")))
                or brace_text(t((enemy_row.get("nickname") or {}).get("id")))
                or title
            )
            enemy_desc = t((enemy_row.get("description") or {}).get("id"))
            add_line(
                f"{row_id}_desc",
                enemy_desc,
                debug={
                    **source_ref(
                        "EnemyTemplateDisplayInfoTable",
                        ref_monster_id,
                        pick_fields(enemy_row, "abilityDescIds", "description", "name", "nickname", "templateId"),
                    ),
                    "fields": {
                        "text": text_trace("EnemyTemplateDisplayInfoTable", ref_monster_id, "description", enemy_row.get("description")),
                    },
                } if enemy_row else None,
            )
            nickname = brace_text(t((enemy_row.get("nickname") or {}).get("id")))
            if nickname and nickname != title:
                summary_rows.append({"text": f"Alias: {nickname}"})
            for ability_id in enemy_row.get("abilityDescIds") or []:
                ability_row = enemy_ability_desc.get(ability_id) if isinstance(enemy_ability_desc.get(ability_id), dict) else {}
                ability_name = brace_text(t((ability_row.get("name") or {}).get("id"))) or str(ability_id)
                ability_text = t((ability_row.get("description") or {}).get("id"))
                summary_rows.append({
                    "text": f"Ability: {ability_name}" + (f" - {ability_text}" if ability_text else ""),
                    "_debug": source_ref(
                        "EnemyAbilityDescTable",
                        str(ability_id),
                        pick_fields(ability_row, "abilityId", "description", "name"),
                    ) if ability_row else None,
                })
        elif category_id == "wiki_type_tutorial":
            page_ids = []
            page_ref_row = (
                wiki_tutorial_pages_by_entry.get(row_id)
                if isinstance(wiki_tutorial_pages_by_entry.get(row_id), dict)
                else {}
            )
            page_ids = [str(page_id) for page_id in (page_ref_row.get("pageIds") or []) if str(page_id)]
            page_title_candidates: list[str] = []
            for page_id in page_ids:
                page_row = wiki_tutorial_pages.get(page_id) if isinstance(wiki_tutorial_pages.get(page_id), dict) else {}
                page_title = brace_text(t((page_row.get("title") or {}).get("id")))
                page_text = t((page_row.get("content") or {}).get("id"))
                if page_title:
                    page_title_candidates.append(page_title)
                add_line(
                    page_id,
                    page_text,
                    hint=page_title,
                    debug={
                        **source_ref(
                            "WikiTutorialPageTable",
                            page_id,
                            pick_fields(page_row, "content", "id", "image", "order", "refWikiEntryIds", "title", "tutorialId", "video", "videoDeviceType"),
                        ),
                        "fields": {
                            "title": text_trace("WikiTutorialPageTable", page_id, "title", page_row.get("title")),
                            "text": text_trace("WikiTutorialPageTable", page_id, "content", page_row.get("content")),
                        },
                    } if page_row else None,
                )
                media_bits = []
                if page_row.get("image"):
                    media_bits.append(f"image={page_row['image']}")
                if page_row.get("video"):
                    media_bits.append(f"video={page_row['video']}")
                if media_bits:
                    summary_rows.append({"text": f"{page_title or page_id}: " + ", ".join(media_bits)})
            title = next((candidate for candidate in page_title_candidates if candidate), row_id)

        if row_desc:
            add_line(
                f"{row_id}_wiki",
                row_desc,
                hint="Wiki",
                debug={
                    **source_ref("WikiEntryDataTable", row_id, pick_fields(row, "desc", "groupId", "id", "order", "prtsId", "refItemId", "refMonsterTemplateId")),
                    "fields": {
                        "text": text_trace("WikiEntryDataTable", row_id, "desc", row.get("desc")),
                    },
                },
            )

        summary_rows.insert(0, {"text": f"Category: {category_name}"})
        if group_name and group_name != category_name:
            summary_rows.insert(1, {"text": f"Group: {group_name}"})
        if prts_id:
            summary_rows.append({"text": f"PRTS: {prts_id}"})
        if ref_item_id:
            summary_rows.append({"text": f"Ref item: {ref_item_id}"})
        if ref_monster_id:
            summary_rows.append({"text": f"Ref enemy: {ref_monster_id}"})

        wiki_fp = text_sequence_fingerprint(lines)
        if wiki_fp:
            wiki_text_fingerprints.add(wiki_fp)

        payload = {
            "key": row_id,
            "kind": "wiki",
            "mission": mission_id,
            "scene": int(row.get("order") or 0),
            "title": title,
            "lines": lines,
            "_debug": {
                "source": source_ref(
                    "WikiEntryDataTable",
                    row_id,
                    pick_fields(row, "desc", "groupId", "id", "order", "prtsId", "refItemId", "refMonsterTemplateId"),
                ),
            },
        }
        if summary_rows:
            payload["summary"] = summary_rows
        if group_id:
            payload["_debug"]["group"] = {
                "categoryId": category_id,
                "categoryName": category_name,
                "groupId": group_id,
                "groupName": group_name,
            }
        with (conv_dir / f"{row_id}.json").open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        entry = {
            "k": row_id,
            "d": "wiki",
            "m": mission_id,
            "s": int(row.get("order") or 0),
            "t": "wiki",
            "a": 0,
            "title": title,
            "c": [],
            "n": len(lines),
            "p": preview(next((line.get("text") or "" for line in lines if line.get("text")), title)),
            "tags": ["wiki", category_id, group_id or category_id],
        }
        search_text = " ".join(
            part
            for part in [
                row_id,
                category_id,
                category_name,
                group_id,
                group_name,
                title,
                row_desc,
                ref_item_id,
                ref_monster_id,
                prts_id,
                " ".join(line.get("text") or "" for line in lines),
            ]
            if part
        )
        if search_text:
            entry["x"] = search_text
        index_entries.append(entry)

    operator_archive_rows = [row for row in character_rows.values() if isinstance(row, dict) and ((row.get("profileRecord") or []) or (row.get("profileVoice") or []))]
    print(f"Writing {len(operator_archive_rows)} operator archive pages...")
    for char_id, row in sorted(
        ((char_id, row) for char_id, row in character_rows.items() if isinstance(row, dict)),
        key=lambda item: (int((item[1] or {}).get("sortOrder") or 0), item[0]),
    ):
        profile_records = [item for item in (row.get("profileRecord") or []) if isinstance(item, dict)]
        profile_voice = [item for item in (row.get("profileVoice") or []) if isinstance(item, dict)]
        if not profile_records and not profile_voice:
            continue

        actor_id = char_id.split("_", 2)[-1] if char_id.startswith("chr_") else char_id
        char_name = (
            brace_text(t((row.get("name") or {}).get("id")))
            or speaker_display_name(actor_id)
            or speaker_display_name(char_id)
            or char_id
        )
        extra_mission_names[char_id] = char_name

        title = char_name
        summary_rows: list[dict] = []
        summary_rows.append({"text": f"Profile sections: {len(profile_records)}"})
        summary_rows.append({"text": f"Voice entries: {len(profile_voice)}"})
        if department := str(row.get("department") or ""):
            summary_rows.append({"text": f"Department: {department}"})
        if cv_name := brace_text(t((((row.get("cvName") or {}).get("ChiCVName") or {}).get("id")))):
            summary_rows.append({"text": f"CV: {cv_name}"})
        if row.get("rarity") is not None:
            summary_rows.append({"text": f"Rarity: {row['rarity']}"})
        if char_type := str(row.get("charTypeId") or ""):
            summary_rows.append({"text": f"Type: {char_type}"})
        if weapon_type := row.get("weaponType"):
            summary_rows.append({"text": f"Weapon type: {weapon_type}"})
        if default_weapon_id := str(row.get("defaultWeaponId") or ""):
            weapon_item_row = item_rows.get(default_weapon_id) if isinstance(item_rows.get(default_weapon_id), dict) else {}
            weapon_name = brace_text(t((weapon_item_row.get("name") or {}).get("id"))) or default_weapon_id
            summary_rows.append({"text": f"Default weapon: {weapon_name}"})

        lines: list[dict] = []
        for record in sorted(profile_records, key=lambda item: (int(item.get("recordIndex") or 0), str(item.get("id") or ""))):
            record_text = t((record.get("recordDesc") or {}).get("id"))
            if not record_text:
                continue
            record_title = brace_text(t((record.get("recordTitle") or {}).get("id"))) or str(record.get("recordID") or record.get("id") or "")
            lines.append({
                "id": str(record.get("id") or record.get("recordID") or f"{char_id}_record"),
                "text": record_text,
                "hint": record_title,
                "_debug": {
                    **source_ref(
                        "CharacterTable.profileRecord",
                        char_id,
                        pick_fields(record, "charId", "id", "recordDesc", "recordID", "recordIndex", "recordTitle", "unlockType", "unlockValue"),
                        nodeId=record.get("recordIndex"),
                    ),
                    "fields": {
                        "title": text_trace("CharacterTable.profileRecord", str(record.get("id") or char_id), "recordTitle", record.get("recordTitle")),
                        "text": text_trace("CharacterTable.profileRecord", str(record.get("id") or char_id), "recordDesc", record.get("recordDesc")),
                    },
                },
            })
        for voice in sorted(profile_voice, key=lambda item: (int(item.get("voiceIndex") or 0), str(item.get("id") or ""))):
            voice_text = t((voice.get("voiceDesc") or {}).get("id"))
            if not voice_text:
                continue
            voice_title = brace_text(t((voice.get("voiceTitle") or {}).get("id"))) or str(voice.get("voId") or voice.get("id") or "")
            lines.append({
                "id": str(voice.get("id") or voice.get("voId") or f"{char_id}_voice"),
                "aid": actor_id,
                "actor": char_name,
                "text": voice_text,
                "hint": voice_title,
                "_debug": {
                    **source_ref(
                        "CharacterTable.profileVoice",
                        char_id,
                        pick_fields(voice, "charId", "id", "unlockType", "unlockValue", "voId", "voiceDesc", "voiceIndex", "voiceTitle"),
                        nodeId=voice.get("voiceIndex"),
                    ),
                    "fields": {
                        "title": text_trace("CharacterTable.profileVoice", str(voice.get("id") or char_id), "voiceTitle", voice.get("voiceTitle")),
                        "text": text_trace("CharacterTable.profileVoice", str(voice.get("id") or char_id), "voiceDesc", voice.get("voiceDesc")),
                    },
                },
            })
        if not lines:
            continue

        out_key = f"wiki_{char_id}"
        payload = {
            "key": out_key,
            "kind": "table_charactertable",
            "mission": char_id,
            "scene": 0,
            "title": title,
            "lines": lines,
            "_debug": {
                "source": source_ref(
                    "CharacterTable",
                    char_id,
                    pick_fields(row, "charId", "cvName", "defaultWeaponId", "department", "name", "profileRecord", "profileVoice", "rarity", "sortOrder"),
                ),
            },
        }
        if summary_rows:
            payload["summary"] = summary_rows
        with (conv_dir / f"{out_key}.json").open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        entry = {
            "k": out_key,
            "d": "table_charactertable",
            "m": char_id,
            "s": 0,
            "t": "table_charactertable",
            "a": 0,
            "title": title,
            "c": [actor_id] if actor_id else [],
            "n": len(lines),
            "p": preview(next((line.get("text") or "" for line in lines if line.get("text")), title)),
            "tags": ["wiki", "character", "archive", "table_charactertable"],
        }
        search_text = " ".join(
            part
            for part in [
                char_id,
                actor_id,
                char_name,
                str(row.get("department") or ""),
                str(row.get("charTypeId") or ""),
                str(row.get("defaultWeaponId") or ""),
                " ".join(line.get("hint") or "" for line in lines),
                " ".join(line.get("text") or "" for line in lines),
            ]
            if part
        )
        if search_text:
            entry["x"] = search_text
        index_entries.append(entry)

    def append_reference_line(
        lines: list[dict],
        seen_texts: set[tuple[str, str, str]],
        line_id: str,
        text: str,
        *,
        hint: str = "",
        actor: str = "",
        aid: str = "",
        debug: dict | None = None,
    ) -> None:
        normalized = (text or "").strip()
        if not normalized:
            return
        key = (hint, actor, normalized)
        if key in seen_texts:
            return
        seen_texts.add(key)
        line = {"id": line_id, "text": normalized}
        if hint:
            line["hint"] = hint
        if actor:
            line["actor"] = actor
        if aid:
            line["aid"] = aid
        if debug:
            line["_debug"] = debug
        lines.append(line)

    def reference_kind_from_tags(tags: list[str] | None = None) -> str:
        for tag in tags or []:
            value = str(tag or "")
            if value.startswith("table_"):
                return value
        return "wiki"

    story_reference_only_tags = {
        "achievement",
        "enemyAbility",
        "errorCode",
        "gameMechanic",
        "growth",
        "skillPatch",
        "snsChat",
        "tip",
    }

    def normalized_reference_tags(tags: list[str] | None, mission_id: str) -> list[str]:
        move_to_other = {"loadingTip", "task", "tip"}
        normalized_mission_id = str(mission_id or "").lower()
        if normalized_mission_id.startswith("wiki_collection_"):
            move_to_other.update({"collection", "worldtext"})
        if normalized_mission_id == "snschattable":
            move_to_other.add("snsChat")
        out: list[str] = []
        for raw_tag in tags or ["wiki"]:
            tag = str(raw_tag or "")
            if not tag:
                continue
            if tag in move_to_other:
                tag = "other"
            if tag not in out:
                out.append(tag)
        return out or ["wiki"]

    def write_reference_page(
        out_key: str,
        mission_id: str,
        scene: int,
        title: str,
        lines: list[dict],
        *,
        kind: str | None = None,
        type_key: str | None = None,
        source_debug: dict | None = None,
        summary_rows: list[dict] | None = None,
        tags: list[str] | None = None,
        search_parts: list[str] | None = None,
        actors: list[str] | None = None,
        preview_text: str | None = None,
        debug_extra: dict | None = None,
    ) -> None:
        if not title and not lines and not summary_rows:
            return
        raw_tags = [str(tag or "") for tag in (tags or ["wiki"]) if str(tag or "")]
        if (
            not include_reference_in_story_index
            and story_reference_only_tags & set(raw_tags)
        ):
            return
        entry_tags = normalized_reference_tags(raw_tags, mission_id)
        ref_kind = str(kind or reference_kind_from_tags(tags))
        ref_type = str(type_key or ref_kind)
        payload = {
            "key": out_key,
            "kind": ref_kind,
            "mission": mission_id,
            "scene": scene,
            "title": title or out_key,
            "lines": lines,
            "_debug": {},
        }
        if source_debug:
            payload["_debug"]["source"] = source_debug
        if summary_rows:
            payload["summary"] = summary_rows
        if debug_extra:
            payload["_debug"].update(debug_extra)
        with (conv_dir / f"{out_key}.json").open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        entry = {
            "k": out_key,
            "d": ref_kind,
            "m": mission_id,
            "s": scene,
            "t": ref_type,
            "a": 0,
            "title": title or out_key,
            "c": list(actors or []),
            "n": len(lines),
            "p": preview(
                preview_text
                or next((line.get("text") or "" for line in lines if line.get("text")), title or out_key)
            ),
            "tags": entry_tags,
        }
        search_text = " ".join(
            part
            for part in [
                *(search_parts or []),
                " ".join(line.get("hint") or "" for line in lines),
                " ".join(line.get("actor") or "" for line in lines),
                " ".join(line.get("text") or "" for line in lines),
                " ".join(row.get("text") or "" for row in (summary_rows or [])),
            ]
            if part
        )
        if search_text:
            entry["x"] = search_text
        index_entries.append(entry)

    def character_page_title(char_id: str) -> str:
        row = character_rows.get(char_id) if isinstance(character_rows.get(char_id), dict) else {}
        actor_id = char_id.split("_", 2)[-1] if char_id.startswith("chr_") else char_id
        return (
            brace_text(t((row.get("name") or {}).get("id")))
            or speaker_display_name(actor_id)
            or speaker_display_name(char_id)
            or char_id
        )

    def collection_slug(value: str) -> str:
        value = re.sub(r"[^0-9A-Za-z]+", "_", str(value or ""))
        return value.strip("_").lower() or "misc"

    def collection_display_name(value: str) -> str:
        raw = str(value or "").strip().replace("_", " ")
        if not raw:
            return "Misc"
        raw = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", raw)
        raw = re.sub(r"\s+", " ", raw).strip()
        if raw.isupper():
            return raw
        words = raw.split(" ")
        return " ".join(word[:1].upper() + word[1:] if word else "" for word in words)

    def collection_hint_from_path(path: str) -> str:
        tokens: list[str] = []
        raw = str(path or "")
        if raw.startswith("$."):
            raw = raw[2:]
        elif raw == "$":
            raw = ""
        for piece in [part for part in raw.split(".") if part]:
            base = re.sub(r"\[\d+\]", "", piece)
            idx_matches = [int(match) + 1 for match in re.findall(r"\[(\d+)\]", piece)]
            label = collection_display_name(base)
            if idx_matches:
                label = f"{label} {idx_matches[-1]}"
            if label:
                tokens.append(label)
        return " / ".join(tokens[-2:])

    def collection_bucket_from_key(row_id: str) -> str:
        value = str(row_id or "")
        if not value:
            return "misc"
        if value.isupper() and "_" in value:
            parts = [part for part in value.split("_") if part]
            return "_".join(parts[:2]) if len(parts) >= 2 else parts[0]
        if "_" in value:
            parts = [part for part in value.split("_") if part]
            if len(parts) >= 2 and parts[0] in {"activity", "battle", "bp", "char", "chr", "dung", "item", "npc", "radio", "skill", "sns", "system", "task", "wiki"}:
                return "_".join(parts[:2])
            return parts[0]
        words = re.findall(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|\d+", value)
        if words:
            return "_".join(words[:2])
        return value[:24]

    def collection_bucket(table_name: str, row_id: str, row: dict | None) -> str:
        if table_name == "CommonDeathTips.json":
            return "common_death_tips"
        if table_name == "DisplayEnemyTypeTable.json":
            return "display_enemy_type"
        if table_name == "TextTable.json":
            return collection_bucket_from_key(row_id)
        if isinstance(row, dict):
            for field in (
                "groupId",
                "categoryId",
                "formulaGroupId",
                "gameCategory",
                "machineId",
                "owner",
                "charId",
                "charTypeId",
                "profession",
                "weaponType",
                "roomType",
                "pageType",
                "tagType",
                "type",
            ):
                value = row.get(field)
                if isinstance(value, str) and value and len(value) <= 48:
                    return value
                if isinstance(value, int | float) and field in {"roomType", "pageType", "tagType"}:
                    return f"{field}_{int(value)}"
        return collection_bucket_from_key(row_id)

    def collection_reading_story_ref(
        table_name: str,
        row_id: str,
        row: dict | None,
    ) -> tuple[str, int, str] | None:
        if table_name not in {"PrtsReading.json", "ReadingPopUpTable.json", "RichContentTable.json"}:
            return None

        candidates: list[str] = []
        if table_name == "PrtsReading.json" and isinstance(row, dict):
            items = row.get("list") or {}
            if isinstance(items, dict):
                sorted_items = sorted(
                    ((node_id, node) for node_id, node in items.items() if isinstance(node, dict)),
                    key=lambda item: (int((item[1] or {}).get("order") or 0), str(item[0])),
                )
                for _node_id, node in sorted_items:
                    content_id = str(node.get("contentId") or "").strip()
                    if content_id:
                        candidates.append(content_id)
        elif table_name == "ReadingPopUpTable.json" and isinstance(row, dict):
            content_id = str(row.get("contentId") or "").strip()
            if content_id:
                candidates.append(content_id)
        elif table_name == "RichContentTable.json" and isinstance(row, dict):
            title_text = rich_content_title_text(str(row_id or ""))
            if title_text:
                candidates.append(title_text)

        candidates.append(str(row_id or ""))

        return (
            collection_story_ref_from_identifiers(*candidates)
            or collection_map_ref_from_identifiers(*candidates)
        )

    collection_story_mission_pattern = re.compile(
        r"(?<![a-z0-9])((?:gm|sm|db|dm|[acefm])\d+(?:[a-z]\d+)*(?:d\d+)?)(?![a-z0-9])",
        re.IGNORECASE,
    )
    collection_map_pattern = re.compile(r"map\d+_lv\d+", re.IGNORECASE)

    def collection_scene_suffix(value: str) -> int:
        match = re.search(r"_(\d+)$", str(value or ""))
        return int(match.group(1)) if match else 0

    def collection_story_ref_from_identifiers(*values: str) -> tuple[str, int, str] | None:
        for raw_value in values:
            value = str(raw_value or "").strip()
            if not value:
                continue
            lowered = value.lower()
            if lowered.startswith("topic_"):
                return (value, 0, "topic")
            if lowered.startswith("sr_"):
                return (value, 0, "f")
            if match := collection_story_mission_pattern.findall(lowered):
                mission_id = match[-1]
                type_key, _act = parse_mission(mission_id)
                if type_key in MISSION_STORY_TYPES:
                    return (mission_id, collection_scene_suffix(value), type_key)
        return None

    def collection_map_ref_from_identifiers(*values: str) -> tuple[str, int, str] | None:
        for raw_value in values:
            value = str(raw_value or "").strip()
            if not value:
                continue
            lowered = value.lower()
            if match := collection_map_pattern.findall(lowered):
                return (match[-1], collection_scene_suffix(value), "map")
        return None

    def collection_story_ref_from_bucket(bucket: str) -> tuple[str, int, str] | None:
        candidates: set[str] = set()
        for match in collection_story_mission_pattern.finditer(str(bucket or "").lower()):
            mission_id = match.group(1)
            type_key, _act = parse_mission(mission_id)
            if type_key in MISSION_STORY_TYPES:
                candidates.add(mission_id)
        if len(candidates) != 1:
            return None

        mission_id = next(iter(candidates))
        type_key, _act = parse_mission(mission_id)
        return (mission_id, 0, type_key)

    def collection_bucket_token(bucket: str) -> str:
        slug = collection_slug(bucket)
        checksum = sum((idx + 1) * ord(ch) for idx, ch in enumerate(str(bucket or ""))) % 104729
        return f"{slug}_{checksum:x}" if checksum else slug

    def collection_scene_value(row: dict | None, fallback: int = 0) -> int:
        if not isinstance(row, dict):
            return fallback
        for field in ("order", "sortId", "sortOrder", "level", "priority", "stage", "step", "index"):
            value = row.get(field)
            if isinstance(value, int | float):
                return int(value)
        return fallback

    def collection_source_label(table_source: str) -> str:
        return {
            "streaming": "StreamingAssets/Table",
            "persistent": "Persistent/Table",
        }.get(table_source, table_source)

    def collection_text_fingerprint(text_nodes: list[dict]) -> tuple[tuple[str, str], ...]:
        rows: list[tuple[str, str]] = []
        for node in text_nodes:
            text = re.sub(r"\s+", " ", str(node.get("text") or "")).strip()
            if not text:
                continue
            rows.append((str(node.get("field") or ""), text))
        return tuple(rows)

    prts_archive_categories = ("collection", "digital", "document", "media", "paper", "report")

    def prts_archive_category_from_identifier(value) -> str:
        raw = re.sub(r"[^0-9A-Za-z]+", "_", str(value or "")).strip("_").lower()
        if not raw:
            return ""
        if raw.startswith("nar_"):
            raw = raw[4:]
        if raw.startswith("multi_media"):
            return "media"
        for category_key in prts_archive_categories:
            if raw == category_key or raw.startswith(f"{category_key}_"):
                return category_key
        return ""

    def prts_archive_category_from_collection_ids(collection_ids) -> str:
        counts: dict[str, int] = {}
        first_seen: dict[str, int] = {}
        for idx, raw_id in enumerate(collection_ids or []):
            category_key = prts_archive_category_from_identifier(raw_id)
            if not category_key:
                continue
            counts[category_key] = counts.get(category_key, 0) + 1
            first_seen.setdefault(category_key, idx)
        if not counts:
            return ""
        return min(
            counts,
            key=lambda category_key: (-counts[category_key], first_seen.get(category_key, 0), category_key),
        )

    def prts_archive_category_from_row(
        table_name: str,
        row_id: str,
        row: dict | None,
    ) -> str:
        if table_name == "PrtsCategory.json":
            if isinstance(row, dict):
                return prts_archive_category_from_identifier(row.get("categoryId"))
            return prts_archive_category_from_identifier(row_id)

        if isinstance(row, dict):
            for field in ("categoryId", "firstLvId", "id", "type"):
                category_key = prts_archive_category_from_identifier(row.get(field))
                if category_key:
                    return category_key
            if table_name in {"PrtsInvestigate.json", "PrtsInvestigateCategory.json"}:
                collection_ids: list[str] = []
                for field in ("collectionIdList",):
                    values = row.get(field) or []
                    if isinstance(values, list):
                        collection_ids.extend(str(value) for value in values if str(value))
                for field in ("categoryDataList", "list"):
                    groups = row.get(field) or []
                    if not isinstance(groups, list):
                        continue
                    for group_row in groups:
                        if not isinstance(group_row, dict):
                            continue
                        values = group_row.get("collectionIdList") or []
                        if isinstance(values, list):
                            collection_ids.extend(str(value) for value in values if str(value))
                category_key = prts_archive_category_from_collection_ids(collection_ids)
                if category_key:
                    return category_key

        return prts_archive_category_from_identifier(row_id)

    def prts_category_display_name(category_key: str) -> str:
        row = prts_categories.get(category_key) if isinstance(prts_categories.get(category_key), dict) else {}
        return (
            brace_text(t((row.get("name") or {}).get("id")))
            or str(category_key or "").replace("_", " ").strip().title()
        )

    prts_note_metadata: dict[str, dict] = {}
    for research_id, research_row in sorted(prts_investigate_categories.items()):
        if not isinstance(research_row, dict):
            continue
        for list_index, list_row in enumerate(research_row.get("list") or [], start=1):
            if not isinstance(list_row, dict):
                continue
            note_title = brace_text(t((list_row.get("name") or {}).get("id")))
            category_key = prts_archive_category_from_collection_ids(list_row.get("collectionIdList") or [])
            collection_ids = [
                str(value)
                for value in (list_row.get("collectionIdList") or [])
                if str(value)
            ]
            for note_id in (list_row.get("noteIdList") or []):
                note_key = str(note_id or "").strip()
                if not note_key:
                    continue
                meta = prts_note_metadata.setdefault(note_key, {})
                if note_title and not meta.get("title"):
                    meta["title"] = note_title
                if category_key and not meta.get("category"):
                    meta["category"] = category_key
                meta.setdefault("researchId", str(research_id))
                meta.setdefault("index", int(list_row.get("index") or list_index))
                if collection_ids and not meta.get("collectionIds"):
                    meta["collectionIds"] = list(collection_ids)

    prts_content_ids = {
        str((row or {}).get("contentId") or "")
        for row in prts_all_items.values()
        if isinstance(row, dict) and str((row or {}).get("contentId") or "")
    }
    prts_investigate_metadata_by_unlock_prts: dict[str, list[dict]] = defaultdict(list)
    for research_id, research_row in sorted(load("PrtsInvestigate.json").items()):
        if not isinstance(research_row, dict):
            continue
        unlock_prts = str(research_row.get("unlockPrts") or "").strip()
        if not unlock_prts:
            continue
        research_name = brace_text(t((research_row.get("name") or {}).get("id")))
        research_desc = t((research_row.get("desc") or {}).get("id"))
        if not research_name and not research_desc:
            continue
        prts_investigate_metadata_by_unlock_prts[unlock_prts].append({
            "researchId": str(research_id),
            "title": research_name,
            "desc": research_desc,
        })

    def collection_tags(
        table_name: str,
        row_id: str,
        bucket: str,
        row: dict | None = None,
        *,
        table_source: str = "streaming",
        variant: bool = False,
    ) -> list[str]:
        stem = table_name.removesuffix(".json")
        tags = [
            "wiki",
            "collection",
            f"table_{collection_slug(stem)}",
            f"source_{collection_slug(table_source)}",
        ]
        lower = stem.lower()
        for needle, tag in (
            ("activity", "activity"),
            ("achievement", "achievement"),
            ("battlepass", "battlePass"),
            ("char", "character"),
            ("dungeon", "dungeon"),
            ("enemy", "enemy"),
            ("factory", "factory"),
            ("item", "item"),
            ("jump", "systemJump"),
            ("mail", "mail"),
            ("money", "money"),
            ("picture", "picture"),
            ("radio", "radio"),
            ("skill", "skill"),
            ("system", "system"),
            ("task", "other"),
            ("tip", "other"),
            ("weapon", "weapon"),
        ):
            if tag == "system" and lower.startswith("systemjump"):
                continue
            if needle in lower and tag not in tags:
                tags.append(tag)
        if variant:
            tags.append("variant")
        bucket_slug = collection_slug(bucket)
        if bucket_slug and bucket_slug != "misc":
            tags.append(f"group_{bucket_slug}")
        if isinstance(row, dict):
            if isinstance(row.get("groupId"), str) and row.get("groupId"):
                tags.append(f"group_{collection_slug(row['groupId'])}")
            if isinstance(row.get("categoryId"), str) and row.get("categoryId"):
                tags.append(f"category_{collection_slug(row['categoryId'])}")
        prts_category_key = prts_archive_category_from_row(table_name, row_id, row)
        if prts_category_key:
            tags.append(f"category_{collection_slug(prts_category_key)}")
        deduped: list[str] = []
        for tag in tags:
            if tag not in deduped:
                deduped.append(tag)
        return deduped

    def collect_reference_text_nodes(
        table_name: str,
        row_id: str,
        raw_value,
        *,
        preferred_source: str = "streaming",
        path: str = "$",
        out: list[dict] | None = None,
    ) -> list[dict]:
        if out is None:
            out = []
        if isinstance(raw_value, dict):
            if "id" in raw_value and "text" in raw_value:
                text = t(raw_value.get("id"), preferred_source=preferred_source)
                if text:
                    field_name = re.sub(r"\[\d+\]", "", path.rsplit(".", 1)[-1] if "." in path else path)
                    out.append({
                        "field": field_name or "text",
                        "hint": collection_hint_from_path(path),
                        "path": path,
                        "raw": raw_value,
                        "text": text,
                    })
            for key, value in raw_value.items():
                child_path = f"{path}.{key}" if path != "$" else f"$.{key}"
                collect_reference_text_nodes(
                    table_name,
                    row_id,
                    value,
                    preferred_source=preferred_source,
                    path=child_path,
                    out=out,
                )
            return out
        if isinstance(raw_value, list):
            for idx, value in enumerate(raw_value):
                child_path = f"{path}[{idx}]"
                collect_reference_text_nodes(
                    table_name,
                    row_id,
                    value,
                    preferred_source=preferred_source,
                    path=child_path,
                    out=out,
                )
        return out

    def collection_row_title(
        table_name: str,
        row_id: str,
        text_nodes: list[dict],
        *,
        preferred_source: str = "streaming",
    ) -> str:
        preferred_fields = {
            "name",
            "title",
            "talentName",
            "gameName",
            "dungeonName",
            "tipsTitle",
            "topicName",
            "recordTitle",
            "voiceTitle",
            "iconDesc",
            "effectTitle",
        }
        for node in text_nodes:
            if node.get("field") in preferred_fields:
                return brace_text(node.get("text") or "") or (node.get("text") or "")
        if table_name == "TextTable.json":
            return row_id
        return row_id

    def collection_summary_rows(
        table_name: str,
        row_id: str,
        row: dict | None,
        bucket: str,
        *,
        table_source: str = "streaming",
        variant: bool = False,
    ) -> list[dict]:
        rows = [
            {"text": f"Table: {collection_display_name(table_name.removesuffix('.json'))}"},
            {"text": f"Row: {row_id}"},
        ]
        if table_source != "streaming":
            rows.append({"text": f"Source: {collection_source_label(table_source)}"})
        if variant:
            rows.append({"text": "Variant: differs from StreamingAssets row"})
        bucket_label = collection_display_name(bucket)
        if bucket_label and bucket_label != "Misc":
            rows.append({"text": f"Group: {bucket_label}"})
        if isinstance(row, dict):
            for field in ("groupId", "categoryId", "type", "gameCategory", "profession", "weaponType", "machineId", "roomType", "unlockMissionId"):
                value = row.get(field)
                if value in (None, "", [], {}):
                    continue
                if isinstance(value, list):
                    preview_value = ", ".join(str(item) for item in value[:4])
                    if len(value) > 4:
                        preview_value += ", ..."
                else:
                    preview_value = str(value)
                rows.append({"text": f"{collection_display_name(field)}: {preview_value}"})
                if len(rows) >= 6:
                    break
        return rows

    def collect_exported_texttable_row_ids() -> set[str]:
        referenced = set(referenced_texttable_row_ids)

        def visit(value) -> None:
            if isinstance(value, dict):
                if value.get("table") == "TextTable" and value.get("rowId"):
                    remember_texttable_row_usage(value.get("rowId"))
                    referenced.add(str(value.get("rowId")))
                for nested in value.values():
                    visit(nested)
                return
            if isinstance(value, list):
                for nested in value:
                    visit(nested)

        for conv_path in conv_dir.glob("*.json"):
            if conv_path.stem.startswith("wiki_collection_texttable_"):
                continue
            try:
                payload = json.loads(conv_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            visit(payload)
        return referenced

    def write_texttable_collection_pages(excluded_row_ids: set[str] | None = None) -> None:
        excluded = {str(row_id) for row_id in (excluded_row_ids or set()) if str(row_id or "").strip()}
        chunks_by_bucket: dict[str, list[tuple[str, dict]]] = defaultdict(list)
        for row_id, row in sorted(text_table.items()):
            if not isinstance(row, dict):
                continue
            if row_id in excluded:
                continue
            text = t(row.get("id"))
            if not text:
                continue
            chunks_by_bucket[collection_bucket("TextTable.json", row_id, row)].append((row_id, row))

        total_pages = 0
        total_rows = 0
        chunk_size = 200
        for bucket, entries in sorted(chunks_by_bucket.items()):
            total_rows += len(entries)
            bucket_token = collection_bucket_token(bucket)
            story_ref = collection_story_ref_from_bucket(bucket)
            if story_ref:
                mission_id, _forced_scene_value, forced_type_key = story_ref
                extra_mission_names.setdefault(mission_id, collection_display_name(mission_id))
            else:
                mission_id = f"wiki_collection_texttable_{bucket_token}"
                forced_type_key = None
            for chunk_index, start in enumerate(range(0, len(entries), chunk_size), start=1):
                chunk = entries[start:start + chunk_size]
                lines: list[dict] = []
                for row_id, row in chunk:
                    text = t(row.get("id"))
                    if not text:
                        continue
                    lines.append({
                        "id": row_id,
                        "text": text,
                        "hint": row_id,
                        "_debug": {
                            **source_ref("TextTable", row_id, pick_fields(row, "id")),
                            "fields": {
                                "text": text_trace("TextTable", row_id, "id", row.get("id")),
                            },
                        },
                    })
                if not lines:
                    continue
                total_pages += 1
                title = f"TextTable / {collection_display_name(bucket)}"
                if len(entries) > chunk_size:
                    title += f" ({chunk_index})"
                out_key = f"wiki_collection_texttable_{bucket_token}_{chunk_index}"
                summary_rows = [
                    {"text": "Table: TextTable"},
                    {"text": f"Group: {collection_display_name(bucket)}"},
                    {"text": f"Entries: {len(lines)}"},
                ]
                write_reference_page(
                    out_key,
                    mission_id,
                    chunk_index,
                    title,
                    lines,
                    type_key=forced_type_key,
                    source_debug=source_ref("TextTable", bucket_token, {"entries": len(lines), "bucket": bucket}),
                    summary_rows=summary_rows,
                    tags=["wiki", "collection", "table_texttable", "source_streaming", f"group_{bucket_token}", "text"],
                    search_parts=[bucket, title, " ".join(line["id"] for line in lines[:50])],
                )
        skipped_rows = len(excluded & {str(row_id) for row_id in text_table})
        print(
            f"Writing {total_pages} text-table collection pages for {total_rows} entries "
            f"({skipped_rows} referenced rows skipped)..."
        )

    print(f"Writing {len(skill_patches)} skill patch reference pages...")
    for skill_id, row in sorted(skill_patches.items()):
        if not isinstance(row, dict):
            continue
        bundles = [bundle for bundle in (row.get("SkillPatchDataBundle") or []) if isinstance(bundle, dict)]
        if not bundles:
            continue
        title = next(
            (
                brace_text(t((bundle.get("skillName") or {}).get("id")))
                for bundle in bundles
                if brace_text(t((bundle.get("skillName") or {}).get("id")))
            ),
            skill_id,
        )
        summary_rows: list[dict] = []
        level_count = len([bundle for bundle in bundles if int(bundle.get("level") or 0) > 0])
        if level_count:
            summary_rows.append({"text": f"Levels: {level_count}"})
        icon_id = next((str(bundle.get("iconId") or "") for bundle in bundles if str(bundle.get("iconId") or "")), "")
        if icon_id:
            summary_rows.append({"text": f"Icon: {icon_id}"})
        tag_id = next((str(bundle.get("tagId") or "") for bundle in bundles if str(bundle.get("tagId") or "")), "")
        if tag_id:
            summary_rows.append({"text": f"Tag: {tag_id}"})
        lines: list[dict] = []
        seen_texts: set[tuple[str, str, str]] = set()
        for bundle in sorted(bundles, key=lambda item: (int(item.get("level") or 0), str(item.get("skillId") or skill_id))):
            level = int(bundle.get("level") or 0)
            level_hint = f"Level {level}" if level else ""
            description = t((bundle.get("description") or {}).get("id"))
            append_reference_line(
                lines,
                seen_texts,
                f"{skill_id}_desc_{level}",
                description,
                hint=level_hint,
                debug={
                    **source_ref(
                        "SkillPatchTable.SkillPatchDataBundle",
                        skill_id,
                        pick_fields(bundle, "coolDown", "description", "iconId", "level", "skillId", "skillName", "subDescList", "subDescNameList", "tagId"),
                        nodeId=level,
                    ),
                    "fields": {
                        "title": text_trace("SkillPatchTable.SkillPatchDataBundle", skill_id, "skillName", bundle.get("skillName")),
                        "text": text_trace("SkillPatchTable.SkillPatchDataBundle", skill_id, "description", bundle.get("description")),
                    },
                } if description else None,
            )
            raw_sub_names = bundle.get("subDescNameList") or []
            raw_sub_values = bundle.get("subDescList") or []
            for idx, raw_name in enumerate(raw_sub_names, start=1):
                label = t((raw_name or {}).get("id"))
                if not label:
                    continue
                value = str(raw_sub_values[idx - 1] or "").strip() if idx - 1 < len(raw_sub_values) else ""
                append_reference_line(
                    lines,
                    seen_texts,
                    f"{skill_id}_sub_{level}_{idx}",
                    label,
                    hint=" ".join(part for part in [level_hint, value] if part),
                    debug={
                        **source_ref(
                            "SkillPatchTable.SkillPatchDataBundle",
                            skill_id,
                            pick_fields(bundle, "level", "skillId", "subDescList", "subDescNameList"),
                            nodeId=level,
                            nodeIndex=idx - 1,
                        ),
                        "fields": {
                            "text": text_trace(
                                "SkillPatchTable.SkillPatchDataBundle",
                                skill_id,
                                f"subDescNameList[{idx - 1}]",
                                raw_name,
                            ),
                        },
                    },
                )
        if title == skill_id and not lines:
            continue
        write_reference_page(
            f"wiki_skill_{skill_id}",
            "SkillPatchTable",
            0,
            title,
            lines,
            source_debug=source_ref("SkillPatchTable", skill_id, pick_fields(row, "SkillPatchDataBundle")),
            summary_rows=summary_rows,
            tags=["wiki", "skillPatch", "table_skillpatchtable"],
            search_parts=[skill_id, title, tag_id],
        )

    print(f"Writing {len(char_growth)} character growth reference pages...")
    for char_id, row in sorted(char_growth.items()):
        if not isinstance(row, dict):
            continue
        title = brace_text(t((row.get("name") or {}).get("id"))) or character_page_title(char_id)
        extra_mission_names.setdefault(char_id, title)
        summary_rows: list[dict] = []
        if row.get("rarity") is not None:
            summary_rows.append({"text": f"Rarity: {row['rarity']}"})
        if profession := str(row.get("profession") or ""):
            summary_rows.append({"text": f"Profession: {profession}"})
        if weapon_type := str(row.get("weaponType") or ""):
            summary_rows.append({"text": f"Weapon type: {weapon_type}"})
        if default_weapon_id := str(row.get("defaultWeaponId") or ""):
            summary_rows.append({"text": f"Default weapon: {default_weapon_id}"})
        lines: list[dict] = []
        seen_texts: set[tuple[str, str, str]] = set()
        for node_id, node in sorted(
            ((node_id, node) for node_id, node in (row.get("charBreakCostMap") or {}).items() if isinstance(node, dict)),
            key=lambda item: (int((item[1] or {}).get("breakStage") or 0), item[0]),
        ):
            node_name = brace_text(t((node.get("name") or {}).get("id")))
            node_desc = t((node.get("description") or {}).get("id"))
            append_reference_line(
                lines,
                seen_texts,
                f"{char_id}_{node_id}",
                node_desc or node_name,
                hint=node_name if node_desc and node_name else "",
                debug={
                    **source_ref(
                        "CharGrowthTable.charBreakCostMap",
                        char_id,
                        pick_fields(node, "breakStage", "charId", "description", "equipTierLimit", "name", "nodeId", "nodeType", "requiredItem"),
                        nodeId=node_id,
                    ),
                    "fields": {
                        "title": text_trace("CharGrowthTable.charBreakCostMap", char_id, "name", node.get("name")),
                        "text": text_trace("CharGrowthTable.charBreakCostMap", char_id, "description", node.get("description")),
                    },
                } if (node_desc or node_name) else None,
            )
        for node_id, node in sorted(
            ((node_id, node) for node_id, node in (row.get("skillGroupMap") or {}).items() if isinstance(node, dict)),
            key=lambda item: item[0],
        ):
            node_name = brace_text(t((node.get("name") or {}).get("id")))
            node_desc = t((node.get("desc") or {}).get("id"))
            append_reference_line(
                lines,
                seen_texts,
                f"{char_id}_{node_id}",
                node_desc or node_name,
                hint=node_name if node_desc and node_name else "",
                debug={
                    **source_ref(
                        "CharGrowthTable.skillGroupMap",
                        char_id,
                        pick_fields(node, "desc", "name", "skillId", "skillType", "unlockLevel"),
                        nodeId=node_id,
                    ),
                    "fields": {
                        "title": text_trace("CharGrowthTable.skillGroupMap", char_id, "name", node.get("name")),
                        "text": text_trace("CharGrowthTable.skillGroupMap", char_id, "desc", node.get("desc")),
                    },
                } if (node_desc or node_name) else None,
            )
        for node_id, node in sorted(
            ((node_id, node) for node_id, node in (row.get("talentNodeMap") or {}).items() if isinstance(node, dict)),
            key=lambda item: item[0],
        ):
            attr_node = node.get("attributeNodeInfo") if isinstance(node.get("attributeNodeInfo"), dict) else {}
            node_name = brace_text(t((attr_node.get("title") or {}).get("id")))
            node_desc = t((attr_node.get("desc") or {}).get("id"))
            append_reference_line(
                lines,
                seen_texts,
                f"{char_id}_{node_id}",
                node_desc or node_name,
                hint=node_name if node_desc and node_name else "",
                debug={
                    **source_ref(
                        "CharGrowthTable.talentNodeMap",
                        char_id,
                        pick_fields(node, "attributeNodeInfo", "nodeId", "nodeType", "preNodeId", "requiredItem", "unlockLevel"),
                        nodeId=node_id,
                    ),
                    "fields": {
                        "title": text_trace("CharGrowthTable.talentNodeMap", char_id, "attributeNodeInfo.title", attr_node.get("title")),
                        "text": text_trace("CharGrowthTable.talentNodeMap", char_id, "attributeNodeInfo.desc", attr_node.get("desc")),
                    },
                } if (node_desc or node_name) else None,
            )
        if title == char_id and not lines:
            continue
        write_reference_page(
            f"wiki_growth_{char_id}",
            char_id,
            0,
            title,
            lines,
            source_debug=source_ref(
                "CharGrowthTable",
                char_id,
                pick_fields(row, "charId", "charBreakCostMap", "defaultWeaponId", "name", "profession", "rarity", "skillGroupMap", "talentNodeMap", "weaponType"),
            ),
            summary_rows=summary_rows,
            tags=["wiki", "character", "growth", "table_chargrowthtable"],
            search_parts=[char_id, title, str(row.get("profession") or ""), str(row.get("weaponType") or "")],
            actors=[char_id.split("_", 2)[-1]] if char_id.startswith("chr_") else [],
        )

    print(f"Writing {len(game_mechanics)} game mechanic reference pages...")
    for mechanic_id, row in sorted(game_mechanics.items()):
        if not isinstance(row, dict):
            continue
        game_category = str(row.get("gameCategory") or "misc")
        mission_id = f"wiki_game_mechanic_{game_category}"
        title = brace_text(t((row.get("gameName") or {}).get("id"))) or mechanic_id
        desc = t((row.get("desc") or {}).get("id"))
        lines: list[dict] = []
        seen_texts: set[tuple[str, str, str]] = set()
        append_reference_line(
            lines,
            seen_texts,
            mechanic_id,
            desc,
            debug={
                **source_ref(
                    "GameMechanicTable",
                    mechanic_id,
                    pick_fields(row, "conditionIds", "costStamina", "desc", "difficulty", "gameCategory", "gameMechanicsId", "gameName", "rewardId"),
                ),
                "fields": {
                    "title": text_trace("GameMechanicTable", mechanic_id, "gameName", row.get("gameName")),
                    "text": text_trace("GameMechanicTable", mechanic_id, "desc", row.get("desc")),
                },
            } if desc else None,
        )
        if title == mechanic_id and not lines:
            continue
        summary_rows: list[dict] = []
        if row.get("difficulty") is not None:
            summary_rows.append({"text": f"Difficulty: {row['difficulty']}"})
        if row.get("costStamina") is not None:
            summary_rows.append({"text": f"Stamina: {row['costStamina']}"})
        write_reference_page(
            f"wiki_mechanic_{mechanic_id}",
            mission_id,
            int(row.get("difficulty") or 0),
            title,
            lines,
            source_debug=source_ref(
                "GameMechanicTable",
                mechanic_id,
                pick_fields(row, "conditionIds", "costStamina", "desc", "difficulty", "gameCategory", "gameMechanicsId", "gameName", "rewardId"),
            ),
            summary_rows=summary_rows,
            tags=["wiki", "gameMechanic", game_category, "table_gamemechanictable"],
            search_parts=[mechanic_id, game_category, title, desc],
        )

    print(f"Writing {len(loading_tips)} loading-tip reference pages...")
    for tip_id, row in sorted(loading_tips.items()):
        if not isinstance(row, dict):
            continue
        title = brace_text(t((row.get("tipsTitle") or {}).get("id"))) or tip_id
        text = t((row.get("text") or {}).get("id"))
        lines: list[dict] = []
        seen_texts: set[tuple[str, str, str]] = set()
        append_reference_line(
            lines,
            seen_texts,
            tip_id,
            text,
            debug={
                **source_ref(
                    "LoadingTipsTable",
                    tip_id,
                    pick_fields(row, "key", "mapTag", "text", "tipsTitle", "typeTag", "unlockMissionId"),
                ),
                "fields": {
                    "title": text_trace("LoadingTipsTable", tip_id, "tipsTitle", row.get("tipsTitle")),
                    "text": text_trace("LoadingTipsTable", tip_id, "text", row.get("text")),
                },
            } if text else None,
        )
        if title == tip_id and not lines:
            continue
        summary_rows: list[dict] = []
        if unlock_mission := str(row.get("unlockMissionId") or ""):
            summary_rows.append({"text": f"Unlock mission: {unlock_mission}"})
        if row.get("typeTag") is not None:
            summary_rows.append({"text": f"Type: {row['typeTag']}"})
        write_reference_page(
            f"wiki_tip_{tip_id}",
            "LoadingTipsTable",
            int(row.get("typeTag") or 0),
            title,
            lines,
            kind="table_loadingtipstable",
            type_key="table_loadingtipstable",
            source_debug=source_ref(
                "LoadingTipsTable",
                tip_id,
                pick_fields(row, "key", "mapTag", "text", "tipsTitle", "typeTag", "unlockMissionId"),
            ),
            summary_rows=summary_rows,
            tags=["wiki", "table_loadingtipstable"],
            search_parts=[tip_id, title, text, str(row.get("unlockMissionId") or "")],
        )

    print(f"Writing {len(error_codes)} error-code reference pages...")
    for code, row in sorted(error_codes.items(), key=lambda item: int(item[0]) if re.fullmatch(r"-?\d+", str(item[0])) else 0):
        if not isinstance(row, dict):
            continue
        text = t((row.get("text") or {}).get("id"))
        if not text:
            continue
        write_reference_page(
            f"wiki_error_{code}",
            "ErrorCodeTable",
            int(code) if re.fullmatch(r"-?\d+", str(code)) else 0,
            str(code),
            [{
                "id": str(code),
                "text": text,
                "_debug": {
                    **source_ref("ErrorCodeTable", str(code), pick_fields(row, "text")),
                    "fields": {
                        "text": text_trace("ErrorCodeTable", str(code), "text", row.get("text")),
                    },
                },
            }],
            source_debug=source_ref("ErrorCodeTable", str(code), pick_fields(row, "text")),
            tags=["wiki", "errorCode", "table_errorcodetable"],
            search_parts=[str(code), text],
        )

    achievement_group_names: dict[str, str] = {}
    achievement_group_category_ids: dict[str, str] = {}
    achievement_category_names: dict[str, str] = {}
    for category_id, category_row in sorted(
        achievement_types.items(),
        key=lambda item: (int((item[1] or {}).get("categoryPriority") or 0), item[0]),
    ):
        if not isinstance(category_row, dict):
            continue
        category_name = brace_text(t((category_row.get("categoryName") or {}).get("id"))) or category_id
        achievement_category_names[category_id] = category_name
        for group_row in (category_row.get("achievementGroupData") or []):
            if not isinstance(group_row, dict):
                continue
            group_id = str(group_row.get("groupId") or "")
            if not group_id:
                continue
            group_name = brace_text(t((group_row.get("groupName") or {}).get("id"))) or category_name
            achievement_group_names[group_id] = group_name
            achievement_group_category_ids[group_id] = category_id

    def achievement_group_meta(group_id: str) -> tuple[str, str, str]:
        category_id = achievement_group_category_ids.get(group_id, "")
        category_name = achievement_category_names.get(category_id, category_id)
        group_name = achievement_group_names.get(group_id) or category_name or group_id
        return group_name, category_id, category_name

    print(f"Writing {len(achievements)} achievement reference pages...")
    for achieve_id, row in sorted(
        achievements.items(),
        key=lambda item: (str((item[1] or {}).get("groupId") or ""), int((item[1] or {}).get("order") or 0), item[0]),
    ):
        if not isinstance(row, dict):
            continue
        group_id = str(row.get("groupId") or "misc")
        group_name, category_id, category_name = achievement_group_meta(group_id)
        mission_id = f"wiki_achievement_{group_id}"
        extra_mission_names.setdefault(mission_id, group_name)
        title = brace_text(t((row.get("name") or {}).get("id"))) or achieve_id
        lines: list[dict] = []
        seen_texts: set[tuple[str, str, str]] = set()
        desc = t((row.get("desc") or {}).get("id"))
        append_reference_line(
            lines,
            seen_texts,
            f"{achieve_id}_desc",
            desc,
            hint="Description" if desc else "",
            debug={
                **source_ref("AchievementTable", achieve_id, pick_fields(row, "achieveId", "desc", "groupId", "levelInfos", "name", "order")),
                "fields": {
                    "title": text_trace("AchievementTable", achieve_id, "name", row.get("name")),
                    "text": text_trace("AchievementTable", achieve_id, "desc", row.get("desc")),
                },
            } if desc else None,
        )
        level_infos = row.get("levelInfos") or {}
        for level_key, level_row in sorted(
            ((level_key, level_row) for level_key, level_row in level_infos.items() if isinstance(level_row, dict)),
            key=lambda item: int(item[0]) if re.fullmatch(r"\d+", str(item[0])) else 0,
        ):
            complete_desc = t((level_row.get("completeDesc") or {}).get("id"))
            append_reference_line(
                lines,
                seen_texts,
                f"{achieve_id}_complete_{level_key}",
                complete_desc,
                hint=f"Level {level_key} completion" if complete_desc else "",
                debug={
                    **source_ref(
                        "AchievementTable.levelInfos",
                        achieve_id,
                        pick_fields(level_row, "achieveLevel", "completeDesc", "conditions"),
                        nodeId=level_key,
                    ),
                    "fields": {
                        "text": text_trace("AchievementTable.levelInfos", achieve_id, "completeDesc", level_row.get("completeDesc")),
                    },
                } if complete_desc else None,
            )
            for idx, condition in enumerate((level_row.get("conditions") or []), start=1):
                if not isinstance(condition, dict):
                    continue
                condition_desc = t((condition.get("desc") or {}).get("id"))
                append_reference_line(
                    lines,
                    seen_texts,
                    f"{achieve_id}_condition_{level_key}_{idx}",
                    condition_desc,
                    hint=f"Level {level_key} condition {idx}" if condition_desc else "",
                    debug={
                        **source_ref(
                            "AchievementTable.levelInfos.conditions",
                            achieve_id,
                            pick_fields(condition, "conditionId", "desc", "progressToCompare"),
                            nodeId=f"{level_key}:{idx}",
                        ),
                        "fields": {
                            "text": text_trace("AchievementTable.levelInfos.conditions", achieve_id, "desc", condition.get("desc")),
                        },
                    } if condition_desc else None,
                )
        if title == achieve_id and not lines:
            continue
        write_reference_page(
            f"wiki_achievement_{achieve_id}",
            mission_id,
            int(row.get("order") or 0),
            title,
            lines,
            source_debug=source_ref(
                "AchievementTable",
                achieve_id,
                pick_fields(row, "achieveId", "desc", "groupId", "levelInfos", "name", "order"),
            ),
            debug_extra={
                "achievementGroup": {
                    "groupId": group_id,
                    "groupName": group_name,
                    "categoryId": category_id,
                    "categoryName": category_name,
                }
            },
            summary_rows=[{"text": f"Levels: {len(level_infos)}"}] if level_infos else None,
            tags=["wiki", "achievement", group_id, "table_achievementtable"],
            search_parts=[achieve_id, group_id, group_name, category_id, category_name, title, desc],
        )

    print(f"Writing {len(sns_chats)} SNS chat reference pages...")
    for chat_id, row in sorted(sns_chats.items()):
        if not isinstance(row, dict):
            continue
        title = brace_text(t((row.get("name") or {}).get("id"))) or chat_id
        desc = t((row.get("desc") or {}).get("id"))
        tag_label = brace_text(t((row.get("tagLabel") or {}).get("id")))
        lines: list[dict] = []
        seen_texts: set[tuple[str, str, str]] = set()
        append_reference_line(
            lines,
            seen_texts,
            f"{chat_id}_desc",
            desc,
            debug={
                **source_ref(
                    "SNSChatTable",
                    chat_id,
                    pick_fields(row, "chatId", "chatType", "desc", "memberRawNum", "name", "owner", "tagLabel", "tagType"),
                ),
                "fields": {
                    "title": text_trace("SNSChatTable", chat_id, "name", row.get("name")),
                    "text": text_trace("SNSChatTable", chat_id, "desc", row.get("desc")),
                    "tag": text_trace("SNSChatTable", chat_id, "tagLabel", row.get("tagLabel")),
                },
            } if desc else None,
        )
        append_reference_line(
            lines,
            seen_texts,
            f"{chat_id}_tag",
            tag_label,
            hint="Tag" if tag_label else "",
            debug={
                **source_ref(
                    "SNSChatTable",
                    chat_id,
                    pick_fields(row, "chatId", "name", "tagLabel", "tagType"),
                ),
                "fields": {
                    "text": text_trace("SNSChatTable", chat_id, "tagLabel", row.get("tagLabel")),
                },
            } if tag_label else None,
        )
        if title == chat_id and not lines:
            continue
        summary_rows: list[dict] = []
        if row.get("chatType") is not None:
            summary_rows.append({"text": f"Chat type: {row['chatType']}"})
        if owner := str(row.get("owner") or ""):
            summary_rows.append({"text": f"Owner: {owner}"})
        if row.get("memberRawNum") is not None:
            summary_rows.append({"text": f"Members: {row['memberRawNum']}"})
        write_reference_page(
            f"wiki_chat_{chat_id}",
            "SNSChatTable",
            int(row.get("chatType") or 0),
            title,
            lines,
            type_key="other",
            source_debug=source_ref(
                "SNSChatTable",
                chat_id,
                pick_fields(row, "chatId", "chatType", "desc", "memberRawNum", "name", "owner", "tagLabel", "tagType"),
            ),
            summary_rows=summary_rows,
            tags=["wiki", "snsChat", "table_snschattable"],
            search_parts=[chat_id, title, desc, tag_label, str(row.get("owner") or "")],
        )

    print(f"Writing {len(enemy_ability_desc)} enemy ability reference pages...")
    for ability_id, row in sorted(enemy_ability_desc.items()):
        if not isinstance(row, dict):
            continue
        title = brace_text(t((row.get("name") or {}).get("id"))) or ability_id
        desc = t((row.get("description") or {}).get("id"))
        lines: list[dict] = []
        seen_texts: set[tuple[str, str, str]] = set()
        append_reference_line(
            lines,
            seen_texts,
            ability_id,
            desc,
            debug={
                **source_ref("EnemyAbilityDescTable", ability_id, pick_fields(row, "abilityId", "description", "name")),
                "fields": {
                    "title": text_trace("EnemyAbilityDescTable", ability_id, "name", row.get("name")),
                    "text": text_trace("EnemyAbilityDescTable", ability_id, "description", row.get("description")),
                },
            } if desc else None,
        )
        if title == ability_id and not lines:
            continue
        write_reference_page(
            f"wiki_enemyability_{ability_id}",
            "EnemyAbilityDescTable",
            0,
            title,
            lines,
            source_debug=source_ref("EnemyAbilityDescTable", ability_id, pick_fields(row, "abilityId", "description", "name")),
            tags=["wiki", "enemyAbility", "table_enemyabilitydesctable"],
            search_parts=[ability_id, title, desc],
        )

    training_death_tips = load_optional_table_json(
        STREAMING_TABLE_DIR,
        "TrainingDeathTips.json",
        "StreamingAssets/Table/TrainingDeathTips.json",
    )
    training_type_info = load_optional_table_json(
        STREAMING_TABLE_DIR,
        "TrainingTypeInfoTable.json",
        "StreamingAssets/Table/TrainingTypeInfoTable.json",
    )
    if isinstance(training_death_tips, dict) or isinstance(training_type_info, dict):
        training_death_tips = training_death_tips if isinstance(training_death_tips, dict) else {}
        training_type_info = training_type_info if isinstance(training_type_info, dict) else {}
        training_keys = sorted(
            set(training_death_tips) | set(training_type_info),
            key=lambda key: (
                int((training_type_info.get(key) or {}).get("priority") or 9999)
                if isinstance(training_type_info.get(key), dict)
                else 9999,
                str(key),
            ),
        )
        for row_index, row_id in enumerate(training_keys, start=1):
            tip_row = training_death_tips.get(row_id)
            info_row = training_type_info.get(row_id)
            tip_row = tip_row if isinstance(tip_row, dict) else {}
            info_row = info_row if isinstance(info_row, dict) else {}

            title = (
                brace_text(t((info_row.get("progressBarLabel") or {}).get("id")))
                or row_id
            )
            lines: list[dict] = []
            seen_texts: set[tuple[str, str, str]] = set()

            tip_contents = tip_row.get("tipContents") or []
            if isinstance(tip_contents, list):
                for idx, tip_ref in enumerate(tip_contents, start=1):
                    text = t((tip_ref or {}).get("id"))
                    append_reference_line(
                        lines,
                        seen_texts,
                        f"{row_id}_tip_{idx}",
                        text,
                        hint=f"Tip {idx}",
                        debug={
                            **source_ref(
                                "TrainingDeathTips",
                                row_id,
                                {"path": f"$.tipContents[{idx-1}]"},
                                nodeId=idx,
                                tableSource="StreamingAssets/Table",
                            ),
                            "fields": {
                                "text": text_trace(
                                    "TrainingDeathTips",
                                    row_id,
                                    f"$.tipContents[{idx-1}]",
                                    tip_ref,
                                ),
                            },
                        } if text else None,
                    )

            label_text = brace_text(t((info_row.get("progressBarLabel") or {}).get("id")))
            if not lines and label_text:
                append_reference_line(
                    lines,
                    seen_texts,
                    f"{row_id}_label",
                    label_text,
                    hint="Type Label",
                    debug={
                        **source_ref(
                            "TrainingTypeInfoTable",
                            row_id,
                            {"path": "$.progressBarLabel"},
                            tableSource="StreamingAssets/Table",
                        ),
                        "fields": {
                            "text": text_trace(
                                "TrainingTypeInfoTable",
                                row_id,
                                "$.progressBarLabel",
                                info_row.get("progressBarLabel"),
                            ),
                        },
                    },
                )

            if not title and not lines:
                continue

            summary_rows = [
                {"text": "Table: TrainingDeathTips / TrainingTypeInfoTable"},
                {"text": f"Row: {row_id}"},
            ]
            if label_text and label_text != title:
                summary_rows.append({"text": f"Label: {label_text}"})
            if info_row.get("priority") is not None:
                summary_rows.append({"text": f"Priority: {info_row['priority']}"})
            if info_row.get("trainingThresholdFactor") is not None:
                summary_rows.append({"text": f"Threshold Factor: {info_row['trainingThresholdFactor']}"})

            source_debug = source_ref(
                "TrainingDeathTips",
                row_id,
                {"table": "TrainingDeathTips / TrainingTypeInfoTable"},
                tableSource="StreamingAssets/Table",
            )
            debug_extra = {
                "mergedSources": [
                    source_ref(
                        "TrainingDeathTips",
                        row_id,
                        pick_fields(tip_row, "tipContents"),
                        tableSource="StreamingAssets/Table",
                    ),
                    source_ref(
                        "TrainingTypeInfoTable",
                        row_id,
                        pick_fields(info_row, "priority", "progressBarLabel", "trainingThresholdFactor", "trainingType"),
                        tableSource="StreamingAssets/Table",
                    ),
                ],
            }
            write_reference_page(
                f"wiki_trainingtip_{collection_slug(row_id)}",
                "TrainingDeathTips",
                int(info_row.get("priority") or row_index),
                title,
                lines,
                kind="table_trainingdeathtips",
                type_key="other",
                source_debug=source_debug,
                summary_rows=summary_rows,
                tags=[
                    "wiki",
                    "table_trainingdeathtips",
                    "table_trainingtypeinfotable",
                    "group_training_death_tips",
                ],
                search_parts=[
                    "TrainingDeathTips",
                    "TrainingTypeInfoTable",
                    row_id,
                    title,
                    label_text,
                ],
                debug_extra=debug_extra,
            )

    collection_omit_tables = {
        "AchievementTable.json",
        "AchievementTypeTable.json",
        "AIBarkText.json",
        "BlocDataTable.json",
        "CheckInRewardTable.json",
        "DialogOptionTable.json",
        "DialogSummaryTable.json",
        "DialogTextTable.json",
        "GamepadImplicitSettingItemTable.json",
        "GamepadSettingItemTable.json",
        "GamepadSettingOptionTable.json",
        "GameSystemConfigTable.json",
        "GiftpackCashShopIdTable.json",
        I18N_HOTFIX_TABLE,
        "MissionExtraInfoTable.json",
        "MoneyConfigTable.json",
        "MoneyConsumeTable.json",
        "MoneyExchangeTable.json",
        "MoneyGainTable.json",
        "MoneyRecordTable.json",
        "PrtsCategory.json",
        "PrtsDocument.json",
        "PrtsInvestigate.json",
        "PrtsInvestigateCategory.json",
        "PrtsMultimedia.json",
        "PrtsRecord.json",
        "QualitySubSettingOptionTable.json",
        "QualitySubSettingTable.json",
        "ReportTable.json",
        "SceneCollectableItemTable.json",
        "ShareChannelTable.json",
        "SNSDialogTopicTable.json",
        "SettingTabTable.json",
        "TowerDefenseGroupTable.json",
        "TrainingDeathTips.json",
        "TrainingTypeInfoTable.json",
        "WeaponBasicTable.json",
    }
    collection_omit_prefixes = (
        "Attribute",
        "CompositeAttributeShow",
        "SocialBuilding",
    )
    collection_skip_tables = {
        "DialogTextTable.json",
        "SNSDialogTable.json",
        "SNSDialogOptionTable.json",
        "RadioTable.json",
        "RemoteCommonTable.json",
        "EnvTalkTable.json",
        "ResponsiveDialog.json",
        "MailSenderTable.json",
        "MailTemplateTable.json",
        "PrtsAllItem.json",
        "PrtsFirstLv.json",
        "PrtsPage.json",
        "PrtsNote.json",
        "WikiCategoryTable.json",
        "WikiGroupTable.json",
        "WikiEntryDataTable.json",
        "WikiTutorialPageTable.json",
        "WikiTutorialPageByEntryTable.json",
        "WikiCraftJumpTable.json",
        "WikiDefaultCraftTable.json",
        "MissionAreaTable.json",
        "NpcProxyTable.json",
        "NpcProxyExDataTable.json",
        "AtmosphericNpcClusterDataTable.json",
        "SkillPatchTable.json",
        "GameMechanicTable.json",
        "DungeonCharTutorialStepTable.json",
        "LoadingTipsTable.json",
        "ErrorCodeTable.json",
        "SNSChatTable.json",
        "EnemyAbilityDescTable.json",
        "TextTable.json",
    }
    collection_preloaded_tables: dict[str, dict] = {
        "AchievementTable.json": achievements,
        "AIBarkText.json": ai_bark_text,
        "AudioDialog.json": audio_dialog,
        "CharGrowthTable.json": char_growth,
        "CharacterTable.json": character_rows,
        "DialogOptionTable.json": dlg_opts,
        "DungeonTable.json": dungeons,
        "EnemyDisplayInfoTable.json": enemy_display_info,
        "EnemyTemplateDisplayInfoTable.json": enemy_template_display,
        "ItemTable.json": item_rows,
        "MissionExtraInfoTable.json": mission_extra_info,
        "NpcTable.json": npc_rows,
        "NpcTemplateGroupTable.json": npc_templates,
        "ResponsiveDialog.json": responsive_dialog,
        "RichContentTable.json": rich_content,
        "WeaponBasicTable.json": weapon_basic,
    }
    collection_table_cache: dict[tuple[str, str], dict] = {
        ("streaming", table_name): payload
        for table_name, payload in collection_preloaded_tables.items()
    }

    def collection_table_name_tokens(table_name: str) -> list[str]:
        stem = table_name.removesuffix(".json")
        return [
            token.lower()
            for token in re.findall(r"[A-Z]+(?=[A-Z][a-z]|\d|$)|[A-Z]?[a-z]+|\d+", stem)
            if token
        ]

    def collection_is_redundant_support_table(table_name: str) -> bool:
        tokens = set(collection_table_name_tokens(table_name))
        return bool({"tag", "title", "label"} & tokens)

    def collection_table_payload(table_source: str, table_name: str) -> dict:
        cache_key = (table_source, table_name)
        if cache_key in collection_table_cache:
            return collection_table_cache[cache_key]
        table_dir = STREAMING_TABLE_DIR if table_source == "streaming" else PERSISTENT_TABLE_DIR
        payload = load_optional_table_json(
            table_dir,
            table_name,
            f"{collection_source_label(table_source)}/{table_name}",
        )
        collection_table_cache[cache_key] = payload if isinstance(payload, dict) else {}
        return collection_table_cache[cache_key]

    def reference_row_texts(text_nodes: list[dict]) -> list[dict]:
        rows: list[dict] = []
        for node in text_nodes:
            raw = node.get("raw") if isinstance(node, dict) else None
            item = {
                "field": str(node.get("field") or "text"),
                "path": str(node.get("path") or "$"),
                "text": str(node.get("text") or ""),
            }
            if node.get("hint"):
                item["hint"] = str(node["hint"])
            if isinstance(raw, dict) and raw.get("id") is not None:
                item["i18nId"] = str(raw.get("id"))
            rows.append(item)
        return rows

    def write_raw_reference_bundle() -> dict:
        reference_dir.mkdir(parents=True, exist_ok=True)
        generated = int(time.time())
        table_index: list[dict] = []
        total_rows = 0
        total_texts = 0
        total_bytes = 0

        for table_source, table_dir in (
            ("streaming", STREAMING_TABLE_DIR),
            ("persistent", PERSISTENT_TABLE_DIR),
        ):
            if not table_dir.exists():
                continue
            source_out_dir = reference_dir / table_source
            source_out_dir.mkdir(parents=True, exist_ok=True)

            for table_path in sorted(table_dir.glob("*.json")):
                table_name = table_path.name
                if table_name.startswith("I18nTextTable_") or table_name == I18N_HOTFIX_TABLE:
                    continue
                payload = collection_table_payload(table_source, table_name)
                if not isinstance(payload, dict) or not payload:
                    continue

                row_payloads: list[dict] = []
                table_texts = 0
                for row_index, (row_id, row) in enumerate(
                    sorted(payload.items(), key=lambda item: str(item[0])),
                    start=1,
                ):
                    row_key = str(row_id)
                    text_nodes = collect_reference_text_nodes(
                        table_name,
                        row_key,
                        row,
                        preferred_source=table_source,
                    )
                    if not text_nodes:
                        continue

                    texts = reference_row_texts(text_nodes)
                    table_texts += len(texts)
                    bucket = collection_bucket(
                        table_name,
                        row_key,
                        row if isinstance(row, dict) else None,
                    )
                    row_payload = {
                        "id": row_key,
                        "title": collection_row_title(
                            table_name,
                            row_key,
                            text_nodes,
                            preferred_source=table_source,
                        ),
                        "bucket": bucket,
                        "order": collection_scene_value(
                            row if isinstance(row, dict) else None,
                            row_index,
                        ),
                        "texts": texts,
                    }
                    row_payloads.append(row_payload)

                if not row_payloads:
                    continue

                rel_file = f"{table_source}/{table_path.stem}.json"
                out_path = reference_dir / rel_file
                out_payload = {
                    "generated": generated,
                    "language": language_code,
                    "source": collection_source_label(table_source),
                    "table": table_name,
                    "label": collection_display_name(table_path.stem),
                    "rows": row_payloads,
                }
                with out_path.open("w", encoding="utf-8") as f:
                    json.dump(out_payload, f, ensure_ascii=False, separators=(",", ":"))
                file_bytes = out_path.stat().st_size
                total_bytes += file_bytes
                total_rows += len(row_payloads)
                total_texts += table_texts
                table_index.append({
                    "source": table_source,
                    "sourceLabel": collection_source_label(table_source),
                    "table": table_name,
                    "label": collection_display_name(table_path.stem),
                    "file": rel_file,
                    "rows": len(row_payloads),
                    "texts": table_texts,
                    "bytes": file_bytes,
                })

        table_index.sort(key=lambda row: (row["source"], row["label"], row["table"]))
        index_payload = {
            "generated": generated,
            "language": language_code,
            "tables": table_index,
            "stats": {
                "tables": len(table_index),
                "rows": total_rows,
                "texts": total_texts,
                "bytes": total_bytes,
            },
        }
        with (reference_dir / "index.json").open("w", encoding="utf-8") as f:
            json.dump(index_payload, f, ensure_ascii=False, separators=(",", ":"))

        print(
            f"Raw reference bundle written: {len(table_index)} tables; "
            f"{total_rows} rows; {total_texts} localized text node(s)"
        )
        return index_payload["stats"]

    ai_bark_reference_cache: dict[str, dict[str, dict[str, str]]] = {}

    def collection_ai_bark_refs(table_source: str) -> dict[str, dict[str, str]]:
        if table_source in ai_bark_reference_cache:
            return ai_bark_reference_cache[table_source]

        refs: dict[str, dict[str, str]] = {}
        responsive_payload = collection_table_payload(table_source, "ResponsiveDialog.json")
        for set_id, top_row in sorted(responsive_payload.items(), key=lambda item: str(item[0])):
            if not isinstance(top_row, dict):
                continue
            speakers = top_row.get("speakers") or {}
            if not isinstance(speakers, dict):
                continue
            for speaker_id, speaker_row in sorted(speakers.items()):
                if not isinstance(speaker_row, dict):
                    continue
                actor_id = speaker_actor_id(str(speaker_id))
                speaker_name = speaker_display_name(str(speaker_id)) or actor_id or str(speaker_id)
                triggers = speaker_row.get("triggers") or {}
                if not isinstance(triggers, dict):
                    continue
                for trigger_key, trigger_row in sorted(triggers.items()):
                    if not isinstance(trigger_row, dict):
                        continue
                    for response_id in (trigger_row.get("response") or []):
                        row_id = str(response_id)
                        current = refs.get(row_id)
                        if current and current.get("source") == "ResponsiveDialog":
                            continue
                        refs[row_id] = {
                            "actorId": actor_id,
                            "speakerId": str(speaker_id),
                            "speakerName": speaker_name,
                            "source": "ResponsiveDialog",
                            "setId": str(set_id),
                            "triggerKey": str(trigger_key),
                        }

        audio_payload = collection_table_payload(table_source, "AudioDialog.json")
        for row_id, audio_row in sorted(audio_payload.items(), key=lambda item: str(item[0])):
            if row_id in refs:
                continue
            if not isinstance(audio_row, dict):
                continue
            speaker_id = str(audio_row.get("speakerChannel") or "")
            actor_id = speaker_actor_id(speaker_id)
            if not actor_id:
                continue
            refs[str(row_id)] = {
                "actorId": actor_id,
                "speakerId": speaker_id,
                "speakerName": speaker_display_name(speaker_id) or actor_id or speaker_id,
                "source": "AudioDialog",
                "audioPath": str(audio_row.get("path") or ""),
            }

        ai_bark_reference_cache[table_source] = refs
        return refs

    def rich_content_row_for_source(content_id: str, table_source: str) -> dict:
        content_key = str(content_id or "").strip()
        if not content_key:
            return {}
        payload = collection_table_payload(table_source, "RichContentTable.json")
        row = payload.get(content_key) if isinstance(payload, dict) else None
        if not isinstance(row, dict) and table_source != "streaming":
            row = rich_content.get(content_key)
        return row if isinstance(row, dict) else {}

    def rich_content_title_text_for_source(content_id: str, table_source: str) -> str:
        row = rich_content_row_for_source(content_id, table_source)
        return t((row.get("title") or {}).get("id"), preferred_source=table_source) if row else ""

    def rich_content_lines_for_source(content_id: str, table_source: str) -> list[dict]:
        row = rich_content_row_for_source(content_id, table_source)
        if not row:
            return []
        out: list[dict] = []
        for idx, item in enumerate(row.get("contentList") or [], start=1):
            if not isinstance(item, dict):
                continue
            content = item.get("content") or {}
            text = t(content.get("id"), preferred_source=table_source)
            out.append({
                "id": f"{content_id}_{idx}",
                "text": text,
                "_debug": {
                    **source_ref(
                        "RichContentTable.contentList",
                        str(content_id),
                        pick_fields(item, "content"),
                        nodeId=idx,
                        tableSource=collection_source_label(table_source),
                    ),
                    "fields": {
                        "text": text_trace(
                            "RichContentTable",
                            str(content_id),
                            "content",
                            content,
                            preferred_source=table_source,
                        ),
                    },
                },
            })
        return out

    def reading_content_refs(table_name: str, row_id: str, row: dict | None, *, table_source: str) -> list[dict]:
        if not isinstance(row, dict):
            return []
        refs: list[dict] = []
        if table_name == "PrtsReading.json":
            items = row.get("list") or {}
            if not isinstance(items, dict):
                return []
            sorted_items = sorted(
                ((node_id, node) for node_id, node in items.items() if isinstance(node, dict)),
                key=lambda item: (int((item[1] or {}).get("order") or 0), str(item[0])),
            )
            for node_id, node in sorted_items:
                content_id = str(node.get("contentId") or "").strip()
                if not content_id:
                    continue
                name = brace_text(t((node.get("name") or {}).get("id"), preferred_source=table_source))
                subtitle = brace_text(t((node.get("subtitle") or {}).get("id"), preferred_source=table_source))
                refs.append({
                    "contentId": content_id,
                    "label": name or subtitle or content_id,
                    "subtitle": subtitle,
                    "path": f"$.list.{node_id}.contentId",
                    "nodeId": node_id,
                    "source": pick_fields(node, "contentId", "name", "order", "subtitle", "uniqId"),
                })
        elif table_name == "ReadingPopUpTable.json":
            content_id = str(row.get("contentId") or "").strip()
            if content_id:
                refs.append({
                    "contentId": content_id,
                    "label": brace_text(t((row.get("title") or {}).get("id"), preferred_source=table_source)) or content_id,
                    "path": "$.contentId",
                    "nodeId": 1,
                    "source": pick_fields(row, "bgType", "contentId", "iconType", "id", "title"),
                })
        return refs

    def append_linked_reading_content_lines(
        table_name: str,
        row_id: str,
        row: dict | None,
        *,
        table_source: str,
        lines: list[dict],
        seen_texts: set[tuple[str, str, str]],
    ) -> tuple[list[dict], str]:
        linked_refs: list[dict] = []
        preview_text = ""
        for ref_index, ref in enumerate(
            reading_content_refs(table_name, row_id, row, table_source=table_source),
            start=1,
        ):
            content_id = str(ref.get("contentId") or "").strip()
            if not content_id:
                continue
            label = str(ref.get("label") or content_id)
            linked_from = source_ref(
                table_name.removesuffix(".json"),
                row_id,
                {
                    "path": ref.get("path") or "$.contentId",
                    "contentId": content_id,
                    **(ref.get("source") or {}),
                },
                nodeId=ref.get("nodeId"),
                tableSource=collection_source_label(table_source),
            )

            rich_title = rich_content_title_text_for_source(content_id, table_source)
            rich_lines = rich_content_lines_for_source(content_id, table_source)
            if rich_title and rich_title != label:
                append_reference_line(
                    lines,
                    seen_texts,
                    f"{row_id}_linked_{ref_index}_title",
                    rich_title,
                    hint=f"{label} / Title",
                    debug={
                        **source_ref(
                            "RichContentTable",
                            content_id,
                            {"title": (rich_content_row_for_source(content_id, table_source).get("title") or {})},
                            tableSource=collection_source_label(table_source),
                        ),
                        "linkedFrom": linked_from,
                        "fields": {
                            "text": text_trace(
                                "RichContentTable",
                                content_id,
                                "title",
                                (rich_content_row_for_source(content_id, table_source).get("title") or {}),
                                preferred_source=table_source,
                            ),
                        },
                    },
                )
                preview_text = preview_text or rich_title

            if rich_lines:
                linked_refs.append({
                    "contentId": content_id,
                    "source": "RichContentTable",
                    "lineCount": len(rich_lines),
                    "label": label,
                })
                for content_index, content_line in enumerate(rich_lines, start=1):
                    text = str(content_line.get("text") or "")
                    debug = dict(content_line.get("_debug") or {})
                    debug["linkedFrom"] = linked_from
                    append_reference_line(
                        lines,
                        seen_texts,
                        f"{row_id}_linked_{ref_index}_{content_index}",
                        text,
                        hint=rich_title or label,
                        debug=debug,
                    )
                    if text:
                        preview_text = preview_text or text
                continue

            radio_row = radio_row_lookup.get(content_id)
            if radio_row:
                radio_lines = [line for line in (radio_row.get("lines") or []) if isinstance(line, dict)]
                linked_refs.append({
                    "contentId": content_id,
                    "source": "RadioTable",
                    "lineCount": len(radio_lines),
                    "label": label,
                })
                for content_index, radio_line in enumerate(radio_lines, start=1):
                    text = str(radio_line.get("text") or "")
                    debug = dict(radio_line.get("_debug") or {})
                    debug["linkedFrom"] = linked_from
                    append_reference_line(
                        lines,
                        seen_texts,
                        f"{row_id}_linked_{ref_index}_{content_index}",
                        text,
                        hint=label,
                        actor=str(radio_line.get("actor") or ""),
                        aid=str(radio_line.get("aid") or ""),
                        debug=debug,
                    )
                    if text:
                        preview_text = preview_text or text

        return linked_refs, preview_text

    def write_generic_collection_pages(
        table_source: str,
        *,
        dedupe_against_streaming: bool = False,
    ) -> tuple[int, int]:
        table_dir = STREAMING_TABLE_DIR if table_source == "streaming" else PERSISTENT_TABLE_DIR
        if not table_dir.exists():
            return (0, 0)
        generic_collection_paths = [
            path
            for path in sorted(table_dir.glob("*.json"))
            if not path.name.startswith("I18nTextTable_")
            and path.name not in collection_omit_tables
            and not path.name.startswith(collection_omit_prefixes)
            and not collection_is_redundant_support_table(path.name)
            and (table_source != "streaming" or path.name not in collection_skip_tables)
        ]
        label = "generic" if table_source == "streaming" else "supplemental persistent"
        print(
            f"Writing {label} collection pages from {len(generic_collection_paths)} tables..."
        )
        generic_collection_pages = 0
        generic_collection_tables = 0
        for table_path in generic_collection_paths:
            table_name = table_path.name
            payload = collection_table_payload(table_source, table_name)
            if not isinstance(payload, dict) or not payload:
                continue

            table_pages = 0
            table_label = collection_display_name(table_path.stem)
            streaming_payload = (
                collection_table_payload("streaming", table_name)
                if dedupe_against_streaming
                else {}
            )
            for row_index, (row_id, row) in enumerate(sorted(payload.items(), key=lambda item: str(item[0])), start=1):
                row_key = str(row_id)
                if table_name == "RichContentTable.json" and row_key in prts_content_ids:
                    continue
                forced_kind = None
                text_nodes = collect_reference_text_nodes(
                    table_name,
                    row_key,
                    row,
                    preferred_source=table_source,
                )
                if not text_nodes:
                    continue
                if (
                    table_name == "RichContentTable.json"
                    and text_sequence_fingerprint(text_nodes) in wiki_text_fingerprints
                ):
                    continue

                variant = False
                if dedupe_against_streaming:
                    streaming_row = streaming_payload.get(row_key) if isinstance(streaming_payload, dict) else None
                    if streaming_row is not None:
                        streaming_nodes = collect_reference_text_nodes(
                            table_name,
                            row_key,
                            streaming_row,
                            preferred_source="streaming",
                        )
                        if collection_text_fingerprint(streaming_nodes) == collection_text_fingerprint(text_nodes):
                            continue
                        variant = bool(streaming_nodes)

                bucket = collection_bucket(table_name, row_key, row if isinstance(row, dict) else None)
                bucket_token = collection_bucket_token(bucket)
                story_ref = collection_reading_story_ref(
                    table_name,
                    row_key,
                    row if isinstance(row, dict) else None,
                ) or collection_story_ref_from_bucket(bucket)
                if story_ref:
                    mission_id, forced_scene_value, forced_type_key = story_ref
                    if not forced_scene_value:
                        forced_scene_value = collection_scene_value(row if isinstance(row, dict) else None, row_index)
                    extra_mission_names.setdefault(mission_id, collection_display_name(mission_id))
                else:
                    mission_id = (
                        f"wiki_collection_{collection_slug(table_source)}_"
                        f"{collection_slug(table_path.stem)}_{bucket_token}"
                    )
                    forced_scene_value = collection_scene_value(row if isinstance(row, dict) else None, row_index)
                    forced_type_key = forced_kind

                title = collection_row_title(
                    table_name,
                    row_key,
                    text_nodes,
                    preferred_source=table_source,
                )
                lines: list[dict] = []
                seen_texts: set[tuple[str, str, str]] = set()
                for node_index, node in enumerate(text_nodes, start=1):
                    hint = node.get("hint") or collection_display_name(node.get("field") or "text")
                    append_reference_line(
                        lines,
                        seen_texts,
                        f"{row_key}_{node_index}",
                        node.get("text") or "",
                        hint=hint,
                        debug={
                            **source_ref(
                                table_path.stem,
                                row_key,
                                {
                                    "path": node.get("path") or "$",
                                },
                                nodeId=node_index,
                                tableSource=collection_source_label(table_source),
                            ),
                            "fields": {
                                "text": text_trace(
                                    table_path.stem,
                                    row_key,
                                    str(node.get("path") or "$"),
                                    node.get("raw"),
                                    preferred_source=table_source,
                                ),
                            },
                        },
                    )
                linked_content_refs, linked_preview_text = append_linked_reading_content_lines(
                    table_name,
                    row_key,
                    row if isinstance(row, dict) else None,
                    table_source=table_source,
                    lines=lines,
                    seen_texts=seen_texts,
                )
                if not lines:
                    continue

                out_key = (
                    f"wiki_collection_{collection_slug(table_source)}_"
                    f"{collection_slug(table_path.stem)}_{row_key}"
                )
                summary_rows = collection_summary_rows(
                    table_name,
                    row_key,
                    row if isinstance(row, dict) else None,
                    bucket,
                    table_source=table_source,
                    variant=variant,
                )
                debug_extra = {}
                if linked_content_refs:
                    total_linked_lines = sum(int(ref.get("lineCount") or 0) for ref in linked_content_refs)
                    summary_rows.append({
                        "text": f"Linked content: {len(linked_content_refs)} ref(s), {total_linked_lines} line(s)",
                    })
                    debug_extra["linkedContent"] = linked_content_refs
                search_parts = [
                    table_label,
                    row_key,
                    bucket,
                    table_source,
                ]
                if isinstance(row, dict):
                    for field in ("groupId", "categoryId", "type", "gameCategory", "charId", "profession", "weaponType", "owner"):
                        value = row.get(field)
                        if value not in (None, "", [], {}):
                            search_parts.append(str(value))
                page_tags = collection_tags(
                    table_name,
                    row_key,
                    bucket,
                    row if isinstance(row, dict) else None,
                    table_source=table_source,
                    variant=variant,
                )
                write_reference_page(
                    out_key,
                    mission_id,
                    forced_scene_value,
                    title,
                    lines,
                    kind=forced_kind,
                    type_key=forced_type_key,
                    source_debug=source_ref(
                        table_path.stem,
                        row_key,
                        {"table": table_name},
                        tableSource=collection_source_label(table_source),
                        variantOf="StreamingAssets/Table" if variant else None,
                    ),
                    summary_rows=summary_rows,
                    tags=page_tags,
                    search_parts=search_parts,
                    preview_text=linked_preview_text or None,
                    debug_extra=debug_extra or None,
                )
                table_pages += 1
                generic_collection_pages += 1

            if table_pages:
                generic_collection_tables += 1
                print(f"  collection {table_source} {table_name}: {table_pages} pages")

        return generic_collection_pages, generic_collection_tables

    if include_reference_in_story_index:
        generic_collection_pages, generic_collection_tables = write_generic_collection_pages("streaming")
        persistent_collection_pages, persistent_collection_tables = write_generic_collection_pages(
            "persistent",
            dedupe_against_streaming=True,
        )

        print(
            f"Generic collection pages written: {generic_collection_pages + persistent_collection_pages} "
            f"across {generic_collection_tables + persistent_collection_tables} tables"
        )
    else:
        print("Skipping generic table collection pages for lean story profile.")

    reference_stats: dict = {}
    if write_reference:
        reference_stats = write_raw_reference_bundle()

    print(f"Writing {len(mail_templates)} mail conversations...")
    for template_id, row in sorted(mail_templates.items()):
        if not isinstance(row, dict):
            continue
        sender_id = str(row.get("senderId") or "system")
        sender_row = mail_senders.get(sender_id) if isinstance(mail_senders.get(sender_id), dict) else {}
        sender_name = (
            brace_text(t((sender_row.get("senderName") or {}).get("id")))
            or speaker_display_name(sender_id)
            or sender_id
        )
        title = brace_text(t((row.get("title") or {}).get("id"))) or template_id
        body = t((row.get("mailContent") or {}).get("id"))
        out_key = f"mail_{template_id}"
        if sender_name:
            extra_mission_names[sender_id] = sender_name
        summary: list[dict] = []
        if row.get("rewardId"):
            summary.append({"text": f"Reward: {row['rewardId']}"})
        if row.get("duration") is not None:
            summary.append({"text": f"Duration: {row['duration']}"})
        if row.get("type") is not None:
            summary.append({"text": f"Type: {row['type']}"})
        lines = [{
            "id": template_id,
            "aid": sender_id,
            "actor": sender_name,
            "text": body,
            "_debug": {
                **source_ref(
                    "MailTemplateTable",
                    template_id,
                    pick_fields(row, "duration", "mailContent", "rewardId", "senderId", "templateId", "title", "type"),
                ),
                "fields": {
                    "title": text_trace("MailTemplateTable", template_id, "title", row.get("title")),
                    "text": text_trace("MailTemplateTable", template_id, "mailContent", row.get("mailContent")),
                },
            },
        }]
        payload = {
            "key": out_key,
            "kind": "mail",
            "mission": sender_id,
            "scene": 0,
            "title": title,
            "lines": lines,
            "_debug": {
                "source": source_ref(
                    "MailTemplateTable",
                    template_id,
                    pick_fields(row, "duration", "mailContent", "rewardId", "senderId", "templateId", "title", "type"),
                ),
            },
        }
        if summary:
            payload["summary"] = summary
        if sender_row:
            payload["_debug"]["sender"] = source_ref(
                "MailSenderTable",
                sender_id,
                pick_fields(sender_row, "id", "senderIcon", "senderName"),
            )
        with (conv_dir / f"{out_key}.json").open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        entry = {
            "k": out_key,
            "d": "mail",
            "m": sender_id,
            "s": 0,
            "t": "mail",
            "a": 0,
            "title": title,
            "c": [sender_id] if sender_id else [],
            "n": len(lines),
            "p": preview(body or title),
            "tags": ["mail"],
        }
        search_text = " ".join(part for part in [
            template_id,
            sender_id,
            sender_name,
            title,
            body,
            str(row.get("rewardId") or ""),
        ] if part)
        if search_text:
            entry["x"] = search_text
        index_entries.append(entry)

    embedded_prts_notes_by_entry: dict[str, list[dict]] = defaultdict(list)
    embedded_prts_note_ids: set[str] = set()
    for note_id, note_meta in sorted(prts_note_metadata.items()):
        note_key = str(note_id or "").strip()
        if not note_key.startswith("hint_research"):
            continue
        note_row = prts_notes.get(note_key)
        if not isinstance(note_row, dict):
            continue
        linked_entry_ids = [
            str(value)
            for value in (note_meta.get("collectionIds") or [])
            if str(value)
        ]
        if not linked_entry_ids:
            continue
        note_text = t((note_row.get("desc") or {}).get("id"))
        if not note_text:
            continue
        embedded_prts_note_ids.add(note_key)
        embedded_note = {
            "id": note_key,
            "title": str(note_meta.get("title") or note_key),
            "text": note_text,
            "researchId": str(note_meta.get("researchId") or ""),
            "index": int(note_meta.get("index") or 0),
        }
        for linked_entry_id in linked_entry_ids:
            linked_key = str(linked_entry_id or "").strip()
            if not linked_key:
                continue
            embedded_prts_notes_by_entry[linked_key].append(dict(embedded_note))

    def resolve_prts_payload(content_id: str) -> tuple[list[dict], list[dict], dict]:
        lines = rich_content_lines(content_id)
        summary_rows: list[dict] = []
        debug_extra: dict = {}
        if rich_row := rich_content.get(content_id):
            rich_title = rich_content_title_text(content_id)
            if rich_title:
                summary_rows.append({"text": f"Content: {rich_title}"})
            debug_extra["content"] = source_ref(
                "RichContentTable",
                content_id,
                pick_fields(rich_row, "title", "contentList"),
            )
        elif radio_row := radio_row_lookup.get(content_id):
            lines = list(radio_row.get("lines") or [])
            summary_rows.append({"text": f"Linked radio: {content_id}"})
        else:
            summary_rows.append({"text": f"Content ref: {content_id}"})
        return lines, summary_rows, debug_extra

    def prts_attachment_aliases(value: str) -> set[str]:
        raw = str(value or "").strip()
        if not raw:
            return set()
        aliases = {raw}
        lowered = raw.lower()
        if lowered.startswith("prts_") and lowered.endswith("_sns"):
            aliases.add(f"sns_{raw[5:-4]}")
        if lowered.startswith("reading_") and lowered.endswith("_sns"):
            aliases.add(f"sns_{raw[8:-4]}")
        return aliases

    def prts_row_attachment_aliases(
        row_id: str,
        content_id: str,
        first_lv_id: str,
        first_lv_row: dict,
    ) -> set[str]:
        aliases: set[str] = set()
        for value in (row_id, content_id, first_lv_id, first_lv_row.get("icon")):
            aliases.update(prts_attachment_aliases(str(value or "")))
        return aliases

    prts_attachment_story_refs: dict[str, tuple[str, int, str]] = {}
    for sns_id, sns_entry in sns_groups.items():
        match = SNS_RE.match(sns_id)
        if not match:
            continue
        mission_id = match.group(1)
        scene_value = int(match.group(2))
        type_key, _act = parse_mission(mission_id)
        if type_key not in MISSION_STORY_TYPES:
            continue
        story_ref = (mission_id, scene_value, type_key)
        cdata = sns_entry.get("dialogContentData") or {}
        if not isinstance(cdata, dict):
            continue
        for node in cdata.values():
            if not isinstance(node, dict):
                continue
            values: list[str] = []
            content_param = node.get("contentParam")
            if isinstance(content_param, list):
                values.extend(str(value) for value in content_param if str(value))
            elif content_param not in (None, "", [], {}):
                values.append(str(content_param))
            content_params = node.get("contentParams")
            if isinstance(content_params, list):
                values.extend(str(value) for value in content_params if str(value))
            elif content_params not in (None, "", [], {}):
                values.append(str(content_params))
            for value in values:
                for alias in prts_attachment_aliases(value):
                    prts_attachment_story_refs.setdefault(alias, story_ref)

    standalone_prts_note_count = sum(
        1
        for note_id, row in prts_notes.items()
        if isinstance(row, dict) and str(note_id) not in embedded_prts_note_ids
    )
    print(f"Writing {len(prts_all_items) + standalone_prts_note_count} PRTS entries...")
    for row_id, row in sorted(prts_all_items.items(), key=lambda item: (
        str(item[1].get("firstLvId") or ""),
        int(item[1].get("order") or 0),
        item[0],
    )):
        if not isinstance(row, dict):
            continue
        content_id = str(row.get("contentId") or "")
        first_lv_id = str(row.get("firstLvId") or row.get("type") or "prts")
        first_lv_row = prts_first_lv.get(first_lv_id) if isinstance(prts_first_lv.get(first_lv_id), dict) else {}
        category_id = str(first_lv_row.get("categoryId") or row.get("type") or "prts")
        page_row = prts_page.get(category_id) if isinstance(prts_page.get(category_id), dict) else {}
        mission_label = brace_text(t((first_lv_row.get("name") or {}).get("id"))) or first_lv_id
        if mission_label:
            extra_mission_names[first_lv_id] = mission_label
        story_ref = collection_story_ref_from_identifiers(
            content_id,
            row_id,
            first_lv_id,
        )
        if not story_ref:
            for alias in prts_row_attachment_aliases(row_id, content_id, first_lv_id, first_lv_row):
                story_ref = prts_attachment_story_refs.get(alias)
                if story_ref:
                    break
        if not story_ref:
            story_ref = collection_map_ref_from_identifiers(content_id, row_id, first_lv_id)
        entry_mission_id = first_lv_id
        entry_scene = int(row.get("order") or 0)
        entry_type = "prts"
        if story_ref:
            entry_mission_id, story_scene, entry_type = story_ref
            entry_scene = story_scene or entry_scene
            extra_mission_names.setdefault(entry_mission_id, collection_display_name(entry_mission_id))
        title = (
            brace_text(t((row.get("name") or {}).get("id")))
            or rich_content_title_text(content_id)
            or row_id
        )
        subtitle = brace_text(t((first_lv_row.get("subName") or {}).get("id")))
        desc = t((row.get("desc") or {}).get("id"))
        lines, summary_rows, debug_extra = resolve_prts_payload(content_id)
        page_label = brace_text(t((page_row.get("name") or {}).get("id"))) or category_id
        if page_label:
            summary_rows.insert(0, {"text": f"Page: {page_label}"})
        if subtitle:
            summary_rows.append({"text": f"Section: {subtitle}"})
        if desc:
            summary_rows.append({"text": desc})
        linked_research_rows = prts_investigate_metadata_by_unlock_prts.get(str(row_id)) or []
        if linked_research_rows:
            for research_row in linked_research_rows:
                research_title = str(research_row.get("title") or "").strip()
                research_desc = str(research_row.get("desc") or "").strip()
                if research_title:
                    summary_rows.append({"text": f"Research: {research_title}"})
                if research_desc:
                    summary_rows.append({"text": research_desc})
            debug_extra["linkedResearch"] = [
                {
                    "researchId": str(research_row.get("researchId") or ""),
                    "title": str(research_row.get("title") or ""),
                    "desc": str(research_row.get("desc") or ""),
                }
                for research_row in linked_research_rows
            ]
        linked_notes = embedded_prts_notes_by_entry.get(str(row_id)) or []
        if linked_notes:
            summary_rows.append({"text": f"Archive notes: {len(linked_notes)}"})
            seen_note_lines: set[tuple[str, str, str]] = set()
            for line in lines:
                normalized = re.sub(r"\s+", " ", str(line.get("text") or "")).strip()
                if not normalized:
                    continue
                seen_note_lines.add((str(line.get("hint") or ""), str(line.get("actor") or ""), normalized))
            linked_note_debug: list[dict] = []
            for note in linked_notes:
                note_id = str(note.get("id") or "")
                note_row = prts_notes.get(note_id) if isinstance(prts_notes.get(note_id), dict) else {}
                note_title = str(note.get("title") or note_id or "Archive Note")
                append_reference_line(
                    lines,
                    seen_note_lines,
                    note_id or row_id,
                    str(note.get("text") or ""),
                    hint=note_title,
                    debug={
                        **source_ref(
                            "PrtsNote",
                            note_id,
                            {
                                "linkedEntry": row_id,
                                "researchId": str(note.get("researchId") or ""),
                            },
                        ),
                        "fields": {
                            "text": text_trace("PrtsNote", note_id, "desc", note_row.get("desc")),
                        },
                    },
                )
                linked_note_debug.append({
                    "noteId": note_id,
                    "title": note_title,
                    "researchId": str(note.get("researchId") or ""),
                    "index": int(note.get("index") or 0),
                })
            if linked_note_debug:
                debug_extra["linkedNotes"] = linked_note_debug
        payload = {
            "key": row_id,
            "kind": "prts",
            "mission": entry_mission_id,
            "scene": entry_scene,
            "title": title,
            "lines": lines,
            "_debug": {
                "source": source_ref(
                    "PrtsAllItem",
                    row_id,
                    pick_fields(row, "contentId", "desc", "firstLvId", "id", "name", "order", "type"),
                ),
            },
        }
        if summary_rows:
            payload["summary"] = summary_rows
        if first_lv_row:
            payload["_debug"]["firstLevel"] = source_ref(
                "PrtsFirstLv",
                first_lv_id,
                pick_fields(first_lv_row, "categoryId", "firstLvId", "icon", "itemIds", "name", "order", "subName"),
            )
        if page_row:
            payload["_debug"]["page"] = source_ref(
                "PrtsPage",
                category_id,
                pick_fields(page_row, "icon", "name", "pageType"),
            )
        payload["_debug"].update(debug_extra)
        with (conv_dir / f"{row_id}.json").open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        entry = {
            "k": row_id,
            "d": "prts",
            "m": entry_mission_id,
            "s": entry_scene,
            "t": entry_type,
            "a": 0,
            "title": title,
            "c": [],
            "n": len(lines),
            "p": preview(next((line.get("text") or "" for line in lines if line.get("text")), title)),
            "tags": [str(row.get("type") or "prts"), category_id],
        }
        search_text = " ".join(part for part in [
            row_id,
            content_id,
            first_lv_id,
            category_id,
            page_label,
            mission_label,
            subtitle,
            title,
            desc,
            " ".join(line.get("text") or "" for line in lines),
        ] if part)
        if search_text:
            entry["x"] = search_text
        index_entries.append(entry)

    for note_id, row in sorted(prts_notes.items()):
        if not isinstance(row, dict):
            continue
        if str(note_id) in embedded_prts_note_ids:
            continue
        text = t((row.get("desc") or {}).get("id"))
        note_meta = prts_note_metadata.get(note_id) or {}
        note_title = str(note_meta.get("title") or note_id)
        note_category = str(note_meta.get("category") or "")
        note_collection_ids = [
            str(value)
            for value in (note_meta.get("collectionIds") or [])
            if str(value)
        ]
        summary_rows: list[dict] = []
        if note_category:
            summary_rows.append({"text": f"Category: {prts_category_display_name(note_category)}"})
        if note_collection_ids:
            preview_ids = ", ".join(note_collection_ids[:3])
            if len(note_collection_ids) > 3:
                preview_ids += ", ..."
            summary_rows.append({"text": f"Linked entries: {preview_ids}"})
        payload = {
            "key": note_id,
            "kind": "prts",
            "mission": "PrtsNote",
            "scene": 0,
            "title": note_title,
            "lines": [{
                "id": note_id,
                "text": text,
                "_debug": {
                    **source_ref("PrtsNote", note_id, pick_fields(row, "desc", "id")),
                    "fields": {
                        "text": text_trace("PrtsNote", note_id, "desc", row.get("desc")),
                    },
                },
            }],
            "_debug": {
                "source": source_ref("PrtsNote", note_id, pick_fields(row, "desc", "id")),
            },
        }
        if summary_rows:
            payload["summary"] = summary_rows
        with (conv_dir / f"{note_id}.json").open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        note_tags = ["note"]
        if note_category:
            note_tags.extend([note_category, f"category_{collection_slug(note_category)}"])
        entry = {
            "k": note_id,
            "d": "prts",
            "m": "PrtsNote",
            "s": 0,
            "t": "prts",
            "a": 0,
            "title": note_title,
            "c": [],
            "n": 1,
            "p": preview(text or note_title),
            "tags": note_tags,
        }
        search_parts = [note_id, note_title, note_category, prts_category_display_name(note_category)]
        if text:
            search_parts.append(text)
        if note_collection_ids:
            search_parts.extend(note_collection_ids)
        entry["x"] = " ".join(part for part in search_parts if part)
        index_entries.append(entry)

    def responsive_sort_values(values: set[str] | list[str]) -> list[str]:
        tokens = [str(value) for value in values if str(value)]
        return sorted(
            tokens,
            key=lambda value: (0, int(value)) if value.lstrip("-").isdigit() else (1, value),
        )

    def responsive_preview_values(values: list[str], *, limit: int = 4) -> str:
        tokens = [str(value) for value in values if str(value)]
        if not tokens:
            return ""
        if len(tokens) <= limit:
            return ", ".join(tokens)
        return ", ".join(tokens[:limit]) + f" +{len(tokens) - limit}"

    def responsive_summary_rows(label: str, values: list[str], *, chunk_size: int = 8) -> list[dict]:
        tokens = [str(value) for value in values if str(value)]
        rows: list[dict] = []
        for idx, start in enumerate(range(0, len(tokens), chunk_size), start=1):
            prefix = label if idx == 1 else f"{label} (cont.)"
            rows.append({"text": f"{prefix}: {', '.join(tokens[start:start + chunk_size])}"})
        return rows

    responsive_refs = collection_ai_bark_refs("streaming")
    responsive_people: dict[str, dict] = {}
    for response_id, bark_row in sorted(ai_bark_text.items(), key=lambda item: str(item[0])):
        if not isinstance(bark_row, dict):
            continue
        response_key = str(response_id)
        ref = responsive_refs.get(response_key) or {}
        speaker_id = str(ref.get("speakerId") or "")
        actor_id = str(ref.get("actorId") or speaker_actor_id(speaker_id) or "")
        person_key = actor_id or speaker_id or response_key
        display_name = (
            str(ref.get("speakerName") or "")
            or speaker_display_name(speaker_id)
            or speaker_display_name(actor_id)
            or actor_id
            or speaker_id
            or person_key
        )
        group = responsive_people.setdefault(
            person_key,
            {
                "displayName": display_name,
                "actorId": actor_id,
                "speakerIds": set(),
                "setIds": set(),
                "triggerKeys": set(),
                "responseIds": [],
                "audioOnlyResponseIds": set(),
                "audioPaths": set(),
                "linesByText": {},
            },
        )
        if display_name and (not group.get("displayName") or group["displayName"] == person_key):
            group["displayName"] = display_name
        if actor_id and not group.get("actorId"):
            group["actorId"] = actor_id

        if speaker_id:
            group["speakerIds"].add(speaker_id)
        if ref.get("setId"):
            group["setIds"].add(str(ref["setId"]))
        if ref.get("triggerKey"):
            group["triggerKeys"].add(str(ref["triggerKey"]))
        if ref.get("audioPath"):
            group["audioPaths"].add(str(ref["audioPath"]))
        group["responseIds"].append(response_key)

        bark_text = t((bark_row.get("barkText") or {}).get("id"))
        normalized_text = re.sub(r"\s+", " ", str(bark_text or "")).strip()
        if not normalized_text:
            if ref.get("audioPath"):
                group["audioOnlyResponseIds"].add(response_key)
            continue

        set_id = str(ref.get("setId") or "")
        set_sort = int(set_id) if set_id.lstrip("-").isdigit() else 10**9
        trigger_key = str(ref.get("triggerKey") or "")
        source_payload = {
            "responseId": response_key,
            "speakerId": speaker_id,
            "actorId": actor_id,
            "setId": set_id,
            "triggerKey": trigger_key,
            "audioPath": str(ref.get("audioPath") or ""),
            "source": str(ref.get("source") or ""),
        }

        line_info = group["linesByText"].get(normalized_text)
        if line_info is None:
            line_info = {
                "id": response_key,
                "text": bark_text,
                "speakerIds": set([speaker_id]) if speaker_id else set(),
                "setIds": set([set_id]) if set_id else set(),
                "triggerKeys": set([trigger_key]) if trigger_key else set(),
                "responseIds": [response_key],
                "audioPaths": set([str(ref.get("audioPath") or "")]) if ref.get("audioPath") else set(),
                "sourceRefs": [source_payload],
                "fieldTrace": text_trace("AIBarkText", response_key, "barkText", bark_row.get("barkText")),
                "sortKey": (set_sort, trigger_key or "~", response_key),
            }
            group["linesByText"][normalized_text] = line_info
        else:
            if speaker_id:
                line_info["speakerIds"].add(speaker_id)
            if set_id:
                line_info["setIds"].add(set_id)
            if trigger_key:
                line_info["triggerKeys"].add(trigger_key)
            if ref.get("audioPath"):
                line_info["audioPaths"].add(str(ref["audioPath"]))
            line_info["responseIds"].append(response_key)
            line_info["sourceRefs"].append(source_payload)
            line_info["sortKey"] = min(line_info["sortKey"], (set_sort, trigger_key or "~", response_key))

    print(f"Writing {len(responsive_people)} responsive conversations...")
    for person_key, group in sorted(
        responsive_people.items(),
        key=lambda item: ((item[1].get("displayName") or item[0]).lower(), item[0]),
    ):
        display_name = str(group.get("displayName") or person_key)
        actor_id = str(group.get("actorId") or person_key)
        mission_id = actor_id or person_key
        if display_name:
            extra_mission_names[mission_id] = display_name

        lines: list[dict] = []
        for line_info in sorted(group["linesByText"].values(), key=lambda item: item["sortKey"]):
            trigger_keys = sorted(line_info["triggerKeys"])
            set_ids = responsive_sort_values(line_info["setIds"])
            hint_bits: list[str] = []
            if trigger_keys:
                hint_bits.append(f"Triggers: {responsive_preview_values(trigger_keys)}")
            if set_ids:
                hint_bits.append(f"Sets: {responsive_preview_values(set_ids)}")
            if not trigger_keys and line_info["audioPaths"]:
                hint_bits.append("Audio fallback")
            if len(line_info["responseIds"]) > 1:
                hint_bits.append(f"Responses: {len(line_info['responseIds'])}")
            line = {
                "id": line_info["id"],
                "aid": actor_id,
                "actor": display_name,
                "text": line_info["text"],
                "_debug": {
                    "source": {
                        "table": "AIBarkText",
                        "actorId": actor_id,
                        "speakerIds": sorted(line_info["speakerIds"]),
                        "setIds": set_ids,
                        "triggerKeys": trigger_keys,
                        "responseIds": responsive_sort_values(line_info["responseIds"]),
                        "audioPaths": sorted(line_info["audioPaths"]),
                        "refs": line_info["sourceRefs"],
                    },
                    "fields": {
                        "text": line_info["fieldTrace"],
                    },
                },
            }
            if hint_bits:
                line["hint"] = " | ".join(hint_bits)
            lines.append(line)

        duplicate_count = max(0, len(group["responseIds"]) - len(lines))
        summary_rows = [
            {"text": f"Speaker: {display_name}"},
            {"text": f"Actor ID: {actor_id}"},
            {"text": f"Unique lines: {len(lines)}"},
            {"text": f"Source bark rows: {len(group['responseIds'])}"},
        ]
        if duplicate_count:
            summary_rows.append({"text": f"Duplicate bark rows merged: {duplicate_count}"})
        if group["audioOnlyResponseIds"]:
            summary_rows.append({"text": f"Audio fallback rows: {len(group['audioOnlyResponseIds'])}"})
        summary_rows.extend(
            responsive_summary_rows("Speaker IDs", sorted(group["speakerIds"]), chunk_size=6)
        )
        summary_rows.extend(
            responsive_summary_rows("Trigger sets", responsive_sort_values(group["setIds"]), chunk_size=12)
        )
        summary_rows.extend(
            responsive_summary_rows("Trigger keys", sorted(group["triggerKeys"]), chunk_size=8)
        )

        out_key = f"responsive_{person_key}"
        payload = {
            "key": out_key,
            "kind": "responsive",
            "mission": mission_id,
            "scene": 0,
            "title": display_name,
            "lines": lines,
            "summary": summary_rows,
            "_debug": {
                "source": {
                    "table": "AIBarkText",
                    "personKey": person_key,
                    "actorId": actor_id,
                    "speakerIds": sorted(group["speakerIds"]),
                    "setIds": responsive_sort_values(group["setIds"]),
                    "triggerKeys": sorted(group["triggerKeys"]),
                    "responseIds": responsive_sort_values(group["responseIds"]),
                    "audioOnlyResponseIds": responsive_sort_values(group["audioOnlyResponseIds"]),
                    "audioPaths": sorted(group["audioPaths"]),
                },
            },
        }
        with (conv_dir / f"{out_key}.json").open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        entry = {
            "k": out_key,
            "d": "responsive",
            "m": mission_id,
            "s": 0,
            "t": "responsive",
            "a": 0,
            "title": payload["title"],
            "c": [actor_id],
            "n": len(lines),
            "p": preview(next((line.get("text") or "" for line in lines if line.get("text")), payload["title"])),
            "tags": ["responsive"],
        }
        search_text = " ".join(
            part
            for part in [
                person_key,
                actor_id,
                display_name,
                " ".join(sorted(group["speakerIds"])),
                " ".join(responsive_sort_values(group["setIds"])),
                " ".join(sorted(group["triggerKeys"])),
                " ".join(line.get("hint") or "" for line in lines),
                " ".join(line.get("text") or "" for line in lines),
            ]
            if part
        )
        if search_text:
            entry["x"] = search_text
        index_entries.append(entry)

    # Emit unmatched dialog ids (utility/spaceship/etc.) as a single bucket per prefix.
    if misc:
        misc_groups: dict[str, list[tuple[str, dict]]] = defaultdict(list)
        for did, e in misc:
            # Group on the substring up to the last underscore-then-digits.
            key = re.sub(r"_\d+(_\d+)?$", "", did) or "_misc"
            misc_groups[key].append((did, e))
        print(f"Writing {len(misc_groups)} misc dialog buckets...")
        for key, items in misc_groups.items():
            items.sort(key=lambda x: x[0])
            lines = []
            actors: set[str] = set()
            for did, e in items:
                actor_id = e.get("actorNameId") or ""
                text = t(e.get("dialogText", {}).get("id"))
                if actor_id:
                    actors.add(actor_id)
                lines.append({
                    "id": did,
                    "aid": actor_id,
                    "actor": t(e.get("actorName", {}).get("id")),
                    "text": text,
                    "hint": t(e.get("hint", {}).get("id")),
                    "audio": e.get("audioOverride") or "",
                    "emo": e.get("emotionType", 0),
                    "_debug": {
                        **source_ref(
                            "DialogTextTable",
                            did,
                            pick_fields(
                                e,
                                "actorNameId",
                                "actorName",
                                "dialogText",
                                "hint",
                                "audioOverride",
                                "emotionType",
                            ),
                        ),
                        "fields": {
                            "actor": text_trace("DialogTextTable", did, "actorName", e.get("actorName")),
                            "text": text_trace("DialogTextTable", did, "dialogText", e.get("dialogText")),
                            "hint": text_trace("DialogTextTable", did, "hint", e.get("hint")),
                        },
                    },
                })
            out_key = f"misc_{key}"
            type_, act, mission, scene = slot_misc(key)
            ordered_line_ids, line_order_debug = resolve_scene_line_order(
                key,
                [line.get("id") or "" for line in lines],
            )
            if ordered_line_ids:
                line_order_index = {line_id: idx for idx, line_id in enumerate(ordered_line_ids)}
                lines = [
                    line
                    for _idx, line in sorted(
                        enumerate(lines),
                        key=lambda item: (
                            line_order_index.get(item[1].get("id") or "", len(ordered_line_ids) + item[0]),
                            item[0],
                        ),
                    )
                ]
            prev_text = next((line.get("text") or "" for line in lines if line.get("text")), "")
            payload = {
                "key": out_key, "kind": "dlg",
                "mission": mission, "scene": scene,
                "lines": lines,
                "_debug": {
                    "title": mission_name_trace(mission),
                },
            }
            if line_order_debug:
                payload["_debug"]["lineOrder"] = line_order_debug
            if out_key in summary_by_key:
                payload["summary"] = summary_by_key[out_key]
            if out_key in options_by_key:
                packed_options = pack_options(options_by_key[out_key], lines, key)
                payload["optionGroups"] = packed_options["groups"]
                if packed_options["warnings"]:
                    payload["warnings"] = packed_options["warnings"]
            line_graph = build_dialog_tree_line_graph_payload(
                key,
                [line.get("id") or "" for line in lines],
            )
            if line_graph:
                payload["lineGraph"] = line_graph
            graph_fragments = build_dialog_tree_fragment_payload(key)
            if graph_fragments:
                payload["graphFragments"] = graph_fragments
            scene_graph_links = build_dialog_tree_scene_link_payload(key)
            if scene_graph_links:
                payload["sceneGraphLinks"] = scene_graph_links
                scene_graph_links_by_key[out_key] = scene_graph_links
            attach_runtime_registry_debug(payload)
            attach_scene_order_warning(payload)
            with (conv_dir / f"{out_key}.json").open("w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
            entry = {
                "k": out_key, "d": "dlg", "m": mission, "s": scene,
                "t": type_, "a": act, "c": sorted(actors),
                "n": len(lines), "p": preview(prev_text),
            }
            if (tags := entry_tags(out_key, mission)):
                entry["tags"] = tags
            entry["x"] = merge_search_text(
                extras_text(out_key),
                mission_context_text(mission),
            )
            entry["x"] = merge_search_text(entry.get("x", ""), graph_fragments_text(graph_fragments))
            entry["x"] = merge_search_text(entry.get("x", ""), scene_links_text(scene_graph_links))
            if graph_fragments:
                tags = entry.setdefault("tags", [])
                if "graphFragment" not in tags:
                    tags.append("graphFragment")
            if scene_graph_links:
                tags = entry.setdefault("tags", [])
                if "sceneGraph" not in tags:
                    tags.append("sceneGraph")
            if not entry["x"]:
                entry.pop("x")
            index_entries.append(entry)

    def sim_duplicate_actor_from_key(key: str) -> str:
        raw = str(key or "")
        if m := re.match(r"^misc_sim_(?:gift|talk|rest|work)_([^_]+)", raw):
            return str(m.group(1) or "").lower()
        if m := re.match(r"^env_greetEnvTalk_([^_]+)", raw):
            return str(m.group(1) or "").lower()
        return ""

    def normalized_duplicate_line_texts(payload: dict) -> list[str]:
        out: list[str] = []
        for line in payload.get("lines") or []:
            text = " ".join(str(line.get("text") or "").split()).strip()
            if text:
                out.append(text)
        return out

    def mark_duplicate_sim_operator_entries() -> None:
        archive_text_by_actor: dict[str, str] = {}
        for entry in index_entries:
            if entry.get("d") != "table_charactertable":
                continue
            actor_ids = [str(actor_id or "").lower() for actor_id in (entry.get("c") or []) if actor_id]
            actor_id = actor_ids[0] if actor_ids else ""
            if not actor_id:
                continue
            conv_path = conv_dir / f"{entry.get('k')}.json"
            if not conv_path.exists():
                continue
            try:
                payload = json.loads(conv_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            line_texts = normalized_duplicate_line_texts(payload)
            if not line_texts:
                continue
            archive_text_by_actor[actor_id] = "\n".join([
                archive_text_by_actor.get(actor_id, ""),
                *line_texts,
            ]).strip()

        for entry in index_entries:
            key = str(entry.get("k") or "")
            if not (key.startswith("misc_sim_") or key.startswith("env_greetEnvTalk_")):
                continue
            actor_id = sim_duplicate_actor_from_key(key)
            archive_blob = archive_text_by_actor.get(actor_id, "")
            if not actor_id or not archive_blob:
                continue
            conv_path = conv_dir / f"{key}.json"
            if not conv_path.exists():
                continue
            try:
                payload = json.loads(conv_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            line_texts = normalized_duplicate_line_texts(payload)
            if line_texts and all(text in archive_blob for text in line_texts):
                entry["omitSimDuplicate"] = True

    mark_duplicate_sim_operator_entries()

    for mission in {entry["m"] for entry in index_entries if entry.get("m")}:
        mission_name(mission)
    if include_reference_in_story_index:
        write_texttable_collection_pages(collect_exported_texttable_row_ids())

    def merge_conv_hint_search_text(entry: dict) -> None:
        key = str(entry.get("k") or "")
        if not key:
            return
        conv_path = conv_dir / f"{key}.json"
        if not conv_path.exists():
            return
        try:
            payload = json.loads(conv_path.read_text(encoding="utf-8"))
        except Exception:
            return
        hint_text = line_haystack(payload.get("lines") or [], "hint")
        if hint_text:
            entry["x"] = merge_search_text(entry.get("x", ""), hint_text)
            if not entry["x"]:
                entry.pop("x", None)

    for entry in index_entries:
        merge_conv_hint_search_text(entry)

    def compact_story_source_link(link: dict) -> dict:
        source = str(link.get("source") or "")
        file_ref = str(link.get("file") or "")
        path_ref = str(link.get("path") or "")
        raw = str(link.get("raw") or "")
        context = link.get("context") if isinstance(link.get("context"), dict) else {}
        compact = {
            "source": source,
            "file": file_ref,
            "path": path_ref,
            "raw": raw,
            "kind": str(link.get("kind") or ""),
            "context": context,
            "_debug": {
                "source": {
                    "source": source,
                    "file": file_ref,
                    "path": path_ref,
                    "raw": raw,
                    "kind": str(link.get("kind") or ""),
                    "matchKind": str(link.get("matchKind") or ""),
                    "context": context,
                },
            },
        }
        for optional in ("sourceKey", "mission", "levelId", "scriptId", "templateGroup", "templateId"):
            if link.get(optional):
                compact[optional] = link[optional]
                compact["_debug"]["source"][optional] = link[optional]
        return compact

    def story_source_link_search_text(links: list[dict]) -> str:
        parts: list[str] = []
        for link in links:
            for field in ("raw", "source", "file", "path", "mission", "levelId", "scriptId", "templateId"):
                value = link.get(field)
                if value:
                    parts.append(str(value))
            context = link.get("context") if isinstance(link.get("context"), dict) else {}
            owner = context.get("owner") if isinstance(context.get("owner"), dict) else {}
            for value in owner.values():
                if value:
                    parts.append(str(value))
        return " ".join(parts)

    def story_source_link_index_summary(links: list[dict]) -> dict:
        source_counts = Counter(str(link.get("source") or "") for link in links)
        files = _unique_preserve(str(link.get("file") or "") for link in links if link.get("file"))
        return {
            "n": len(links),
            "sources": {
                key: source_counts[key]
                for key in sorted(source_counts)
                if key
            },
            "files": files[:5],
        }

    def story_source_link_report_rows(keys: set[str]) -> list[dict]:
        rows: list[dict] = []
        for key in sorted(keys):
            links = story_source_links.get(key) or []
            source_counts = Counter(str(link.get("source") or "") for link in links)
            rows.append({
                "key": key,
                "kind": str((links[0] if links else {}).get("kind") or ""),
                "references": len(links),
                "sources": {
                    source: source_counts[source]
                    for source in sorted(source_counts)
                    if source
                },
                "files": _unique_preserve(
                    str(link.get("file") or "")
                    for link in links
                    if link.get("file")
                )[:8],
            })
        return rows

    def render_story_source_link_report_md(report: dict) -> str:
        summary = report.get("summary") or {}
        lines = [
            f"# Story Source Links ({language_code})",
            "",
            "## Summary",
            "",
            f"- Source-link keys: `{summary.get('sourceLinkKeys', 0)}`",
            f"- Source references: `{summary.get('sourceReferences', 0)}`",
            f"- Attached WebUI keys: `{summary.get('attachedKeys', 0)}`",
            f"- Attached references: `{summary.get('attachedReferences', 0)}`",
            f"- Referenced but missing in WebUI: `{summary.get('referencedMissingKeys', 0)}`",
            f"- Story entries without source links: `{summary.get('storyEntriesWithoutSourceLinks', 0)}`",
            "",
            "## Missing Referenced Keys",
            "",
        ]
        for row in (report.get("referencedMissing") or [])[:80]:
            lines.append(f"- `{row.get('key')}` ({row.get('kind')}, `{row.get('references')}` refs)")
        if not report.get("referencedMissing"):
            lines.append("- None")
        lines.extend(["", "## Story Entries Without Source Links", ""])
        for row in (report.get("storyEntriesWithoutSourceLinks") or [])[:80]:
            label = row.get("mission") or ""
            lines.append(f"- `{row.get('key')}` ({row.get('kind')}{', ' + label if label else ''})")
        if not report.get("storyEntriesWithoutSourceLinks"):
            lines.append("- None")
        lines.append("")
        return "\n".join(lines)

    def attach_story_source_links_to_outputs() -> dict:
        if not story_source_links:
            return {}
        available_keys = {
            str(entry.get("k") or "")
            for entry in index_entries
            if entry.get("k")
        }
        def resolve_source_link_key(source_key: str) -> str:
            if source_key in available_keys:
                return source_key
            if source_key.startswith("dlg_"):
                misc_key = f"misc_{source_key}"
                if misc_key in available_keys:
                    return misc_key
                match = re.match(r"^(dlg_.+_\d+)d\d+$", source_key)
                if match and match.group(1) in available_keys:
                    return match.group(1)
            if source_key.startswith("cutscene_") and source_key.endswith("_start"):
                base_key = source_key.removesuffix("_start")
                if base_key in available_keys:
                    return base_key
            return ""

        resolved_source_links: dict[str, list[dict]] = defaultdict(list)
        unresolved_source_keys: set[str] = set()
        for source_key, links in story_source_links.items():
            resolved_key = resolve_source_link_key(source_key)
            if not resolved_key:
                unresolved_source_keys.add(source_key)
                continue
            for link in links:
                resolved_link = dict(link)
                if source_key != resolved_key:
                    resolved_link["sourceKey"] = source_key
                resolved_source_links[resolved_key].append(resolved_link)

        attached_keys: set[str] = set()
        attached_refs = 0
        for entry in index_entries:
            key = str(entry.get("k") or "")
            links = resolved_source_links.get(key) or []
            if not links:
                continue
            attached_keys.add(key)
            attached_refs += len(links)
            compact_links = [compact_story_source_link(link) for link in links[:12]]
            omitted = max(0, len(links) - len(compact_links))
            entry["src"] = story_source_link_index_summary(links)
            entry["x"] = merge_search_text(entry.get("x", ""), story_source_link_search_text(links))
            tags = entry.setdefault("tags", [])
            if "sourceLinked" not in tags:
                tags.append("sourceLinked")

            conv_path = conv_dir / f"{key}.json"
            if not conv_path.exists():
                continue
            try:
                payload = json.loads(conv_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            payload["sourceLinks"] = compact_links
            if omitted:
                payload["sourceLinksOmitted"] = omitted
            debug = payload.setdefault("_debug", {})
            debug["sourceLinks"] = {
                "source": {
                    "index": STORY_SOURCE_LINKS_PATH.relative_to(ROOT).as_posix(),
                    "key": key,
                    "count": len(links),
                    "shown": len(compact_links),
                    "omitted": omitted,
                },
            }
            with conv_path.open("w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

        referenced_missing = unresolved_source_keys
        source_link_candidate_kinds = set(MISSION_SCENE_ENTRY_KINDS) | {"env", "misc"}
        story_entries_without_links = [
            {
                "key": str(entry.get("k") or ""),
                "kind": str(entry.get("d") or ""),
                "mission": str(entry.get("m") or ""),
            }
            for entry in index_entries
            if entry.get("k")
            and entry.get("d") in source_link_candidate_kinds
            and entry.get("k") not in resolved_source_links
        ]
        report = {
            "generated": int(time.time()),
            "language": language_code,
            "sourceIndex": STORY_SOURCE_LINKS_PATH.relative_to(ROOT).as_posix(),
            "summary": {
                "sourceLinkKeys": len(story_source_links),
                "sourceReferences": sum(len(rows) for rows in story_source_links.values()),
                "attachedKeys": len(attached_keys),
                "attachedReferences": attached_refs,
                "referencedMissingKeys": len(referenced_missing),
                "storyEntriesWithoutSourceLinks": len(story_entries_without_links),
            },
            "referencedMissing": sorted(
                story_source_link_report_rows(referenced_missing),
                key=lambda row: (-int(row.get("references") or 0), row.get("key") or ""),
            )[:300],
            "storyEntriesWithoutSourceLinks": story_entries_without_links[:500],
        }
        report_json = REPORTS_DIR / f"story_source_links_{language_code}.json"
        report_md = REPORTS_DIR / f"story_source_links_{language_code}.md"
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        report_md.write_text(render_story_source_link_report_md(report), encoding="utf-8")
        report["report"] = {
            "json": report_json.relative_to(ROOT).as_posix(),
            "markdown": report_md.relative_to(ROOT).as_posix(),
        }
        return report

    story_source_link_report = attach_story_source_links_to_outputs()

    def compact_narrative_video_ref(ref: dict) -> dict:
        compact = {
            "name": str(ref.get("name") or ""),
            "rel": str(ref.get("rel") or ""),
            "source": str(ref.get("source") or ""),
            "format": str(ref.get("format") or ""),
            "size": int(ref.get("size") or 0),
            "stem": str(ref.get("stem") or ""),
            "baseStem": str(ref.get("baseStem") or ""),
            "kind": str(ref.get("kind") or ""),
            "_debug": {
                "source": {
                    "rel": str(ref.get("rel") or ""),
                    "source": str(ref.get("source") or ""),
                    "name": str(ref.get("name") or ""),
                    "kind": str(ref.get("kind") or ""),
                    "keyCandidates": list(ref.get("keyCandidates") or []),
                },
            },
        }
        if ref.get("gender"):
            compact["gender"] = str(ref["gender"])
            compact["_debug"]["source"]["gender"] = str(ref["gender"])
        if ref.get("resolvedKey"):
            compact["_debug"]["source"]["resolvedKey"] = str(ref["resolvedKey"])
        return compact

    def narrative_video_sort_key(ref: dict) -> tuple:
        source = str(ref.get("source") or "")
        fmt = str(ref.get("format") or "")
        source_rank = {
            "StreamingAssets-structured": 0,
            "Persistent-structured": 1,
            "raw_vfs": 2,
        }.get(source, 9)
        format_rank = {
            "mp4": 0,
            "webm": 1,
            "ogv": 2,
            "mov": 3,
            "m4v": 4,
            "avi": 5,
            "usm": 6,
        }.get(fmt, 9)
        gender = str(ref.get("gender") or "")
        gender_rank = {"": 0, "m": 1, "f": 2}.get(gender, 9)
        return (
            str(ref.get("baseStem") or ""),
            gender_rank,
            format_rank,
            source_rank,
            str(ref.get("rel") or ""),
        )

    def narrative_video_search_text(refs: list[dict]) -> str:
        parts: list[str] = []
        for ref in refs:
            for field in ("name", "rel", "source", "stem", "baseStem", "gender", "format", "kind"):
                value = ref.get(field)
                if value:
                    parts.append(str(value))
        return " ".join(parts)

    def narrative_video_index_summary(refs: list[dict]) -> dict:
        source_counts = Counter(str(ref.get("source") or "") for ref in refs)
        format_counts = Counter(str(ref.get("format") or "") for ref in refs)
        names = _unique_preserve(str(ref.get("name") or "") for ref in refs if ref.get("name"))
        return {
            "n": len(refs),
            "sources": {
                key: source_counts[key]
                for key in sorted(source_counts)
                if key
            },
            "formats": {
                key: format_counts[key]
                for key in sorted(format_counts)
                if key
            },
            "files": names[:5],
        }

    def render_narrative_video_report_md(report: dict) -> str:
        summary = report.get("summary") or {}
        lines = [
            f"# Narrative Videos ({language_code})",
            "",
            "## Summary",
            "",
            f"- Scanned video files: `{summary.get('scannedVideos', 0)}`",
            f"- Attached WebUI keys: `{summary.get('attachedKeys', 0)}`",
            f"- Attached video refs: `{summary.get('attachedVideos', 0)}`",
            f"- Unresolved video refs: `{summary.get('unresolvedVideos', 0)}`",
            "",
            "## Attached Keys",
            "",
        ]
        for row in (report.get("attached") or [])[:120]:
            names = ", ".join((row.get("files") or [])[:4])
            lines.append(f"- `{row.get('key')}` ({row.get('kind')}, `{row.get('videos')}` refs): {names}")
        if not report.get("attached"):
            lines.append("- None")
        lines.extend(["", "## Unresolved Videos", ""])
        for row in (report.get("unresolved") or [])[:120]:
            candidates = ", ".join(f"`{candidate}`" for candidate in (row.get("keyCandidates") or [])[:4])
            lines.append(f"- `{row.get('name')}` ({row.get('kind')}) -> {candidates}")
        if not report.get("unresolved"):
            lines.append("- None")
        lines.append("")
        return "\n".join(lines)

    def attach_narrative_videos_to_outputs() -> dict:
        if not narrative_video_assets:
            return {}
        available_keys = {
            str(entry.get("k") or "")
            for entry in index_entries
            if entry.get("k")
        }

        def resolve_video_key(ref: dict) -> str:
            for candidate in ref.get("keyCandidates") or []:
                candidate = str(candidate or "")
                if candidate in available_keys:
                    return candidate
                if candidate.startswith("dlg_"):
                    misc_key = f"misc_{candidate}"
                    if misc_key in available_keys:
                        return misc_key
                    match = re.match(r"^(dlg_.+_\d+)d\d+$", candidate)
                    if match and match.group(1) in available_keys:
                        return match.group(1)
            return ""

        resolved_videos: dict[str, list[dict]] = defaultdict(list)
        unresolved_videos: list[dict] = []
        for ref in narrative_video_assets:
            resolved_key = resolve_video_key(ref)
            if not resolved_key:
                unresolved_videos.append(ref)
                continue
            resolved_ref = dict(ref)
            resolved_ref["resolvedKey"] = resolved_key
            resolved_videos[resolved_key].append(resolved_ref)

        attached_rows: list[dict] = []
        attached_refs = 0
        for entry in index_entries:
            key = str(entry.get("k") or "")
            refs = sorted(resolved_videos.get(key) or [], key=narrative_video_sort_key)
            if not refs:
                continue
            attached_refs += len(refs)
            compact_refs = [compact_narrative_video_ref(ref) for ref in refs[:16]]
            omitted = max(0, len(refs) - len(compact_refs))
            entry["vid"] = narrative_video_index_summary(refs)
            entry["x"] = merge_search_text(entry.get("x", ""), narrative_video_search_text(refs))
            tags = entry.setdefault("tags", [])
            if "narrativeVideo" not in tags:
                tags.append("narrativeVideo")

            conv_path = conv_dir / f"{key}.json"
            if conv_path.exists():
                try:
                    payload = json.loads(conv_path.read_text(encoding="utf-8"))
                except Exception:
                    payload = None
                if isinstance(payload, dict):
                    payload["narrativeVideos"] = compact_refs
                    if omitted:
                        payload["narrativeVideosOmitted"] = omitted
                    if isinstance(payload.get("cutscene"), dict):
                        payload["cutscene"]["videoRefs"] = compact_refs
                    debug = payload.setdefault("_debug", {})
                    debug["narrativeVideos"] = {
                        "source": {
                            "key": key,
                            "count": len(refs),
                            "shown": len(compact_refs),
                            "omitted": omitted,
                        },
                    }
                    with conv_path.open("w", encoding="utf-8") as f:
                        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

            source_counts = Counter(str(ref.get("source") or "") for ref in refs)
            attached_rows.append({
                "key": key,
                "kind": str(entry.get("d") or ""),
                "mission": str(entry.get("m") or ""),
                "videos": len(refs),
                "sources": {
                    source: source_counts[source]
                    for source in sorted(source_counts)
                    if source
                },
                "files": _unique_preserve(
                    str(ref.get("name") or "")
                    for ref in refs
                    if ref.get("name")
                )[:12],
            })

        unresolved_rows = [
            {
                "name": str(ref.get("name") or ""),
                "kind": str(ref.get("kind") or ""),
                "rel": str(ref.get("rel") or ""),
                "keyCandidates": list(ref.get("keyCandidates") or []),
            }
            for ref in unresolved_videos
        ]
        report = {
            "generated": int(time.time()),
            "language": language_code,
            "summary": {
                "scannedVideos": len(narrative_video_assets),
                "attachedKeys": len(attached_rows),
                "attachedVideos": attached_refs,
                "unresolvedVideos": len(unresolved_videos),
                "cutsceneVideoFiles": sum(1 for ref in narrative_video_assets if ref.get("kind") == "cutscene"),
                "remotecommVideoFiles": sum(1 for ref in narrative_video_assets if ref.get("kind") == "remotecomm"),
            },
            "attached": sorted(
                attached_rows,
                key=lambda row: (-int(row.get("videos") or 0), row.get("key") or ""),
            )[:500],
            "unresolved": unresolved_rows[:500],
        }
        report_json = REPORTS_DIR / f"narrative_videos_{language_code}.json"
        report_md = REPORTS_DIR / f"narrative_videos_{language_code}.md"
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        report_md.write_text(render_narrative_video_report_md(report), encoding="utf-8")
        report["report"] = {
            "json": report_json.relative_to(ROOT).as_posix(),
            "markdown": report_md.relative_to(ROOT).as_posix(),
        }
        return report

    narrative_video_report = attach_narrative_videos_to_outputs()

    def normalize_index_entry_defaults(entry: dict) -> None:
        type_key = str(entry.get("t") or "").strip()
        if not type_key or type_key in {"?", "x"}:
            entry["t"] = "other"

        tags = []
        for raw_tag in entry.get("tags") or []:
            tag = str(raw_tag or "").strip()
            if tag and tag not in tags:
                tags.append(tag)
        entry["tags"] = tags or ["other"]

    for entry in index_entries:
        normalize_index_entry_defaults(entry)

    # Sort index by type, act, mission, scene
    index_entries.sort(key=lambda e: (e["d"], e["t"], e["a"], e["m"], e["s"]))
    mission_names = {
        mission: name
        for mission in sorted({e["m"] for e in index_entries if e.get("m")})
        if (name := mission_name(mission))
    }
    present_missions = {e["m"] for e in index_entries if e.get("m")}
    for mission, name in sorted(extra_mission_names.items()):
        if mission in present_missions and name:
            mission_names.setdefault(mission, name)

    def env_entry_search_text(env_entry: dict) -> str:
        parts: list[str] = []
        if env_entry.get("id"):
            parts.append(str(env_entry["id"]))
        if env_entry.get("lines"):
            parts.append(line_haystack(env_entry["lines"], "text", "actor", "aid", "emoji"))
        npc = env_entry.get("npc") or {}
        for field in ("npcId", "name", "title", "dialogSelector"):
            value = npc.get(field)
            if value:
                parts.append(str(value))
        return " ".join(part for part in parts if part)

    index_entry_by_key = {
        entry["k"]: entry
        for entry in index_entries
        if entry.get("k")
    }
    scene_bindings_by_mission: dict[str, dict[str, dict]] = defaultdict(dict)
    for mission, refs in mission_level_refs.items():
        scene_targets = {
            entry["k"]
            for entry in index_entries
            if entry.get("m") == mission and entry.get("d") in SCENE_BINDING_TARGET_KINDS
        }
        if not scene_targets:
            continue

        processed_chain_levels: set[str] = set()
        for ref in refs:
            level_id = ref.get("levelId") or ""
            if not level_id:
                continue

            leveldata_path = ROOT / ref["file"]
            named_entries = _load_leveldata_named_entries(leveldata_path)
            if any(LT_BINDING_RE.match(entry["text"]) for entry in named_entries):
                levelscript_info = _load_levelscript_binding_data(level_id)
                binding_groups = _build_level_binding_groups(
                    named_entries,
                    levelscript_info["uidPayloads"],
                    dialog_scene_out_key,
                    mission,
                )
                for group in binding_groups:
                    group_scene_keys = {
                        payload["sceneKey"]
                        for row in group["rows"]
                        for payload in row.get("payloads") or []
                        if payload.get("sceneKey")
                    }
                    for scene_key in sorted(group_scene_keys & scene_targets):
                        scene_entry = scene_bindings_by_mission[mission].setdefault(
                            scene_key,
                            {"groups": [], "chains": []},
                        )
                        scene_entry["groups"].append({
                            "label": group["label"],
                            "levelId": level_id,
                            "hostType": ref.get("hostType") or "",
                            "levelKind": ref.get("kind") or "",
                            "levelDataFile": ref["file"],
                            "rows": group["rows"],
                            "_debug": {
                                "source": {
                                    "file": ref["file"],
                                    "levelId": level_id,
                                    "hostType": ref.get("hostType") or "",
                                    "kind": ref.get("kind") or "",
                                },
                            },
                        })

            if level_id in processed_chain_levels:
                continue
            processed_chain_levels.add(level_id)
            level_chain_map = _build_levelscript_scene_chain_map(level_id, dialog_scene_out_key, mission)
            for scene_key, chains in level_chain_map.items():
                if scene_key not in scene_targets:
                    continue
                scene_entry = scene_bindings_by_mission[mission].setdefault(
                    scene_key,
                    {"groups": [], "chains": []},
                )
                scene_entry["chains"].extend(chains)

    for mission, scene_map in scene_bindings_by_mission.items():
        for scene_key, scene_entry in scene_map.items():
            scene_entry["groups"].sort(
                key=lambda group: (
                    group.get("levelId") or "",
                    group.get("label") or "",
                    group.get("levelDataFile") or "",
                )
            )
            scene_entry["chains"].sort(
                key=lambda chain: (
                    chain.get("levelId") or "",
                    chain.get("file") or "",
                    (chain.get("steps") or [{}])[0].get("localId", 0),
                )
            )

            index_entry = index_entry_by_key.get(scene_key)
            if not index_entry:
                continue
            index_entry["x"] = merge_search_text(
                index_entry.get("x", ""),
                _scene_binding_search_text(scene_entry),
            )
            tags = index_entry.setdefault("tags", [])
            if "levelBinding" not in tags:
                tags.append("levelBinding")

    scene_env_talks_by_mission: dict[str, dict[str, list[dict]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for mission, env_entries in story_env_entries_by_mission.items():
        scene_targets = {
            entry["k"]
            for entry in index_entries
            if entry.get("m") == mission and entry.get("d") in ("dlg", "misc")
        }
        if not scene_targets:
            continue

        scene_tracking: dict[str, dict[str, set[str]]] = defaultdict(
            lambda: {"levels": set(), "proxies": set()}
        )
        if flow := load_mission_flow(mission):
            for quest in flow.get("quests") or []:
                quest_targets: list[str] = []
                for dialog_id in quest.get("dialogs") or []:
                    out_key = dialog_scene_out_key(dialog_id)
                    if out_key and out_key in scene_targets and out_key not in quest_targets:
                        quest_targets.append(out_key)
                if not quest_targets:
                    continue

                quest_levels = {
                    hint["scene"]
                    for hint in (quest.get("tracking") or [])
                    if hint.get("scene")
                }
                quest_proxies = {
                    hint["npcProxyId"]
                    for hint in (quest.get("tracking") or [])
                    if hint.get("npcProxyId")
                }
                for out_key in quest_targets:
                    scene_tracking[out_key]["levels"].update(quest_levels)
                    scene_tracking[out_key]["proxies"].update(quest_proxies)

        only_scene_target = next(iter(scene_targets)) if len(scene_targets) == 1 else ""

        for env_entry in env_entries:
            hints = env_entry.pop("_attachHints", None) or {}
            env_levels = set(hints.get("levels") or [])
            env_proxies = set(hints.get("proxies") or [])

            proxy_hits = {
                out_key
                for out_key, tracking in scene_tracking.items()
                if env_proxies and env_proxies & tracking["proxies"]
            }
            level_hits = {
                out_key
                for out_key, tracking in scene_tracking.items()
                if env_levels and env_levels & tracking["levels"]
            }

            target_key = ""
            binding_source: dict = {}
            if len(proxy_hits) == 1:
                target_key = next(iter(proxy_hits))
                binding_source = {
                    "mode": "npcProxyId",
                    "targetKey": target_key,
                    "matchedProxyIds": sorted(
                        env_proxies & scene_tracking[target_key]["proxies"]
                    ),
                    "candidateSceneKeys": sorted(proxy_hits),
                }
            elif not proxy_hits and len(level_hits) == 1:
                target_key = next(iter(level_hits))
                binding_source = {
                    "mode": "sceneLevel",
                    "targetKey": target_key,
                    "matchedLevels": sorted(
                        env_levels & scene_tracking[target_key]["levels"]
                    ),
                    "candidateSceneKeys": sorted(level_hits),
                }
            elif not proxy_hits and not level_hits and only_scene_target:
                target_key = only_scene_target
                binding_source = {
                    "mode": "onlySceneInMission",
                    "targetKey": target_key,
                }

            if not target_key:
                continue

            env_entry["_debug"]["sceneBinding"] = {"source": binding_source}
            scene_env_talks_by_mission[mission][target_key].append(env_entry)

            if env_index_entry := index_entry_by_key.get(env_entry.get("key") or ""):
                env_index_entry["attachTo"] = target_key

            index_entry = index_entry_by_key.get(target_key)
            if not index_entry:
                continue
            index_entry["x"] = merge_search_text(
                index_entry.get("x", ""),
                env_entry_search_text(env_entry),
            )
            tags = index_entry.setdefault("tags", [])
            if "envTalk" not in tags:
                tags.append("envTalk")

    mission_extras_payload: dict[str, dict] = {}
    for mission in sorted(
        set(scene_env_talks_by_mission)
        | set(scene_bindings_by_mission)
        | set(mission_note_by_mission)
        | set(mission_level_refs)
    ):
        extra: dict[str, list[dict]] = {}
        if mission in mission_note_by_mission:
            extra["notes"] = mission_note_by_mission[mission]
        if mission in mission_level_refs:
            extra["levelRefs"] = mission_level_refs[mission]
        if mission in scene_bindings_by_mission:
            extra["sceneBindings"] = {
                out_key: scene_bindings_by_mission[mission][out_key]
                for out_key in sorted(scene_bindings_by_mission[mission])
            }
        if mission in scene_env_talks_by_mission:
            extra["sceneEnvTalk"] = {
                out_key: scene_env_talks_by_mission[mission][out_key]
                for out_key in sorted(scene_env_talks_by_mission[mission])
            }
        mission_extras_payload[mission] = extra

    # Mission flow graphs from MissionRuntimeAsset. Story-gated dialog
    # ordering + choice-branches live here; pure-env ambient scenes do not.
    scene_keys_by_mission: dict[str, set[str]] = defaultdict(set)
    for entry in index_entries:
        if entry.get("d") in MISSION_SCENE_ENTRY_KINDS:
            scene_keys_by_mission[entry["m"]].add(entry["k"])

    def resolve_scene_ref_out_key(raw_ref: str, available_scene_keys: set[str]) -> str:
        if not raw_ref:
            return ""
        for candidate in _unique_preserve([
            str(raw_ref or "").strip(),
            *_scene_ref_alias_candidates(raw_ref),
        ]):
            if not candidate:
                continue
            if candidate in available_scene_keys:
                return candidate
            if out_key := dialog_scene_out_key(candidate):
                if out_key in available_scene_keys:
                    return out_key
            if canonical_cutscene := _canonical_cutscene_key(candidate):
                if canonical_cutscene in available_scene_keys:
                    return canonical_cutscene
        return ""

    def build_mission_map_pins(flow: dict | None) -> list[dict]:
        if not flow:
            return []
        merged: dict[tuple, dict] = {}
        for quest in flow.get("quests") or []:
            for pin in quest.get("pins") or []:
                position = pin.get("position") or {}
                key = (
                    pin.get("scene") or "",
                    pin.get("sourceType") or "",
                    pin.get("trackingType") or "",
                    pin.get("missionAreaId") or "",
                    pin.get("npcProxyId") or "",
                    round(float(position.get("x", 0.0)), 3),
                    round(float(position.get("y", 0.0)), 3),
                    round(float(position.get("z", 0.0)), 3),
                )
                row = merged.get(key)
                if row is None:
                    row = {
                        "scene": pin.get("scene") or "",
                        "sourceType": pin.get("sourceType") or "",
                        "trackingType": pin.get("trackingType") or "",
                        "position": {
                            "x": float(position.get("x", 0.0)),
                            "y": float(position.get("y", 0.0)),
                            "z": float(position.get("z", 0.0)),
                        },
                        "questIds": [],
                        "flowIndices": [],
                    }
                    if pin.get("missionAreaId"):
                        row["missionAreaId"] = pin["missionAreaId"]
                    if pin.get("npcProxyId"):
                        row["npcProxyId"] = pin["npcProxyId"]
                    if pin.get("radius") is not None:
                        row["radius"] = pin["radius"]
                    if pin.get("routePointCount") is not None:
                        row["routePointCount"] = pin["routePointCount"]
                    merged[key] = row
                quest_id = quest.get("id") or ""
                if quest_id and quest_id not in row["questIds"]:
                    row["questIds"].append(quest_id)
                flow_index = quest.get("flowIndex")
                if flow_index is not None and flow_index not in row["flowIndices"]:
                    row["flowIndices"].append(flow_index)
        return sorted(
            merged.values(),
            key=lambda row: (
                min(row.get("flowIndices") or [10**9]),
                row.get("scene") or "",
                row.get("sourceType") or "",
                row["position"]["x"],
                row["position"]["z"],
            ),
        )

    def build_mission_scene_pins(
        flow: dict | None,
        available_scene_keys: set[str],
    ) -> dict[str, list[dict]]:
        if not flow or not available_scene_keys:
            return {}

        scene_rows: dict[str, dict[tuple, dict]] = defaultdict(dict)
        for quest in flow.get("quests") or []:
            # Prefer stronger authored/runtime scene refs for spatial pinning.
            # Radios are only used when a quest has no dialog/cutscene/remotecomm target.
            primary_scene_refs = _unique_preserve([
                *(
                    resolved
                    for dialog_id in (quest.get("dialogs") or [])
                    if (resolved := resolve_scene_ref_out_key(dialog_id, available_scene_keys))
                ),
                *(
                    resolved
                    for cutscene_id in (quest.get("cutscenes") or [])
                    if (resolved := resolve_scene_ref_out_key(cutscene_id, available_scene_keys))
                ),
                *(
                    resolved
                    for remote_id in (quest.get("remotecomms") or [])
                    if (resolved := resolve_scene_ref_out_key(remote_id, available_scene_keys))
                ),
            ])
            radio_scene_refs = _unique_preserve([
                resolved
                for radio_id in (quest.get("radios") or [])
                if (resolved := resolve_scene_ref_out_key(radio_id, available_scene_keys))
            ])
            scene_refs = primary_scene_refs or radio_scene_refs
            if len(scene_refs) != 1:
                continue
            scene_key = scene_refs[0]

            for pin in quest.get("pins") or []:
                position = pin.get("position") or {}
                key = (
                    pin.get("scene") or "",
                    pin.get("sourceType") or "",
                    pin.get("trackingType") or "",
                    pin.get("missionAreaId") or "",
                    pin.get("npcProxyId") or "",
                    round(float(position.get("x", 0.0)), 3),
                    round(float(position.get("y", 0.0)), 3),
                    round(float(position.get("z", 0.0)), 3),
                )
                row = scene_rows[scene_key].get(key)
                if row is None:
                    row = {
                        "scene": pin.get("scene") or "",
                        "sourceType": pin.get("sourceType") or "",
                        "trackingType": pin.get("trackingType") or "",
                        "position": {
                            "x": float(position.get("x", 0.0)),
                            "y": float(position.get("y", 0.0)),
                            "z": float(position.get("z", 0.0)),
                        },
                        "questIds": [],
                        "flowIndices": [],
                    }
                    if pin.get("missionAreaId"):
                        row["missionAreaId"] = pin["missionAreaId"]
                    if pin.get("npcProxyId"):
                        row["npcProxyId"] = pin["npcProxyId"]
                    if pin.get("radius") is not None:
                        row["radius"] = pin["radius"]
                    if pin.get("routePointCount") is not None:
                        row["routePointCount"] = pin["routePointCount"]
                    scene_rows[scene_key][key] = row
                quest_id = quest.get("id") or ""
                if quest_id and quest_id not in row["questIds"]:
                    row["questIds"].append(quest_id)
                flow_index = quest.get("flowIndex")
                if flow_index is not None and flow_index not in row["flowIndices"]:
                    row["flowIndices"].append(flow_index)

        return {
            scene_key: sorted(
                rows.values(),
                key=lambda row: (
                    min(row.get("flowIndices") or [10**9]),
                    row.get("scene") or "",
                    row.get("sourceType") or "",
                    row["position"]["x"],
                    row["position"]["z"],
                ),
            )
            for scene_key, rows in sorted(scene_rows.items())
            if rows
        }

    def build_mission_scene_graph(mission: str, flow: dict | None) -> dict | None:
        available = scene_keys_by_mission.get(mission, set())
        ui_nodes: set[str] = set()
        chain_nodes: set[str] = set()
        chain_sequences: list[dict] = []
        scene_chain_sequences: list[dict] = []
        if flow:
            for quest in flow.get("quests") or []:
                for hint in quest.get("tracking") or []:
                    jump_id = hint.get("jumpId") or ""
                    if jump_id:
                        ui_nodes.add(f"ui:{jump_id}")
        seen_chain_signatures: set[tuple[str, tuple[str, ...]]] = set()
        for scene_entry in (scene_bindings_by_mission.get(mission) or {}).values():
            for chain in scene_entry.get("chains") or []:
                sequence: list[str] = []
                for step in chain.get("steps") or []:
                    for payload in step.get("payloads") or []:
                        raw_text = str(payload.get("text") or "")
                        node_key = str(
                            resolve_scene_ref_out_key(raw_text, available)
                            or payload.get("nodeKey")
                            or _scene_graph_runtime_payload_key(
                                raw_text,
                                mission,
                                dialog_scene_out_key,
                            )
                        )
                        if not node_key:
                            continue
                        if not sequence or sequence[-1] != node_key:
                            sequence.append(node_key)
                if not sequence:
                    continue
                signature = (chain.get("file") or "", tuple(sequence))
                if signature in seen_chain_signatures:
                    continue
                seen_chain_signatures.add(signature)
                chain_nodes.update(sequence)
                scene_sequence = _compact_scene_graph_sequence(sequence, available)
                if scene_sequence:
                    scene_chain_sequences.append({
                        "file": chain.get("file") or "",
                        "levelId": chain.get("levelId") or "",
                        "sequence": scene_sequence,
                    })
                if len(sequence) < 2:
                    continue
                chain_sequences.append({
                    "file": chain.get("file") or "",
                    "levelId": chain.get("levelId") or "",
                    "sequence": sequence,
                })
        all_nodes = set(available) | ui_nodes | chain_nodes
        if not all_nodes:
            return None

        mission_entries = [entry for entry in index_entries if entry.get("m") == mission]
        order_map = infer_mission_dialog_order(
            mission,
            mission_entries,
            flow,
            mission_level_refs.get(mission),
        )
        node_entries = sorted(
            (entry for entry in mission_entries if entry.get("k") in available),
            key=lambda entry: (
                order_map.get(entry["k"], 10**9),
                entry.get("s", 10**9),
                entry.get("k") or "",
            ),
        )
        mission_entry_by_key = {
            entry["k"]: entry
            for entry in node_entries
            if entry.get("k")
        }

        edges_by_key: dict[tuple[str, str, str], dict] = {}

        def ensure_edge(src: str, dst: str, kind: str) -> dict | None:
            if not src or not dst or src == dst:
                return None
            if src not in all_nodes or dst not in all_nodes:
                return None
            edge = edges_by_key.get((src, dst, kind))
            if edge is None:
                edge = {"from": src, "to": dst, "kind": kind}
                edges_by_key[(src, dst, kind)] = edge
            return edge

        if flow:
            quest_by_id = {
                quest.get("id") or "": quest
                for quest in flow.get("quests") or []
                if quest.get("id")
            }
            quest_scene_refs: dict[str, list[str]] = {}
            quest_scene_meta: dict[str, dict] = defaultdict(lambda: {
                "questIds": [],
                "rootQuestIds": [],
                "flowIndices": [],
            })

            def gather_upstream_scene_refs(quest_id: str, seen: set[str] | None = None) -> list[str]:
                if not quest_id:
                    return []
                if seen is None:
                    seen = set()
                if quest_id in seen:
                    return []
                seen.add(quest_id)
                scene_refs = quest_scene_refs.get(quest_id, [])
                if scene_refs:
                    return scene_refs
                out: list[str] = []
                for prev_id in (quest_by_id.get(quest_id) or {}).get("prev") or []:
                    for scene_ref in gather_upstream_scene_refs(prev_id, seen):
                        if scene_ref not in out:
                            out.append(scene_ref)
                return out

            script_scene_ref_cache: dict[tuple[str, str], list[str]] = {}

            def normalized_script_ids(values) -> list[str]:
                out: list[str] = []
                for value in values or []:
                    script_id = value
                    if isinstance(value, dict):
                        script_id = value.get("scriptId") or value.get("value")
                        if isinstance(script_id, dict):
                            script_id = script_id.get("scriptId")
                    if script_id is None:
                        continue
                    script_id_text = str(script_id)
                    if script_id_text and script_id_text not in out:
                        out.append(script_id_text)
                return out

            def levelscript_scene_refs_for_script(level_id: str, script_id) -> list[str]:
                if not level_id or script_id is None:
                    return []
                script_stem = str(script_id)
                cache_key = (level_id, script_stem)
                if cache_key in script_scene_ref_cache:
                    return script_scene_ref_cache[cache_key]
                hits: list[tuple[int, int, str]] = []
                for file_info in _load_levelscript_binding_data(level_id).get("files") or []:
                    if Path(file_info.get("file") or "").stem != script_stem:
                        continue
                    for record in file_info.get("records") or []:
                        record_start = int(record.get("start") or 0)
                        for hit in record.get("strings") or []:
                            scene_ref = resolve_scene_ref_out_key(hit.get("text") or "", available)
                            if not scene_ref:
                                continue
                            hits.append((
                                record_start,
                                int(hit.get("offset") or record_start),
                                scene_ref,
                            ))
                refs = _unique_preserve([scene_ref for _, __, scene_ref in sorted(hits)])
                script_scene_ref_cache[cache_key] = refs
                return refs

            def quest_condition_script_scene_refs(quest: dict) -> list[str]:
                refs: list[str] = []
                default_scene_ids = list(quest.get("scenes") or [])
                for anchor in quest.get("objectiveAnchors") or []:
                    anchor_scene_ids = list(anchor.get("sceneIds") or default_scene_ids)
                    for script_id in normalized_script_ids(anchor.get("scriptIds")):
                        for scene_id in anchor_scene_ids:
                            for scene_ref in levelscript_scene_refs_for_script(scene_id, script_id):
                                if scene_ref not in refs:
                                    refs.append(scene_ref)
                    for leaf in anchor.get("conditionLeaves") or []:
                        leaf_scene_ids = list(leaf.get("sceneIds") or anchor_scene_ids)
                        for script_id in normalized_script_ids(leaf.get("scriptIds")):
                            for scene_id in leaf_scene_ids:
                                for scene_ref in levelscript_scene_refs_for_script(scene_id, script_id):
                                    if scene_ref not in refs:
                                        refs.append(scene_ref)
                return refs

            for quest in flow.get("quests") or []:
                scene_refs = _unique_preserve([
                    *quest_condition_script_scene_refs(quest),
                    *(dialog_id for dialog_id in (quest.get("dialogs") or []) if dialog_id in available),
                    *(cutscene_id for cutscene_id in (quest.get("cutscenes") or []) if cutscene_id in available),
                    *(remote_id for remote_id in (quest.get("remotecomms") or []) if remote_id in available),
                    *(radio_id for radio_id in (quest.get("radios") or []) if radio_id in available),
                ])
                quest_id = quest.get("id") or ""
                flow_index = quest.get("flowIndex", 0)
                if scene_refs:
                    quest_scene_refs[quest_id] = scene_refs
                    first_scene = scene_refs[0]
                    meta = quest_scene_meta[first_scene]
                    if quest_id and quest_id not in meta["questIds"]:
                        meta["questIds"].append(quest_id)
                    if isinstance(flow_index, int | float) and flow_index not in meta["flowIndices"]:
                        meta["flowIndices"].append(int(flow_index))
                    if quest_id and not (quest.get("prev") or []) and quest_id not in meta["rootQuestIds"]:
                        meta["rootQuestIds"].append(quest_id)
                for src, dst in zip(scene_refs, scene_refs[1:]):
                    if edge := ensure_edge(src, dst, "questSequence"):
                        refs = edge.setdefault("questIds", [])
                        if quest_id and quest_id not in refs:
                            refs.append(quest_id)
                jump_nodes = [
                    f"ui:{hint.get('jumpId')}"
                    for hint in (quest.get("tracking") or [])
                    if hint.get("jumpId")
                ]
                sources = scene_refs[:]
                if not sources:
                    for prev_id in quest.get("prev") or []:
                        for scene_ref in gather_upstream_scene_refs(prev_id):
                            if scene_ref not in sources:
                                sources.append(scene_ref)
                for jump_node in jump_nodes:
                    for src in _unique_preserve(sources):
                        if edge := ensure_edge(src, jump_node, "uiJump"):
                            refs = edge.setdefault("questIds", [])
                            if quest_id and quest_id not in refs:
                                refs.append(quest_id)
            for quest in flow.get("quests") or []:
                quest_id = quest.get("id") or ""
                scene_refs = quest_scene_refs.get(quest_id, [])
                if not scene_refs:
                    continue
                first_scene = scene_refs[0]
                for prev_id in quest.get("prev") or []:
                    for prev_scene in gather_upstream_scene_refs(prev_id):
                        if edge := ensure_edge(prev_scene, first_scene, "questPrev"):
                            refs = edge.setdefault("questIds", [])
                            if quest_id and quest_id not in refs:
                                refs.append(quest_id)
                            if prev_id and prev_id not in refs:
                                refs.append(prev_id)
                fail_scene_refs = _unique_preserve([
                    resolved
                    for raw_ref in (quest.get("failStoryRefs") or [])
                    if (resolved := resolve_scene_ref_out_key(raw_ref, available))
                ])
                guard_sources = scene_refs[-1:] or _unique_preserve([
                    upstream
                    for prev_id in quest.get("prev") or []
                    for upstream in gather_upstream_scene_refs(prev_id)
                ])
                for guard_src in guard_sources:
                    for fail_scene in fail_scene_refs:
                        if edge := ensure_edge(guard_src, fail_scene, "questFailGuard"):
                            refs = edge.setdefault("questIds", [])
                            if quest_id and quest_id not in refs:
                                refs.append(quest_id)
        else:
            quest_scene_meta = defaultdict(lambda: {
                "questIds": [],
                "rootQuestIds": [],
                "flowIndices": [],
            })

        for scene_key, links in scene_graph_links_by_key.items():
            if scene_key not in available:
                continue
            for link in links:
                source_key = link.get("sourceKey") or ""
                for opt in link.get("options") or []:
                    option_id = opt.get("optionId") or ""
                    if first_scene := opt.get("firstSceneKey"):
                        if first_scene != scene_key:
                            if edge := ensure_edge(scene_key, first_scene, "authoredDirect"):
                                if option_id:
                                    edge.setdefault("optionIds", [])
                                    if option_id not in edge["optionIds"]:
                                        edge["optionIds"].append(option_id)
                                if source_key:
                                    edge.setdefault("sourceKeys", [])
                                    if source_key not in edge["sourceKeys"]:
                                        edge["sourceKeys"].append(source_key)
                    for submenu_scene in opt.get("submenuSceneKeys") or []:
                        if submenu_scene == scene_key or submenu_scene == opt.get("firstSceneKey"):
                            continue
                        if edge := ensure_edge(scene_key, submenu_scene, "authoredMenu"):
                            if option_id:
                                edge.setdefault("optionIds", [])
                                if option_id not in edge["optionIds"]:
                                    edge["optionIds"].append(option_id)
                            if source_key:
                                edge.setdefault("sourceKeys", [])
                                if source_key not in edge["sourceKeys"]:
                                    edge["sourceKeys"].append(source_key)

        for chain in chain_sequences:
            sequence = chain.get("sequence") or []
            for src, dst in zip(sequence, sequence[1:]):
                if edge := ensure_edge(src, dst, "levelscriptChain"):
                    file_ref = chain.get("file") or ""
                    if file_ref:
                        refs = edge.setdefault("sourceFiles", [])
                        if file_ref not in refs:
                            refs.append(file_ref)
                    level_id = chain.get("levelId") or ""
                    if level_id:
                        refs = edge.setdefault("levelIds", [])
                        if level_id not in refs:
                            refs.append(level_id)

        chain_start_meta: dict[str, dict] = defaultdict(lambda: {
            "sourceFiles": [],
            "levelIds": [],
            "positions": [],
        })
        for chain in scene_chain_sequences:
            sequence = chain.get("sequence") or []
            if sequence:
                first_scene = sequence[0]
                meta = chain_start_meta[first_scene]
                file_ref = chain.get("file") or ""
                if file_ref and file_ref not in meta["sourceFiles"]:
                    meta["sourceFiles"].append(file_ref)
                level_id = chain.get("levelId") or ""
                if level_id and level_id not in meta["levelIds"]:
                    meta["levelIds"].append(level_id)
                meta["positions"].append(0)
            for pos, (src, dst) in enumerate(zip(sequence, sequence[1:])):
                if edge := ensure_edge(src, dst, "levelscriptSceneChain"):
                    file_ref = chain.get("file") or ""
                    if file_ref:
                        refs = edge.setdefault("sourceFiles", [])
                        if file_ref not in refs:
                            refs.append(file_ref)
                    level_id = chain.get("levelId") or ""
                    if level_id:
                        refs = edge.setdefault("levelIds", [])
                        if level_id not in refs:
                            refs.append(level_id)
                    edge.setdefault("positions", [])
                    if pos not in edge["positions"]:
                        edge["positions"].append(pos)

        graph_order_map = _refine_scene_graph_order(
            all_nodes,
            list(edges_by_key.values()),
            order_map,
            available,
        )
        chained_node_keys: set[str] = {
            k
            for edge in edges_by_key.values()
            for k in (edge.get("from") or "", edge.get("to") or "")
            if k
        }
        nodes = [
            {
                "key": node_key,
                "kind": (
                    (mission_entry_by_key.get(node_key) or {}).get("d")
                    or _scene_graph_node_kind(node_key, available)
                ),
                "order": graph_order_map.get(node_key, -1),
                **({"orderConfirmed": False} if node_key not in chained_node_keys else {}),
            }
            for node_key in sorted(
                all_nodes,
                key=lambda key: (
                    graph_order_map.get(key, 10**9),
                    order_map.get(key, 10**9),
                    _scene_graph_node_kind(key, available),
                    key,
                ),
            )
        ]
        edges = sorted(
            edges_by_key.values(),
            key=lambda edge: (
                graph_order_map.get(edge["from"], 10**9),
                graph_order_map.get(edge["to"], 10**9),
                edge.get("kind") or "",
                edge["from"],
                edge["to"],
            ),
        )
        scene_entry = _detect_scene_graph_entries(
            nodes,
            edges,
            dict(quest_scene_meta),
            dict(chain_start_meta),
            order_map,
            graph_order_map,
            available,
        )
        payload = {"nodes": nodes, "edges": edges}
        if scene_entry:
            payload.update(scene_entry)
        return payload

    def build_mission_timeline_recovery_report(
        scene_graphs: dict[str, dict],
    ) -> dict:
        timeline_index, timeline_meta = load_mission_timeline_index(
            timeline_recovery_order_out(EXPORT_ROOT)
        )
        recovered: list[dict] = []
        files = mission_timeline_files(MRA_DIR, set()) if MRA_DIR.is_dir() else []
        for path in files:
            mission_id = path.stem
            recovered.append(
                recover_source_mission_timeline(
                    path,
                    timeline_index,
                    None,
                    source_backed_scene_edges_from_scene_graph(
                        scene_graphs.get(mission_id)
                    ),
                )
            )
        return {
            "evidencePolicy": MISSION_TIMELINE_EVIDENCE_POLICY,
            "summary": summarize_mission_timeline_recovery(
                recovered,
                timeline_meta,
                generated_by="scripts/webui/build_story.py",
            ),
            "missions": recovered,
        }

    mission_flows_payload: dict[str, dict] = {}
    mission_scene_graphs: dict[str, dict] = {}
    for mission in sorted({e["m"] for e in index_entries if e.get("m")}):
        flow = load_mission_flow(mission)
        scene_graph = build_mission_scene_graph(mission, flow)
        if not flow and not scene_graph:
            continue
        payload = {"quests": (flow or {}).get("quests") or []}
        if flow:
            referenced: set[str] = set()
            for q in flow["quests"]:
                referenced.update(q.get("dialogs") or [])
                referenced.update(q.get("cutscenes") or [])
                referenced.update(q.get("remotecomms") or [])
                referenced.update(q.get("radios") or [])
            available = scene_keys_by_mission.get(mission, set())
            unlinked = sorted(available - referenced)
            if flow.get("level"):
                payload["level"] = flow["level"]
            if unlinked:
                payload["unlinked"] = unlinked
            map_pins = build_mission_map_pins(flow)
            if map_pins:
                payload["mapPins"] = map_pins
            scene_pins = build_mission_scene_pins(flow, available)
            if scene_pins:
                payload["scenePins"] = scene_pins
        if scene_graph:
            payload["sceneGraph"] = scene_graph
            mission_scene_graphs[mission] = scene_graph
            unconfirmed_keys: set[str] = {
                node.get("key")
                for node in scene_graph.get("nodes") or []
                if node.get("key") and node.get("orderConfirmed") is False
            }
            scene_graph_order = {
                node.get("key"): int(node.get("order"))
                for node in scene_graph.get("nodes") or []
                if node.get("key") and isinstance(node.get("order"), int)
                and node.get("orderConfirmed") is not False
            }
            if scene_graph_order or unconfirmed_keys:
                attach_offsets: Counter[str] = Counter()
                for entry in index_entries:
                    if entry.get("m") != mission:
                        continue
                    k = entry.get("k") or ""
                    if k in unconfirmed_keys:
                        entry["goUnknown"] = True
                        continue
                    order = scene_graph_order.get(k)
                    if order is not None:
                        entry["go"] = order
                        continue
                    attached_to = entry.get("attachTo")
                    attach_order = scene_graph_order.get(attached_to)
                    if attach_order is not None:
                        attach_offsets[attached_to] += 1
                        entry["go"] = attach_order + (attach_offsets[attached_to] / 1000)
        mission_flows_payload[mission] = payload

    mission_timeline_recovery_payload = build_mission_timeline_recovery_report(
        mission_scene_graphs
    )
    mission_timelines_by_mission = {
        mission.get("mission") or "": mission
        for mission in mission_timeline_recovery_payload.get("missions") or []
        if mission.get("mission")
    }
    mission_timeline_json = REPORTS_DIR / f"mission_timeline_recovery_{language_code}.json"
    mission_timeline_md = REPORTS_DIR / f"mission_timeline_recovery_{language_code}.md"
    write_mission_timeline_recovery_json(
        mission_timeline_json,
        mission_timeline_recovery_payload,
    )
    mission_timeline_md.parent.mkdir(parents=True, exist_ok=True)
    mission_timeline_md.write_text(
        render_mission_timeline_markdown(mission_timeline_recovery_payload),
        encoding="utf-8",
    )
    mission_timeline_report = {
        "json": str(mission_timeline_json.relative_to(ROOT)).replace("\\", "/"),
        "markdown": str(mission_timeline_md.relative_to(ROOT)).replace("\\", "/"),
        "summary": mission_timeline_recovery_payload["summary"],
        "evidencePolicy": MISSION_TIMELINE_EVIDENCE_POLICY,
    }

    def safe_mission_data_filename(mission_id: str, used_names: set[str]) -> str:
        stem = re.sub(r"[^0-9A-Za-z_.-]+", "_", str(mission_id or "")).strip("._")
        if not stem:
            stem = "mission"
        name = f"{stem}.json"
        if name.lower() not in used_names:
            used_names.add(name.lower())
            return name
        index = 2
        while True:
            candidate = f"{stem}_{index}.json"
            if candidate.lower() not in used_names:
                used_names.add(candidate.lower())
                return candidate
            index += 1

    mission_data_files: dict[str, str] = {}
    mission_data_bytes = 0
    mission_data_missions = sorted(
        set(mission_extras_payload)
        | set(mission_flows_payload)
        | set(mission_timelines_by_mission)
    )
    if mission_data_missions:
        mission_dir.mkdir(parents=True, exist_ok=True)
        used_mission_filenames: set[str] = set()
        for mission in mission_data_missions:
            filename = safe_mission_data_filename(mission, used_mission_filenames)
            rel_file = f"mission/{filename}"
            payload = {"mission": mission}
            if mission in mission_extras_payload:
                payload["extras"] = mission_extras_payload[mission]
            if mission in mission_flows_payload:
                payload["flow"] = mission_flows_payload[mission]
            if mission in mission_timelines_by_mission:
                payload["timelineRecovery"] = mission_timelines_by_mission[mission]
            out_path = out_dir / rel_file
            with out_path.open("w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
            mission_data_files[mission] = rel_file
            mission_data_bytes += out_path.stat().st_size

    with (out_dir / "index.json").open("w", encoding="utf-8") as f:
        index_payload = {
            "generated": int(time.time()),
            "profile": profile,
            "actorNames": actor_names,
            "missionNames": mission_names,
            "entries": index_entries,
        }
        if write_reference and reference_stats:
            index_payload["reference"] = {
                "index": "reference/index.json",
                "stats": reference_stats,
            }
        if mission_data_files:
            index_payload["missionData"] = {
                "files": mission_data_files,
                "missions": len(mission_data_files),
                "bytes": mission_data_bytes,
            }
        index_payload["missionTimelineRecovery"] = mission_timeline_report
        if story_source_link_report:
            index_payload["storySourceLinks"] = {
                "sourceIndex": story_source_link_report.get("sourceIndex"),
                "summary": story_source_link_report.get("summary"),
                "report": story_source_link_report.get("report"),
            }
        if narrative_video_report:
            index_payload["narrativeVideos"] = {
                "summary": narrative_video_report.get("summary"),
                "report": narrative_video_report.get("report"),
            }
        if include_reference_in_story_index:
            index_payload["missionExtras"] = mission_extras_payload
            index_payload["missionFlows"] = mission_flows_payload
        json.dump(index_payload, f, ensure_ascii=False, separators=(",", ":"))

    total_size = sum(p.stat().st_size for p in conv_dir.glob("*.json"))
    conv_count = len(list(conv_dir.glob("*.json")))
    index_path = out_dir / "index.json"
    scene_order_report = write_scene_order_gap_reports(language_code, conv_dir)
    inferred_anchor_report = write_inferred_option_anchors_report(language_code, conv_dir)
    print(f"\n[{language_code}] Done in {time.time()-t0:.1f}s")
    print(f"  profile:       {profile}")
    print(f"  conversations: {len(index_entries)}")
    print(f"  actors:        {len(actor_names)}")
    print(f"  conv data:     {total_size/1024/1024:.1f} MB across {conv_count} files")
    if mission_data_files:
        print(f"  mission data:  {mission_data_bytes/1024/1024:.1f} MB across {len(mission_data_files)} files")
    print(
        "  mission timelines: "
        f"{mission_timeline_recovery_payload['summary']['missionCount']} missions, "
        f"{mission_timeline_recovery_payload['summary']['questCount']} quests"
    )
    if story_source_link_report:
        source_summary = story_source_link_report.get("summary") or {}
        print(
            "  source links:  "
            f"{source_summary.get('attachedKeys', 0)} keys, "
            f"{source_summary.get('attachedReferences', 0)} refs attached"
        )
    if narrative_video_report:
        video_summary = narrative_video_report.get("summary") or {}
        print(
            "  narrative vid: "
            f"{video_summary.get('attachedKeys', 0)} keys, "
            f"{video_summary.get('attachedVideos', 0)} refs attached"
        )
    if reference_stats:
        print(f"  reference:     {reference_stats.get('bytes', 0)/1024/1024:.1f} MB across {reference_stats.get('tables', 0)} tables")
    print(f"  index:         {index_path.stat().st_size/1024:.1f} KB")
    return {
        "language": language_code,
        "profile": profile,
        "conversations": len(index_entries),
        "actors": len(actor_names),
        "convBytes": total_size,
        "convFiles": conv_count,
        "missionDataBytes": mission_data_bytes,
        "missionDataFiles": len(mission_data_files),
        "missionTimelineRecoveryReport": mission_timeline_report["markdown"],
        "missionTimelineRecoveryData": mission_timeline_report["json"],
        "missionTimelineRecoveryMissions": mission_timeline_recovery_payload["summary"]["missionCount"],
        "missionTimelineRecoveryUnresolved": mission_timeline_recovery_payload["summary"].get("unresolvedByKind", {}),
        "referenceBytes": int(reference_stats.get("bytes", 0)) if reference_stats else 0,
        "referenceTables": int(reference_stats.get("tables", 0)) if reference_stats else 0,
        "referenceRows": int(reference_stats.get("rows", 0)) if reference_stats else 0,
        "indexBytes": index_path.stat().st_size,
        "sceneOrderGapReport": str(scene_order_report["markdown"].relative_to(ROOT)).replace("\\", "/"),
        "sceneOrderGapData": str(scene_order_report["json"].relative_to(ROOT)).replace("\\", "/"),
        "sceneOrderGapCount": scene_order_report["summary"]["totalFlaggedScenes"],
        "inferredOptionAnchorsReport": str(inferred_anchor_report["markdown"].relative_to(ROOT)).replace("\\", "/"),
        "inferredOptionAnchorsData": str(inferred_anchor_report["json"].relative_to(ROOT)).replace("\\", "/"),
        "inferredOptionAnchorsScenes": inferred_anchor_report["summary"]["totalScenes"],
        "inferredOptionAnchorsGroups": inferred_anchor_report["summary"]["totalInferredGroups"],
        "narrativeVideoReport": str((narrative_video_report.get("report") or {}).get("markdown") or ""),
        "narrativeVideoData": str((narrative_video_report.get("report") or {}).get("json") or ""),
        "narrativeVideoKeys": int((narrative_video_report.get("summary") or {}).get("attachedKeys", 0)),
        "narrativeVideoRefs": int((narrative_video_report.get("summary") or {}).get("attachedVideos", 0)),
    }


def build_asset_index(out_path: Path, export_root: Path = EXPORTED_DIR) -> dict:
    return shared_build_asset_index(out_path, root=ROOT, export_root=export_root)

def collect_scene_order_gap_rows(conv_dir: Path) -> list[dict]:
    return shared_collect_scene_order_gap_rows(ROOT, conv_dir)


def build_scene_order_gap_summary(rows: list[dict], language: str) -> dict:
    return shared_build_scene_order_gap_summary(rows, language)


def write_scene_order_gap_reports(language: str, conv_dir: Path) -> dict:
    return shared_write_scene_order_gap_reports(ROOT, REPORTS_DIR, language, conv_dir)


def write_inferred_option_anchors_report(language: str, conv_dir: Path) -> dict:
    return shared_write_inferred_option_anchors_report(REPORTS_DIR, language, conv_dir)


def recover_timeline_orders_for_build(mode: str, force: bool = False) -> None:
    global _DIALOG_TIMELINE_LINE_ORDER_CACHE, _TIMELINE_TO_DIALOG_KEYS_CACHE
    if mode == "never":
        print("Timeline line-order recovery: skipped")
        return

    maps = discover_timeline_asset_maps(EXPORT_ROOT)
    order_out = timeline_recovery_order_out(EXPORT_ROOT)
    if not force and timeline_order_is_current(order_out, maps):
        print(f"Timeline line-order recovery: using {order_out}")
        return

    if mode == "auto" and not maps:
        print("Timeline line-order recovery: skipped (no AnimeStudio CLI AssetMaps found)")
        return

    print("Timeline line-order recovery: extracting and parsing Timeline assets...")
    try:
        recover_timeline_line_orders(
            TimelineRecoveryConfig(
                export_root=EXPORT_ROOT,
                maps=maps,
                order_out=order_out,
            )
        )
    except Exception as exc:
        if mode == "always":
            raise
        print(f"Timeline line-order recovery: skipped ({exc})")
        return

    _DIALOG_TIMELINE_LINE_ORDER_CACHE = None
    _TIMELINE_TO_DIALOG_KEYS_CACHE = None


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    recover_timeline_orders_for_build(args.timeline_recovery, args.force_timeline_recovery)

    available_languages = discover_languages()
    if not available_languages:
        raise SystemExit(
            "No I18nTextTable_*.json files found in export_full/structured/StreamingAssets/Table "
            "(or the legacy export_full/StreamingAssets/Table fallback)."
        )

    target_languages = normalize_language_selection(args.languages, available_languages)
    default_language = args.default_language.strip().upper() if args.default_language else DEFAULT_LANGUAGE
    if default_language not in target_languages:
        raise SystemExit(
            f"Default language {default_language!r} is not in the selected build set: "
            + ", ".join(target_languages)
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(LANG_DIR, ignore_errors=True)
    LANG_DIR.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(OUT_DIR / "conv", ignore_errors=True)
    for stale_file in ("manifest.json", "index.json", "actors.json"):
        stale_path = OUT_DIR / stale_file
        if stale_path.exists():
            stale_path.unlink()

    print("Building localized web UI bundles...")
    print("Languages:", ", ".join(target_languages))
    print("Default language:", default_language)
    print("Profile:", args.profile)
    if args.skip_reference:
        print("Reference bundle: disabled")

    stats: list[dict] = []
    for language_code in target_languages:
        stats.append(
            build_language_bundle(
                language_code,
                LANG_DIR / language_code,
                profile=args.profile,
                write_reference=not args.skip_reference,
            )
        )

    manifest = {
        "generated": int(time.time()),
        "defaultLanguage": default_language,
        "profile": args.profile,
        "reference": not args.skip_reference,
        "languages": [language_info(code) for code in target_languages],
        "stats": stats,
    }
    with (OUT_DIR / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    default_dir = LANG_DIR / default_language
    shutil.copy2(default_dir / "index.json", OUT_DIR / "index.json")

    print("\nManifest written to", OUT_DIR / "manifest.json")
    print("Default root copy:", OUT_DIR / "index.json")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)

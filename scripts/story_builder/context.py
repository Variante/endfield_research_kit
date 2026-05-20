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

Uses the structured export_full layout produced by the current WebUI export.

Writes:
  webui/data/manifest.json                 (available language bundles)
  webui/data/lang/<code>/index.json        (lightweight conversation list)
  webui/data/lang/<code>/actors.json       (actor display names)
  webui/data/lang/<code>/missions.json     (mission display names)
  webui/data/lang/<code>/search.json       (lazy full-text search text)
  webui/data/lang/<code>/conv/<key>.json
  webui/data/lang/<code>/mission/<id>.json (lazy mission context/flow)
  webui/data/lang/<code>/reference/...     (raw localized table reference)

Run from the repo root:
    python scripts/story_builder/build.py
    python scripts/story_builder/build.py --profile full
"""
from __future__ import annotations

import argparse
import base64
import binascii
import copy
import html
import itertools
import json
import os
import re
import shutil
import sys
import time
import unicodedata
from bisect import bisect_left
from collections import Counter, defaultdict, deque
from difflib import SequenceMatcher
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
WEBUI_SCRIPT_DIR = PACKAGE_DIR.parent
if str(WEBUI_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(WEBUI_SCRIPT_DIR))

from common import (
    ASSET_DIR,
    EXPORT_ROOT,
    LANG_DIR,
    OUT_DIR,
    REPORTS_DIR,
    ROOT,
    first_string_field as _first_string_field,
    is_present,
    path_id_export_base_stem,
    path_id_export_path_id,
    rel_path as repo_rel,
    rel_requires_path_id_export_name,
    unique_preserve as _unique_preserve,
    unique_strings,
    walk_const_values as _walk_const_values,
    walk_field_values as _walk_field_values,
    write_json,
)

SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from source_paths import _existing_unique_paths, _resolve_recovered_dir, _resolve_structured_source_dir
from .reports import (
    write_inferred_option_anchors_report as shared_write_inferred_option_anchors_report,
    write_scene_order_gap_reports as shared_write_scene_order_gap_reports,
)
from .source_links import build_source_links
from .timeline_recovery import (
    TimelineRecoveryConfig,
    default_order_out as timeline_recovery_order_out,
    discover_asset_maps as discover_timeline_asset_maps,
    recover_timeline_line_orders,
    timeline_order_is_current,
)
from .mission_recovery import (
    EVIDENCE_POLICY as MISSION_TIMELINE_EVIDENCE_POLICY,
    build_script_condition_ownership as build_mission_script_condition_ownership,
    canonical_cutscene_key as mission_canonical_cutscene_key,
    load_timeline_index as load_mission_timeline_index,
    mission_files as mission_timeline_files,
    recover_mission as recover_source_mission_timeline,
    render_markdown as render_mission_timeline_markdown,
    source_backed_scene_edges_from_scene_graph,
    source_backed_hash_terminals_from_scene_graph,
    source_backed_story_call_contexts_from_scene_graph,
    summarize as summarize_mission_timeline_recovery,
    write_json as write_mission_timeline_recovery_json,
)
from scene_order_gap_shared import (
    analyze_scene_order_disorder as shared_analyze_scene_order_disorder,
    build_scene_placement_index_from_timelines as shared_build_scene_placement_index_from_timelines,
    build_runtime_registry_debug as shared_build_runtime_registry_debug,
    build_scene_order_disorder_warning as shared_build_scene_order_disorder_warning,
    collect_scene_order_gap_rows_from_payloads as shared_collect_scene_order_gap_rows_from_payloads,
    load_dialog_id_registry as shared_load_dialog_id_registry,
)


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
ANIME_RESOURCE_DIRS = _existing_unique_paths([
    EXPORT_ROOT / "recovered" / "AnimeStudio-cli" / "StreamingAssets" / "json_by_type" / "TextAsset",
    EXPORT_ROOT / "recovered" / "AnimeStudio-cli" / "Persistent" / "json_by_type" / "TextAsset",
    EXPORT_ROOT / "recovered" / "AnimeStudio-cli" / "StreamingAssets" / "json_by_type" / "MonoBehaviour",
    EXPORT_ROOT / "recovered" / "AnimeStudio-cli" / "Persistent" / "json_by_type" / "MonoBehaviour",
])
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
DIALOG_OPTION_ID_CORRECTIONS = {
    # DialogOptionTable numbers this second topic as group 2, but the recovered
    # env_12 flow and adjacent env topic rows use one pre-scene menu where this
    # should be the second choice.
    "option_dlg_map01_lv002_env_12_2_001": "option_dlg_map01_lv002_env_12_1_002",
}
DIALOG_OPTION_GROUP_POSITION_OVERRIDES = {
    ("dlg_map01_lv002_env_12", 1): "pre",
}
CORRECTED_DIALOG_OPTION_IDS = set(DIALOG_OPTION_ID_CORRECTIONS.values())


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
_LEVELDATA_QUEST_STORY_REF_CACHE: dict[str, dict[str, list[dict]]] | None = None
_JSON_FILE_CACHE: dict[str, dict] = {}
_MISSION_AREA_CACHE: dict[str, dict] | None = None
_NPC_PROXY_TABLE_CACHE: dict[str, dict] | None = None
_CUTSCENE_ASSET_CACHE: dict[str, dict] | None = None
_CUTSCENE_SUBTITLE_TRACK_CACHE: dict[str, list[dict]] | None = None
_NARRATIVE_VIDEO_CACHE: list[dict] | None = None
_VIDEO_BINDINGS_CACHE: dict[str, dict] | None = None
VIDEO_BINDINGS_PATH = EXPORT_ROOT / "recovered" / "video_bindings.json"
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




__all__ = [name for name in globals() if not name.startswith("__")]

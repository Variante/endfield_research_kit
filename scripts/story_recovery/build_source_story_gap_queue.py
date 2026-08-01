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
import base64
import binascii
import hashlib
import json
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
from story_builder.level_bindings import (  # noqa: E402
    _load_levelscript_binding_data,
    _levelscript_native_control_paths_to_record,
    parse_leveldata_levelscript_brief_dictionary,
)
from story_builder.levelscript_binary import (  # noqa: E402
    decode_levelscript_record_payload,
    decode_levelscript_task_conditions,
    extract_levelscript_uid_records,
    levelscript_action_map_membership,
    levelscript_record_semantic_key,
)
from story_builder.mission_recovery import natural_key  # noqa: E402


SCHEMA = "sourceStoryGapQueue.v94"
STORY_BINDING_COVERAGE_SCHEMA_VERSION = 10
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
NON_OWNING_DIAGNOSTIC_QUEST_ATTACH_SOURCES = frozenset({
    "npcProxyDialog",
})
NPC_PROXY_DIALOG_SELECTION_GAMEASSEMBLY_SHA256 = (
    "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
)
DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID = (
    "dialog-tree-narrative-mask-connection-native-v1"
)
OFFLINE_EXHAUSTION_MAPPING_ID = (
    "current-build-offline-story-carrier-exhaustion-v71"
)
OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256 = (
    "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
)
OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS = {
    "dlg_gm01m22_6": "dlg_gm01m22_6",
    "dlg_gm01m22_7": "dlg_gm01m22_7",
    "dlg_gm01m22_8": "dlg_gm01m22_8",
    "misc_dlg_gm01m22_2d5": "dlg_gm01m22_2d5",
    "misc_dlg_gm01m22_3d2": "dlg_gm01m22_3d2",
    "misc_dlg_gm01m22_3d8": "dlg_gm01m22_3d8",
    "misc_dlg_gm01m22_4d0": "dlg_gm01m22_4d0",
    "radio_gm01m22_1d2": "radio_gm01m22_1d2",
    "radio_gm01m22_1d3": "radio_gm01m22_1d3",
    "sns_gm01m22_2": "sns_gm01m22_2",
    "text_gm01m22_5": "text_gm01m22_5",
    "dlg_gm02m3_1": "dlg_gm02m3_1",
    "dlg_gm02m3_2": "dlg_gm02m3_2",
    "dlg_gm02m3_3": "dlg_gm02m3_3",
    "dlg_gm02m3_4": "dlg_gm02m3_4",
    "dlg_gm02m3_5": "dlg_gm02m3_5",
    "radio_gm02m3_1": "radio_gm02m3_1",
    "radio_gm02m3_2": "radio_gm02m3_2",
    "radio_gm02m3_3": "radio_gm02m3_3",
    "radio_gm02m3_4": "radio_gm02m3_4",
    "radio_gm02m3_5": "radio_gm02m3_5",
    "dlg_gm02m3_1X": "dlg_gm02m3_1X",
    "dlg_gm02m3_1Y": "dlg_gm02m3_1Y",
    "dlg_gm02m3_2Y": "dlg_gm02m3_2Y",
    "dlg_gm02m3_2Z": "dlg_gm02m3_2Z",
    "dlg_gm02m3_3Z": "dlg_gm02m3_3Z",
    "dlg_gm02m3_3d": "dlg_gm02m3_3d",
    "dlg_gm01m6_6": "dlg_gm01m6_6",
    "dlg_gm01m6_7": "dlg_gm01m6_7",
    "misc_dlg_gm01m6_1d5": "dlg_gm01m6_1d5",
    "misc_dlg_gm01m6_3d7": "dlg_gm01m6_3d7",
    "misc_dlg_gm01m6_4d5": "dlg_gm01m6_4d5",
    "misc_dlg_gm01m6_4d7": "dlg_gm01m6_4d7",
    "radio_gm01m6_0d5": "radio_gm01m6_0d5",
    "radio_gm01m6_4d5": "radio_gm01m6_4d5",
    "radio_gm01m6_6": "radio_gm01m6_6",
    "dlg_gm01m7_1": "dlg_gm01m7_1",
    "dlg_gm01m7_2": "dlg_gm01m7_2",
    "dlg_gm01m7_3": "dlg_gm01m7_3",
    "dlg_gm01m7_5": "dlg_gm01m7_5",
    "dlg_gm01m7_7": "dlg_gm01m7_7",
    "radio_gm01m7_9": "radio_gm01m7_9",
    "sns_gm01m7_1": "sns_gm01m7_1",
    "sns_gm01m7_2": "sns_gm01m7_2",
    "text_gm01m7_1": "text_gm01m7_1",
    "dlg_gm01m12_1": "dlg_gm01m12_1",
    "dlg_gm01m12_3": "dlg_gm01m12_3",
    "dlg_gm01m12_6": "dlg_gm01m12_6",
    "dlg_gm01m12_8": "dlg_gm01m12_8",
    "text_gm01m12_1": "text_gm01m12_1",
    "text_gm01m12_3": "text_gm01m12_3",
    "text_gm01m12_5": "text_gm01m12_5",
    "text_gm01m12_6": "text_gm01m12_6",
    "text_gm01m12_7": "text_gm01m12_7",
    "radio_gm01m16_8": "radio_gm01m16_8",
    "radio_gm01m16_13": "radio_gm01m16_13",
    "radio_gm01m16_14": "radio_gm01m16_14",
    "dlg_gm01m20_1": "dlg_gm01m20_1",
    "dlg_gm01m20_5": "dlg_gm01m20_5",
    "dlg_gm01m20_6": "dlg_gm01m20_6",
    "dlg_gm01m20_7": "dlg_gm01m20_7",
    "radio_gm01m20_1": "radio_gm01m20_1",
    "radio_gm01m20_2": "radio_gm01m20_2",
    "radio_gm01m20_3": "radio_gm01m20_3",
    "radio_gm01m20_4": "radio_gm01m20_4",
    "dlg_gm01m24_5": "dlg_gm01m24_5",
    "radio_gm01m24_1d5": "radio_gm01m24_1d5",
    "radio_gm01m24_2": "radio_gm01m24_2",
    "radio_gm01m24_3": "radio_gm01m24_3",
    "radio_gm01m24_4": "radio_gm01m24_4",
    "dlg_gm01m25_5": "dlg_gm01m25_5",
    "radio_gm01m25_1d5": "radio_gm01m25_1d5",
    "radio_gm01m25_2": "radio_gm01m25_2",
    "radio_gm01m25_3": "radio_gm01m25_3",
    "radio_gm01m25_4": "radio_gm01m25_4",
    "dlg_gm01m26_5": "dlg_gm01m26_5",
    "radio_gm01m26_1d5": "radio_gm01m26_1d5",
    "radio_gm01m26_2": "radio_gm01m26_2",
    "radio_gm01m26_3": "radio_gm01m26_3",
    "radio_gm01m26_4": "radio_gm01m26_4",
}
OFFLINE_EXHAUSTION_MISSION_BRANCH_CONTEXTS = {
    "gm01m7": {
        "sourceFile": (
            "export_full/structured/Persistent/Data/Json/"
            "MissionRuntimeAsset/gm01m7.json"
        ),
        "sourceSha256":
            "3C6C04A5F5985E35A10EF3B87A9359B9CFA9CF2B4C379B9D3BA30E14ACB3B869",
        "fork": {
            "questId": "gm01m7_q#1",
            "successorQuestIds": ("gm01m7_q#8", "gm01m7_q#14"),
        },
        "merge": {
            "predecessorQuestIds": ("gm01m7_q#14", "gm01m7_q#8"),
            "questId": "gm01m7_q#9",
        },
        "sharedTracking": {
            "questIds": (
                "gm01m7_q#8",
                "gm01m7_q#14",
                "gm01m7_q#9",
            ),
            "proxyId": "sesidun_map01_001",
            "levelId": "map01_lv001",
        },
    },
}
OFFLINE_EXHAUSTION_MISSION_LINEAR_CONTEXTS = {
    "gm01m12": {
        "sourceFile": (
            "export_full/structured/Persistent/Data/Json/"
            "MissionRuntimeAsset/gm01m12.json"
        ),
        "sourceSha256":
            "B5022E18326385BCCCC4ACFBC076A5563C5B18066D291D1CA63F2DB11AC12EBB",
        "questSequence": tuple(
            f"gm01m12_q#{number}"
            for number in (15, 16, 13, 14, 1, 2, 3, 4, 12, 5, 6)
        ),
    },
}
OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS = {
    "gm01m16": {
        "sourceFile": (
            "export_full/structured/Persistent/Data/Json/"
            "MissionRuntimeAsset/gm01m16.json"
        ),
        "sourceSha256":
            "36DA8C77813A10590B4F03866BD43BB7B8376CB6392BB1FBBC7E56AA96A4CAE7",
        "mainPathQuestIds": tuple(
            f"gm01m16_q#{number}"
            for number in (1, 3, 34, 28, 10, 12, 40, 16, 21, 20, 24, 26)
        ),
        "prevQuestIdsByQuest": {
            f"gm01m16_q#{quest}": tuple(
                f"gm01m16_q#{previous}" for previous in predecessors
            )
            for quest, predecessors in {
                1: (), 2: (), 3: (2, 1), 5: (2, 1), 7: (5,),
                34: (3, 7), 4: (3, 7), 25: (34,), 27: (34,),
                28: (34,), 41: (34,), 42: (34,), 8: (34,), 9: (34,),
                10: (28,), 11: (9,), 12: (10,), 40: (12,), 16: (40,),
                21: (16,), 20: (21,), 24: (20,), 26: (24,), 43: (27,),
                44: (25,), 45: (41,),
            }.items()
        },
    },
    "gm01m20": {
        "sourceFile": (
            "export_full/structured/Persistent/Data/Json/"
            "MissionRuntimeAsset/gm01m20.json"
        ),
        "sourceSha256":
            "01BC364A3A64CFFE8BE236B017020D76ACDBB42866862031A5DC4405B501E355",
        "mainPathQuestIds": tuple(
            f"gm01m20_q#{number}" for number in (7, 1, 6, 3, 4, 2)
        ),
        "prevQuestIdsByQuest": {
            f"gm01m20_q#{quest}": tuple(
                f"gm01m20_q#{previous}" for previous in predecessors
            )
            for quest, predecessors in {
                7: (), 1: (7,), 6: (1,), 3: (6,), 4: (3,),
                2: (4,), 10: (4,),
            }.items()
        },
    },
}
OFFLINE_EXHAUSTION_LEVELDATA_DIALOG_BRANCH_CONTEXTS = {
    "gm01m24": {
        "levelId": "map01_lv006",
        "scriptId": "3500190001",
        "levelDataFile": (
            "export_full/structured/StreamingAssets/Data/Json/LevelData/"
            "map01_lv006/map01_lv006_lv_data_sub_gm01m24.json"
        ),
        "levelDataSha256":
            "AA4A3915C3D1655CAA9A74F043EABAF7B1B9449CE2AC2990D5362D8E3BC21AC2",
        "levelScriptFile": (
            "export_full/structured/StreamingAssets/Data/Json/LevelScriptData/"
            "map01_lv006/3500190001.json"
        ),
        "levelScriptSha256":
            "34432759C834431DD12FE68F81167775D94F9002578D04E2F12FAC7994785B32",
        "dictionaryEntryCount": 5,
        "dictionaryScriptIds": tuple(
            str(3500190000 + number) for number in range(1, 6)
        ),
        "propertyDialogs": {
            "start_dialog": "dlg_gm01m24_1",
            "succeed_dialog": "dlg_gm01m24_2",
            "failed_dialog": "dlg_gm01m24_3",
        },
        "startDialogListener": {
            "headerLocalId": 80,
            "eventName": "LevelEvent_OnDialogEnter",
            "nextLocalId": 81,
            "propertyPath": "start_dialog",
        },
        "resultSwitch": {
            "eventHeaderLocalId": 233,
            "eventName": "ScriptEvent_OnCustomEvent",
            "eventKey": "#e9dcab93",
            "switchLocalId": 181,
            "getterLocalId": 180,
            "getterPath": "result",
            "switchCases": (
                (0, -1), (1, 182), (2, 183), (3, 18),
                (4, 184), (5, 185), (8, 209), (9, 186),
            ),
            "cases": ({
                "value": 8,
                "entryLocalId": 209,
                "actionLocalId": 142,
                "getterLocalId": 141,
                "propertyPath": "succeed_dialog",
                "pathLocalIds": (181, 209, 210, 212, 213, 214, 227, 228, 142),
            }, {
                "value": 9,
                "entryLocalId": 186,
                "actionLocalId": 145,
                "getterLocalId": 144,
                "propertyPath": "failed_dialog",
                "pathLocalIds": (181, 186, 189, 190, 191, 204, 205, 145),
            }),
        },
    },
    "gm01m25": {
        "levelId": "map01_lv007",
        "scriptId": "2800020003",
        "levelDataFile": (
            "export_full/structured/StreamingAssets/Data/Json/LevelData/"
            "map01_lv007/map01_lv007_lv_data_sub_01.json"
        ),
        "levelDataSha256":
            "210C01BD69A88F6E8F66DB13EBA200E996A1F989615579B8E702923DD85A7DE0",
        "levelScriptFile": (
            "export_full/structured/StreamingAssets/Data/Json/LevelScriptData/"
            "map01_lv007/2800020003.json"
        ),
        "levelScriptSha256":
            "0B10781C03A03DA8710FA9A92AAF4247034771A7B8D4A5662D42BA7CE943ACF5",
        "dictionaryEntryCount": 5,
        "dictionaryScriptIds": (
            "2800020003", "2800020005", "2800020008",
            "2800020014", "2800020015",
        ),
        "propertyDialogs": {
            "start_dialog": "dlg_gm01m25_1",
            "succeed_dialog": "dlg_gm01m25_2",
            "failed_dialog": "dlg_gm01m25_3",
        },
        "startDialogListener": {
            "headerLocalId": 78,
            "eventName": "LevelEvent_OnDialogEnter",
            "nextLocalId": 79,
            "propertyPath": "start_dialog",
        },
        "resultSwitch": {
            "eventHeaderLocalId": 231,
            "eventName": "ScriptEvent_OnCustomEvent",
            "eventKey": "#33fa174c",
            "switchLocalId": 179,
            "getterLocalId": 178,
            "getterPath": "result",
            "switchCases": (
                (0, -1), (1, 180), (2, 181), (3, 18),
                (4, 182), (5, 183), (8, 207), (9, 184),
            ),
            "cases": ({
                "value": 8,
                "entryLocalId": 207,
                "actionLocalId": 140,
                "getterLocalId": 139,
                "propertyPath": "succeed_dialog",
                "pathLocalIds": (179, 207, 208, 210, 211, 212, 225, 226, 140),
            }, {
                "value": 9,
                "entryLocalId": 184,
                "actionLocalId": 143,
                "getterLocalId": 142,
                "propertyPath": "failed_dialog",
                "pathLocalIds": (179, 184, 187, 188, 189, 202, 203, 143),
            }),
        },
    },
    "gm01m26": {
        "levelId": "map01_lv005",
        "scriptId": "3400010017",
        "levelDataFile": (
            "export_full/structured/StreamingAssets/Data/Json/LevelData/"
            "map01_lv005/map01_lv005_lv_data_sub_01.json"
        ),
        "levelDataSha256":
            "7AEEE38BBBBEF778ACD6AE2F50A6F587652053E9CB57FACB5506621D091FD95D",
        "levelScriptFile": (
            "export_full/structured/StreamingAssets/Data/Json/LevelScriptData/"
            "map01_lv005/3400010017.json"
        ),
        "levelScriptSha256":
            "585D5E7B49C40765801D27867446D410F4D703FF8A62654CE776233D7C97879F",
        "dictionaryEntryCount": 22,
        "dictionaryScriptIds": (
            "3400010000", "3400010001", "3400010002", "3400010003",
            "3400010004", "3400010009", "3400010010", "3400010011",
            "3400010012", "3400010013", "3400010017", "3400010018",
            "3400010019", "3400010020", "3400010021", "3400010027",
            "3400010028", "3400010029", "3400010031", "3400010032",
            "3400010033", "3400010044",
        ),
        "propertyDialogs": {
            "start_dialog": "dlg_gm01m26_1",
            "succeed_dialog": "dlg_gm01m26_2",
            "failed_dialog": "dlg_gm01m26_3",
        },
        "startDialogListener": {
            "headerLocalId": 79,
            "eventName": "LevelEvent_OnDialogEnter",
            "nextLocalId": 80,
            "propertyPath": "start_dialog",
        },
        "resultSwitch": {
            "eventHeaderLocalId": 232,
            "eventName": "ScriptEvent_OnCustomEvent",
            "eventKey": "#3ebdaf39",
            "switchLocalId": 180,
            "getterLocalId": 179,
            "getterPath": "result",
            "switchCases": (
                (0, -1), (1, 181), (2, 182), (3, 22),
                (4, 183), (5, 184), (8, 208), (9, 185),
            ),
            "cases": ({
                "value": 8,
                "entryLocalId": 208,
                "actionLocalId": 141,
                "getterLocalId": 140,
                "propertyPath": "succeed_dialog",
                "pathLocalIds": (180, 208, 209, 211, 212, 213, 226, 227, 141),
            }, {
                "value": 9,
                "entryLocalId": 185,
                "actionLocalId": 144,
                "getterLocalId": 143,
                "propertyPath": "failed_dialog",
                "pathLocalIds": (180, 185, 188, 189, 190, 203, 204, 144),
            }),
        },
    },
}
OFFLINE_EXHAUSTION_LEVELSCRIPT_TASK_CONSUMERS = {
    "dlg_gm01m12_1": {
        "sourceFile": (
            "export_full/structured/Persistent/Data/Json/LevelScriptData/"
            "map01_lv001/2100110001.json"
        ),
        "sourceSha256":
            "86176021964C371921D28983D2394A934DF2F16C4C7892695D70EB71E01B8791",
        "levelId": "map01_lv001",
        "scriptId": "2100110001",
        "taskKey": "f7239bd1",
        "conditionKey": "10bf8411",
        "postDialogAction": {
            "eventName": "LevelEvent_OnDialogExit",
            "headerLocalId": 11,
            "actionLocalId": 12,
            "actionUnionTag": "0x001f",
            "serializedMemberCount": 19,
            "actionName": "BlackScreenFadeInAndOut",
        },
    },
    "dlg_gm01m12_3": {
        "sourceFile": (
            "export_full/structured/Persistent/Data/Json/LevelScriptData/"
            "map01_lv001/2100110003.json"
        ),
        "sourceSha256":
            "D47D6B43462380E1D399536BD2F016F93415EE24CA8C7B3F91A19E4681892A68",
        "levelId": "map01_lv001",
        "scriptId": "2100110003",
        "taskKey": "f7239bd1",
        "conditionKey": "10bf8411",
    },
}
EXACT_PARENT_DIALOG_DEPENDENCIES = {
    "dlg_a1m4_2": {
        "missionId": "a1m4",
        "questId": "a1m4_q#IntroDialog",
        "parentStoryKey": "dlg_a1m4_1",
        "sourceFile": (
            "export_full/recovered/AnimeStudio-cli/StreamingAssets/"
            "json_by_type/TextAsset/dlg_a1m4_1_p14B2A876733D2220.json"
        ),
        "sourceSha256":
            "E1AD79F7324E3772BB1CB8D95352A55C955F1229C1867EF33541982AD5059382",
        "sourcePathId": "14B2A876733D2220",
        "carrierKind": "trunk",
        "trunkIds": ("dlg_a1m4_2_001", "dlg_a1m4_2_002"),
        "carrierCount": 2,
    },
    "dlg_gm01m22_6": {
        "missionId": "gm01m22",
        "questId": "gm01m22_q#27",
        "parentStoryKey": "dlg_gm01m22_hapo",
        "sourceFile": (
            "export_full/recovered/AnimeStudio-cli/StreamingAssets/"
            "json_by_type/TextAsset/dlg_gm01m22_hapo_p4AEE0BFF15D9FD8F.json"
        ),
        "sourceSha256":
            "E8C224D75F98349C9272C16222538DC73BC0F99623DE974B2AC86941E85B5D08",
        "sourcePathId": "4AEE0BFF15D9FD8F",
        "carrierKind": "dialog",
        "dialogIds": ("dlg_gm01m22_6",),
        "carrierCount": 1,
    },
    "dlg_gm01m22_8": {
        "missionId": "gm01m22",
        "questId": "gm01m22_q#27",
        "parentStoryKey": "dlg_gm01m22_hapo",
        "sourceFile": (
            "export_full/recovered/AnimeStudio-cli/StreamingAssets/"
            "json_by_type/TextAsset/dlg_gm01m22_hapo_p4AEE0BFF15D9FD8F.json"
        ),
        "sourceSha256":
            "E8C224D75F98349C9272C16222538DC73BC0F99623DE974B2AC86941E85B5D08",
        "sourcePathId": "4AEE0BFF15D9FD8F",
        "carrierKind": "dialog",
        "dialogIds": ("dlg_gm01m22_8",),
        "carrierCount": 1,
    },
}
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
OFFLINE_EXHAUSTION_DIALOG_TEXT_TABLE_SHA256 = (
    "1C1BB59ACEA89212C9F2E34FE86457672FE5C8783FCD199F161D3F0DC9DEAD72"
)
OFFLINE_EXHAUSTION_DIALOG_OPTION_TABLE_SHA256 = (
    "8D86E8A10025DC0B54F800750650738A360DEBA169A0E3B3C48CB72FB8857C29"
)
OFFLINE_EXHAUSTION_READING_POPUP_TABLE_SHA256 = (
    "119BEFCA19E85FB11DF33D945FBA6374BB24E622F717CC50D7DA011BDB2A533C"
)
OFFLINE_EXHAUSTION_RICH_CONTENT_TABLE_SHA256 = (
    "1AB726FC15EA75A8212DB10D24630F75C565196A2EDCCCCCF5D57BC4D40B3301"
)
OFFLINE_EXHAUSTION_PRTS_ALL_ITEM_TABLE_SHA256 = (
    "28767DA031EA923EEB7FF852B7FFDDE9FDDB6892B5C7AC9E306B734E7314D7AA"
)
OFFLINE_EXHAUSTION_PRTS_RECORD_TABLE_SHA256 = (
    "7E9F2B5812494C045189C03C7E52513C4AB67FF16E06A0D817FC267784F8C61E"
)
OFFLINE_EXHAUSTION_PRTS_READING_TABLE_SHA256 = (
    "7686CE995F0C0DAE8C65ADA53A3E2737CC1CFD238F2E9C781C1A98F2860BDE05"
)
OFFLINE_EXHAUSTION_SNS_DIALOG_TABLE_SHA256 = (
    "6DA0BCAB64EB0ECFCFF8D21A446D8AA637669D6DAE3E2A66D43FC2721098A0BF"
)
OFFLINE_EXHAUSTION_SNS_OPTION_TABLE_SHA256 = (
    "CB0DF9E75EC049B404D73F5A65502D043BE951072A7AF215C80D2FC078319C11"
)
OFFLINE_EXHAUSTION_NPC_PROXY_EX_TABLE_SHA256 = (
    "19C9A7DC69DEED52A9EAFD26D216F31826065137490548E5917BE589BA11BBAC"
)
OFFLINE_EXHAUSTION_DIALOG_ID_SOURCE_SHA256 = (
    "AE2E68E93DCDE3C2AC792541A7456E5CE6B7AF4F2AE10887D178EBFBDC080F79"
)
OFFLINE_EXHAUSTION_DIALOG_ID_INDEX_SHA256 = (
    "3FC412F637063386E7BE4934099A546E24858836FD6C221AA1C2F6BC4092B083"
)
OFFLINE_EXHAUSTION_TIMELINE_LINE_ORDERS_SHA256 = (
    "C8408C67D8E6AD07CECF2007795C8E388B7F9BCE117B11DAADE8A7EFAD4EAEF2"
)
QUEST_ATTACHMENT_DIAGNOSTIC_MAPPING_ID = (
    "current-build-quest-story-attachment-negative-v3"
)
QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS = {
    "missionRuntime:e10m3d5": (
        "export_full/structured/Persistent/Data/Json/"
        "MissionRuntimeAsset/e10m3d5.json"
    ),
    "missionRuntime:e2m8": (
        "export_full/structured/Persistent/Data/Json/"
        "MissionRuntimeAsset/e2m8.json"
    ),
    "levelScript:map01_lv006/3500100002": (
        "export_full/structured/StreamingAssets/Data/Json/"
        "LevelScriptData/map01_lv006/3500100002.json"
    ),
    "levelData:map02_lv002/map02_lv002_lv_data_sub_e10m3": (
        "export_full/structured/StreamingAssets/Data/Json/"
        "LevelData/map02_lv002/map02_lv002_lv_data_sub_e10m3.json"
    ),
    "gameplayConfig:NpcProxyTable": (
        "export_full/structured/Persistent/Data/Json/"
        "GameplayConfig/NpcProxyTable.json"
    ),
    "gameplayConfig:WorldEntityRegistry": (
        "export_full/structured/Persistent/Data/Json/"
        "GameplayConfig/WorldEntityRegistry.json"
    ),
    "missionRuntime:e10m4d5": (
        "export_full/structured/Persistent/Data/Json/"
        "MissionRuntimeAsset/e10m4d5.json"
    ),
    "levelScript:dung02_rdg002/24400000018": (
        "export_full/structured/StreamingAssets/Data/Json/"
        "LevelScriptData/dung02_rdg002/24400000018.json"
    ),
    "missionRuntime:e5m2": (
        "export_full/structured/Persistent/Data/Json/"
        "MissionRuntimeAsset/e5m2.json"
    ),
    "missionRuntime:e5m2d5": (
        "export_full/structured/Persistent/Data/Json/"
        "MissionRuntimeAsset/e5m2d5.json"
    ),
    "levelScript:map02_lv001/10100070004": (
        "export_full/structured/StreamingAssets/Data/Json/"
        "LevelScriptData/map02_lv001/10100070004.json"
    ),
    "levelData:map02_lv001/map02_lv001_lv_data_sub_e5m2": (
        "export_full/structured/StreamingAssets/Data/Json/"
        "LevelData/map02_lv001/map02_lv001_lv_data_sub_e5m2.json"
    ),
    "gameplayConfig:NpcProxyExDataTable": (
        "export_full/structured/StreamingAssets/Data/Json/"
        "GameplayConfig/NpcProxyExDataTable.json"
    ),
}
QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_HASHES = {
    "missionRuntime:e10m3d5": (
        "086086FABEBD61CCC458987FC62AC426EBF6752B49621D739E32FA1DF82AB663"
    ),
    "missionRuntime:e2m8": (
        "5A6663F8AE1DFB134DD9DC17191AD6AE0297BAC26399C6BA68748828DCCE4FB0"
    ),
    "levelScript:map01_lv006/3500100002": (
        "218B0CB48328B20DD001F1F27EF904E120312BE827517D8644B0534488C8775D"
    ),
    "levelData:map02_lv002/map02_lv002_lv_data_sub_e10m3": (
        "A5B6FAFC682D7E12941FFA60DFE8A22BB64CADBF17DAFFB5B14A4381FB02D0EB"
    ),
    "gameplayConfig:NpcProxyTable": (
        "E3D14D56E6E1B769BD23560CE039F3455DDF8DEDDD80512A6BE726870CD8A14E"
    ),
    "gameplayConfig:WorldEntityRegistry": (
        "ABA73DDCB14B8DDDB354D5C97F62557581214119EDC95F00750FD30421836ED8"
    ),
    "missionRuntime:e10m4d5": (
        "D417581D527A42350597FF802A071F2F629C350C3B0942ACDBEB19FD5518FD0B"
    ),
    "levelScript:dung02_rdg002/24400000018": (
        "674D1733DDFA890AABEF7A2D534ED49D99EE427D3C782A6B904C00BFBCB5C5E3"
    ),
    "missionRuntime:e5m2": (
        "1F22C2F11071DAEFC85DB0D573B1A353B317053338A4AC3D664B430F5FF8D4F3"
    ),
    "missionRuntime:e5m2d5": (
        "5A0C49C5C0D1491CD04EBA23DACAA4D590F74D3AA6CCE77FD7B322A10D71C5B6"
    ),
    "levelScript:map02_lv001/10100070004": (
        "B155BA6346D8FC8B9DBFA6DD4BFD8F32F26E4575C5B6B1CE08E622FFA6BBD0DB"
    ),
    "levelData:map02_lv001/map02_lv001_lv_data_sub_e5m2": (
        "A134F81DC8797941B356B0C2775CF5AC545290ECB7D34E7E82B9EDAD74F602B8"
    ),
    "gameplayConfig:NpcProxyExDataTable": (
        "19C9A7DC69DEED52A9EAFD26D216F31826065137490548E5917BE589BA11BBAC"
    ),
}
QUEST_ATTACHMENT_DIAGNOSTIC_DECLARATIONS = {
    "e10m3d5_q#7": {
        "mission": "e10m3",
        "variantMission": "e10m3d5",
        "sourceKey": "missionRuntime:e10m3d5",
        "sourceFile": QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS[
            "missionRuntime:e10m3d5"
        ],
        "prevQuestIds": ("e10m3d5_q#1",),
        "conditionType": "GameConditionServerPlaceHolder",
        "comparer": 3,
        "progressToCompare": 1,
        "validationKind": "mission_bound_npc_proxy_context",
        "npcProxyId": "cuidaifu_map02_e10m3d5",
        "npcProxyMissionId": "e10m3d5",
        "npcProxyDialogRows": (
            ("e10m3d5", ""),
            ("e10m3d5", "dlg_e10m3_2"),
            ("e10m3d5", ""),
        ),
        "npcProxyPosition": {
            "x": -1179.63171,
            "y": 297.717682,
            "z": -171.104172,
        },
        "worldEntitySegmentId": "22800780001",
        "diagnosticStoryKeys": (
            "dlg_e10m3_2",
            "radio_e10m3_9",
        ),
        "connectionRows": (
            {
                "key": "radio_e10m3_9",
                "kind": "level_data",
                "relation": "leveldata_quest_reference",
                "direction": "context",
                "phase": "context",
                "confidence": "direct",
                "source": "LevelData quest/story byte-string context",
                "levelId": "map02_lv002",
                "file": QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS[
                    "levelData:map02_lv002/map02_lv002_lv_data_sub_e10m3"
                ],
            },
            {
                "key": "dlg_e10m3_2",
                "kind": "dialog",
                "relation": "npc_proxy_ex_attachment",
                "direction": "context",
                "phase": "context",
                "confidence": "scoped_unique",
                "source": (
                    "NpcProxyExDataTable.data[*] exact missionId + unique "
                    "quest tracking proxy"
                ),
                "npcProxyId": "cuidaifu_map02_e10m3d5",
                "npcProxyMissionId": "e10m3d5",
            },
            {
                "key": "dlg_e10m3_2",
                "kind": "dialog",
                "relation": "variant_runtime_attachment",
                "direction": "context",
                "phase": "context",
                "confidence": "scoped_variant",
                "source": "variant MissionRuntime quest attachment",
                "variantMission": "e10m3d5",
                "attachmentKind": "levelDataQuestRef",
            },
            {
                "key": "radio_e10m3_9",
                "kind": "radio",
                "relation": "variant_runtime_attachment",
                "direction": "context",
                "phase": "context",
                "confidence": "scoped_variant",
                "source": "variant MissionRuntime quest attachment",
                "variantMission": "e10m3d5",
                "attachmentKind": "levelDataQuestRef",
            },
        ),
        "levelDataStoryRefs": (
            {
                "storyRef": "radio_e10m3_9",
                "levelId": "map02_lv002",
                "file": QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS[
                    "levelData:map02_lv002/map02_lv002_lv_data_sub_e10m3"
                ],
                "distance": 140,
                "source": "LevelData quest/story byte-string context",
                "fields": ["radio_e10m3_9"],
            },
        ),
        "levelDataSourceKey": (
            "levelData:map02_lv002/map02_lv002_lv_data_sub_e10m3"
        ),
        "levelDataFile": QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS[
            "levelData:map02_lv002/map02_lv002_lv_data_sub_e10m3"
        ],
        "levelDataByteStringCounts": {
            "e10m3d5_q#7": 1,
            "radio_e10m3_9": 2,
            "dlg_e10m3_2": 0,
            "cuidaifu_map02_e10m3d5": 0,
        },
        "relatedSourceFiles": (
            QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS[
                "missionRuntime:e10m3d5"
            ],
            QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS[
                "levelData:map02_lv002/map02_lv002_lv_data_sub_e10m3"
            ],
            QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS[
                "gameplayConfig:NpcProxyTable"
            ],
            QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS[
                "gameplayConfig:NpcProxyExDataTable"
            ],
            QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS[
                "gameplayConfig:WorldEntityRegistry"
            ],
        ),
        "recoveryStatus": (
            "closed_server_placeholder_with_mission_bound_proxy_context"
        ),
        "evidenceKind": (
            "exact server placeholder plus mission-bound tracked NPC proxy "
            "and non-owning LevelData context"
        ),
        "attachmentBoundary": (
            "the objective tracks the exact doctor proxy and that proxy has "
            "a mission-bound dlg_e10m3_2 interaction row; the server-owned "
            "completion condition still exposes no dialog-finish or playback "
            "field, while radio_e10m3_9 is only LevelData byte proximity"
        ),
        "orderBoundary": (
            "the tracked proxy, mission-bound dialog selection, LevelData "
            "collection proximity, and predecessor shell do not identify "
            "the server completion event or relative Story order"
        ),
    },
    "e2m8_q#5": {
        "mission": "e2m8",
        "variantMission": "e2m8",
        "sourceKey": "missionRuntime:e2m8",
        "sourceFile": QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS[
            "missionRuntime:e2m8"
        ],
        "prevQuestIds": (),
        "conditionType": "CheckLevelScriptPropertyBool",
        "scriptId": "3500100002",
        "levelId": "map01_lv006",
        "propertyKey": "CarParked",
        "validationKind": "property_getter_without_story_chain",
        "levelScriptSourceKey": "levelScript:map01_lv006/3500100002",
        "levelScriptFile": QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS[
            "levelScript:map01_lv006/3500100002"
        ],
        "diagnosticStoryKeys": (
            "dlg_e2m8_1",
            "radio_e2m8_1",
            "radio_e2m8_1d5",
        ),
        "connectionRows": tuple(
            {
                "key": story_key,
                "kind": kind,
                "relation": "levelscript_condition_scope",
                "direction": "context",
                "phase": "context",
                "confidence": "scoped_script",
                "source": "LevelScript referenced by this quest condition",
                "mapId": "map01_lv006",
                "scriptId": "3500100002",
                "conditionKey": "CarParked",
            }
            for story_key, kind in (
                ("dlg_e2m8_1", "dialog"),
                ("radio_e2m8_1", "radio"),
                ("radio_e2m8_1d5", "radio"),
            )
        ),
        "levelScriptByteStringCounts": {
            "CarParked": 1,
            "dlg_e2m8_1": 2,
            "radio_e2m8_1": 3,
            "radio_e2m8_1d5": 1,
        },
        "getterRecord": {
            "start": 2113,
            "localId": 5,
            "nextId": 4,
            "code": 2564,
            "kind": 0,
            "uid": "112ebae2",
            "membership": "getterList#2",
            "texts": ("CarParked",),
        },
        "relatedSourceFiles": (
            QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS[
                "missionRuntime:e2m8"
            ],
            QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS[
                "levelScript:map01_lv006/3500100002"
            ],
        ),
        "recoveryStatus": (
            "closed_property_getter_without_story_control_chain"
        ),
        "evidenceKind": (
            "exact property checker plus hash-locked getter-list record"
        ),
        "attachmentBoundary": (
            "CarParked resolves to one exact getterList record at 0x841; "
            "the record carries no Story id and is serialized outside the "
            "three independent Story action chains in the same script"
        ),
        "orderBoundary": (
            "shared script membership cannot attach dlg_e2m8_1, "
            "radio_e2m8_1, or radio_e2m8_1d5 to this hidden parallel quest"
        ),
    },
    "e10m4d5_q#31": {
        "mission": "e10m4",
        "variantMission": "e10m4d5",
        "prevQuestIds": ("e10m4d5_q#8",),
        "conditionType": "CheckLevelScriptPropertyBool",
        "scriptId": "24400000018",
        "propertyKey": "enemyStart1",
        "diagnosticStoryKeys": (
            "dlg_e10m4_3",
            "dlg_e10m4_4",
            "dlg_e10m4_5",
            "radio_e10m4_68",
        ),
        "recoveryStatus":
            "closed_shared_levelscript_without_property_scoped_story_bridge",
    },
    "e10m4d5_q#34": {
        "mission": "e10m4",
        "variantMission": "e10m4d5",
        "prevQuestIds": ("e10m4d5_q#12",),
        "conditionType": "GameConditionServerPlaceHolder",
        "comparer": 3,
        "progressToCompare": 6,
        "diagnosticStoryKeys": ("radio_e10m4_68",),
        "recoveryStatus":
            "closed_server_placeholder_without_client_story_semantics",
    },
    "e10m4d5_q#35": {
        "mission": "e10m4",
        "variantMission": "e10m4d5",
        "prevQuestIds": ("e10m4d5_q#34",),
        "conditionType": "CheckLevelScriptPropertyBool",
        "scriptId": "24400000018",
        "propertyKey": "enemyStart2",
        "diagnosticStoryKeys": (
            "dlg_e10m4_3",
            "dlg_e10m4_4",
            "dlg_e10m4_5",
            "radio_e10m4_68",
        ),
        "recoveryStatus":
            "closed_shared_levelscript_without_property_scoped_story_bridge",
    },
    "e5m2_q#33": {
        "mission": "e5m2",
        "variantMission": "e5m2",
        "sourceKey": "missionRuntime:e5m2",
        "sourceFile": QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS[
            "missionRuntime:e5m2"
        ],
        "prevQuestIds": ("e5m2_q#12",),
        "conditionType": "CheckLevelScriptPropertyBool",
        "scriptId": "10100070004",
        "propertyKey": "bridge",
        "validationKind": "shared_levelscript_condition_scope",
        "levelScriptSourceKey": "levelScript:map02_lv001/10100070004",
        "levelScriptFile": QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS[
            "levelScript:map02_lv001/10100070004"
        ],
        "diagnosticStoryKeys": (
            "dlg_e5m2_10",
            "radio_e5m2_10",
        ),
        "connectionRows": (
            {
                "key": "dlg_e5m2_10",
                "kind": "dialog",
                "relation": "levelscript_condition_scope",
                "direction": "context",
                "phase": "context",
                "confidence": "scoped_script",
                "source": "LevelScript referenced by this quest condition",
                "mapId": "map02_lv001",
                "scriptId": "10100070004",
                "conditionKey": "bridge",
            },
            {
                "key": "radio_e5m2_10",
                "kind": "radio",
                "relation": "levelscript_condition_scope",
                "direction": "context",
                "phase": "context",
                "confidence": "scoped_script",
                "source": "LevelScript referenced by this quest condition",
                "mapId": "map02_lv001",
                "scriptId": "10100070004",
                "conditionKey": "bridge",
            },
        ),
        "levelScriptByteStringCounts": {
            "e5m2_q#33": 1,
            "dlg_e5m2_10": 1,
            "radio_e5m2_10": 1,
        },
        "recoveryStatus":
            "closed_shared_levelscript_without_property_scoped_story_bridge",
        "evidenceKind": (
            "exact property checker plus hash-locked same-script task and "
            "Story-call boundary"
        ),
        "attachmentBoundary": (
            "the script contains this quest id and two Story calls, but its "
            "only bridge substrings belong to guide_group_wltechbridge and "
            "guide_text_wltechbridge_title; it has no exact MemoryPack "
            "string for the six-character property key and no decoded "
            "property-scoped Story control path"
        ),
        "orderBoundary": (
            "same-script quest/task bytes, Story calls, and generated "
            "condition scope do not identify playback, ownership, or order"
        ),
    },
    "e5m2d5_q#12": {
        "mission": "e5m2",
        "variantMission": "e5m2d5",
        "sourceKey": "missionRuntime:e5m2d5",
        "sourceFile": QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS[
            "missionRuntime:e5m2d5"
        ],
        "prevQuestIds": ("e5m2d5_q#11",),
        "conditionType": "GameConditionServerPlaceHolder",
        "progressToCompare": 1,
        "validationKind": "weak_leveldata_context",
        "levelDataSourceKey": (
            "levelData:map02_lv001/map02_lv001_lv_data_sub_e5m2"
        ),
        "levelDataFile": QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS[
            "levelData:map02_lv001/map02_lv001_lv_data_sub_e5m2"
        ],
        "npcProxyId": "tangtang_map02_e5m2duizhi",
        "npcProxyDialogRows": (
            ("", ""),
            ("", "dlg_e5m2_8"),
        ),
        "diagnosticStoryKeys": (
            "radio_e5m2_7d5",
            "radio_e5m2_18",
        ),
        "connectionRows": (
            {
                "key": "radio_e5m2_18",
                "kind": "level_data",
                "relation": "leveldata_quest_reference",
                "direction": "context",
                "phase": "context",
                "confidence": "direct",
                "source": "LevelData quest/story byte-string context",
                "levelId": "map02_lv001",
                "file": QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS[
                    "levelData:map02_lv001/map02_lv001_lv_data_sub_e5m2"
                ],
            },
            {
                "key": "radio_e5m2_7d5",
                "kind": "radio",
                "relation": "variant_runtime_attachment",
                "direction": "context",
                "phase": "context",
                "confidence": "scoped_variant",
                "source": "variant MissionRuntime quest attachment",
                "variantMission": "e5m2d5",
                "attachmentKind": "levelDataQuestRef",
            },
            {
                "key": "radio_e5m2_18",
                "kind": "radio",
                "relation": "variant_runtime_attachment",
                "direction": "context",
                "phase": "context",
                "confidence": "scoped_variant",
                "source": "variant MissionRuntime quest attachment",
                "variantMission": "e5m2d5",
                "attachmentKind": "levelDataQuestRef",
            },
        ),
        "levelDataStoryRefs": (
            {
                "storyRef": "radio_e5m2_18",
                "levelId": "map02_lv001",
                "file": QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS[
                    "levelData:map02_lv001/map02_lv001_lv_data_sub_e5m2"
                ],
                "distance": 118,
                "source": "LevelData quest/story byte-string context",
                "fields": ["radio_e5m2_18"],
            },
        ),
        "levelDataByteStringCounts": {
            "e5m2d5_q#12": 2,
            "radio_e5m2_18": 3,
        },
        "recoveryStatus":
            "closed_weak_leveldata_reference_without_typed_story_bridge",
        "evidenceKind": (
            "exact server placeholder plus hash-locked weak LevelData "
            "quest/Story byte proximity"
        ),
        "attachmentBoundary": (
            "the objective is server-owned; its tracked NPC proxy has no "
            "mission-bound dialog, while the LevelData evidence is only "
            "byte-string proximity to radio_e5m2_18 and a weak synthesized "
            "variant attachment"
        ),
        "orderBoundary": (
            "LevelData collection proximity and predecessor-shell context "
            "do not establish playback, ownership, or relative Story order"
        ),
        "reopenWhen": (
            "any source hash or generated shape changes, or a typed "
            "MissionRuntime, LevelData, or mission-bound NPC-proxy Story "
            "route is recovered"
        ),
    },
}
OFFLINE_EXHAUSTION_E11M4_CUTSCENE = (
    "cutscene_e11m4_rift_camera_state1to2"
)
OFFLINE_EXHAUSTION_E11M1_TEXT_ONLY_CUTSCENE = "cutscene_e11m1_2"
OFFLINE_EXHAUSTION_TEXT_ONLY_CUTSCENES = {
    "cutscene_e1m1_6": {
        "missionId": "e1m1",
        "definitionRowKeys": tuple(
            f"cutscene_e1m1_6_{number:02d}" for number in range(1, 6)
        ),
    },
    "cutscene_e2m1_1": {
        "missionId": "e2m1",
        "definitionRowKeys": (
            "cutscene_e2m1_1_01",
            "cutscene_e2m1_1_02",
        ),
    },
    "cutscene_e2m5_2": {
        "missionId": "e2m5",
        "definitionRowKeys": (
            "cutscene_e2m5_2_01",
            "cutscene_e2m5_2_11",
        ),
    },
    "cutscene_e2m5_3": {
        "missionId": "e2m5",
        "definitionRowKeys": (
            "cutscene_e2m5_3_01",
            "cutscene_e2m5_3_11",
        ),
    },
    "cutscene_e3m4_1": {
        "missionId": "e3m4",
        "definitionRowKeys": tuple(
            f"cutscene_e3m4_1_{number:02d}" for number in range(1, 12)
        ),
        "consumerBoundary": (
            "the exact TextTable group has no recovered original Story "
            "consumer; the displayed cs_video_e3m5_4 media is a manual "
            "presentation override, while its authoritative LevelScript/FMV "
            "binding targets cutscene_e3m5_4"
        ),
        "orderBoundary": (
            "the manual video attachment and TextTable row order do not "
            "establish e3m4 activation, ownership, or relative Story order"
        ),
    },
    "cutscene_e4m1_1": {
        "missionId": "e4m1",
        "definitionRowKeys": (
            "cutscene_e4m1_1_01",
            "cutscene_e4m1_1_02",
        ),
    },
    "cutscene_e6m3_2": {
        "missionId": "e6m3",
        "definitionRowKeys": tuple(
            f"cutscene_e6m3_2_{number:02d}"
            for number in range(1, 15)
        ),
    },
    OFFLINE_EXHAUSTION_E11M1_TEXT_ONLY_CUTSCENE: {
        "missionId": "e11m1",
        "definitionRowKeys": tuple(
            f"{OFFLINE_EXHAUSTION_E11M1_TEXT_ONLY_CUTSCENE}_{number:02d}"
            for number in range(1, 5)
        ),
    },
}
OFFLINE_EXHAUSTION_SNS_DEFINITIONS = {
    "sns_gm01m7_1": {
        "missionId": "gm01m7",
        "chatId": "sns_npc_fiona",
        "contentIds": (-1, 1, 2, 3),
        "optionIdsByContentId": {},
        "optionNextContentIds": {},
        "optionDescriptionIds": {},
        "runtimeTracking": {
            "sourceFile": (
                "export_full/structured/Persistent/Data/Json/"
                "MissionRuntimeAsset/gm01m12.json"
            ),
            "sourceSha256":
                "B5022E18326385BCCCC4ACFBC076A5563C5B18066D291D1CA63F2DB11AC12EBB",
            "runtimeMissionId": "gm01m12",
            "questId": "gm01m12_q#16",
            "objectiveIndex": 0,
            "trackingIndex": 0,
        },
    },
    "sns_gm01m7_2": {
        "missionId": "gm01m7",
        "chatId": "sns_npc_fiona",
        "contentIds": (-1, 1, 2, 3, 4),
        "optionIdsByContentId": {},
        "optionNextContentIds": {},
        "optionDescriptionIds": {},
    },
    "sns_gm01m22_2": {
        "missionId": "gm01m22",
        "chatId": "sns_chr_jite",
        "dialogType": 2,
        "contentIds": (-1, *range(1, 12)),
        "optionIdsByContentId": {
            2: ("option_sns_gm01m22_2_1_001",),
            7: ("option_sns_gm01m22_2_2_001",),
        },
        "optionNextContentIds": {
            "option_sns_gm01m22_2_1_001": 3,
            "option_sns_gm01m22_2_2_001": 8,
        },
        "optionDescriptionIds": {
            "option_sns_gm01m22_2_1_001": 755145669281044969,
            "option_sns_gm01m22_2_2_001": -5063182789246158849,
        },
        "preContentIds": {
            1: 0,
            2: 1,
            3: 2,
            4: 3,
            5: 4,
            6: 5,
            7: 6,
            8: 7,
            9: 8,
            10: 9,
            11: 10,
            -1: 11,
        },
        "nextContentIds": {
            1: 2,
            3: 4,
            4: 5,
            5: 6,
            6: 7,
            8: 9,
            9: 10,
            10: 11,
            11: -1,
        },
    },
    "sns_a1m8d1_1": {
        "missionId": "a1m8d1",
        "chatId": "sns_npc_zuoguyan_a1m8d3",
        "contentIds": (-1, *range(1, 20)),
        "optionIdsByContentId": {
            2: ("option_sns_a1m8d1_1_1_001",),
            8: (
                "option_sns_a1m8d1_1_2_001",
                "option_sns_a1m8d1_1_2_002",
            ),
            12: (
                "option_sns_a1m8d1_1_3_001",
                "option_sns_a1m8d1_1_3_002",
            ),
            17: ("option_sns_a1m8d1_1_4_001",),
        },
        "optionNextContentIds": {
            "option_sns_a1m8d1_1_1_001": 3,
            "option_sns_a1m8d1_1_2_001": 9,
            "option_sns_a1m8d1_1_2_002": 10,
            "option_sns_a1m8d1_1_3_001": 13,
            "option_sns_a1m8d1_1_3_002": 14,
            "option_sns_a1m8d1_1_4_001": 18,
        },
        "optionDescriptionIds": {
            "option_sns_a1m8d1_1_1_001": -2785675792856990654,
            "option_sns_a1m8d1_1_2_001": 116550779129542386,
            "option_sns_a1m8d1_1_2_002": 6872746145578674578,
            "option_sns_a1m8d1_1_3_001": -3208068959343489344,
            "option_sns_a1m8d1_1_3_002": -3974861342589115965,
            "option_sns_a1m8d1_1_4_001": 8144357534706424610,
        },
        "preContentIds": {
            9: 8,
            10: 8,
            11: 10,
            13: 12,
            14: 12,
            15: 14,
        },
        "nextContentIds": {
            9: 11,
            10: 11,
            13: 15,
            14: 15,
        },
    },
    "sns_e1m9_1": {
        "missionId": "e1m9",
        "chatId": "sns_chr_0006_wolfgd",
        "contentIds": (-1, 1, 2),
        "optionIdsByContentId": {},
        "optionNextContentIds": {},
        "optionDescriptionIds": {},
    },
    "sns_e7m4_1": {
        "missionId": "e7m4",
        "chatId": "sns_npc_yanning_e7m4",
        "contentIds": (-1, *range(1, 8)),
        "optionIdsByContentId": {},
        "optionNextContentIds": {},
        "optionDescriptionIds": {},
        "contentParamsByContentId": {
            4: ("sns_image_e7m4_1",),
        },
    },
    "sns_e10m4_1": {
        "missionId": "e10m4",
        "chatId": "sns_chr_0030_zhuangfy",
        "contentIds": (-1, *range(1, 27)),
        "optionIdsByContentId": {
            1: ("option_sns_e10m4_1_1_001",),
            9: ("option_sns_e10m4_1_2_001",),
            13: ("option_sns_e10m4_1_3_001",),
            20: ("option_sns_e10m4_1_5_001",),
        },
        "optionNextContentIds": {
            "option_sns_e10m4_1_1_001": 2,
            "option_sns_e10m4_1_2_001": 10,
            "option_sns_e10m4_1_3_001": 14,
            "option_sns_e10m4_1_5_001": 21,
        },
        "optionDescriptionIds": {
            "option_sns_e10m4_1_1_001": -4875347938820133196,
            "option_sns_e10m4_1_2_001": 2580651301956064440,
            "option_sns_e10m4_1_3_001": 6992366624230327000,
            "option_sns_e10m4_1_5_001": 7374390088086658274,
        },
    },
}
OFFLINE_EXHAUSTION_TEXT_TABLE_ONLY_STORIES = {
    "black_e7m1_3": {
        "missionId": "e7m1",
        "storyKind": "black",
        "definitionRowKeys": ("black_e7m1_3_001",),
    },
    "black_e11m8_12": {
        "missionId": "e11m8",
        "storyKind": "black",
        "definitionRowKeys": ("black_e11m8_12_001",),
    },
    "black_e11m8_39": {
        "missionId": "e11m8",
        "storyKind": "black",
        "definitionRowKeys": ("black_e11m8_39_001",),
    },
}
OFFLINE_EXHAUSTION_E11M1_PRESENTATION_CUTSCENES = frozenset({
    "cutscene_e11m1_fire_end",
    "cutscene_e11m1_gatebattleend",
    "cutscene_e11m1_jsspsi_ground_cast",
    "cutscene_e11m1_shenjiaoe",
})
OFFLINE_EXHAUSTION_CUTSCENES_BY_MISSION = {
    "e0m0": frozenset({
        "cutscene_e0m0_1",
        "cutscene_e0m0_10",
        "cutscene_e0m0_11",
        "cutscene_e0m0_12",
        "cutscene_e0m0_11111",
    }),
    "e0m2": frozenset({
        "cutscene_e0m2_3_3",
        "cutscene_e0m2_99",
    }),
    "e1m1": frozenset({
        "cutscene_e1m1_3_1_test",
        "cutscene_e1m1_4",
        "cutscene_e1m1_6",
    }),
    "e1m3": frozenset({"cutscene_e1m3_1"}),
    "e2m1": frozenset({"cutscene_e2m1_1"}),
    "e2m5": frozenset({
        "cutscene_e2m5_2",
        "cutscene_e2m5_3",
    }),
    "e2m6": frozenset({
        "cutscene_e2m6_designer_AngelSurrounding",
    }),
    "e3m1": frozenset({"cutscene_e3m1_1"}),
    "e3m4": frozenset({"cutscene_e3m4_1"}),
    "e6m3": frozenset({"cutscene_e6m3_2"}),
    "e6m4": frozenset({
        "cutscene_e6m4_1",
        "cutscene_e6m4_hydrantStart",
    }),
    "e7m2": frozenset({"cutscene_e7m2_designer_QingBoZhai"}),
    "e9m2": frozenset({
        "cutscene_dung02_dg002_e9m2_lightthewall",
        "cutscene_dung02_dg002_e9m2_zipline01",
        "cutscene_dung02_dg002_e9m2_zipline02",
        "cutscene_dung02_dg002_e9m2_zipline03",
        "cutscene_dung02_dg002_e9m2_zipline06",
    }),
    "e11m1": frozenset({
        OFFLINE_EXHAUSTION_E11M1_TEXT_ONLY_CUTSCENE,
        *OFFLINE_EXHAUSTION_E11M1_PRESENTATION_CUTSCENES,
    }),
    "e11m2": frozenset({
        "cutscene_e11m2_liexi_xs_m_01_last_01",
        "cutscene_e11m2_liexi_xs_m_01_last_02",
        "cutscene_e11m2_liexi_xs_m_01_last_03",
        "cutscene_e11m2_rift_camera_state1to2",
    }),
    "e11m4": frozenset({OFFLINE_EXHAUSTION_E11M4_CUTSCENE}),
    "e11m6": frozenset({
        "cutscene_e11m6_rift_camera_state1to2",
        "cutscene_e11m6_zhuangcomein",
    }),
}
OFFLINE_EXHAUSTION_REVERSE_HOST_COUNTS = {
    "cutscene_e0m0_1": 1,
    "cutscene_e0m0_10": 1,
    "cutscene_e0m0_11": 1,
    "cutscene_e0m0_12": 1,
    "cutscene_e0m0_11111": 1,
    "cutscene_e0m2_3_3": 1,
    "cutscene_e0m2_99": 1,
    "cutscene_e1m1_3_1_test": 1,
    "cutscene_e1m1_4": 2,
    "cutscene_e1m3_1": 1,
    "cutscene_e2m6_designer_AngelSurrounding": 1,
    "cutscene_e3m1_1": 2,
    "cutscene_e6m4_1": 1,
    "cutscene_e6m4_hydrantStart": 1,
    "cutscene_e7m2_designer_QingBoZhai": 1,
    "cutscene_dung02_dg002_e9m2_lightthewall": 1,
    "cutscene_dung02_dg002_e9m2_zipline01": 1,
    "cutscene_dung02_dg002_e9m2_zipline02": 1,
    "cutscene_dung02_dg002_e9m2_zipline03": 1,
    "cutscene_dung02_dg002_e9m2_zipline06": 1,
    "cutscene_e11m1_fire_end": 2,
    "cutscene_e11m1_gatebattleend": 1,
    "cutscene_e11m1_jsspsi_ground_cast": 1,
    "cutscene_e11m1_shenjiaoe": 2,
    "cutscene_e11m2_liexi_xs_m_01_last_01": 1,
    "cutscene_e11m2_liexi_xs_m_01_last_02": 1,
    "cutscene_e11m2_liexi_xs_m_01_last_03": 1,
    "cutscene_e11m2_rift_camera_state1to2": 1,
    OFFLINE_EXHAUSTION_E11M4_CUTSCENE: 1,
    "cutscene_e11m6_rift_camera_state1to2": 1,
    "cutscene_e11m6_zhuangcomein": 1,
}
OFFLINE_EXHAUSTION_CUTSCENE_DEFINITIONS = {
    "cutscene_e0m0_1": {
        "timelineRegistryId": 158,
        "files": ((
            "cutscene_e0m0_1_pE3B9F4725855A80B.json",
            "E9571177CCA5CF3690DB72C5DA9CEE58675A3EFA5F09BB9A3E089227221F229D",
            "cutscene_e0m0_1",
        ),),
    },
    "cutscene_e0m0_10": {
        "timelineRegistryId": 134,
        "files": ((
            "cutscene_e0m0_10_p0BACFA664DABE351.json",
            "BAF4A8C03B894FD38949A55AE1098F55692A1C57C8A99ED2986424AE8A20F03E",
            "cutscene_e0m0_10",
        ),),
    },
    "cutscene_e0m0_11": {
        "timelineRegistryId": 133,
        "files": ((
            "cutscene_e0m0_11_pF7E1B65901F9C153.json",
            "A9FDB83E16EB188E74FC77016CDB1F60A0754268DB975626C4D6FC1F15D654F3",
            "cutscene_e0m0_11",
        ),),
    },
    "cutscene_e0m0_12": {
        "timelineRegistryId": 135,
        "files": ((
            "cutscene_e0m0_12_pE8E7E6C9DCF62878.json",
            "E49889DD3AA96950A71C9089357E96DA0A66D88F379006C254340198E8C897C2",
            "cutscene_e0m0_12",
        ),),
    },
    "cutscene_e0m0_11111": {
        "timelineRegistryId": None,
        "files": (),
    },
    "cutscene_e0m2_3_3": {
        "timelineRegistryId": 262,
        "files": ((
            "cutscene_e0m2_3_3_p8B24FED0A23FB54B.json",
            "4EF56CABF4E9136760664CD139ABC032A124E76B9EF411BD2A0D0B560FFDEFB9",
            "cutscene_e0m2_3_3",
        ),),
    },
    "cutscene_e0m2_99": {
        "timelineRegistryId": 237,
        "files": ((
            "m_cutscene_e0m2_99_pEA3DAF65D39D43C5.json",
            "0D33C200EA445BC610DD13FBA2EF7C1150E0E5344DE708CED686E64971C08E00",
            "m_cutscene_e0m2_99",
        ),),
    },
    "cutscene_e1m1_3_1_test": {
        "timelineRegistryId": 70,
        "files": ((
            "cutscene_e1m1_3_1_test_p9F77BA72F7CBE5D2.json",
            "CB22EB28D3500691B0A00F6862F93164F69D9D8B6315E05E2C072B8A8DB0D653",
            "cutscene_e1m1_3_1_test",
        ),),
    },
    "cutscene_e1m1_4": {
        "timelineRegistryId": 190,
        "files": (
            (
                "f_cutscene_e1m1_4_p45CAD9531490A151.json",
                "8BA0287DD75E0FD55AF4D86ABA157964A3A7D8A3F03563DC5291CEE4FA9A2AEF",
                "f_cutscene_e1m1_4",
            ),
            (
                "m_cutscene_e1m1_4_p52315EB9895D6AEB.json",
                "F421068C0B963F45B077BC8776D39EF0A5766332BB43B8B0B39C6EE73211F567",
                "m_cutscene_e1m1_4",
            ),
        ),
    },
    "cutscene_e1m3_1": {
        "timelineRegistryId": 89,
        "files": (
            (
                "cutscene_e1m3_1_p08A501CA1E17069D.json",
                "21F8CFA0B384573D011677A68F2D45C0A9E521CAB35AAB392F22405E3E428BB6",
                "cutscene_e1m3_1",
            ),
        ),
    },
    "cutscene_e2m6_designer_AngelSurrounding": {
        "timelineRegistryId": 310,
        "files": ((
            "cutscene_e2m6_designer_AngelSurrounding_p9E14E210A67B0AF8.json",
            "4CFD3CEECC55198E4B99FDEA37EB02E6E62F3676600AE6DA3B4D878264659FBD",
            "cutscene_e2m6_designer_AngelSurrounding",
        ),),
    },
    "cutscene_e3m1_1": {
        "timelineRegistryId": 191,
        "files": (
            (
                "f_cutscene_e3m1_1_p55C72BC571F24192.json",
                "F0385C7FA352A9707F40860BCF8155A0E0C5E714D73B9C3DCA36106B3B755EC4",
                "f_cutscene_e3m1_1",
            ),
            (
                "m_cutscene_e3m1_1_pDAF9DE02EC84436D.json",
                "4960D26EC2D83D96A58D4A7D6B11402827CC339D9CD3102F5451A53CF40B6160",
                "m_cutscene_e3m1_1",
            ),
        ),
    },
    "cutscene_e6m4_1": {
        "timelineRegistryId": 400,
        "files": ((
            "cutscene_e6m4_1_pB347CD3C7DD041A4.json",
            "A3EDEC8195ED17AFFC57FA2447057FB7BF19D011255052015D3930AA74356B35",
            "cutscene_e6m4_1",
        ),),
    },
    "cutscene_e6m4_hydrantStart": {
        "timelineRegistryId": 324,
        "files": ((
            "cutscene_e6m4_hydrantStart_pD2D24003F92DFB3F.json",
            "7AB80057A5325DB17BAC4C2563E8163E0FC7F7CD242B2A10D9C67B03AA1DB042",
            "cutscene_e6m4_hydrantStart",
        ),),
    },
    "cutscene_e7m2_designer_QingBoZhai": {
        "timelineRegistryId": 406,
        "files": (
            (
                "cutscene_e7m2_designer_QingBoZhai_p2FD121DA4B9E08A2.json",
                "F2FF234312A17C0E78854C5287236035790AB95113E1F6F0DC7EF02823B73063",
                "cutscene_e7m2_designer_QingBoZhai",
            ),
        ),
    },
    "cutscene_dung02_dg002_e9m2_lightthewall": {
        "timelineRegistryId": 327,
        "files": (
            (
                "cutscene_dung02_dg002_e9m2_lightthewall_"
                "pDC3E873CBC4A0AF3.json",
                "51492BC69BB7859C3E54B3C7028FF5E7999ED5F24AD28E09396948F7EDAE56D4",
                "cutscene_dung02_dg002_e9m2_lightthewall",
            ),
        ),
    },
    "cutscene_dung02_dg002_e9m2_zipline01": {
        "timelineRegistryId": 325,
        "files": (
            (
                "cutscene_dung02_dg002_e9m2_zipline01_"
                "p9FC50793C47BFF30.json",
                "50EC447D25DD5781C65CCCC3F1036CCD50AF88EF771B7A81C3286409F0AE9483",
                "cutscene_dung02_dg002_e9m2_zipline01",
            ),
        ),
    },
    "cutscene_dung02_dg002_e9m2_zipline02": {
        "timelineRegistryId": 334,
        "files": (
            (
                "cutscene_dung02_dg002_e9m2_zipline02_"
                "p4B6883C99A6D2D4D.json",
                "CFD426B2A75A1A124E7A9486D61DBDBDEE7D4E1E21E163263D47762DA9E21A51",
                "cutscene_dung02_dg002_e9m2_zipline02",
            ),
        ),
    },
    "cutscene_dung02_dg002_e9m2_zipline03": {
        "timelineRegistryId": 333,
        "files": (
            (
                "cutscene_dung02_dg002_e9m2_zipline03_"
                "p5B5782E97A94C0D0.json",
                "B738BB60C02B57812E031A7B452AA3F70D13446ACD4ABFF787C4A840F928C3B6",
                "cutscene_dung02_dg002_e9m2_zipline03",
            ),
        ),
    },
    "cutscene_dung02_dg002_e9m2_zipline06": {
        "timelineRegistryId": 326,
        "files": (
            (
                "cutscene_dung02_dg002_e9m2_zipline06_"
                "p97F0C0478EBE00B0.json",
                "572ECDDA73CEA155043FA045914AA78BA713A8ED63724D31152F30D79FF89B2B",
                "cutscene_dung02_dg002_e9m2_zipline06",
            ),
        ),
    },
    "cutscene_e11m1_fire_end": {
        "timelineRegistryId": 458,
        "files": (
            (
                "f_cutscene_e11m1_fire_end_pD7686B40F0A16B92.json",
                "2886C9B0440702DC416E54338BDA0F2A84F4268F9C0B951D3D96B9DFA6D63EF5",
                "f_cutscene_e11m1_fire_end",
            ),
            (
                "m_cutscene_e11m1_fire_end_pCC43771AC811B454.json",
                "8690B570AFEEA02F4C5C446F150090E90B67F7C70759A3B637D712238D78AE53",
                "m_cutscene_e11m1_fire_end",
            ),
        ),
    },
    "cutscene_e11m1_gatebattleend": {
        "timelineRegistryId": 488,
        "files": (
            (
                "cutscene_e11m1_gatebattleend_pE2667486BB094752.json",
                "0F14260AA21D4BA3B75373E03A66661B625A7789970F23A509CDEA7740900D64",
                "cutscene_e11m1_gatebattleend",
            ),
        ),
    },
    "cutscene_e11m1_jsspsi_ground_cast": {
        "timelineRegistryId": 481,
        "files": (
            (
                "cutscene_e11m1_jsspsi_ground_cast_p6540AA2BB4C80312.json",
                "10A09BFD2F689BB0E6A51C5022022C36CA9BF838866723D90C152EA82A537BEC",
                "cutscene_e11m1_jsspsi_ground_cast",
            ),
        ),
    },
    "cutscene_e11m1_shenjiaoe": {
        "timelineRegistryId": 454,
        "files": (
            (
                "f_cutscene_e11m1_shenjiaoe_p5B823ED46AD8814D.json",
                "ABF4FC8671603D1C47C10CA3A659EFA079A18B13431632FB6D86F5BF73D023CC",
                "f_cutscene_e11m1_shenjiaoe",
            ),
            (
                "m_cutscene_e11m1_shenjiaoe_p51A93B02AA4BE50A.json",
                "0E2AB3EBB31F633DFD672C4FB7F1977207019C14AC0FCE35BFDCBD6793AB9693",
                "m_cutscene_e11m1_shenjiaoe",
            ),
        ),
    },
    "cutscene_e11m2_liexi_xs_m_01_last_01": {
        "timelineRegistryId": 540,
        "files": (
            (
                "cutscene_e11m2_liexi_xs_m_01_last_01_p1062615A5F282A62.json",
                "77B3BF24826C0E640517506D4B8008BF602037FA5847E34007A97EA8CD56AE36",
                "cutscene_e11m2_liexi_xs_m_01_last_01",
            ),
        ),
    },
    "cutscene_e11m2_liexi_xs_m_01_last_02": {
        "timelineRegistryId": 541,
        "files": (
            (
                "cutscene_e11m2_liexi_xs_m_01_last_02_pD1933E2EC8EE84E6.json",
                "751B1869BB3DEC25E9E9843CA702C9511F66221E3D0C336EC317A5DAD2FDDE43",
                "cutscene_e11m2_liexi_xs_m_01_last_02",
            ),
        ),
    },
    "cutscene_e11m2_liexi_xs_m_01_last_03": {
        "timelineRegistryId": 539,
        "files": (
            (
                "cutscene_e11m2_liexi_xs_m_01_last_03_p0FB7F5823DFDB681.json",
                "0110DCA894B243A50E6BF869AA0E8177449398432095C688A2E528269F21ECD3",
                "cutscene_e11m2_liexi_xs_m_01_last_03",
            ),
        ),
    },
    "cutscene_e11m2_rift_camera_state1to2": {
        "timelineRegistryId": 485,
        "files": (
            (
                "cutscene_e11m2_rift_camera_state1to2_pA751B325BC1816CA.json",
                "6887771164CCD875EFFF2920869E1F64614EF44AF710030201E77C9FD2FB0DA4",
                "cutscene_e11m2_rift_camera_state1to2",
            ),
        ),
    },
    OFFLINE_EXHAUSTION_E11M4_CUTSCENE: {
        "timelineRegistryId": 484,
        "files": (
            (
                "cutscene_e11m4_rift_camera_state1to2_p86E71A990775EC2D.json",
                "EF073ADA194D047E28500ECEF71E2B370587905C83DFEFA1CAE5E9E591A0EA99",
                OFFLINE_EXHAUSTION_E11M4_CUTSCENE,
            ),
        ),
    },
    "cutscene_e11m6_rift_camera_state1to2": {
        "timelineRegistryId": 483,
        "files": (
            (
                "cutscene_e11m6_rift_camera_state1to2_pA96D959869136A8C.json",
                "3DF5E0A78B69EE7A512E30A84F1AE351D7BA04FEB3C1B687DED33ABB3318170A",
                "cutscene_e11m6_rift_camera_state1to2",
            ),
        ),
    },
    "cutscene_e11m6_zhuangcomein": {
        "timelineRegistryId": 547,
        "files": (
            (
                "cutscene_e11m6_zhuangcomein_pE9B3097117A5932B.json",
                "99420E962A10B4B202390D372F30F9DF1C3D51058F84094279B3126A1206678F",
                "cutscene_e11m6_zhuangcomein",
            ),
        ),
    },
}
OFFLINE_EXHAUSTION_GAMEOBJECT_ROW_COUNTS = {
    "cutscene_e0m0_1": 1,
    "cutscene_e0m0_10": 1,
    "cutscene_e0m0_11": 1,
    "cutscene_e0m0_12": 1,
    "cutscene_e0m0_11111": 1,
    "cutscene_e0m2_3_3": 1,
    "cutscene_e0m2_99": 1,
    "cutscene_e1m1_3_1_test": 1,
    "cutscene_e1m1_4": 2,
    "cutscene_e1m3_1": 1,
    "cutscene_e2m6_designer_AngelSurrounding": 1,
    "cutscene_e3m1_1": 2,
    "cutscene_e6m4_1": 1,
    "cutscene_e6m4_hydrantStart": 1,
    "cutscene_e7m2_designer_QingBoZhai": 1,
    "cutscene_dung02_dg002_e9m2_lightthewall": 1,
    "cutscene_dung02_dg002_e9m2_zipline01": 1,
    "cutscene_dung02_dg002_e9m2_zipline02": 1,
    "cutscene_dung02_dg002_e9m2_zipline03": 1,
    "cutscene_dung02_dg002_e9m2_zipline06": 1,
    "cutscene_e11m1_fire_end": 4,
    "cutscene_e11m1_gatebattleend": 1,
    "cutscene_e11m1_jsspsi_ground_cast": 1,
    "cutscene_e11m1_shenjiaoe": 2,
    "cutscene_e11m2_liexi_xs_m_01_last_01": 1,
    "cutscene_e11m2_liexi_xs_m_01_last_02": 1,
    "cutscene_e11m2_liexi_xs_m_01_last_03": 0,
    "cutscene_e11m2_rift_camera_state1to2": 1,
    OFFLINE_EXHAUSTION_E11M4_CUTSCENE: 1,
    "cutscene_e11m6_rift_camera_state1to2": 1,
    "cutscene_e11m6_zhuangcomein": 1,
}
OFFLINE_EXHAUSTION_ROOT_PLAYBACK_ALIASES = {
    "cutscene_e11m2_liexi_xs_m_01_last_02": (
        "cutscene_e11m2_liexi_xs_m_01_last_01",
        "cutscene_e11m2_liexi_xs_m_01_last_02",
    ),
    "cutscene_e11m2_liexi_xs_m_01_last_03": (
        "cutscene_e11m2_liexi_xs_m_01_last_02",
        "cutscene_e11m2_liexi_xs_m_01_last_03",
    ),
}
OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS = {
    "dlg_gm01m22_6": {
        "missionId": "gm01m22",
        "filename": "dlg_gm01m22_6_p3D89315D99916D18.json",
        "sha256":
            "CA2DFFCDFCE34A072E22FCECFBDC2FFCD1C0FB6002A6BD699327F4D242CD3FC2",
        "extraConfigFilename":
            "dlg_gm01m22_6_extra_config_pD19B07425E6A1717.json",
        "extraConfigSha256":
            "BC55FA8527B7EEE4459EF8246412DDE3914ACCBE1BB5E1DE72B20EDC1C895790",
        "lineIds": tuple(
            f"dlg_gm01m22_6_{number:03d}" for number in range(1, 17)
        ),
        "optionIds": (
            "option_dlg_gm01m22_6_1_001",
            "option_dlg_gm01m22_6_2_001",
            "option_dlg_gm01m22_6_3_001",
            "option_dlg_gm01m22_6_3_002",
            "option_dlg_gm01m22_6_3_003",
            "option_dlg_gm01m22_6_4_001",
            "option_dlg_gm01m22_6_5_001",
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m22_6_{number:03d}" for number in range(1, 17)
        ),
        "treeBranchGroups": ({
            "optionGroup": 3,
            "optionIds": (
                "option_dlg_gm01m22_6_3_001",
                "option_dlg_gm01m22_6_3_002",
                "option_dlg_gm01m22_6_3_003",
            ),
            "targetLineIds": (
                "dlg_gm01m22_6_007",
                "dlg_gm01m22_6_009",
                "dlg_gm01m22_6_012",
            ),
            "routeKind": "authored_split",
        },),
        "allowedNonOwningRoute": {
            "relation":
                "dialog_tree_prime_reachable_story_playback_dependency",
            "direction": "context",
            "phase": "dialog_tree_prime_reachable_story_playback",
            "confidence":
                "native_exact_prime_reachable_parent_quest_dependency",
            "storyOwnerMission": "gm01m22",
            "parentStoryKey": "dlg_gm01m22_hapo",
            "dependencyOnly": True,
            "ownership": False,
        },
    },
    "dlg_gm01m22_7": {
        "missionId": "gm01m22",
        "filename": "dlg_gm01m22_7_pFC3004E2C86780B5.json",
        "sha256":
            "6252D65C4EB1135192352318C31C2EB50DA3B78CC93FC595F53A904DEB5F156E",
        "extraConfigFilename":
            "dlg_gm01m22_7_extra_config_pE73606718DBFDA95.json",
        "extraConfigSha256":
            "2DFC46F37FC0699C1AA8BF9AFE6F7A5134789E1B222F662F55881B2662C7A4B4",
        "lineIds": (
            "dlg_gm01m22_7_001",
            "dlg_gm01m22_7_002",
        ),
        "optionIds": ("option_dlg_gm01m22_7_1_001",),
        "missingAudioIds": (
            "au_dlg_gm01m22_7_001",
            "au_dlg_gm01m22_7_002",
        ),
        "treeBranchGroups": (),
    },
    "dlg_gm01m22_8": {
        "missionId": "gm01m22",
        "filename": "dlg_gm01m22_8_p0F191D9E6BBFA3DE.json",
        "sha256":
            "D7E5981C915EECF39E6C819DD710369D894AE1AC9840C76C03A940F413FE498F",
        "extraConfigFilename":
            "dlg_gm01m22_8_extra_config_p65B42F5F951203A0.json",
        "extraConfigSha256":
            "B7A7A7319CB6C6D39417A4B138D60CECB1B8E81A3F492A7B8CBA29A2B824D53D",
        "lineIds": tuple(
            f"dlg_gm01m22_8_{number:03d}" for number in range(12, 36)
        ),
        "optionIds": (
            "option_dlg_gm01m22_8_10_001",
            "option_dlg_gm01m22_8_11_001",
            "option_dlg_gm01m22_8_1_001",
            "option_dlg_gm01m22_8_2_001",
            "option_dlg_gm01m22_8_3_001",
            "option_dlg_gm01m22_8_4_001",
            "option_dlg_gm01m22_8_5_001",
            "option_dlg_gm01m22_8_6_001",
            "option_dlg_gm01m22_8_6_002",
            "option_dlg_gm01m22_8_7_001",
            "option_dlg_gm01m22_8_8_001",
            "option_dlg_gm01m22_8_9_001",
            "option_dlg_gm01m22_8_9_002",
            "option_dlg_gm01m22_8_9_003",
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m22_8_{number:03d}" for number in range(12, 36)
        ),
        "treeBranchGroups": ({
            "optionGroup": 6,
            "optionIds": (
                "option_dlg_gm01m22_8_6_001",
                "option_dlg_gm01m22_8_6_002",
            ),
            "targetLineIds": (
                "dlg_gm01m22_8_019",
                "dlg_gm01m22_8_019",
            ),
            "routeKind": "authored_convergence",
        }, {
            "optionGroup": 9,
            "optionIds": (
                "option_dlg_gm01m22_8_9_001",
                "option_dlg_gm01m22_8_9_002",
                "option_dlg_gm01m22_8_9_003",
            ),
            "targetLineIds": (
                "dlg_gm01m22_8_026",
                "dlg_gm01m22_8_028",
                "dlg_gm01m22_8_031",
            ),
            "routeKind": "authored_split",
        }),
        "allowedNonOwningRoute": {
            "relation":
                "dialog_tree_prime_reachable_story_playback_dependency",
            "direction": "context",
            "phase": "dialog_tree_prime_reachable_story_playback",
            "confidence":
                "native_exact_prime_reachable_parent_quest_dependency",
            "storyOwnerMission": "gm01m22",
            "parentStoryKey": "dlg_gm01m22_hapo",
            "dependencyOnly": True,
            "ownership": False,
        },
    },
    "misc_dlg_gm01m22_2d5": {
        "missionId": "gm01m22",
        "registryKey": "dlg_gm01m22_2d5",
        "definitionName": "dlg_gm01m22_2d5",
        "linePrefix": "dlg_gm01m22_2d5",
        "filename": "dlg_gm01m22_2d5_p3781B8823A5F4C76.json",
        "sha256":
            "CD96D9F7AF1B92B457CA3E0C6B769879999FFE6E52982B27CB3239CD401DDB86",
        "extraConfigFilename":
            "dlg_gm01m22_2d5_extra_config_p5A94AF7776AD0C50.json",
        "extraConfigSha256":
            "C465A816C3D918B3CD79B2ED776424E9ED3E068B170101563B870790E66C2DE4",
        "lineIds": (
            "dlg_gm01m22_2d5_001",
            "dlg_gm01m22_2d5_002",
        ),
        "optionIds": (),
        "missingAudioIds": (
            "au_dlg_gm01m22_2d5_001",
            "au_dlg_gm01m22_2d5_002",
        ),
        "treeBranchGroups": (),
        "npcProxyConsumer": {
            "proxyId": "jite_map01_006",
            "entryIndex": 0,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_gm01m22_2d5",
                "missionId": "",
            },
        },
    },
    "misc_dlg_gm01m22_3d2": {
        "missionId": "gm01m22",
        "registryKey": "dlg_gm01m22_3d2",
        "definitionName": "dlg_gm01m22_3d2",
        "linePrefix": "dlg_gm01m22_3d2",
        "filename": "dlg_gm01m22_3d2_pC7E056D5589F1F1A.json",
        "sha256":
            "76AEDDD4D838EBB33E692A9230F6EF2860983766D6BEEF1B00BA44C27DFACA55",
        "extraConfigFilename":
            "dlg_gm01m22_3d2_extra_config_pEE775857FCE0EB6B.json",
        "extraConfigSha256":
            "25FFC45783252E1F5E9491ACD10509E676B2E4BFFFA8025AF3DC682EC1A43A7C",
        "lineIds": tuple(
            f"dlg_gm01m22_3d2_{number:03d}" for number in range(1, 5)
        ),
        "optionIds": (),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m22_3d2_{number:03d}" for number in range(1, 5)
        ),
        "treeBranchGroups": (),
    },
    "misc_dlg_gm01m22_3d8": {
        "missionId": "gm01m22",
        "registryKey": "dlg_gm01m22_3d8",
        "definitionName": "dlg_gm01m22_3d8",
        "linePrefix": "dlg_gm01m22_3d8",
        "filename": "dlg_gm01m22_3d8_p23E8C43668908CF2.json",
        "sha256":
            "C1EC6771847955296FA04978C397C1CD50D62D4C0178A205030A7D7D8E7B2B08",
        "extraConfigFilename":
            "dlg_gm01m22_3d8_extra_config_pB63AD6D3EACA7E49.json",
        "extraConfigSha256":
            "536D68369BADFEEC9204CF934591494E2DBAADB537AB3617CF88A25AD83703C1",
        "lineIds": (
            "dlg_gm01m22_3d8_002",
            "dlg_gm01m22_3d8_003",
            "dlg_gm01m22_3d8_004",
        ),
        "optionIds": (),
        "missingAudioIds": (
            "au_dlg_gm01m22_3d8_002",
            "au_dlg_gm01m22_3d8_003",
            "au_dlg_gm01m22_3d8_004",
        ),
        "treeBranchGroups": (),
    },
    "misc_dlg_gm01m22_4d0": {
        "missionId": "gm01m22",
        "registryKey": "dlg_gm01m22_4d0",
        "definitionName": "dlg_gm01m22_4d0",
        "linePrefix": "dlg_gm01m22_4d0",
        "filename": "dlg_gm01m22_4d0_p99B63749393B3E23.json",
        "sha256":
            "C2D8E1542AD52D7C342BEEB7A910298DAB9E31EE2B81285275FFEE369998DF77",
        "extraConfigFilename":
            "dlg_gm01m22_4d0_extra_config_p6664D02E215DC570.json",
        "extraConfigSha256":
            "978E5A1304D040015B201F0E7A0329B33C1FEFC48BBF7984B7BEF0E800D3598E",
        "lineIds": ("dlg_gm01m22_4d0_002",),
        "optionIds": (),
        "missingAudioIds": ("au_dlg_gm01m22_4d0_002",),
        "treeBranchGroups": (),
    },
    "dlg_gm01m6_6": {
        "missionId": "gm01m6",
        "filename": "dlg_gm01m6_6_pEAAF7ACAF314A409.json",
        "sha256":
            "97B366CECDC24CCEED4BC3F583A9D3A69775A704EAF35987303FEAC354AB7F3E",
        "extraConfigFilename":
            "dlg_gm01m6_6_extra_config_p62FB4BC8D39CC6AF.json",
        "extraConfigSha256":
            "805103584399CE5D828BEF1E74550FB367F4E81FCE868112392DF03E21E3F64F",
        "lineIds": ("dlg_gm01m6_6_001", "dlg_gm01m6_6_002"),
        "optionIds": (),
        "missingAudioIds": (
            "au_dlg_gm01m6_6_001",
            "au_dlg_gm01m6_6_002",
        ),
        "treeBranchGroups": (),
        "npcProxyConsumer": {
            "proxyId": "heerman_map01_default",
            "entryIndex": 1,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_gm01m6_6",
                "missionId": "",
            },
        },
        "missionNpcProxyTracking": {
            "sourceFile": (
                "export_full/structured/Persistent/Data/Json/"
                "MissionRuntimeAsset/gm01m6.json"
            ),
            "sourceSha256":
                "210142C46704FA160B2397BB48A78EC989D6BEF04D029AEB17A6FF745CC8DBF7",
            "proxyId": "heerman_map01_default",
            "levelId": "map01_lv006",
            "rows": ({
                "questId": "gm01m6_q#12",
                "objectiveIndex": 0,
                "trackingIndex": 0,
            },),
        },
    },
    "dlg_gm01m6_7": {
        "missionId": "gm01m6",
        "filename": "dlg_gm01m6_7_p321590FA5ABC5DEE.json",
        "sha256":
            "68411E1779C71BB1264EE32B04A57B90641DB1BD02E99C37DCD8ABCBBE3754AD",
        "extraConfigFilename":
            "dlg_gm01m6_7_extra_config_p7764E80EA5AC8B0F.json",
        "extraConfigSha256":
            "9734F2AD1E39B269A7DDDE806DB070ADBD4482406EFD85DA10245662F5C44346",
        "lineIds": ("dlg_gm01m6_7_001", "dlg_gm01m6_7_002"),
        "optionIds": ("option_dlg_gm01m6_7_1_001",),
        "missingAudioIds": (
            "au_dlg_gm01m6_7_001",
            "au_dlg_gm01m6_7_002",
        ),
        "treeBranchGroups": (),
        "npcProxyConsumer": {
            "proxyId": "sikete_map01_default",
            "entryIndex": 0,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_gm01m6_7",
                "missionId": "",
            },
        },
    },
    "misc_dlg_gm01m6_1d5": {
        "missionId": "gm01m6",
        "registryKey": "dlg_gm01m6_1d5",
        "definitionName": "dlg_gm01m6_1d5",
        "linePrefix": "dlg_gm01m6_1d5",
        "filename": "dlg_gm01m6_1d5_p0DD18C793D122156.json",
        "sha256":
            "C72DE1DC8C052111DF4CEFB908C32E064290D4312AD3E78CAE6A2AE21DC06BFC",
        "extraConfigFilename":
            "dlg_gm01m6_1d5_extra_config_p6FEA6F24042A77B9.json",
        "extraConfigSha256":
            "7005182628D0AD82094AAF29855DE0CDDC318B7FE3F0A132A424F0C2DB2B4719",
        "lineIds": ("dlg_gm01m6_1d5_001",),
        "optionIds": (),
        "missingAudioIds": ("au_dlg_gm01m6_1d5_001",),
        "treeBranchGroups": (),
    },
    "misc_dlg_gm01m6_3d7": {
        "missionId": "gm01m6",
        "registryKey": "dlg_gm01m6_3d7",
        "definitionName": "dlg_gm01m6_3d7",
        "linePrefix": "dlg_gm01m6_3d7",
        "filename": "dlg_gm01m6_3d7_pA32C176F716FBCC1.json",
        "sha256":
            "FAFC48AB767F01FB0F3AE0C47468A5F232AE9824714226FF6A32A73F6D37AE76",
        "extraConfigFilename":
            "dlg_gm01m6_3d7_extra_config_p51952F8858F44E85.json",
        "extraConfigSha256":
            "A0048DEF39A1560B749F5B2E160B23802B4CAE9AF56730B915C34852530E5DE8",
        "lineIds": (
            "dlg_gm01m6_3d7_001",
            "dlg_gm01m6_3d7_002",
        ),
        "optionIds": ("option_dlg_gm01m6_3d7_1_001",),
        "missingAudioIds": (
            "au_dlg_gm01m6_3d7_001",
            "au_dlg_gm01m6_3d7_002",
        ),
        "treeBranchGroups": (),
        "npcProxyConsumer": {
            "proxyId": "heerman_map01_001",
            "entryIndex": 3,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_gm01m6_3d7",
                "missionId": "",
            },
        },
        "missionNpcProxyTracking": {
            "sourceFile": (
                "export_full/structured/Persistent/Data/Json/"
                "MissionRuntimeAsset/gm01m6.json"
            ),
            "sourceSha256":
                "210142C46704FA160B2397BB48A78EC989D6BEF04D029AEB17A6FF745CC8DBF7",
            "proxyId": "heerman_map01_001",
            "levelId": "map01_lv006",
            "rows": (
                {
                    "questId": "gm01m6_q#3",
                    "objectiveIndex": 0,
                    "trackingIndex": 0,
                },
                {
                    "questId": "gm01m6_q#10",
                    "objectiveIndex": 0,
                    "trackingIndex": 0,
                },
            ),
        },
    },
    "misc_dlg_gm01m6_4d5": {
        "missionId": "gm01m6",
        "registryKey": "dlg_gm01m6_4d5",
        "definitionName": "dlg_gm01m6_4d5",
        "linePrefix": "dlg_gm01m6_4d5",
        "filename": "dlg_gm01m6_4d5_p85775DE3FF157C61.json",
        "sha256":
            "177E8CEFB4414EFB096D4F182C1C30A68C339DBA25E5C8A636F970DAD906BBB8",
        "extraConfigFilename":
            "dlg_gm01m6_4d5_extra_config_p9965F84865FB6738.json",
        "extraConfigSha256":
            "662331DC8914C802E8710F7D384C013614241A16D9B1A4BB73DD000672906635",
        "lineIds": ("dlg_gm01m6_4d5_001",),
        "optionIds": ("option_dlg_gm01m6_4d5_1_001",),
        "missingAudioIds": ("au_dlg_gm01m6_4d5_001",),
        "treeBranchGroups": (),
        "npcProxyConsumer": {
            "proxyId": "heerman_map01_002",
            "entryIndex": 0,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_gm01m6_4d5",
                "missionId": "",
            },
        },
    },
    "misc_dlg_gm01m6_4d7": {
        "missionId": "gm01m6",
        "registryKey": "dlg_gm01m6_4d7",
        "definitionName": "dlg_gm01m6_4d7",
        "linePrefix": "dlg_gm01m6_4d7",
        "filename": "dlg_gm01m6_4d7_pA978A915C7F0E3C4.json",
        "sha256":
            "F5F6B421362EA8795D6F1721F07833F534CA3A9C1170494CF61FA73E4CE99E4A",
        "extraConfigFilename":
            "dlg_gm01m6_4d7_extra_config_p98E21661A5F3E7E5.json",
        "extraConfigSha256":
            "780DE6BE430457BE24686F3F81EDC9C049FC7DA4FA0F77ED52315BBC0F779F06",
        "lineIds": ("dlg_gm01m6_4d7_001",),
        "optionIds": (),
        "missingAudioIds": ("au_dlg_gm01m6_4d7_001",),
        "treeBranchGroups": (),
        "npcProxyConsumer": {
            "proxyId": "sikete_map01_002",
            "entryIndex": 0,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_gm01m6_4d7",
                "missionId": "",
            },
        },
    },
    "dlg_gm01m7_1": {
        "missionId": "gm01m7",
        "filename": "dlg_gm01m7_1_p4C33EC5A99345897.json",
        "sha256":
            "998E254B83630E2B8700A75D7A2F5EC33BD3E2866AC2FECB137A8FC24A9750CA",
        "extraConfigFilename":
            "dlg_gm01m7_1_extra_config_p6FC81A3430523880.json",
        "extraConfigSha256":
            "1A8F0A25C791C565A58E6E128AB4A8CD3FA879411379FF4A32BDEA41BF7356AA",
        "lineIds": tuple(
            f"dlg_gm01m7_1_{number:03d}" for number in range(1, 9)
        ),
        "optionIds": (
            "option_dlg_gm01m7_1_1_001",
            "option_dlg_gm01m7_1_1_002",
            "option_dlg_gm01m7_1_2_001",
            "option_dlg_gm01m7_1_2_002",
            "option_dlg_gm01m7_1_3_001",
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m7_1_{number:03d}" for number in range(1, 9)
        ),
        "treeBranchGroups": (
            {
                "optionGroup": 1,
                "optionIds": (
                    "option_dlg_gm01m7_1_1_001",
                    "option_dlg_gm01m7_1_1_002",
                ),
                "targetLineIds": (
                    "dlg_gm01m7_1_003",
                    "dlg_gm01m7_1_004",
                ),
                "routeKind": "authored_split",
            },
            {
                "optionGroup": 2,
                "optionIds": (
                    "option_dlg_gm01m7_1_2_001",
                    "option_dlg_gm01m7_1_2_002",
                ),
                "targetLineIds": (
                    "dlg_gm01m7_1_006",
                    "dlg_gm01m7_1_006",
                ),
                "routeKind": "authored_convergence",
            },
        ),
        "npcProxyConsumer": {
            "proxyId": "sesidun_map01_003",
            "entryIndex": 0,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_gm01m7_1",
            },
        },
        "missionNpcProxyTracking": {
            "sourceFile": (
                "export_full/structured/Persistent/Data/Json/"
                "MissionRuntimeAsset/gm01m12.json"
            ),
            "sourceSha256":
                "B5022E18326385BCCCC4ACFBC076A5563C5B18066D291D1CA63F2DB11AC12EBB",
            "runtimeMissionId": "gm01m12",
            "proxyId": "sesidun_map01_003",
            "levelId": "map01_lv001",
            "rows": ({
                "questId": "gm01m12_q#14",
                "objectiveIndex": 0,
                "trackingIndex": 0,
            },),
        },
    },
    "dlg_gm01m7_2": {
        "missionId": "gm01m7",
        "filename": "dlg_gm01m7_2_pD803554221ADE07D.json",
        "sha256":
            "4E8A6F6B34B407FD79417ACE3E616C923E20AD2C51EA5FC812A9FDA53A4B1FBF",
        "extraConfigFilename":
            "dlg_gm01m7_2_extra_config_p7FB3078E3CB4CCE7.json",
        "extraConfigSha256":
            "8FE5E44DDA7B7A4FC87CC30339DBB2759F6251B9C9AFAABD63A7ADCD51763307",
        "lineIds": tuple(
            f"dlg_gm01m7_2_{number:03d}" for number in range(1, 4)
        ),
        "optionIds": (
            "option_dlg_gm01m7_2_1_001",
            "option_dlg_gm01m7_2_2_001",
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m7_2_{number:03d}" for number in range(1, 4)
        ),
        "treeBranchGroups": (),
        "npcProxyConsumers": (
            {
                "proxyId": "sesidun_map01_002",
                "entryIndex": 2,
                "entry": {
                    "addDialogExOption": False,
                    "envTalkData": {"envTalkOverrideNpc": True},
                    "dialogExOptionData": [],
                    "dialogId": "dlg_gm01m7_2",
                },
            },
            {
                "proxyId": "wolfgd_map01_gm01m12",
                "entryIndex": 1,
                "entry": {
                    "addDialogExOption": False,
                    "envTalkData": {"envTalkOverrideNpc": True},
                    "dialogExOptionData": [],
                    "dialogId": "dlg_gm01m7_2",
                },
            },
        ),
        "missionNpcProxyTracking": {
            "sourceFile": (
                "export_full/structured/Persistent/Data/Json/"
                "MissionRuntimeAsset/gm01m12.json"
            ),
            "sourceSha256":
                "B5022E18326385BCCCC4ACFBC076A5563C5B18066D291D1CA63F2DB11AC12EBB",
            "runtimeMissionId": "gm01m12",
            "proxyId": "wolfgd_map01_gm01m12",
            "levelId": "map01_lv005",
            "rows": tuple({
                "questId": f"gm01m12_q#{number}",
                "objectiveIndex": 0,
                "trackingIndex": 0,
            } for number in (2, 3, 4, 6, 12)),
        },
    },
    "dlg_gm01m7_3": {
        "missionId": "gm01m7",
        "filename": "dlg_gm01m7_3_p7B822F2AE7CE59D1.json",
        "sha256":
            "945AA4C8AE7B5E183660F7701D26316F575434C903F9CDEB36F49A4D0ED46BC4",
        "extraConfigFilename":
            "dlg_gm01m7_3_extra_config_p09B245131C13EFC6.json",
        "extraConfigSha256":
            "2408FD841987D0D2B4AB5D1E023C97B1C86D19EBC4B1B03C167DB97A8C602450",
        "lineIds": (
            "dlg_gm01m7_3_001",
            "dlg_gm01m7_3_003",
            "dlg_gm01m7_3_004",
        ),
        "optionIds": tuple(
            f"option_dlg_gm01m7_3_1_{number:03d}"
            for number in range(1, 4)
        ),
        "missingAudioIds": (
            "au_dlg_gm01m7_3_001",
            "au_dlg_gm01m7_3_003",
            "au_dlg_gm01m7_3_004",
        ),
        "treeBranchGroups": ({
            "optionGroup": 1,
            "optionIds": tuple(
                f"option_dlg_gm01m7_3_1_{number:03d}"
                for number in range(1, 4)
            ),
            "targetLineIds": ("dlg_gm01m7_3_003",) * 3,
            "routeKind": "authored_convergence",
        },),
        "npcProxyConsumers": (
            {
                "proxyId": "sesidun_map01_002",
                "entryIndex": 3,
                "entry": {
                    "addDialogExOption": False,
                    "envTalkData": {"envTalkOverrideNpc": True},
                    "dialogExOptionData": [],
                    "dialogId": "dlg_gm01m7_3",
                },
            },
            {
                "proxyId": "wolfgd_map01_gm01m12",
                "entryIndex": 2,
                "entry": {
                    "addDialogExOption": False,
                    "envTalkData": {"envTalkOverrideNpc": True},
                    "dialogExOptionData": [],
                    "dialogId": "dlg_gm01m7_3",
                },
            },
        ),
        "missionNpcProxyTracking": {
            "sourceFile": (
                "export_full/structured/Persistent/Data/Json/"
                "MissionRuntimeAsset/gm01m12.json"
            ),
            "sourceSha256":
                "B5022E18326385BCCCC4ACFBC076A5563C5B18066D291D1CA63F2DB11AC12EBB",
            "runtimeMissionId": "gm01m12",
            "proxyId": "wolfgd_map01_gm01m12",
            "levelId": "map01_lv005",
            "rows": tuple({
                "questId": f"gm01m12_q#{number}",
                "objectiveIndex": 0,
                "trackingIndex": 0,
            } for number in (2, 3, 4, 6, 12)),
        },
    },
    "dlg_gm01m7_5": {
        "missionId": "gm01m7",
        "filename": "dlg_gm01m7_5_pAD342EBDE8DCA8CA.json",
        "sha256":
            "921AF0A4051FDD9E058CE0B64951AFC1793FBDE4189053576F9E0FF0F2279273",
        "extraConfigFilename":
            "dlg_gm01m7_5_extra_config_pA42F6859B58AA126.json",
        "extraConfigSha256":
            "FB3A4B5CB7A823C728EEB833569DB733A9C81E6E2ED94CDB247C616132427B16",
        "lineIds": tuple(
            f"dlg_gm01m7_5_{number:03d}" for number in range(1, 14)
        ),
        "optionIds": (
            "option_dlg_gm01m7_5_1_001",
            "option_dlg_gm01m7_5_2_001",
            "option_dlg_gm01m7_5_3_001",
            "option_dlg_gm01m7_5_4_001",
            "option_dlg_gm01m7_5_4_002",
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m7_5_{number:03d}" for number in range(1, 14)
        ),
        "treeBranchGroups": ({
            "optionGroup": 4,
            "optionIds": (
                "option_dlg_gm01m7_5_4_001",
                "option_dlg_gm01m7_5_4_002",
            ),
            "targetLineIds": ("dlg_gm01m7_5_012",) * 2,
            "routeKind": "authored_convergence",
        },),
        "npcProxyConsumers": (
            {
                "proxyId": "sesidun_map01_002",
                "entryIndex": 1,
                "entry": {
                    "addDialogExOption": False,
                    "envTalkData": {"envTalkOverrideNpc": True},
                    "dialogExOptionData": [],
                    "dialogId": "dlg_gm01m7_5",
                },
            },
            {
                "proxyId": "wolfgd_map01_gm01m12",
                "entryIndex": 3,
                "entry": {
                    "addDialogExOption": False,
                    "envTalkData": {"envTalkOverrideNpc": True},
                    "dialogExOptionData": [],
                    "dialogId": "dlg_gm01m7_5",
                },
            },
        ),
        "missionNpcProxyTracking": {
            "sourceFile": (
                "export_full/structured/Persistent/Data/Json/"
                "MissionRuntimeAsset/gm01m12.json"
            ),
            "sourceSha256":
                "B5022E18326385BCCCC4ACFBC076A5563C5B18066D291D1CA63F2DB11AC12EBB",
            "runtimeMissionId": "gm01m12",
            "proxyId": "wolfgd_map01_gm01m12",
            "levelId": "map01_lv005",
            "rows": tuple({
                "questId": f"gm01m12_q#{number}",
                "objectiveIndex": 0,
                "trackingIndex": 0,
            } for number in (2, 3, 4, 6, 12)),
        },
    },
    "dlg_gm01m7_7": {
        "missionId": "gm01m7",
        "filename": "dlg_gm01m7_7_p329466434333CE69.json",
        "sha256":
            "DB9A42693B48EE4C8D003CFC54457C97A6945A08F25145A4812D13DB3AB657E0",
        "extraConfigFilename":
            "dlg_gm01m7_7_extra_config_p325DF5E5D79CB0E7.json",
        "extraConfigSha256":
            "A4F855C5E8181B6DA3ABE10AA5CC65291B1D3556EF1B3FB44D2BAD7D980E47C1",
        "lineIds": tuple(
            f"dlg_gm01m7_7_{number:03d}" for number in range(1, 4)
        ),
        "optionIds": ("option_dlg_gm01m7_7_1_001",),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m7_7_{number:03d}" for number in range(1, 4)
        ),
        "treeBranchGroups": (),
        "npcProxyConsumer": {
            "proxyId": "wolfgd_map01_gm01m12",
            "entryIndex": 4,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_gm01m7_7",
            },
        },
        "missionNpcProxyTracking": {
            "sourceFile": (
                "export_full/structured/Persistent/Data/Json/"
                "MissionRuntimeAsset/gm01m12.json"
            ),
            "sourceSha256":
                "B5022E18326385BCCCC4ACFBC076A5563C5B18066D291D1CA63F2DB11AC12EBB",
            "runtimeMissionId": "gm01m12",
            "proxyId": "wolfgd_map01_gm01m12",
            "levelId": "map01_lv005",
            "rows": tuple({
                "questId": f"gm01m12_q#{number}",
                "objectiveIndex": 0,
                "trackingIndex": 0,
            } for number in (2, 3, 4, 6, 12)),
        },
    },
    "dlg_a1m2_4": {
        "missionId": "a1m2",
        "filename": "dlg_a1m2_4_p23BC729FEA1147B6.json",
        "sha256":
            "5F44A1771081047DBA74251FF20833DCAF5791C572449814B02E8F7310EFA364",
        "extraConfigFilename":
            "dlg_a1m2_4_extra_config_p204ACA7058EBE31A.json",
        "extraConfigSha256":
            "32E0B431B9FAAF96424F5028055EA3E9FBE075201903FE950C7EE29DC73B303E",
        "lineIds": tuple(
            f"dlg_a1m2_4_{number:03d}" for number in range(1, 4)
        ),
        "optionIds": (
            "option_dlg_a1m2_4_1_001",
            "option_dlg_a1m2_4_1_002",
        ),
        "missingAudioIds": tuple(
            f"au_dlg_a1m2_4_{number:03d}" for number in range(1, 4)
        ),
        "npcProxyConsumer": {
            "proxyId": "kelala_map01_v1d1d0_005",
            "entryIndex": 0,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {
                    "envTalkIds": [],
                    "envTalkOdd": [],
                    "envTalkOverrideNpc": True,
                },
                "dialogExOptionData": [],
                "dialogId": "dlg_a1m2_4",
                "missionId": "",
            },
        },
    },
    "dlg_a1m8d3_2": {
        "missionId": "a1m8d3",
        "filename": "dlg_a1m8d3_2_p9BCBAF7FB96B40D2.json",
        "sha256":
            "8CBA037D2AFEE68BA6E171EE6BADFE82BCBBC348C70FE3A8C556EECE9AA64136",
        "extraConfigFilename":
            "dlg_a1m8d3_2_extra_config_pAF2E11B8A59BE74B.json",
        "extraConfigSha256":
            "F27D2AF4365E5769D5B93C1E5DBCFE67FCCFAA0A1141A10271E55769D6823C76",
        "lineIds": tuple(
            f"dlg_a1m8d3_2_{number:03d}" for number in range(2, 20)
        ),
        "optionIds": (
            "option_dlg_a1m8d3_2_1_001",
            "option_dlg_a1m8d3_2_2_001",
        ),
        "missingAudioIds": tuple(
            f"au_dlg_a1m8d3_2_{number:03d}" for number in range(2, 20)
        ),
    },
    "dlg_e5m0d5_1": {
        "missionId": "e5m0d5",
        "filename": "dlg_e5m0d5_1_pAF0BBC8AD9824BE9.json",
        "sha256":
            "81353788DEDAEB34DF4DD05C5940ED0831DEE2D57A12A2CC996C559E96885A4B",
        "extraConfigFilename":
            "dlg_e5m0d5_1_extra_config_p6D91A9314ED0DB83.json",
        "extraConfigSha256":
            "CE90DD0CD2C1DA8EE9478C8D16D01586205AB1F9E4E3F207A5E5252ED95E08F9",
        "lineIds": tuple(
            f"dlg_e5m0d5_1_{number:03d}" for number in range(1, 15)
        ),
        "optionIds": (),
        "ownedTimeline": {
            "timeline": "dlgtl_e5m0d5_1_sub_1",
            "sourceFile": "CAB-80a46b02bcb42629e533be06211f6e5f",
            "trackPathId": 3386777180023897082,
            "fullLineIds": tuple(
                f"dlg_e5m0d5_1_{number:03d}"
                for number in range(1, 15)
            ),
        },
    },
    "dlg_e11m8d5_1": {
        "missionId": "e11m8d5",
        "filename": "dlg_e11m8d5_1_pD376152BDDDA1FBD.json",
        "sha256":
            "F119A842BD1328FD3908D264E616CAF3BE1E0231E8875AC1779793963EE76DD2",
        "extraConfigFilename":
            "dlg_e11m8d5_1_extra_config_pC0736E349974AB51.json",
        "extraConfigSha256":
            "0CA91C4AC4CB6BC1F28870C09B3D1F59B55BBD347334735B6DB725594A6FF7AB",
        "lineIds": tuple(
            f"dlg_e11m8d5_1_{number:03d}" for number in range(1, 11)
        ),
        "optionIds": (
            "option_dlg_e11m8d5_1_1_001",
            "option_dlg_e11m8d5_1_1_002",
        ),
        "missingAudioIds": tuple(
            f"au_dlg_e11m8d5_1_{number:03d}" for number in range(1, 11)
        ),
        "npcProxyConsumer": {
            "proxyId": "lizy_map02_v1d4d0_world",
            "entryIndex": 0,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {
                    "envTalkIds": [],
                    "envTalkOdd": [],
                    "envTalkOverrideNpc": True,
                },
                "dialogExOptionData": [],
                "dialogId": "dlg_e11m8d5_1",
                "missionId": "",
            },
        },
    },
    "dlg_e2m8d5_2": {
        "missionId": "e2m8d5",
        "filename": "dlg_e2m8d5_2_p40FE1FD84FBFFF67.json",
        "sha256":
            "6144278E2A7FB2E292C29E9B826C7914570908F29EDC3C5920ED94080A111705",
        "extraConfigFilename":
            "dlg_e2m8d5_2_extra_config_p3B9E851FEEA7D1DC.json",
        "extraConfigSha256":
            "53C9F005CCEB3F6BDF26FC633F958CC60FB17F3FA572A74E90BD89208B6389A5",
        "lineIds": (
            "dlg_e2m8d5_2_001",
            "dlg_e2m8d5_2_002",
            "dlg_e2m8d5_2_004",
            "dlg_e2m8d5_2_006",
            "dlg_e2m8d5_2_007",
        ),
        "optionIds": (
            "option_dlg_e2m8d5_2_1_001",
            "option_dlg_e2m8d5_2_1_002",
        ),
        "npcProxyConsumer": {
            "proxyId": "pelica_map01_e2m8d5",
            "entryIndex": 2,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_e2m8d5_2",
            },
        },
    },
    "dlg_e2m8d5_3": {
        "missionId": "e2m8d5",
        "filename": "dlg_e2m8d5_3_p66A773A94C4A1029.json",
        "sha256":
            "8C5B6620298DE24694E13761A79A91E716FE8F985A4C4DD0C32B8FFF12F747D8",
        "extraConfigFilename":
            "dlg_e2m8d5_3_extra_config_pC4EE4C59F6880FB3.json",
        "extraConfigSha256":
            "78B0AD444399ED453180D29741AD9772A6D4065CD7E62C318256EC2F81D03912",
        "lineIds": tuple(
            f"dlg_e2m8d5_3_{number:03d}" for number in range(1, 6)
        ),
        "optionIds": ("option_dlg_e2m8d5_3_1_001",),
        "npcProxyConsumer": {
            "proxyId": "chen_map01_e2m8d5",
            "entryIndex": 0,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_e2m8d5_3",
                "missionId": "",
            },
        },
    },
    "misc_dlg_e2m5d5_1d5": {
        "missionId": "e2m5d5",
        "registryKey": "dlg_e2m5d5_1d5",
        "definitionName": "dlg_e2m5d5_1d5",
        "linePrefix": "dlg_e2m5d5_1d5",
        "filename": "dlg_e2m5d5_1d5_p283CA25C97A4E526.json",
        "sha256":
            "D07E14840CF2D9ACFC6187192D5894B509EAAB4B84AA6D366B0D25FBFB8E5B6E",
        "extraConfigFilename":
            "dlg_e2m5d5_1d5_extra_config_p1E57E3CC2B4FADEA.json",
        "extraConfigSha256":
            "6392019E5E7A21100A59979C2A2073A7785437ED910359246140C6BEB45DA091",
        "lineIds": (
            "dlg_e2m5d5_1d5_001",
            "dlg_e2m5d5_1d5_002",
            "dlg_e2m5d5_1d5_003",
        ),
        "optionIds": (),
        "npcProxyConsumer": {
            "proxyId": "pelica_map01_e2m5d5",
            "entryIndex": 0,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_e2m5d5_1d5",
            },
        },
    },
    "misc_dlg_e2m5d5_1d7": {
        "missionId": "e2m5d5",
        "registryKey": "dlg_e2m5d5_1d7",
        "definitionName": "dlg_e2m5d5_1d7",
        "linePrefix": "dlg_e2m5d5_1d7",
        "filename": "dlg_e2m5d5_1d7_p59A1D0106995688C.json",
        "sha256":
            "F6FBCFE421574591313153C98087B27EAB5F75F48663BD6D97C40B9D139F6ECE",
        "extraConfigFilename":
            "dlg_e2m5d5_1d7_extra_config_pE56AFA56FF7D7F1E.json",
        "extraConfigSha256":
            "D7700F7906D8FB76631353ED6B34AAB0D87C73D940B0E35A305F0095ABE77ADD",
        "lineIds": tuple(
            f"dlg_e2m5d5_1d7_{number:03d}" for number in range(1, 6)
        ),
        "optionIds": (),
        "npcProxyConsumer": {
            "proxyId": "chen_map01_e2m5d5",
            "entryIndex": 0,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_e2m5d5_1d7",
                "missionId": "",
            },
        },
    },
    "dlg_e8m5_6": {
        "missionId": "e8m5",
        "filename": "dlg_e8m5_6_p1798BED17504D95D.json",
        "sha256":
            "F17952247DD0743990DE8E19C956B29800FCA7F053A71881B275AD391C707ECB",
        "extraConfigFilename":
            "dlg_e8m5_6_extra_config_p282BF1B166503A76.json",
        "extraConfigSha256":
            "5C8AB8C0D60704ED8687FD386371CF9E723C3B74718079185DF520079FE91805",
        "lineIds": (
            "dlg_e8m5_6_001",
            "dlg_e8m5_6_002",
        ),
        "optionIds": (),
        "ownedTimeline": {
            "timeline": "dlgtl_e8m5_6_sub_1",
            "sourceFile": "CAB-42aad6a7bfd8d23c4e3f6c1e0d515744",
            "trackPathId": -7243836360867709977,
            "fullLineIds": (
                "dlg_e8m5_6_001",
                "dlg_e8m5_6_002",
            ),
        },
    },
    "dlg_e10m2_8": {
        "missionId": "e10m2",
        "filename": "dlg_e10m2_8_p8F2AEBCBA2C91D5B.json",
        "sha256":
            "928A56F6901AD60BA2D7F2CC598EF88DDDFF614F14A803F0A588E9188C2217F5",
        "extraConfigFilename":
            "dlg_e10m2_8_extra_config_p38D17B98E4C62C52.json",
        "extraConfigSha256":
            "AE0E94E927ED9CBE169C0237078AC18290979CE25EE628FF1269F73E6860E928",
        "lineIds": ("dlg_e10m2_8_001",),
        "optionIds": (),
    },
    "dlg_e8m1_10": {
        "missionId": "e8m1",
        "filename": "dlg_e8m1_10_p76A11D6AD289E50D.json",
        "sha256":
            "F4D8E2C6239F68FBF4282D175FD50AD634EE1ADBF657D79CA33715323D5B2055",
        "extraConfigFilename":
            "dlg_e8m1_10_extra_config_p02314CA91CB6C920.json",
        "extraConfigSha256":
            "563DADBDA67EB2735FF7A1503E734C496296535B79419ED6C1FD48959F901E97",
        "lineIds": tuple(
            f"dlg_e8m1_10_{number:03d}" for number in range(1, 14)
        ),
        "optionIds": tuple(
            f"option_dlg_e8m1_10_1_{number:03d}"
            for number in range(1, 6)
        ),
        "npcProxyConsumer": {
            "proxyId": "ximo_map02_default",
            "entryIndex": 0,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_e8m1_10",
                "missionId": "",
            },
        },
    },
    "misc_dlg_e1m10_2d7": {
        "missionId": "e1m10",
        "registryKey": "dlg_e1m10_2d7",
        "definitionName": "dlg_e1m10_2d7",
        "linePrefix": "dlg_e1m10_2d7",
        "filename": "dlg_e1m10_2d7_pAF0815267196C2D1.json",
        "sha256":
            "B13AB9764A768CF2DA34DCBCD5BF3050480118267BE06E8BBD2B5DA1E7A74C50",
        "extraConfigFilename":
            "dlg_e1m10_2d7_extra_config_p86362B97C91C7811.json",
        "extraConfigSha256":
            "BC62FC59A605E61C09A3BC90199A85BE20993469B81C6A11C97B5E2A2DEDE74D",
        "lineIds": (
            "dlg_e1m10_2d7_001",
            "dlg_e1m10_2d7_002",
            "dlg_e1m10_2d7_003",
            "dlg_e1m10_2d7_005",
            "dlg_e1m10_2d7_006",
            "dlg_e1m10_2d7_007",
        ),
        "optionIds": (),
    },
    "dlg_e1m2_6": {
        "missionId": "e1m2",
        "filename": "dlg_e1m2_6_p907BD8F50D35BD49.json",
        "sha256":
            "9C07D0344F9A810357826D4911072314EEC62233C2E8BCF1395A70B2CAB7883F",
        "extraConfigFilename":
            "dlg_e1m2_6_extra_config_pA8612C99DE845E7C.json",
        "extraConfigSha256":
            "89B14D65387F1567990671228000339E8AEC0EE76D7529324C3AD2204F490D48",
        "lineIds": tuple(
            f"dlg_e1m2_6_{number:03d}" for number in range(1, 5)
        ),
        "optionIds": ("option_dlg_e1m2_6_1_001",),
        "npcProxyConsumer": {
            "proxyId": "chen_map01_e1m2Factory",
            "entryIndex": 0,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_e1m2_6",
                "missionId": "",
            },
        },
    },
    "dlg_e1m1_6": {
        "missionId": "e1m1",
        "filename": "dlg_e1m1_6_p90B20316D58C764A.json",
        "sha256":
            "9696F301E71FAA3350DD30612CA5C00A6D2F49635E501219AA03D3E5E4F7BCE0",
        "extraConfigFilename":
            "dlg_e1m1_6_extra_config_pDCB49B20E5F08D9B.json",
        "extraConfigSha256":
            "94B7CCDF409671461EBA12616DB65D27C18D9C00269142DFF5E999ABDDAFE218",
        "lineIds": tuple(
            f"dlg_e1m1_6_{number:03d}" for number in range(1, 6)
        ),
        "optionIds": (),
        "npcProxyConsumer": {
            "proxyId": "chen_map01_e1m1Basement1",
            "entryIndex": 0,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_e1m1_6",
                "missionId": "",
            },
        },
    },
    "dlg_e6m2_1": {
        "missionId": "e6m2",
        "filename": "dlg_e6m2_1_p333D254D69A4BEB6.json",
        "sha256":
            "7B698B34BADDCAB684F63B4AF04B5DBE10287D1C1BABF481CB43991D4B845CF0",
        "extraConfigFilename":
            "dlg_e6m2_1_extra_config_pC9185BD9CBF1B1E1.json",
        "extraConfigSha256":
            "28FEA34339E89F33DC929B7E5F24D961BF20577EB53A3A18F41FDB8C9194B795",
        "lineIds": tuple(
            f"dlg_e6m2_1_{number:03d}" for number in range(1, 18)
        ),
        "optionIds": tuple(
            f"option_dlg_e6m2_1_1_{number:03d}"
            for number in range(1, 6)
        ),
        "npcProxyConsumer": {
            "proxyId": "zhuangfy_indie_dg005_e6m1Final",
            "entryIndex": 0,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_e6m2_1",
                "missionId": "",
            },
        },
    },
    "dlg_e6m2_2": {
        "missionId": "e6m2",
        "filename": "dlg_e6m2_2_pFACA10BA2A38E87A.json",
        "sha256":
            "F64F6C648C9FAD2ADD45BF9957D3F1DE351DA2494092BBAE6BFA3258EFFEB916",
        "extraConfigFilename":
            "dlg_e6m2_2_extra_config_p2D93C81BDF39CE10.json",
        "extraConfigSha256":
            "840A16AFEC6D09C25976CF00AE335BE4D1A0024CC7EF74CCDF2FE08A6B5FD039",
        "lineIds": (
            "dlg_e6m2_2_001",
            "dlg_e6m2_2_003",
            "dlg_e6m2_2_004",
            "dlg_e6m2_2_005",
            "dlg_e6m2_2_006",
            "dlg_e6m2_2_007",
        ),
        "optionIds": (
            "option_dlg_e6m2_2_2_001",
            "option_dlg_e6m2_2_2_002",
        ),
        "npcProxyConsumer": {
            "proxyId": "mifu_indie_dg005_e6m1DianTiKou",
            "entryIndex": 2,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_e6m2_2",
            },
        },
    },
    "dlg_e9m4_14": {
        "missionId": "e9m4",
        "filename": "dlg_e9m4_14_p768B8CEABD032004.json",
        "sha256":
            "7C77CD38377045DC4D90698CA6DBB8A21F029240F6D035295817AB1D2A1513A8",
        "extraConfigFilename":
            "dlg_e9m4_14_extra_config_p56E67CAE03CCC702.json",
        "extraConfigSha256":
            "2B5B11599578C60B7C5BDF0895B94B00443717018DEB88DAFC8BCF6A584811E5",
        "lineIds": (
            "dlg_e9m4_14_001",
            "dlg_e9m4_14_002",
            "dlg_e9m4_14_003",
            "dlg_e9m4_14_004",
            "dlg_e9m4_14_005",
            "dlg_e9m4_14_006",
            "dlg_e9m4_14_009",
        ),
        "optionIds": (),
        "npcProxyConsumer": {
            "proxyId": "lizhui_map02_e9m4",
            "entryIndex": 0,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_e9m4_14",
            },
        },
    },
    "dlg_e3m2_3": {
        "missionId": "e3m2",
        "filename": "dlg_e3m2_3_p073FB64F2553F62C.json",
        "sha256":
            "C287E7567A0627AAF98E8A89D07B57544745CFF9010D583AF7131937172983D5",
        "extraConfigFilename":
            "dlg_e3m2_3_extra_config_pD18056EEFF76A7CB.json",
        "extraConfigSha256":
            "0FA5094331379166E3BDCF8D716B43A02015BA029AB05B521A7C7170BCA57B3D",
        "lineIds": (
            "dlg_e3m2_3_001",
            "dlg_e3m2_3_002",
        ),
        "optionIds": (),
        "missingAudioIds": (
            "au_dlg_e3m2_3_001",
            "au_dlg_e3m2_3_002",
        ),
        "npcProxyConsumer": {
            "proxyId": "angelu_map01_e3m201",
            "entryIndex": 0,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_e3m2_3",
            },
        },
    },
    "dlg_e2m2_7": {
        "missionId": "e2m2",
        "filename": "dlg_e2m2_7_p28BF6C7E795E9C93.json",
        "sha256":
            "514C97986686C2C30733D0496511E4F44208A3F6252D95E3F80FEDEF1C82D5D5",
        "extraConfigFilename":
            "dlg_e2m2_7_extra_config_pFC77A69216F00A44.json",
        "extraConfigSha256":
            "7F88C33446D83009C0D7C3E8C8650743EA0A46DD2D1D07489A2FCE9BC3E824C2",
        "lineIds": tuple(
            f"dlg_e2m2_7_{number:03d}" for number in range(1, 13)
        ),
        "optionIds": (
            "option_dlg_e2m2_7_1_001",
            "option_dlg_e2m2_7_1_002",
            "option_dlg_e2m2_7_2_001",
        ),
        "npcProxyConsumer": {
            "proxyId": "tata_map01_i002",
            "entryIndex": 1,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_e2m2_7",
                "missionId": "",
            },
        },
    },
    "misc_dlg_e2m2_1d5": {
        "missionId": "e2m2",
        "registryKey": "dlg_e2m2_1d5",
        "definitionName": "dlg_e2m2_1d5",
        "linePrefix": "dlg_e2m2_1d5",
        "filename": "dlg_e2m2_1d5_p32D55E7FEE2AB358.json",
        "sha256":
            "4872E1D7D5AA7B30E36AD86D3AC6AD5DC1C577D33C1A1D5DC88684A1EC3D964B",
        "extraConfigFilename":
            "dlg_e2m2_1d5_extra_config_pD4CCA655FC1BBDC9.json",
        "extraConfigSha256":
            "AE06AC62D18F6D29C144B410A1280C3DB900EECFF111812EEF49F3EAA208D50F",
        "lineIds": tuple(
            f"dlg_e2m2_1d5_{number:03d}" for number in range(1, 12)
        ),
        "optionIds": ("option_dlg_e2m2_1d5_1_001",),
        "npcProxyConsumer": {
            "proxyId": "fabian_map01_lv005",
            "entryIndex": 0,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_e2m2_1d5",
                "missionId": "",
            },
        },
    },
    "misc_dlg_e2m2_4d5": {
        "missionId": "e2m2",
        "registryKey": "dlg_e2m2_4d5",
        "definitionName": "dlg_e2m2_4d5",
        "linePrefix": "dlg_e2m2_4d5",
        "filename": "dlg_e2m2_4d5_pD12E16AC83FB67E1.json",
        "sha256":
            "170B3BC1425BA0786A9273C110B770C9115DFD7043B53C81AC7C9860FB6A2BBD",
        "extraConfigFilename":
            "dlg_e2m2_4d5_extra_config_p64CA0B5FC6406B2D.json",
        "extraConfigSha256":
            "7884230613647CB1E8CCB771743DCE5DE997D8CDB229C4396A80779570ACC10B",
        "lineIds": tuple(
            f"dlg_e2m2_4d5_{number:03d}" for number in range(1, 8)
        ),
        "optionIds": (
            "option_dlg_e2m2_4d5_1_001",
            "option_dlg_e2m2_4d5_1_002",
        ),
        "npcProxyConsumer": {
            "proxyId": "ailaizha_map01_lv005",
            "entryIndex": 0,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_e2m2_4d5",
                "missionId": "",
            },
        },
    },
    "misc_dlg_e1m3_5d5": {
        "missionId": "e1m3",
        "registryKey": "dlg_e1m3_5d5",
        "definitionName": "dlg_e1m3_5d5",
        "linePrefix": "dlg_e1m3_5d5",
        "filename": "dlg_e1m3_5d5_pA56DA1BBAEFC3080.json",
        "sha256":
            "014F63CEB6317CAC1DD68FFDEED1D52DBDF8CBCEC55902265302B34296634D6B",
        "lineIds": (
            "dlg_e1m3_5d5_002",
            "dlg_e1m3_5d5_003",
        ),
        "optionIds": (),
    },
    "dlg_e2m4_10": {
        "missionId": "e2m4",
        "filename": "dlg_e2m4_10_pE6CEEAF69EAEC061.json",
        "sha256":
            "2F438CED7B5B49349A966E365B69798F4F835F9C3797CB7E8C47DA2E1CC3D6A7",
        "lineIds": tuple(
            f"dlg_e2m4_10_{number:03d}" for number in range(1, 6)
        ),
        "optionIds": (
            "option_dlg_e2m4_10_1_001",
            "option_dlg_e2m4_10_1_002",
        ),
    },
    "dlg_e2m5_6": {
        "missionId": "e2m5",
        "filename": "dlg_e2m5_6_p3913E9EAD5687F40.json",
        "sha256":
            "5DC06B64F1EED679B16A7AFFFE3AFE4671569390664C481FC0C926B14CB1BC5B",
        "extraConfigFilename":
            "dlg_e2m5_6_extra_config_pA53AAFF29A7089F5.json",
        "extraConfigSha256":
            "ECB4AAE557503DD87DD1D3C02088A41277EE32D977BAE4998BB23D457A1239EF",
        "lineIds": tuple(
            f"dlg_e2m5_6_{number:03d}" for number in range(1, 7)
        ),
        "optionIds": (
            "option_dlg_e2m5_6_1_001",
            "option_dlg_e2m5_6_1_002",
        ),
        "npcProxyConsumer": {
            "proxyId": "tata_map01_i008",
            "entryIndex": 0,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_e2m5_6",
                "missionId": "",
            },
        },
    },
    "dlg_e2m6_12": {
        "missionId": "e2m6",
        "filename": "dlg_e2m6_12_p5F708F0BF48A1164.json",
        "sha256":
            "38B38F5C9170CDCA9476545072F986FCF9C3BC6E62EA7B1CA0FA074352E12EDB",
        "lineIds": tuple(
            f"dlg_e2m6_12_{number:03d}" for number in range(1, 25)
        ),
        "optionIds": tuple(
            f"option_dlg_e2m6_12_1_{number:03d}"
            for number in range(1, 5)
        ),
    },
    "dlg_e5m2_2": {
        "missionId": "e5m2",
        "filename": "dlg_e5m2_2_pEB6A5B995EA35166.json",
        "sha256":
            "4C31923E2B17DEA1FB0E79A9710D6BFEDC199FC0DA3AF8E46D31613879CDFC97",
        "extraConfigFilename":
            "dlg_e5m2_2_extra_config_pFC8C62321BCB344B.json",
        "extraConfigSha256":
            "CD05840A7EC0AFBEE61E7FB2952B860F7040C1B08A608B55C44B11ACC5102359",
        "lineIds": (
            "dlg_e5m2_2_001",
            "dlg_e5m2_2_002",
            "dlg_e5m2_2_003",
            "dlg_e5m2_2_005",
            "dlg_e5m2_2_006",
            "dlg_e5m2_2_008",
            "dlg_e5m2_2_010",
            "dlg_e5m2_2_011",
            "dlg_e5m2_2_012",
            "dlg_e5m2_2_013",
            "dlg_e5m2_2_014",
            "dlg_e5m2_2_015",
            "dlg_e5m2_2_019",
            "dlg_e5m2_2_020",
            "dlg_e5m2_2_022",
            "dlg_e5m2_2_023",
            "dlg_e5m2_2_024",
            "dlg_e5m2_2_028",
            "dlg_e5m2_2_030",
            "dlg_e5m2_2_031",
            "dlg_e5m2_2_032",
            "dlg_e5m2_2_035",
            "dlg_e5m2_2_036",
            "dlg_e5m2_2_037",
            "dlg_e5m2_2_039",
            "dlg_e5m2_2_040",
            "dlg_e5m2_2_041",
            "dlg_e5m2_2_042",
            "dlg_e5m2_2_043",
        ),
        "optionIds": (
            "option_dlg_e5m2_2_3_001",
            "option_dlg_e5m2_2_4_001",
        ),
        "missingAudioIds": ("au_dlg_e5m2_2_003",),
        "ownedTimeline": {
            "timeline": "dlgtl_e5m2_2_sub_1",
            "sourceFile": "CAB-d519c34c420d1804280357b6cb378d57",
            "trackPathId": -6721394561739517947,
            "fullLineIds": (
                "dlg_e5m2_2_001",
                "dlg_e5m2_2_002",
                "dlg_e5m2_2_003",
                "dlg_e5m2_2_005",
                "dlg_e5m2_2_006",
                "dlg_e5m2_2_008",
                "dlg_e5m2_2_032",
                "dlg_e5m2_2_010",
                "dlg_e5m2_2_011",
                "dlg_e5m2_2_012",
                "dlg_e5m2_2_013",
                "dlg_e5m2_2_014",
                "dlg_e5m2_2_035",
                "dlg_e5m2_2_036",
                "dlg_e5m2_2_015",
                "dlg_e5m2_2_030",
                "dlg_e5m2_2_019",
                "dlg_e5m2_2_020",
                "dlg_e5m2_2_037",
                "dlg_e5m2_2_022",
                "dlg_e5m2_2_023",
                "dlg_e5m2_2_024",
                "dlg_e5m2_2_039",
                "dlg_e5m2_2_040",
                "dlg_e5m2_2_041",
                "dlg_e5m2_2_042",
                "dlg_e5m2_2_043",
                "dlg_e5m2_2_028",
                "dlg_e5m2_2_031",
            ),
        },
        "npcProxyConsumer": {
            "proxyId": "tangtang_map02_e5m2rongdong",
            "entryIndex": 1,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_e5m2_2",
                "missionId": "",
            },
        },
    },
    "dlg_e5m2_8": {
        "missionId": "e5m2",
        "filename": "dlg_e5m2_8_p0532B39D7F861ACB.json",
        "sha256":
            "DFD36D9BA920DB724F18D3508CE7EC31AB87D2BC8D4129ECA6141C08B83DB131",
        "extraConfigFilename":
            "dlg_e5m2_8_extra_config_pE99F71CD3EB3F7B3.json",
        "extraConfigSha256":
            "620C42152579A15BF41E9C314E2A111252860A29EED0CA571FE05E2EA4FC4083",
        "lineIds": (
            "dlg_e5m2_8_001",
            "dlg_e5m2_8_004",
        ),
        "optionIds": (
            "option_dlg_e5m2_8_1_001",
            "option_dlg_e5m2_8_1_002",
        ),
        "npcProxyConsumer": {
            "proxyId": "tangtang_map02_e5m2duizhi",
            "entryIndex": 1,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_e5m2_8",
                "missionId": "",
            },
        },
    },
    "misc_dlg_e5m2_3d5": {
        "missionId": "e5m2",
        "registryKey": "dlg_e5m2_3d5",
        "definitionName": "dlg_e5m2_3d5",
        "linePrefix": "dlg_e5m2_3d5",
        "filename": "dlg_e5m2_3d5_pBBF809F4820EC1D7.json",
        "sha256":
            "69AE360E3678E6A4E1497A38DF111829CEBD71A9B291A375D06C8E2CB82D99EA",
        "extraConfigFilename":
            "dlg_e5m2_3d5_extra_config_p4A78736D728AD6CA.json",
        "extraConfigSha256":
            "001E4FFBE713E679D7938CFABADEC973BF3749E014D14CBCD2D04F46A30954C0",
        "lineIds": (
            "dlg_e5m2_3d5_001",
            "dlg_e5m2_3d5_003",
            "dlg_e5m2_3d5_004",
            "dlg_e5m2_3d5_005",
            "dlg_e5m2_3d5_006",
        ),
        "optionIds": (),
        "missingAudioIds": ("au_dlg_e5m2_3d5_003",),
        "npcProxyConsumer": {
            "proxyId": "ruanyi_map02_e5m2rongdong",
            "entryIndex": 1,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_e5m2_3d5",
            },
        },
    },
    "dlg_e5m1_3": {
        "missionId": "e5m1",
        "filename": "dlg_e5m1_3_p55224304204EA22A.json",
        "sha256":
            "4CAE541C5D33768930C20788527EA4489EABA4D3EBA3EE73EED1197E6727EFA8",
        "extraConfigFilename":
            "dlg_e5m1_3_extra_config_pF7AFF626DE2A4B70.json",
        "extraConfigSha256":
            "EA46F8F70C493BD6EF92097431AF29077F6B30DF6729CCDFBFA6D383A414BA9D",
        "lineIds": (
            "dlg_e5m1_3_001",
            "dlg_e5m1_3_002",
        ),
        "optionIds": (
            "option_dlg_e5m1_3_1_001",
            "option_dlg_e5m1_3_1_002",
        ),
        "npcProxyConsumer": {
            "proxyId": "pelica_base01_lv001_e5m1back",
            "entryIndex": 1,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_e5m1_3",
                "missionId": "",
            },
        },
    },
    "dlg_e10m1_7": {
        "missionId": "e10m1",
        "filename": "dlg_e10m1_7_pDDE0B4406DC04365.json",
        "sha256":
            "3A29348AC1A0732F4DCFC85404D1F11C08F48CB1B546903F71723CF16A509FCD",
        "extraConfigFilename":
            "dlg_e10m1_7_extra_config_p56C17FD0ACF11710.json",
        "extraConfigSha256":
            "95BB5B09DEA22F63EFBB5506FBF1900AFC43D7DC3C6411F8281E33216DA7E5FA",
        "lineIds": ("dlg_e10m1_7_001",),
        "optionIds": (),
        "missingAudioIds": ("au_dlg_e10m1_7_001",),
    },
    "dlg_e10m3_3": {
        "missionId": "e10m3",
        "filename": "dlg_e10m3_3_pB9BB31A2F515FDA0.json",
        "sha256":
            "19DF7EB6FE6BEAC868C6C19B73BA54AF656B9366569D103B4B5FF625BEDF449A",
        "lineIds": tuple(
            f"dlg_e10m3_3_{number:03d}" for number in range(1, 11)
        ),
        "optionIds": (),
    },
    "dlg_e10m3_9": {
        "missionId": "e10m3",
        "filename": "dlg_e10m3_9_p2CF5E96699979960.json",
        "sha256":
            "A0A35752AAAAA5BB6326D14EBBFA1DACCE571761AFE104B9D46AAD0B39CA4BB2",
        "lineIds": tuple(
            f"dlg_e10m3_9_{number:03d}" for number in range(1, 20)
        ),
        "optionIds": (),
        "missingAudioIds": (
            "au_dlg_e10m3_9_006",
            "au_dlg_e10m3_9_007",
            "au_dlg_e10m3_9_008",
            "au_dlg_e10m3_9_010",
            "au_dlg_e10m3_9_011",
            "au_dlg_e10m3_9_013",
            "au_dlg_e10m3_9_014",
            "au_dlg_e10m3_9_015",
        ),
        "ownedTimeline": {
            "timeline": "dlgtl_e10m3_9_sub_1",
            "sourceFile": "CAB-6b6c94f7ad380e1b021f87bd7177e880",
            "trackPathIds": (
                -3513721562143553181,
                4679925721215633763,
            ),
            "fullLineIds": (
                "dlg_e10m3_9_016",
                "dlg_e10m3_9_017",
                "dlg_e10m3_9_018",
                "dlg_e10m3_9_019",
                *(
                    f"dlg_e10m3_9_{number:03d}"
                    for number in range(1, 16)
                ),
            ),
        },
    },
    "dlg_e10m4_21": {
        "missionId": "e10m4",
        "filename": "dlg_e10m4_21_pE22DEC2EC32D6B16.json",
        "sha256":
            "E18C531CAD71317B99AD161E58B596BFFC8AD7E6B4F450EB7401680BF5894E2A",
        "extraConfigFilename":
            "dlg_e10m4_21_extra_config_pB7B941BA25FCA30C.json",
        "extraConfigSha256":
            "BBA7D588A2B3D0B9A44D8D4D9D58A14246096C41E85ABA330357BAFC32140B94",
        "lineIds": (
            "dlg_e10m4_21_001",
            "dlg_e10m4_21_002",
            "dlg_e10m4_21_003",
        ),
        "optionIds": (),
        "missingAudioIds": (
            "au_dlg_e10m4_21_001",
            "au_dlg_e10m4_21_002",
            "au_dlg_e10m4_21_003",
        ),
    },
    "dlg_e3m3_12": {
        "missionId": "e3m3",
        "filename": "dlg_e3m3_12_p689304794B0379C8.json",
        "sha256":
            "4740A3B03F953F51E9D29514C374DC2A1D0ABA6C140CB861540594AB594553CA",
        "lineIds": tuple(
            f"dlg_e3m3_12_{number:03d}"
            for number in range(1, 19)
        ),
        "optionIds": (
            "option_dlg_e3m3_12_1_001",
            "option_dlg_e3m3_12_1_002",
            "option_dlg_e3m3_12_1_003",
            "option_dlg_e3m3_12_1_004",
        ),
    },
    "dlg_e3m3_13": {
        "missionId": "e3m3",
        "filename": "dlg_e3m3_13_p385E5A04C27D079C.json",
        "sha256":
            "4E0B8DACC721093A2C165A49A9E8572F7415BF3CBF28982359757D174EA3569C",
        "lineIds": (
            "dlg_e3m3_13_001",
            "dlg_e3m3_13_002",
            "dlg_e3m3_13_003",
            "dlg_e3m3_13_004",
        ),
        "optionIds": (),
    },
    "dlg_e7m4_7": {
        "missionId": "e7m4",
        "filename": "dlg_e7m4_7_p2D060CEE2EAD8EDA.json",
        "sha256":
            "849E5337AE53789BABF0F032BC91F6D78A9AEEEC39A04AF0C7607BDCDF221794",
        "extraConfigFilename":
            "dlg_e7m4_7_extra_config_pD963D3DAC28A8950.json",
        "extraConfigSha256":
            "CDF50562A00FA606836690E37B5BC2F9C69F9D16246FEE21528E7026919DA2E0",
        "lineIds": (
            "dlg_e7m4_7_001",
            "dlg_e7m4_7_002",
            "dlg_e7m4_7_003",
        ),
        "optionIds": (),
        "missingAudioIds": (
            "au_dlg_e7m4_7_001",
            "au_dlg_e7m4_7_002",
            "au_dlg_e7m4_7_003",
        ),
    },
    "dlg_e7m2_11": {
        "missionId": "e7m2",
        "filename": "dlg_e7m2_11_p1D1D1CB6DCE33F66.json",
        "sha256":
            "E60981C01179E2FDE65F3A76D10128330CAFAFF4F451EDD57FBE3B843299F41C",
        "lineIds": (
            "dlg_e7m2_11_001",
            "dlg_e7m2_11_002",
            "dlg_e7m2_11_003",
        ),
        "optionIds": (),
    },
    "dlg_e7m2_13": {
        "missionId": "e7m2",
        "filename": "dlg_e7m2_13_p8219B1D5393A3051.json",
        "sha256":
            "EF0C416CD15649F3A9BD911C87EB97CF4A71F6715878090125F947518B570A27",
        "lineIds": (
            "dlg_e7m2_13_001",
            "dlg_e7m2_13_002",
        ),
        "optionIds": (),
        "missingAudioIds": (
            "au_dlg_e7m2_13_001",
            "au_dlg_e7m2_13_002",
        ),
    },
    "dlg_e7m3_13": {
        "missionId": "e7m3",
        "filename": "dlg_e7m3_13_pD75255B67D51A16E.json",
        "sha256":
            "437FD848FEBF1BD10E90C9CAB6B68F415E29ED7A8DAFDE21EE1A35C10DDAB56B",
        "lineIds": tuple(
            f"dlg_e7m3_13_{number:03d}" for number in range(1, 10)
        ),
        "optionIds": tuple(
            f"option_dlg_e7m3_13_1_{number:03d}"
            for number in range(1, 4)
        ),
    },
    "dlg_e7m3_15": {
        "missionId": "e7m3",
        "filename": "dlg_e7m3_15_pC808C6988F2464AA.json",
        "sha256":
            "62FF31B559B95F30B5AEE5547D4964044F818ED6C41F75101CF5E602739572F1",
        "lineIds": tuple(
            f"dlg_e7m3_15_{number:03d}" for number in range(1, 13)
        ),
        "optionIds": (
            "option_dlg_e7m3_15_1_001",
            "option_dlg_e7m3_15_1_002",
            "option_dlg_e7m3_15_2_001",
            "option_dlg_e7m3_15_3_001",
            "option_dlg_e7m3_15_4_001",
            "option_dlg_e7m3_15_4_002",
        ),
    },
    "dlg_e7m3_16": {
        "missionId": "e7m3",
        "filename": "dlg_e7m3_16_p9BE01C45211C9E1C.json",
        "sha256":
            "0CF7478E1B968C0E164FC13E0EB79BF73A72D15DC6EE80B87B32A85490C37F76",
        "lineIds": tuple(
            f"dlg_e7m3_16_{number:03d}" for number in range(1, 7)
        ),
        "optionIds": ("option_dlg_e7m3_16_1_001",),
    },
    "dlg_e11m8_9": {
        "missionId": "e11m8",
        "filename": "dlg_e11m8_9_p2B015B8998EBB34F.json",
        "sha256":
            "AD30F62C0FCC7C8412EF56AF9B765B3209444D2B7DAB6C39D98BBE28D48916D2",
        "lineIds": tuple(
            f"dlg_e11m8_9_{number:03d}"
            for number in range(1, 33)
            if number not in {10, 19}
        ),
        "optionIds": (
            "option_dlg_e11m8_9_1_001",
            "option_dlg_e11m8_9_1_002",
        ),
        "missingAudioIds": (
            "au_dlg_e11m8_9_004",
            "au_dlg_e11m8_9_007",
            "au_dlg_e11m8_9_009",
            "au_dlg_e11m8_9_012",
            "au_dlg_e11m8_9_015",
            "au_dlg_e11m8_9_024",
            "au_dlg_e11m8_9_026",
            "au_dlg_e11m8_9_029",
        ),
        "ownedTimeline": {
            "timeline": "dlgtl_e11m8_9_sub_1",
            "sourceFile": "CAB-d4eda23280ba987e1fdf52eb15872d23",
            "trackPathId": -1012842435443729704,
            "fullLineIds": (
                "dlg_e11m8_9_001", "dlg_e11m8_9_014",
                "dlg_e11m8_9_002", "dlg_e11m8_9_003",
                "dlg_e11m8_9_004", "dlg_e11m8_9_005",
                "dlg_e11m8_9_015", "dlg_e11m8_9_016",
                "dlg_e11m8_9_017", "dlg_e11m8_9_032",
                "dlg_e11m8_9_006", "dlg_e11m8_9_029",
                "dlg_e11m8_9_018", "dlg_e11m8_9_007",
                "dlg_e11m8_9_020", "dlg_e11m8_9_021",
                "dlg_e11m8_9_030", "dlg_e11m8_9_022",
                "dlg_e11m8_9_008", "dlg_e11m8_9_023",
                "dlg_e11m8_9_012", "dlg_e11m8_9_024",
                "dlg_e11m8_9_013", "dlg_e11m8_9_025",
                "dlg_e11m8_9_009", "dlg_e11m8_9_026",
                "dlg_e11m8_9_011", "dlg_e11m8_9_027",
                "dlg_e11m8_9_028", "dlg_e11m8_9_031",
            ),
        },
    },
    "dlg_e6m3_6": {
        "missionId": "e6m3",
        "filename": "dlg_e6m3_6_p5CAF49EFDB182127.json",
        "sha256":
            "E955FC5FB469A635FCCA931CE68103F30E93CD81D3AE8CD98CEF358E245702DE",
        "lineIds": tuple(
            f"dlg_e6m3_6_{number:03d}"
            for number in range(1, 10)
        ),
        "optionIds": (),
    },
    "dlg_e6m1_14": {
        "missionId": "e6m1",
        "filename": "dlg_e6m1_14_p68EC42E095AD2906.json",
        "sha256":
            "2D52AD3AFC477391C10D0CC4F7A6E6EDAF26ABB4B5570D2A117FED25D4DB1D29",
        "extraConfigFilename":
            "dlg_e6m1_14_extra_config_p8B575A1C0B9C3E39.json",
        "extraConfigSha256":
            "CD3EA19136503B91592A6FE009C4158438C13EA999A3529B98FF8CE40B270359",
        "lineIds": (
            "dlg_e6m1_14_001",
            "dlg_e6m1_14_002",
            "dlg_e6m1_14_003",
            "dlg_e6m1_14_004",
        ),
        "optionIds": (),
        "npcProxyConsumer": {
            "proxyId": "lugang_map02_e6m1ZhenLie",
            "entryIndex": 0,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_e6m1_14",
            },
        },
    },
    "dlg_e6m1_15": {
        "missionId": "e6m1",
        "filename": "dlg_e6m1_15_pA6CAD82C1F00354C.json",
        "sha256":
            "60B8DBAD94965EDAD4936DCDCDEDC2B79F65B4C4514CDC0D54164AED44CD49AA",
        "extraConfigFilename":
            "dlg_e6m1_15_extra_config_p89766E5FF99A9E3D.json",
        "extraConfigSha256":
            "A59BE414E636958B7B85D98BE65563675160E538E9DB22E230A60FB486BE4A0A",
        "lineIds": (
            "dlg_e6m1_15_001",
            "dlg_e6m1_15_002",
            "dlg_e6m1_15_003",
        ),
        "optionIds": (
            "option_dlg_e6m1_15_1_001",
            "option_dlg_e6m1_15_1_002",
        ),
        "npcProxyConsumers": (
            {
                "proxyId": "puyuan_map02_default",
                "entryIndex": 0,
                "entry": {
                    "addDialogExOption": False,
                    "envTalkData": {"envTalkOverrideNpc": True},
                    "dialogExOptionData": [],
                    "dialogId": "dlg_e6m1_15",
                    "missionId": "",
                },
            },
            {
                "proxyId": "puyuan_map02_e6m1ZhenLie",
                "entryIndex": 0,
                "entry": {
                    "addDialogExOption": False,
                    "envTalkData": {"envTalkOverrideNpc": True},
                    "dialogExOptionData": [],
                    "dialogId": "dlg_e6m1_15",
                    "missionId": "",
                },
            },
        ),
    },
    "dlg_e6m3_12": {
        "missionId": "e6m3",
        "filename": "dlg_e6m3_12_p1A4EB66DB59018DA.json",
        "sha256":
            "AD57436D5155E735D1897C1D6E4173E8AECBBEAEE0C31F9961C935C75475F5CC",
        "lineIds": (
            "dlg_e6m3_12_001",
            "dlg_e6m3_12_002",
            "dlg_e6m3_12_003",
        ),
        "optionIds": (
            "option_dlg_e6m3_12_1_001",
            "option_dlg_e6m3_12_1_002",
        ),
    },
    "misc_dlg_e6m3_3d5": {
        "missionId": "e6m3",
        "registryKey": "dlg_e6m3_3d5",
        "definitionName": "dlg_e6m3_3d5",
        "linePrefix": "dlg_e6m3_3d5",
        "filename": "dlg_e6m3_3d5_pF3CFDA0ED349033C.json",
        "sha256":
            "85D89C0B57537D497FB38F9C912FCCFFB2AE14A1E2F59AEDEDCA7849B7959BB6",
        "lineIds": (
            "dlg_e6m3_3d5_001",
            "dlg_e6m3_3d5_002",
            "dlg_e6m3_3d5_003",
            "dlg_e6m3_3d5_004",
        ),
        "optionIds": ("option_dlg_e6m3_3d5_1_001",),
    },
    "dlg_e11m5_9": {
        "missionId": "e11m5",
        "filename": "dlg_e11m5_9_pC23DB75515095666.json",
        "sha256":
            "C0D65ACEC9E7A12EEBC4DF36A63F9885DF164B2501C1D6F01364299BB17C7DA9",
        "lineIds": tuple(
            f"dlg_e11m5_9_{number:03d}"
            for number in range(1, 12)
        ),
        "optionIds": (
            "option_dlg_e11m5_9_1_001",
            "option_dlg_e11m5_9_1_002",
        ),
        "ownedTimeline": {
            "timeline": "dlgtl_e11m5_9_sub_1",
            "sourceFile": "CAB-97f6deec242463684933cb9d8b65c753",
            "trackPathId": 5795311945645305682,
            "fullLineIds": (
                *(
                    f"dlg_e11m5_9_{number:03d}"
                    for number in range(1, 10)
                ),
                "dlg_e11m6_9_005",
                "dlg_e11m6_9_006",
                "dlg_e11m6_9_007",
                "dlg_e11m6_9_003",
                "dlg_e11m6_9_008",
                "dlg_e11m6_9_004",
                "dlg_e11m5_9_010",
                "dlg_e11m5_9_011",
            ),
        },
    },
    "dlg_e11m5_10": {
        "missionId": "e11m5",
        "filename": "dlg_e11m5_10_p5A9129339D481CC0.json",
        "sha256":
            "220464C78CC64E58B76634BF25FB8FE9A1C38188DD7B1D6961D89E948773499D",
        "lineIds": (
            "dlg_e11m5_10_001",
            "dlg_e11m5_10_002",
            "dlg_e11m5_10_003",
        ),
        "optionIds": (),
        "missingAudioIds": (
            "au_dlg_e11m5_10_002",
            "au_dlg_e11m5_10_003",
        ),
    },
    "dlg_e11m5_11": {
        "missionId": "e11m5",
        "filename": "dlg_e11m5_11_pD688FD9D65549B75.json",
        "sha256":
            "1F04DF04E1397B5936EE12EE1236C10E8ACCE5543451E0F8472AADF14708E5DB",
        "lineIds": (
            "dlg_e11m5_11_001",
            "dlg_e11m5_11_002",
            "dlg_e11m5_11_003",
        ),
        "optionIds": (),
    },
    "dlg_e11m5_12": {
        "missionId": "e11m5",
        "filename": "dlg_e11m5_12_p135B7060CFFC8F28.json",
        "sha256":
            "F333A7ECF1A52DF7C10BA33995A4CF27831540E6CF48C2C83DC39A4DE2BA49F9",
        "lineIds": (
            "dlg_e11m5_12_001",
            "dlg_e11m5_12_003",
            "dlg_e11m5_12_004",
        ),
        "optionIds": (),
    },
    "dlg_e11m5_13": {
        "missionId": "e11m5",
        "filename": "dlg_e11m5_13_p96F8614CB2A35E7F.json",
        "sha256":
            "47D743F27339ABDA651973E2CE3338337A25B1DE903D35F78CA933A1A686F5CC",
        "lineIds": ("dlg_e11m5_13_001",),
        "optionIds": (),
    },
    "dlg_e11m5_18": {
        "missionId": "e11m5",
        "filename": "dlg_e11m5_18_p416EFA9E2A6F4828.json",
        "sha256":
            "FDAA2B6D8F2D2E490FA394C0EBF7B9786C0A4D5FC48CA26F46C0C819EC337538",
        "lineIds": (
            "dlg_e11m5_18_001",
            "dlg_e11m5_18_002",
            "dlg_e11m5_18_003",
            "dlg_e11m5_18_004",
        ),
        "optionIds": (),
    },
    "dlg_e11m5_19": {
        "missionId": "e11m5",
        "filename": "dlg_e11m5_19_p60D5560775C02212.json",
        "sha256":
            "2DF312DB709D69E5F68574D8599B748EE69ACCDFF72FBCB1D619FBF5FDA69782",
        "lineIds": (
            "dlg_e11m5_19_001",
            "dlg_e11m5_19_002",
        ),
        "optionIds": (),
    },
    "dlg_e11m2_17": {
        "missionId": "e11m2",
        "filename": "dlg_e11m2_17_pFD065A1EEEB7D282.json",
        "sha256":
            "3B88159A1EAAFE08D7E933592D087E239BA60B49FD0D4B14E20D7E306A5B2F41",
        "lineIds": ("dlg_e11m2_17_001",),
        "optionIds": (),
    },
    "dlg_e11m2_18": {
        "missionId": "e11m2",
        "filename": "dlg_e11m2_18_pE605FDA82B1E2E4A.json",
        "sha256":
            "B6352DAA05B09772DBC31922F9CA27C173025641D4C20D949CD9DF8079543A2C",
        "lineIds": (
            "dlg_e11m2_18_001",
            "dlg_e11m2_18_002",
            "dlg_e11m2_18_003",
            "dlg_e11m2_18_004",
        ),
        "optionIds": (),
    },
    "dlg_e11m6_9": {
        "missionId": "e11m6",
        "filename": "dlg_e11m6_9_p23FC2E711EB7DE5B.json",
        "sha256":
            "680FCF761BC0239B626C6441296A653E19549EE9E2510C5EB22FE8AAA27061CF",
        "lineIds": (
            "dlg_e11m6_9_001",
            "dlg_e11m6_9_003",
            "dlg_e11m6_9_004",
            "dlg_e11m6_9_005",
            "dlg_e11m6_9_006",
            "dlg_e11m6_9_007",
            "dlg_e11m6_9_008",
        ),
        "optionIds": (
            "option_dlg_e11m6_9_1_001",
            "option_dlg_e11m6_9_1_002",
        ),
        "sharedTimeline": {
            "ownerDialogKey": "dlg_e11m5_9",
            "timeline": "dlgtl_e11m5_9_sub_1",
            "sourceFile": "CAB-97f6deec242463684933cb9d8b65c753",
            "trackPathId": 5795311945645305682,
            "beforeLineId": "dlg_e11m5_9_009",
            "embeddedLineIds": (
                "dlg_e11m6_9_005",
                "dlg_e11m6_9_006",
                "dlg_e11m6_9_007",
                "dlg_e11m6_9_003",
                "dlg_e11m6_9_008",
                "dlg_e11m6_9_004",
            ),
            "afterLineId": "dlg_e11m5_9_010",
        },
    },
    "dlg_gm01m12_1": {
        "missionId": "gm01m12",
        "filename": "dlg_gm01m12_1_pF2AF8213565C6977.json",
        "sha256":
            "C52741D0325B6CEA1BCF9E5E06C150C2CB3ED391E9C855B73ABF51B8DE84B40F",
        "extraConfigFilename":
            "dlg_gm01m12_1_extra_config_p06142BC1CDCE8FC7.json",
        "extraConfigSha256":
            "BAEF05D1D1255319B7E4C4466C8EA2E20650A18EBED33DEC50175F8E9603390D",
        "lineIds": tuple(
            f"dlg_gm01m12_1_{number:03d}" for number in range(1, 8)
        ),
        "optionIds": (
            "option_dlg_gm01m12_1_1_001",
            "option_dlg_gm01m12_1_2_001",
            "option_dlg_gm01m12_1_2_002",
            "option_dlg_gm01m12_1_3_001",
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m12_1_{number:03d}" for number in range(1, 8)
        ),
        "treeBranchGroups": ({
            "optionGroup": 2,
            "optionIds": (
                "option_dlg_gm01m12_1_2_001",
                "option_dlg_gm01m12_1_2_002",
            ),
            "targetLineIds": ("dlg_gm01m12_1_005",) * 2,
            "routeKind": "authored_convergence",
        },),
        "npcProxyConsumer": {
            "proxyId": "sesidun_map01_001",
            "entryIndex": 0,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_gm01m12_1",
            },
        },
    },
    "dlg_gm01m12_3": {
        "missionId": "gm01m12",
        "filename": "dlg_gm01m12_3_p53FF91C6849A030C.json",
        "sha256":
            "77729BDC4CADACFF5783AAB9317B0F42F655B9C8CE5D8E8C100F6CAE36410470",
        "extraConfigFilename":
            "dlg_gm01m12_3_extra_config_p16586299C6F9FFBA.json",
        "extraConfigSha256":
            "839031387E1ABEF0CAD71518C23ED5B8C2E06D75E58BF37E79B52A7BDFF0690F",
        "lineIds": tuple(
            f"dlg_gm01m12_3_{number:03d}" for number in range(1, 6)
        ),
        "optionIds": (
            "option_dlg_gm01m12_3_1_001",
            "option_dlg_gm01m12_3_1_002",
            "option_dlg_gm01m12_3_2_001",
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m12_3_{number:03d}" for number in range(1, 6)
        ),
        "treeBranchGroups": ({
            "optionGroup": 1,
            "optionIds": (
                "option_dlg_gm01m12_3_1_001",
                "option_dlg_gm01m12_3_1_002",
            ),
            "targetLineIds": ("dlg_gm01m12_3_002",) * 2,
            "routeKind": "authored_convergence",
        },),
        "npcProxyConsumer": {
            "proxyId": "sesidun_map01_001",
            "entryIndex": 2,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_gm01m12_3",
            },
        },
    },
    "dlg_gm01m12_6": {
        "missionId": "gm01m12",
        "filename": "dlg_gm01m12_6_p0F7AFEA3958AE324.json",
        "sha256":
            "F8A0E8812ABE280036A1521FD0091093CCA38DBC21946077FA2ED957B81983B3",
        "extraConfigFilename":
            "dlg_gm01m12_6_extra_config_pF48D871B428F357B.json",
        "extraConfigSha256":
            "B9119531E4D96398037D132F36C364CC3E401E7891FEB63E8AE2ABE72A1F5529",
        "lineIds": ("dlg_gm01m12_6_001", "dlg_gm01m12_6_002"),
        "optionIds": (),
        "missingAudioIds": (
            "au_dlg_gm01m12_6_001",
            "au_dlg_gm01m12_6_002",
        ),
        "treeBranchGroups": (),
    },
    "dlg_gm01m20_1": {
        "missionId": "gm01m20",
        "filename": "dlg_gm01m20_1_p3E261E43E6E27E12.json",
        "sha256":
            "D643490D25B83810DFA5362A8C2BE633FE73ECECC7127CADDFC18D6561C1A5BF",
        "extraConfigFilename":
            "dlg_gm01m20_1_extra_config_p8CA71C2BA146C847.json",
        "extraConfigSha256":
            "7E918CFE99522C54CB6BB6F84BC383ADCD15678FC1D9ACF282AAF20ABF5F157B",
        "lineIds": tuple(
            f"dlg_gm01m20_1_{number:03d}" for number in range(1, 5)
        ),
        "optionIds": (),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m20_1_{number:03d}" for number in range(1, 5)
        ),
        "treeBranchGroups": (),
        "npcProxyConsumer": {
            "proxyId": "kupe_map01_normal",
            "entryIndex": 6,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_gm01m20_1",
                "missionId": "",
            },
        },
        "missionNpcProxyTracking": {
            "sourceFile": (
                "export_full/structured/Persistent/Data/Json/"
                "MissionRuntimeAsset/gm01m20.json"
            ),
            "sourceSha256":
                "01BC364A3A64CFFE8BE236B017020D76ACDBB42866862031A5DC4405B501E355",
            "proxyId": "kupe_map01_normal",
            "levelId": "map01_lv001",
            "rows": tuple({
                "questId": f"gm01m20_q#{quest}",
                "objectiveIndex": 0,
                "trackingIndex": 0,
            } for quest in (1, 3, 2, 10)),
        },
    },
    "dlg_gm01m20_5": {
        "missionId": "gm01m20",
        "filename": "dlg_gm01m20_5_pA68209E428C780DF.json",
        "sha256":
            "91244B53B797F4A82C3CB2234937C57CCF23CAC705C115BA8D99A5BA92D9BC6B",
        "extraConfigFilename":
            "dlg_gm01m20_5_extra_config_p597B261A582F262B.json",
        "extraConfigSha256":
            "E3F4F5A14BFFE6A0C45673C844C4C4BB5A0E9246ED7FBF0D49FD702CBE168C60",
        "lineIds": tuple(
            f"dlg_gm01m20_5_{number:03d}" for number in range(1, 5)
        ),
        "optionIds": (),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m20_5_{number:03d}" for number in range(1, 5)
        ),
        "treeBranchGroups": (),
        "npcProxyConsumer": {
            "proxyId": "bulongze_map01_normal",
            "entryIndex": 0,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_gm01m20_5",
                "missionId": "",
            },
        },
    },
    "dlg_gm01m20_6": {
        "missionId": "gm01m20",
        "filename": "dlg_gm01m20_6_pD24399E8F7195888.json",
        "sha256":
            "9F3041C9F45FD47D49515D6E4BE356E079BE8DFAB76AE1713401EEA125C0BD61",
        "extraConfigFilename":
            "dlg_gm01m20_6_extra_config_p8C7D71AAC32E8A1E.json",
        "extraConfigSha256":
            "CC1ECBF3C934264D4BECCAE3F59D37D7E3ED941442F4C0A89170D31795867009",
        "lineIds": ("dlg_gm01m20_6_001", "dlg_gm01m20_6_002"),
        "optionIds": (),
        "missingAudioIds": (
            "au_dlg_gm01m20_6_001",
            "au_dlg_gm01m20_6_002",
        ),
        "treeBranchGroups": (),
        "npcProxyConsumer": {
            "proxyId": "bulongze_map01_normal",
            "entryIndex": 1,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_gm01m20_6",
                "missionId": "",
            },
        },
    },
    "dlg_gm01m20_7": {
        "missionId": "gm01m20",
        "filename": "dlg_gm01m20_7_pFD15B4590CD2E063.json",
        "sha256":
            "20FB5080BCBCC43E6A80864644D4AF4C72716521AA284D2E44E2E8FB17905159",
        "extraConfigFilename":
            "dlg_gm01m20_7_extra_config_p2E7AD2EF233846E0.json",
        "extraConfigSha256":
            "BDA0446EB2158BCE174CA81E9191DA6E2FE44B3988E34FD076F70E992A116779",
        "lineIds": tuple(
            f"dlg_gm01m20_7_{number:03d}" for number in range(1, 4)
        ),
        "optionIds": (),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m20_7_{number:03d}" for number in range(1, 4)
        ),
        "treeBranchGroups": (),
        "npcProxyConsumer": {
            "proxyId": "kupe_map01_normal",
            "entryIndex": 5,
            "entry": {
                "addDialogExOption": False,
                "envTalkData": {"envTalkOverrideNpc": True},
                "dialogExOptionData": [],
                "dialogId": "dlg_gm01m20_7",
                "missionId": "",
            },
        },
        "missionNpcProxyTracking": {
            "sourceFile": (
                "export_full/structured/Persistent/Data/Json/"
                "MissionRuntimeAsset/gm01m20.json"
            ),
            "sourceSha256":
                "01BC364A3A64CFFE8BE236B017020D76ACDBB42866862031A5DC4405B501E355",
            "proxyId": "kupe_map01_normal",
            "levelId": "map01_lv001",
            "rows": tuple({
                "questId": f"gm01m20_q#{quest}",
                "objectiveIndex": 0,
                "trackingIndex": 0,
            } for quest in (1, 3, 2, 10)),
        },
    },
}
OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS.update({
    "dlg_gm01m24_1": {
        "missionId": "gm01m24",
        "filename": "dlg_gm01m24_1_p79A4F29BA2561B1A.json",
        "sha256":
            "4675D4B89F9BD135249BF590A12C335FF8096EA15DC01C0F0C3797C8290AC195",
        "extraConfigFilename":
            "dlg_gm01m24_1_extra_config_pE595ACB405045450.json",
        "extraConfigSha256":
            "B6DCD1B6DC763EC5144E8899C864C12ACE4FAF7F3363FF9245817F45C789DD6E",
        "lineIds": tuple(
            f"dlg_gm01m24_1_{number:03d}"
            for number in (1, *range(5, 17))
        ),
        "optionIds": tuple(
            f"option_dlg_gm01m24_1_1_{number:03d}" for number in range(1, 4)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m24_1_{number:03d}"
            for number in (1, *range(5, 17))
        ),
        "treeBranchGroups": ({
            "optionGroup": 1,
            "optionIds": tuple(
                f"option_dlg_gm01m24_1_1_{number:03d}"
                for number in range(1, 4)
            ),
            "targetLineIds": (
                "dlg_gm01m24_1_014",
                "dlg_gm01m24_1_005",
                "dlg_gm01m24_1_009",
            ),
            "routeKind": "authored_split",
        },),
    },
    "dlg_gm01m24_2": {
        "missionId": "gm01m24",
        "filename": "dlg_gm01m24_2_p205ABEA30356033D.json",
        "sha256":
            "2976C3D43C97C37E715D8E10A2A98D02693D1C34959E1B904F26619D75A13BDD",
        "extraConfigFilename":
            "dlg_gm01m24_2_extra_config_p2386CE5133D132E5.json",
        "extraConfigSha256":
            "7CDD719BA4116F348758E84CB680B015FBC9F1754137E109832F59172D23D325",
        "lineIds": tuple(
            f"dlg_gm01m24_2_{number:03d}" for number in range(1, 4)
        ),
        "optionIds": tuple(
            f"option_dlg_gm01m24_2_1_{number:03d}" for number in range(1, 3)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m24_2_{number:03d}" for number in range(1, 4)
        ),
    },
    "dlg_gm01m24_3": {
        "missionId": "gm01m24",
        "filename": "dlg_gm01m24_3_pB62FBC62BE7B1E3B.json",
        "sha256":
            "0B0F2BC7E36976FC0D0F990BDE5A54463251DE3F91BEE049DD4776297676ADF9",
        "extraConfigFilename":
            "dlg_gm01m24_3_extra_config_p4F40313305D0C643.json",
        "extraConfigSha256":
            "C1F8C28F650C84E86A17A36499C870AAFA0F34248EE2C9727E75FFE83EDE5EC8",
        "lineIds": tuple(
            f"dlg_gm01m24_3_{number:03d}" for number in range(1, 4)
        ),
        "optionIds": tuple(
            f"option_dlg_gm01m24_3_1_{number:03d}" for number in range(1, 3)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m24_3_{number:03d}" for number in range(1, 4)
        ),
    },
    "dlg_gm01m25_1": {
        "missionId": "gm01m25",
        "filename": "dlg_gm01m25_1_pBC02BD93868F7244.json",
        "sha256":
            "936F8B0806E8C9665E3E893FCEF907BFF39447C8C4E329272FB646B61A8DA6C5",
        "extraConfigFilename":
            "dlg_gm01m25_1_extra_config_p283B84916755BA6E.json",
        "extraConfigSha256":
            "77F4F895E5195AEDDA2A26E04D6B12D22501FAE9F32C66A08A492A56E2ED5F65",
        "lineIds": tuple(
            f"dlg_gm01m25_1_{number:03d}" for number in range(9, 21)
        ),
        "optionIds": tuple(
            f"option_dlg_gm01m25_1_1_{number:03d}"
            for number in (1, 3, 4)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m25_1_{number:03d}" for number in range(9, 21)
        ),
        "treeBranchGroups": ({
            "optionGroup": 1,
            "optionIds": (
                "option_dlg_gm01m25_1_1_003",
                "option_dlg_gm01m25_1_1_001",
                "option_dlg_gm01m25_1_1_004",
            ),
            "targetLineIds": (
                "dlg_gm01m25_1_016",
                "dlg_gm01m25_1_013",
                "dlg_gm01m25_1_009",
            ),
            "routeKind": "authored_split",
        },),
    },
    "dlg_gm01m25_2": {
        "missionId": "gm01m25",
        "filename": "dlg_gm01m25_2_p61364FB28BF6E590.json",
        "sha256":
            "21E7C047FD7963144B258A6BF48FEE880AC5A2F8CC988E8652C8A8AC890528AF",
        "extraConfigFilename":
            "dlg_gm01m25_2_extra_config_p51073A344245C91A.json",
        "extraConfigSha256":
            "84F053C0E5C62364BC5A20266CE831C6F2858956768AE98B519FA198F73E936D",
        "lineIds": tuple(
            f"dlg_gm01m25_2_{number:03d}" for number in range(1, 5)
        ),
        "optionIds": tuple(
            f"option_dlg_gm01m25_2_1_{number:03d}" for number in range(1, 3)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m25_2_{number:03d}" for number in range(1, 5)
        ),
        "terminalOptionRoutes": ({
            "optionGroup": 1,
            "routes": ({
                "optionId": "option_dlg_gm01m25_2_1_001",
                "targetKind": "finish",
                "finishId": 1,
                "finishIdSerialized": True,
            }, {
                "optionId": "option_dlg_gm01m25_2_1_002",
                "targetKind": "finish",
                "finishId": None,
                "finishIdSerialized": False,
            }),
        },),
    },
    "dlg_gm01m25_3": {
        "missionId": "gm01m25",
        "filename": "dlg_gm01m25_3_pE99800EF4392A0ED.json",
        "sha256":
            "E560FE80168629B52FC91E37200F615830462B388310E2BF6F4CE1825245171E",
        "extraConfigFilename":
            "dlg_gm01m25_3_extra_config_pD29AE7415BF90392.json",
        "extraConfigSha256":
            "3E7A166BE7721B67B34ACD2A2F3DD54ED77B7A5998E7E01F3BB3F2A21511BAB3",
        "lineIds": tuple(
            f"dlg_gm01m25_3_{number:03d}" for number in range(1, 4)
        ),
        "optionIds": tuple(
            f"option_dlg_gm01m25_3_1_{number:03d}" for number in range(1, 3)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m25_3_{number:03d}" for number in range(1, 4)
        ),
        "terminalOptionRoutes": ({
            "optionGroup": 1,
            "routes": ({
                "optionId": "option_dlg_gm01m25_3_1_001",
                "targetKind": "finish",
                "finishId": 1,
                "finishIdSerialized": True,
            }, {
                "optionId": "option_dlg_gm01m25_3_1_002",
                "targetKind": "finish",
                "finishId": None,
                "finishIdSerialized": False,
            }),
        },),
    },
    "dlg_gm01m26_1": {
        "missionId": "gm01m26",
        "filename": "dlg_gm01m26_1_p84AB417C755724F4.json",
        "sha256":
            "CA6AE7B5B260F0109F8F3C6F926C4DE9798409F77405F111A1935F31C2D51903",
        "extraConfigFilename":
            "dlg_gm01m26_1_extra_config_pD89622849551AACA.json",
        "extraConfigSha256":
            "6C932CE0A3060D33116B68F43BE6B6E967E9844D504403E11ABE3B84618ABD5F",
        "lineIds": tuple(
            f"dlg_gm01m26_1_{number:03d}" for number in range(9, 22)
        ),
        "optionIds": tuple(
            f"option_dlg_gm01m26_1_1_{number:03d}"
            for number in (1, 3, 4)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m26_1_{number:03d}" for number in range(9, 22)
        ),
        "treeBranchGroups": ({
            "optionGroup": 1,
            "optionIds": (
                "option_dlg_gm01m26_1_1_001",
                "option_dlg_gm01m26_1_1_003",
                "option_dlg_gm01m26_1_1_004",
            ),
            "targetLineIds": (
                "dlg_gm01m26_1_014",
                "dlg_gm01m26_1_017",
                "dlg_gm01m26_1_009",
            ),
            "routeKind": "authored_split",
        },),
    },
    "dlg_gm01m26_2": {
        "missionId": "gm01m26",
        "filename": "dlg_gm01m26_2_p679A1BBCA360401E.json",
        "sha256":
            "E2A19D27A11E9D065492807192B033124D2DCCFB305C2B3F29BD9A1F4673F086",
        "extraConfigFilename":
            "dlg_gm01m26_2_extra_config_pD55EAC322AD2673B.json",
        "extraConfigSha256":
            "CC2A6D98C9ED66647498A29C22621CD63DEDF97CAA2D6276D1817A8060BF57D8",
        "lineIds": tuple(
            f"dlg_gm01m26_2_{number:03d}" for number in range(1, 4)
        ),
        "optionIds": tuple(
            f"option_dlg_gm01m26_2_1_{number:03d}" for number in range(1, 3)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m26_2_{number:03d}" for number in range(1, 4)
        ),
        "terminalOptionRoutes": ({
            "optionGroup": 1,
            "routes": ({
                "optionId": "option_dlg_gm01m26_2_1_001",
                "targetKind": "finish",
                "finishId": 1,
                "finishIdSerialized": True,
            }, {
                "optionId": "option_dlg_gm01m26_2_1_002",
                "targetKind": "finish",
                "finishId": None,
                "finishIdSerialized": False,
            }),
        },),
    },
    "dlg_gm01m26_3": {
        "missionId": "gm01m26",
        "filename": "dlg_gm01m26_3_p0B7B834EB62EDD5D.json",
        "sha256":
            "216CC8DC7363291868940FAEED5398C5F54F1AEB2AE74A78E978934B06025326",
        "extraConfigFilename":
            "dlg_gm01m26_3_extra_config_p3433C90175C7C10D.json",
        "extraConfigSha256":
            "B17C9F79C0D8F3BBA3ED807280C571D4100D6214DEDAD649EA0C8CEF7C81E7DE",
        "lineIds": tuple(
            f"dlg_gm01m26_3_{number:03d}" for number in range(1, 4)
        ),
        "optionIds": tuple(
            f"option_dlg_gm01m26_3_1_{number:03d}" for number in range(1, 3)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m26_3_{number:03d}" for number in range(1, 4)
        ),
        "terminalOptionRoutes": ({
            "optionGroup": 1,
            "routes": ({
                "optionId": "option_dlg_gm01m26_3_1_001",
                "targetKind": "finish",
                "finishId": 1,
                "finishIdSerialized": True,
            }, {
                "optionId": "option_dlg_gm01m26_3_1_002",
                "targetKind": "finish",
                "finishId": None,
                "finishIdSerialized": False,
            }),
        },),
    },
    "dlg_gm01m26_5": {
        "missionId": "gm01m26",
        "filename": "dlg_gm01m26_5_p3E79AC01BA5A94CF.json",
        "sha256":
            "4F1F0BB5E3D43D7E5AB2D5B2AE8FDF684929D1A35C112EB320B4794A22D2694C",
        "extraConfigFilename":
            "dlg_gm01m26_5_extra_config_p30D7F99DBF5386DA.json",
        "extraConfigSha256":
            "48320DB9CEA242FBB8E419D6CDEB4EC052DA1BEBC8DD0D8A25E4966FF7F68709",
        "lineIds": tuple(
            f"dlg_gm01m26_5_{number:03d}"
            for number in (1, 2, 6, 7, 8, 14, 15, 16)
        ),
        "optionIds": tuple(
            f"option_dlg_gm01m26_5_1_{number:03d}"
            for number in (1, 3, 4)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m26_5_{number:03d}"
            for number in (1, 2, 6, 7, 8, 14, 15, 16)
        ),
        "treeBranchGroups": ({
            "optionGroup": 1,
            "optionIds": (
                "option_dlg_gm01m26_5_1_001",
                "option_dlg_gm01m26_5_1_003",
                "option_dlg_gm01m26_5_1_004",
            ),
            "targetLineIds": (
                "dlg_gm01m26_5_014",
                "dlg_gm01m26_5_006",
                "dlg_gm01m26_5_008",
            ),
            "routeKind": "authored_split",
        },),
    },
})
OFFLINE_EXHAUSTION_POSITIVE_DIALOG_KEYS = frozenset({
    "dlg_e10m3_9",
    "dlg_e11m5_9",
    "dlg_e11m8_9",
})
OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS = {
    "dlg_gm01m12_8": {
        "missionId": "gm01m12",
        "dialogIdRegistrationStatus": "absent",
        "lineIds": tuple(
            f"dlg_gm01m12_8_{number:03d}" for number in range(1, 7)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m12_8_{number:03d}" for number in range(1, 7)
        ),
        "optionRows": {
            "option_dlg_gm01m12_8_1_001": {
                "iconType": "Default",
                "optionText": {"id": 180588015484261940, "text": ""},
            },
            "option_dlg_gm01m12_8_1_002": {
                "iconType": "Default",
                "optionText": {"id": -1365299828596346002, "text": ""},
            },
            "option_dlg_gm01m12_8_1_003": {
                "iconType": "Default",
                "optionText": {"id": -5116520205592897546, "text": ""},
            },
            "option_dlg_gm01m12_8_2_001": {
                "iconType": "Default",
                "optionText": {"id": 1507979733122474165, "text": ""},
            },
            "option_dlg_gm01m12_8_2_002": {
                "iconType": "Default",
                "optionText": {"id": 8277868852189869355, "text": ""},
            },
        },
    },
    "dlg_gm02m2_1": {
        "missionId": "gm02m2",
        "dialogIdRegistrationStatus": "present_table_only",
        "lineIds": tuple(
            f"dlg_gm02m2_1_{number:03d}" for number in range(1, 8)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm02m2_1_{number:03d}" for number in range(1, 8)
        ),
        "optionRows": {
            "option_dlg_gm02m2_1_1_001": {
                "iconType": "Default",
                "optionText": {"id": 1005686289051488859, "text": ""},
            },
            "option_dlg_gm02m2_1_2_001": {
                "iconType": "Default",
                "optionText": {"id": 451515391251513941, "text": ""},
            },
            "option_dlg_gm02m2_1_3_001": {
                "iconType": "Default",
                "optionText": {"id": -5322096947619821327, "text": ""},
            },
        },
    },
    "dlg_gm02m2_2": {
        "missionId": "gm02m2",
        "dialogIdRegistrationStatus": "present_table_only",
        "lineIds": ("dlg_gm02m2_2_001",),
        "missingAudioIds": ("au_dlg_gm02m2_2_001",),
        "optionRows": {
            "option_dlg_gm02m2_2_1_001": {
                "iconType": "Default",
                "optionText": {"id": -477720497132806138, "text": ""},
            },
            "option_dlg_gm02m2_2_1_002": {
                "iconType": "Default",
                "optionText": {"id": -1825776472958836845, "text": ""},
            },
        },
    },
    "dlg_gm02m2_3": {
        "missionId": "gm02m2",
        "dialogIdRegistrationStatus": "present_table_only",
        "lineIds": tuple(
            f"dlg_gm02m2_3_{number:03d}" for number in range(1, 6)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm02m2_3_{number:03d}" for number in range(1, 6)
        ),
        "optionRows": {
            "option_dlg_gm02m2_3_1_001": {
                "iconType": "Default",
                "optionText": {"id": -5736142493487414003, "text": ""},
            },
            "option_dlg_gm02m2_3_2_001": {
                "iconType": "Default",
                "optionText": {"id": -3823516309636354685, "text": ""},
            },
            "option_dlg_gm02m2_3_2_002": {
                "iconType": "Default",
                "optionText": {"id": -2598838857313388174, "text": ""},
            },
        },
    },
    "dlg_gm02m2_4": {
        "missionId": "gm02m2",
        "dialogIdRegistrationStatus": "present_table_only",
        "lineIds": tuple(
            f"dlg_gm02m2_4_{number:03d}" for number in range(1, 4)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm02m2_4_{number:03d}" for number in range(1, 4)
        ),
        "optionRows": {
            "option_dlg_gm02m2_4_1_001": {
                "iconType": "Default",
                "optionText": {"id": -6194702338391986197, "text": ""},
            },
        },
    },
    "dlg_gm02m3_1": {
        "missionId": "gm02m3",
        "dialogIdRegistrationStatus": "present_table_only",
        "lineIds": tuple(
            f"dlg_gm02m3_1_{number:03d}" for number in range(5, 17)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm02m3_1_{number:03d}" for number in range(5, 17)
        ),
        "printableOnlyDialogTokens": (
            "dlg_gm02m3_1X",
            "dlg_gm02m3_1Y",
        ),
        "optionRows": {
            "option_dlg_gm02m3_1_1_001": {
                "iconType": "Default",
                "optionText": {"id": -3828274658471633553, "text": ""},
            },
            "option_dlg_gm02m3_1_1_003": {
                "iconType": "main",
                "optionText": {"id": 8683254705963111422, "text": ""},
            },
            "option_dlg_gm02m3_1_1_004": {
                "iconType": "Default",
                "optionText": {"id": 6923242290816326074, "text": ""},
            },
        },
    },
    "dlg_gm02m3_2": {
        "missionId": "gm02m3",
        "dialogIdRegistrationStatus": "present_table_only",
        "lineIds": tuple(
            f"dlg_gm02m3_2_{number:03d}" for number in range(1, 5)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm02m3_2_{number:03d}" for number in range(1, 5)
        ),
        "printableOnlyDialogTokens": (
            "dlg_gm02m3_2Y",
            "dlg_gm02m3_2Z",
        ),
        "optionRows": {
            "option_dlg_gm02m3_2_1_001": {
                "iconType": "Default",
                "optionText": {"id": -1637408631732126940, "text": ""},
            },
            "option_dlg_gm02m3_2_1_002": {
                "iconType": "Default",
                "optionText": {"id": -1214579014914497398, "text": ""},
            },
        },
    },
    "dlg_gm02m3_3": {
        "missionId": "gm02m3",
        "dialogIdRegistrationStatus": "present_table_only",
        "lineIds": tuple(
            f"dlg_gm02m3_3_{number:03d}" for number in range(1, 4)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm02m3_3_{number:03d}" for number in range(1, 4)
        ),
        "printableOnlyDialogTokens": (
            "dlg_gm02m3_3Z",
            "dlg_gm02m3_3d",
        ),
        "optionRows": {
            "option_dlg_gm02m3_3_1_001": {
                "iconType": "Default",
                "optionText": {"id": 3658541488536480160, "text": ""},
            },
            "option_dlg_gm02m3_3_1_002": {
                "iconType": "Default",
                "optionText": {"id": -6519032108786470153, "text": ""},
            },
        },
    },
    "dlg_gm02m3_4": {
        "missionId": "gm02m3",
        "lineIds": tuple(
            f"dlg_gm02m3_4_{number:03d}" for number in range(1, 5)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm02m3_4_{number:03d}" for number in range(1, 5)
        ),
        "optionRows": {},
    },
    "dlg_gm02m3_5": {
        "missionId": "gm02m3",
        "lineIds": tuple(
            f"dlg_gm02m3_5_{number:03d}" for number in range(1, 8)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm02m3_5_{number:03d}" for number in range(1, 8)
        ),
        "optionRows": {
            "option_dlg_gm02m3_5_1_001": {
                "iconType": "Default",
                "optionText": {"id": -7430164597458610152, "text": ""},
            },
            "option_dlg_gm02m3_5_1_003": {
                "iconType": "main",
                "optionText": {"id": -5398790576921489908, "text": ""},
            },
            "option_dlg_gm02m3_5_1_004": {
                "iconType": "Default",
                "optionText": {"id": -2526259664854754454, "text": ""},
            },
        },
    },
    "dlg_a1m11_3": {
        "missionId": "a1m11",
        "lineIds": ("dlg_a1m11_3_001",),
        "missingAudioIds": ("au_dlg_a1m11_3_001",),
        "optionRows": {
            "option_dlg_a1m11_3_1_001": {
                "iconType": "activity_openui",
                "optionText": {
                    "id": 4913019528184533200,
                    "text": "",
                },
            },
            "option_dlg_a1m11_3_1_002": {
                "iconType": "exit",
                "optionText": {
                    "id": 6553332152207896152,
                    "text": "",
                },
            },
        },
    },
    "dlg_a1m7_2": {
        "missionId": "a1m7",
        "lineIds": (
            "dlg_a1m7_2_001",
            "dlg_a1m7_2_002",
        ),
        "missingAudioIds": (
            "au_dlg_a1m7_2_001",
            "au_dlg_a1m7_2_002",
        ),
        "optionRows": {
            "option_dlg_a1m7_2_1_001": {
                "iconType": "Default",
                "optionText": {
                    "id": -7326389481153936424,
                    "text": "",
                },
            },
            "option_dlg_a1m7_2_2_001": {
                "iconType": "Default",
                "optionText": {
                    "id": 3896246422494591643,
                    "text": "",
                },
            },
            "option_dlg_a1m7_2_2_002": {
                "iconType": "Default",
                "optionText": {
                    "id": 3120352741321777196,
                    "text": "",
                },
            },
        },
    },
    "dlg_a1m7_12": {
        "missionId": "a1m7",
        "lineIds": (
            "dlg_a1m7_12_001",
            "dlg_a1m7_12_002",
            "dlg_a1m7_12_003",
        ),
        "missingAudioIds": (
            "au_dlg_a1m7_12_001",
            "au_dlg_a1m7_12_002",
            "au_dlg_a1m7_12_003",
        ),
        "optionRows": {},
    },
    "dlg_a1m5_5": {
        "missionId": "a1m5",
        "lineIds": (
            "dlg_a1m5_5_001",
            "dlg_a1m5_5_002",
        ),
        "missingAudioIds": (
            "au_dlg_a1m5_5_001",
            "au_dlg_a1m5_5_002",
        ),
        "allowedNonOwningRoute": {
            "relation": "dialog_tree_reachable_story_playback",
            "direction": "context",
            "phase": "dialog_tree_story_playback",
            "confidence": "native_exact_cross_story_quest_state_context",
            "storyOwnerMission": "a1m5",
            "parentStoryKey": "dlg_a1m5_2",
            "dependencyOnly": True,
            "ownership": False,
        },
        "nonOwningContext": {
            "parentStoryKey": "dlg_a1m5_2",
            "candidateQuestIds": (
                "a1m5_q#4",
                "a1m5_q#5",
                "a1m5_q#8",
                "a1m5_q#10",
                "a1m5_q#12",
                "a1m5_q#14",
                "a1m5_q#16",
            ),
            "targetQuestState": 2,
            "conditionEvalString": "{0} or {1} or {2} or {3} or {4} or {5} or {6}",
            "sourceFile": (
                "export_full/recovered/AnimeStudio-cli/StreamingAssets/"
                "json_by_type/TextAsset/"
                "dlg_a1m5_2_p28C9B9297D5DAF06.json"
            ),
        },
    },
    "dlg_e11m8d5_2": {
        "missionId": "e11m8d5",
        "lineIds": (
            "dlg_e11m8d5_2_001",
            "dlg_e11m8d5_2_002",
        ),
        "missingAudioIds": (
            "au_dlg_e11m8d5_2_001",
            "au_dlg_e11m8d5_2_002",
        ),
    },
    "dlg_e3m4_9": {
        "missionId": "e3m4",
        "lineIds": ("dlg_e3m4_9_001",),
        "missingAudioIds": ("au_dlg_e3m4_9_001",),
    },
    "dlg_e10m4_16": {
        "missionId": "e10m4",
        "lineIds": (
            "dlg_e10m4_16_001",
            "dlg_e10m4_16_002",
        ),
        "audioVariants": {
            "au_dlg_e10m4_16_001": (
                "au_dlg_e10m4_16_001_f",
                "au_dlg_e10m4_16_001_m",
            ),
        },
        "missingAudioIds": (),
    },
    "dlg_e10m4_17": {
        "missionId": "e10m4",
        "lineIds": (
            "dlg_e10m4_17_001",
            "dlg_e10m4_17_002",
        ),
        "missingAudioIds": (
            "au_dlg_e10m4_17_001",
            "au_dlg_e10m4_17_002",
        ),
    },
    "dlg_e10m3_10": {
        "missionId": "e10m3",
        "lineIds": (
            "dlg_e10m3_10_001",
            "dlg_e10m3_10_002",
            "dlg_e10m3_10_003",
            "dlg_e10m3_10_004",
            "dlg_e10m3_10_006",
            "dlg_e10m3_10_007",
            "dlg_e10m3_10_009",
            "dlg_e10m3_10_010",
        ),
        "missingAudioIds": (
            "au_dlg_e10m3_10_001",
            "au_dlg_e10m3_10_002",
            "au_dlg_e10m3_10_003",
            "au_dlg_e10m3_10_004",
            "au_dlg_e10m3_10_006",
            "au_dlg_e10m3_10_007",
            "au_dlg_e10m3_10_009",
            "au_dlg_e10m3_10_010",
        ),
    },
    "dlg_e10m3_11": {
        "missionId": "e10m3",
        "lineIds": tuple(
            f"dlg_e10m3_11_{number:03d}" for number in range(1, 5)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_e10m3_11_{number:03d}" for number in range(1, 5)
        ),
    },
    "dlg_e10m3_12": {
        "missionId": "e10m3",
        "lineIds": tuple(
            f"dlg_e10m3_12_{number:03d}" for number in range(1, 17)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_e10m3_12_{number:03d}" for number in range(1, 17)
        ),
    },
    "dlg_e2m6_18": {
        "missionId": "e2m6",
        "lineIds": tuple(
            f"dlg_e2m6_18_{number:03d}" for number in range(1, 8)
        ),
        "missingAudioIds": (),
    },
    "dlg_e11m8_13": {
        "missionId": "e11m8",
        "lineIds": ("dlg_e11m8_13_001",),
        "missingAudioIds": (),
    },
    "dlg_e11m8_14": {
        "missionId": "e11m8",
        "lineIds": ("dlg_e11m8_14_001",),
        "missingAudioIds": (),
    },
}
OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS.update({
    "dlg_gm01m24_5": {
        "missionId": "gm01m24",
        "dialogIdRegistrationStatus": "absent",
        "lineIds": tuple(
            f"dlg_gm01m24_5_{number:03d}" for number in range(1, 9)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m24_5_{number:03d}" for number in range(1, 9)
        ),
        "optionRows": {
            "option_dlg_gm01m24_5_1_001": {
                "iconType": "Default",
                "optionText": {"id": 8992213548012664663, "text": ""},
            },
            "option_dlg_gm01m24_5_1_003": {
                "iconType": "main",
                "optionText": {"id": -8305820588426344756, "text": ""},
            },
            "option_dlg_gm01m24_5_1_004": {
                "iconType": "Default",
                "optionText": {"id": -4851703353575780175, "text": ""},
            },
        },
    },
    "dlg_gm01m25_5": {
        "missionId": "gm01m25",
        "dialogIdRegistrationStatus": "absent",
        "lineIds": tuple(
            f"dlg_gm01m25_5_{number:03d}"
            for number in (1, 2, *range(6, 12))
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m25_5_{number:03d}"
            for number in (1, 2, *range(6, 12))
        ),
        "optionRows": {
            "option_dlg_gm01m25_5_1_001": {
                "iconType": "Default",
                "optionText": {"id": -4403692503426426134, "text": ""},
            },
            "option_dlg_gm01m25_5_1_003": {
                "iconType": "main",
                "optionText": {"id": -2179532275863901932, "text": ""},
            },
            "option_dlg_gm01m25_5_1_004": {
                "iconType": "Default",
                "optionText": {"id": 5754714993178035148, "text": ""},
            },
        },
    },
})
OFFLINE_EXHAUSTION_DIALOG_ROW_FIELDS = frozenset({
    "actorName",
    "actorNameId",
    "audioEffect",
    "audioOverride",
    "dialogText",
    "emotionType",
    "hideHint",
    "hint",
})
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
OFFLINE_EXHAUSTION_E11M6_RADIOS = frozenset({
    "radio_e11m6_10",
    "radio_e11m6_13",
    *{
        f"radio_e11m6_{number}"
        for number in range(19, 39)
    },
})
OFFLINE_EXHAUSTION_E11M2_RADIOS = frozenset({
    "radio_e11m2_22",
    "radio_e11m2_25",
    "radio_e11m2_27",
    "radio_e11m2_30",
    "radio_e11m2_33",
    "radio_e11m2_34",
    "radio_e11m2_35",
    "radio_e11m2_36",
    "radio_e11m2_37",
})
OFFLINE_EXHAUSTION_E11M5_RADIOS = frozenset({
    "radio_e11m5_12",
    "radio_e11m5_19",
    "radio_e11m5_20",
    "radio_e11m5_21",
    "radio_e11m5_22",
    "radio_e11m5_23",
    "radio_e11m5_24",
})
OFFLINE_EXHAUSTION_E9M2_RADIOS = frozenset({
    "radio_e9m2_12",
    "radio_e9m2_33",
    "radio_e9m2_34",
    "radio_e9m2_41",
    "radio_e9m2_44",
    "radio_e9m2_49",
    "radio_e9m2_50",
    "radio_e9m2_51",
})
OFFLINE_EXHAUSTION_E9M3_RADIOS = frozenset({
    "radio_e9m3_3",
    "radio_e9m3_7",
    "radio_e9m3_8",
    "radio_e9m3_9",
    "radio_e9m3_13",
    "radio_e9m3_20",
    "radio_e9m3_22",
})
OFFLINE_EXHAUSTION_E9M4_RADIOS = frozenset({
    "radio_e9m4_1",
    "radio_e9m4_4d5",
})
OFFLINE_EXHAUSTION_E6M3_RADIOS = frozenset({
    "radio_e6m3_10d6",
    "radio_e6m3_21",
    "radio_e6m3_22",
    "radio_e6m3_23",
})
OFFLINE_EXHAUSTION_E1M2_RADIOS = frozenset({
    "radio_e1m2_2d5",
    "radio_e1m2_3d5",
    "radio_e1m2_5",
    "radio_e1m2_7d7",
})
OFFLINE_EXHAUSTION_E1M3_RADIOS = frozenset({
    "radio_e1m3_3",
    "radio_e1m3_4",
    "radio_e1m3_7",
    "radio_e1m3_18",
})
OFFLINE_EXHAUSTION_E1M4_RADIOS = frozenset({
    "radio_e1m4_0d5",
    "radio_e1m4_1d5",
    "radio_e1m4_2d5",
})
OFFLINE_EXHAUSTION_E1M5_RADIOS = frozenset({"radio_e1m5_3d5"})
OFFLINE_EXHAUSTION_E1M6_RADIOS = frozenset({"radio_e1m6_2"})
OFFLINE_EXHAUSTION_E1M10_RADIOS = frozenset({
    "radio_e1m10_0d2",
})
OFFLINE_EXHAUSTION_E7M2_RADIOS = frozenset({
    "radio_e7m2_2",
    "radio_e7m2_9",
    "radio_e7m2_12",
    "radio_e7m2_18",
})
OFFLINE_EXHAUSTION_E6M4_RADIOS = frozenset({
    "radio_e6m4_5",
    "radio_e6m4_9",
    "radio_e6m4_15",
    "radio_e6m4_25",
    "radio_e6m4_35",
    "radio_e6m4_36",
    "radio_e6m4_37",
})
OFFLINE_EXHAUSTION_E6M5_RADIOS = frozenset({"radio_e6m5_4"})
OFFLINE_EXHAUSTION_E7M3_RADIOS = frozenset({
    "radio_e7m3_16",
    "radio_e7m3_26",
})
OFFLINE_EXHAUSTION_E11M3_RADIOS = frozenset({
    "radio_e11m3_3",
    "radio_e11m3_15",
    "radio_e11m3_18",
    "radio_e11m3_22",
    "radio_e11m3_23",
})
OFFLINE_EXHAUSTION_E11M8_RADIOS = frozenset({"radio_e11m8_5"})
OFFLINE_EXHAUSTION_E3M2_RADIOS = frozenset({
    "radio_e3m2_0d5",
    "radio_e3m2_4d5",
})
OFFLINE_EXHAUSTION_E3M1_RADIOS = frozenset({"radio_e3m1_3"})
OFFLINE_EXHAUSTION_E3M3_RADIOS = frozenset({
    "radio_e3m3_1d5",
    "radio_e3m3_1d7",
    "radio_e3m3_2",
    "radio_e3m3_2d5",
    "radio_e3m3_3",
    "radio_e3m3_4d5",
    "radio_e3m3_5",
    "radio_e3m3_6",
})
OFFLINE_EXHAUSTION_E0M0_RADIOS = frozenset({
    "radio_e0m0_9d5",
    "radio_e0m0_10",
    "radio_e0m0_21",
})
OFFLINE_EXHAUSTION_E2M4_RADIOS = frozenset({
    "radio_e2m4_4",
    "radio_e2m4_5d5",
    "radio_e2m4_11",
    "radio_e2m4_14",
    "radio_e2m4_15",
    "radio_e2m4_19",
    "radio_e2m4_22",
})
OFFLINE_EXHAUSTION_E2M5_RADIOS = frozenset({
    "radio_e2m5_5",
    "radio_e2m5_27",
    "radio_e2m5_29",
})
OFFLINE_EXHAUSTION_E2M6_RADIOS = frozenset({
    "radio_e2m6_2",
    "radio_e2m6_7d2",
    "radio_e2m6_7d4",
})
OFFLINE_EXHAUSTION_E2M7_RADIOS = frozenset({
    "radio_e2m7_9",
    "radio_e2m7_10",
    "radio_e2m7_16",
})
OFFLINE_EXHAUSTION_E2M2_RADIOS = frozenset({"radio_e2m2_7"})
OFFLINE_EXHAUSTION_E2M3_RADIOS = frozenset({
    "radio_e2m3_4",
    "radio_e2m3_6",
    "radio_e2m3_15",
})
OFFLINE_EXHAUSTION_E5M2_RADIOS = frozenset({"radio_e5m2_3"})
OFFLINE_EXHAUSTION_E5M3_RADIOS = frozenset({"radio_e5m3_14"})
OFFLINE_EXHAUSTION_E5M4_RADIOS = frozenset({
    "radio_e5m4_1",
    "radio_e5m4_1d5",
    "radio_e5m4_2",
})
OFFLINE_EXHAUSTION_E5M1_RADIOS = frozenset({
    "radio_e5m1_7",
    "radio_e5m1_10d8",
    "radio_e5m1_12",
    "radio_e5m1_15",
})
OFFLINE_EXHAUSTION_E5M5_RADIOS = frozenset({
    "radio_e5m5_1",
    "radio_e5m5_2",
})
OFFLINE_EXHAUSTION_E6M1_RADIOS = frozenset({
    "radio_e6m1_19",
})
OFFLINE_EXHAUSTION_E6M2_RADIOS = frozenset({
    "radio_e6m2_3",
    "radio_e6m2_7",
})
OFFLINE_EXHAUSTION_E3M4_RADIOS = frozenset({
    "radio_e3m4_1",
    "radio_e3m4_2",
})
OFFLINE_EXHAUSTION_E4M1_RADIOS = frozenset({
    "radio_e4m1_106",
    "radio_e4m1_107",
})
OFFLINE_EXHAUSTION_E4M1D5_RADIOS = frozenset({"radio_e4m1d5_3"})
OFFLINE_EXHAUSTION_E7M4_RADIOS = frozenset({"radio_e7m4_3"})
OFFLINE_EXHAUSTION_E8M2_RADIOS = frozenset({
    "radio_e8m2_1",
    "radio_e8m2_9",
    "radio_e8m2_15",
    "radio_e8m2_16",
})
OFFLINE_EXHAUSTION_E8M1_RADIOS = frozenset({"radio_e8m1_9"})
OFFLINE_EXHAUSTION_E8M3_RADIOS = frozenset({"radio_e8m3_27"})
OFFLINE_EXHAUSTION_E8M5_RADIOS = frozenset({"radio_e8m5_4"})
OFFLINE_EXHAUSTION_E10M1_RADIOS = frozenset({
    "radio_e10m1_6",
    "radio_e10m1_9",
})
OFFLINE_EXHAUSTION_E10M2_RADIOS = frozenset({"radio_e10m2_1"})
OFFLINE_EXHAUSTION_A1M6D1_RADIOS = frozenset({"radio_a1m6d1_2"})
OFFLINE_EXHAUSTION_A1M6D2_RADIOS = frozenset({"radio_a1m6d2_1"})
OFFLINE_EXHAUSTION_A1M6D3_RADIOS = frozenset({"radio_a1m6d3_1"})
OFFLINE_EXHAUSTION_A1M8D3_RADIOS = frozenset({"radio_a1m8d3_1"})
OFFLINE_EXHAUSTION_GM02M2_RADIOS = frozenset({
    "radio_gm02m2_1",
    "radio_gm02m2_2",
    "radio_gm02m2_2d5",
    "radio_gm02m2_3",
    "radio_gm02m2_4",
    "radio_gm02m2_5",
    "radio_gm02m2_6",
    "radio_gm02m2_7",
    "radio_gm02m2_10",
})
OFFLINE_EXHAUSTION_GM02M3_RADIOS = frozenset({
    "radio_gm02m3_1",
    "radio_gm02m3_2",
    "radio_gm02m3_3",
    "radio_gm02m3_4",
    "radio_gm02m3_5",
})
OFFLINE_EXHAUSTION_GM01M6_RADIOS = frozenset({
    "radio_gm01m6_0d5",
    "radio_gm01m6_4d5",
    "radio_gm01m6_6",
})
OFFLINE_EXHAUSTION_GM01M7_RADIOS = frozenset({"radio_gm01m7_9"})
OFFLINE_EXHAUSTION_GM01M16_RADIOS = frozenset({
    "radio_gm01m16_8",
    "radio_gm01m16_13",
    "radio_gm01m16_14",
})
OFFLINE_EXHAUSTION_GM01M20_RADIOS = frozenset({
    "radio_gm01m20_1",
    "radio_gm01m20_2",
    "radio_gm01m20_3",
    "radio_gm01m20_4",
})
OFFLINE_EXHAUSTION_GM01M22_RADIOS = frozenset({
    "radio_gm01m22_1d2",
    "radio_gm01m22_1d3",
})
OFFLINE_EXHAUSTION_GM01M24_RADIOS = frozenset({
    "radio_gm01m24_1d5",
    "radio_gm01m24_2",
    "radio_gm01m24_3",
    "radio_gm01m24_4",
})
OFFLINE_EXHAUSTION_GM01M25_RADIOS = frozenset({
    "radio_gm01m25_1d5",
    "radio_gm01m25_2",
    "radio_gm01m25_3",
    "radio_gm01m25_4",
})
OFFLINE_EXHAUSTION_GM01M26_RADIOS = frozenset({
    "radio_gm01m26_1d5",
    "radio_gm01m26_2",
    "radio_gm01m26_3",
    "radio_gm01m26_4",
})
OFFLINE_EXHAUSTION_RADIOS_BY_MISSION = {
    "a1m6d1": OFFLINE_EXHAUSTION_A1M6D1_RADIOS,
    "a1m6d2": OFFLINE_EXHAUSTION_A1M6D2_RADIOS,
    "a1m6d3": OFFLINE_EXHAUSTION_A1M6D3_RADIOS,
    "a1m8d3": OFFLINE_EXHAUSTION_A1M8D3_RADIOS,
    "gm02m2": OFFLINE_EXHAUSTION_GM02M2_RADIOS,
    "gm02m3": OFFLINE_EXHAUSTION_GM02M3_RADIOS,
    "gm01m6": OFFLINE_EXHAUSTION_GM01M6_RADIOS,
    "gm01m7": OFFLINE_EXHAUSTION_GM01M7_RADIOS,
    "gm01m16": OFFLINE_EXHAUSTION_GM01M16_RADIOS,
    "gm01m20": OFFLINE_EXHAUSTION_GM01M20_RADIOS,
    "gm01m22": OFFLINE_EXHAUSTION_GM01M22_RADIOS,
    "gm01m24": OFFLINE_EXHAUSTION_GM01M24_RADIOS,
    "gm01m25": OFFLINE_EXHAUSTION_GM01M25_RADIOS,
    "gm01m26": OFFLINE_EXHAUSTION_GM01M26_RADIOS,
    "e0m0": OFFLINE_EXHAUSTION_E0M0_RADIOS,
    "e1m2": OFFLINE_EXHAUSTION_E1M2_RADIOS,
    "e1m3": OFFLINE_EXHAUSTION_E1M3_RADIOS,
    "e1m4": OFFLINE_EXHAUSTION_E1M4_RADIOS,
    "e1m5": OFFLINE_EXHAUSTION_E1M5_RADIOS,
    "e1m6": OFFLINE_EXHAUSTION_E1M6_RADIOS,
    "e1m10": OFFLINE_EXHAUSTION_E1M10_RADIOS,
    "e2m2": OFFLINE_EXHAUSTION_E2M2_RADIOS,
    "e2m3": OFFLINE_EXHAUSTION_E2M3_RADIOS,
    "e2m4": OFFLINE_EXHAUSTION_E2M4_RADIOS,
    "e2m5": OFFLINE_EXHAUSTION_E2M5_RADIOS,
    "e2m6": OFFLINE_EXHAUSTION_E2M6_RADIOS,
    "e2m7": OFFLINE_EXHAUSTION_E2M7_RADIOS,
    "e3m1": OFFLINE_EXHAUSTION_E3M1_RADIOS,
    "e3m2": OFFLINE_EXHAUSTION_E3M2_RADIOS,
    "e3m3": OFFLINE_EXHAUSTION_E3M3_RADIOS,
    "e3m4": OFFLINE_EXHAUSTION_E3M4_RADIOS,
    "e4m1": OFFLINE_EXHAUSTION_E4M1_RADIOS,
    "e4m1d5": OFFLINE_EXHAUSTION_E4M1D5_RADIOS,
    "e5m1": OFFLINE_EXHAUSTION_E5M1_RADIOS,
    "e5m2": OFFLINE_EXHAUSTION_E5M2_RADIOS,
    "e5m3": OFFLINE_EXHAUSTION_E5M3_RADIOS,
    "e5m4": OFFLINE_EXHAUSTION_E5M4_RADIOS,
    "e5m5": OFFLINE_EXHAUSTION_E5M5_RADIOS,
    "e6m1": OFFLINE_EXHAUSTION_E6M1_RADIOS,
    "e6m2": OFFLINE_EXHAUSTION_E6M2_RADIOS,
    "e6m3": OFFLINE_EXHAUSTION_E6M3_RADIOS,
    "e6m4": OFFLINE_EXHAUSTION_E6M4_RADIOS,
    "e6m5": OFFLINE_EXHAUSTION_E6M5_RADIOS,
    "e7m2": OFFLINE_EXHAUSTION_E7M2_RADIOS,
    "e7m3": OFFLINE_EXHAUSTION_E7M3_RADIOS,
    "e7m4": OFFLINE_EXHAUSTION_E7M4_RADIOS,
    "e8m1": OFFLINE_EXHAUSTION_E8M1_RADIOS,
    "e8m2": OFFLINE_EXHAUSTION_E8M2_RADIOS,
    "e8m3": OFFLINE_EXHAUSTION_E8M3_RADIOS,
    "e8m5": OFFLINE_EXHAUSTION_E8M5_RADIOS,
    "e9m2": OFFLINE_EXHAUSTION_E9M2_RADIOS,
    "e9m3": OFFLINE_EXHAUSTION_E9M3_RADIOS,
    "e9m4": OFFLINE_EXHAUSTION_E9M4_RADIOS,
    "e10m1": OFFLINE_EXHAUSTION_E10M1_RADIOS,
    "e10m2": OFFLINE_EXHAUSTION_E10M2_RADIOS,
    "e10m4": OFFLINE_EXHAUSTION_E10M4_RADIOS,
    "e11m1": OFFLINE_EXHAUSTION_E11M1_RADIOS,
    "e11m2": OFFLINE_EXHAUSTION_E11M2_RADIOS,
    "e11m3": OFFLINE_EXHAUSTION_E11M3_RADIOS,
    "e11m4": OFFLINE_EXHAUSTION_E11M4_RADIOS,
    "e11m5": OFFLINE_EXHAUSTION_E11M5_RADIOS,
    "e11m6": OFFLINE_EXHAUSTION_E11M6_RADIOS,
    "e11m8": OFFLINE_EXHAUSTION_E11M8_RADIOS,
}
OFFLINE_EXHAUSTION_RADIO_CONTEXTS = {
    "radio_e1m5_3d5": {
        "sourceKey": "levelData:map01_lv002/map01_lv002_lv_data",
        "sourceFile": (
            "export_full/structured/StreamingAssets/Data/Json/LevelData/"
            "map01_lv002/map01_lv002_lv_data.json"
        ),
        "sha256":
            "4342010C5E51FCC24738C0E5D4D61D42BCA2CF8B1453D574647F7CA4E1F399E1",
        "questId": "e1m5_q#8",
        "distance": 65,
        "byteStringCounts": {
            "radio_e1m5_3d5": 5,
            "e1m5_q#8": 1,
        },
        "allowedRoute": {
            "relation": "leveldata_quest_reference",
            "direction": "context",
            "phase": "context",
            "confidence": "direct",
            "levelId": "map01_lv002",
        },
    },
}
OFFLINE_EXHAUSTION_RADIO_AUDIO_VARIANTS = {
    "radio_e0m0_10": {
        f"au_radio_e0m0_10_{number:03d}": (
            f"au_radio_e0m0_10_{number:03d}_f",
            f"au_radio_e0m0_10_{number:03d}_m",
        )
        for number in range(1, 4)
    },
    "radio_e0m0_21": {
        "au_radio_e0m0_21_001": (
            "au_radio_e0m0_21_001_f",
            "au_radio_e0m0_21_001_m",
        ),
    },
    "radio_e1m4_0d5": {
        "au_radio_e1m4_0d5_001": (
            "au_radio_e1m4_0d5_001_f",
            "au_radio_e1m4_0d5_001_m",
        ),
    },
    "radio_e10m4_11": {
        "au_radio_e10m4_11_001": (
            "au_radio_e10m4_11_001_f",
            "au_radio_e10m4_11_001_m",
        ),
    },
    "radio_e10m4_38": {
        "au_radio_e10m4_38_001": (
            "au_radio_e10m4_38_001_f",
            "au_radio_e10m4_38_001_m",
        ),
    },
}
OFFLINE_EXHAUSTION_RADIO_MISSING_AUDIO_IDS = {
    "radio_a1m6d1_2": frozenset({"au_radio_a1m6d1_2_001"}),
    "radio_a1m6d2_1": frozenset({"au_radio_a1m6d2_1_001"}),
    "radio_a1m6d3_1": frozenset({"au_radio_a1m6d3_1_001"}),
    "radio_a1m8d3_1": frozenset({"au_radio_a1m8d3_1_001"}),
    "radio_gm02m2_1": frozenset(
        f"au_radio_gm02m2_1_{number:03d}" for number in range(1, 3)
    ),
    "radio_gm02m2_2": frozenset(
        f"au_radio_gm02m2_2_{number:03d}" for number in range(1, 3)
    ),
    "radio_gm02m2_2d5": frozenset(
        f"au_radio_gm02m2_2d5_{number:03d}" for number in range(1, 4)
    ),
    "radio_gm02m2_3": frozenset(
        f"au_radio_gm02m2_3_{number:03d}" for number in range(1, 3)
    ),
    "radio_gm02m2_4": frozenset({"au_radio_gm02m2_4_001"}),
    "radio_gm02m2_5": frozenset({"au_radio_gm02m2_5_001"}),
    "radio_gm02m2_6": frozenset({"au_radio_gm02m2_6_001"}),
    "radio_gm02m2_7": frozenset({"au_radio_gm02m2_7_001"}),
    "radio_gm02m2_10": frozenset(
        f"au_radio_gm02m2_10_{number:03d}" for number in range(1, 3)
    ),
    "radio_gm02m3_1": frozenset({"au_radio_gm02m3_1_001"}),
    "radio_gm02m3_2": frozenset({"au_radio_gm02m3_2_002"}),
    "radio_gm02m3_3": frozenset({"au_radio_gm02m3_3_003"}),
    "radio_gm02m3_4": frozenset({"au_radio_gm02m3_4_004"}),
    "radio_gm02m3_5": frozenset({"au_radio_gm02m3_5_001"}),
    "radio_gm01m6_0d5": frozenset({
        "au_radio_gm01m6_0d5_001",
        "au_radio_gm01m6_0d5_002",
    }),
    "radio_gm01m6_4d5": frozenset({"au_radio_gm01m6_4d5_001"}),
    "radio_gm01m6_6": frozenset({"au_radio_gm01m6_6_001"}),
    "radio_gm01m7_9": frozenset({
        f"au_radio_gm01m7_9_{number:03d}" for number in range(1, 13)
    }),
    "radio_gm01m16_8": frozenset({"au_radio_gm01m16_8_001"}),
    "radio_gm01m16_13": frozenset(
        f"au_radio_gm01m16_13_{number:03d}" for number in range(1, 4)
    ),
    "radio_gm01m16_14": frozenset({"au_radio_gm01m16_14_001"}),
    "radio_gm01m20_1": frozenset({"au_radio_gm01m20_1_001"}),
    "radio_gm01m20_2": frozenset({"au_radio_gm01m20_2_001"}),
    "radio_gm01m20_3": frozenset({"au_radio_gm01m20_3_001"}),
    "radio_gm01m20_4": frozenset({"au_radio_gm01m20_4_001"}),
    "radio_gm01m24_1d5": frozenset({"au_radio_gm01m24_1d5_001"}),
    "radio_gm01m24_2": frozenset({"au_radio_gm01m24_2_002"}),
    "radio_gm01m24_3": frozenset({"au_radio_gm01m24_3_003"}),
    "radio_gm01m24_4": frozenset({"au_radio_gm01m24_4_004"}),
    "radio_gm01m25_1d5": frozenset({"au_radio_gm01m25_1d5_001"}),
    "radio_gm01m25_2": frozenset({"au_radio_gm01m25_2_002"}),
    "radio_gm01m25_3": frozenset({"au_radio_gm01m25_3_003"}),
    "radio_gm01m25_4": frozenset({"au_radio_gm01m25_4_004"}),
    "radio_gm01m26_1d5": frozenset({"au_radio_gm01m26_1d5_001"}),
    "radio_gm01m26_2": frozenset({"au_radio_gm01m26_2_002"}),
    "radio_gm01m26_3": frozenset({"au_radio_gm01m26_3_003"}),
    "radio_gm01m26_4": frozenset({"au_radio_gm01m26_4_004"}),
    "radio_gm01m22_1d2": frozenset({"au_radio_gm01m22_1d2_001"}),
    "radio_gm01m22_1d3": frozenset({"au_radio_gm01m22_1d3_001"}),
    "radio_e5m5_1": frozenset({
        "au_radio_e5m5_1_001",
        "au_radio_e5m5_1_002",
    }),
    "radio_e5m5_2": frozenset({"au_radio_e5m5_2_001"}),
    "radio_e5m4_1": frozenset(
        f"au_radio_e5m4_1_{number:03d}"
        for number in range(1, 5)
    ),
    "radio_e5m4_1d5": frozenset(
        f"au_radio_e5m4_1d5_{number:03d}"
        for number in range(1, 4)
    ),
    "radio_e5m4_2": frozenset(
        f"au_radio_e5m4_2_{number:03d}"
        for number in range(1, 4)
    ),
}
OFFLINE_EXHAUSTION_RADIO_ROW_FIELDS = frozenset({
    "continueAfterDialog",
    "continueAfterRadio",
    "priority",
    "radioSingleDataList",
    "radioType",
})


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
OFFLINE_EXHAUSTION_TEXT_DEFINITIONS = {
    "text_gm01m12_1": {
        "missionId": "gm01m12",
        "readingPopupRowId": "text_gm01m12_1",
        "bgType": 1,
        "iconType": 1,
        "titleId": 2293272716794736060,
        "contentTextIds": (
            2793666067577584250,
            1177065351896539995,
            3116054607192772258,
            -2288554824343091267,
            -1348820074256568586,
            6247410809703034848,
        ),
        "prtsDefinition": {
            "rowId": "nar_digital_map01_research1_1_1",
            "row": {
                "contentId": "text_gm01m12_1",
                "desc": {"id": 0, "text": ""},
                "firstLvId": "digital_map01_research1_1",
                "id": "nar_digital_map01_research1_1_1",
                "name": {"id": -3440260695365784665, "text": ""},
                "order": 1,
                "overrideRadioId": "",
                "type": "text",
            },
        },
    },
    "text_gm01m12_3": {
        "missionId": "gm01m12",
        "readingPopupRows": {
            "rp_test_text_1": {
                "bgType": 0,
                "contentId": "text_gm01m12_3",
                "iconType": 1,
                "id": "rp_test_text_1",
                "overrideRadioId": "",
                "title": {"id": 0, "text": ""},
            },
            "rp_test_text_3": {
                "bgType": 2,
                "contentId": "text_gm01m12_3",
                "iconType": 0,
                "id": "rp_test_text_3",
                "overrideRadioId": "",
                "title": {"id": 0, "text": ""},
            },
        },
        "titleId": -4684272300736787803,
        "contentTextIds": (
            8714151621675154155,
            -2570004242404188716,
            7700964276903699737,
            -3617402496525378850,
            -8171718110792362214,
            -8879273103725698056,
            -5395881018091111953,
            -7199702518671668833,
            -7382605069448195347,
        ),
        "prtsReadingDefinition": {
            "rowId": "term_001_gm01m7",
            "row": {
                "list": {
                    "1": {
                        "contentId": "text_gm01m12_3",
                        "name": {"id": -4037519105218976214, "text": ""},
                        "order": 1,
                        "overrideRadioId": "",
                        "prtsId": "",
                        "subtitle": {"id": 0, "text": ""},
                        "uniqId": "term_001_gm01m7_1",
                    },
                    "2": {
                        "contentId": "text_gm01m12_4",
                        "name": {"id": 8051702914420708692, "text": ""},
                        "order": 2,
                        "overrideRadioId": "",
                        "prtsId": "",
                        "subtitle": {"id": 0, "text": ""},
                        "uniqId": "term_001_gm01m7_2",
                    },
                },
            },
        },
    },
    "text_gm01m12_5": {
        "missionId": "gm01m12",
        "readingPopupRowId": "rp_test_text_2",
        "bgType": 1,
        "iconType": 2,
        "richContentStatus": "absent",
        "contentTextIds": (),
    },
    "text_gm01m12_6": {
        "missionId": "gm01m12",
        "readingPopupRowId": "text_gm01m12_6",
        "bgType": 0,
        "iconType": 1,
        "titleId": 3976427637254295323,
        "contentTextIds": (
            7326707735276244258,
            1334924606921900205,
        ),
    },
    "text_gm01m12_7": {
        "missionId": "gm01m12",
        "readingPopupRowId": "text_gm01m12_7",
        "bgType": 0,
        "iconType": 1,
        "titleId": -7790167985152345202,
        "contentTextIds": (
            -2191157560911838532,
            -656007744742926406,
        ),
    },
    "text_gm01m7_1": {
        "missionId": "gm01m7",
        "readingPopupRowId": "text_gm01m7_1",
        "bgType": 1,
        "iconType": 1,
        "titleId": -3330387669642480022,
        "contentTextIds": (
            -5915528571394765142,
            -607617217296507689,
            8320492395787603997,
            -5031344750760939710,
            5136828325909646067,
            5299782474897035236,
            3603826759507356629,
            1049447087589480420,
            -3489542913473775155,
            5703443812336597184,
            6951779877936539235,
            -2560478141870650391,
            4693505613823197508,
        ),
    },
    "text_gm01m22_5": {
        "missionId": "gm01m22",
        "readingPopupRowId": "text_gm01m22_5",
        "bgType": 1,
        "iconType": 2,
        "titleId": -7956574651987707031,
        "contentTextIds": (
            9056785448930934737,
            -3599045778776472798,
            -8943409554594408505,
            -5685369311502986662,
        ),
    },
    "text_a1m6d5_1": {
        "missionId": "a1m6d5",
        "readingPopupRowId": "rp_text_a1m6d5_1",
        "bgType": 0,
        "iconType": 3,
        "titleId": 3721744607745831916,
        "contentTextIds": (
            -7408517779335732445,
            6495096817380252349,
            -8078140136953514928,
            -8140252314052994329,
            -6342349983915179518,
            8831008759808930696,
            -4685756133895238350,
            -9219690230359492856,
            -1181758195704643561,
            4387948783769873472,
            -143699607535162167,
            -6152714073317416528,
            -85705076186752261,
            -7240525900018077618,
        ),
    },
    "text_a1m5_1": {
        "missionId": "a1m5",
        "readingPopupRowId": "text_a1m5_1",
        "bgType": 0,
        "iconType": 0,
        "titleId": -8904306416814611456,
        "contentTextIds": (
            7065289209916235881,
            -3793799197369702242,
        ),
    },
    "text_a1m5_2": {
        "missionId": "a1m5",
        "readingPopupRowId": "text_a1m5_2",
        "bgType": 0,
        "iconType": 0,
        "titleId": -2647826485076773960,
        "contentTextIds": (145014796983259450,),
    },
    "text_a1m5_3": {
        "missionId": "a1m5",
        "readingPopupRowId": "text_a1m5_3",
        "bgType": 0,
        "iconType": 0,
        "titleId": -676517154678141545,
        "contentTextIds": (
            -4841045965292223135,
            -89499260089272388,
        ),
    },
    "text_a1m5_4": {
        "missionId": "a1m5",
        "readingPopupRowId": "text_a1m5_4",
        "bgType": 0,
        "iconType": 0,
        "titleId": 2405623048071579055,
        "contentTextIds": (-4489297013210307938,),
    },
    "text_a1m5_5": {
        "missionId": "a1m5",
        "readingPopupRowId": "text_a1m5_5",
        "bgType": 0,
        "iconType": 0,
        "titleId": 1365793654747611898,
        "contentTextIds": (
            -5413898867121804929,
            -1357598897532823788,
        ),
    },
    "text_a1m5_6": {
        "missionId": "a1m5",
        "readingPopupRowId": "text_a1m5_6",
        "bgType": 0,
        "iconType": 0,
        "titleId": 5740509153553995198,
        "contentTextIds": (1303745015045365078,),
    },
    "text_a1m5_7": {
        "missionId": "a1m5",
        "readingPopupRowId": "text_a1m5_7",
        "bgType": 0,
        "iconType": 0,
        "titleId": 2638866450720374170,
        "contentTextIds": (-7046570968636013796,),
    },
    "text_a1m9_1": {
        "missionId": "a1m9",
        "readingPopupRowId": "rp_text_a1m9_1",
        "bgType": 0,
        "iconType": 0,
        "titleId": 6133950036636760715,
        "contentTextIds": (
            4360361720766943813,
            -5286642356287476400,
        ),
    },
    "text_a1m9_2": {
        "missionId": "a1m9",
        "readingPopupRowId": "rp_text_a1m9_2",
        "bgType": 0,
        "iconType": 0,
        "titleId": -9061878788721069148,
        "contentTextIds": (
            -8710457857620610713,
            195657822153420954,
        ),
    },
    "text_a1m9_3": {
        "missionId": "a1m9",
        "readingPopupRowId": "rp_text_a1m9_3",
        "bgType": 0,
        "iconType": 0,
        "titleId": -4216673929559825878,
        "contentTextIds": (
            5233675183060561957,
            4427207018166369215,
        ),
    },
    "text_a1m9_4": {
        "missionId": "a1m9",
        "readingPopupRowId": "rp_text_a1m9_4",
        "bgType": 0,
        "iconType": 0,
        "titleId": 1447286566198348849,
        "contentTextIds": (
            1656717363105155858,
            -8370465523951817989,
        ),
    },
    "text_a1m9_5": {
        "missionId": "a1m9",
        "readingPopupRowId": "rp_text_a1m9_5",
        "bgType": 0,
        "iconType": 0,
        "titleId": -7333612545186178263,
        "contentTextIds": (
            -5168759132077193528,
            7120988803212617269,
        ),
    },
    "text_a1m9_6": {
        "missionId": "a1m9",
        "readingPopupRowId": "rp_text_a1m9_6",
        "bgType": 0,
        "iconType": 0,
        "titleId": 93296881304760627,
        "contentTextIds": (
            -5058010235124771975,
            -8995527205053721848,
        ),
    },
    "text_a1m9_7": {
        "missionId": "a1m9",
        "readingPopupRowId": "rp_text_a1m9_7",
        "bgType": 0,
        "iconType": 0,
        "titleId": -8532814195849073983,
        "contentTextIds": (
            1466176077223606619,
            4212985633755235735,
        ),
    },
    "text_e0m0_1": {
        "missionId": "e0m0",
        "readingPopupRowId": "text_e0m0_1",
        "bgType": 2,
        "iconType": 0,
        "titleId": -3638864379184205404,
        "contentTextIds": (
            2511221695470576053,
            5177474080784617714,
            8007409330529367903,
        ),
    },
    "text_e10m3_4": {
        "missionId": "e10m3",
        "readingPopupRowId": "text_e10m3_4",
        "bgType": 0,
        "iconType": 3,
        "titleId": -5418710251494718770,
        "contentTextIds": (
            -8827241115560565798, 3401144266780048260,
            -2101308974918454148, 5570283511765309427,
            6178047961822559599, -8818643026856084710,
            850312379198939459, 4060913547180972966,
            582887558014247241, -5144848699727818632,
            -1010583869551587167, 328614111041957338,
            6573251800662124396, -1591242057905168982,
            2275343241851983068, -885900605359348217,
            -2667917706143050240, 87081009426089158,
            7360346659785914719, -1527854070225454202,
            -1542198782537429374, -542349533057357304,
            7199667849336722774, 2561335607091393850,
        ),
    },
    "text_e10m3_6": {
        "missionId": "e10m3",
        "readingPopupRowId": "text_e10m3_6",
        "bgType": 0,
        "iconType": 3,
        "titleId": -8074740233441308703,
        "contentTextIds": (
            4355960837539480641,
            5185389162623878510,
            7800398873603388730,
        ),
    },
    "text_e10m3_8": {
        "missionId": "e10m3",
        "readingPopupRowId": "text_e10m3_8",
        "bgType": 0,
        "iconType": 3,
        "titleId": 5039628381429284738,
        "contentTextIds": (
            2791055190685483097,
            728539389262413568,
            5155466343858857033,
            5364191593684276737,
            930002605663977827,
            7716424929400781990,
            -3160792100437463961,
        ),
    },
    "text_e10m4_1": {
        "missionId": "e10m4",
        "readingPopupRowId": "rp_text_e10m4_1",
        "bgType": 0,
        "iconType": 3,
        "titleId": -3224153425811396292,
        "contentTextIds": (
            6210860659101700604,
            -4533903028538338649,
        ),
    },
    "text_e6m3_1": {
        "missionId": "e6m3",
        "readingPopupRowId": "text_e6m3_1",
        "bgType": 1,
        "iconType": 3,
        "titleId": -166052796557014664,
        "contentTextIds": (
            -1945154020598643100,
            -9052274316405367490,
            3894316646028624580,
            -984061992837130580,
        ),
    },
    "text_e6m3_4": {
        "missionId": "e6m3",
        "readingPopupRowId": "rp_text_e6m3_4",
        "bgType": 2,
        "iconType": 3,
        "titleId": 9138086639682545558,
        "contentTextIds": (
            -1462227912355393055,
            3546372858747322539,
        ),
    },
    "text_e8m4_1": {
        "missionId": "e8m4",
        "readingPopupRowId": "rp_text_e8m4_1",
        "bgType": 0,
        "iconType": 0,
        "titleId": -1501744430170614848,
        "contentTextIds": (
            -2333372693013596797,
            7514769952417356497,
            -7329223948121738333,
            -6955748145096260696,
        ),
        "prtsDefinition": {
            "rowId": "nar_collection_map02_12136_1",
            "row": {
                "contentId": "text_e8m4_1",
                "desc": {"id": 0, "text": ""},
                "firstLvId": "collection_map02_12136",
                "id": "nar_collection_map02_12136_1",
                "name": {
                    "id": -6906129919037809411,
                    "text": "",
                },
                "order": 1,
                "overrideRadioId": "",
                "type": "text",
            },
        },
    },
    "text_e6m5_1": {
        "missionId": "e6m5",
        "readingPopupRowId": "rp_text_e6m5_1",
        "bgType": 2,
        "iconType": 0,
        "titleId": 5611922659515474422,
        "contentTextIds": (
            2915169207318156019,
            -3317420327824307745,
        ),
        "prtsDefinition": {
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
    },
    "text_e7m2_2": {
        "missionId": "e7m2",
        "readingPopupRowId": "rp_text_e7m2_2",
        "bgType": 0,
        "iconType": 0,
        "titleId": -7588282709172754827,
        "contentTextIds": (
            -9023359770995415827,
            7212521158429018502,
            8882406176969361569,
            -8265050631721938907,
            -3110117479021689552,
        ),
    },
    "text_e7m3_1": {
        "missionId": "e7m3",
        "readingPopupRowId": "text_e7m3_1",
        "bgType": 2,
        "iconType": 0,
        "titleId": -8375347242993854697,
        "contentTextIds": (
            -6133919335048897276,
            -1559385323000989057,
        ),
    },
    "text_e7m4_1": {
        "missionId": "e7m4",
        "readingPopupRowId": "text_e7m4_1",
        "bgType": 2,
        "iconType": 0,
        "titleId": -9107143714236678642,
        "contentTextIds": (
            -11413322245013826,
            -7389517897749196338,
        ),
    },
}


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


def build_quest_attachment_diagnostic_index(
    mission_payloads: dict[str, dict[str, Any]],
    *,
    mission_runtime_path: Path | None = None,
    levelscript_path: Path | None = None,
    source_path_overrides: dict[str, Path] | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Validate exact current-build quest/Story negative boundaries.

    These rows retire broad diagnostic co-membership from the actionable queue.
    They do not attach a quest to a Story file and do not assert chronology.
    Hash changes, generated-shape changes, or a newly recovered strict route
    reopen the quest automatically.
    """
    source_paths = {
        name: ROOT / relative_path
        for name, relative_path
        in QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS.items()
    }
    if mission_runtime_path is not None:
        source_paths["missionRuntime:e10m4d5"] = mission_runtime_path
    if levelscript_path is not None:
        source_paths[
            "levelScript:dung02_rdg002/24400000018"
        ] = levelscript_path
    source_paths.update(source_path_overrides or {})
    actual_hashes = {
        name: _sha256_file(path)
        for name, path in source_paths.items()
    }
    mismatches = sorted(
        name
        for name, expected
        in QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_HASHES.items()
        if actual_hashes.get(name) != expected
    )
    status: dict[str, Any] = {
        "mappingId": QUEST_ATTACHMENT_DIAGNOSTIC_MAPPING_ID,
        "status":
            "inactive_source_validation_failed" if mismatches else "validating",
        "sourceHashes": actual_hashes,
        "expectedSourceHashes": QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_HASHES,
        "sourceHashMismatches": mismatches,
        "graphEffect": "none",
        "queueEffect":
            "close broad diagnostic quest co-membership only while every "
            "current-build source and generated condition shape matches",
    }
    if mismatches:
        return {}, status

    source_bytes = {
        name: path.read_bytes()
        for name, path in source_paths.items()
    }
    npc_proxy_payload = read_json(
        source_paths["gameplayConfig:NpcProxyExDataTable"]
    )
    npc_proxy_table_payload = read_json(
        source_paths["gameplayConfig:NpcProxyTable"]
    )
    world_entity_registry_payload = read_json(
        source_paths["gameplayConfig:WorldEntityRegistry"]
    )

    def exact_rows(actual: Any, expected: Any) -> bool:
        if (
            not isinstance(actual, list)
            or not isinstance(expected, (list, tuple))
            or len(actual) != len(expected)
            or not all(isinstance(row, dict) for row in actual)
            or not all(isinstance(row, dict) for row in expected)
        ):
            return False
        return sorted(
            json.dumps(row, sort_keys=True, separators=(",", ":"))
            for row in actual
        ) == sorted(
            json.dumps(row, sort_keys=True, separators=(",", ":"))
            for row in expected
        )

    index: dict[str, dict[str, Any]] = {}
    validation_failures: list[str] = []
    validation_failure_details: list[dict[str, Any]] = []
    for quest_id, declaration in (
        QUEST_ATTACHMENT_DIAGNOSTIC_DECLARATIONS.items()
    ):
        payload = mission_payloads.get(declaration["mission"])
        timeline = _timeline(payload)
        flow = _flow(payload)
        timeline_quests = {
            safe_key(row.get("questId")): row
            for row in timeline.get("quests") or []
            if isinstance(row, dict) and safe_key(row.get("questId"))
        }
        flow_quests = {
            safe_key(row.get("id")): row
            for row in flow.get("quests") or []
            if isinstance(row, dict) and safe_key(row.get("id"))
        }
        quest = timeline_quests.get(quest_id)
        flow_quest = flow_quests.get(quest_id)
        objectives = quest.get("objectives") if isinstance(quest, dict) else None
        objective = (
            objectives[0]
            if isinstance(objectives, list)
            and len(objectives) == 1
            and isinstance(objectives[0], dict)
            else {}
        )
        leaves = objective.get("conditionLeaves")
        leaf = (
            leaves[0]
            if isinstance(leaves, list)
            and len(leaves) == 1
            and isinstance(leaves[0], dict)
            else {}
        )
        connections = (
            flow_quest.get("storyConnections")
            if isinstance(flow_quest, dict)
            else None
        )
        expected_source_file = declaration.get(
            "sourceFile",
            QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS[
                "missionRuntime:e10m4d5"
            ],
        )
        valid = (
            isinstance(quest, dict)
            and isinstance(flow_quest, dict)
            and safe_key((quest.get("source") or {}).get("file"))
            == expected_source_file
            and tuple(_string_list(quest.get("prevQuestIds")))
            == declaration["prevQuestIds"]
            and objective.get("index") == 1
            and safe_key(leaf.get("type")) == declaration["conditionType"]
            and set(_string_list(objective.get("conditionTypes")))
            == {declaration["conditionType"]}
        )
        validation_kind = declaration.get(
            "validationKind",
            "variant_runtime_shell",
        )
        if valid and validation_kind == "variant_runtime_shell":
            diagnostic_connections = (
                connections
                if isinstance(connections, list)
                and connections
                and all(
                    isinstance(row, dict)
                    and safe_key(row.get("relation"))
                    == "variant_runtime_attachment"
                    and safe_key(row.get("direction")) == "context"
                    and safe_key(row.get("phase")) == "context"
                    and safe_key(row.get("confidence")) == "scoped_variant"
                    and safe_key(row.get("source"))
                    == "variant MissionRuntime quest attachment"
                    and safe_key(row.get("variantMission"))
                    == declaration["variantMission"]
                    and safe_key(row.get("attachmentKind"))
                    in {"questPrev", "questSequence"}
                    for row in connections
                )
                else []
            )
            valid = (
                bool(diagnostic_connections)
                and {
                    safe_key(row.get("key"))
                    for row in diagnostic_connections
                }
                == set(declaration["diagnosticStoryKeys"])
            )
        elif valid:
            valid = exact_rows(
                connections,
                declaration.get("connectionRows") or (),
            )

        if valid and declaration["conditionType"] == (
            "CheckLevelScriptPropertyBool"
        ):
            property_values = [
                safe_key(row.get("value"))
                for row in leaf.get("propertyKeys") or []
                if isinstance(row, dict)
            ]
            script_values = [
                safe_key((row.get("value") or {}).get("scriptId"))
                for row in leaf.get("scriptIds") or []
                if isinstance(row, dict)
                and isinstance(row.get("value"), dict)
            ]
            valid = (
                property_values == [declaration["propertyKey"]]
                and script_values == [declaration["scriptId"]]
            )
        elif valid:
            comparers = [
                row.get("value")
                for row in leaf.get("comparers") or []
                if isinstance(row, dict)
            ]
            progress_values = [
                row.get("value")
                for row in leaf.get("compareValues") or []
                if isinstance(row, dict)
            ]
            valid = (
                comparers == (
                    [declaration["comparer"]]
                    if "comparer" in declaration
                    else []
                )
                and progress_values == [declaration["progressToCompare"]]
            )

        if valid and validation_kind == "property_getter_without_story_chain":
            levelscript_data = source_bytes.get(
                declaration["levelScriptSourceKey"],
                b"",
            )
            byte_counts = declaration["levelScriptByteStringCounts"]
            try:
                decoded_level = _load_levelscript_binding_data(
                    declaration["levelId"]
                )
            except Exception:
                decoded_level = None
            expected_suffix = f"/{declaration['scriptId']}.json"
            file_entries = [
                row
                for row in (
                    decoded_level.get("files") or []
                    if isinstance(decoded_level, dict)
                    else []
                )
                if str(row.get("file") or "").replace("\\", "/").endswith(
                    expected_suffix
                )
            ]
            file_entry = file_entries[0] if len(file_entries) == 1 else {}
            records = file_entry.get("records") or []
            try:
                action_map, membership_by_start = (
                    levelscript_action_map_membership(
                        levelscript_data,
                        records,
                    )
                )
            except Exception:
                action_map, membership_by_start = {}, {}

            def record_texts(record: dict[str, Any]) -> tuple[str, ...]:
                return tuple(
                    safe_key(hit.get("text"))
                    for field in ("strings", "plainStrings")
                    for hit in record.get(field) or []
                    if isinstance(hit, dict) and safe_key(hit.get("text"))
                )

            getter_records = [
                row
                for row in records
                if declaration["propertyKey"] in record_texts(row)
            ]
            expected_getter = declaration["getterRecord"]
            actual_getter = (
                {
                    "start": getter_records[0].get("start"),
                    "localId": getter_records[0].get("localId"),
                    "nextId": getter_records[0].get("nextId"),
                    "code": getter_records[0].get("code"),
                    "kind": getter_records[0].get("kind"),
                    "uid": safe_key(getter_records[0].get("uid")),
                    "membership": membership_by_start.get(
                        getter_records[0].get("start")
                    ),
                    "texts": record_texts(getter_records[0]),
                }
                if len(getter_records) == 1
                else {}
            )
            story_records_are_separate_actions = all(
                any(
                    story_key in record_texts(record)
                    and safe_key(
                        membership_by_start.get(record.get("start"))
                    ).startswith("actionList#")
                    for record in records
                )
                for story_key in declaration["diagnosticStoryKeys"]
            )
            valid = (
                all(
                    levelscript_data.count(value.encode("utf-8")) == count
                    for value, count in byte_counts.items()
                )
                and actual_getter == expected_getter
                and action_map.get("listCounts") == {
                    "actionList": 18,
                    "getterList": 5,
                    "headerList": 3,
                }
                and story_records_are_separate_actions
            )
        elif valid and validation_kind == "shared_levelscript_condition_scope":
            levelscript_data = source_bytes.get(
                declaration["levelScriptSourceKey"],
                b"",
            )
            byte_counts = declaration["levelScriptByteStringCounts"]
            exact_property_string = (
                b"\x04"
                + len(declaration["propertyKey"]).to_bytes(4, "little")
                + declaration["propertyKey"].encode("utf-8")
            )
            valid = (
                all(
                    levelscript_data.count(value.encode("utf-8")) == count
                    for value, count in byte_counts.items()
                )
                and exact_property_string not in levelscript_data
            )
        elif valid and validation_kind == "mission_bound_npc_proxy_context":
            tracking = objective.get("tracking")
            tracking_row = (
                tracking[0]
                if isinstance(tracking, list)
                and len(tracking) == 1
                and isinstance(tracking[0], dict)
                else {}
            )
            proxy_id = declaration["npcProxyId"]
            proxy_rows = (
                (npc_proxy_payload.get("data") or {}).get(proxy_id)
                if isinstance(npc_proxy_payload, dict)
                else None
            )
            proxy_dialog_rows = (
                tuple(
                    (
                        safe_key(row.get("missionId")),
                        safe_key(row.get("dialogId")),
                    )
                    for row in proxy_rows
                    if isinstance(row, dict)
                )
                if isinstance(proxy_rows, list)
                else ()
            )
            proxy_definition = (
                (npc_proxy_table_payload.get("dataTable") or {}).get(
                    proxy_id
                )
                if isinstance(npc_proxy_table_payload, dict)
                else None
            )
            world_entity = (
                (
                    world_entity_registry_payload.get(
                        "npcProxyBriefInfos"
                    )
                    or {}
                ).get(declaration["worldEntitySegmentId"])
                if isinstance(world_entity_registry_payload, dict)
                else None
            )
            leveldata_data = source_bytes.get(
                declaration["levelDataSourceKey"],
                b"",
            )
            valid = (
                safe_key(tracking_row.get("type"))
                == "NpcProxyTrackingInfo"
                and safe_key(tracking_row.get("npcProxyId")) == proxy_id
                and safe_key(tracking_row.get("scene")) == "map02_lv002"
                and exact_rows(
                    flow_quest.get("levelDataStoryRefs"),
                    declaration["levelDataStoryRefs"],
                )
                and exact_rows(
                    flow_quest.get("proxyDialogs"),
                    ({
                        "dialogId": "dlg_e10m3_2",
                        "npcProxyId": proxy_id,
                        "missionId": declaration["npcProxyMissionId"],
                        "source": (
                            "NpcProxyExDataTable.data[*].dialogId"
                        ),
                    },),
                )
                and proxy_dialog_rows
                == declaration["npcProxyDialogRows"]
                and isinstance(proxy_definition, dict)
                and proxy_definition.get("subDataParentId") == 22800780000
                and safe_key(proxy_definition.get("proxyId")) == proxy_id
                and safe_key(proxy_definition.get("levelId"))
                == "map02_lv002"
                and proxy_definition.get("position")
                == declaration["npcProxyPosition"]
                and proxy_definition.get("envTalkIds")
                == ["envTalk_e10m3_1"]
                and isinstance(world_entity, dict)
                and safe_key(world_entity.get("proxyId")) == proxy_id
                and world_entity.get("position")
                == declaration["npcProxyPosition"]
                and all(
                    leveldata_data.count(value.encode("utf-8")) == count
                    for value, count
                    in declaration["levelDataByteStringCounts"].items()
                )
            )
        elif valid and validation_kind == "weak_leveldata_context":
            tracking = objective.get("tracking")
            tracking_row = (
                tracking[0]
                if isinstance(tracking, list)
                and len(tracking) == 1
                and isinstance(tracking[0], dict)
                else {}
            )
            leveldata_data = source_bytes.get(
                declaration["levelDataSourceKey"],
                b"",
            )
            byte_counts = declaration["levelDataByteStringCounts"]
            proxy_rows = (
                (npc_proxy_payload.get("data") or {}).get(
                    declaration["npcProxyId"]
                )
                if isinstance(npc_proxy_payload, dict)
                else None
            )
            proxy_dialog_rows = (
                tuple(
                    (
                        safe_key(row.get("missionId")),
                        safe_key(row.get("dialogId")),
                    )
                    for row in proxy_rows
                    if isinstance(row, dict)
                )
                if isinstance(proxy_rows, list)
                else ()
            )
            valid = (
                safe_key(tracking_row.get("type"))
                == "NpcProxyTrackingInfo"
                and safe_key(tracking_row.get("npcProxyId"))
                == declaration["npcProxyId"]
                and exact_rows(
                    flow_quest.get("levelDataStoryRefs"),
                    declaration["levelDataStoryRefs"],
                )
                and not flow_quest.get("proxyDialogs")
                and proxy_dialog_rows
                == declaration["npcProxyDialogRows"]
                and all(
                    leveldata_data.count(value.encode("utf-8")) == count
                    for value, count in byte_counts.items()
                )
            )
        if not valid:
            validation_failures.append(quest_id)
            validation_failure_details.append({
                "validator": "questAttachmentDiagnostic",
                "gate": validation_kind,
                "questId": quest_id,
                "missionId": declaration["mission"],
                "sourcePath": expected_source_file,
                "sourceSha256": actual_hashes.get(
                    declaration.get("sourceKey", "missionRuntime:e10m4d5"),
                    "",
                ),
                "expected": {
                    "conditionType": declaration["conditionType"],
                    "prevQuestIds": list(declaration["prevQuestIds"]),
                    "diagnosticStoryKeys": list(
                        declaration["diagnosticStoryKeys"]
                    ),
                    "validationKind": validation_kind,
                },
                "actual": {
                    "conditionType": safe_key(leaf.get("type")),
                    "prevQuestIds": _string_list(
                        quest.get("prevQuestIds")
                        if isinstance(quest, dict)
                        else []
                    ),
                    "connectionStoryKeys": sorted({
                        safe_key(row.get("key"))
                        for row in connections or []
                        if isinstance(row, dict) and safe_key(row.get("key"))
                    }, key=natural_key),
                    "connectionRelations": sorted({
                        safe_key(row.get("relation"))
                        for row in connections or []
                        if isinstance(row, dict)
                        and safe_key(row.get("relation"))
                    }),
                },
            })
            continue

        shared_boundary = declaration["conditionType"] == (
            "CheckLevelScriptPropertyBool"
        )
        index[quest_id] = {
            "questId": quest_id,
            "missionId": declaration["mission"],
            "variantMissionId": declaration["variantMission"],
            "recoveryStatus": declaration["recoveryStatus"],
            "evidenceKind": declaration.get(
                "evidenceKind",
                (
                    "exact property checker plus hash-locked LevelScript "
                    "negative"
                    if shared_boundary
                    else "exact server-owned placeholder with no client "
                    "Story field"
                ),
            ),
            "conditionType": declaration["conditionType"],
            "scriptId": declaration.get("scriptId", ""),
            "propertyKey": declaration.get("propertyKey", ""),
            "diagnosticStoryKeys": list(
                declaration["diagnosticStoryKeys"]
            ),
            "sourceFile": expected_source_file,
            "levelScriptFile": declaration.get(
                "levelScriptFile",
                (
                    QUEST_ATTACHMENT_DIAGNOSTIC_SOURCE_PATHS[
                        "levelScript:dung02_rdg002/24400000018"
                    ]
                    if shared_boundary
                    else ""
                ),
            ),
            "levelDataFile": declaration.get("levelDataFile", ""),
            "relatedSourceFiles": list(
                declaration.get("relatedSourceFiles") or ()
            ),
            "propertyRecord": declaration.get("getterRecord") or {},
            "npcProxyId": declaration.get("npcProxyId", ""),
            "nativeMappingId": QUEST_ATTACHMENT_DIAGNOSTIC_MAPPING_ID,
            "graphEffect": "none",
            "attachmentBoundary": declaration.get(
                "attachmentBoundary",
                (
                    "the quest checks a named property in a script that "
                    "contains multiple Story calls, but the exact "
                    "current-build script has no matching quest id, property "
                    "key, or property-scoped Story bridge"
                    if shared_boundary
                    else "the objective is server-owned and exposes no "
                    "client-readable Story id or playback field"
                ),
            ),
            "orderBoundary": declaration.get(
                "orderBoundary",
                (
                    "shared LevelScript membership and generated "
                    "quest-sequence context do not identify which Story call, "
                    "if any, belongs to this quest"
                    if shared_boundary
                    else
                    "the generated predecessor-shell Story context is "
                    "diagnostic only and does not establish playback or order"
                ),
            ),
            "reopenWhen": declaration.get(
                "reopenWhen",
                "either source hash or generated condition shape changes, "
                "or a property/quest-scoped native playback route is "
                "recovered",
            ),
        }

    status["validationFailures"] = validation_failures
    status["validationFailureDetails"] = validation_failure_details
    status["validatedQuestIds"] = sorted(index, key=natural_key)
    status["status"] = (
        "active"
        if len(index) == len(QUEST_ATTACHMENT_DIAGNOSTIC_DECLARATIONS)
        and not validation_failures
        else "inactive_generated_shape_validation_failed"
    )
    if status["status"] != "active":
        return {}, status
    return index, status


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


def _offline_text_definition_validation_failure(
    story_key: str,
    definition: dict[str, Any],
    popup: Any,
    rich: Any,
    prts_all_item_table: dict[str, Any],
    prts_record_table: dict[str, Any],
    prts_reading_table: dict[str, Any] | None = None,
    *,
    source_paths: dict[str, Path] | None = None,
    actual_hashes: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    expected_popup_rows = definition.get("readingPopupRows")
    if not isinstance(expected_popup_rows, dict):
        popup_row_id = definition["readingPopupRowId"]
        expected_popup_rows = {
            popup_row_id: {
                "bgType": definition["bgType"],
                "contentId": story_key,
                "iconType": definition["iconType"],
                "id": popup_row_id,
                "overrideRadioId": "",
                "title": {"id": 0, "text": ""},
            },
        }
    actual_popup_rows = (
        popup if isinstance(popup, dict) and set(popup) == set(expected_popup_rows)
        else {next(iter(expected_popup_rows)): popup}
    )
    expected_content_ids = tuple(definition["contentTextIds"])
    actual_content_ids = tuple(
        item.get("content", {}).get("id")
        for item in (
            rich.get("contentList") or []
            if isinstance(rich, dict)
            else []
        )
        if isinstance(item, dict)
        and isinstance(item.get("content"), dict)
    )
    prts_definition = definition.get("prtsDefinition")
    prts_definition_valid = prts_definition is None
    if isinstance(prts_definition, dict):
        prts_row_id = safe_key(prts_definition.get("rowId"))
        expected_prts_row = prts_definition.get("row")
        prts_definition_valid = (
            bool(prts_row_id)
            and isinstance(expected_prts_row, dict)
            and prts_all_item_table.get(prts_row_id) == expected_prts_row
            and prts_record_table.get(prts_row_id) == expected_prts_row
            and expected_prts_row.get("id") == prts_row_id
            and expected_prts_row.get("contentId") == story_key
        )
    prts_reading_definition = definition.get("prtsReadingDefinition")
    prts_reading_valid = prts_reading_definition is None
    if isinstance(prts_reading_definition, dict):
        prts_reading_row_id = safe_key(prts_reading_definition.get("rowId"))
        expected_prts_reading_row = prts_reading_definition.get("row")
        prts_reading_valid = (
            bool(prts_reading_row_id)
            and isinstance(expected_prts_reading_row, dict)
            and isinstance(prts_reading_table, dict)
            and prts_reading_table.get(prts_reading_row_id)
            == expected_prts_reading_row
        )
    rich_absent = definition.get("richContentStatus") == "absent"
    valid = (
        actual_popup_rows == expected_popup_rows
        and (
            rich is None
            if rich_absent
            else (
                isinstance(rich, dict)
                and set(rich) == {"contentList", "title"}
                and rich.get("title")
                == {"id": definition["titleId"], "text": ""}
                and len(rich.get("contentList") or [])
                == len(expected_content_ids)
                and actual_content_ids == expected_content_ids
                and all(
                    item == {"content": {"id": text_id, "text": ""}}
                    for item, text_id in zip(
                        rich.get("contentList") or [],
                        expected_content_ids,
                    )
                )
            )
        )
        and prts_definition_valid
        and prts_reading_valid
    )
    if valid:
        return None
    source_paths = source_paths or {}
    actual_hashes = actual_hashes or {}
    return {
        "validator": "offlineTextDefinition",
        "gate": "exactReadingPopupAndRichContentRows",
        "storyKey": story_key,
        "missionId": definition["missionId"],
        "sourcePaths": [
            str(source_paths[name])
            for name in ("readingPopupTable", "richContentTable")
            if name in source_paths
        ],
        "sourceSha256": {
            name: actual_hashes.get(name, "")
            for name in ("readingPopupTable", "richContentTable")
        },
        "expected": {
            "popup": next(iter(expected_popup_rows.values())),
            "popupRows": expected_popup_rows,
            "richContentStatus": "absent" if rich_absent else "present",
            "richTitle": (
                None if rich_absent
                else {"id": definition["titleId"], "text": ""}
            ),
            "contentTextIds": list(expected_content_ids),
            "prtsDefinitionValid": True,
            "prtsReadingDefinitionValid": True,
        },
        "actual": {
            "popup": next(iter(actual_popup_rows.values())),
            "popupRows": actual_popup_rows,
            "richContentStatus": "absent" if rich is None else "present",
            "richTitle": rich.get("title") if isinstance(rich, dict) else None,
            "contentTextIds": list(actual_content_ids),
            "prtsDefinitionValid": prts_definition_valid,
            "prtsReadingDefinitionValid": prts_reading_valid,
        },
    }


def _dialog_tree_branch_groups(
    tree_asset: Any,
) -> list[dict[str, Any]] | None:
    """Decode exact multi-option DialogTree edges from one TextAsset.

    Connection order is paired with ``_normalOptions`` exactly as the shipped
    DialogTree runtime/parser does.  This helper deliberately accepts only
    immediate typed trunk targets: a changed or more complex graph reopens the
    recovery instead of guessing through editor layout or node-array order.
    """
    if not isinstance(tree_asset, dict):
        return None
    script = tree_asset.get("m_Script")
    if not isinstance(script, str) or not script:
        return None
    try:
        payload = json.loads(
            base64.b64decode(script, validate=True).decode("utf-8-sig")
        )
    except (
        ValueError,
        binascii.Error,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        return None
    if (
        not isinstance(payload, dict)
        or payload.get("type") != "Beyond.Gameplay.DialogTree"
        or not isinstance(payload.get("nodes"), list)
        or not isinstance(payload.get("connections"), list)
    ):
        return None
    node_by_id: dict[str, dict[str, Any]] = {}
    for node in payload["nodes"]:
        if not isinstance(node, dict) or node.get("$id") in (None, ""):
            return None
        node_id = str(node["$id"])
        if node_id in node_by_id:
            return None
        node_by_id[node_id] = node
    targets_by_source: dict[str, list[str]] = defaultdict(list)
    for connection in payload["connections"]:
        if (
            not isinstance(connection, dict)
            or connection.get("$type")
            != "Beyond.Gameplay.DialogTreeConnection"
        ):
            return None
        source = connection.get("_sourceNode")
        target = connection.get("_targetNode")
        source_id = (
            str(source.get("$ref") or "")
            if isinstance(source, dict) else ""
        )
        target_id = (
            str(target.get("$ref") or "")
            if isinstance(target, dict) else ""
        )
        if source_id not in node_by_id or target_id not in node_by_id:
            return None
        targets_by_source[source_id].append(target_id)

    groups: list[dict[str, Any]] = []
    for node_id, node in node_by_id.items():
        option_rows = [
            row
            for row in node.get("_normalOptions") or []
            if isinstance(row, dict) and safe_key(row.get("_optionId"))
        ]
        if len(option_rows) <= 1:
            continue
        option_ids = [safe_key(row["_optionId"]) for row in option_rows]
        group_matches = [
            re.search(r"_(\d+)_\d+$", option_id)
            for option_id in option_ids
        ]
        if any(match is None for match in group_matches):
            return None
        group_numbers = {int(match.group(1)) for match in group_matches if match}
        if len(group_numbers) != 1:
            return None
        targets = list(targets_by_source.get(node_id) or [])
        if len(targets) == 1 and len(option_ids) > 1:
            targets *= len(option_ids)
        if len(targets) != len(option_ids):
            return None
        target_line_ids: list[str] = []
        for target_id in targets:
            target = node_by_id[target_id]
            if not safe_key(target.get("$type")).endswith(
                ".DialogTreeTrunkNode"
            ):
                return None
            actor_data = target.get("_actorNodeData")
            trunk_data = (
                actor_data.get("mfTrunkActionData")
                if isinstance(actor_data, dict) else None
            )
            line_id = (
                safe_key(trunk_data.get("_trunkId"))
                if isinstance(trunk_data, dict) else ""
            )
            if not line_id:
                return None
            target_line_ids.append(line_id)
        groups.append({
            "optionGroup": next(iter(group_numbers)),
            "optionIds": option_ids,
            "targetLineIds": target_line_ids,
            "routeKind": (
                "authored_convergence"
                if len(set(target_line_ids)) == 1
                else "authored_split"
            ),
        })
    return sorted(groups, key=lambda row: row["optionGroup"])


def _dialog_tree_terminal_option_routes(
    tree_asset: Any,
) -> list[dict[str, Any]] | None:
    """Decode exact multi-option routes that terminate at FinishNodes.

    The shipped connection order is paired with ``_normalOptions``.  An
    omitted ``finishId`` remains explicitly absent here; this recovery does
    not guess the runtime default value.
    """
    if not isinstance(tree_asset, dict):
        return None
    script = tree_asset.get("m_Script")
    if not isinstance(script, str) or not script:
        return None
    try:
        payload = json.loads(
            base64.b64decode(script, validate=True).decode("utf-8-sig")
        )
    except (
        ValueError,
        binascii.Error,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        return None
    if (
        not isinstance(payload, dict)
        or payload.get("type") != "Beyond.Gameplay.DialogTree"
        or not isinstance(payload.get("nodes"), list)
        or not isinstance(payload.get("connections"), list)
    ):
        return None
    node_by_id: dict[str, dict[str, Any]] = {}
    for node in payload["nodes"]:
        if not isinstance(node, dict) or node.get("$id") in (None, ""):
            return None
        node_id = str(node["$id"])
        if node_id in node_by_id:
            return None
        node_by_id[node_id] = node
    targets_by_source: dict[str, list[str]] = defaultdict(list)
    for connection in payload["connections"]:
        if (
            not isinstance(connection, dict)
            or connection.get("$type")
            != "Beyond.Gameplay.DialogTreeConnection"
        ):
            return None
        source = connection.get("_sourceNode")
        target = connection.get("_targetNode")
        source_id = (
            str(source.get("$ref") or "")
            if isinstance(source, dict) else ""
        )
        target_id = (
            str(target.get("$ref") or "")
            if isinstance(target, dict) else ""
        )
        if source_id not in node_by_id or target_id not in node_by_id:
            return None
        targets_by_source[source_id].append(target_id)

    groups: list[dict[str, Any]] = []
    for node_id, node in node_by_id.items():
        option_rows = [
            row
            for row in node.get("_normalOptions") or []
            if isinstance(row, dict) and safe_key(row.get("_optionId"))
        ]
        if len(option_rows) <= 1:
            continue
        option_ids = [safe_key(row["_optionId"]) for row in option_rows]
        group_matches = [
            re.search(r"_(\d+)_\d+$", option_id)
            for option_id in option_ids
        ]
        if any(match is None for match in group_matches):
            return None
        group_numbers = {int(match.group(1)) for match in group_matches if match}
        if len(group_numbers) != 1:
            return None
        targets = list(targets_by_source.get(node_id) or [])
        if len(targets) != len(option_ids):
            return None
        target_nodes = [node_by_id[target_id] for target_id in targets]
        terminal_flags = [
            safe_key(target.get("$type")).endswith(".DialogTreeFinishNode")
            for target in target_nodes
        ]
        if not any(terminal_flags):
            continue
        if not all(terminal_flags):
            return None
        routes: list[dict[str, Any]] = []
        for option_id, target in zip(option_ids, target_nodes, strict=True):
            finish_id_serialized = "finishId" in target
            finish_id = target.get("finishId")
            if finish_id_serialized and not isinstance(finish_id, int):
                return None
            routes.append({
                "optionId": option_id,
                "targetKind": "finish",
                "finishId": finish_id,
                "finishIdSerialized": finish_id_serialized,
            })
        groups.append({
            "optionGroup": next(iter(group_numbers)),
            "routes": routes,
        })
    return sorted(groups, key=lambda row: row["optionGroup"])


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
        "dialogTextTable": table_root / "DialogTextTable.json",
        "dialogOptionTable": table_root / "DialogOptionTable.json",
        "readingPopupTable": table_root / "ReadingPopUpTable.json",
        "richContentTable": table_root / "RichContentTable.json",
        "prtsAllItemTable": table_root / "PrtsAllItem.json",
        "prtsRecordTable": table_root / "PrtsRecord.json",
        "prtsReadingTable": table_root / "PrtsReading.json",
        "snsDialogTable": table_root / "SNSDialogTable.json",
        "snsOptionTable": table_root / "SNSDialogOptionTable.json",
        "npcProxyExDataTable": (
            ROOT
            / "export_full"
            / "structured"
            / "Persistent"
            / "Data"
            / "Json"
            / "GameplayConfig"
            / "NpcProxyExDataTable.json"
        ),
        "dialogIdSource": (
            ROOT
            / "export_full"
            / "structured"
            / "StreamingAssets"
            / "Data"
            / "Json"
            / "GameplayConfig"
            / "DialogIdTable.json"
        ),
        "dialogIdIndex": (
            ROOT
            / "export_full"
            / "recovered"
            / "dialog_id_table_index.json"
        ),
        "timelineLineOrders": (
            ROOT
            / "export_full"
            / "recovered"
            / "AnimeStudio-cli"
            / "timeline_line_orders.json"
        ),
        "gameAssembly": game_assembly_path,
        "carrierAudit": carrier_audit_path,
        "gameObjectAudit": gameobject_audit_path,
        "reversePptrAudit": reverse_pptr_audit_path,
    }
    for context in OFFLINE_EXHAUSTION_RADIO_CONTEXTS.values():
        source_paths[context["sourceKey"]] = ROOT / context["sourceFile"]
    cutscene_definition_root = (
        ROOT
        / "export_full"
        / "recovered"
        / "AnimeStudio-cli"
        / "StreamingAssets"
        / "json_by_type"
        / "TextAsset"
    )
    source_paths["dialogTextAssetRoot"] = cutscene_definition_root
    for story_key, definition in (
        OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS.items()
    ):
        source_paths[
            f"dialogDefinition:{story_key}"
        ] = cutscene_definition_root / definition["filename"]
        if definition.get("extraConfigFilename"):
            source_paths[
                f"dialogExtraConfig:{story_key}"
            ] = (
                cutscene_definition_root
                / definition["extraConfigFilename"]
            )
        tracking = definition.get("missionNpcProxyTracking")
        if isinstance(tracking, dict):
            source_paths[
                f"missionNpcProxyTracking:{story_key}"
            ] = ROOT / tracking["sourceFile"]
    for mission_id, context in (
        OFFLINE_EXHAUSTION_MISSION_BRANCH_CONTEXTS.items()
    ):
        source_paths[
            f"missionBranchContext:{mission_id}"
        ] = ROOT / context["sourceFile"]
    for mission_id, context in (
        OFFLINE_EXHAUSTION_MISSION_LINEAR_CONTEXTS.items()
    ):
        source_paths[
            f"missionLinearContext:{mission_id}"
        ] = ROOT / context["sourceFile"]
    for mission_id, context in (
        OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS.items()
    ):
        source_paths[
            f"missionTopologyContext:{mission_id}"
        ] = ROOT / context["sourceFile"]
    for mission_id, context in (
        OFFLINE_EXHAUSTION_LEVELDATA_DIALOG_BRANCH_CONTEXTS.items()
    ):
        source_paths[
            f"levelDataDialogBranch:{mission_id}"
        ] = ROOT / context["levelDataFile"]
        source_paths[
            f"levelScriptDialogBranch:{mission_id}"
        ] = ROOT / context["levelScriptFile"]
    for story_key, consumer in (
        OFFLINE_EXHAUSTION_LEVELSCRIPT_TASK_CONSUMERS.items()
    ):
        source_paths[
            f"levelScriptTaskConsumer:{story_key}"
        ] = ROOT / consumer["sourceFile"]
    for story_key, definition in (
        OFFLINE_EXHAUSTION_SNS_DEFINITIONS.items()
    ):
        tracking = definition.get("runtimeTracking")
        if isinstance(tracking, dict):
            source_paths[
                f"snsRuntimeTracking:{story_key}"
            ] = ROOT / tracking["sourceFile"]
    for story_key, definition in (
        OFFLINE_EXHAUSTION_CUTSCENE_DEFINITIONS.items()
    ):
        for index, (filename, _sha256, _root_name) in enumerate(
            definition["files"],
            start=1,
        ):
            source_paths[
                f"cutsceneDefinition:{story_key}:{index}"
            ] = cutscene_definition_root / filename
    expected_hashes = {
        "radioTable": OFFLINE_EXHAUSTION_RADIO_TABLE_SHA256,
        "audioDialog": OFFLINE_EXHAUSTION_AUDIO_DIALOG_SHA256,
        "numIdStrTable": OFFLINE_EXHAUSTION_NUM_ID_STR_TABLE_SHA256,
        "textTable": OFFLINE_EXHAUSTION_TEXT_TABLE_SHA256,
        "dialogTextTable": OFFLINE_EXHAUSTION_DIALOG_TEXT_TABLE_SHA256,
        "dialogOptionTable": OFFLINE_EXHAUSTION_DIALOG_OPTION_TABLE_SHA256,
        "readingPopupTable":
            OFFLINE_EXHAUSTION_READING_POPUP_TABLE_SHA256,
        "richContentTable":
            OFFLINE_EXHAUSTION_RICH_CONTENT_TABLE_SHA256,
        "prtsAllItemTable":
            OFFLINE_EXHAUSTION_PRTS_ALL_ITEM_TABLE_SHA256,
        "prtsRecordTable":
            OFFLINE_EXHAUSTION_PRTS_RECORD_TABLE_SHA256,
        "prtsReadingTable":
            OFFLINE_EXHAUSTION_PRTS_READING_TABLE_SHA256,
        "snsDialogTable": OFFLINE_EXHAUSTION_SNS_DIALOG_TABLE_SHA256,
        "snsOptionTable": OFFLINE_EXHAUSTION_SNS_OPTION_TABLE_SHA256,
        "npcProxyExDataTable":
            OFFLINE_EXHAUSTION_NPC_PROXY_EX_TABLE_SHA256,
        "dialogIdSource": OFFLINE_EXHAUSTION_DIALOG_ID_SOURCE_SHA256,
        "dialogIdIndex": OFFLINE_EXHAUSTION_DIALOG_ID_INDEX_SHA256,
        "timelineLineOrders":
            OFFLINE_EXHAUSTION_TIMELINE_LINE_ORDERS_SHA256,
        "gameAssembly": OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
    }
    for context in OFFLINE_EXHAUSTION_RADIO_CONTEXTS.values():
        expected_hashes[context["sourceKey"]] = context["sha256"]
    for story_key, definition in (
        OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS.items()
    ):
        expected_hashes[
            f"dialogDefinition:{story_key}"
        ] = definition["sha256"]
        if definition.get("extraConfigFilename"):
            expected_hashes[
                f"dialogExtraConfig:{story_key}"
            ] = definition["extraConfigSha256"]
        tracking = definition.get("missionNpcProxyTracking")
        if isinstance(tracking, dict):
            expected_hashes[
                f"missionNpcProxyTracking:{story_key}"
            ] = tracking["sourceSha256"]
    for mission_id, context in (
        OFFLINE_EXHAUSTION_MISSION_BRANCH_CONTEXTS.items()
    ):
        expected_hashes[
            f"missionBranchContext:{mission_id}"
        ] = context["sourceSha256"]
    for mission_id, context in (
        OFFLINE_EXHAUSTION_MISSION_LINEAR_CONTEXTS.items()
    ):
        expected_hashes[
            f"missionLinearContext:{mission_id}"
        ] = context["sourceSha256"]
    for mission_id, context in (
        OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS.items()
    ):
        expected_hashes[
            f"missionTopologyContext:{mission_id}"
        ] = context["sourceSha256"]
    for mission_id, context in (
        OFFLINE_EXHAUSTION_LEVELDATA_DIALOG_BRANCH_CONTEXTS.items()
    ):
        expected_hashes[
            f"levelDataDialogBranch:{mission_id}"
        ] = context["levelDataSha256"]
        expected_hashes[
            f"levelScriptDialogBranch:{mission_id}"
        ] = context["levelScriptSha256"]
    for story_key, consumer in (
        OFFLINE_EXHAUSTION_LEVELSCRIPT_TASK_CONSUMERS.items()
    ):
        expected_hashes[
            f"levelScriptTaskConsumer:{story_key}"
        ] = consumer["sourceSha256"]
    for story_key, definition in (
        OFFLINE_EXHAUSTION_SNS_DEFINITIONS.items()
    ):
        tracking = definition.get("runtimeTracking")
        if isinstance(tracking, dict):
            expected_hashes[
                f"snsRuntimeTracking:{story_key}"
            ] = tracking["sourceSha256"]
    for story_key, definition in (
        OFFLINE_EXHAUSTION_CUTSCENE_DEFINITIONS.items()
    ):
        for index, (_filename, sha256, _root_name) in enumerate(
            definition["files"],
            start=1,
        ):
            expected_hashes[
                f"cutsceneDefinition:{story_key}:{index}"
            ] = sha256
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

    try:
        game_assembly_bytes = source_paths["gameAssembly"].read_bytes()
    except OSError as exc:
        status.update({
            "status": "inactive_game_assembly_token_validation_failed",
            "validatorDiagnostics": [{
                "validator": "offlineGameAssemblyTokenAbsence",
                "gate": "readCurrentGameAssembly",
                "sourcePaths": [str(source_paths["gameAssembly"])],
                "sourceSha256": {
                    "gameAssembly": actual_hashes.get("gameAssembly", ""),
                },
                "expected": {"readable": True},
                "actual": {
                    "readable": False,
                    "error": f"{type(exc).__name__}: {exc}",
                },
            }],
        })
        return {}, status
    binary_token_counts = {
        story_key: {
            "token": token,
            "utf8": game_assembly_bytes.count(token.encode("utf-8")),
            "utf16le": game_assembly_bytes.count(token.encode("utf-16le")),
        }
        for story_key, token
        in OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS.items()
    }
    present_binary_tokens = {
        story_key: counts
        for story_key, counts in binary_token_counts.items()
        if counts["utf8"] or counts["utf16le"]
    }
    if present_binary_tokens:
        status.update({
            "status": "inactive_game_assembly_token_validation_failed",
            "validatorDiagnostics": [{
                "validator": "offlineGameAssemblyTokenAbsence",
                "gate": "exactRootTokensAbsent",
                "sourcePaths": [str(source_paths["gameAssembly"])],
                "sourceSha256": {
                    "gameAssembly": actual_hashes.get("gameAssembly", ""),
                },
                "expected": {
                    "utf8Count": 0,
                    "utf16leCount": 0,
                },
                "actual": present_binary_tokens,
            }],
        })
        return {}, status
    status["gameAssemblyAbsentRootTokens"] = binary_token_counts

    mission_branch_context_by_mission: dict[str, dict[str, Any]] = {}
    for mission_id, declaration in (
        OFFLINE_EXHAUSTION_MISSION_BRANCH_CONTEXTS.items()
    ):
        source_name = f"missionBranchContext:{mission_id}"
        payload = read_json(source_paths[source_name], {})
        quest_dic = payload.get("questDic") if isinstance(payload, dict) else None
        fork = declaration["fork"]
        merge = declaration["merge"]
        shared_tracking = declaration["sharedTracking"]
        fork_quest_id = fork["questId"]
        successor_quest_ids = list(fork["successorQuestIds"])
        merge_quest_id = merge["questId"]
        predecessor_quest_ids = list(merge["predecessorQuestIds"])
        tracking_quest_ids = list(shared_tracking["questIds"])
        actual: dict[str, Any] = {
            "forkQuestPrev": None,
            "successorQuestPrev": {},
            "mergeQuestPrev": None,
            "sharedTracking": {},
        }
        valid = isinstance(quest_dic, dict)
        if valid:
            fork_quest = quest_dic.get(fork_quest_id)
            actual["forkQuestPrev"] = (
                fork_quest.get("prevQuestIdList")
                if isinstance(fork_quest, dict) else None
            )
            valid = actual["forkQuestPrev"] == []
            for quest_id in successor_quest_ids:
                quest = quest_dic.get(quest_id)
                prev = (
                    quest.get("prevQuestIdList")
                    if isinstance(quest, dict) else None
                )
                actual["successorQuestPrev"][quest_id] = prev
                valid = valid and prev == [fork_quest_id]
            merge_quest = quest_dic.get(merge_quest_id)
            actual["mergeQuestPrev"] = (
                merge_quest.get("prevQuestIdList")
                if isinstance(merge_quest, dict) else None
            )
            valid = valid and actual["mergeQuestPrev"] == predecessor_quest_ids
            expected_tracking = {
                "$type": (
                    "Beyond.Gameplay.NpcProxyTrackingInfo, "
                    "Gameplay.Beyond"
                ),
                "useFilterCondition": False,
                "sceneId": shared_tracking["levelId"],
                "guidingArea": 0.0,
                "npcProxyId": shared_tracking["proxyId"],
            }
            for quest_id in tracking_quest_ids:
                quest = quest_dic.get(quest_id)
                tracking: Any = None
                try:
                    tracking = quest["objectiveList"][0][
                        "trackingInfoList"
                    ][0]
                except (KeyError, IndexError, TypeError):
                    valid = False
                actual["sharedTracking"][quest_id] = tracking
                valid = valid and tracking == expected_tracking
        if not valid:
            status.update({
                "status": "inactive_mission_branch_context_validation_failed",
                "validatorDiagnostics": [{
                    "validator": "offlineMissionBranchContext",
                    "gate": "exactForkMergeAndSharedNpcTracking",
                    "mission": mission_id,
                    "sourcePaths": [str(source_paths[source_name])],
                    "sourceSha256": {
                        source_name: actual_hashes.get(source_name, ""),
                    },
                    "expected": {
                        "fork": fork,
                        "merge": merge,
                        "sharedTracking": shared_tracking,
                    },
                    "actual": actual,
                }],
            })
            return {}, status
        mission_branch_context_by_mission[mission_id] = {
            "sourceFile": declaration["sourceFile"],
            "fork": {
                "questId": fork_quest_id,
                "successorQuestIds": successor_quest_ids,
            },
            "merge": {
                "predecessorQuestIds": predecessor_quest_ids,
                "questId": merge_quest_id,
            },
            "sharedNpcTracking": {
                "questIds": tracking_quest_ids,
                "proxyId": shared_tracking["proxyId"],
                "levelId": shared_tracking["levelId"],
                "relation": "mission_quest_npc_proxy_tracking_context",
                "playback": False,
            },
            "storyArmAssignmentStatus": "unresolved",
            "storyArmAssignments": [],
            "serverSuccessorSelectionStatus": "not_serialized_in_client_asset",
            "orderEvidence": False,
            "graphEffect": "none",
        }

    mission_linear_context_by_mission: dict[str, dict[str, Any]] = {}
    for mission_id, declaration in (
        OFFLINE_EXHAUSTION_MISSION_LINEAR_CONTEXTS.items()
    ):
        source_name = f"missionLinearContext:{mission_id}"
        payload = read_json(source_paths[source_name], {})
        quest_dic = payload.get("questDic") if isinstance(payload, dict) else None
        sequence = list(declaration["questSequence"])
        actual_prev = {
            quest_id: (
                quest_dic.get(quest_id, {}).get("prevQuestIdList")
                if isinstance(quest_dic, dict)
                and isinstance(quest_dic.get(quest_id), dict)
                else None
            )
            for quest_id in sequence
        }
        expected_prev = {
            quest_id: ([] if index == 0 else [sequence[index - 1]])
            for index, quest_id in enumerate(sequence)
        }
        valid = (
            isinstance(quest_dic, dict)
            and set(quest_dic) == set(sequence)
            and actual_prev == expected_prev
        )
        if not valid:
            status.update({
                "status": "inactive_mission_linear_context_validation_failed",
                "validatorDiagnostics": [{
                    "validator": "offlineMissionLinearContext",
                    "gate": "exactSinglePredecessorQuestSequence",
                    "mission": mission_id,
                    "sourcePaths": [str(source_paths[source_name])],
                    "sourceSha256": {
                        source_name: actual_hashes.get(source_name, ""),
                    },
                    "expected": {
                        "questIds": sequence,
                        "prevQuestIdListByQuest": expected_prev,
                    },
                    "actual": {
                        "questIds": sorted(quest_dic) if isinstance(quest_dic, dict) else None,
                        "prevQuestIdListByQuest": actual_prev,
                    },
                }],
            })
            return {}, status
        mission_linear_context_by_mission[mission_id] = {
            "sourceFile": declaration["sourceFile"],
            "questSequence": sequence,
            "forkQuestIds": [],
            "mergeQuestIds": [],
            "relation": "authored_single_predecessor_quest_sequence",
            "storyPlacementStatus": "unresolved",
            "storyAssignments": [],
            "orderEvidence": False,
            "graphEffect": "none",
        }

    mission_topology_context_by_mission: dict[str, dict[str, Any]] = {}
    for mission_id, declaration in (
        OFFLINE_EXHAUSTION_MISSION_TOPOLOGY_CONTEXTS.items()
    ):
        source_name = f"missionTopologyContext:{mission_id}"
        payload = read_json(source_paths[source_name], {})
        quest_dic = payload.get("questDic") if isinstance(payload, dict) else None
        expected_prev = {
            quest_id: list(predecessors)
            for quest_id, predecessors
            in declaration["prevQuestIdsByQuest"].items()
        }
        actual_prev = {
            quest_id: (
                quest_dic.get(quest_id, {}).get("prevQuestIdList")
                if isinstance(quest_dic, dict)
                and isinstance(quest_dic.get(quest_id), dict)
                else None
            )
            for quest_id in expected_prev
        }
        expected_main_path = list(declaration["mainPathQuestIds"])
        actual_main_path = (
            payload.get("mainPathQuests") if isinstance(payload, dict) else None
        )
        valid = (
            isinstance(quest_dic, dict)
            and set(quest_dic) == set(expected_prev)
            and actual_prev == expected_prev
            and actual_main_path == expected_main_path
        )
        if not valid:
            status.update({
                "status": "inactive_mission_topology_context_validation_failed",
                "validatorDiagnostics": [{
                    "validator": "offlineMissionTopologyContext",
                    "gate": "exactQuestPredecessorGraphAndMainPath",
                    "mission": mission_id,
                    "sourcePaths": [str(source_paths[source_name])],
                    "sourceSha256": {
                        source_name: actual_hashes.get(source_name, ""),
                    },
                    "expected": {
                        "questIds": sorted(expected_prev, key=natural_key),
                        "prevQuestIdListByQuest": expected_prev,
                        "mainPathQuests": expected_main_path,
                    },
                    "actual": {
                        "questIds": sorted(quest_dic, key=natural_key)
                        if isinstance(quest_dic, dict) else None,
                        "prevQuestIdListByQuest": actual_prev,
                        "mainPathQuests": actual_main_path,
                    },
                }],
            })
            return {}, status
        successors = {quest_id: [] for quest_id in expected_prev}
        for quest_id, predecessors in expected_prev.items():
            for predecessor in predecessors:
                successors[predecessor].append(quest_id)
        forks = [
            {"questId": quest_id, "successorQuestIds": quest_successors}
            for quest_id, quest_successors in successors.items()
            if len(quest_successors) > 1
        ]
        merges = [
            {"predecessorQuestIds": predecessors, "questId": quest_id}
            for quest_id, predecessors in expected_prev.items()
            if len(predecessors) > 1
        ]
        mission_topology_context_by_mission[mission_id] = {
            "sourceFile": declaration["sourceFile"],
            "entryQuestIds": [
                quest_id for quest_id, predecessors in expected_prev.items()
                if not predecessors
            ],
            "mainPathQuestIds": expected_main_path,
            "forks": forks,
            "merges": merges,
            "terminalQuestIds": [
                quest_id for quest_id, quest_successors in successors.items()
                if not quest_successors
            ],
            "relation": "authored_mission_quest_predecessor_topology",
            "storyPlacementStatus": "unresolved",
            "storyAssignments": [],
            "flowIndexExclusivityStatus": "not_evidence",
            "serverSuccessorSelectionStatus": "not_serialized_in_client_asset",
            "orderEvidence": False,
            "graphEffect": "none",
        }

    leveldata_dialog_branch_by_story: dict[str, dict[str, Any]] = {}
    for mission_id, declaration in (
        OFFLINE_EXHAUSTION_LEVELDATA_DIALOG_BRANCH_CONTEXTS.items()
    ):
        leveldata_name = f"levelDataDialogBranch:{mission_id}"
        levelscript_name = f"levelScriptDialogBranch:{mission_id}"
        leveldata_path = source_paths[leveldata_name]
        levelscript_path = source_paths[levelscript_name]
        levelscript_ids = {
            int(path.stem)
            for path in levelscript_path.parent.glob("*.json")
            if path.stem.isdigit()
        }
        leveldata_bytes = leveldata_path.read_bytes()
        levelscript_bytes = levelscript_path.read_bytes()
        brief_dictionary = parse_leveldata_levelscript_brief_dictionary(
            leveldata_bytes,
            levelscript_ids,
        )
        brief = brief_dictionary.get(int(declaration["scriptId"])) or {}
        property_values: dict[str, str] = {}
        for property_row in brief.get("properties") or []:
            if not isinstance(property_row, dict):
                continue
            name = safe_key(property_row.get("name"))
            value = property_row.get("value")
            atoms = value.get("atoms") if isinstance(value, dict) else None
            if (
                name in declaration["propertyDialogs"]
                and value.get("valueType") == 7
                and value.get("atomCount") == 1
                and isinstance(atoms, list)
                and len(atoms) == 1
                and isinstance(atoms[0], dict)
            ):
                property_values[name] = safe_key(atoms[0].get("text"))

        records = extract_levelscript_uid_records(levelscript_bytes)
        _action_map, membership = levelscript_action_map_membership(
            levelscript_bytes,
            records,
        )
        ordered_records = sorted(
            records,
            key=lambda row: int(row.get("start") or 0),
        )
        next_starts = {
            int(record.get("start") or 0): (
                int(ordered_records[index + 1].get("start") or len(levelscript_bytes))
                if index + 1 < len(ordered_records)
                else len(levelscript_bytes)
            )
            for index, record in enumerate(ordered_records)
        }
        records_by_local: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for record in records:
            local_id = record.get("localId")
            if isinstance(local_id, int):
                records_by_local[local_id].append(record)

        def unique_record(local_id: int) -> dict[str, Any] | None:
            rows = records_by_local.get(local_id) or []
            return rows[0] if len(rows) == 1 else None

        def decoded(local_id: int) -> dict[str, Any]:
            record = unique_record(local_id)
            if not record:
                return {}
            start = int(record.get("start") or 0)
            return decode_levelscript_record_payload(
                levelscript_bytes,
                record,
                next_start=next_starts.get(start),
                action_map_role=safe_key(membership.get(start)),
            )

        listener = declaration["startDialogListener"]
        listener_record = unique_record(listener["headerLocalId"])
        listener_decoded = decoded(listener["headerLocalId"])
        listener_start = int(listener_record.get("start") or 0) if listener_record else -1
        listener_end = next_starts.get(listener_start, listener_start)
        listener_payload = (
            levelscript_bytes[listener_start:listener_end]
            if listener_start >= 0 and listener_end > listener_start else b""
        )

        result_switch = declaration["resultSwitch"]
        event_decoded = decoded(result_switch["eventHeaderLocalId"])
        switch_decoded = decoded(result_switch["switchLocalId"])
        switch_getter = decoded(result_switch["getterLocalId"])
        branch_outputs: list[dict[str, Any]] = []
        branch_valid = True
        for branch in result_switch["cases"]:
            action_record = unique_record(branch["actionLocalId"])
            action_decoded = decoded(branch["actionLocalId"])
            getter_decoded = decoded(branch["getterLocalId"])
            paths = (
                _levelscript_native_control_paths_to_record(
                    levelscript_bytes,
                    records,
                    membership,
                    action_record,
                )
                if action_record else []
            )
            exact_paths = [
                row for row in paths
                if row.get("status") == "exact_serialized_control_path"
                and row.get("headerLocalId") == result_switch["eventHeaderLocalId"]
                and row.get("pathLocalIds") == list(branch["pathLocalIds"])
            ]
            property_path = (
                (getter_decoded.get("getterString") or {}).get("path")
            )
            target_dialog = declaration["propertyDialogs"].get(property_path, "")
            current_valid = (
                len(exact_paths) == 1
                and (action_decoded.get("startDialogAction") or {}).get(
                    "dialogGetterLocalId"
                ) == branch["getterLocalId"]
                and property_path == branch["propertyPath"]
                and target_dialog
            )
            branch_valid = branch_valid and bool(current_valid)
            branch_outputs.append({
                "resultValue": branch["value"],
                "entryLocalId": branch["entryLocalId"],
                "actionLocalId": branch["actionLocalId"],
                "getterLocalId": branch["getterLocalId"],
                "propertyPath": property_path,
                "dialogId": target_dialog,
                "controlPath": exact_paths[0] if len(exact_paths) == 1 else None,
            })

        expected_script_ids = list(declaration["dictionaryScriptIds"])
        actual_script_ids = sorted(
            (str(value) for value in brief_dictionary),
            key=int,
        )
        switch_cases = switch_decoded.get("switchCases") or []
        event_detail = event_decoded.get("nativeEventDetail") or {}
        valid = (
            len(brief_dictionary) == declaration["dictionaryEntryCount"]
            and actual_script_ids == expected_script_ids
            and brief.get("propertyCount") == 37
            and brief.get("propertyMapCount") == 37
            and property_values == declaration["propertyDialogs"]
            and listener_decoded.get("label") == listener["eventName"]
            and (listener_decoded.get("actionHeader") or {}).get("nextId")
            == listener["nextLocalId"]
            and listener["propertyPath"].encode("utf-8") in listener_payload
            and (
                f"${listener['headerLocalId']}@_dialogId".encode("utf-8")
                in listener_payload
            )
            and event_decoded.get("label") == result_switch["eventName"]
            and event_detail.get("eventKey") == result_switch["eventKey"]
            and event_detail.get("serverExchange") is False
            and event_detail.get("serializedMissionOrQuestId") is False
            and (event_decoded.get("actionHeader") or {}).get("nextId")
            == result_switch["switchLocalId"]
            and switch_decoded.get("switchValueGetterLocalId")
            == result_switch["getterLocalId"]
            and (switch_getter.get("getterInt") or {}).get("value") == {
                "value": 0,
                "idRef": -1,
                "paramSource": 300,
                "path": result_switch["getterPath"],
            }
            and switch_cases == [
                {"value": value, "actionLocalId": action}
                for value, action in result_switch["switchCases"]
            ]
            and branch_valid
        )
        if not valid:
            status.update({
                "status": "inactive_leveldata_dialog_branch_validation_failed",
                "validatorDiagnostics": [{
                    "validator": "offlineLevelDataDialogBranchContext",
                    "gate": "exactPropertiesSwitchAndStartDialogControlPaths",
                    "mission": mission_id,
                    "sourcePaths": [str(leveldata_path), str(levelscript_path)],
                    "sourceSha256": {
                        leveldata_name: actual_hashes.get(leveldata_name, ""),
                        levelscript_name: actual_hashes.get(levelscript_name, ""),
                    },
                    "expected": {
                        "dictionaryScriptIds": expected_script_ids,
                        "propertyDialogs": declaration["propertyDialogs"],
                        "listener": listener,
                        "resultSwitch": result_switch,
                    },
                    "actual": {
                        "dictionaryScriptIds": actual_script_ids,
                        "propertyCount": brief.get("propertyCount"),
                        "propertyMapCount": brief.get("propertyMapCount"),
                        "propertyDialogs": property_values,
                        "listener": listener_decoded,
                        "event": event_decoded,
                        "switch": switch_decoded,
                        "switchGetter": switch_getter,
                        "branches": branch_outputs,
                    },
                }],
            })
            return {}, status

        shared_context = {
            "missionId": mission_id,
            "levelId": declaration["levelId"],
            "scriptId": declaration["scriptId"],
            "levelDataFile": declaration["levelDataFile"],
            "levelScriptFile": declaration["levelScriptFile"],
            "dictionaryScriptIds": actual_script_ids,
            "propertyDialogs": property_values,
            "startDialogListener": {
                **listener,
                "dialogId": property_values[listener["propertyPath"]],
                "playback": False,
                "relation": "exact_dialog_enter_listener_filter",
            },
            "resultProperty": result_switch["getterPath"],
            "resultBranches": branch_outputs,
            "runtimeMissionAssetStatus": "absent_for_nominal_mission",
            "serverExchange": False,
            "orderEvidence": True,
            "branchExclusivity": "switch_int_case_exclusive",
            "graphEffect": "none",
            "evidenceBoundary": (
                "the LevelData property names and exact LevelScript control paths "
                "prove start-dialog configuration plus mutually exclusive result "
                "branches; they do not serialize a MissionRuntime quest owner or "
                "the producer that raises the local custom event"
            ),
        }
        for property_path, story_key in property_values.items():
            leveldata_dialog_branch_by_story[story_key] = {
                **shared_context,
                "storyPropertyPath": property_path,
            }

    levelscript_task_consumer_by_story: dict[str, dict[str, Any]] = {}
    for story_key, declaration in (
        OFFLINE_EXHAUSTION_LEVELSCRIPT_TASK_CONSUMERS.items()
    ):
        source_name = f"levelScriptTaskConsumer:{story_key}"
        data = source_paths[source_name].read_bytes()
        decoded = decode_levelscript_task_conditions(
            data,
            declaration["scriptId"],
        )
        task_map = decoded[0] if len(decoded) == 1 else None
        task = (
            (task_map.get("tasks") or [None])[0]
            if isinstance(task_map, dict)
            else None
        )
        condition_row = (
            (task.get("conditions") or [None])[0]
            if isinstance(task, dict)
            else None
        )
        condition = (
            condition_row.get("condition")
            if isinstance(condition_row, dict)
            else None
        )
        actual = {
            "decodedMapCount": len(decoded),
            "startType": task_map.get("startType") if isinstance(task_map, dict) else None,
            "taskMapBoundaryStatus": (
                task_map.get("taskMapBoundaryStatus")
                if isinstance(task_map, dict) else None
            ),
            "taskKey": task.get("taskKey") if isinstance(task, dict) else None,
            "taskCount": len(task_map.get("tasks") or []) if isinstance(task_map, dict) else 0,
            "conditionKey": (
                condition_row.get("conditionKey")
                if isinstance(condition_row, dict) else None
            ),
            "conditionCount": len(task.get("conditions") or []) if isinstance(task, dict) else 0,
            "condition": condition,
        }
        valid = (
            len(decoded) == 1
            and actual["startType"] == "Manual"
            and actual["taskMapBoundaryStatus"] == "exact_trigger_volumes_offset"
            and actual["taskCount"] == 1
            and actual["taskKey"] == declaration["taskKey"]
            and actual["conditionCount"] == 1
            and actual["conditionKey"] == declaration["conditionKey"]
            and isinstance(condition, dict)
            and condition.get("type") == "CheckTalkOptionFinish"
            and condition.get("conditionUnionTag") == "0x009f"
            and condition.get("serializedMemberCount") == 6
            and condition.get("scopeMask") == 1
            and condition.get("uniqueId") == declaration["conditionKey"]
            and condition.get("useCurrentScope") is False
            and condition.get("useGraphScope") is True
            and condition.get("dialogId") == {
                "value": story_key,
                "idRef": -1,
                "paramSource": 0,
                "path": None,
            }
            and condition.get("finishId") == {
                "value": -1,
                "idRef": -1,
                "paramSource": 0,
                "path": None,
            }
        )
        post_dialog_action = declaration.get("postDialogAction")
        post_dialog_output = None
        if valid and isinstance(post_dialog_action, dict):
            records = extract_levelscript_uid_records(data)
            action_record = next(
                (row for row in records if row.get("localId") == post_dialog_action["actionLocalId"]),
                None,
            )
            header_record = next(
                (row for row in records if row.get("localId") == post_dialog_action["headerLocalId"]),
                None,
            )
            header_payload = (
                decode_levelscript_record_payload(data, header_record)
                if isinstance(header_record, dict) else {}
            )
            valid = (
                isinstance(action_record, dict)
                and levelscript_record_semantic_key(action_record)
                == (
                    int(post_dialog_action["actionUnionTag"], 16),
                    post_dialog_action["serializedMemberCount"],
                )
                and action_record.get("nextId") == -1
                and isinstance(header_record, dict)
                and header_payload.get("label") == post_dialog_action["eventName"]
                and header_payload.get("actionHeader", {}).get("nextId")
                == post_dialog_action["actionLocalId"]
                and any(
                    field.get("type") == "string"
                    and field.get("value") == story_key
                    for field in header_payload.get("taggedFields") or []
                )
            )
            actual["postDialogAction"] = {
                "actionRecord": action_record,
                "headerRecord": header_record,
                "headerPayload": header_payload,
            }
            post_dialog_output = {
                **post_dialog_action,
                "relation": "dialog_exit_event_to_local_presentation_action",
                "playback": False,
                "orderEvidence": False,
            }
        if not valid:
            status.update({
                "status": "inactive_levelscript_task_consumer_validation_failed",
                "validatorDiagnostics": [{
                    "validator": "offlineLevelScriptTaskConsumer",
                    "gate": "exactLevelScriptTalkCompletionConsumer",
                    "mission": "gm01m12",
                    "storyKey": story_key,
                    "sourcePaths": [str(source_paths[source_name])],
                    "sourceSha256": {
                        source_name: actual_hashes.get(source_name, ""),
                    },
                    "expected": declaration,
                    "actual": actual,
                }],
            })
            return {}, status
        levelscript_task_consumer_by_story[story_key] = {
            "sourceFile": declaration["sourceFile"],
            "levelId": declaration["levelId"],
            "scriptId": declaration["scriptId"],
            "startType": "Manual",
            "taskKey": declaration["taskKey"],
            "conditionKey": declaration["conditionKey"],
            "conditionType": "CheckTalkOptionFinish",
            "dialogId": story_key,
            "finishId": -1,
            "relation": "levelscript_task_depends_on_dialog_completion",
            "playback": False,
            "missionOwnership": False,
            "orderEvidence": False,
            "postDialogAction": post_dialog_output,
        }

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
    dialog_mission_by_key = {
        story_key: safe_key(definition.get("missionId"))
        for story_key, definition
        in OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS.items()
        if story_key not in OFFLINE_EXHAUSTION_POSITIVE_DIALOG_KEYS
    }
    all_dialog_keys = set(dialog_mission_by_key)
    text_only_dialog_mission_by_key = {
        story_key: safe_key(definition.get("missionId"))
        for story_key, definition
        in OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS.items()
    }
    all_text_only_dialog_keys = set(text_only_dialog_mission_by_key)
    all_dialog_mission_by_key = {
        **dialog_mission_by_key,
        **text_only_dialog_mission_by_key,
    }
    sns_mission_by_key = {
        story_key: safe_key(definition.get("missionId"))
        for story_key, definition
        in OFFLINE_EXHAUSTION_SNS_DEFINITIONS.items()
    }
    all_sns_keys = set(sns_mission_by_key)
    text_mission_by_key = {
        story_key: safe_key(definition.get("missionId"))
        for story_key, definition
        in OFFLINE_EXHAUSTION_TEXT_DEFINITIONS.items()
    }
    all_text_keys = set(text_mission_by_key)
    text_table_only_story_mission_by_key = {
        story_key: safe_key(definition.get("missionId"))
        for story_key, definition
        in OFFLINE_EXHAUSTION_TEXT_TABLE_ONLY_STORIES.items()
    }
    all_text_table_only_story_keys = set(
        text_table_only_story_mission_by_key
    )
    required_key_missions = {
        **radio_mission_by_key,
        **cutscene_mission_by_key,
        **dialog_mission_by_key,
        **text_only_dialog_mission_by_key,
        **sns_mission_by_key,
        **text_mission_by_key,
        **text_table_only_story_mission_by_key,
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
    radio_audio_ids_by_story: dict[str, set[str]] = {}
    base_absent_audio_ids_by_story: dict[str, set[str]] = {}
    radio_audio_variants_by_story: dict[
        str,
        dict[str, tuple[str, ...]],
    ] = {}
    missing_audio_ids_by_story: dict[str, set[str]] = {}
    radio_rows_valid = isinstance(radio_table, dict)
    radio_validation_failures: list[dict[str, Any]] = []
    for story_key in all_radio_keys:
        row = radio_table.get(story_key) if isinstance(radio_table, dict) else None
        failure = _offline_radio_definition_validation_failure(
            story_key,
            row,
            audio_stems,
        )
        if failure is not None:
            radio_validation_failures.append(failure)
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
        radio_audio_ids_by_story[story_key] = row_audio_ids
        base_absent_audio_ids = row_audio_ids - audio_stems
        expected_audio_variants = {
            safe_key(audio_id): tuple(
                safe_key(variant)
                for variant in variants
                if safe_key(variant)
            )
            for audio_id, variants in (
                OFFLINE_EXHAUSTION_RADIO_AUDIO_VARIANTS.get(
                    story_key,
                    {},
                )
            ).items()
            if isinstance(variants, (list, tuple))
        }
        expected_missing_audio_ids = set(
            OFFLINE_EXHAUSTION_RADIO_MISSING_AUDIO_IDS.get(
                story_key,
                (),
            )
        )
        if (
            set(expected_audio_variants) & expected_missing_audio_ids
            or base_absent_audio_ids
            != set(expected_audio_variants) | expected_missing_audio_ids
            or any(
                not variants
                or any(
                    not variant.startswith(f"{audio_id}_")
                    for variant in variants
                )
                or set(variants) != {
                    stem
                    for stem in audio_stems
                    if stem.startswith(f"{audio_id}_")
                }
                for audio_id, variants
                in expected_audio_variants.items()
            )
            or any(
                any(
                    stem.startswith(f"{audio_id}_")
                    for stem in audio_stems
                )
                for audio_id in expected_missing_audio_ids
            )
        ):
            radio_rows_valid = False
            break
        if base_absent_audio_ids:
            base_absent_audio_ids_by_story[story_key] = (
                base_absent_audio_ids
            )
            radio_audio_variants_by_story[story_key] = (
                expected_audio_variants
            )
        if expected_missing_audio_ids:
            missing_audio_ids_by_story[story_key] = (
                expected_missing_audio_ids
            )
    if (
        not radio_rows_valid
        or not (
            set(OFFLINE_EXHAUSTION_RADIO_AUDIO_VARIANTS)
            <= all_radio_keys
        )
        or not (
            set(OFFLINE_EXHAUSTION_RADIO_MISSING_AUDIO_IDS)
            <= all_radio_keys
        )
        or not (
            radio_audio_ids
            - {
                audio_id
                for audio_ids in base_absent_audio_ids_by_story.values()
                for audio_id in audio_ids
            }
        ) <= audio_stems
    ):
        if not radio_validation_failures:
            radio_validation_failures.append({
                "validator": "offlineRadioDefinition",
                "gate": "declaredAudioExceptionCoverage",
                "sourcePaths": ["RadioTable", "AudioDialog"],
                "expected": {
                    "variantKeysSubsetOfDeclaredRadios": True,
                    "missingAudioKeysSubsetOfDeclaredRadios": True,
                    "allUnexceptedAudioIdsPresent": True,
                },
                "actual": {
                    "unknownVariantKeys": sorted(
                        set(OFFLINE_EXHAUSTION_RADIO_AUDIO_VARIANTS)
                        - all_radio_keys
                    ),
                    "unknownMissingAudioKeys": sorted(
                        set(OFFLINE_EXHAUSTION_RADIO_MISSING_AUDIO_IDS)
                        - all_radio_keys
                    ),
                },
            })
        status.update({
            "status": "inactive_radio_definition_validation_failed",
            "validatorDiagnostics": radio_validation_failures,
        })
        return {}, status

    radio_contexts_valid = (
        set(OFFLINE_EXHAUSTION_RADIO_CONTEXTS) <= all_radio_keys
    )
    radio_context_validation_failures: list[dict[str, Any]] = []
    if not radio_contexts_valid:
        radio_context_validation_failures.append({
            "validator": "offlineRadioContext",
            "gate": "declaredContextIsKnownRadio",
            "expected": sorted(OFFLINE_EXHAUSTION_RADIO_CONTEXTS),
            "actualMissing": sorted(
                set(OFFLINE_EXHAUSTION_RADIO_CONTEXTS) - all_radio_keys,
                key=natural_key,
            ),
        })
    for story_key, context in OFFLINE_EXHAUSTION_RADIO_CONTEXTS.items():
        source = source_paths.get(context["sourceKey"])
        source_bytes = source.read_bytes() if isinstance(source, Path) else b""
        actual_counts = {
            value: source_bytes.count(value.encode("utf-8"))
            for value in context["byteStringCounts"]
        }
        if not source_bytes or actual_counts != context["byteStringCounts"]:
            radio_contexts_valid = False
            radio_context_validation_failures.append({
                "validator": "offlineRadioContext",
                "gate": "exactLevelDataByteStringCounts",
                "storyKey": story_key,
                "questId": context["questId"],
                "sourcePath": context["sourceFile"],
                "sourceSha256": actual_hashes.get(context["sourceKey"], ""),
                "expected": context["byteStringCounts"],
                "actual": actual_counts,
            })
    if not radio_contexts_valid:
        status["status"] = "inactive_radio_context_validation_failed"
        status["validationFailures"] = radio_context_validation_failures
        return {}, status

    reading_popup_table = read_json(source_paths["readingPopupTable"], {})
    rich_content_table = read_json(source_paths["richContentTable"], {})
    prts_all_item_table = read_json(source_paths["prtsAllItemTable"], {})
    prts_record_table = read_json(source_paths["prtsRecordTable"], {})
    prts_reading_table = read_json(source_paths["prtsReadingTable"], {})
    text_definitions_valid = (
        isinstance(reading_popup_table, dict)
        and isinstance(rich_content_table, dict)
        and isinstance(prts_all_item_table, dict)
        and isinstance(prts_record_table, dict)
        and isinstance(prts_reading_table, dict)
    )
    text_definition_validation_failures: list[dict[str, Any]] = []
    if not text_definitions_valid:
        text_definition_validation_failures.append({
            "validator": "offlineTextDefinition",
            "gate": "sourceTablesAreObjects",
            "sourcePaths": [
                str(source_paths[name])
                for name in (
                    "readingPopupTable",
                    "richContentTable",
                    "prtsAllItemTable",
                    "prtsRecordTable",
                    "prtsReadingTable",
                )
            ],
            "expected": {
                name: "object"
                for name in (
                    "readingPopupTable",
                    "richContentTable",
                    "prtsAllItemTable",
                    "prtsRecordTable",
                    "prtsReadingTable",
                )
            },
            "actual": {
                "readingPopupTable": type(reading_popup_table).__name__,
                "richContentTable": type(rich_content_table).__name__,
                "prtsAllItemTable": type(prts_all_item_table).__name__,
                "prtsRecordTable": type(prts_record_table).__name__,
                "prtsReadingTable": type(prts_reading_table).__name__,
            },
        })
    for story_key, definition in (
        OFFLINE_EXHAUSTION_TEXT_DEFINITIONS.items()
    ):
        if not text_definitions_valid:
            break
        popup = (
            {
                row_id: reading_popup_table.get(row_id)
                for row_id in definition["readingPopupRows"]
            }
            if isinstance(definition.get("readingPopupRows"), dict)
            else reading_popup_table.get(definition["readingPopupRowId"])
        )
        rich = rich_content_table.get(story_key)
        failure = _offline_text_definition_validation_failure(
            story_key,
            definition,
            popup,
            rich,
            prts_all_item_table,
            prts_record_table,
            prts_reading_table,
            source_paths=source_paths,
            actual_hashes=actual_hashes,
        )
        if failure is not None:
            text_definitions_valid = False
            text_definition_validation_failures.append(failure)
            break
    if not text_definitions_valid:
        status["status"] = "inactive_text_definition_validation_failed"
        status["validationFailures"] = text_definition_validation_failures
        return {}, status

    sns_dialog_table = read_json(source_paths["snsDialogTable"], {})
    sns_option_table = read_json(source_paths["snsOptionTable"], {})
    sns_validation_by_key: dict[str, dict[str, Any]] = {}
    sns_validation_failures: list[dict[str, Any]] = []
    sns_definitions_valid = (
        isinstance(sns_dialog_table, dict)
        and isinstance(sns_option_table, dict)
    )
    sns_dialog_fields = {
        "chatId",
        "dialogContentData",
        "dialogId",
        "dialogType",
        "noticeType",
        "relatedMissionId",
        "skipToFirstOption",
        "topicId",
    }
    sns_content_fields = {
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
    }
    sns_option_fields = {
        "optionDesc",
        "optionId",
        "optionNPCCount",
        "optionNPCIds",
        "optionNextContentId",
        "optionResPath",
    }
    for story_key, definition in (
        OFFLINE_EXHAUSTION_SNS_DEFINITIONS.items()
    ):
        if not sns_definitions_valid:
            break
        dialog = sns_dialog_table.get(story_key)
        content = (
            dialog.get("dialogContentData")
            if isinstance(dialog, dict)
            else None
        )
        expected_content_ids = tuple(definition["contentIds"])
        expected_content_keys = {
            str(content_id) for content_id in expected_content_ids
        }
        option_ids_by_content_id = definition["optionIdsByContentId"]
        content_params_by_content_id = (
            definition.get("contentParamsByContentId") or {}
        )
        pre_content_ids = definition.get("preContentIds") or {}
        next_content_ids = definition.get("nextContentIds") or {}
        expected_option_ids = set(definition["optionNextContentIds"])
        terminal_content_id = max(
            (
                content_id
                for content_id in expected_content_ids
                if content_id >= 0
            ),
            default=0,
        )
        actual_prefixed_option_ids = {
            option_id
            for option_id in sns_option_table
            if option_id.startswith(f"option_{story_key}_")
        }
        if (
            not isinstance(dialog, dict)
            or set(dialog) != sns_dialog_fields
            or dialog.get("dialogId") != story_key
            or dialog.get("chatId") != definition["chatId"]
            or dialog.get("dialogType")
            != int(definition.get("dialogType", 1))
            or dialog.get("noticeType") != 1
            or dialog.get("relatedMissionId") != ""
            or dialog.get("topicId") != ""
            or dialog.get("skipToFirstOption") is not False
            or not isinstance(content, dict)
            or set(content) != expected_content_keys
            or actual_prefixed_option_ids != expected_option_ids
        ):
            sns_definitions_valid = False
            sns_validation_failures.append({
                "validator": "offline_sns_definition",
                "gate": "dialog_shape_and_exact_key_sets",
                "storyKey": story_key,
                "sourcePaths": [
                    str(source_paths["snsDialogTable"]),
                    str(source_paths["snsOptionTable"]),
                ],
                "expected": {
                    "dialogFields": sorted(sns_dialog_fields),
                    "contentIds": sorted(expected_content_keys),
                    "optionIds": sorted(expected_option_ids, key=natural_key),
                    "chatId": definition["chatId"],
                    "dialogType": int(definition.get("dialogType", 1)),
                },
                "actual": {
                    "dialogType": type(dialog).__name__,
                    "dialogFields": (
                        sorted(dialog) if isinstance(dialog, dict) else []
                    ),
                    "contentIds": (
                        sorted(content) if isinstance(content, dict) else []
                    ),
                    "optionIds": sorted(
                        actual_prefixed_option_ids,
                        key=natural_key,
                    ),
                    "chatId": (
                        safe_key(dialog.get("chatId"))
                        if isinstance(dialog, dict) else ""
                    ),
                    "dialogType": (
                        dialog.get("dialogType")
                        if isinstance(dialog, dict) else None
                    ),
                },
            })
            break
        for content_id in expected_content_ids:
            node = content.get(str(content_id))
            expected_pre = (
                terminal_content_id if content_id == -1
                else 0 if content_id == 1
                else content_id - 1
            )
            expected_pre = pre_content_ids.get(content_id, expected_pre)
            expected_next = (
                0 if content_id == -1
                else -1 if content_id == terminal_content_id
                else 0 if content_id in option_ids_by_content_id
                else content_id + 1
            )
            expected_next = next_content_ids.get(content_id, expected_next)
            if (
                not isinstance(node, dict)
                or set(node) != sns_content_fields
                or node.get("contentId") != content_id
                or node.get("preContentId") != expected_pre
                or node.get("nextContentId") != expected_next
                or node.get("isEnd") is not (content_id == -1)
                or tuple(node.get("dialogOptionIds") or ())
                != tuple(option_ids_by_content_id.get(content_id) or ())
                or node.get("linkMissionId") != ""
                or node.get("linkRewardId") != ""
                or tuple(node.get("contentParam") or ())
                != tuple(content_params_by_content_id.get(content_id) or ())
                or node.get("contentParams") != ""
                or not isinstance(node.get("contentType"), int)
                or isinstance(node.get("contentType"), bool)
                or not isinstance(node.get("optionType"), int)
                or isinstance(node.get("optionType"), bool)
                or not isinstance(node.get("speaker"), str)
                or not isinstance(node.get("content"), dict)
                or set(node["content"]) != {"id", "text"}
                or not isinstance(node["content"].get("id"), int)
                or isinstance(node["content"].get("id"), bool)
                or node["content"].get("text") != ""
            ):
                sns_definitions_valid = False
                sns_validation_failures.append({
                    "validator": "offline_sns_definition",
                    "gate": "content_node_exact",
                    "storyKey": story_key,
                    "contentId": content_id,
                    "sourcePath": str(source_paths["snsDialogTable"]),
                    "expected": {
                        "preContentId": expected_pre,
                        "nextContentId": expected_next,
                        "dialogOptionIds": list(
                            option_ids_by_content_id.get(content_id) or ()
                        ),
                        "contentParam": list(
                            content_params_by_content_id.get(content_id) or ()
                        ),
                    },
                    "actual": node if isinstance(node, dict) else node,
                })
                break
        if not sns_definitions_valid:
            break
        for option_id in sorted(expected_option_ids, key=natural_key):
            option = sns_option_table.get(option_id)
            if (
                not isinstance(option, dict)
                or set(option) != sns_option_fields
                or option.get("optionId") != option_id
                or option.get("optionNextContentId")
                != definition["optionNextContentIds"][option_id]
                or option.get("optionDesc") != {
                    "id": definition["optionDescriptionIds"][option_id],
                    "text": "",
                }
                or option.get("optionNPCCount") != 0
                or option.get("optionNPCIds") != []
                or option.get("optionResPath") != ""
            ):
                sns_definitions_valid = False
                sns_validation_failures.append({
                    "validator": "offline_sns_definition",
                    "gate": "option_row_exact",
                    "storyKey": story_key,
                    "optionId": option_id,
                    "sourcePath": str(source_paths["snsOptionTable"]),
                    "expected": {
                        "optionNextContentId":
                            definition["optionNextContentIds"][option_id],
                        "optionDescriptionId":
                            definition["optionDescriptionIds"][option_id],
                    },
                    "actual": option if isinstance(option, dict) else option,
                })
                break
        if not sns_definitions_valid:
            break
        runtime_tracking_context: dict[str, Any] | None = None
        runtime_tracking = definition.get("runtimeTracking")
        if isinstance(runtime_tracking, dict):
            source_name = f"snsRuntimeTracking:{story_key}"
            runtime_payload = read_json(source_paths[source_name], {})
            quest_id = runtime_tracking["questId"]
            objective_index = runtime_tracking["objectiveIndex"]
            tracking_index = runtime_tracking["trackingIndex"]
            actual_tracking: Any = None
            try:
                actual_tracking = (
                    runtime_payload["questDic"][quest_id]
                    ["objectiveList"][objective_index]
                    ["trackingInfoList"][tracking_index]
                )
            except (KeyError, IndexError, TypeError):
                pass
            expected_tracking = {
                "$type": "Beyond.Gameplay.SnsTrackingInfo, Gameplay.Beyond",
                "useFilterCondition": False,
                "sceneId": "",
                "guidingArea": 0.0,
                "snsDialogId": story_key,
            }
            if actual_tracking != expected_tracking:
                sns_definitions_valid = False
                sns_validation_failures.append({
                    "validator": "offline_sns_definition",
                    "gate": "exactCrossMissionSnsTrackingContext",
                    "mission": runtime_tracking["runtimeMissionId"],
                    "storyKey": story_key,
                    "sourcePaths": [str(source_paths[source_name])],
                    "sourceSha256": {
                        source_name: actual_hashes.get(source_name, ""),
                    },
                    "expected": {
                        "questId": quest_id,
                        "objectiveIndex": objective_index,
                        "trackingIndex": tracking_index,
                        "tracking": expected_tracking,
                    },
                    "actual": actual_tracking,
                })
                break
            runtime_tracking_context = {
                "runtimeMissionId": runtime_tracking["runtimeMissionId"],
                "questId": quest_id,
                "objectiveIndex": objective_index,
                "trackingIndex": tracking_index,
                "sourceFile": runtime_tracking["sourceFile"],
                "relation": "objective_tracking_story_reference",
                "trackingType": "SnsTrackingInfo",
                "playback": False,
                "nominalMissionOwnership": False,
                "runtimeMissionContext": True,
                "orderEvidence": False,
                "graphEffect": "none",
            }
        sns_validation_by_key[story_key] = {
            "chatId": definition["chatId"],
            "contentIds": list(expected_content_ids),
            "optionIds": sorted(expected_option_ids, key=natural_key),
            "contentParamsByContentId": {
                str(content_id): list(content_params)
                for content_id, content_params
                in content_params_by_content_id.items()
            },
            "runtimeTracking": runtime_tracking_context,
        }
    if not sns_definitions_valid:
        status["status"] = "inactive_sns_definition_validation_failed"
        status["validationFailures"] = sns_validation_failures or [{
            "validator": "offline_sns_definition",
            "gate": "source_table_type",
            "sourcePaths": [
                str(source_paths["snsDialogTable"]),
                str(source_paths["snsOptionTable"]),
            ],
            "expected": "two JSON objects",
            "actual": {
                "snsDialogTable": type(sns_dialog_table).__name__,
                "snsOptionTable": type(sns_option_table).__name__,
            },
        }]
        status["validatorDiagnostics"] = status["validationFailures"]
        return {}, status

    dialog_text_table = read_json(source_paths["dialogTextTable"], {})
    dialog_option_table = read_json(source_paths["dialogOptionTable"], {})
    dialog_id_index = read_json(source_paths["dialogIdIndex"], {})
    timeline_line_orders = read_json(source_paths["timelineLineOrders"], {})
    npc_proxy_ex_table = read_json(
        source_paths["npcProxyExDataTable"],
        {},
    )
    dialog_validation_by_key: dict[str, dict[str, Any]] = {}
    dialog_validation_failures: list[dict[str, Any]] = []
    dialog_definitions_valid = (
        isinstance(dialog_text_table, dict)
        and isinstance(dialog_id_index, dict)
        and isinstance(timeline_line_orders, dict)
        and isinstance(npc_proxy_ex_table, dict)
    )
    for story_key, definition in (
        OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS.items()
    ):
        if not dialog_definitions_valid:
            break
        tree = read_json(
            source_paths[f"dialogDefinition:{story_key}"],
            {},
        )
        registry_key = safe_key(
            definition.get("registryKey")
        ) or story_key
        definition_name = safe_key(
            definition.get("definitionName")
        ) or registry_key
        line_prefix = safe_key(
            definition.get("linePrefix")
        ) or registry_key
        registry = dialog_id_index.get(registry_key)
        expected_line_ids = tuple(definition["lineIds"])
        actual_line_ids = tuple(sorted(
            key
            for key in dialog_text_table
            if key.startswith(f"{line_prefix}_")
        ))
        expected_option_ids = tuple(definition["optionIds"])
        expected_tree_branch_groups = (
            [
                {
                    "optionGroup": int(row["optionGroup"]),
                    "optionIds": list(row["optionIds"]),
                    "targetLineIds": list(row["targetLineIds"]),
                    "routeKind": safe_key(row.get("routeKind")),
                }
                for row in definition["treeBranchGroups"]
            ]
            if "treeBranchGroups" in definition else None
        )
        actual_tree_branch_groups = _dialog_tree_branch_groups(tree)
        tree_branch_groups_valid = (
            expected_tree_branch_groups is None
            or actual_tree_branch_groups == expected_tree_branch_groups
        )
        expected_terminal_option_routes = (
            [
                {
                    "optionGroup": int(row["optionGroup"]),
                    "routes": [dict(route) for route in row["routes"]],
                }
                for row in definition["terminalOptionRoutes"]
            ]
            if "terminalOptionRoutes" in definition else None
        )
        actual_terminal_option_routes = (
            _dialog_tree_terminal_option_routes(tree)
        )
        terminal_option_routes_valid = (
            expected_terminal_option_routes is None
            or actual_terminal_option_routes
            == expected_terminal_option_routes
        )
        registered_option_ids = tuple(sorted(
            option_id
            for option_ids in (
                (registry.get("optionsByGroup") or {}).values()
                if isinstance(registry, dict)
                else []
            )
            for option_id in option_ids
            if isinstance(option_id, str)
        ))
        line_audio_ids = tuple(
            safe_key(dialog_text_table[line_id].get("audioOverride"))
            for line_id in expected_line_ids
            if isinstance(dialog_text_table.get(line_id), dict)
        )
        expected_missing_audio_ids = set(
            definition.get("missingAudioIds") or ()
        )
        actual_missing_audio_ids = set(line_audio_ids) - audio_stems
        shared_timeline = definition.get("sharedTimeline")
        owned_timeline = definition.get("ownedTimeline")
        npc_proxy_consumer = definition.get("npcProxyConsumer")
        npc_proxy_consumers = definition.get("npcProxyConsumers")
        npc_proxy_consumer_contexts: list[dict[str, Any]] = []
        npc_proxy_consumer_valid = True
        if npc_proxy_consumer is not None and npc_proxy_consumers is not None:
            npc_proxy_consumer_valid = False
        consumer_specs = (
            [npc_proxy_consumer]
            if isinstance(npc_proxy_consumer, dict)
            else (
                list(npc_proxy_consumers)
                if isinstance(npc_proxy_consumers, (list, tuple))
                else []
            )
        )
        if (
            npc_proxy_consumers is not None
            and (
                not isinstance(npc_proxy_consumers, (list, tuple))
                or not npc_proxy_consumers
                or any(
                    not isinstance(spec, dict)
                    for spec in npc_proxy_consumers
                )
            )
        ):
            npc_proxy_consumer_valid = False
        for consumer_spec in consumer_specs:
            proxy_id = safe_key(consumer_spec.get("proxyId"))
            entry_index = consumer_spec.get("entryIndex")
            expected_entry = consumer_spec.get("entry")
            proxy_entries = (
                (npc_proxy_ex_table.get("data") or {}).get(proxy_id)
                if isinstance(npc_proxy_ex_table.get("data"), dict)
                else None
            )
            current_consumer_valid = (
                isinstance(entry_index, int)
                and not isinstance(entry_index, bool)
                and isinstance(expected_entry, dict)
                and isinstance(proxy_entries, list)
                and 0 <= entry_index < len(proxy_entries)
                and proxy_entries[entry_index] == expected_entry
                and expected_entry.get("dialogId") == registry_key
                and not safe_key(expected_entry.get("missionId"))
            )
            if not current_consumer_valid:
                npc_proxy_consumer_valid = False
                continue
            npc_proxy_consumer_contexts.append({
                "proxyId": proxy_id,
                "entryIndex": entry_index,
                "dialogId": (
                    safe_key(expected_entry.get("dialogId"))
                    if isinstance(expected_entry, dict)
                    else ""
                ),
                "missionId": (
                    safe_key(expected_entry.get("missionId"))
                    if isinstance(expected_entry, dict)
                    else ""
                ),
                "relation": "npc_proxy_ex_dialog_consumer_without_mission_id",
                "missionOwnership": False,
                "orderEvidence": False,
                "graphEffect": "none",
            })
        npc_proxy_consumer_context = (
            npc_proxy_consumer_contexts[0]
            if len(npc_proxy_consumer_contexts) == 1
            else None
        )
        mission_tracking_spec = definition.get("missionNpcProxyTracking")
        mission_tracking_context: dict[str, Any] | None = None
        if isinstance(mission_tracking_spec, dict):
            tracking_source_name = f"missionNpcProxyTracking:{story_key}"
            tracking_payload = read_json(
                source_paths[tracking_source_name],
                {},
            )
            expected_tracking_rows = list(
                mission_tracking_spec.get("rows") or []
            )
            proxy_id = safe_key(mission_tracking_spec.get("proxyId"))
            level_id = safe_key(mission_tracking_spec.get("levelId"))
            nominal_mission_id = safe_key(definition.get("missionId"))
            runtime_mission_id = (
                safe_key(mission_tracking_spec.get("runtimeMissionId"))
                or nominal_mission_id
            )
            actual_tracking_rows: list[dict[str, Any]] = []
            tracking_rows_valid = bool(
                proxy_id and level_id and expected_tracking_rows
            )
            for expected_row in expected_tracking_rows:
                quest_id = safe_key(expected_row.get("questId"))
                objective_index = expected_row.get("objectiveIndex")
                tracking_index = expected_row.get("trackingIndex")
                actual_tracking: Any = None
                try:
                    actual_tracking = (
                        tracking_payload["questDic"][quest_id]
                        ["objectiveList"][objective_index]
                        ["trackingInfoList"][tracking_index]
                    )
                except (KeyError, IndexError, TypeError):
                    tracking_rows_valid = False
                expected_tracking = {
                    "$type": (
                        "Beyond.Gameplay.NpcProxyTrackingInfo, "
                        "Gameplay.Beyond"
                    ),
                    "useFilterCondition": False,
                    "sceneId": level_id,
                    "guidingArea": 0.0,
                    "npcProxyId": proxy_id,
                }
                if actual_tracking != expected_tracking:
                    tracking_rows_valid = False
                actual_tracking_rows.append({
                    "questId": quest_id,
                    "objectiveIndex": objective_index,
                    "trackingIndex": tracking_index,
                    "tracking": actual_tracking,
                })
            if not tracking_rows_valid:
                dialog_definitions_valid = False
                dialog_validation_failures.append({
                    "validator": "offlineDialogDefinition",
                    "gate": "exactMissionNpcProxyTrackingContext",
                    "mission": runtime_mission_id,
                    "storyKey": story_key,
                    "sourcePaths": [
                        str(source_paths[tracking_source_name]),
                    ],
                    "sourceSha256": {
                        tracking_source_name:
                            actual_hashes.get(tracking_source_name, ""),
                    },
                    "expected": {
                        "proxyId": proxy_id,
                        "levelId": level_id,
                        "rows": expected_tracking_rows,
                    },
                    "actual": actual_tracking_rows,
                })
                break
            mission_tracking_context = {
                "proxyId": proxy_id,
                "levelId": level_id,
                "missionId": runtime_mission_id,
                "nominalMissionId": nominal_mission_id,
                "crossMission": runtime_mission_id != nominal_mission_id,
                "questIds": [
                    safe_key(row.get("questId"))
                    for row in expected_tracking_rows
                ],
                "sourceFile": mission_tracking_spec["sourceFile"],
                "relation": "mission_quest_npc_proxy_tracking_context",
                "missionContextOnly": True,
                "missionOwnership": False,
                "questPlaybackOwnership": False,
                "orderEvidence": False,
                "graphEffect": "none",
            }
        timeline_context: dict[str, Any] | None = None
        if isinstance(shared_timeline, dict):
            owner_dialog_key = safe_key(
                shared_timeline.get("ownerDialogKey")
            )
            timeline_entry = timeline_line_orders.get(owner_dialog_key)
            embedded_line_ids = tuple(
                shared_timeline["embeddedLineIds"]
            )
            timeline_line_ids = tuple(
                timeline_entry.get("lineIds") or []
                if isinstance(timeline_entry, dict)
                else []
            )
            try:
                start = timeline_line_ids.index(embedded_line_ids[0])
            except (ValueError, IndexError):
                start = -1
            end = start + len(embedded_line_ids)
            timeline_lines = [
                row
                for row in (
                    timeline_entry.get("lines") or []
                    if isinstance(timeline_entry, dict)
                    else []
                )
                if (
                    isinstance(row, dict)
                    and safe_key(row.get("id")) in embedded_line_ids
                )
            ]
            timeline_context_valid = (
                start > 0
                and tuple(timeline_line_ids[start:end])
                == embedded_line_ids
                and timeline_line_ids[start - 1]
                == shared_timeline["beforeLineId"]
                and end < len(timeline_line_ids)
                and timeline_line_ids[end]
                == shared_timeline["afterLineId"]
                and {
                    line_id
                    for line_id in timeline_line_ids
                    if line_id.startswith(f"{story_key}_")
                }
                == set(embedded_line_ids)
                and len(timeline_lines) == len(embedded_line_ids)
                and all(
                    safe_key(row.get("timeline"))
                    == shared_timeline["timeline"]
                    and safe_key(row.get("sourceFile"))
                    == shared_timeline["sourceFile"]
                    and row.get("trackPathId")
                    == shared_timeline["trackPathId"]
                    and safe_key(row.get("lineIdSource"))
                    == "assetTrunkId"
                    for row in timeline_lines
                )
            )
            timeline_context = {
                "ownerDialogKey": owner_dialog_key,
                "timeline": shared_timeline["timeline"],
                "sourceFile": shared_timeline["sourceFile"],
                "trackPathId": shared_timeline["trackPathId"],
                "beforeLineId": shared_timeline["beforeLineId"],
                "embeddedLineIds": list(embedded_line_ids),
                "afterLineId": shared_timeline["afterLineId"],
                "relation":
                    "shared_dialog_timeline_embedded_line_context",
                "graphEffect": "none",
            }
            registry_timeline_valid = (
                isinstance(registry, dict)
                and int(registry.get("usedDialogTimelineCount") or 0) == 0
                and not registry.get("usedDialogTimelineIds")
            )
        elif isinstance(owned_timeline, dict):
            timeline_entry = timeline_line_orders.get(story_key)
            timeline_id = safe_key(owned_timeline.get("timeline"))
            source_file = safe_key(owned_timeline.get("sourceFile"))
            track_path_id = owned_timeline.get("trackPathId")
            expected_track_path_ids = set(
                owned_timeline.get("trackPathIds") or (
                    (track_path_id,) if track_path_id is not None else ()
                )
            )
            full_line_ids = tuple(owned_timeline["fullLineIds"])
            timeline_lines = (
                timeline_entry.get("lines") or []
                if isinstance(timeline_entry, dict)
                else []
            )
            timeline_option_ids = tuple(sorted(
                safe_key(option_id)
                for option_id in (
                    timeline_entry.get("optionIds") or []
                    if isinstance(timeline_entry, dict)
                    else []
                )
                if safe_key(option_id)
            ))
            timeline_context_valid = (
                isinstance(timeline_entry, dict)
                and safe_key(timeline_entry.get("dialogKey")) == story_key
                and safe_key(timeline_entry.get("timeline")) == timeline_id
                and tuple(timeline_entry.get("lineIds") or [])
                == full_line_ids
                and len(timeline_lines) == len(full_line_ids)
                and tuple(
                    safe_key(row.get("id"))
                    for row in timeline_lines
                    if isinstance(row, dict)
                )
                == full_line_ids
                and all(
                    safe_key(row.get("timeline")) == timeline_id
                    and safe_key(row.get("sourceFile")) == source_file
                    and row.get("trackPathId") in expected_track_path_ids
                    and safe_key(row.get("lineIdSource"))
                    == "assetTrunkId"
                    for row in timeline_lines
                    if isinstance(row, dict)
                )
                and {
                    row.get("trackPathId")
                    for row in timeline_lines
                    if isinstance(row, dict)
                } == expected_track_path_ids
                and timeline_option_ids == expected_option_ids
            )
            registry_timeline_valid = (
                isinstance(registry, dict)
                and int(registry.get("usedDialogTimelineCount") or 0) == 1
                and tuple(registry.get("usedDialogTimelineIds") or [])
                == (timeline_id,)
            )
            timeline_context = {
                "ownerDialogKey": story_key,
                "timeline": timeline_id,
                "sourceFile": source_file,
                "trackPathIds": sorted(expected_track_path_ids),
                "lineIds": list(full_line_ids),
                "embeddedForeignLineIds": [
                    line_id
                    for line_id in full_line_ids
                    if not line_id.startswith(f"{story_key}_")
                ],
                "optionIds": list(expected_option_ids),
                "relation":
                    "owned_dialog_timeline_exact_mixed_story_context",
                "graphEffect": "none",
            }
        else:
            timeline_context_valid = (
                story_key not in timeline_line_orders
                and registry_key not in timeline_line_orders
            )
            registry_timeline_valid = (
                isinstance(registry, dict)
                and int(registry.get("usedDialogTimelineCount") or 0) == 0
                and not registry.get("usedDialogTimelineIds")
            )
        if (
            not isinstance(tree, dict)
            or safe_key(tree.get("m_Name")) != definition_name
            or safe_key(tree.get("Name")) != definition_name
            or not isinstance(tree.get("m_Script"), str)
            or not tree["m_Script"]
            or not isinstance(registry, dict)
            or registry.get("registered") is not True
            or registry.get("memoryPackRecordKey") is not True
            or registry.get("hasRootKey") is not True
            or set(registry.get("registrationEvidence") or [])
            != {"memorypack_record_key", "printable_root_token"}
            or int(registry.get("trunkCount") or 0) != 0
            or int(registry.get("lineCount") or 0) != 0
            or not registry_timeline_valid
            or actual_line_ids != expected_line_ids
            or registered_option_ids != expected_option_ids
            or not tree_branch_groups_valid
            or not terminal_option_routes_valid
            or len(line_audio_ids) != len(expected_line_ids)
            or not all(line_audio_ids)
            or actual_missing_audio_ids != expected_missing_audio_ids
            or not (
                set(line_audio_ids) - expected_missing_audio_ids
            ) <= audio_stems
            or any(
                set(dialog_text_table[line_id])
                != OFFLINE_EXHAUSTION_DIALOG_ROW_FIELDS
                for line_id in expected_line_ids
            )
            or not timeline_context_valid
            or not npc_proxy_consumer_valid
        ):
            dialog_validation_failures.append({
                "validator": "offlineDialogDefinition",
                "gate": "exactRegisteredDialogDefinition",
                "mission": safe_key(definition.get("missionId")),
                "storyKey": story_key,
                "sourcePaths": [
                    str(source_paths[f"dialogDefinition:{story_key}"]),
                    str(source_paths["dialogTextTable"]),
                    str(source_paths["dialogIdIndex"]),
                    str(source_paths["audioDialog"]),
                ],
                "expected": {
                    "definitionName": definition_name,
                    "lineIds": list(expected_line_ids),
                    "optionIds": list(expected_option_ids),
                    "treeBranchGroups": expected_tree_branch_groups,
                    "terminalOptionRoutes": expected_terminal_option_routes,
                    "missingAudioIds": sorted(expected_missing_audio_ids),
                    "registered": True,
                    "registrationEvidence": [
                        "memorypack_record_key",
                        "printable_root_token",
                    ],
                    "timelineContextValid": True,
                    "npcProxyConsumerValid": True,
                },
                "actual": {
                    "treeMName": safe_key(tree.get("m_Name"))
                        if isinstance(tree, dict) else "",
                    "treeName": safe_key(tree.get("Name"))
                        if isinstance(tree, dict) else "",
                    "scriptLength": len(tree.get("m_Script") or "")
                        if isinstance(tree, dict) else 0,
                    "lineIds": list(actual_line_ids),
                    "optionIds": list(registered_option_ids),
                    "treeBranchGroups": actual_tree_branch_groups,
                    "terminalOptionRoutes": actual_terminal_option_routes,
                    "missingAudioIds": sorted(actual_missing_audio_ids),
                    "registry": {
                        key: registry.get(key)
                        for key in (
                            "registered",
                            "memoryPackRecordKey",
                            "hasRootKey",
                            "registrationEvidence",
                            "trunkCount",
                            "lineCount",
                            "usedDialogTimelineCount",
                            "usedDialogTimelineIds",
                        )
                    } if isinstance(registry, dict) else None,
                    "timelineContextValid": timeline_context_valid,
                    "npcProxyConsumerValid": npc_proxy_consumer_valid,
                },
            })
            dialog_definitions_valid = False
            break
        dialog_validation_by_key[story_key] = {
            "registryKey": registry_key,
            "definitionName": definition_name,
            "lineIds": list(expected_line_ids),
            "audioIds": list(line_audio_ids),
            "missingAudioIds": sorted(
                actual_missing_audio_ids,
                key=natural_key,
            ),
            "optionIds": list(expected_option_ids),
            "treeBranchGroups": actual_tree_branch_groups or [],
            "terminalOptionRoutes": actual_terminal_option_routes or [],
            "timelineContext": timeline_context,
            "npcProxyConsumer": npc_proxy_consumer_context,
            "npcProxyConsumers": npc_proxy_consumer_contexts,
            "missionNpcProxyTracking": mission_tracking_context,
            "levelScriptTaskConsumer":
                levelscript_task_consumer_by_story.get(story_key),
            "levelDataDialogBranchContext":
                leveldata_dialog_branch_by_story.get(story_key),
        }
    if not dialog_definitions_valid:
        status.update({
            "status": "inactive_dialog_definition_validation_failed",
            "validatorDiagnostics": dialog_validation_failures or [{
                "validator": "offlineDialogDefinition",
                "gate": "requiredSourcePayloadTypes",
                "sourcePaths": [
                    str(source_paths["dialogTextTable"]),
                    str(source_paths["dialogIdIndex"]),
                    str(source_paths["timelineLineOrders"]),
                    str(source_paths["npcProxyExDataTable"]),
                ],
                "expected": {"allPayloadsAreObjects": True},
                "actual": {
                    "types": {
                        "dialogTextTable": type(dialog_text_table).__name__,
                        "dialogIdIndex": type(dialog_id_index).__name__,
                        "timelineLineOrders": type(timeline_line_orders).__name__,
                        "npcProxyExDataTable": type(npc_proxy_ex_table).__name__,
                    },
                },
            }],
        })
        return {}, status

    text_only_dialog_validation_by_key: dict[str, dict[str, Any]] = {}
    text_only_dialog_validation_failures: list[dict[str, Any]] = []
    for story_key, definition in (
        OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS.items()
    ):
        expected_line_ids = tuple(definition["lineIds"])
        actual_line_ids = tuple(sorted(
            key
            for key in dialog_text_table
            if key.startswith(f"{story_key}_")
        ))
        line_audio_ids = tuple(
            safe_key(dialog_text_table[line_id].get("audioOverride"))
            for line_id in expected_line_ids
            if isinstance(dialog_text_table.get(line_id), dict)
        )
        expected_audio_ids = tuple(
            definition.get("audioIds")
            or tuple(f"au_{line_id}" for line_id in expected_line_ids)
        )
        expected_missing_audio_ids = set(
            definition["missingAudioIds"]
        )
        expected_audio_variants = {
            safe_key(audio_id): tuple(
                safe_key(variant)
                for variant in variants
                if safe_key(variant)
            )
            for audio_id, variants
            in (definition.get("audioVariants") or {}).items()
            if isinstance(variants, (list, tuple))
        }
        actual_missing_audio_ids = {
            audio_id
            for audio_id in line_audio_ids
            if (
                audio_id not in audio_stems
                and not (
                    audio_id in expected_audio_variants
                    and set(expected_audio_variants[audio_id]) <= audio_stems
                )
            )
        }
        expected_option_rows = definition.get("optionRows")
        actual_option_ids = tuple(sorted(
            key for key in dialog_option_table
            if key.startswith(f"option_{story_key}_")
        )) if isinstance(dialog_option_table, dict) else ()
        expected_option_ids = tuple(sorted(
            expected_option_rows or {}
        ))
        cutscene_matches = sorted(
            str(path.relative_to(ROOT)).replace("\\", "/")
            for path in cutscene_definition_root.glob(f"{story_key}_p*.json")
        )
        failures_before = len(text_only_dialog_validation_failures)

        def add_text_only_failure(
            gate: str,
            source_names: tuple[str, ...],
            expected: Any,
            actual: Any,
        ) -> None:
            text_only_dialog_validation_failures.append({
                "validator": "offlineTextOnlyDialogDefinition",
                "gate": gate,
                "storyKey": story_key,
                "missionId": safe_key(definition.get("missionId")),
                "sourcePaths": [
                    str(source_paths[name]) for name in source_names
                ],
                "sourceSha256": {
                    name: actual_hashes.get(name, "")
                    for name in source_names
                },
                "expected": expected,
                "actual": actual,
            })

        if actual_line_ids != expected_line_ids:
            add_text_only_failure(
                "exactDialogTextLineSet",
                ("dialogTextTable",),
                list(expected_line_ids),
                list(actual_line_ids),
            )
        if (
            len(line_audio_ids) != len(expected_line_ids)
            or not all(line_audio_ids)
            or line_audio_ids != expected_audio_ids
        ):
            add_text_only_failure(
                "exactDialogTextAudioOverrides",
                ("dialogTextTable",),
                list(expected_audio_ids),
                list(line_audio_ids),
            )
        row_fields = {
            line_id: sorted(dialog_text_table.get(line_id, {}))
            if isinstance(dialog_text_table.get(line_id), dict) else []
            for line_id in expected_line_ids
        }
        if any(
            set(row_fields[line_id])
            != OFFLINE_EXHAUSTION_DIALOG_ROW_FIELDS
            for line_id in expected_line_ids
        ):
            add_text_only_failure(
                "exactDialogTextRowFields",
                ("dialogTextTable",),
                sorted(OFFLINE_EXHAUSTION_DIALOG_ROW_FIELDS),
                row_fields,
            )
        variant_shape_valid = (
            set(expected_audio_variants) <= set(line_audio_ids)
            and all(
                variants
                and all(
                    variant.startswith(f"{audio_id}_")
                    for variant in variants
                )
                for audio_id, variants in expected_audio_variants.items()
            )
        )
        present_base_audio_ids = (
            set(line_audio_ids) - expected_missing_audio_ids
        )
        if (
            not variant_shape_valid
            or actual_missing_audio_ids != expected_missing_audio_ids
            or not present_base_audio_ids <= (
                audio_stems | set(expected_audio_variants)
            )
        ):
            add_text_only_failure(
                "exactAudioDialogMembership",
                ("dialogTextTable", "audioDialog"),
                {
                    "missingAudioIds": sorted(expected_missing_audio_ids),
                    "audioVariants": {
                        key: list(values)
                        for key, values in expected_audio_variants.items()
                    },
                },
                {
                    "missingAudioIds": sorted(actual_missing_audio_ids),
                    "lineAudioIds": list(line_audio_ids),
                    "variantShapeValid": variant_shape_valid,
                },
            )
        expected_registration_status = safe_key(
            definition.get("dialogIdRegistrationStatus")
        ) or "absent"
        registry = dialog_id_index.get(story_key)
        printable_only_tokens = tuple(
            definition.get("printableOnlyDialogTokens") or ()
        )
        if expected_registration_status == "present_table_only":
            expected_options_by_group: dict[str, list[str]] = defaultdict(list)
            option_prefix = f"option_{story_key}_"
            for option_id in expected_option_ids:
                suffix = option_id.removeprefix(option_prefix)
                group = suffix.split("_", 1)[0]
                expected_options_by_group[group].append(option_id)
            expected_registry = {
                "registered": True,
                "memoryPackRecordKey": True,
                "registrationEvidence": [
                    "memorypack_record_key",
                    "printable_root_token",
                ],
                "hasRootKey": True,
                "trunkCount": 0,
                "trunkIndices": [],
                "lineCount": 0,
                "linesByTrunk": {},
                "optionGroupCount": len(expected_options_by_group),
                "optionCount": len(expected_option_ids),
                "optionsByGroup": dict(expected_options_by_group),
                "usedDialogTimelineCount": 0,
                "usedDialogTimelineIds": [],
            }
            if registry != expected_registry:
                add_text_only_failure(
                    "exactTableOnlyDialogIdRegistration",
                    ("dialogIdSource", "dialogIdIndex"),
                    expected_registry,
                    registry,
                )
            expected_printable_only_registry = {
                "registered": True,
                "memoryPackRecordKey": False,
                "registrationEvidence": ["printable_root_token"],
                "hasRootKey": True,
                "trunkCount": 0,
                "trunkIndices": [],
                "lineCount": 0,
                "linesByTrunk": {},
                "optionGroupCount": 0,
                "optionCount": 0,
                "optionsByGroup": {},
                "usedDialogTimelineCount": 0,
                "usedDialogTimelineIds": [],
            }
            actual_printable_only_registries = {
                token: dialog_id_index.get(token)
                for token in printable_only_tokens
            }
            if any(
                row != expected_printable_only_registry
                for row in actual_printable_only_registries.values()
            ):
                add_text_only_failure(
                    "exactPrintableOnlyDialogTokens",
                    ("dialogIdSource", "dialogIdIndex"),
                    {
                        token: expected_printable_only_registry
                        for token in printable_only_tokens
                    },
                    actual_printable_only_registries,
                )
        elif expected_registration_status == "absent":
            if registry is not None:
                add_text_only_failure(
                    "dialogIdRegistrationAbsent",
                    ("dialogIdIndex",),
                    {"present": False},
                    {"present": True, "row": registry},
                )
        else:
            add_text_only_failure(
                "supportedDialogIdRegistrationStatus",
                ("dialogIdIndex",),
                ["absent", "present_table_only"],
                expected_registration_status,
            )
        if story_key in timeline_line_orders:
            add_text_only_failure(
                "timelineRegistrationAbsent",
                ("timelineLineOrders",),
                {"present": False},
                {"present": True, "row": timeline_line_orders.get(story_key)},
            )
        if cutscene_matches:
            add_text_only_failure(
                "dialogTreeTextAssetAbsent",
                ("dialogTextAssetRoot",),
                [],
                cutscene_matches,
            )
        if expected_option_rows is not None and (
            not isinstance(dialog_option_table, dict)
            or actual_option_ids != expected_option_ids
            or any(
                dialog_option_table.get(option_id) != expected_row
                for option_id, expected_row in expected_option_rows.items()
            )
        ):
            add_text_only_failure(
                "exactDialogOptionDefinitions",
                ("dialogOptionTable",),
                expected_option_rows,
                {
                    option_id: dialog_option_table.get(option_id)
                    for option_id in actual_option_ids
                } if isinstance(dialog_option_table, dict) else {
                    "payloadType": type(dialog_option_table).__name__,
                },
            )
        if len(text_only_dialog_validation_failures) != failures_before:
            continue
        text_only_dialog_validation_by_key[story_key] = {
            "lineIds": list(expected_line_ids),
            "audioIds": list(line_audio_ids),
            "missingAudioIds": sorted(
                actual_missing_audio_ids,
                key=natural_key,
            ),
            "audioVariants": {
                audio_id: list(variants)
                for audio_id, variants
                in expected_audio_variants.items()
            },
            "optionIds": list(expected_option_ids),
            "optionRows": expected_option_rows,
            "dialogIdRegistrationStatus": expected_registration_status,
            "printableOnlyDialogTokens": list(printable_only_tokens),
            "printableOnlyTokenStatus": (
                "string_table_only_not_memorypack_records"
                if printable_only_tokens else "none"
            ),
        }
    if text_only_dialog_validation_failures:
        status["status"] = (
            "inactive_text_only_dialog_definition_validation_failed"
        )
        status["validationFailures"] = text_only_dialog_validation_failures
        status["validatorDiagnostics"] = text_only_dialog_validation_failures
        return {}, status

    num_id_table = read_json(source_paths["numIdStrTable"], {})
    timeline_ids = (
        ((num_id_table.get("timelines_id") or {}).get("dic") or {})
        if isinstance(num_id_table, dict)
        else {}
    )
    text_table = read_json(source_paths["textTable"], {})
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
    presentation_cutscene_valid = (
        set(OFFLINE_EXHAUSTION_REVERSE_HOST_COUNTS)
        == set(OFFLINE_EXHAUSTION_GAMEOBJECT_ROW_COUNTS)
        == set(OFFLINE_EXHAUSTION_CUTSCENE_DEFINITIONS)
    )
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
        expected_alias = OFFLINE_EXHAUSTION_ROOT_PLAYBACK_ALIASES.get(
            story_key
        )
        aliases = [
            alias
            for row in director_hosts
            for alias in row.get("crossStoryPlaybackAliases") or []
            if isinstance(alias, dict)
        ]
        containments = [
            containment
            for row in director_hosts
            for containment in row.get("crossStoryContainments") or []
            if isinstance(containment, dict)
        ]
        if expected_alias:
            root_story_key, playable_story_key = expected_alias
            alias_valid = (
                len(aliases) == 1
                and len(containments) == 1
                and safe_key(aliases[0].get("rootStoryKey"))
                == root_story_key
                and safe_key(aliases[0].get("playableAssetStoryKey"))
                == playable_story_key
                and safe_key(aliases[0].get("relation"))
                == "cutscene_root_director_playable_asset"
                and safe_key(aliases[0].get("edgeStatus"))
                == "exact_root_playback_alias_no_chronology_or_mission_owner"
                and safe_key(containments[0].get("hostStoryKey"))
                == root_story_key
                and safe_key(containments[0].get("embeddedStoryKey"))
                == playable_story_key
                and safe_key(containments[0].get("relation"))
                == "cutscene_root_embedded_timeline_asset"
                and safe_key(containments[0].get("edgeStatus"))
                == "exact_containment_no_chronology_or_mission_owner"
            )
        else:
            alias_valid = not aliases and not containments
        if (
            not presentation_cutscene_valid
            or len(object_rows)
            != OFFLINE_EXHAUSTION_GAMEOBJECT_ROW_COUNTS[story_key]
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
                for row in director_hosts
            )
            or not alias_valid
        ):
            presentation_cutscene_valid = False
            break

    registered_timeline_story_keys = {
        safe_key(value)
        for value in (
            timeline_ids.values()
            if isinstance(timeline_ids, dict)
            else []
        )
    }
    text_table_only_story_valid = True
    text_table_only_definitions = {
        **OFFLINE_EXHAUSTION_TEXT_ONLY_CUTSCENES,
        **OFFLINE_EXHAUSTION_TEXT_TABLE_ONLY_STORIES,
    }
    for text_only_key, definition in (
        text_table_only_definitions.items()
    ):
        expected_text_only_row_keys = set(
            definition["definitionRowKeys"]
        )
        text_only_row_keys = {
            key
            for key in (
                text_table
                if isinstance(text_table, dict)
                else {}
            )
            if key.startswith(f"{text_only_key}_")
        }
        if (
            text_only_row_keys != expected_text_only_row_keys
            or not all(
                isinstance(text_table.get(key), dict)
                and set(text_table[key]) == {"id", "text"}
                and isinstance(text_table[key].get("id"), int)
                and not isinstance(text_table[key].get("id"), bool)
                for key in expected_text_only_row_keys
            )
            or text_only_key in registered_timeline_story_keys
            or any(
                text_only_key in _string_list(row.get("storyKeys"))
                for row in gameobject_audit.get("gameObjects") or []
                if isinstance(row, dict)
            )
            or any(
                text_only_key in _string_list(row.get("targetStoryKeys"))
                for row in reverse_pptr_audit.get("relations") or []
                if isinstance(row, dict)
            )
            or any(
                text_only_key in _string_list(row.get("storyKeys"))
                for row in reverse_pptr_audit.get("directorHosts") or []
                if isinstance(row, dict)
            )
        ):
            text_table_only_story_valid = False
            break
    cutscene_definitions_valid = (
        set(OFFLINE_EXHAUSTION_CUTSCENE_DEFINITIONS)
        == set(OFFLINE_EXHAUSTION_REVERSE_HOST_COUNTS)
        and all(
            (
                (
                    isinstance(definition["timelineRegistryId"], int)
                    and safe_key(timeline_ids.get(
                        str(definition["timelineRegistryId"])
                    )) == story_key
                )
                or (
                    definition["timelineRegistryId"] is None
                    and not definition["files"]
                    and story_key not in registered_timeline_story_keys
                )
            )
            and all(
                (
                    isinstance(
                        payload := read_json(
                            source_paths[
                                f"cutsceneDefinition:{story_key}:{index}"
                            ],
                            {},
                        ),
                        dict,
                    )
                    and safe_key(payload.get("m_Name")) == root_name
                    and safe_key(payload.get("Name")) == root_name
                )
                for index, (_filename, _sha256, root_name) in enumerate(
                    definition["files"],
                    start=1,
                )
            )
            for story_key, definition in (
                OFFLINE_EXHAUSTION_CUTSCENE_DEFINITIONS.items()
            )
        )
    )
    if (
        not presentation_cutscene_valid
        or not cutscene_definitions_valid
        or not text_table_only_story_valid
    ):
        status["status"] = "inactive_cutscene_definition_validation_failed"
        return {}, status

    index: dict[str, dict[str, Any]] = {}
    for story_key in sorted(
        all_radio_keys,
        key=natural_key,
    ):
        context = OFFLINE_EXHAUSTION_RADIO_CONTEXTS.get(story_key)
        index[story_key] = {
            "sceneKey": story_key,
            "missionId": radio_mission_by_key[story_key],
            "recoveryStatus":
                "deferred_current_build_offline_surface_exhausted",
            "evidenceKind": (
                "leveldata_context_without_typed_story_activator"
                if context
                else "radio_definition_without_recovered_consumer"
            ),
            "definitionTable": "RadioTable",
            "audioMembershipTable": "AudioDialog",
            "audioMembershipStatus": (
                (
                    "all_current_audio_dialog_ids_missing"
                    if set(missing_audio_ids_by_story.get(
                        story_key,
                        (),
                    )) == radio_audio_ids_by_story[story_key]
                    else "partial_current_audio_dialog_missing_ids"
                )
                if story_key in missing_audio_ids_by_story
                else (
                    "present_current_audio_dialog_variants"
                    if story_key in radio_audio_variants_by_story
                    else "present_current_audio_dialog"
                )
            ),
            "audioVariants": {
                audio_id: list(variants)
                for audio_id, variants in (
                    radio_audio_variants_by_story.get(
                        story_key,
                        {},
                    )
                ).items()
            },
            "missingAudioIds": sorted(
                missing_audio_ids_by_story.get(story_key) or set(),
                key=natural_key,
            ),
            "nonOwningContext": (
                {
                    "questId": context["questId"],
                    "sourceFile": context["sourceFile"],
                    "distance": context["distance"],
                    "relation": context["allowedRoute"]["relation"],
                    "missionOwnership": False,
                    "orderEvidence": False,
                }
                if context else None
            ),
            "allowedNonOwningRoute": (
                {
                    **context["allowedRoute"],
                    "file": context["sourceFile"],
                }
                if context else None
            ),
            "nativeMappingId": OFFLINE_EXHAUSTION_MAPPING_ID,
            "gameAssemblySha256":
                OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
            "consumerBoundary": (
                (
                    "the exact LevelData file contains this radio id near "
                    f"{context['questId']}, but the collection proximity "
                    "has no typed playback action, activation carrier, or "
                    "mission-order semantics; the RadioTable and "
                    "AudioDialog rows establish only the playable definition"
                    if context else
                    "exact ids occur only in current RadioTable definitions "
                    "and AudioDialog membership, including exact authored "
                    "variants where present, across the audited "
                    "MissionRuntime, LevelScript, GameplayConfig, Table, "
                    "object-index, and direct native playback-caller "
                    "surfaces"
                )
            ),
            "orderBoundary": (
                "LevelData byte proximity, collection order, quest "
                "predecessors, and filename suffixes do not establish "
                "playback or relative Story order"
                if context else None
            ),
            "reopenWhen": (
                "installed binary, exported tables, object index, "
                "or another typed producer/consumer registry changes"
            ),
            "graphEffect": "none",
        }
    for story_key in sorted(all_dialog_keys, key=natural_key):
        definition = OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[story_key]
        validation = dialog_validation_by_key[story_key]
        allowed_non_owning_route = definition.get("allowedNonOwningRoute")
        index[story_key] = {
            "sceneKey": story_key,
            "missionId": dialog_mission_by_key[story_key],
            "recoveryStatus":
                "deferred_current_build_offline_surface_exhausted",
            "evidenceKind":
                (
                    "leveldata_property_resolved_levelscript_result_branch"
                    if validation["levelDataDialogBranchContext"]
                    else (
                    "levelscript_talk_completion_dependency_without_playback_owner"
                    if validation["levelScriptTaskConsumer"]
                    else (
                        "mission_tracked_npc_proxy_dialog_context_without_playback_owner"
                        if validation["missionNpcProxyTracking"]
                        else (
                            "npc_proxy_dialog_consumer_without_mission_owner"
                            if validation["npcProxyConsumers"]
                            else (
                                "registered_dialog_definition_with_nonowning_parent_carrier"
                                if allowed_non_owning_route else
                                "registered_dialog_definition_without_recovered_activator"
                            )
                        )
                    ))
                ),
            "definitionAsset":
                OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[story_key]["filename"],
            "definitionAssets": [
                filename
                for filename in (
                    OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[story_key][
                        "filename"
                    ],
                    OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[story_key].get(
                        "extraConfigFilename"
                    ),
                )
                if filename
            ],
            "definitionTable": "DialogTextTable",
            "runtimeRegistry": "Beyond.Gameplay.DialogIdTable",
            "runtimeRegistryKey": validation["registryKey"],
            "definitionName": validation["definitionName"],
            "runtimeRegistrationEvidence": [
                "memorypack_record_key",
                "printable_root_token",
            ],
            "lineIds": validation["lineIds"],
            "audioIds": validation["audioIds"],
            "missingAudioIds": validation["missingAudioIds"],
            "audioMembershipStatus": (
                "all_current_audio_dialog_ids_missing"
                if len(validation["missingAudioIds"])
                == len(validation["audioIds"])
                else (
                    "partial_current_audio_dialog_missing_ids"
                    if validation["missingAudioIds"]
                    else "present_current_audio_dialog"
                )
            ),
            "optionIds": validation["optionIds"],
            "dialogTreeAssetStatus": "present_exact_definition",
            "dialogTreeBranchGroups": validation["treeBranchGroups"],
            "dialogTreeTerminalOptionRoutes":
                validation["terminalOptionRoutes"],
            "dialogTreeRouteStatus": (
                (
                    "authored_terminal_option_routes_recovered"
                    if validation["terminalOptionRoutes"]
                    else (
                        "authored_internal_branch_routes_recovered"
                        if validation["treeBranchGroups"]
                        else "authored_linear_or_single_option_routes_recovered"
                    )
                )
                if (
                    "treeBranchGroups" in definition
                    or "terminalOptionRoutes" in definition
                )
                else "not_explicitly_audited"
            ),
            "sharedTimelineContext": validation["timelineContext"],
            "npcProxyConsumer": validation["npcProxyConsumer"],
            "npcProxyConsumers": validation["npcProxyConsumers"],
            "missionNpcProxyTracking":
                validation["missionNpcProxyTracking"],
            "levelScriptTaskConsumer":
                validation["levelScriptTaskConsumer"],
            "levelDataDialogBranchContext":
                validation["levelDataDialogBranchContext"],
            "allowedNonOwningRoute": allowed_non_owning_route,
            "nativeMappingId": OFFLINE_EXHAUSTION_MAPPING_ID,
            "gameAssemblySha256":
                OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
            "consumerBoundary": (
                (
                    "the hash-locked LevelData properties resolve this dialog "
                    "through an exact LevelScript listener or StartDialogAction "
                    "control path; the local script has no serialized nominal "
                    "MissionRuntime quest owner or server-event producer"
                    if validation["levelDataDialogBranchContext"]
                    else (
                    "the exact NpcProxyEx entry selects this registered "
                    "DialogTree, and exact MissionRuntime quest tracking points "
                    "to the same NPC proxy for HUD/navigation context; the "
                    "NpcProxyEx missionId is empty and no serialized selection "
                    "condition proves dialog playback, a unique quest owner, "
                    "or activation timing"
                    if validation["missionNpcProxyTracking"]
                    else (
                        "the exact NpcProxyEx entry selects this registered "
                        "DialogTree as an NPC interaction dialog, but its "
                        "authored missionId is empty; no exact mission/quest "
                        "owner or activation timing is serialized"
                        if validation["npcProxyConsumers"]
                        else (
                            "the registered parent DialogTree has an exact typed "
                            "prime-reachable carrier for this dialog; the owning "
                            "mission observes completion of the parent, but no "
                            "original-data source identifies what activates the "
                            "parent dialog"
                            if allowed_non_owning_route else
                            "the exact DialogTree, MemoryPack DialogId registration, "
                            "DialogTextTable rows, and AudioDialog membership where "
                            "present establish a current runtime-loadable definition; "
                            "no exact MissionRuntime, LevelScript, NpcProxyEx, "
                            "object-index, or direct native playback caller exposes "
                            "its activator"
                        )
                    )
                ))
            ),
            "orderBoundary": (
                (
                    "result case 8 selects succeed_dialog and case 9 selects "
                    "failed_dialog in the same configured start_dialog context; "
                    "the two outcome dialogs are exclusive alternatives, not a "
                    "sequence"
                    if validation["levelDataDialogBranchContext"]
                    else
                    "DialogId registration, DialogTree node order, line ids, "
                    "shared Timeline context, and filename suffixes do not order "
                    "the Story file relative to mission playback"
                )
            ),
            "reopenWhen": (
                "installed binary, DialogId source/index, DialogTree, "
                "DialogTextTable, AudioDialog, NpcProxyExDataTable, object "
                "index, MissionRuntime tracking, shared Timeline, or another "
                "typed producer/consumer "
                "registry changes"
            ),
            "graphEffect": "none",
        }
    for story_key in sorted(
        all_text_only_dialog_keys,
        key=natural_key,
    ):
        definition = OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS[story_key]
        validation = text_only_dialog_validation_by_key[story_key]
        branch_context = definition.get("nonOwningContext")
        table_only_registration = (
            validation["dialogIdRegistrationStatus"]
            == "present_table_only"
        )
        index[story_key] = {
            "sceneKey": story_key,
            "missionId": text_only_dialog_mission_by_key[story_key],
            "recoveryStatus":
                "deferred_current_build_offline_surface_exhausted",
            "evidenceKind": (
                "dialog_text_table_branch_payload_with_parent_dialog_tree_context"
                if branch_context
                else (
                    "registered_dialog_table_rows_without_tree_asset_or_consumer"
                    if table_only_registration
                    else "dialog_text_table_only_without_registry_asset_or_consumer"
                )
            ),
            "definitionTable": "DialogTextTable",
            "definitionTables": (
                ["DialogTextTable", "DialogOptionTable"]
                if validation["optionIds"]
                else ["DialogTextTable"]
            ),
            "lineIds": validation["lineIds"],
            "audioIds": validation["audioIds"],
            "audioVariants": validation["audioVariants"],
            "missingAudioIds": validation["missingAudioIds"],
            "optionIds": validation["optionIds"],
            "optionRows": validation["optionRows"],
            "optionRouteStatus": (
                "definitions_present_route_unresolved"
                if validation["optionIds"]
                else "no_current_option_definitions"
            ),
            "audioMembershipStatus": (
                "all_current_audio_dialog_ids_missing"
                if len(validation["missingAudioIds"])
                == len(validation["audioIds"])
                else (
                    "partial_current_audio_dialog_missing_ids"
                    if validation["missingAudioIds"]
                    else "present_current_audio_dialog"
                )
            ),
            "dialogIdRegistrationStatus": (
                "present_table_only"
                if table_only_registration else "absent"
            ),
            "printableOnlyDialogTokens":
                validation["printableOnlyDialogTokens"],
            "printableOnlyTokenStatus":
                validation["printableOnlyTokenStatus"],
            "dialogTreeAssetStatus": "absent",
            "timelineStatus": "absent",
            "nonOwningContext": definition.get("nonOwningContext"),
            "allowedNonOwningRoute": definition.get(
                "allowedNonOwningRoute"
            ),
            "nativeMappingId": OFFLINE_EXHAUSTION_MAPPING_ID,
            "gameAssemblySha256":
                OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
            "consumerBoundary": (
                "the exact DialogTextTable line/audio group is consumed "
                "as authored trunks inside the registered parent "
                f"DialogTree {branch_context['parentStoryKey']} behind "
                "a no-bypass multi-quest completion branch; this proves "
                "reachable branch context but not one unique quest trigger"
                if branch_context
                else (
                    "the exact DialogId registration and DialogTextTable/"
                    "DialogOptionTable rows establish a loadable table-only "
                    "dialog root, but no DialogTree TextAsset, Timeline, "
                    "AudioDialog membership, typed MissionRuntime or "
                    "LevelScript consumer, Lua reference, or object-index "
                    "carrier exposes its activator; option definitions prove "
                    "authored choices but not their route graph; printable-only "
                    "DialogId tokens are not MemoryPack records or route targets"
                    if table_only_registration
                    else
                    "the exact DialogTextTable line/audio group and any exact "
                    "DialogOptionTable option definitions have no current "
                    "DialogId registration, DialogTree asset, Timeline, "
                    "AudioDialog membership, typed MissionRuntime or "
                    "LevelScript consumer, Lua reference, or object-index "
                    "carrier; option definitions prove authored choices but "
                    "not their route graph"
                )
            ),
            "orderBoundary": (
                (
                    "the parent DialogTree branch identifies authored "
                    "reachability after any of seven completed quest states, "
                    "but does not select one triggering quest or place this "
                    "payload in a unique mission chronology"
                    if branch_context
                    else
                    "line ids, printable-only token suffixes, and fallback/"
                    "manual display positions do not establish playback, "
                    "option routing, or mission chronology"
                )
            ),
            "reopenWhen": (
                "installed binary, DialogTextTable, DialogOptionTable, "
                "AudioDialog, DialogId index, TextAsset inventory, Timeline "
                "index, object index, Lua corpus, or another typed "
                "producer/consumer changes"
            ),
            "graphEffect": "none",
        }
    for story_key in sorted(all_sns_keys, key=natural_key):
        validation = sns_validation_by_key[story_key]
        index[story_key] = {
            "sceneKey": story_key,
            "missionId": sns_mission_by_key[story_key],
            "recoveryStatus":
                "deferred_current_build_offline_surface_exhausted",
            "evidenceKind":
                (
                    "cross_mission_sns_tracking_context_without_playback"
                    if validation["runtimeTracking"]
                    else "sns_dialog_definition_without_recovered_activator"
                ),
            "definitionTables": [
                "SNSDialogTable",
                "SNSDialogOptionTable",
            ],
            "chatId": validation["chatId"],
            "contentIds": validation["contentIds"],
            "optionIds": validation["optionIds"],
            "contentParamsByContentId":
                validation["contentParamsByContentId"],
            "relatedMissionId": "",
            "runtimeTrackingContext": validation["runtimeTracking"],
            "nativeMappingId": OFFLINE_EXHAUSTION_MAPPING_ID,
            "gameAssemblySha256":
                OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
            "consumerBoundary": (
                (
                    "the exact SNSDialogTable content graph defines this "
                    "Story file, and an exact SnsTrackingInfo in the named "
                    "runtime mission points to it for HUD/navigation; "
                    "SnsTrackingInfo does not play SNS content, relatedMissionId "
                    "is empty, and no original-data source assigns it to the "
                    "nominal mission or a branch arm"
                    if validation["runtimeTracking"]
                    else
                    "the exact SNSDialogTable content graph and "
                    "SNSDialogOptionTable routes define this current Story "
                    "file; relatedMissionId is empty, and no exact "
                    "MissionRuntime, LevelScript/LevelData, Lua, object-index, "
                    "or accepted native playback dispatch exposes its activator"
                )
            ),
            "orderBoundary": (
                "the internal SNS content graph orders messages only; table "
                "order, dialog suffixes, and character chat membership do not "
                "place the Story file in mission chronology"
            ),
            "reopenWhen": (
                "installed binary, MissionRuntime, SNSDialogTable, "
                "SNSDialogOptionTable, object index, Lua corpus, or another typed "
                "producer/consumer registry changes"
            ),
            "graphEffect": "none",
        }
    for story_key in sorted(all_text_keys, key=natural_key):
        definition = OFFLINE_EXHAUSTION_TEXT_DEFINITIONS[story_key]
        index[story_key] = {
            "sceneKey": story_key,
            "missionId": text_mission_by_key[story_key],
            "recoveryStatus":
                "deferred_current_build_offline_surface_exhausted",
            "evidenceKind":
                "reading_popup_definition_without_recovered_activator",
            "definitionTables": [
                "ReadingPopUpTable",
                *(
                    []
                    if definition.get("richContentStatus") == "absent"
                    else ["RichContentTable"]
                ),
                *(
                    ["PrtsAllItem", "PrtsRecord"]
                    if definition.get("prtsDefinition")
                    else []
                ),
                *(
                    ["PrtsReading"]
                    if definition.get("prtsReadingDefinition")
                    else []
                ),
            ],
            "readingPopupRowId": definition.get("readingPopupRowId"),
            "readingPopupRowIds": list(
                definition.get("readingPopupRows")
                or [definition.get("readingPopupRowId")]
            ),
            "richContentStatus":
                definition.get("richContentStatus", "present"),
            "contentTextIds": list(definition["contentTextIds"]),
            "prtsDefinition": (
                {
                    "rowId": definition["prtsDefinition"]["rowId"],
                    "firstLvId":
                        definition["prtsDefinition"]["row"]["firstLvId"],
                    "type": definition["prtsDefinition"]["row"]["type"],
                    "order": definition["prtsDefinition"]["row"]["order"],
                    "relation": "prts_archive_entry_targets_story",
                    "missionOwnership": False,
                    "orderEvidence": False,
                }
                if definition.get("prtsDefinition")
                else None
            ),
            "prtsReadingDefinition": (
                {
                    "rowId": definition["prtsReadingDefinition"]["rowId"],
                    "contentIds": [
                        row["contentId"]
                        for row in definition["prtsReadingDefinition"]["row"]["list"].values()
                    ],
                    "relation": "prts_reading_catalog_targets_story",
                    "missionOwnership": False,
                    "orderEvidence": False,
                }
                if definition.get("prtsReadingDefinition")
                else None
            ),
            "nativeMappingId": OFFLINE_EXHAUSTION_MAPPING_ID,
            "gameAssemblySha256":
                OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
            "consumerBoundary": (
                "the exact ReadingPopUpTable carrier and RichContentTable "
                "payload define this current Story file"
                + (
                    ", while the exact PRTS archive entry provides a second "
                    "non-activating content carrier"
                    if definition.get("prtsDefinition")
                    else ""
                )
                + "; no exact "
                "MissionRuntime, LevelScript/LevelData interactive, "
                "object-index, or direct native caller exposes its activator"
            ),
            "orderBoundary": (
                "popup table order, PRTS collection order, content-node "
                "order, text ids, and filename suffixes do not place the "
                "Story file in mission chronology"
            ),
            "reopenWhen": (
                "installed binary, ReadingPopUpTable, RichContentTable, "
                "PrtsAllItem, PrtsRecord, object index, or another typed "
                "producer/consumer registry changes, or an original Lua "
                "corpus becomes available"
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
                OFFLINE_EXHAUSTION_CUTSCENE_DEFINITIONS[story_key][
                    "timelineRegistryId"
                ]
            ),
            "definitionRootNames": [
                root_name
                for _filename, _sha256, root_name
                in OFFLINE_EXHAUSTION_CUTSCENE_DEFINITIONS[story_key][
                    "files"
                ]
            ],
            "directorHostCount": len(director_hosts),
            "gameObjectRowCount": len(object_rows),
            "rootPlaybackAlias": (
                {
                    "rootStoryKey": (
                        OFFLINE_EXHAUSTION_ROOT_PLAYBACK_ALIASES[story_key][0]
                    ),
                    "playableAssetStoryKey": (
                        OFFLINE_EXHAUSTION_ROOT_PLAYBACK_ALIASES[story_key][1]
                    ),
                    "relation": "cutscene_root_director_playable_asset",
                    "edgeStatus":
                        "exact_root_playback_alias_no_chronology_or_mission_owner",
                }
                if story_key in OFFLINE_EXHAUSTION_ROOT_PLAYBACK_ALIASES
                else None
            ),
            "nativeMappingId": OFFLINE_EXHAUSTION_MAPPING_ID,
            "playbackMappingId":
                OFFLINE_EXHAUSTION_REVERSE_PPTR_MAPPING_ID,
            "gameAssemblySha256":
                OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
            "logicalBundles": [
                row.get("logicalBundle") or {}
                for row in object_rows
            ],
            "candidateStatus": (
                "no_typed_owner_or_runtime_sibling_or_descendant"
                if object_rows
                else "no_forward_gameobject_row_or_typed_owner_runtime_candidate"
            ),
            "consumerBoundary": (
                "exact root Timeline assets resolve through PlayableDirector "
                "hosts and complete GameObject descendant hierarchies where "
                "a separate root object exists; exact cross-Story director "
                "aliases are composition only, not chronology or ownership; "
                "and "
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
    for text_only_key, definition in (
        OFFLINE_EXHAUSTION_TEXT_ONLY_CUTSCENES.items()
    ):
        index[text_only_key] = {
            "sceneKey": text_only_key,
            "missionId": definition["missionId"],
            "recoveryStatus":
                "deferred_current_build_offline_surface_exhausted",
            "evidenceKind":
                "text_table_only_cutscene_without_recovered_original_story_consumer",
            "definitionTable": "TextTable",
            "definitionRowKeys": sorted(
                definition["definitionRowKeys"],
                key=natural_key,
            ),
            "nativeMappingId": OFFLINE_EXHAUSTION_MAPPING_ID,
            "gameAssemblySha256": OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
            "consumerBoundary": definition.get("consumerBoundary") or (
                "the exact TextTable group has no Timeline registry entry, "
                "indexed cutscene root, reverse PPtr relation, "
                "PlayableDirector host, structured action, Lua consumer, or "
                "direct native cutscene caller in the audited build"
            ),
            "orderBoundary": definition.get("orderBoundary") or (
                "TextTable row order and fallback/manual display positions "
                "do not establish playback, ownership, or mission chronology"
            ),
            "reopenWhen": (
                "installed binary, TextTable, Timeline registry, object "
                "index, Lua corpus, or another typed producer/consumer "
                "registry changes"
            ),
            "graphEffect": "none",
        }
    for story_key, definition in (
        OFFLINE_EXHAUSTION_TEXT_TABLE_ONLY_STORIES.items()
    ):
        index[story_key] = {
            "sceneKey": story_key,
            "missionId": definition["missionId"],
            "recoveryStatus":
                "deferred_current_build_offline_surface_exhausted",
            "evidenceKind":
                "text_table_only_story_without_recovered_asset_or_consumer",
            "storyKind": definition["storyKind"],
            "definitionTable": "TextTable",
            "definitionRowKeys": list(definition["definitionRowKeys"]),
            "nativeMappingId": OFFLINE_EXHAUSTION_MAPPING_ID,
            "gameAssemblySha256":
                OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
            "consumerBoundary": (
                "the exact TextTable group has no Timeline registration, "
                "DialogTree/TextAsset carrier, object-index relation, "
                "structured action or direct native caller "
                "in the audited build"
            ),
            "reopenWhen": (
                "installed binary, TextTable, Timeline or DialogId registry, "
                "TextAsset/object index or another typed "
                "producer/consumer registry changes"
            ),
            "graphEffect": "none",
        }
    for row in index.values():
        mission_id = safe_key(row.get("missionId"))
        branch_context = mission_branch_context_by_mission.get(mission_id)
        if branch_context:
            row["missionQuestBranchContext"] = branch_context
        linear_context = mission_linear_context_by_mission.get(mission_id)
        if linear_context:
            row["missionQuestSequenceContext"] = linear_context
        topology_context = mission_topology_context_by_mission.get(mission_id)
        if topology_context:
            row["missionQuestTopologyContext"] = topology_context
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
        "deferredDialogStoryKeysByMission": {
            mission: sorted(
                (
                    story_key
                    for story_key, story_mission
                    in all_dialog_mission_by_key.items()
                    if story_mission == mission
                ),
                key=natural_key,
            )
            for mission in sorted(
                set(all_dialog_mission_by_key.values()),
                key=natural_key,
            )
        },
        "deferredSnsStoryKeysByMission": {
            mission: sorted(
                (
                    story_key
                    for story_key, story_mission
                    in sns_mission_by_key.items()
                    if story_mission == mission
                ),
                key=natural_key,
            )
            for mission in sorted(
                set(sns_mission_by_key.values()),
                key=natural_key,
            )
        },
        "deferredTextStoryKeysByMission": {
            mission: sorted(
                (
                    story_key
                    for story_key, story_mission
                    in text_mission_by_key.items()
                    if story_mission == mission
                ),
                key=natural_key,
            )
            for mission in sorted(
                set(text_mission_by_key.values()),
                key=natural_key,
            )
        },
        "deferredTextTableOnlyStoryKeysByMission": {
            mission: sorted(
                (
                    story_key
                    for story_key, story_mission
                    in text_table_only_story_mission_by_key.items()
                    if story_mission == mission
                ),
                key=natural_key,
            )
            for mission in sorted(
                set(text_table_only_story_mission_by_key.values()),
                key=natural_key,
            )
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
    direct_quest_story_relations = {
        "client_action_start": (1, "start"),
        "client_action_succeed": (2, "succeed"),
        "client_action_failed": (4, "failed"),
    }
    for quest in (flow or {}).get("quests") or []:
        if not isinstance(quest, dict):
            continue
        quest_id = safe_key(quest.get("id"))
        if not quest_id:
            continue
        for row in quest.get("storyConnections") or []:
            if not isinstance(row, dict):
                continue
            scene_key = safe_key(row.get("key"))
            relation = safe_key(row.get("relation"))
            objective_index = row.get("objectiveIndex")
            finish_id = row.get("finishId")
            if (
                scene_key
                and relation == "objective_tracking_story_reference"
                and safe_key(row.get("direction")) == "context"
                and safe_key(row.get("phase")) == "tracking"
                and safe_key(row.get("confidence")) == "native_typed_context"
                and safe_key(row.get("trackingType")) == "SnsTrackingInfo"
                and row.get("playback") is False
                and re.fullmatch(
                    r"MissionRuntimeAsset\.questDic\[\*\]\.objectiveList"
                    r"\[\d+\]\.trackingInfoList\[\d+\]\.snsDialogId",
                    safe_key(row.get("source")),
                )
                and isinstance(objective_index, int)
                and not isinstance(objective_index, bool)
                and objective_index > 0
                and isinstance(row.get("trackingIndex"), int)
                and not isinstance(row.get("trackingIndex"), bool)
                and int(row["trackingIndex"]) >= 0
            ):
                quest_ids.add(quest_id)
                scene_keys.add(scene_key)
                continue
            if (
                scene_key
                and relation == "objective_condition"
                and safe_key(row.get("direction")) == "story_to_quest"
                and safe_key(row.get("phase")) == "progress"
                and safe_key(row.get("confidence")) == "direct"
                and safe_key(row.get("conditionType"))
                == "CheckTalkOptionFinish"
                and re.fullmatch(
                    r"MissionRuntimeAsset\.questDic\[\*\]\.objectiveList"
                    r"\[\d+\]\.condition\._dialogId",
                    safe_key(row.get("source")),
                )
                and isinstance(objective_index, int)
                and not isinstance(objective_index, bool)
                and objective_index > 0
                and isinstance(finish_id, int)
                and not isinstance(finish_id, bool)
            ):
                quest_ids.add(quest_id)
                scene_keys.add(scene_key)
                continue
            expected = direct_quest_story_relations.get(relation)
            if (
                not scene_key
                or not expected
                or safe_key(row.get("direction")) != "quest_to_story"
                or safe_key(row.get("phase")) != expected[1]
                or safe_key(row.get("confidence")) != "native_typed_direct"
                or row.get("actionSlot") != expected[0]
                or not isinstance(row.get("actionId"), int)
                or isinstance(row.get("actionId"), bool)
                or int(row["actionId"]) < 0
                or not safe_key(row.get("actionType"))
                or not re.fullmatch(
                    r"MissionRuntimeAsset\.clientActionMapKey\[\d+\] -> "
                    r"actionMapRaw\.actionList\[\d+\]\._[A-Za-z]+Id",
                    safe_key(row.get("source")),
                )
            ):
                continue
            quest_ids.add(quest_id)
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
        attach_sources = [
            source
            for source in placement.get("questAttachSources") or []
            if isinstance(source, dict)
        ]
        non_owning_ids = {
            safe_key(source.get("questId"))
            for source in attach_sources
            if (
                safe_key(source.get("source"))
                in NON_OWNING_DIAGNOSTIC_QUEST_ATTACH_SOURCES
                and safe_key(source.get("questId"))
            )
        }
        owning_or_unclassified_ids = {
            safe_key(source.get("questId"))
            for source in attach_sources
            if (
                safe_key(source.get("source"))
                not in NON_OWNING_DIAGNOSTIC_QUEST_ATTACH_SOURCES
                and safe_key(source.get("questId"))
            )
        }
        attached_ids = [
            quest_id
            for quest_id in _string_list(placement.get("questIds"))
            if (
                quest_id not in non_owning_ids
                or quest_id in owning_or_unclassified_ids
            )
        ]
        if not attached_ids:
            continue
        quest_ids.update(attached_ids)
        scene_keys.add(scene_key)
        for source in attach_sources:
            if safe_key(source.get("questId")) not in attached_ids:
                continue
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


def _closed_exact_native_context_isolated_scenes(
    flow: dict[str, Any],
    isolated_scene_keys: set[str],
    owner_mission: str,
) -> list[dict[str, Any]]:
    """Close exact playback contexts that deliberately provide no chronology."""
    closed: list[dict[str, Any]] = []
    for connection in _flow_story_connections(flow):
        scene_key = safe_key(connection.get("key"))
        relation = safe_key(connection.get("relation"))
        if (
            scene_key not in isolated_scene_keys
            or safe_key(connection.get("storyOwnerMission")) != owner_mission
            or safe_key(connection.get("direction")) != "context"
        ):
            continue
        if relation == "npc_proxy_segment_levelscript_mission_context":
            context_mission = (
                safe_key(connection.get("contextMissionBundle"))
                or owner_mission
            )
            native_owners = [
                row for row in connection.get("nativeEventOwners") or []
                if isinstance(row, dict)
            ]
            exact_paths = [
                row for row in native_owners
                if safe_key(row.get("status"))
                == "exact_serialized_control_path"
                and safe_key(row.get("headerName"))
                == "ScriptEvent_OnLeaderEnterTriggerVolume"
                and any(
                    isinstance(step, dict)
                    and safe_key(step.get("recordClass")).startswith("play_")
                    and scene_key in (
                        {
                            safe_key(text_id).rsplit("_", 1)[0]
                            for text_id in step.get("texts") or []
                            if safe_key(text_id)
                        }
                        if safe_key(step.get("recordClass")) == "play_black"
                        else set(_string_list(step.get("texts")))
                    )
                    for step in row.get("path") or []
                )
            ]
            if (
                safe_key(connection.get("confidence"))
                != "native_exact_npc_proxy_segment_shell"
                or safe_key(connection.get("evidenceTier"))
                != "derived_exact_shell"
                or safe_key(connection.get("questTriggerStatus"))
                != "same_authored_npc_proxy_segment_not_quest_playback"
                or safe_key(connection.get("executionSide")) != "client"
                or connection.get("serverExchange") is not False
                or not _string_list(connection.get("npcProxyIds"))
                or not _string_list(connection.get("segmentIdsGlobal"))
                or not _string_list(connection.get("candidateQuestIds"))
                or any(
                    not quest_id.startswith(f"{context_mission}_q#")
                    for quest_id in _string_list(
                        connection.get("candidateQuestIds")
                    )
                )
                or len(exact_paths) != len(native_owners)
                or not exact_paths
                or not _string_list(connection.get("sourceFiles"))
            ):
                continue
            closed.append({
                "sceneKey": scene_key,
                "recoveryStatus":
                    "closed_exact_npc_proxy_segment_playback_context_no_relative_order",
                "relation": relation,
                "nominalStoryMissionId": owner_mission,
                "contextMissionId": context_mission,
                "contextMissionMismatch": context_mission != owner_mission,
                "npcProxyIds": _string_list(connection.get("npcProxyIds")),
                "segmentIdsGlobal": _string_list(
                    connection.get("segmentIdsGlobal")
                ),
                "candidateQuestIds": _string_list(
                    connection.get("candidateQuestIds")
                ),
                "nativeEventPaths": exact_paths,
                "sourceFiles": _string_list(connection.get("sourceFiles")),
                "orderBoundary": (
                    "the exact tracked NpcProxy segment and serialized native "
                    "event path establish mission-shell playback context; they "
                    "do not identify one quest trigger or relative Story order"
                ),
            })
            continue
        if (
            connection.get("storyBinding") is not True
            or connection.get("ownership") is not False
        ):
            continue
        if relation == "radio_trigger_zone_mission_state_playback_context":
            gate_roles = set(_string_list(
                connection.get("missionStateGateRoles")
            ))
            roles_by_id = connection.get("missionStateRolesById")
            recognized_roles = {
                "hideAfterMissionId",
                "hideBeforeMissionId",
                "hideCompleteMissionId",
            }
            if (
                safe_key(connection.get("phase"))
                != "mission_state_trigger_zone"
                or safe_key(connection.get("confidence"))
                != "native_exact_serialized_co_carrier"
                or safe_key(connection.get("evidenceTier")) != "direct"
                or safe_key(connection.get("missionStateId"))
                != owner_mission
                or not gate_roles
                or not gate_roles.issubset(recognized_roles)
                or not isinstance(roles_by_id, dict)
                or set(_string_list(roles_by_id.get(owner_mission)))
                != gate_roles
                or any(
                    not safe_key(mission_id)
                    or not set(_string_list(roles)).issubset(
                        recognized_roles
                    )
                    or not _string_list(roles)
                    for mission_id, roles in roles_by_id.items()
                )
                or not safe_key(connection.get("nativeMappingId"))
                or "PlayRadio" not in safe_key(
                    connection.get("nativeConsumer")
                )
                or connection.get("unionTag") != 9
                or connection.get("serializedMemberCount") != 7
                or connection.get("specificDataListCount") != 1
                or not _string_list(connection.get("levelIds"))
                or not _string_list(connection.get("sourceFiles"))
                or not isinstance(connection.get("recordOffset"), int)
                or not isinstance(connection.get("recordEndOffset"), int)
            ):
                continue
            closed.append({
                "sceneKey": scene_key,
                "recoveryStatus":
                    "closed_exact_native_playback_context_no_relative_order",
                "relation": relation,
                "missionStateId": owner_mission,
                "missionStateGateRoles": sorted(
                    _string_list(connection.get("missionStateGateRoles")),
                    key=natural_key,
                ),
                "levelIds": _string_list(connection.get("levelIds")),
                "sourceFiles": _string_list(connection.get("sourceFiles")),
                "nativeMappingId": safe_key(
                    connection.get("nativeMappingId")
                ),
                "orderBoundary": (
                    "the exact radio trigger-zone row and mission-state "
                    "gates establish playback context, but entering the "
                    "world trigger supplies no relative Story order"
                ),
            })
            continue
        if relation == "npc_patrol_action_radio_playback_context":
            patrol_offset = connection.get("patrolRecordOffset")
            action_offset = connection.get("radioActionRecordOffset")
            action_end = connection.get("radioActionRecordEndOffset")
            next_patrol_offset = connection.get("nextPatrolRecordOffset")
            if (
                safe_key(connection.get("phase")) != "npc_patrol_action"
                or safe_key(connection.get("confidence"))
                != "native_exact_serialized_patrol_action"
                or safe_key(connection.get("evidenceTier")) != "direct"
                or connection.get("questActivation") is not False
                or connection.get("questPlayback") is not False
                or connection.get("questCompletion") is not False
                or safe_key(connection.get("patrolEnvelopeStatus")) not in {
                    "exact_full_patrol_record_consume",
                    "exact_typed_neighbor_boundaries_partial_point_decode",
                }
                or not isinstance(connection.get("patrolId"), int)
                or connection.get("patrolId") <= 0
                or connection.get("patrolActionType") != 9
                or connection.get("serializedMemberCount") != 26
                or safe_key(connection.get("patrolSubActionDataStatus"))
                != "null"
                or not safe_key(connection.get("nativeMappingId"))
                or "PlayRadio" not in safe_key(
                    connection.get("nativeConsumer")
                )
                or not _string_list(connection.get("levelIds"))
                or not _string_list(connection.get("sourceFiles"))
                or not all(isinstance(value, int) for value in (
                    patrol_offset,
                    action_offset,
                    action_end,
                    next_patrol_offset,
                ))
                or not (
                    patrol_offset < action_offset < action_end
                    <= next_patrol_offset
                )
            ):
                continue
            closed.append({
                "sceneKey": scene_key,
                "recoveryStatus":
                    "closed_exact_native_patrol_playback_context_no_relative_order",
                "relation": relation,
                "patrolId": connection.get("patrolId"),
                "patrolPointIndex": connection.get("patrolPointIndex"),
                "patrolEnvelopeStatus": safe_key(
                    connection.get("patrolEnvelopeStatus")
                ),
                "levelIds": _string_list(connection.get("levelIds")),
                "sourceFiles": _string_list(connection.get("sourceFiles")),
                "nativeMappingId": safe_key(
                    connection.get("nativeMappingId")
                ),
                "orderBoundary": (
                    "the exact typed patrol action establishes native radio "
                    "playback context; the patrol payload serializes no "
                    "mission/quest identity or relative Story order"
                ),
            })
            continue
        if relation != "mission_tracked_world_entity_levelscript_context":
            continue
        native_rows = connection.get("worldEntityLevelScriptEvidence") or []
        candidate_quest_ids = _string_list(
            connection.get("candidateQuestIds")
        )
        tracking_rows = connection.get("trackingRows") or []
        native_rows_valid = bool(native_rows)
        for row in native_rows:
            listener = row.get("listener") if isinstance(row, dict) else None
            path = (
                listener.get("path")
                if isinstance(listener, dict)
                else None
            )
            if (
                not isinstance(row, dict)
                or safe_key(row.get("nativeAction")) != "PlayRadio"
                or not isinstance(row.get("playbackRecordOffset"), int)
                or not isinstance(listener, dict)
                or safe_key(listener.get("status"))
                != "exact_serialized_control_path"
                or not isinstance(path, list)
                or not any(
                    isinstance(step, dict)
                    and safe_key(step.get("actionName")) == "PlayRadio"
                    and safe_key(step.get("recordClass")) == "play_radio"
                    and scene_key in _string_list(step.get("texts"))
                    for step in path
                )
            ):
                native_rows_valid = False
                break
        if (
            safe_key(connection.get("phase"))
            != "local_leader_trigger_world_entity_context"
            or safe_key(connection.get("confidence"))
            != "native_exact_mission_navigation_context"
            or safe_key(connection.get("evidenceTier"))
            != "derived_exact_foreign_key"
            or connection.get("questActivation") is not False
            or connection.get("questPlayback") is not False
            or connection.get("questCompletion") is not False
            or not candidate_quest_ids
            or any(
                not quest_id.startswith(f"{owner_mission}_q#")
                for quest_id in candidate_quest_ids
            )
            or not tracking_rows
            or any(
                not isinstance(row, dict)
                or safe_key(row.get("missionId")) != owner_mission
                or safe_key(row.get("questId")) not in candidate_quest_ids
                for row in tracking_rows
            )
            or not native_rows_valid
        ):
            continue
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_native_playback_context_no_relative_order",
            "relation": relation,
            "candidateQuestIds": candidate_quest_ids,
            "worldEntityIds": _string_list(
                connection.get("worldEntityIds")
            ),
            "levelIds": _string_list(connection.get("levelIds")),
            "scriptIds": _string_list(connection.get("scriptIds")),
            "sourceFiles": _string_list(connection.get("sourceFiles")),
            "nativeEventPathCount": len(native_rows),
            "orderBoundary": (
                "the exact local leader-trigger playback path and typed "
                "MissionRuntime world-entity tracking join establish mission "
                "context, but tracking is not activation, playback, "
                "completion, ownership, or relative Story order"
            ),
        })
    return sorted(closed, key=lambda row: natural_key(row["sceneKey"]))


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
    routed_rows_by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _flow_story_connections(flow):
        if isinstance(row, dict) and safe_key(row.get("key")):
            routed_rows_by_key[safe_key(row.get("key"))].append(row)
    deferred: list[dict[str, Any]] = []
    for scene_key in sorted(isolated_scene_keys, key=natural_key):
        evidence = offline_exhaustion_index.get(scene_key)
        routed_rows = routed_rows_by_key.get(scene_key, [])
        allowed_route = (
            evidence.get("allowedNonOwningRoute")
            if isinstance(evidence, dict)
            else None
        )
        routed_rows_valid = not routed_rows
        if routed_rows and isinstance(allowed_route, dict):
            routed_rows_valid = all(
                all(row.get(field) == value for field, value in allowed_route.items())
                for row in routed_rows
            )
            context = evidence.get("nonOwningContext") or {}
            quest_id = safe_key(context.get("questId"))
            if quest_id:
                expected_distance = context.get("distance")
                quest_rows = [
                    quest
                    for quest in flow.get("quests") or []
                    if isinstance(quest, dict)
                    if safe_key(quest.get("id")) == quest_id
                ]
                level_data_refs = [
                    ref
                    for quest in quest_rows
                    for ref in quest.get("levelDataStoryRefs") or []
                    if isinstance(ref, dict)
                    and safe_key(ref.get("storyRef")) == scene_key
                ]
                routed_rows_valid = (
                    routed_rows_valid
                    and len(quest_rows) == 1
                    and len(level_data_refs) == 1
                    and level_data_refs[0].get("distance")
                    == expected_distance
                    and safe_key(level_data_refs[0].get("file"))
                    == safe_key(allowed_route.get("file"))
                )
            elif context.get("candidateQuestIds"):
                expected_quests = sorted(
                    [
                        safe_key(value)
                        for value in context.get("candidateQuestIds") or []
                        if safe_key(value)
                    ],
                    key=natural_key,
                )
                route = routed_rows[0] if len(routed_rows) == 1 else {}
                carrier_context = (
                    route.get("carrierQuestStateContext") or {}
                    if isinstance(route, dict)
                    else {}
                )
                branch_contexts = carrier_context.get(
                    "questStateBranchContexts"
                ) or []
                routed_rows_valid = (
                    routed_rows_valid
                    and len(routed_rows) == 1
                    and sorted(
                        _string_list(carrier_context.get("candidateQuestIds")),
                        key=natural_key,
                    ) == expected_quests
                    and safe_key(context.get("parentStoryKey"))
                    == safe_key(route.get("parentStoryKey"))
                    and safe_key(context.get("sourceFile"))
                    in _string_list(route.get("sourceFiles"))
                    and bool(branch_contexts)
                    and all(
                        sorted(
                            _string_list(branch.get("questIds")),
                            key=natural_key,
                        ) == expected_quests
                        and safe_key(branch.get("conditionEvalString"))
                        == safe_key(context.get("conditionEvalString"))
                        and branch.get("noBypass") is True
                        and {
                            condition.get("targetQuestState")
                            for condition in branch.get("conditions") or []
                            if isinstance(condition, dict)
                        } == {context.get("targetQuestState")}
                        for branch in branch_contexts
                        if isinstance(branch, dict)
                    )
                )
        if (
            not isinstance(evidence, dict)
            or safe_key(evidence.get("missionId")) != owner_mission
            or not routed_rows_valid
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


def _closed_exact_disconnected_dialog_tree_context_isolated_scenes(
    flow: dict[str, Any],
    isolated_scene_keys: set[str],
    owner_mission: str,
) -> list[dict[str, Any]]:
    """Close exact authored DialogTree actions disconnected from the prime path."""
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
    closed: list[dict[str, Any]] = []
    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        parent_story_key = safe_key(row.get("parentStoryKey"))
        occurrences = [
            occurrence
            for occurrence in row.get("dialogTreeNarrativeActions") or []
            if isinstance(occurrence, dict)
        ]
        if (
            scene_key not in isolated_scene_keys
            or safe_key(row.get("relation"))
            != "dialog_tree_narrative_action"
            or safe_key(row.get("storyOwnerMission")) != owner_mission
            or not parent_story_key
            or safe_key(row.get("confidence")) not in allowed_confidences
            or safe_key(row.get("evidenceTier"))
            not in allowed_evidence_tiers
            or safe_key(row.get("scopeCompleteness")) != "complete"
            or row.get("unscopedParentStoryKeys")
            or parent_story_key
            not in set(_string_list(row.get("allParentStoryKeys")))
            or safe_key(row.get("nativeMappingId"))
            != DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID
            or not _string_list(row.get("sourceFiles"))
            or not _string_list(row.get("sourcePathIds"))
            or not occurrences
            or int(row.get("occurrenceCount") or 0) != len(occurrences)
            or any(
                safe_key(occurrence.get("dialogKey"))
                != parent_story_key
                or safe_key(occurrence.get("actionType"))
                not in allowed_action_types
                or safe_key(occurrence.get("nativeMappingId"))
                != DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID
                or occurrence.get("reachableFromPrimeNode") is not False
                or _string_list(occurrence.get("primeToActionNodePath"))
                or _string_list(
                    occurrence.get("primeToActionConnectionPath")
                )
                or not (
                    _string_list(occurrence.get("incomingNodeIds"))
                    or _string_list(occurrence.get("outgoingNodeIds"))
                )
                or not safe_key(occurrence.get("textId"))
                or not safe_key(occurrence.get("actionPath"))
                or not safe_key(occurrence.get("nodeId"))
                or not safe_key(occurrence.get("sourceFile"))
                or not safe_key(occurrence.get("sourcePathId"))
                for occurrence in occurrences
            )
        ):
            continue
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_native_disconnected_dialog_tree_context_no_file_order",
            "relation": "dialog_tree_narrative_action",
            "parentStoryKey": parent_story_key,
            "textIds": sorted({
                safe_key(occurrence.get("textId"))
                for occurrence in occurrences
            }, key=natural_key),
            "nodeIds": sorted({
                safe_key(occurrence.get("nodeId"))
                for occurrence in occurrences
            }, key=natural_key),
            "sourceFiles": _string_list(row.get("sourceFiles")),
            "sourcePathIds": _string_list(row.get("sourcePathIds")),
            "nativeMappingId":
                DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID,
            "activationBoundary": (
                "the exact narrative action and parent DialogTree are "
                "authored, but the action node has no serialized path from "
                "the tree's prime node; an unknown external activation "
                "mechanism is not inferred"
            ),
            "orderBoundary": (
                "disconnected local node adjacency supplies neither runtime "
                "playback nor a Story-file order edge"
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


def _closed_exact_timeline_foreign_dialog_isolated_scenes(
    flow: dict[str, Any],
    isolated_scene_keys: set[str],
    mission: str,
) -> list[dict[str, Any]]:
    """Close exact foreign-dialog Timeline blocks with parent playback scope."""
    accepted_host_missions = {
        mission,
        *_string_list(flow.get("_sourceVariantMissionIds")),
    }
    exact_owner_statuses = {
        "exact_serialized_control_path",
        "exact_serialized_control_path_equivalent_duplicates",
    }
    closed: list[dict[str, Any]] = []
    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        parent_story_key = safe_key(row.get("parentStoryKey"))
        text_ids = set(_string_list(row.get("textIds")))
        option_ids = set(_string_list(row.get("optionIds")))
        timeline_ids = set(_string_list(row.get("timelines")))
        source_files = set(_string_list(row.get("sourceFiles")))
        containments = [
            containment
            for containment in row.get(
                "timelineDialogContainments"
            ) or []
            if isinstance(containment, dict)
        ]
        parent_occurrences = [
            occurrence
            for occurrence in row.get(
                "parentDialogNativeOccurrences"
            ) or []
            if isinstance(occurrence, dict)
        ]
        if (
            scene_key not in isolated_scene_keys
            or safe_key(row.get("relation"))
            != "timeline_dialog_contains_foreign_dialog"
            or safe_key(row.get("confidence")) != "native_exact_host"
            or safe_key(row.get("storyOwnerMission")) != mission
            or safe_key(row.get("graphEffect")) != "none"
            or not parent_story_key
            or not text_ids
            or not timeline_ids
            or not source_files
            or len(containments) != int(row.get("occurrenceCount") or 0)
            or not containments
            or not parent_occurrences
        ):
            continue
        if any(
            safe_key(containment.get("key")) != scene_key
            or scene_key not in {
                safe_key(containment.get("rawDialogKey")),
                "misc_"
                + safe_key(containment.get("rawDialogKey")),
            }
            or safe_key(containment.get("dialogKey"))
            != parent_story_key
            or safe_key(containment.get("timeline"))
            not in timeline_ids
            or safe_key(containment.get("sourceFile"))
            not in source_files
            or set(_string_list(containment.get("lineIds")))
            != text_ids
            or not set(_string_list(containment.get("optionIds")))
            <= option_ids
            or safe_key(containment.get("dialogJoin"))
            != "dialog_id_table_used_timeline"
            or safe_key(containment.get("placementStatus"))
            != (
                "exact_contiguous_foreign_dialog_lines_"
                "with_parent_on_both_sides"
            )
            or not safe_key(
                containment.get("beforeParentLineId")
            ).startswith(f"{parent_story_key}_")
            or not safe_key(
                containment.get("afterParentLineId")
            ).startswith(f"{parent_story_key}_")
            or safe_key(containment.get("graphEffect")) != "none"
            for containment in containments
        ):
            continue

        native_paths: list[dict[str, Any]] = []
        valid = True
        for occurrence in parent_occurrences:
            action_local_id = occurrence.get("localId")
            if (
                safe_key(occurrence.get("recordClass"))
                != "play_dialog"
                or not safe_key(occurrence.get("actionName"))
                or parent_story_key
                not in _string_list(
                    occurrence.get("allStoryKeysInRecord")
                )
                or not isinstance(action_local_id, int)
                or isinstance(action_local_id, bool)
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
                    in exact_owner_statuses
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
                "closed_exact_native_timeline_foreign_dialog_playback_"
                "context_no_file_order",
            "relation":
                "timeline_dialog_contains_foreign_dialog",
            "parentStoryKey": parent_story_key,
            "timelineIds": sorted(timeline_ids, key=natural_key),
            "textIds": sorted(text_ids, key=natural_key),
            "optionIds": sorted(option_ids, key=natural_key),
            "beforeParentLineIds": sorted({
                safe_key(containment.get("beforeParentLineId"))
                for containment in containments
            }, key=natural_key),
            "afterParentLineIds": sorted({
                safe_key(containment.get("afterParentLineId"))
                for containment in containments
            }, key=natural_key),
            "nativeEventPaths": native_paths,
            "placementBoundary": (
                "the exact registered parent Timeline and native parent "
                "playback path establish nested playback; parent dialog "
                "content occurs on both sides, so no Story-file edge is "
                "created"
            ),
            "graphEffect": "none",
        })
    return sorted(closed, key=lambda row: natural_key(row["sceneKey"]))


def _closed_exact_lua_controller_playback_isolated_scenes(
    story_trigger_manifest: dict[str, Any],
    isolated_scene_keys: set[str],
    owner_mission: str,
) -> list[dict[str, Any]]:
    """Close exact shipped-Lua playback with deliberately unresolved owner."""
    closed: list[dict[str, Any]] = []
    for scene_key in sorted(isolated_scene_keys, key=natural_key):
        row = story_trigger_manifest.get(scene_key)
        if (
            not isinstance(row, dict)
            or safe_key(row.get("key")) != scene_key
            or safe_key(row.get("nominalMissionId")) != owner_mission
            or safe_key(row.get("attachmentStatus"))
            != "trigger_known_owner_unresolved"
        ):
            continue
        routes = [
            route
            for route in row.get("routes") or []
            if isinstance(route, dict)
        ]
        if len(routes) != 1:
            continue
        route = routes[0]
        lua_file = safe_key(route.get("luaFile"))
        phase = safe_key(route.get("phase"))
        expected_steps = [
            {
                "id": lua_file,
                "kind": "luaController",
                "phase": phase,
            },
            {
                "id": "Beyond.Gameplay.Actions.GameAction::PlayCutscene",
                "kind": "nativePlayback",
            },
        ]
        if (
            safe_key(route.get("storyKey")) != scene_key
            or safe_key(route.get("relation")) != "lua_controller_playback"
            or safe_key(route.get("direction")) != "playback"
            or safe_key(route.get("causality"))
            != "playback_owner_unresolved"
            or safe_key(route.get("confidence"))
            != "shipped_lua_literal_plus_native_entry"
            or safe_key(route.get("evidenceTier")) != "direct"
            or safe_key(route.get("ownerStatus")) != "unresolved"
            or route.get("missionId") is not None
            or route.get("questId") is not None
            or safe_key(route.get("questTriggerStatus"))
            != "no_mission_or_quest_identity_serialized"
            or safe_key(route.get("scope")) != "phase"
            or not phase
            or safe_key(route.get("luaCall")) != "GameAction.PlayCutscene"
            or safe_key(route.get("luaSymbol")) != "CUT_SCENE_ID"
            or safe_key(route.get("nativeEntry"))
            != "Beyond.Gameplay.Actions.GameAction::PlayCutscene"
            or not lua_file
            or _string_list(route.get("sourceFiles")) != [lua_file]
            or route.get("serverExchange") is not False
            or route.get("steps") != expected_steps
        ):
            continue
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_lua_controller_playback_"
                "no_mission_owner_or_relative_order",
            "relation": "lua_controller_playback",
            "phase": phase,
            "luaFile": lua_file,
            "luaSymbol": "CUT_SCENE_ID",
            "luaCall": "GameAction.PlayCutscene",
            "nativeEntry":
                "Beyond.Gameplay.Actions.GameAction::PlayCutscene",
            "ownerStatus": "unresolved",
            "playbackBoundary": (
                "the shipped phase controller proves exact cutscene playback; "
                "it serializes no mission or quest identity and therefore "
                "establishes neither mission ownership nor relative Story order"
            ),
            "graphEffect": "none",
        })
    return closed


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

    ``CheckTalkOptionFinish`` objective conditions are exact Story-to-quest
    completion dependencies. They prove that one quest consumes the dialog's
    synchronized finish state, but not which mission or quest starts playback.

    Counted LevelScript interactive maps are similarly exact: a typed
    ``LevelInteractiveData`` record's component-94 ``type_id`` selects one
    dialog or ReadingPopUp Story file. This recovers the source script and
    interactive identity, but neither map/local-id order nor object placement
    establishes activation timing or relative Story order.
    """
    closed: list[dict[str, Any]] = []
    for quest in flow.get("quests") or []:
        if not isinstance(quest, dict):
            continue
        quest_id = safe_key(quest.get("id"))
        for row in quest.get("storyConnections") or []:
            if not isinstance(row, dict):
                continue
            scene_key = safe_key(row.get("key"))
            objective_index = row.get("objectiveIndex")
            tracking_index = row.get("trackingIndex")
            if (
                scene_key not in isolated_scene_keys
                or not quest_id.startswith(f"{owner_mission}_q#")
                or safe_key(row.get("kind")) != "sns"
                or safe_key(row.get("relation"))
                != "objective_tracking_story_reference"
                or safe_key(row.get("direction")) != "context"
                or safe_key(row.get("phase")) != "tracking"
                or safe_key(row.get("confidence"))
                != "native_typed_context"
                or safe_key(row.get("trackingType")) != "SnsTrackingInfo"
                or row.get("playback") is not False
                or safe_key(row.get("attachmentBoundary"))
                != (
                    "authored objective tracking attachment only; "
                    "SnsTrackingInfo.Execute is not SNS playback"
                )
                or safe_key(row.get("orderBoundary"))
                != (
                    "tracking configuration establishes no activation time "
                    "or relative Story order"
                )
                or not re.fullmatch(
                    r"MissionRuntimeAsset\.questDic\[\*\]\.objectiveList"
                    r"\[\d+\]\.trackingInfoList\[\d+\]\.snsDialogId",
                    safe_key(row.get("source")),
                )
                or not isinstance(objective_index, int)
                or isinstance(objective_index, bool)
                or objective_index <= 0
                or not isinstance(tracking_index, int)
                or isinstance(tracking_index, bool)
                or tracking_index < 0
            ):
                continue
            closed.append({
                "sceneKey": scene_key,
                "recoveryStatus":
                    "closed_exact_mission_tracking_context_no_relative_order",
                "relation": "objective_tracking_story_reference",
                "missionId": owner_mission,
                "questId": quest_id,
                "objectiveIndex": objective_index,
                "trackingIndex": tracking_index,
                "trackingType": "SnsTrackingInfo",
                "activationBoundary": (
                    "the exact MissionRuntime objective config attaches this "
                    "SNS conversation to client tracking; the native tracking "
                    "type does not start SNS playback"
                ),
                "orderBoundary": (
                    "quest attachment establishes mission context but no "
                    "activation time or relative Story order"
                ),
                "sourceFile": (
                    "export_full/structured/Persistent/Data/Json/"
                    f"MissionRuntimeAsset/{owner_mission}.json"
                ),
            })

    for row in flow.get("missionStoryConnections") or []:
        if not isinstance(row, dict):
            continue
        scene_key = safe_key(row.get("key"))
        accept_mode = row.get("acceptMode")
        finish_id = row.get("finishId")
        if (
            scene_key not in isolated_scene_keys
            or safe_key(row.get("kind")) != "dialog"
            or safe_key(row.get("relation")) != "mission_accept_dialog"
            or safe_key(row.get("direction")) != "story_to_mission"
            or safe_key(row.get("phase")) != "accept"
            or safe_key(row.get("confidence")) != "native_typed_direct"
            or safe_key(row.get("source"))
            != (
                f"MissionRuntimeAsset/{owner_mission}_meta.json."
                "acceptMode.modeInfo.dialogId"
            )
            or not isinstance(accept_mode, int)
            or isinstance(accept_mode, bool)
            or accept_mode < 0
            or safe_key(row.get("acceptModeType"))
            != "MissionAcceptMode+NPCInfo"
            or not safe_key(row.get("npcProxyId"))
            or not safe_key(row.get("levelId"))
            or not isinstance(finish_id, int)
            or isinstance(finish_id, bool)
        ):
            continue
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_mission_accept_dialog_no_relative_order",
            "relation": "mission_accept_dialog",
            "missionId": owner_mission,
            "phase": "accept",
            "acceptMode": accept_mode,
            "acceptModeType": "MissionAcceptMode+NPCInfo",
            "npcProxyId": safe_key(row.get("npcProxyId")),
            "levelId": safe_key(row.get("levelId")),
            "finishId": finish_id,
            "attachmentSemantics": (
                "the exact typed MissionRuntime meta asset selects this "
                "dialog for the mission-accept interaction"
            ),
            "orderBoundary": (
                "the accept phase proves mission ownership and lifecycle "
                "placement, but does not create a relative edge to another "
                "Story file"
            ),
            "sourceFile": (
                "export_full/structured/Persistent/Data/Json/"
                f"MissionRuntimeAsset/{owner_mission}_meta.json"
            ),
        })

    already_closed = {row["sceneKey"] for row in closed}
    for quest in flow.get("quests") or []:
        if not isinstance(quest, dict):
            continue
        quest_id = safe_key(quest.get("id"))
        for row in quest.get("storyConnections") or []:
            if not isinstance(row, dict):
                continue
            scene_key = safe_key(row.get("key"))
            carriers = [
                carrier
                for carrier in (
                    row.get("dialogTreePrimeStoryPlaybackCarriers") or []
                )
                if isinstance(carrier, dict)
            ]
            source_files = _string_list(row.get("sourceFiles"))
            dependency = EXACT_PARENT_DIALOG_DEPENDENCIES.get(scene_key)
            if not isinstance(dependency, dict):
                continue
            expected_source = dependency["sourceFile"]
            source_path = ROOT / expected_source
            expected_carrier_values = list(
                dependency.get("trunkIds")
                or dependency.get("dialogIds")
                or ()
            )
            if (
                scene_key in already_closed
                or scene_key not in isolated_scene_keys
                or owner_mission != dependency["missionId"]
                or quest_id != dependency["questId"]
                or safe_key(row.get("relation"))
                != "dialog_tree_prime_reachable_story_playback_dependency"
                or safe_key(row.get("direction")) != "context"
                or safe_key(row.get("phase"))
                != "dialog_tree_prime_reachable_story_playback"
                or safe_key(row.get("confidence"))
                != "native_exact_prime_reachable_parent_quest_dependency"
                or safe_key(row.get("evidenceTier"))
                != "native_exact_context"
                or safe_key(row.get("parentStoryKey"))
                != dependency["parentStoryKey"]
                or safe_key(row.get("storyOwnerMission")) != owner_mission
                or row.get("storyBinding") is not True
                or row.get("ownership") is not False
                or row.get("dependencyOnly") is not True
                or row.get("questActivation") is not False
                or row.get("questPlayback") is not False
                or row.get("questCompletion") is not False
                or safe_key(row.get("questTriggerStatus"))
                != "exact_parent_dialog_completion_context_not_quest_playback_trigger"
                or safe_key(row.get("nativeMappingId"))
                != "dialog-tree-prime-reachable-completion-dependency-native-v1"
                or source_files != [expected_source]
                or not source_path.is_file()
                or _sha256_file(source_path)
                != dependency["sourceSha256"]
                or _string_list(row.get("sourcePathIds"))
                != [dependency["sourcePathId"]]
                or _string_list(row.get("trunkIds"))
                != list(dependency.get("trunkIds") or ())
                or _string_list(row.get("dialogIds"))
                != list(dependency.get("dialogIds") or ())
                or len(carriers) != dependency["carrierCount"]
                or [safe_key(carrier.get("carrierValue")) for carrier in carriers]
                != expected_carrier_values
                or any(
                    safe_key(carrier.get("dialogKey"))
                    != dependency["parentStoryKey"]
                    or safe_key(carrier.get("storyKey")) != scene_key
                    or safe_key(carrier.get("carrierKind"))
                    != dependency["carrierKind"]
                    or safe_key(carrier.get("reachDirection"))
                    != "prime_to_carrier"
                    or carrier.get("reachableFromPrimeNode") is not True
                    or safe_key(carrier.get("entryProof"))
                    != "exact_registered_dialog_tree_prime_node_reachability"
                    or carrier.get("registeredDialogRoot") is not True
                    or safe_key(carrier.get("sourceFile")) != expected_source
                    or safe_key(carrier.get("sourcePathId"))
                    != dependency["sourcePathId"]
                    or not _string_list(carrier.get("nodePath"))
                    or not carrier.get("connectionPath")
                    for carrier in carriers
                )
            ):
                continue
            closed.append({
                "sceneKey": scene_key,
                "recoveryStatus":
                    "closed_exact_parent_dialog_dependency_no_relative_order",
                "relation":
                    "dialog_tree_prime_reachable_story_playback_dependency",
                "missionId": owner_mission,
                "questId": quest_id,
                "parentStoryKey": dependency["parentStoryKey"],
                "trunkIds": list(dependency.get("trunkIds") or ()),
                "dialogIds": list(dependency.get("dialogIds") or ()),
                "sourceFiles": source_files,
                "sourceSha256": _sha256_file(source_path),
                "playbackSemantics": (
                    "the registered parent DialogTree's exact prime-node "
                    "path reaches the typed Story carrier for this file"
                ),
                "activationBoundary": (
                    "MissionRuntime observes completion of the parent dialog; "
                    "it does not identify the activator of either dialog"
                ),
                "orderBoundary": (
                    "prime-node reachability orders nodes inside the parent "
                    "DialogTree only; it creates no inter-file chronology"
                ),
            })

    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        if (
            scene_key not in isolated_scene_keys
            or safe_key(row.get("relation"))
            != "focus_mode_interact_locked_radio"
            or safe_key(row.get("direction")) != "context"
            or safe_key(row.get("phase")) != "interact_locked"
            or safe_key(row.get("confidence")) != "direct_mission_scope"
            or safe_key(row.get("storyOwnerMission")) != owner_mission
            or safe_key(row.get("focusModeField"))
            != "radioIdInteractLocked"
            or not safe_key(row.get("focusModeId"))
            or not safe_key(row.get("focusModeMissionId"))
            or not isinstance(row.get("subDataParentId"), int)
            or isinstance(row.get("subDataParentId"), bool)
        ):
            continue
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_runtime_config_no_relative_order",
            "relation": "focus_mode_interact_locked_radio",
            "focusModeId": safe_key(row.get("focusModeId")),
            "focusModeMissionId": safe_key(
                row.get("focusModeMissionId")
            ),
            "focusModeField": "radioIdInteractLocked",
            "subDataParentId": row["subDataParentId"],
            "activationBoundary": (
                "the exact FocusModeInstanceTable field selects the radio "
                "when interaction is locked, but does not establish when "
                "that focus-mode state is entered"
            ),
            "orderBoundary": (
                "table row order, focus-mode naming, and parent id do not "
                "establish relative Story chronology"
            ),
        })
    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        mission_state_id = safe_key(row.get("missionStateId"))
        target_checks = [
            check
            for check in row.get("targetMissionStateChecks") or []
            if isinstance(check, dict)
        ]
        if (
            scene_key not in isolated_scene_keys
            or safe_key(row.get("relation"))
            != "airwall_mission_state_radio_playback_context"
            or safe_key(row.get("direction")) != "context"
            or safe_key(row.get("phase"))
            != "airwall_mission_state_gate"
            or safe_key(row.get("confidence"))
            != "native_exact_serialized_co_carrier"
            or safe_key(row.get("evidenceTier")) != "direct"
            or safe_key(row.get("storyOwnerMission")) != owner_mission
            or not mission_state_id
            or row.get("storyBinding") is not True
            or row.get("ownership") is not False
            or row.get("dependencyOnly") is not False
            or row.get("questActivation") is not False
            or row.get("questPlayback") is not False
            or row.get("questCompletion") is not False
            or safe_key(row.get("nativeMappingId"))
            != "leveldata-airwall-mission-radio-memorypack-v1d4"
            or "GameAction.PlayRadio" not in safe_key(
                row.get("nativeConsumer")
            )
            or not _string_list(row.get("levelIds"))
            or not _string_list(row.get("sourceFiles"))
            or not safe_key(row.get("sourcePath"))
            or not isinstance(row.get("recordOffset"), int)
            or isinstance(row.get("recordOffset"), bool)
            or not isinstance(row.get("recordEndOffset"), int)
            or isinstance(row.get("recordEndOffset"), bool)
            or row["recordEndOffset"] <= row["recordOffset"]
            or row.get("serializedMemberCount") != 8
            or not safe_key(row.get("airWallGroupId"))
            or not isinstance(row.get("airWallSlotId"), int)
            or isinstance(row.get("airWallSlotId"), bool)
            or not isinstance(row.get("airWallDefaultOn"), bool)
            or not target_checks
            or any(
                safe_key(check.get("targetMissionId"))
                != mission_state_id
                or safe_key(check.get("comparison")) != "equal"
                or not isinstance(check.get("isQuest"), bool)
                or not isinstance(check.get("detailState"), int)
                or isinstance(check.get("detailState"), bool)
                for check in target_checks
            )
        ):
            continue
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_native_playback_context_no_relative_order",
            "relation": "airwall_mission_state_radio_playback_context",
            "missionStateId": mission_state_id,
            "targetMissionStateChecks": target_checks,
            "levelIds": _string_list(row.get("levelIds")),
            "sourceFiles": _string_list(row.get("sourceFiles")),
            "sourcePath": safe_key(row.get("sourcePath")),
            "recordOffset": row["recordOffset"],
            "recordEndOffset": row["recordEndOffset"],
            "airWallGroupId": safe_key(row.get("airWallGroupId")),
            "nativeMappingId": safe_key(row.get("nativeMappingId")),
            "activationBoundary": (
                "the exact AirWall row gates wall state on synchronized "
                "mission/quest state and the later pushback callback plays "
                "this radio; it does not prove a mission transition trigger "
                "or quest-owned playback"
            ),
            "orderBoundary": (
                "wall state, row order, and a later local pushback event do "
                "not establish relative Story chronology"
            ),
        })
    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        candidate_quest_ids = _string_list(row.get("candidateQuestIds"))
        if (
            scene_key not in isolated_scene_keys
            or safe_key(row.get("relation"))
            != "entity_tracking_interactive_story_target"
            or safe_key(row.get("direction")) != "context"
            or safe_key(row.get("phase")) != "tracking"
            or safe_key(row.get("confidence"))
            != "native_exact_tracked_interactive_property"
            or safe_key(row.get("evidenceTier")) != "native_exact_context"
            or safe_key(row.get("storyOwnerMission")) != owner_mission
            or safe_key(row.get("trackingMissionId")) != owner_mission
            or safe_key(row.get("questTriggerStatus"))
            != "navigation_target_configured_story_not_playback"
            or safe_key(row.get("executionSide")) != "client"
            or safe_key(row.get("networkRole"))
            != "local_navigation_context"
            or row.get("clientNavigationOnly") is not True
            or row.get("serverExchange") is not False
            or not candidate_quest_ids
            or any(
                not quest_id.startswith(f"{owner_mission}_q#")
                for quest_id in candidate_quest_ids
            )
            or not _string_list(row.get("levelIds"))
            or not _string_list(row.get("scriptIds"))
            or not _string_list(row.get("localScriptIds"))
            or not _string_list(row.get("entitySlotIds"))
            or not _string_list(row.get("entityDetailIds"))
            or not _string_list(row.get("entityTemplateIds"))
            or not _string_list(row.get("entityTemplatePaths"))
            or not _string_list(row.get("registrySourceFiles"))
            or not _string_list(row.get("interactiveTableSourceFiles"))
            or not _string_list(row.get("sourceFiles"))
            or safe_key(row.get("interactivePropertyKey")) != "type_id"
            or not isinstance(row.get("trackingObjectiveIndex"), int)
            or isinstance(row.get("trackingObjectiveIndex"), bool)
            or not isinstance(row.get("trackingIndex"), int)
            or isinstance(row.get("trackingIndex"), bool)
            or not isinstance(row.get("interactiveEntryOffset"), int)
            or isinstance(row.get("interactiveEntryOffset"), bool)
            or not isinstance(row.get("interactivePropertyOffset"), int)
            or isinstance(row.get("interactivePropertyOffset"), bool)
            or not isinstance(row.get("interactiveStoryOffset"), int)
            or isinstance(row.get("interactiveStoryOffset"), bool)
            or not (
                row["interactiveEntryOffset"]
                < row["interactivePropertyOffset"]
                < row["interactiveStoryOffset"]
            )
        ):
            continue
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_tracked_interactive_context_no_relative_order",
            "relation": "entity_tracking_interactive_story_target",
            "missionId": owner_mission,
            "candidateQuestIds": candidate_quest_ids,
            "trackingObjectiveIndex": row["trackingObjectiveIndex"],
            "trackingIndex": row["trackingIndex"],
            "levelIds": _string_list(row.get("levelIds")),
            "scriptIds": _string_list(row.get("scriptIds")),
            "localScriptIds": _string_list(row.get("localScriptIds")),
            "entitySlotIds": _string_list(row.get("entitySlotIds")),
            "entityDetailIds": _string_list(row.get("entityDetailIds")),
            "entityTemplateIds": _string_list(row.get("entityTemplateIds")),
            "interactivePropertyKey": "type_id",
            "interactiveEntryOffset": row["interactiveEntryOffset"],
            "interactivePropertyOffset": row["interactivePropertyOffset"],
            "interactiveStoryOffset": row["interactiveStoryOffset"],
            "sourceFiles": _string_list(row.get("sourceFiles")),
            "activationBoundary": (
                "the exact MissionRuntime EntityTrackingInfo target resolves "
                "through the registry to an interactive whose serialized "
                "type_id is this Story key; this is client navigation "
                "configuration, not playback or quest completion"
            ),
            "orderBoundary": (
                "tracking index, entity slot, serialized offsets, and world "
                "placement do not establish activation time or relative "
                "Story chronology"
            ),
        })
    completion_grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        context_mission = safe_key(row.get("contextMissionBundle"))
        context_quest = safe_key(row.get("contextQuestId"))
        source = safe_key(row.get("source"))
        objective_index = row.get("objectiveIndex")
        finish_id = row.get("finishId")
        if (
            scene_key not in isolated_scene_keys
            or safe_key(row.get("relation")) != "objective_condition"
            or safe_key(row.get("direction")) != "story_to_quest"
            or safe_key(row.get("phase")) != "progress"
            or safe_key(row.get("confidence")) != "direct"
            or safe_key(row.get("conditionType"))
            != "CheckTalkOptionFinish"
            or not re.fullmatch(
                r"MissionRuntimeAsset\.questDic\[\*\]\.objectiveList"
                r"\[\d+\]\.condition\._dialogId",
                source,
            )
            or not context_mission
            or not context_quest
            or not isinstance(objective_index, int)
            or isinstance(objective_index, bool)
            or objective_index <= 0
            or not isinstance(finish_id, int)
            or isinstance(finish_id, bool)
        ):
            continue
        completion_grouped[scene_key].append(row)

    for scene_key, rows in completion_grouped.items():
        targets = {
            (
                safe_key(row.get("contextMissionBundle")),
                safe_key(row.get("contextQuestId")),
                int(row["objectiveIndex"]),
                int(row["finishId"]),
            )
            for row in rows
        }
        if not targets:
            continue
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_mission_dialog_finish_dependency_no_relative_order",
            "relation": "objective_condition",
            "nominalStoryMissionId": owner_mission,
            "dependentMissionIds": sorted({
                mission_id
                for mission_id, _quest_id, _objective_index, _finish_id
                in targets
            }, key=natural_key),
            "dependentQuestIds": sorted({
                quest_id
                for _mission_id, quest_id, _objective_index, _finish_id
                in targets
            }, key=natural_key),
            "objectiveIndexes": sorted({
                objective_index
                for _mission_id, _quest_id, objective_index, _finish_id
                in targets
            }),
            "finishIds": sorted({
                finish_id
                for _mission_id, _quest_id, _objective_index, finish_id
                in targets
            }),
            "dependencySemantics": (
                "the quest objective reads the exact dialog's synchronized "
                "completion state through CheckTalkOptionFinish"
            ),
            "activationBoundary": (
                "the objective observes completion only; it does not prove "
                "which mission, quest, NPC interaction, or other runtime path "
                "starts the dialog"
            ),
            "orderBoundary": (
                "the dependency places quest completion after dialog finish "
                "but creates no relative edge between Story files"
            ),
            "sourceFiles": sorted({
                safe_key(row.get("sourceFile"))
                for row in rows
                if safe_key(row.get("sourceFile"))
            }),
        })

    quest_action_grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    expected_quest_actions = {
        "client_action_start": (1, "start"),
        "client_action_succeed": (2, "succeed"),
        "client_action_failed": (4, "failed"),
    }

    def append_exact_quest_action(
        raw_row: dict[str, Any],
        quest_id: str,
    ) -> None:
        scene_key = safe_key(raw_row.get("key"))
        relation = safe_key(raw_row.get("relation"))
        expected = expected_quest_actions.get(relation)
        if (
            scene_key not in isolated_scene_keys
            or not quest_id
            or not expected
            or safe_key(raw_row.get("direction")) != "quest_to_story"
            or safe_key(raw_row.get("phase")) != expected[1]
            or safe_key(raw_row.get("confidence")) != "native_typed_direct"
            or raw_row.get("actionSlot") != expected[0]
            or not isinstance(raw_row.get("actionId"), int)
            or isinstance(raw_row.get("actionId"), bool)
            or int(raw_row["actionId"]) < 0
            or not safe_key(raw_row.get("actionType"))
            or not re.fullmatch(
                r"MissionRuntimeAsset\.clientActionMapKey\[\d+\] -> "
                r"actionMapRaw\.actionList\[\d+\]\._[A-Za-z]+Id",
                safe_key(raw_row.get("source")),
            )
        ):
            return
        quest_action_grouped[scene_key].append({
            **raw_row,
            "contextQuestId": quest_id,
        })

    for quest in flow.get("quests") or []:
        if not isinstance(quest, dict):
            continue
        quest_id = safe_key(quest.get("id"))
        if not quest_id:
            continue
        for raw_row in quest.get("storyConnections") or []:
            if isinstance(raw_row, dict):
                append_exact_quest_action(raw_row, quest_id)
    for raw_row in flow.get("missionStoryConnections") or []:
        if (
            isinstance(raw_row, dict)
            and safe_key(raw_row.get("contextMissionBundle"))
            and safe_key(raw_row.get("contextMissionBundle")) != owner_mission
        ):
            append_exact_quest_action(
                raw_row,
                safe_key(raw_row.get("contextQuestId")),
            )
    for scene_key, rows in quest_action_grouped.items():
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_mission_quest_client_action_no_relative_order",
            "relation": safe_key(rows[0].get("relation")),
            "missionId": owner_mission,
            "contextMissionIds": sorted({
                safe_key(row.get("contextMissionBundle")) or owner_mission
                for row in rows
            }, key=natural_key),
            "contextMissionMismatch": any(
                safe_key(row.get("contextMissionBundle"))
                and safe_key(row.get("contextMissionBundle")) != owner_mission
                for row in rows
            ),
            "questIds": sorted({
                safe_key(row.get("contextQuestId"))
                for row in rows
                if safe_key(row.get("contextQuestId"))
            }, key=natural_key),
            "phases": sorted({
                safe_key(row.get("phase"))
                for row in rows
                if safe_key(row.get("phase"))
            }),
            "actionSlots": sorted({
                int(row["actionSlot"])
                for row in rows
            }),
            "actionIds": sorted({
                int(row["actionId"])
                for row in rows
            }),
            "actionTypes": sorted({
                safe_key(row.get("actionType"))
                for row in rows
                if safe_key(row.get("actionType"))
            }),
            "playbackSemantics": (
                "the exact typed MissionRuntime client action plays this "
                "Story id at the named quest lifecycle phase"
            ),
            "orderBoundary": (
                "quest lifecycle placement proves mission/quest playback "
                "context but creates no relative edge between Story files"
            ),
            "sourceFiles": sorted({
                safe_key(row.get("sourceFile"))
                or (
                    "export_full/structured/Persistent/Data/Json/"
                    f"MissionRuntimeAsset/{owner_mission}.json"
                )
                for row in rows
            }),
        })

    already_closed = {row["sceneKey"] for row in closed}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        mission_id = safe_key(row.get("npcProxyMissionId"))
        context_mission_bundle = safe_key(
            row.get("contextMissionBundle")
        )
        if (
            scene_key in already_closed
            or scene_key not in isolated_scene_keys
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
    quest_attachment_diagnostic_index:
        dict[str, dict[str, Any]] | None = None,
    cross_owner_story_connections: list[dict[str, Any]] | None = None,
    story_trigger_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    non_mission_content = non_mission_content or {}
    offline_exhaustion_index = offline_exhaustion_index or {}
    quest_attachment_diagnostic_index = (
        quest_attachment_diagnostic_index or {}
    )
    story_trigger_manifest = story_trigger_manifest or {}
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
    raw_missing_strict_quest_ids = sorted(
        (quest_ids & diagnostic_quest_ids) - strict_quest_ids,
        key=natural_key,
    )
    closed_quest_attachment_diagnostics = [
        quest_attachment_diagnostic_index[quest_id]
        for quest_id in raw_missing_strict_quest_ids
        if (
            quest_id in quest_attachment_diagnostic_index
            and safe_key(
                quest_attachment_diagnostic_index[quest_id].get("missionId")
            ) == mission
            and quest_attachment_diagnostic_index[quest_id].get(
                "graphEffect"
            ) == "none"
        )
    ]
    closed_quest_attachment_ids = {
        safe_key(row.get("questId"))
        for row in closed_quest_attachment_diagnostics
    }
    missing_strict_quest_ids = [
        quest_id
        for quest_id in raw_missing_strict_quest_ids
        if quest_id not in closed_quest_attachment_ids
    ]
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
    cross_owner_flow = flow
    if cross_owner_story_connections:
        cross_owner_flow = dict(flow)
        cross_owner_flow["missionStoryConnections"] = [
            *(
                flow.get("missionStoryConnections")
                if isinstance(flow.get("missionStoryConnections"), list)
                else []
            ),
            *cross_owner_story_connections,
        ]
    (
        closed_exact_native_isolated,
        _incomplete_native_isolated_keys,
    ) = _closed_exact_native_unordered_scenes(
        cross_owner_flow,
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
    for row in (
        _closed_exact_disconnected_dialog_tree_context_isolated_scenes(
            flow,
            set(isolated_scene_keys),
            safe_key(partial_row.get("mission")),
        )
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
    for row in _closed_exact_timeline_foreign_dialog_isolated_scenes(
        flow,
        set(isolated_scene_keys),
        safe_key(partial_row.get("mission")),
    ):
        closed_exact_native_isolated_by_key.setdefault(
            row["sceneKey"],
            row,
        )
    for row in _closed_exact_native_context_isolated_scenes(
        cross_owner_flow,
        set(isolated_scene_keys),
        safe_key(partial_row.get("mission")),
    ):
        if (
            row.get("contextMissionMismatch") is True
            or row["sceneKey"] not in closed_exact_native_isolated_by_key
        ):
            closed_exact_native_isolated_by_key[row["sceneKey"]] = row
    for row in _closed_exact_lua_controller_playback_isolated_scenes(
        story_trigger_manifest,
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
    closed_exact_runtime_config_isolated = (
        _closed_exact_runtime_config_isolated_scenes(
            cross_owner_flow,
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
    deferred_offline_option_route_groups: list[dict[str, Any]] = []
    for group_row in (
        ((partial_row.get("branches") or {}).get(
            "branchingNoExplicitRouteGroups"
        ) or [])
    ):
        if not isinstance(group_row, dict):
            continue
        story_key = safe_key(group_row.get("storyKey"))
        recovery = offline_exhaustion_index.get(story_key)
        if (
            story_key not in deferred_offline_exhausted_isolated_keys
            or not isinstance(recovery, dict)
            or recovery.get("optionRouteStatus")
            != "definitions_present_route_unresolved"
        ):
            continue
        group = int(group_row.get("group") or 0)
        option_ids = tuple(sorted(
            safe_key(option.get("optionId"))
            for option in group_row.get("options") or []
            if isinstance(option, dict) and safe_key(option.get("optionId"))
        ))
        expected_option_ids = tuple(sorted(
            option_id
            for option_id in _string_list(recovery.get("optionIds"))
            if option_id.startswith(f"option_{story_key}_{group}_")
        ))
        if not option_ids or option_ids != expected_option_ids:
            continue
        deferred_offline_option_route_groups.append({
            "storyKey": story_key,
            "group": group,
            "optionIds": list(option_ids),
            "recoveryStatus":
                "deferred_current_build_offline_route_surface_exhausted",
            "evidenceKind": recovery.get("evidenceKind"),
            "consumerBoundary": recovery.get("consumerBoundary"),
            "routeBoundary": (
                "the exact option definitions survive, but the current "
                "registered table-only dialog has no DialogTree, Timeline, "
                "typed runtime consumer, native token, or object-index "
                "carrier from which an option destination could be recovered"
            ),
            "graphEffect": "none",
        })
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
        "closedQuestAttachmentDiagnostics": len(
            closed_quest_attachment_diagnostics
        ),
        "questIdsWithoutAnyStoryEvidence": len(quest_ids_without_story_evidence),
        "diagnosticQuestAttachedSceneCount": len(diagnostic_quest_scenes),
        "diagnosticQuestIdsWithStoryAttachment": len(quest_ids & diagnostic_quest_ids),
        "questForks": int(summary.get("questForkCount") or 0),
        "questMerges": int(summary.get("questMergeCount") or 0),
        "strictDialogOptionGroups": int(summary.get("dialogLineOptionGroupCount") or 0),
        "noExplicitOptionRouteGroups": int(
            summary.get("noExplicitRouteGroupCount") or 0
        ),
        "actionableNoExplicitOptionRouteGroups": max(
            0,
            int(
                summary.get(
                    "branchingNoExplicitRouteGroupCount",
                    summary.get("noExplicitRouteGroupCount"),
                )
                or 0
            ) - len(deferred_offline_option_route_groups),
        ),
        "deferredOfflineExhaustedOptionRouteGroups": len(
            deferred_offline_option_route_groups
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
        "deferredOfflineExhaustedOptionRouteGroups":
            deferred_offline_option_route_groups,
        "actionableWeakOnlySceneKeys": actionable_weak_only_scene_keys,
        "closedExactNativeWeakOnlyScenes": closed_exact_native_weak_only,
        "nonActionableWeakOnlySceneKeys":
            non_actionable_weak_only_scene_keys,
        "isolatedSceneKinds": dict(sorted(isolated_kinds.items())),
        "questIdsWithoutStrictStoryAttachment": missing_strict_quest_ids,
        "closedQuestAttachmentDiagnostics":
            closed_quest_attachment_diagnostics,
        "questIdsWithoutAnyStoryEvidence": quest_ids_without_story_evidence,
        "untypedMultiSceneLevelscriptContexts": context_gaps,
        "closedNonPlaybackLevelscriptContexts": closed_context_gaps,
        "timelineUnresolvedKinds": dict(sorted(unresolved_kinds.items())),
        "diagnosticQuestAttachmentSources": dict(sorted(diagnostic_source_counts.items())),
        "unresolvedSourceNodes": partial_row.get("unresolvedSourceNodes") or [],
    }


def _exact_cross_owner_leveldata_story_context(
    connection: dict[str, Any],
    owner_mission: str,
    context_mission: str,
) -> bool:
    """Validate an exact foreign mission-shell LevelScript playback route."""
    story_key = safe_key(connection.get("key"))
    occurrences = connection.get("levelScriptOccurrences") or []
    if (
        not story_key
        or safe_key(connection.get("relation"))
        != "leveldata_levelscript_mission_context"
        or safe_key(connection.get("direction")) != "context"
        or safe_key(connection.get("phase")) != "context"
        or safe_key(connection.get("confidence")) != "native_exact_host"
        or safe_key(connection.get("storyOwnerMission")) != owner_mission
        or safe_key(connection.get("levelDataHostMissionId"))
        != context_mission
        or owner_mission == context_mission
        or safe_key(connection.get("questTriggerStatus")) != "unresolved"
        or connection.get("hasUnscopedOrOtherMissionOccurrences") is not False
        or not isinstance(occurrences, list)
        or not occurrences
        or connection.get("occurrenceCount") != len(occurrences)
        or connection.get("allOccurrenceCount") != len(occurrences)
    ):
        return False

    occurrence_actions: set[str] = set()
    occurrence_opcodes: set[str] = set()
    occurrence_level_ids: set[str] = set()
    occurrence_script_ids: set[str] = set()
    occurrence_source_files: set[str] = set()
    occurrence_level_data_files: set[str] = set()
    has_playback = False
    for occurrence in occurrences:
        if not isinstance(occurrence, dict):
            return False
        action_name = safe_key(occurrence.get("actionName"))
        action_code = safe_key(occurrence.get("actionCode"))
        action_kind = safe_key(occurrence.get("actionKind"))
        level_id = safe_key(occurrence.get("levelId"))
        script_id = safe_key(occurrence.get("scriptId"))
        source_file = safe_key(occurrence.get("sourceFile"))
        record_class = safe_key(occurrence.get("recordClass"))
        action_local_id = occurrence.get("localId")
        owners = occurrence.get("nativeEventOwners") or []
        level_data_hosts = occurrence.get("levelDataHosts") or []
        if (
            not action_name
            or not action_code
            or not action_kind
            or not level_id
            or not script_id
            or not source_file
            or not isinstance(action_local_id, int)
            or not safe_key(occurrence.get("actionMapRole")).startswith(
                "actionList#"
            )
            or not (
                record_class.startswith("play_")
                or record_class.startswith("preload_")
            )
            or not safe_key(occurrence.get("nativeMappingId")).startswith(
                "gameassembly-"
            )
            or set(_string_list(occurrence.get("allStoryKeysInRecord")))
            != {story_key}
            or safe_key(occurrence.get("nativeEventOwnerStatus"))
            != "exact_serialized_control_path"
            or not owners
            or not any(
                isinstance(owner, dict)
                and safe_key(owner.get("status"))
                == "exact_serialized_control_path"
                and isinstance(owner.get("headerLocalId"), int)
                and action_local_id in {
                    step.get("localId")
                    for step in owner.get("path") or []
                    if isinstance(step, dict)
                }
                for owner in owners
            )
            or not level_data_hosts
            or any(
                not isinstance(host, dict)
                or safe_key(host.get("missionId")) != context_mission
                or safe_key(host.get("levelId")) != level_id
                or safe_key(host.get("scriptId")) != script_id
                or not safe_key(host.get("levelDataFile"))
                or safe_key(host.get("encoding"))
                != "leveldata_member22_levelscriptbriefdata"
                or safe_key(host.get("nativeSchema"))
                != (
                    "LevelData/43.member22:"
                    "Dictionary<u64,LevelScriptBriefData/8>"
                )
                or not isinstance(host.get("briefData"), list)
                or not host["briefData"]
                or any(
                    not isinstance(brief, dict)
                    or safe_key(brief.get("scriptId")) != script_id
                    for brief in host["briefData"]
                )
                for host in level_data_hosts
            )
            or set(_string_list(occurrence.get("scopeEvidenceKinds")))
            != {
                "mission_leveldata_member22_contains_validated_"
                "levelscript_brief"
            }
        ):
            return False
        has_playback = has_playback or record_class.startswith("play_")
        occurrence_actions.add(action_name)
        occurrence_opcodes.add(f"{action_code}/{action_kind}")
        occurrence_level_ids.add(level_id)
        occurrence_script_ids.add(script_id)
        occurrence_source_files.add(source_file)
        occurrence_level_data_files.update(
            safe_key(host.get("levelDataFile"))
            for host in level_data_hosts
        )

    return (
        has_playback
        and set(_string_list(connection.get("nativeActions")))
        == occurrence_actions
        and set(_string_list(connection.get("opcodes")))
        == occurrence_opcodes
        and set(_string_list(connection.get("levelIds")))
        == occurrence_level_ids
        and set(_string_list(connection.get("scriptIds")))
        == occurrence_script_ids
        and set(_string_list(connection.get("sourceFiles")))
        == occurrence_source_files
        and set(_string_list(connection.get("levelDataFiles")))
        == occurrence_level_data_files
    )


def _exact_cross_owner_mission_condition_story_context(
    connection: dict[str, Any],
    owner_mission: str,
    context_mission: str,
) -> bool:
    """Validate a foreign playback route scoped by a typed mission condition."""
    story_key = safe_key(connection.get("key"))
    occurrences = connection.get("levelScriptOccurrences") or []
    if (
        not story_key
        or safe_key(connection.get("relation"))
        != "levelscript_mission_context"
        or safe_key(connection.get("direction")) != "context"
        or safe_key(connection.get("phase")) != "context"
        or safe_key(connection.get("confidence")) != "scoped_script"
        or safe_key(connection.get("storyOwnerMission")) != owner_mission
        or safe_key(connection.get("levelScriptMissionId"))
        != context_mission
        or owner_mission == context_mission
        or connection.get("hasUnscopedOrOtherMissionOccurrences") is not False
        or set(_string_list(connection.get("scopeEvidenceKinds")))
        != {"mission_condition_checks_script"}
        or not isinstance(occurrences, list)
        or not occurrences
        or connection.get("occurrenceCount") != len(occurrences)
        or connection.get("allOccurrenceCount") != len(occurrences)
    ):
        return False

    has_playback = False
    for occurrence in occurrences:
        if not isinstance(occurrence, dict):
            return False
        action_local_id = occurrence.get("localId")
        record_class = safe_key(occurrence.get("recordClass"))
        owners = occurrence.get("nativeEventOwners") or []
        mission_conditions = occurrence.get("missionConditions") or []
        if (
            not safe_key(occurrence.get("levelId"))
            or not safe_key(occurrence.get("scriptId"))
            or not safe_key(occurrence.get("sourceFile"))
            or not isinstance(action_local_id, int)
            or not safe_key(occurrence.get("actionMapRole")).startswith(
                "actionList#"
            )
            or not (
                record_class.startswith("play_")
                or record_class.startswith("preload_")
            )
            or not safe_key(occurrence.get("actionName"))
            or not safe_key(occurrence.get("nativeMappingId")).startswith(
                "gameassembly-"
            )
            or set(_string_list(occurrence.get("allStoryKeysInRecord")))
            != {story_key}
            or safe_key(occurrence.get("nativeEventOwnerStatus"))
            != "exact_serialized_control_path"
            or not owners
            or not any(
                isinstance(owner, dict)
                and safe_key(owner.get("status"))
                == "exact_serialized_control_path"
                and isinstance(owner.get("headerLocalId"), int)
                and action_local_id in {
                    step.get("localId")
                    for step in owner.get("path") or []
                    if isinstance(step, dict)
                }
                for owner in owners
            )
            or set(_string_list(occurrence.get("scopeEvidenceKinds")))
            != {"mission_condition_checks_script"}
            or not mission_conditions
            or any(
                not isinstance(condition, dict)
                or safe_key(condition.get("missionId")) != context_mission
                or not safe_key(condition.get("questId")).startswith(
                    f"{context_mission}_q#"
                )
                or not safe_key(condition.get("conditionType")).startswith(
                    "CheckLevelScript"
                )
                or not safe_key(condition.get("sourceFile"))
                for condition in mission_conditions
            )
        ):
            return False
        has_playback = has_playback or record_class.startswith("play_")
    return has_playback


def _exact_cross_owner_npc_proxy_segment_story_context(
    connection: dict[str, Any],
    owner_mission: str,
    context_mission: str,
) -> bool:
    """Validate a foreign Story playback path in one exact NpcProxy shell."""
    story_key = safe_key(connection.get("key"))
    proxy_ids = set(_string_list(connection.get("npcProxyIds")))
    segment_ids = set(_string_list(connection.get("segmentIdsGlobal")))
    candidate_quests = set(_string_list(connection.get("candidateQuestIds")))
    native_owners = connection.get("nativeEventOwners") or []
    tracking_rows = connection.get("npcProxyTrackingRows") or []
    registry_rows = connection.get("npcProxyRegistryRows") or []
    proxy_ex_rows = connection.get("npcProxyExRows") or []
    if (
        not story_key
        or safe_key(connection.get("relation"))
        != "npc_proxy_segment_levelscript_mission_context"
        or safe_key(connection.get("direction")) != "context"
        or safe_key(connection.get("phase")) != "runtime_playback"
        or safe_key(connection.get("confidence"))
        != "native_exact_npc_proxy_segment_shell"
        or safe_key(connection.get("evidenceTier")) != "derived_exact_shell"
        or safe_key(connection.get("storyOwnerMission")) != owner_mission
        or owner_mission == context_mission
        or safe_key(connection.get("questTriggerStatus"))
        != "same_authored_npc_proxy_segment_not_quest_playback"
        or safe_key(connection.get("executionSide")) != "client"
        or connection.get("serverExchange") is not False
        or not proxy_ids
        or not segment_ids
        or not candidate_quests
        or any(
            not quest_id.startswith(f"{context_mission}_q#")
            for quest_id in candidate_quests
        )
        or set(_string_list(connection.get("scriptIds"))) != segment_ids
        or not native_owners
        or not tracking_rows
        or not registry_rows
        or not proxy_ex_rows
        or not _string_list(connection.get("sourceFiles"))
    ):
        return False
    if any(
        not isinstance(row, dict)
        or safe_key(row.get("missionId")) != context_mission
        or safe_key(row.get("questId")) not in candidate_quests
        or not safe_key(row.get("sourceFile"))
        for row in tracking_rows
    ):
        return False
    if any(
        not isinstance(row, dict)
        or safe_key(row.get("proxyId")) not in proxy_ids
        or safe_key(row.get("dictionaryKey")) not in segment_ids
        or safe_key(row.get("segmentIdGlobal")) not in segment_ids
        or not safe_key(row.get("sourceFile"))
        for row in registry_rows
    ):
        return False
    if any(
        not isinstance(row, dict)
        or safe_key(row.get("proxyId")) not in proxy_ids
        or safe_key(row.get("missionId")) != context_mission
        or not isinstance(row.get("rowIndex"), int)
        or isinstance(row.get("rowIndex"), bool)
        or not safe_key(row.get("sourceFile"))
        for row in proxy_ex_rows
    ):
        return False
    for owner in native_owners:
        if (
            not isinstance(owner, dict)
            or safe_key(owner.get("status"))
            != "exact_serialized_control_path"
            or safe_key(owner.get("headerName"))
            != "ScriptEvent_OnLeaderEnterTriggerVolume"
        ):
            return False
        playback_found = False
        for step in owner.get("path") or []:
            if not isinstance(step, dict):
                continue
            record_class = safe_key(step.get("recordClass"))
            texts = _string_list(step.get("texts"))
            step_story_keys = (
                {text.rsplit("_", 1)[0] for text in texts}
                if record_class == "play_black"
                else set(texts)
            )
            if record_class.startswith("play_") and story_key in step_story_keys:
                playback_found = True
                break
        if not playback_found:
            return False
    return True


def build_gap_report(
    partial_report: dict[str, Any],
    mission_payloads: dict[str, dict[str, Any]],
    mission_bundle_presence: set[str],
    native_playback_index: dict[str, list[dict[str, Any]]] | None = None,
    action_story_occurrences: dict[str, list[dict[str, Any]]] | None = None,
    table_root: Path | None = None,
    offline_exhaustion_index: dict[str, dict[str, Any]] | None = None,
    offline_exhaustion_status: dict[str, Any] | None = None,
    quest_attachment_diagnostic_index:
        dict[str, dict[str, Any]] | None = None,
    quest_attachment_diagnostic_status: dict[str, Any] | None = None,
    story_trigger_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    non_mission_content = (
        combined_non_mission_content_keys(table_root)
        if table_root is not None
        else {}
    )
    cross_owner_connections: dict[str, list[dict[str, Any]]] = defaultdict(
        list
    )
    story_owners: dict[str, set[str]] = defaultdict(set)
    for partial_row in partial_report.get("missions") or []:
        if not isinstance(partial_row, dict):
            continue
        owner_mission = safe_key(partial_row.get("mission"))
        if not owner_mission:
            continue
        for node in partial_row.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            story_key = safe_key(node.get("key"))
            if story_key:
                story_owners[story_key].add(owner_mission)
    for context_mission, payload in mission_payloads.items():
        flow = _flow(payload)
        for connection in _flow_story_connections(flow):
            owner_mission = safe_key(connection.get("storyOwnerMission"))
            proxy_mission = safe_key(connection.get("npcProxyMissionId"))
            relation = safe_key(connection.get("relation"))
            if (
                not owner_mission
                or owner_mission == context_mission
                or owner_mission not in mission_payloads
            ):
                continue
            if relation == "npc_proxy_ex_mission_context":
                if proxy_mission != context_mission:
                    continue
            elif relation == "npc_proxy_segment_levelscript_mission_context":
                if not _exact_cross_owner_npc_proxy_segment_story_context(
                    connection,
                    owner_mission,
                    context_mission,
                ):
                    continue
            elif relation == "leveldata_levelscript_mission_context":
                if not _exact_cross_owner_leveldata_story_context(
                    connection,
                    owner_mission,
                    context_mission,
                ):
                    continue
            elif relation == "levelscript_mission_context":
                if not _exact_cross_owner_mission_condition_story_context(
                    connection,
                    owner_mission,
                    context_mission,
                ):
                    continue
            elif relation not in {
                "airwall_mission_state_radio_playback_context",
                "focus_mode_interact_locked_radio",
            }:
                continue
            cross_owner_connections[owner_mission].append({
                **connection,
                "contextMissionBundle": context_mission,
            })
        for quest in flow.get("quests") or []:
            if not isinstance(quest, dict):
                continue
            context_quest = safe_key(quest.get("id"))
            if not context_quest:
                continue
            for connection in quest.get("storyConnections") or []:
                if not isinstance(connection, dict):
                    continue
                story_key = safe_key(connection.get("key"))
                owners = story_owners.get(story_key) or set()
                if len(owners) != 1:
                    continue
                relation = safe_key(connection.get("relation"))
                exact_dialog_finish = (
                    relation == "objective_condition"
                    and safe_key(connection.get("conditionType"))
                    == "CheckTalkOptionFinish"
                    and safe_key(connection.get("direction"))
                    == "story_to_quest"
                    and safe_key(connection.get("confidence")) == "direct"
                )
                expected_action = {
                    "client_action_start": (1, "start"),
                    "client_action_succeed": (2, "succeed"),
                    "client_action_failed": (4, "failed"),
                }.get(relation)
                exact_client_action = (
                    expected_action is not None
                    and safe_key(connection.get("direction"))
                    == "quest_to_story"
                    and safe_key(connection.get("phase"))
                    == expected_action[1]
                    and safe_key(connection.get("confidence"))
                    == "native_typed_direct"
                    and connection.get("actionSlot") == expected_action[0]
                    and isinstance(connection.get("actionId"), int)
                    and not isinstance(connection.get("actionId"), bool)
                    and int(connection["actionId"]) >= 0
                    and bool(safe_key(connection.get("actionType")))
                    and bool(re.fullmatch(
                        r"MissionRuntimeAsset\.clientActionMapKey\[\d+\] -> "
                        r"actionMapRaw\.actionList\[\d+\]\._[A-Za-z]+Id",
                        safe_key(connection.get("source")),
                    ))
                )
                if not exact_dialog_finish and not exact_client_action:
                    continue
                owner_mission = next(iter(owners))
                if owner_mission not in mission_payloads:
                    continue
                cross_owner_connections[owner_mission].append({
                    **connection,
                    "contextMissionBundle": context_mission,
                    "contextQuestId": context_quest,
                    "sourceFile": (
                        "export_full/structured/Persistent/Data/Json/"
                        f"MissionRuntimeAsset/{context_mission}.json"
                    ),
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
            quest_attachment_diagnostic_index=(
                quest_attachment_diagnostic_index
            ),
            cross_owner_story_connections=cross_owner_connections.get(
                safe_key(row.get("mission"))
            ),
            story_trigger_manifest=story_trigger_manifest,
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
        "questAttachmentDiagnosticEvidence": (
            quest_attachment_diagnostic_status
            or {
                "status": "not_supplied",
                "graphEffect": "none",
            }
        ),
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
        (
            "Current-build quest-attachment diagnostic evidence: "
            f"`{safe_key((report.get('questAttachmentDiagnosticEvidence') or {}).get('status')) or 'unknown'}`. "
            "These rows close broad co-membership as non-owning only; they add "
            "no quest-to-Story or order edge."
        ),
        "",
    ]
    offline_failures = (
        report.get("offlineExhaustionEvidence") or {}
    ).get("validationFailures") or []
    if offline_failures:
        lines.extend([
            "## Offline-Exhaustion Validator Failures",
            "",
            "| Story | gate | source | expected | actual |",
            "| --- | --- | --- | --- | --- |",
        ])
        for failure in offline_failures:
            expected = failure.get("expected") or {}
            actual = failure.get("actual") or {}
            source_paths = failure.get("sourcePaths") or []
            lines.append(
                f"| `{md_escape(safe_key(failure.get('storyKey')) or '-')}` | "
                f"`{md_escape(safe_key(failure.get('gate')))}` | "
                f"`{md_escape('; '.join(map(str, source_paths)))}` | "
                f"`{md_escape(json.dumps(expected, ensure_ascii=False, sort_keys=True)[:500])}` | "
                f"`{md_escape(json.dumps(actual, ensure_ascii=False, sort_keys=True)[:500])}` |"
            )
        lines.append("")
    diagnostic_failures = (
        report.get("questAttachmentDiagnosticEvidence") or {}
    ).get("validationFailureDetails") or []
    if diagnostic_failures:
        lines.extend([
            "## Quest-Attachment Validator Failures",
            "",
            "| quest | gate | source | expected condition | actual condition |",
            "| --- | --- | --- | --- | --- |",
        ])
        for failure in diagnostic_failures:
            expected = failure.get("expected") or {}
            actual = failure.get("actual") or {}
            lines.append(
                f"| `{md_escape(safe_key(failure.get('questId')))}` | "
                f"`{md_escape(safe_key(failure.get('gate')))}` | "
                f"`{md_escape(safe_key(failure.get('sourcePath')))}` | "
                f"`{md_escape(safe_key(expected.get('conditionType')))}` | "
                f"`{md_escape(safe_key(actual.get('conditionType')))}` |"
            )
        lines.append("")
    lines.extend([
        "## Bucket Summary",
        "",
        "| bucket | missions | score | scenes | isolated (core: actionable / native-closed / runtime-config-closed / definition-closed / non-mission-closed / offline-exhausted) | weak-only (actionable / exact-closed) | cycles | actionable LS gaps | closed LS negatives | quest gaps (actionable / diagnostic-closed) | option gaps |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])
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
            f"{row.get('questIdsWithoutStrictStoryAttachment', 0)} / "
            f"{row.get('closedQuestAttachmentDiagnostics', 0)} | "
            f"{option_gaps} |"
        )

    lines.extend([
        "",
        "## Ranked Missions",
        "",
        "| rank | mission | bucket rank | score | scenes | isolated (core: actionable / native-closed / runtime-config-closed / definition-closed / non-mission-closed / offline-exhausted) | weak-only (actionable / exact-closed) | cycles | LS gaps | quest gaps (actionable / diagnostic-closed) | option gaps | primary frontier |",
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
            f"{metrics['questIdsWithoutStrictStoryAttachment']} / "
            f"{metrics['closedQuestAttachmentDiagnostics']} | {option_gaps} | "
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
            f"`{metrics['questIdsWithoutStrictStoryAttachment']}`; "
            f"closed non-owning diagnostic co-memberships: "
            f"`{metrics['closedQuestAttachmentDiagnostics']}`; untyped multi-scene "
            f"LevelScript contexts: `{metrics['untypedMultiSceneLevelscriptContexts']}`; "
            f"closed binary-negative contexts: "
            f"`{metrics['closedNonPlaybackLevelscriptContexts']}`; "
            f"actionable option gap groups: "
            f"`{metrics['actionableNoExplicitOptionRouteGroups'] + metrics['actionableExcludedOptionEvidenceGroups']}` "
            f"(`{metrics['deferredOfflineExhaustedOptionRouteGroups']}` "
            f"current-build offline-exhausted; "
            f"`{metrics['singleOptionNoExplicitRouteGroups']}` single-option "
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
    # Completion observers can live in a mission that owns no Story file and
    # therefore has no partial-order row (for example e9m9 consuming
    # dlg_e9m2_14). Load the remaining generated sidecars as context only so
    # exact cross-mission dependencies cannot disappear from gap
    # classification merely because the consumer has no narrative graph.
    for path in sorted(mission_dir.glob("*.json")):
        mission = path.stem
        if mission in mission_payloads:
            continue
        payload = read_json(path, {})
        if isinstance(payload, dict):
            mission_payloads[mission] = payload

    coverage_report = read_json(
        ROOT
        / "reports"
        / "story"
        / "build"
        / f"mission_pipeline_story_binding_coverage_{args.language}.json",
        {},
    )
    story_trigger_manifest = {}
    if (
        isinstance(coverage_report, dict)
        and coverage_report.get("schemaVersion")
        == STORY_BINDING_COVERAGE_SCHEMA_VERSION
        and safe_key(coverage_report.get("language")) == args.language
        and isinstance(coverage_report.get("storyTriggerManifest"), dict)
    ):
        story_trigger_manifest = coverage_report["storyTriggerManifest"]

    offline_exhaustion_index, offline_exhaustion_status = (
        build_offline_exhaustion_index(
            partial_report,
            args.table_root,
            game_assembly_path=args.game_assembly,
        )
    )
    (
        quest_attachment_diagnostic_index,
        quest_attachment_diagnostic_status,
    ) = build_quest_attachment_diagnostic_index(mission_payloads)
    report = build_gap_report(
        partial_report,
        mission_payloads,
        mission_bundle_presence,
        native_playback_index,
        action_story_occurrences,
        table_root=args.table_root,
        offline_exhaustion_index=offline_exhaustion_index,
        offline_exhaustion_status=offline_exhaustion_status,
        quest_attachment_diagnostic_index=(
            quest_attachment_diagnostic_index
        ),
        quest_attachment_diagnostic_status=(
            quest_attachment_diagnostic_status
        ),
        story_trigger_manifest=story_trigger_manifest,
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
    offline_status = report.get("offlineExhaustionEvidence") or {}
    offline_failures = offline_status.get("validationFailures") or []
    if offline_failures:
        first = offline_failures[0]
        print(
            "Offline-exhaustion validator failure: "
            f"story={safe_key(first.get('storyKey')) or '-'} "
            f"gate={safe_key(first.get('gate'))} "
            f"source={safe_key((first.get('sourcePaths') or [''])[0])}"
        )
    elif offline_status.get("sourceHashMismatches"):
        print(
            "Offline-exhaustion source hash mismatch: "
            + ", ".join(offline_status["sourceHashMismatches"])
        )
    diagnostic_status = report.get("questAttachmentDiagnosticEvidence") or {}
    diagnostic_failures = diagnostic_status.get(
        "validationFailureDetails"
    ) or []
    if diagnostic_failures:
        first = diagnostic_failures[0]
        print(
            "Quest-attachment validator failure: "
            f"quest={safe_key(first.get('questId'))} "
            f"gate={safe_key(first.get('gate'))} "
            f"source={safe_key(first.get('sourcePath'))}"
        )
    elif diagnostic_status.get("sourceHashMismatches"):
        print(
            "Quest-attachment source hash mismatch: "
            + ", ".join(diagnostic_status["sourceHashMismatches"])
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

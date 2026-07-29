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


SCHEMA = "sourceStoryGapQueue.v56"
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
    "current-build-offline-story-carrier-exhaustion-v35"
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
OFFLINE_EXHAUSTION_DIALOG_TEXT_TABLE_SHA256 = (
    "1C1BB59ACEA89212C9F2E34FE86457672FE5C8783FCD199F161D3F0DC9DEAD72"
)
OFFLINE_EXHAUSTION_READING_POPUP_TABLE_SHA256 = (
    "119BEFCA19E85FB11DF33D945FBA6374BB24E622F717CC50D7DA011BDB2A533C"
)
OFFLINE_EXHAUSTION_RICH_CONTENT_TABLE_SHA256 = (
    "1AB726FC15EA75A8212DB10D24630F75C565196A2EDCCCCCF5D57BC4D40B3301"
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
    "e1m1": frozenset({
        "cutscene_e1m1_3_1_test",
        "cutscene_e1m1_4",
        "cutscene_e1m1_6",
    }),
    "e1m3": frozenset({"cutscene_e1m3_1"}),
    "e2m5": frozenset({
        "cutscene_e2m5_2",
        "cutscene_e2m5_3",
    }),
    "e2m6": frozenset({
        "cutscene_e2m6_designer_AngelSurrounding",
        "cutscene_e2m6_designer_anchorperish_001",
    }),
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
    "cutscene_e1m1_3_1_test": 1,
    "cutscene_e1m1_4": 2,
    "cutscene_e1m3_1": 1,
    "cutscene_e2m6_designer_AngelSurrounding": 1,
    "cutscene_e2m6_designer_anchorperish_001": 1,
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
    "cutscene_e2m6_designer_anchorperish_001": {
        "timelineRegistryId": 265,
        "files": ((
            "cutscene_e2m6_designer_anchorperish_001_p47B0268A95477A92.json",
            "EB2D6F282B72DC47FAFAB970B64360A4FA8BF9B6B19D531E37980042604DE960",
            "cutscene_e2m6_designer_anchorperish_001",
        ),),
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
    "cutscene_e1m1_3_1_test": 1,
    "cutscene_e1m1_4": 2,
    "cutscene_e1m3_1": 1,
    "cutscene_e2m6_designer_AngelSurrounding": 1,
    "cutscene_e2m6_designer_anchorperish_001": 1,
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
}
OFFLINE_EXHAUSTION_POSITIVE_DIALOG_KEYS = frozenset({
    "dlg_e10m3_9",
    "dlg_e11m5_9",
    "dlg_e11m8_9",
})
OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS = {
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
OFFLINE_EXHAUSTION_E5M2_RADIOS = frozenset({"radio_e5m2_3"})
OFFLINE_EXHAUSTION_E5M1_RADIOS = frozenset({
    "radio_e5m1_7",
    "radio_e5m1_10d8",
    "radio_e5m1_12",
    "radio_e5m1_15",
})
OFFLINE_EXHAUSTION_E6M1_RADIOS = frozenset({
    "radio_e6m1_19",
})
OFFLINE_EXHAUSTION_E6M2_RADIOS = frozenset({
    "radio_e6m2_3",
    "radio_e6m2_7",
})
OFFLINE_EXHAUSTION_E7M4_RADIOS = frozenset({"radio_e7m4_3"})
OFFLINE_EXHAUSTION_E8M2_RADIOS = frozenset({
    "radio_e8m2_1",
    "radio_e8m2_9",
    "radio_e8m2_15",
    "radio_e8m2_16",
})
OFFLINE_EXHAUSTION_E10M1_RADIOS = frozenset({
    "radio_e10m1_6",
    "radio_e10m1_9",
})
OFFLINE_EXHAUSTION_RADIOS_BY_MISSION = {
    "e0m0": OFFLINE_EXHAUSTION_E0M0_RADIOS,
    "e1m2": OFFLINE_EXHAUSTION_E1M2_RADIOS,
    "e1m3": OFFLINE_EXHAUSTION_E1M3_RADIOS,
    "e2m2": OFFLINE_EXHAUSTION_E2M2_RADIOS,
    "e2m4": OFFLINE_EXHAUSTION_E2M4_RADIOS,
    "e2m5": OFFLINE_EXHAUSTION_E2M5_RADIOS,
    "e2m6": OFFLINE_EXHAUSTION_E2M6_RADIOS,
    "e2m7": OFFLINE_EXHAUSTION_E2M7_RADIOS,
    "e3m3": OFFLINE_EXHAUSTION_E3M3_RADIOS,
    "e5m1": OFFLINE_EXHAUSTION_E5M1_RADIOS,
    "e5m2": OFFLINE_EXHAUSTION_E5M2_RADIOS,
    "e6m1": OFFLINE_EXHAUSTION_E6M1_RADIOS,
    "e6m2": OFFLINE_EXHAUSTION_E6M2_RADIOS,
    "e6m3": OFFLINE_EXHAUSTION_E6M3_RADIOS,
    "e6m4": OFFLINE_EXHAUSTION_E6M4_RADIOS,
    "e7m2": OFFLINE_EXHAUSTION_E7M2_RADIOS,
    "e7m3": OFFLINE_EXHAUSTION_E7M3_RADIOS,
    "e7m4": OFFLINE_EXHAUSTION_E7M4_RADIOS,
    "e8m2": OFFLINE_EXHAUSTION_E8M2_RADIOS,
    "e9m2": OFFLINE_EXHAUSTION_E9M2_RADIOS,
    "e9m3": OFFLINE_EXHAUSTION_E9M3_RADIOS,
    "e10m1": OFFLINE_EXHAUSTION_E10M1_RADIOS,
    "e10m4": OFFLINE_EXHAUSTION_E10M4_RADIOS,
    "e11m1": OFFLINE_EXHAUSTION_E11M1_RADIOS,
    "e11m2": OFFLINE_EXHAUSTION_E11M2_RADIOS,
    "e11m3": OFFLINE_EXHAUSTION_E11M3_RADIOS,
    "e11m4": OFFLINE_EXHAUSTION_E11M4_RADIOS,
    "e11m5": OFFLINE_EXHAUSTION_E11M5_RADIOS,
    "e11m6": OFFLINE_EXHAUSTION_E11M6_RADIOS,
    "e11m8": OFFLINE_EXHAUSTION_E11M8_RADIOS,
}
OFFLINE_EXHAUSTION_MISSING_AUDIO_IDS = {
    "radio_e0m0_10": frozenset({
        "au_radio_e0m0_10_001",
        "au_radio_e0m0_10_002",
        "au_radio_e0m0_10_003",
    }),
    "radio_e0m0_21": frozenset({"au_radio_e0m0_21_001"}),
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
OFFLINE_EXHAUSTION_TEXT_DEFINITIONS = {
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
        "dialogTextTable": table_root / "DialogTextTable.json",
        "readingPopupTable": table_root / "ReadingPopUpTable.json",
        "richContentTable": table_root / "RichContentTable.json",
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
    cutscene_definition_root = (
        ROOT
        / "export_full"
        / "recovered"
        / "AnimeStudio-cli"
        / "StreamingAssets"
        / "json_by_type"
        / "TextAsset"
    )
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
        "readingPopupTable":
            OFFLINE_EXHAUSTION_READING_POPUP_TABLE_SHA256,
        "richContentTable":
            OFFLINE_EXHAUSTION_RICH_CONTENT_TABLE_SHA256,
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

    reading_popup_table = read_json(source_paths["readingPopupTable"], {})
    rich_content_table = read_json(source_paths["richContentTable"], {})
    text_definitions_valid = (
        isinstance(reading_popup_table, dict)
        and isinstance(rich_content_table, dict)
    )
    for story_key, definition in (
        OFFLINE_EXHAUSTION_TEXT_DEFINITIONS.items()
    ):
        if not text_definitions_valid:
            break
        popup_row_id = definition["readingPopupRowId"]
        popup = reading_popup_table.get(popup_row_id)
        rich = rich_content_table.get(story_key)
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
        if (
            not isinstance(popup, dict)
            or set(popup) != {
                "bgType",
                "contentId",
                "iconType",
                "id",
                "overrideRadioId",
                "title",
            }
            or popup.get("id") != popup_row_id
            or popup.get("contentId") != story_key
            or popup.get("bgType") != definition["bgType"]
            or popup.get("iconType") != definition["iconType"]
            or popup.get("overrideRadioId") != ""
            or popup.get("title") != {"id": 0, "text": ""}
            or not isinstance(rich, dict)
            or set(rich) != {"contentList", "title"}
            or rich.get("title")
            != {"id": definition["titleId"], "text": ""}
            or len(rich.get("contentList") or [])
            != len(expected_content_ids)
            or actual_content_ids != expected_content_ids
            or any(
                item != {"content": {"id": text_id, "text": ""}}
                for item, text_id in zip(
                    rich.get("contentList") or [],
                    expected_content_ids,
                )
            )
        ):
            text_definitions_valid = False
            break
    if not text_definitions_valid:
        status["status"] = "inactive_text_definition_validation_failed"
        return {}, status

    sns_dialog_table = read_json(source_paths["snsDialogTable"], {})
    sns_option_table = read_json(source_paths["snsOptionTable"], {})
    sns_validation_by_key: dict[str, dict[str, Any]] = {}
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
            or dialog.get("dialogType") != 1
            or dialog.get("noticeType") != 1
            or dialog.get("relatedMissionId") != ""
            or dialog.get("topicId") != ""
            or dialog.get("skipToFirstOption") is not False
            or not isinstance(content, dict)
            or set(content) != expected_content_keys
            or actual_prefixed_option_ids != expected_option_ids
        ):
            sns_definitions_valid = False
            break
        for content_id in expected_content_ids:
            node = content.get(str(content_id))
            expected_pre = (
                terminal_content_id if content_id == -1
                else 0 if content_id == 1
                else content_id - 1
            )
            expected_next = (
                0 if content_id == -1
                else -1 if content_id == terminal_content_id
                else 0 if content_id in option_ids_by_content_id
                else content_id + 1
            )
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
                break
        if not sns_definitions_valid:
            break
        sns_validation_by_key[story_key] = {
            "chatId": definition["chatId"],
            "contentIds": list(expected_content_ids),
            "optionIds": sorted(expected_option_ids, key=natural_key),
            "contentParamsByContentId": {
                str(content_id): list(content_params)
                for content_id, content_params
                in content_params_by_content_id.items()
            },
        }
    if not sns_definitions_valid:
        status["status"] = "inactive_sns_definition_validation_failed"
        return {}, status

    dialog_text_table = read_json(source_paths["dialogTextTable"], {})
    dialog_id_index = read_json(source_paths["dialogIdIndex"], {})
    timeline_line_orders = read_json(source_paths["timelineLineOrders"], {})
    npc_proxy_ex_table = read_json(
        source_paths["npcProxyExDataTable"],
        {},
    )
    dialog_validation_by_key: dict[str, dict[str, Any]] = {}
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
            "timelineContext": timeline_context,
            "npcProxyConsumer": npc_proxy_consumer_context,
            "npcProxyConsumers": npc_proxy_consumer_contexts,
        }
    if not dialog_definitions_valid:
        status["status"] = "inactive_dialog_definition_validation_failed"
        return {}, status

    text_only_dialog_validation_by_key: dict[str, dict[str, Any]] = {}
    text_only_dialog_definitions_valid = True
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
        if (
            actual_line_ids != expected_line_ids
            or len(line_audio_ids) != len(expected_line_ids)
            or not all(line_audio_ids)
            or line_audio_ids != expected_audio_ids
            or not set(expected_audio_variants) <= set(line_audio_ids)
            or any(
                not variants
                or any(
                    not variant.startswith(f"{audio_id}_")
                    for variant in variants
                )
                for audio_id, variants in expected_audio_variants.items()
            )
            or actual_missing_audio_ids != expected_missing_audio_ids
            or not (
                set(line_audio_ids) - expected_missing_audio_ids
            ) <= (
                audio_stems
                | set(expected_audio_variants)
            )
            or any(
                set(dialog_text_table[line_id])
                != OFFLINE_EXHAUSTION_DIALOG_ROW_FIELDS
                for line_id in expected_line_ids
            )
            or story_key in dialog_id_index
            or story_key in timeline_line_orders
            or any(cutscene_definition_root.glob(
                f"{story_key}_p*.json"
            ))
        ):
            text_only_dialog_definitions_valid = False
            break
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
        }
    if not text_only_dialog_definitions_valid:
        status["status"] = (
            "inactive_text_only_dialog_definition_validation_failed"
        )
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
    for story_key in sorted(all_dialog_keys, key=natural_key):
        validation = dialog_validation_by_key[story_key]
        index[story_key] = {
            "sceneKey": story_key,
            "missionId": dialog_mission_by_key[story_key],
            "recoveryStatus":
                "deferred_current_build_offline_surface_exhausted",
            "evidenceKind":
                (
                    "npc_proxy_dialog_consumer_without_mission_owner"
                    if validation["npcProxyConsumers"]
                    else
                    "registered_dialog_definition_without_recovered_activator"
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
            "sharedTimelineContext": validation["timelineContext"],
            "npcProxyConsumer": validation["npcProxyConsumer"],
            "npcProxyConsumers": validation["npcProxyConsumers"],
            "nativeMappingId": OFFLINE_EXHAUSTION_MAPPING_ID,
            "gameAssemblySha256":
                OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
            "consumerBoundary": (
                (
                    "the exact NpcProxyEx entry selects this registered "
                    "DialogTree as an NPC interaction dialog, but its authored "
                    "missionId is empty; no exact mission/quest owner or "
                    "activation timing is serialized"
                    if validation["npcProxyConsumers"]
                    else
                    "the exact DialogTree, MemoryPack DialogId registration, "
                    "DialogTextTable rows, and AudioDialog membership where "
                    "present establish a current runtime-loadable definition; "
                    "no exact MissionRuntime, LevelScript, NpcProxyEx, Lua, "
                    "object-index, or direct native playback caller exposes "
                    "its activator"
                )
            ),
            "orderBoundary": (
                "DialogId registration, DialogTree node order, line ids, "
                "shared Timeline context, and filename suffixes do not order "
                "the Story file relative to mission playback"
            ),
            "reopenWhen": (
                "installed binary, DialogId source/index, DialogTree, "
                "DialogTextTable, AudioDialog, NpcProxyExDataTable, object "
                "index, shared Timeline, or another typed producer/consumer "
                "registry changes"
            ),
            "graphEffect": "none",
        }
    for story_key in sorted(
        all_text_only_dialog_keys,
        key=natural_key,
    ):
        validation = text_only_dialog_validation_by_key[story_key]
        index[story_key] = {
            "sceneKey": story_key,
            "missionId": text_only_dialog_mission_by_key[story_key],
            "recoveryStatus":
                "deferred_current_build_offline_surface_exhausted",
            "evidenceKind":
                "dialog_text_table_only_without_registry_asset_or_consumer",
            "definitionTable": "DialogTextTable",
            "lineIds": validation["lineIds"],
            "audioIds": validation["audioIds"],
            "audioVariants": validation["audioVariants"],
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
            "dialogIdRegistrationStatus": "absent",
            "dialogTreeAssetStatus": "absent",
            "timelineStatus": "absent",
            "nativeMappingId": OFFLINE_EXHAUSTION_MAPPING_ID,
            "gameAssemblySha256":
                OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
            "consumerBoundary": (
                "the exact DialogTextTable line/audio group has no current "
                "DialogId registration, DialogTree asset, Timeline, "
                "AudioDialog membership, typed MissionRuntime or LevelScript "
                "consumer, Lua reference, or object-index carrier"
            ),
            "orderBoundary": (
                "line ids and fallback/manual display positions do not "
                "establish playback, option routing, or mission chronology"
            ),
            "reopenWhen": (
                "installed binary, DialogTextTable, AudioDialog, DialogId "
                "index, TextAsset inventory, Timeline index, object index, "
                "Lua corpus, or another typed producer/consumer changes"
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
                "sns_dialog_definition_without_recovered_activator",
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
            "nativeMappingId": OFFLINE_EXHAUSTION_MAPPING_ID,
            "gameAssemblySha256":
                OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
            "consumerBoundary": (
                "the exact SNSDialogTable content graph and "
                "SNSDialogOptionTable routes define this current Story file; "
                "relatedMissionId is empty, and no exact MissionRuntime, "
                "LevelScript/LevelData, Lua, object-index, or accepted native "
                "playback dispatch exposes its activator"
            ),
            "orderBoundary": (
                "the internal SNS content graph orders messages only; table "
                "order, dialog suffixes, and character chat membership do not "
                "place the Story file in mission chronology"
            ),
            "reopenWhen": (
                "installed binary, SNSDialogTable, SNSDialogOptionTable, "
                "object index, Lua corpus, or another typed "
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
                "RichContentTable",
            ],
            "readingPopupRowId": definition["readingPopupRowId"],
            "contentTextIds": list(definition["contentTextIds"]),
            "nativeMappingId": OFFLINE_EXHAUSTION_MAPPING_ID,
            "gameAssemblySha256":
                OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
            "consumerBoundary": (
                "the exact ReadingPopUpTable carrier and RichContentTable "
                "payload define this current Story file; no exact "
                "MissionRuntime, LevelScript/LevelData interactive, Lua, "
                "object-index, or direct native caller exposes its activator"
            ),
            "orderBoundary": (
                "popup table order, content-node order, text ids, and filename "
                "suffixes do not place the Story file in mission chronology"
            ),
            "reopenWhen": (
                "installed binary, ReadingPopUpTable, RichContentTable, "
                "object index, Lua corpus, or another typed producer/consumer "
                "registry changes"
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
            "consumerBoundary": (
                "the exact TextTable group has no Timeline registry entry, "
                "indexed cutscene root, reverse PPtr relation, "
                "PlayableDirector host, structured action, Lua consumer, or "
                "direct native cutscene caller in the audited build"
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
                "structured action, Lua consumer, or direct native caller "
                "in the audited build"
            ),
            "reopenWhen": (
                "installed binary, TextTable, Timeline or DialogId registry, "
                "TextAsset/object index, Lua corpus, or another typed "
                "producer/consumer registry changes"
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
        if (
            scene_key not in isolated_scene_keys
            or safe_key(connection.get("storyOwnerMission")) != owner_mission
            or connection.get("storyBinding") is not True
            or connection.get("ownership") is not False
            or safe_key(connection.get("direction")) != "context"
        ):
            continue
        relation = safe_key(connection.get("relation"))
        if relation == "radio_trigger_zone_mission_state_playback_context":
            if (
                safe_key(connection.get("phase"))
                != "mission_state_trigger_zone"
                or safe_key(connection.get("confidence"))
                != "native_exact_serialized_co_carrier"
                or safe_key(connection.get("evidenceTier")) != "direct"
                or safe_key(connection.get("missionStateId"))
                != owner_mission
                or set(_string_list(
                    connection.get("missionStateGateRoles")
                ))
                != {"hideBeforeMissionId", "hideCompleteMissionId"}
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
            elif relation == "leveldata_levelscript_mission_context":
                if not _exact_cross_owner_leveldata_story_context(
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

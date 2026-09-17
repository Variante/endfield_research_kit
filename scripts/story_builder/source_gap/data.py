"""Build-locked declarations used by source Story gap evidence.

This module intentionally contains data rather than recovery algorithms. Its
mapping ids and source hashes make the client-build boundary reviewable.
"""

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
NPC_PROXY_TRACKING_INFO_TYPE = (
    "Beyond.Gameplay.NpcProxyTrackingInfo, Gameplay.Beyond"
)
NPC_PROXY_TRACKING_INFO_FIELDS = frozenset({
    "$type",
    "guidingArea",
    "npcProxyId",
    "sceneId",
    "useFilterCondition",
})
DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID = (
    "dialog-tree-narrative-mask-connection-native-v1"
)
DIALOG_TREE_TRUNK_GROUP_MAPPING_ID = (
    "gameassembly-2026-07-11-dialog-tree-trunk-playback-v1"
)
DIALOG_TREE_TRUNK_NATIVE_CONSUMERS = (
    {
        "method": "DTTrunkNodeData.get_trunkId",
        "token": "0x06003977",
        "address": "0x187292f78",
    },
    {
        "method": "DialogTreeTrunkNode.DoExecute",
        "token": "0x06003bb4",
        "address": "0x1872a74b4",
    },
    {
        "method": "DialogTreeTrunkNode._DoPlayTrunk",
        "token": "0x06003bb6",
        "address": "0x1872a80b8",
    },
    {
        "method": "DialogManager.PlayTrunkNode",
        "token": "0x0600f785",
        "address": "0x186e16cc8",
    },
)
OFFLINE_EXHAUSTION_MAPPING_ID = (
    "current-build-offline-story-carrier-exhaustion-v93"
)
OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256 = (
    "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
)
OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS = {
    "dlg_gm01m13_2": "dlg_gm01m13_2",
    "dlg_gm01m13_3": "dlg_gm01m13_3",
    "dlg_gm01m13_5": "dlg_gm01m13_5",
    "text_gm01m13_1": "text_gm01m13_1",
    "misc_dlg_gm01m3_1d5": "dlg_gm01m3_1d5",
    "radio_gm01m3_3d2": "radio_gm01m3_3d2",
    "radio_gm01m3_3d8": "radio_gm01m3_3d8",
    "sns_gm01m3_1": "sns_gm01m3_1",
    "dlg_gm01m2_1": "dlg_gm01m2_1",
    "dlg_gm01m2_2": "dlg_gm01m2_2",
    "dlg_gm01m2_3": "dlg_gm01m2_3",
    "dlg_gm01m2_5": "dlg_gm01m2_5",
    "radio_gm01m17_4": "radio_gm01m17_4",
    "radio_gm01m17_5": "radio_gm01m17_5",
    "radio_gm01m17_9": "radio_gm01m17_9",
    "radio_gm02m14_1": "radio_gm02m14_1",
    "radio_gm02m14_12": "radio_gm02m14_12",
    "radio_gm02m13_3": "radio_gm02m13_3",
    "radio_gm02m13_4": "radio_gm02m13_4",
    "radio_gm02m13_5": "radio_gm02m13_5",
    "radio_gm02m17_2": "radio_gm02m17_2",
    "radio_gm02m17_4": "radio_gm02m17_4",
    "radio_gm02m15_9": "radio_gm02m15_9",
    "radio_gm02m15_12": "radio_gm02m15_12",
    "radio_gm02m21_4": "radio_gm02m21_4",
    "radio_gm02m21_7": "radio_gm02m21_7",
    "dlg_gm01m4_7": "dlg_gm01m4_7",
    "misc_dlg_gm01m4_3d5": "dlg_gm01m4_3d5",
    "radio_gm01m4_1": "radio_gm01m4_1",
    "dlg_gm01m15_7": "dlg_gm01m15_7",
    "text_gm01m15_1": "text_gm01m15_1",
    "text_gm01m15_8": "text_gm01m15_8",
    "text_gm01m17_1": "text_gm01m17_1",
    "dlg_gm01m22_6": "dlg_gm01m22_6",
    "dlg_gm01m22_7": "dlg_gm01m22_7",
    "dlg_gm01m22_8": "dlg_gm01m22_8",
    "dlg_gm02m8_2": "dlg_gm02m8_2",
    "dlg_gm02m8_3": "dlg_gm02m8_3",
    "dlg_gm02m8_4": "dlg_gm02m8_4",
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
    "dlg_gm01m27_1": "dlg_gm01m27_1",
    "dlg_gm01m27_2": "dlg_gm01m27_2",
    "dlg_gm01m27_3": "dlg_gm01m27_3",
    "radio_gm01m27_1": "radio_gm01m27_1",
    "radio_gm01m27_2": "radio_gm01m27_2",
    "radio_gm01m27_3": "radio_gm01m27_3",
    "dlg_gm01m5_1": "dlg_gm01m5_1",
    "dlg_gm01m5_2": "dlg_gm01m5_2",
    "dlg_gm01m5_3": "dlg_gm01m5_3",
    "dlg_gm01m5_4": "dlg_gm01m5_4",
    "radio_gm01m5_1": "radio_gm01m5_1",
    "radio_gm01m5_2": "radio_gm01m5_2",
    "radio_gm01m5_3": "radio_gm01m5_3",
    "radio_gm01m5_4": "radio_gm01m5_4",
    "dlg_gm02m1_1": "dlg_gm02m1_1",
    "dlg_gm02m1_2": "dlg_gm02m1_2",
    "misc_dlg_gm02m1_1d5": "dlg_gm02m1_1d5",
    "radio_gm02m1_1": "radio_gm02m1_1",
    "radio_gm02m1_2": "radio_gm02m1_2",
    "radio_gm02m1_6": "radio_gm02m1_6",
    "radio_gm02m1_7": "radio_gm02m1_7",
    "radio_gm02m1_8": "radio_gm02m1_8",
    "radio_gm02m20_7": "radio_gm02m20_7",
    "radio_gm02m20_8": "radio_gm02m20_8",
    "radio_gm02m20_10": "radio_gm02m20_10",
    "radio_gm02m20_11": "radio_gm02m20_11",
    "radio_gm02m20_13": "radio_gm02m20_13",
    "dlg_gm02m23_3": "dlg_gm02m23_3",
    "dlg_gm02m23_10": "dlg_gm02m23_10",
    "radio_gm02m23_2": "radio_gm02m23_2",
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
OFFLINE_EXHAUSTION_MISSION_RELATED_ORIGINAL_DATA = {
    "gm01m27": {
        "relation": "same_nominal_mission_prts_terminal_bundle",
        "groupId": "term_map01_lv001_gm01m27",
        "levelId": "map01_lv001",
        "entries": (
            {
                "order": 1,
                "contentId": "text_gm01m27_1",
                "prtsId": "nar_gm01m27_1",
                "uniqId": "term_map01_lv001_gm01m27_1",
                "numericId": 176,
                "nameId": 2291375224637431152,
            },
            {
                "order": 2,
                "contentId": "text_gm01m27_2",
                "prtsId": "nar_gm01m27_2",
                "uniqId": "term_map01_lv001_gm01m27_2",
                "numericId": 175,
                "nameId": -1279490884708468702,
            },
        ),
        "missionTextRows": {
            "gm01m27_desc_008": -4721954571166861173,
            "gm01m27_desc_010": 4234351872060234760,
            "gm01m27_desc_026": -5260360960064451117,
            "gm01m27_name": -1774444844579267245,
            "objective_gm01m27_1_001": -1424917977080405441,
            "objective_gm01m27_2_001": -6425752074915612424,
            "objective_gm01m27_2_002": -6913698330769929737,
            "objective_gm01m27_2_003": 5217138335650443298,
            "objective_gm01m27_4_001": -1996591101611484771,
            "objective_gm01m27_5_001": 3054271297337201381,
            "objective_gm01m27_6_001": 3502640477416576227,
        },
        "sourceKeys": (
            "prtsReadingTable",
            "numIdStrTable",
            "strIdNumTable",
            "textTable",
        ),
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
    "gm01m15": {
        "sourceFile": (
            "export_full/structured/Persistent/Data/Json/"
            "MissionRuntimeAsset/gm01m15.json"
        ),
        "sourceSha256":
            "0397C4DAD94F167EE1EE571280C7723F8D17D0905FA5CCA71AA101B26B0D5622",
        "mainPathQuestIds": tuple(
            f"gm01m15_q#{number}"
            for number in (2, 3, 4, 6, 7, 8, 14, 5, 10, 11, 12)
        ),
        "prevQuestIdsByQuest": {
            "gm01m15_q#2": (),
            "gm01m15_q#3": ("gm01m15_q#2",),
            "gm01m15_q#4": ("gm01m15_q#3",),
            "gm01m15_q#13": ("gm01m15_q#3",),
            "gm01m15_q#6": ("gm01m15_q#4", "gm01m15_q#13"),
            "gm01m15_q#7": ("gm01m15_q#6",),
            "gm01m15_q#8": ("gm01m15_q#7",),
            "gm01m15_q#14": ("gm01m15_q#8",),
            "gm01m15_q#5": ("gm01m15_q#14",),
            "gm01m15_q#10": ("gm01m15_q#5",),
            "gm01m15_q#11": ("gm01m15_q#10",),
            "gm01m15_q#12": ("gm01m15_q#11",),
        },
        "failedConditionsByQuest": {
            f"gm01m15_q#{number}": None
            for number in (2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14)
        },
    },
    "gm01m4": {
        "sourceFile": (
            "export_full/structured/Persistent/Data/Json/"
            "MissionRuntimeAsset/gm01m4.json"
        ),
        "sourceSha256":
            "43F95A2A63978A06F1CDCC73EC073154A88A7A3E1DB9C6EA2F4195862390868D",
        "mainPathQuestIds": ("gm01m4_q#1", "gm01m4_q#2"),
        "prevQuestIdsByQuest": {
            "gm01m4_q#1": (),
            "gm01m4_q#2": ("gm01m4_q#1",),
        },
        "failedConditionsByQuest": {
            "gm01m4_q#1": None,
            "gm01m4_q#2": None,
        },
    },
    "gm02m13": {
        "sourceFile": (
            "export_full/structured/Persistent/Data/Json/"
            "MissionRuntimeAsset/gm02m13.json"
        ),
        "sourceSha256":
            "5F1BFCD6CB10E46B4A613E59CD20E28501B1E283BFA15EAC8B0708E14D914A70",
        "mainPathQuestIds": tuple(
            f"gm02m13_q#{number}" for number in (5, 6, 7, 15)
        ),
        "prevQuestIdsByQuest": {
            f"gm02m13_q#{quest}": tuple(
                f"gm02m13_q#{previous}" for previous in predecessors
            )
            for quest, predecessors in {
                5: (), 6: (5,), 7: (6,), 8: (5,), 9: (5,),
                10: (6,), 11: (8,), 12: (8,), 13: (9,), 14: (9,),
                15: (7, 10, 12, 11, 13, 14),
            }.items()
        },
        "failedConditionsByQuest": {
            **{
                f"gm02m13_q#{number}": None
                for number in (5, 7, 10, 11, 12, 13, 14, 15)
            },
            **{
                f"gm02m13_q#{quest}": {
                    "$type": (
                        "Beyond.Gameplay.CombineCondition, Gameplay.Beyond"
                    ),
                    "uniqueId": unique_id,
                    "useCurrentScope": False,
                    "scopeMask": 1,
                    "useGraphScope": True,
                    "conditionEvalString": "{0}or{1}",
                    "subConditions": [
                        {
                            "$type": (
                                "Beyond.Gameplay.CheckTalkOptionFinish, "
                                "Gameplay.Beyond"
                            ),
                            "uniqueId": leaf_id,
                            "useCurrentScope": False,
                            "scopeMask": 1,
                            "useGraphScope": True,
                            "_dialogId": {"constValue": dialog_id},
                            "_finishId": {"constValue": 0},
                        }
                        for leaf_id, dialog_id in leaves
                    ],
                }
                for quest, unique_id, leaves in (
                    (6, "c5de1b18", (
                        ("d0f334db", "dlg_gm02m13_3"),
                        ("218fc83e", "dlg_gm02m13_4"),
                    )),
                    (8, "3707d033", (
                        ("e5a9d6b4", "dlg_gm02m13_2"),
                        ("3f7c0016", "dlg_gm02m13_4"),
                    )),
                    (9, "b37321d6", (
                        ("7017c5b8", "dlg_gm02m13_3"),
                        ("dbf73271", "dlg_gm02m13_2"),
                    )),
                )
            },
        },
    },
    "gm02m8": {
        "sourceFile": (
            "export_full/structured/Persistent/Data/Json/"
            "MissionRuntimeAsset/gm02m8.json"
        ),
        "sourceSha256":
            "D927D6757223E97D50A88202804CCEAC6D1B48DD3BF4D76060992DDFBFE2D3DE",
        "mainPathQuestIds": tuple(
            f"gm02m8_q#{number}" for number in (1, 2, 3)
        ),
        "prevQuestIdsByQuest": {
            "gm02m8_q#1": (),
            "gm02m8_q#2": ("gm02m8_q#1",),
            "gm02m8_q#3": ("gm02m8_q#2",),
        },
    },
    "gm02m14": {
        "sourceFile": (
            "export_full/structured/Persistent/Data/Json/"
            "MissionRuntimeAsset/gm02m14.json"
        ),
        "sourceSha256":
            "1427E0281C167DC04DE4AC9776CBEBB78C6E31158601EE95E089DDAB4312DA7C",
        "mainPathQuestIds": tuple(
            f"gm02m14_q#{number}"
            for number in (1, 2, 3, 5, 6, 4, 7, 8, 9, 10, 11, 12)
        ),
        "prevQuestIdsByQuest": {
            f"gm02m14_q#{quest}": tuple(
                f"gm02m14_q#{previous}" for previous in predecessors
            )
            for quest, predecessors in {
                1: (), 2: (1,), 3: (2,), 5: (3,), 6: (5,), 4: (6,),
                7: (4,), 8: (7,), 9: (8,), 10: (9,), 11: (10,),
                12: (11,),
            }.items()
        },
    },
    "gm02m15": {
        "sourceFile": (
            "export_full/structured/Persistent/Data/Json/"
            "MissionRuntimeAsset/gm02m15.json"
        ),
        "sourceSha256":
            "026F401C4F0D6DE15235812563B91CD06798509963B8234488AA5D66273891E1",
        "mainPathQuestIds": tuple(
            f"gm02m15_q#{number}" for number in range(1, 9)
        ),
        "prevQuestIdsByQuest": {
            f"gm02m15_q#{quest}": (
                () if quest == 1 else (f"gm02m15_q#{quest - 1}",)
            )
            for quest in range(1, 9)
        },
        "objectiveConjunctionsByQuest": {
            "gm02m15_q#5": ({
                "objectiveIndex": 1,
                "conditionType": "Beyond.Gameplay.CombineCondition",
                "conditionEvalString": "{0} and {1} and {2}",
                "subConditions": tuple({
                    "conditionIndex": index,
                    "conditionType": (
                        "Beyond.Gameplay.CheckLevelScriptPropertyBool"
                    ),
                    "mapId": "map02_lv006",
                    "scriptId": 25000120003,
                    "key": key,
                    "value": True,
                    "comparer": 0,
                    "sourceFile": (
                        "export_full/structured/StreamingAssets/Data/Json/"
                        "LevelScriptData/map02_lv006/25000120003.json"
                    ),
                } for index, key in enumerate(
                    ("jianbei1", "jianbei2", "jianbei3")
                )),
            },),
        },
    },
    "gm02m21": {
        "sourceFile": (
            "export_full/structured/Persistent/Data/Json/"
            "MissionRuntimeAsset/gm02m21.json"
        ),
        "sourceSha256":
            "FBEE030B16BC77EC465523E7E0CCEF8CC77B50328C645C3694DEA9125730599F",
        "mainPathQuestIds": tuple(
            f"gm02m21_q#{number}" for number in range(1, 6)
        ),
        "prevQuestIdsByQuest": {
            "gm02m21_q#1": (),
            "gm02m21_q#2": ("gm02m21_q#1",),
            "gm02m21_q#3": ("gm02m21_q#2",),
            "gm02m21_q#4": ("gm02m21_q#3",),
            "gm02m21_q#5": ("gm02m21_q#4",),
            "gm02m21_q#6": ("gm02m21_q#1",),
        },
        "failedConditionsByQuest": {
            **{f"gm02m21_q#{number}": None for number in range(1, 6)},
            "gm02m21_q#6": {
                "$type": "Beyond.Gameplay.CheckQuestState, Gameplay.Beyond",
                "uniqueId": "7ed8c99f",
                "useCurrentScope": False,
                "scopeMask": 1,
                "useGraphScope": True,
                "_questId": {"constValue": "gm02m21_q#1"},
                "_comparer": {"constValue": 1},
                "_targetQuestState": {"constValue": 3},
            },
        },
        "questStateDependenciesByQuest": {
            "gm02m21_q#6": ({
                "objectiveIndex": 1,
                "targetQuestId": "gm02m21_q#2",
                "comparer": 0,
                "targetQuestState": 3,
                "scopeMask": 1,
                "useGraphScope": True,
            },),
        },
        "objectiveConjunctionsByQuest": {
            "gm02m21_q#2": ({
                "objectiveIndex": 1,
                "conditionType": "Beyond.Gameplay.CombineCondition",
                "conditionEvalString": "{0}and{1}and{2}and{3}and{4}",
                "subConditions": tuple({
                    "conditionIndex": index,
                    "conditionType": (
                        "Beyond.Gameplay.CheckLevelScriptStage"
                    ),
                    "mapId": "map02_lv007",
                    "scriptId": 10200190002,
                    "stageValue": stage,
                    "compareOperator": 3,
                    "sourceFile": (
                        "export_full/structured/StreamingAssets/Data/Json/"
                        "LevelScriptData/map02_lv007/10200190002.json"
                    ),
                } for index, stage in enumerate((1, 2, 3, 4, 7))),
            },),
        },
        "levelScriptPlaybackInventories": ({
            "sourceFile": (
                "export_full/structured/StreamingAssets/Data/Json/"
                "LevelScriptData/map02_lv007/10200190002.json"
            ),
            "sourceSha256": (
                "444389EA6AC01B7FBF9823A50FEDB8405711675520848A3C19FD9050DCE732A8"
            ),
            "playbackRecords": tuple({
                "action": "PlayRadio",
                "storyKey": f"radio_gm02m21_{number}",
                "independentActionRoot": True,
            } for number in (1, 2, 3, 5, 8)),
            "absentStoryKeys": (
                "radio_gm02m21_4",
                "radio_gm02m21_7",
            ),
        },),
    },
    "gm02m17": {
        "sourceFile": (
            "export_full/structured/Persistent/Data/Json/"
            "MissionRuntimeAsset/gm02m17.json"
        ),
        "sourceSha256":
            "1AA34C807318E0AB8226F69F5BED97D3C9B84563D8405F25F2BC07E0D8C9574D",
        "mainPathQuestIds": ("gm02m17_q#1",),
        "prevQuestIdsByQuest": {
            "gm02m17_q#1": (),
            "gm02m17_q#3": ("gm02m17_q#1",),
            "gm02m17_q#5": ("gm02m17_q#3",),
            "gm02m17_q#4": ("gm02m17_q#5", "gm02m17_q#1"),
            "gm02m17_q#6": ("gm02m17_q#4",),
        },
        "failedConditionsByQuest": {
            f"gm02m17_q#{number}": None for number in (1, 3, 4, 5, 6)
        },
    },
    "gm01m13": {
        "sourceFile": (
            "export_full/structured/Persistent/Data/Json/"
            "MissionRuntimeAsset/gm01m13.json"
        ),
        "sourceSha256":
            "383E76E5CA4C9AA632CAE2132D76182E644F992E092CBF43BB5D5EEE1844ED30",
        "mainPathQuestIds": tuple(
            f"gm01m13_q#{number}"
            for number in (1, 2, 3, 4, 8, 9, 5, 7, 11)
        ),
        "prevQuestIdsByQuest": {
            f"gm01m13_q#{quest}": tuple(
                f"gm01m13_q#{previous}" for previous in predecessors
            )
            for quest, predecessors in {
                1: (), 2: (1,), 3: (2,), 4: (3, 12), 5: (9,),
                7: (5,), 8: (4,), 9: (8,), 11: (7,), 12: (2,),
            }.items()
        },
    },
    "gm01m17": {
        "sourceFile": (
            "export_full/structured/Persistent/Data/Json/"
            "MissionRuntimeAsset/gm01m17.json"
        ),
        "sourceSha256":
            "B056CF7FE5496B477208487DA74B510828CE122E685ED32D67070B7AD84A7E82",
        "mainPathQuestIds": tuple(
            f"gm01m17_q#{number}"
            for number in (1, 2, 13, 14, 16, 18)
        ),
        "prevQuestIdsByQuest": {
            f"gm01m17_q#{quest}": tuple(
                f"gm01m17_q#{previous}" for previous in predecessors
            )
            for quest, predecessors in {
                1: (), 11: (), 12: (), 13: (2,), 14: (13,),
                15: (13,), 16: (14,), 17: (15,), 18: (16,),
                19: (17,), "1d1": (), 2: (1,), 20: (4,), 21: (6,),
                22: (2,), 3: (2,), 4: (3,), 5: (4,), 6: (),
                7: (), 8: (), 9: (),
            }.items()
        },
        "failedConditionsByQuest": {
            **{
                f"gm01m17_q#{number}": None
                for number in (
                    1, 11, 12, 14, 15, 16, 17, 18, 19, "1d1", 2,
                    20, 21, 22, 3, 4, 5, 6, 7, 8, 9,
                )
            },
            "gm01m17_q#13": {
                "$type": "Beyond.Gameplay.CheckQuestState, Gameplay.Beyond",
                "uniqueId": "ea935d5b",
                "useCurrentScope": False,
                "scopeMask": 1,
                "useGraphScope": True,
                "_questId": {"constValue": "gm01m17_q#3"},
                "_comparer": {"constValue": 0},
                "_targetQuestState": {"constValue": 3},
            },
        },
        "questStateDependenciesByQuest": {
            "gm01m17_q#3": tuple({
                "objectiveIndex": 1,
                "conditionIndexPath": (condition_index, 1),
                "targetQuestId": "gm01m17_q#13",
                "comparer": 0,
                "targetQuestState": 3,
                "scopeMask": 1,
                "useGraphScope": True,
            } for condition_index in range(3)),
            "gm01m17_q#4": ({
                "objectiveIndex": 1,
                "conditionIndexPath": (1,),
                "targetQuestId": "gm01m17_q#13",
                "comparer": 0,
                "targetQuestState": 3,
                "scopeMask": 1,
                "useGraphScope": True,
            },),
        },
    },
    "gm02m20": {
        "sourceFile": (
            "export_full/structured/Persistent/Data/Json/"
            "MissionRuntimeAsset/gm02m20.json"
        ),
        "sourceSha256":
            "39A69825551FB99F98FDBA0F9B72F771CA2BAA5E091174D363270329675785C7",
        "mainPathQuestIds": tuple(
            f"gm02m20_q#{number}"
            for number in (1, 2, 10, 11, 3, 6, 4, 7, 5, 8)
        ),
        "prevQuestIdsByQuest": {
            f"gm02m20_q#{quest}": tuple(
                f"gm02m20_q#{previous}" for previous in predecessors
            )
            for quest, predecessors in {
                1: (), 2: (1,), 10: (2,), 11: (10,), 3: (11,),
                6: (3,), 4: (6,), 7: (4,), 5: (7,), 8: (5,),
                9: (),
            }.items()
        },
        "questStateDependenciesByQuest": {
            "gm02m20_q#9": ({
                "objectiveIndex": 1,
                "targetQuestId": "gm02m20_q#1",
                "comparer": 0,
                "targetQuestState": 3,
                "scopeMask": 1,
                "useGraphScope": True,
            },),
        },
    },
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
    "gm02m23": {
        "sourceFile": (
            "export_full/structured/Persistent/Data/Json/"
            "MissionRuntimeAsset/gm02m23.json"
        ),
        "sourceSha256":
            "09987B7764C23CA0AA2A1BD4302BAA549E7833F9BE0498283E07814D74F3F5AB",
        "mainPathQuestIds": tuple(
            f"gm02m23_q#{number}"
            for number in (1, 2, 11, 3, 7, 8, 13, 10, 6)
        ),
        "prevQuestIdsByQuest": {
            f"gm02m23_q#{quest}": tuple(
                f"gm02m23_q#{previous}" for previous in predecessors
            )
            for quest, predecessors in {
                1: (), 2: (1,), 11: (2,), 3: (11,), 7: (3,),
                8: (7,), 13: (8,), 10: (13,), 6: (10,), 9: (2,),
            }.items()
        },
        "failedConditionsByQuest": {
            **{
                f"gm02m23_q#{number}": None
                for number in (1, 2, 11, 3, 7, 8, 13, 10, 6)
            },
            "gm02m23_q#9": {
                "$type": "Beyond.Gameplay.CheckQuestState, Gameplay.Beyond",
                "uniqueId": "d234408a",
                "useCurrentScope": False,
                "scopeMask": 1,
                "useGraphScope": True,
                "_questId": {"constValue": "gm02m23_q#11"},
                "_comparer": {"constValue": 0},
                "_targetQuestState": {"constValue": 3},
            },
        },
    },
}
OFFLINE_EXHAUSTION_LEVELDATA_DIALOG_BRANCH_CONTEXTS = {
    "gm01m2": {
        "levelId": "map01_lv001",
        "scriptId": "2100210004",
        "levelDataFile": (
            "export_full/structured/StreamingAssets/Data/Json/LevelData/"
            "map01_lv001/map01_lv001_lv_data_sub_gm01m2.json"
        ),
        "levelDataSha256":
            "E54CF09A81D8A54C4677DF4CA2C727711F9B7E1174551997D4F5814414561378",
        "levelScriptFile": (
            "export_full/structured/StreamingAssets/Data/Json/LevelScriptData/"
            "map01_lv001/2100210004.json"
        ),
        "levelScriptSha256":
            "1A57F97CE96D2674C63B38410A05213F2816F911C2F36AD5BD745E2C45A68155",
        "dictionaryEntryCount": 3,
        "dictionaryScriptIds": (
            "2100210004", "2100210017", "2100210019",
        ),
        "propertyCount": 38,
        "propertyDialogs": {
            "start_dialog": "dlg_gm01m2_1",
            "succeed_dialog": "dlg_gm01m2_2",
            "failed_dialog": "dlg_gm01m2_3",
        },
        "startDialogListener": {
            "headerLocalId": 87,
            "eventName": "LevelEvent_OnDialogEnter",
            "nextLocalId": 88,
            "propertyPath": "start_dialog",
        },
        "resultSwitch": {
            "eventHeaderLocalId": 188,
            "eventName": "ScriptEvent_OnCustomEvent",
            "eventKey": "#72a43b08",
            "switchLocalId": 189,
            "getterLocalId": 240,
            "getterPath": "result",
            "switchCases": (
                (0, -1), (1, 190), (2, 191), (3, 21),
                (4, 192), (5, 193), (8, 217), (9, 194),
            ),
            "cases": ({
                "value": 8,
                "entryLocalId": 217,
                "actionLocalId": 148,
                "getterLocalId": 147,
                "propertyPath": "succeed_dialog",
                "pathLocalIds": (189, 217, 218, 220, 221, 222, 235, 236, 148),
            }, {
                "value": 9,
                "entryLocalId": 194,
                "actionLocalId": 151,
                "getterLocalId": 150,
                "propertyPath": "failed_dialog",
                "pathLocalIds": (189, 194, 197, 198, 199, 212, 213, 151),
            }),
        },
    },
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
        "propertyCount": 37,
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
        "propertyCount": 37,
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
        "propertyCount": 37,
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
OFFLINE_EXHAUSTION_EMPTY_LEVELSCRIPT_CONTEXTS = {
    "gm01m5": {
        "levelId": "map01_lv001",
        "scriptId": "2100100004",
        "levelDataFile": (
            "export_full/structured/StreamingAssets/Data/Json/LevelData/"
            "map01_lv001/map01_lv001_lv_data_sub_gm01m5.json"
        ),
        "levelDataSha256":
            "3F32678F67E08B81AFCBFA05F2283EB098DE3E0E3C091E08D69AA502F9B0C6EB",
        "levelScriptFile": (
            "export_full/structured/StreamingAssets/Data/Json/LevelScriptData/"
            "map01_lv001/2100100004.json"
        ),
        "levelScriptSha256":
            "561A82A611951483CD9DEEDAFDB7BDADE58DBCE163A3B3E393370BD4AF460112",
        "dataPathHash": "15306503476277701362",
        "levelScriptType": 0,
        "maxStage": 1,
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
OFFLINE_EXHAUSTION_STR_ID_NUM_TABLE_SHA256 = (
    "9F7EAD0C728058952575EF0C085321A4E21834A336F661B061758EE827DAFBA7"
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
OFFLINE_EXHAUSTION_DIALOG_SUMMARY_MAP_TABLE_SHA256 = (
    "86A9DF70D9AB2C797E09F0827FB5EADFC7DB67CB80A3AF21C40A4215972BA133"
)
OFFLINE_EXHAUSTION_DIALOG_SUMMARY_TABLE_SHA256 = (
    "98CAC57FB20458208B174E34F8944B51296C8A967C28F7BBB56C75F04E5E792E"
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
    "572A9F8128F58AA3659F26176F4EDFA167B8AB8623B6367E5B9F739802082AE2"
)
OFFLINE_EXHAUSTION_NPC_PROXY_TABLE_SHA256 = (
    "E683D0F7666451D7E7E22D863CC9F2C52AC79D1DBAA6F1A89BA2681829C5C5EA"
)
OFFLINE_EXHAUSTION_SNS_CHAT_TABLE_SHA256 = (
    "B7CC51B37FAE4F34A8E35C7D1E4F87651602CE9E2314287B8DC2C9980D751026"
)
OFFLINE_EXHAUSTION_DIALOG_ID_SOURCE_SHA256 = (
    "AE2E68E93DCDE3C2AC792541A7456E5CE6B7AF4F2AE10887D178EBFBDC080F79"
)
OFFLINE_EXHAUSTION_DIALOG_ID_INDEX_SHA256 = (
    "3FC412F637063386E7BE4934099A546E24858836FD6C221AA1C2F6BC4092B083"
)
OFFLINE_EXHAUSTION_TIMELINE_LINE_ORDERS_SHA256 = (
    "E222AFD698CF6DACE7734AE1CB33108C5369AF1A416419615C94D02B2449C785"
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
        "739D890C9D7173F0F20163450814B93B2B68E40B71384E1767BD8A1C2A58F745"
    ),
    "gameplayConfig:WorldEntityRegistry": (
        "528591EA60669E624E3B9F8C89D9BBEC0FBCAC215DA086791F2425960D96901A"
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
        "connectionRows": (
            {
                "key": "dlg_e2m8_1",
                "kind": "dialog",
                "relation": "levelscript_condition_scope",
                "direction": "context",
                "phase": "context",
                "confidence": "scoped_script",
                "source": "LevelScript referenced by this quest condition",
                "mapId": "map01_lv006",
                "scriptId": "3500100002",
                "conditionKey": "CarParked",
            },
            {
                "key": "radio_e2m8_1d5",
                "kind": "radio",
                "relation": "levelscript_condition_scope",
                "direction": "context",
                "phase": "context",
                "confidence": "scoped_script",
                "source": "LevelScript referenced by this quest condition",
                "mapId": "map01_lv006",
                "scriptId": "3500100002",
                "conditionKey": "CarParked",
            },
        ),
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
            "three independent Story action chains in the same script; the "
            "generated condition-scope rows remain context-only diagnostics"
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
    "sns_gm01m3_1": {
        "missionId": "gm01m3",
        "chatId": "sns_npc_qinjc",
        "contentIds": (-1, 1, 2, 3, 4),
        "optionIdsByContentId": {},
        "optionNextContentIds": {},
        "optionDescriptionIds": {},
        "relatedMissionId": "gm01m3",
        "contentParamsByContentId": {
            3: ("sns_image_001_mountaintop",),
            4: ("gm01m3",),
        },
        "linkMissionIdsByContentId": {4: "gm01m3"},
    },
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
    },
}
OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS.update({
    "dlg_gm01m2_1": {
        "missionId": "gm01m2",
        "filename": "dlg_gm01m2_1_p6DE17CB17A678D5A.json",
        "sha256":
            "BD2DBE7E4BAC8987033E2157261C174D7D4379A2E4D5ED646B080FE93555257D",
        "extraConfigFilename":
            "dlg_gm01m2_1_extra_config_pED5DC4585FE28B44.json",
        "extraConfigSha256":
            "F73D45BACC004E3B72A099E50210CBF20228B30B23B1E8286C496A830D7F413B",
        "lineIds": tuple(
            f"dlg_gm01m2_1_{number:03d}"
            for number in (3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 17)
        ),
        "optionIds": tuple(
            f"option_dlg_gm01m2_1_1_{number:03d}"
            for number in range(1, 5)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m2_1_{number:03d}"
            for number in (3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 17)
        ),
        "treeBranchGroups": ({
            "optionGroup": 1,
            "optionIds": tuple(
                f"option_dlg_gm01m2_1_1_{number:03d}"
                for number in range(1, 5)
            ),
            "targetLineIds": (
                "dlg_gm01m2_1_003",
                "dlg_gm01m2_1_004",
                "dlg_gm01m2_1_005",
                "dlg_gm01m2_1_009",
            ),
            "routeKind": "authored_split",
        },),
    },
    "dlg_gm01m2_2": {
        "missionId": "gm01m2",
        "filename": "dlg_gm01m2_2_p71A462BBE8385359.json",
        "sha256":
            "A27896657297FD845B3B0990E86D888C4CC75ED8320EC04C696C7116CB4EF0F0",
        "extraConfigFilename":
            "dlg_gm01m2_2_extra_config_pD96C8B0A3A7DDFF6.json",
        "extraConfigSha256":
            "25530A8723A86A80C14DAA396F2F62017B3BB3615D34FA970EE87968D1F27523",
        "lineIds": tuple(
            f"dlg_gm01m2_2_{number:03d}" for number in range(1, 5)
        ),
        "optionIds": tuple(
            f"option_dlg_gm01m2_2_1_{number:03d}" for number in range(1, 3)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m2_2_{number:03d}" for number in range(1, 5)
        ),
        "terminalOptionRoutes": ({
            "optionGroup": 1,
            "routes": ({
                "optionId": "option_dlg_gm01m2_2_1_001",
                "targetKind": "finish",
                "finishId": 1,
                "finishIdSerialized": True,
            }, {
                "optionId": "option_dlg_gm01m2_2_1_002",
                "targetKind": "finish",
                "finishId": None,
                "finishIdSerialized": False,
            }),
        },),
    },
    "dlg_gm01m2_3": {
        "missionId": "gm01m2",
        "filename": "dlg_gm01m2_3_p37EE6EE6D808E6E1.json",
        "sha256":
            "7C4401FB90DC797C0664F86B3B2C9167DB0AC82163E5133BD82C5463AC0DFB8B",
        "extraConfigFilename":
            "dlg_gm01m2_3_extra_config_pFC448B2675E98ACB.json",
        "extraConfigSha256":
            "F7063C1108A662A67E420E9F5141B3F1C7328FD6924B18DF0A500115529E3BF9",
        "lineIds": tuple(
            f"dlg_gm01m2_3_{number:03d}" for number in range(1, 4)
        ),
        "optionIds": ("option_dlg_gm01m2_3_1_001",),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m2_3_{number:03d}" for number in range(1, 4)
        ),
        "terminalOptionRoutes": ({
            "optionGroup": 1,
            "routes": ({
                "optionId": "option_dlg_gm01m2_3_1_001",
                "targetKind": "finish",
                "finishId": 1,
                "finishIdSerialized": True,
            }, {
                "optionId": "option_dlg_gm01m2_2_1_002",
                "targetKind": "finish",
                "finishId": None,
                "finishIdSerialized": False,
            }),
        },),
    },
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
})
OFFLINE_EXHAUSTION_POSITIVE_DIALOG_KEYS = frozenset({
    "dlg_e10m3_9",
    "dlg_e11m5_9",
    "dlg_e11m8_9",
})
OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS = {
    "dlg_gm01m15_7": {
        "missionId": "gm01m15",
        "dialogIdRegistrationStatus": "absent",
        "lineIds": tuple(
            f"dlg_gm01m15_7_{number:03d}" for number in range(1, 12)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m15_7_{number:03d}" for number in range(1, 12)
        ),
        "optionRows": {
            "option_dlg_gm01m15_7_1_001": {
                "iconType": "Default",
                "optionText": {"id": 7313625240270065029, "text": ""},
            },
            "option_dlg_gm01m15_7_2_001": {
                "iconType": "Default",
                "optionText": {"id": -699915481480001162, "text": ""},
            },
            "option_dlg_gm01m15_7_3_001": {
                "iconType": "Default",
                "optionText": {"id": 1876383331345779089, "text": ""},
            },
            "option_dlg_gm01m15_7_3_002": {
                "iconType": "Default",
                "optionText": {"id": 6833042270075956263, "text": ""},
            },
            "option_dlg_gm01m15_7_3_003": {
                "iconType": "Default",
                "optionText": {"id": -2379227851902736757, "text": ""},
            },
        },
        "summaryDefinition": {
            "summaryId": "summary_gm01m15_7_001",
            "row": {"id": 1386392558646000191, "text": ""},
        },
    },
    "dlg_gm01m2_5": {
        "missionId": "gm01m2",
        "dialogIdRegistrationStatus": "absent",
        "lineIds": tuple(
            f"dlg_gm01m2_5_{number:03d}" for number in range(1, 8)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m2_5_{number:03d}" for number in range(1, 8)
        ),
        "optionRows": {
            "option_dlg_gm01m2_5_1_001": {
                "iconType": "Default",
                "optionText": {"id": -5068127566167360989, "text": ""},
            },
            "option_dlg_gm01m2_5_1_003": {
                "iconType": "main",
                "optionText": {"id": -4926826630742191157, "text": ""},
            },
            "option_dlg_gm01m2_5_1_004": {
                "iconType": "Default",
                "optionText": {"id": -2556373309257697984, "text": ""},
            },
        },
    },
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
    "dlg_gm02m8_2": {
        "missionId": "gm02m8",
        "dialogIdRegistrationStatus": "absent",
        "lineIds": ("dlg_gm02m8_2_001", "dlg_gm02m8_2_002"),
        "missingAudioIds": (
            "au_dlg_gm02m8_2_001",
            "au_dlg_gm02m8_2_002",
        ),
    },
    "dlg_gm02m8_3": {
        "missionId": "gm02m8",
        "dialogIdRegistrationStatus": "absent",
        "lineIds": ("dlg_gm02m8_3_001", "dlg_gm02m8_3_002"),
        "missingAudioIds": (
            "au_dlg_gm02m8_3_001",
            "au_dlg_gm02m8_3_002",
        ),
    },
    "dlg_gm02m8_4": {
        "missionId": "gm02m8",
        "dialogIdRegistrationStatus": "absent",
        "lineIds": ("dlg_gm02m8_4_001", "dlg_gm02m8_4_002"),
        "missingAudioIds": (
            "au_dlg_gm02m8_4_001",
            "au_dlg_gm02m8_4_002",
        ),
    },
    "dlg_gm01m13_5": {
        "missionId": "gm01m13",
        "dialogIdRegistrationStatus": "absent",
        "lineIds": tuple(
            f"dlg_gm01m13_5_{number:03d}" for number in range(1, 16)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m13_5_{number:03d}" for number in range(1, 16)
        ),
        "optionRows": {
            "option_dlg_gm01m13_5_1_001": {
                "iconType": "Default",
                "optionText": {
                    "id": -3178452435804590040,
                    "text": "",
                },
            },
            "option_dlg_gm01m13_5_1_002": {
                "iconType": "Default",
                "optionText": {
                    "id": -3944096404965079386,
                    "text": "",
                },
            },
            "option_dlg_gm01m13_5_1_003": {
                "iconType": "Default",
                "optionText": {
                    "id": -2327908650745307579,
                    "text": "",
                },
            },
            "option_dlg_gm01m13_5_1_004": {
                "iconType": "Default",
                "optionText": {
                    "id": -8130280685462198942,
                    "text": "",
                },
            },
        },
    },
    "dlg_gm01m27_1": {
        "missionId": "gm01m27",
        "dialogIdRegistrationStatus": "absent",
        "lineIds": tuple(
            f"dlg_gm01m27_1_{number:03d}" for number in range(1, 7)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m27_1_{number:03d}" for number in range(1, 7)
        ),
        "optionRows": {
            "option_dlg_gm01m27_1_1_001": {
                "iconType": "Default",
                "optionText": {"id": -897435998557284210, "text": ""},
            },
            "option_dlg_gm01m27_1_2_001": {
                "iconType": "Default",
                "optionText": {"id": -8919008434441766997, "text": ""},
            },
            "option_dlg_gm01m27_1_5_001": {
                "iconType": "Default",
                "optionText": {"id": -4283208703194747952, "text": ""},
            },
        },
    },
    "dlg_gm01m27_2": {
        "missionId": "gm01m27",
        "dialogIdRegistrationStatus": "absent",
        "lineIds": tuple(
            f"dlg_gm01m27_2_{number:03d}" for number in range(2, 5)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m27_2_{number:03d}" for number in range(2, 5)
        ),
        "optionRows": {
            "option_dlg_gm01m27_2_2_001": {
                "iconType": "Default",
                "optionText": {"id": -2766844433419409788, "text": ""},
            },
            "option_dlg_gm01m27_2_3_001": {
                "iconType": "Default",
                "optionText": {"id": -3963554508229574333, "text": ""},
            },
        },
    },
    "dlg_gm01m27_3": {
        "missionId": "gm01m27",
        "dialogIdRegistrationStatus": "absent",
        "lineIds": tuple(
            f"dlg_gm01m27_3_{number:03d}" for number in range(2, 5)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m27_3_{number:03d}" for number in range(2, 5)
        ),
        "optionRows": {
            "option_dlg_gm01m27_3_2_001": {
                "iconType": "Default",
                "optionText": {"id": 7795092187764496173, "text": ""},
            },
            "option_dlg_gm01m27_3_3_001": {
                "iconType": "Default",
                "optionText": {"id": -6802259785297879704, "text": ""},
            },
        },
    },
    "dlg_gm01m14_7": {
        "missionId": "gm01m14",
        "dialogIdRegistrationStatus": "absent",
        "lineIds": tuple(
            f"dlg_gm01m14_7_{number:03d}" for number in range(1, 12)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m14_7_{number:03d}" for number in range(1, 12)
        ),
        "optionRows": {
            "option_dlg_gm01m14_7_1_001": {
                "iconType": "Default",
                "optionText": {"id": 3647346594405892853, "text": ""},
            },
            "option_dlg_gm01m14_7_2_001": {
                "iconType": "Default",
                "optionText": {"id": 7767138832851147519, "text": ""},
            },
            "option_dlg_gm01m14_7_2_002": {
                "iconType": "Default",
                "optionText": {"id": -1430088916609540453, "text": ""},
            },
            "option_dlg_gm01m14_7_3_001": {
                "iconType": "Default",
                "optionText": {"id": -6624451327300641428, "text": ""},
            },
            "option_dlg_gm01m14_7_3_002": {
                "iconType": "Default",
                "optionText": {"id": -1888007264299593017, "text": ""},
            },
        },
    },
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
    "dlg_gm01m5_1": {
        "missionId": "gm01m5",
        "dialogIdRegistrationStatus": "absent",
        "lineIds": tuple(
            f"dlg_gm01m5_1_{number:03d}"
            for number in (5, 7, *range(9, 18))
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m5_1_{number:03d}"
            for number in (5, 7, *range(9, 18))
        ),
        "optionRows": {
            "option_dlg_gm01m5_1_0d5_001": {
                "iconType": "Default",
                "optionText": {"id": 7545901413321559642, "text": ""},
            },
            "option_dlg_gm01m5_1_0d7_001": {
                "iconType": "Default",
                "optionText": {"id": 7393317461208971066, "text": ""},
            },
            "option_dlg_gm01m5_1_0d8_001": {
                "iconType": "Default",
                "optionText": {"id": -2504463061219860905, "text": ""},
            },
            "option_dlg_gm01m5_1_1_001": {
                "iconType": "Default",
                "optionText": {"id": 7521016891150217685, "text": ""},
            },
        },
    },
    "dlg_gm01m5_2": {
        "missionId": "gm01m5",
        "dialogIdRegistrationStatus": "absent",
        "lineIds": tuple(
            f"dlg_gm01m5_2_{number:03d}" for number in range(1, 7)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m5_2_{number:03d}" for number in range(1, 7)
        ),
        "optionRows": {
            "option_dlg_gm01m5_2_1_001": {
                "iconType": "Default",
                "optionText": {"id": 6525773029524646060, "text": ""},
            },
            "option_dlg_gm01m5_2_2_001": {
                "iconType": "Default",
                "optionText": {"id": -4462706000586211826, "text": ""},
            },
        },
    },
    "dlg_gm01m5_3": {
        "missionId": "gm01m5",
        "dialogIdRegistrationStatus": "absent",
        "lineIds": tuple(
            f"dlg_gm01m5_3_{number:03d}" for number in range(2, 6)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m5_3_{number:03d}" for number in range(2, 6)
        ),
        "optionRows": {
            "option_dlg_gm01m5_3_1_001": {
                "iconType": "Default",
                "optionText": {"id": 8151213580389047998, "text": ""},
            },
        },
    },
    "dlg_gm01m5_4": {
        "missionId": "gm01m5",
        "dialogIdRegistrationStatus": "absent",
        "lineIds": (
            "dlg_gm01m5_4_001",
            "dlg_gm01m5_4_002",
        ),
        "missingAudioIds": (
            "au_dlg_gm01m5_4_001",
            "au_dlg_gm01m5_4_002",
        ),
    },
    "dlg_gm02m1_1": {
        "missionId": "gm02m1",
        "dialogIdRegistrationStatus": "absent",
        "lineIds": tuple(
            f"dlg_gm02m1_1_{number:03d}" for number in range(1, 8)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm02m1_1_{number:03d}" for number in range(1, 8)
        ),
        "optionRows": {
            "option_dlg_gm02m1_1_1_001": {
                "iconType": "Default",
                "optionText": {"id": -8588518942092011657, "text": ""},
            },
            "option_dlg_gm02m1_1_2_001": {
                "iconType": "Default",
                "optionText": {"id": 1502928144381080327, "text": ""},
            },
            "option_dlg_gm02m1_1_3_001": {
                "iconType": "Default",
                "optionText": {"id": 5996584186730631298, "text": ""},
            },
        },
    },
    "dlg_gm02m1_2": {
        "missionId": "gm02m1",
        "dialogIdRegistrationStatus": "absent",
        "lineIds": tuple(
            f"dlg_gm02m1_2_{number:03d}" for number in range(1, 5)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm02m1_2_{number:03d}" for number in range(1, 5)
        ),
        "optionRows": {
            "option_dlg_gm02m1_2_2_001": {
                "iconType": "Default",
                "optionText": {"id": -2271504872494968850, "text": ""},
            },
        },
    },
    "misc_dlg_gm02m1_1d5": {
        "missionId": "gm02m1",
        "definitionRootKey": "dlg_gm02m1_1d5",
        "dialogIdRegistrationStatus": "absent",
        "lineIds": (
            "dlg_gm02m1_1d5_001",
            "dlg_gm02m1_1d5_002",
        ),
        "missingAudioIds": (
            "au_dlg_gm02m1_1d5_001",
            "au_dlg_gm02m1_1d5_002",
        ),
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
OFFLINE_EXHAUSTION_GM02M14_RADIOS = frozenset({
    "radio_gm02m14_1",
    "radio_gm02m14_12",
})
OFFLINE_EXHAUSTION_GM02M15_RADIOS = frozenset({
    "radio_gm02m15_9",
    "radio_gm02m15_12",
})
OFFLINE_EXHAUSTION_GM02M21_RADIOS = frozenset({
    "radio_gm02m21_4",
    "radio_gm02m21_7",
})
OFFLINE_EXHAUSTION_GM02M13_RADIOS = frozenset({
    "radio_gm02m13_3",
    "radio_gm02m13_4",
    "radio_gm02m13_5",
})
OFFLINE_EXHAUSTION_GM02M17_RADIOS = frozenset({
    "radio_gm02m17_2",
    "radio_gm02m17_4",
})
OFFLINE_EXHAUSTION_GM01M4_RADIOS = frozenset({"radio_gm01m4_1"})
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
OFFLINE_EXHAUSTION_GM01M27_RADIOS = frozenset({
    "radio_gm01m27_1",
    "radio_gm01m27_2",
    "radio_gm01m27_3",
})
OFFLINE_EXHAUSTION_GM01M17_RADIOS = frozenset({
    "radio_gm01m17_4",
    "radio_gm01m17_5",
    "radio_gm01m17_9",
})
OFFLINE_EXHAUSTION_GM01M3_RADIOS = frozenset({
    "radio_gm01m3_3d8",
})
OFFLINE_EXHAUSTION_GM01M5_RADIOS = frozenset({
    "radio_gm01m5_1",
    "radio_gm01m5_2",
    "radio_gm01m5_3",
    "radio_gm01m5_4",
})
OFFLINE_EXHAUSTION_GM02M1_RADIOS = frozenset({
    "radio_gm02m1_1",
    "radio_gm02m1_2",
    "radio_gm02m1_6",
    "radio_gm02m1_7",
    "radio_gm02m1_8",
})
OFFLINE_EXHAUSTION_GM02M20_RADIOS = frozenset({
    "radio_gm02m20_7",
    "radio_gm02m20_8",
    "radio_gm02m20_10",
    "radio_gm02m20_11",
    "radio_gm02m20_13",
})
OFFLINE_EXHAUSTION_GM02M23_RADIOS = frozenset({
    "radio_gm02m23_2",
})
OFFLINE_EXHAUSTION_RADIOS_BY_MISSION = {
    "a1m6d1": OFFLINE_EXHAUSTION_A1M6D1_RADIOS,
    "a1m6d2": OFFLINE_EXHAUSTION_A1M6D2_RADIOS,
    "a1m6d3": OFFLINE_EXHAUSTION_A1M6D3_RADIOS,
    "a1m8d3": OFFLINE_EXHAUSTION_A1M8D3_RADIOS,
    "gm02m2": OFFLINE_EXHAUSTION_GM02M2_RADIOS,
    "gm02m3": OFFLINE_EXHAUSTION_GM02M3_RADIOS,
    "gm02m13": OFFLINE_EXHAUSTION_GM02M13_RADIOS,
    "gm02m14": OFFLINE_EXHAUSTION_GM02M14_RADIOS,
    "gm02m15": OFFLINE_EXHAUSTION_GM02M15_RADIOS,
    "gm02m21": OFFLINE_EXHAUSTION_GM02M21_RADIOS,
    "gm02m17": OFFLINE_EXHAUSTION_GM02M17_RADIOS,
    "gm01m4": OFFLINE_EXHAUSTION_GM01M4_RADIOS,
    "gm01m6": OFFLINE_EXHAUSTION_GM01M6_RADIOS,
    "gm01m7": OFFLINE_EXHAUSTION_GM01M7_RADIOS,
    "gm01m16": OFFLINE_EXHAUSTION_GM01M16_RADIOS,
    "gm01m17": OFFLINE_EXHAUSTION_GM01M17_RADIOS,
    "gm01m3": OFFLINE_EXHAUSTION_GM01M3_RADIOS,
    "gm01m20": OFFLINE_EXHAUSTION_GM01M20_RADIOS,
    "gm01m22": OFFLINE_EXHAUSTION_GM01M22_RADIOS,
    "gm01m24": OFFLINE_EXHAUSTION_GM01M24_RADIOS,
    "gm01m25": OFFLINE_EXHAUSTION_GM01M25_RADIOS,
    "gm01m26": OFFLINE_EXHAUSTION_GM01M26_RADIOS,
    "gm01m27": OFFLINE_EXHAUSTION_GM01M27_RADIOS,
    "gm01m5": OFFLINE_EXHAUSTION_GM01M5_RADIOS,
    "gm02m1": OFFLINE_EXHAUSTION_GM02M1_RADIOS,
    "gm02m20": OFFLINE_EXHAUSTION_GM02M20_RADIOS,
    "gm02m23": OFFLINE_EXHAUSTION_GM02M23_RADIOS,
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
    "radio_gm02m14_1": frozenset({"au_radio_gm02m14_1_001"}),
    "radio_gm02m14_12": frozenset({"au_radio_gm02m14_12_001"}),
    "radio_gm02m15_9": frozenset(
        f"au_radio_gm02m15_9_{number:03d}" for number in range(1, 5)
    ),
    "radio_gm02m15_12": frozenset({
        "au_radio_gm02m15_12_001",
        "au_radio_gm02m15_12_002",
    }),
    "radio_gm02m21_4": frozenset({
        "au_radio_gm02m21_4_001",
        "au_radio_gm02m21_4_002",
    }),
    "radio_gm02m21_7": frozenset({"au_radio_gm02m21_7_001"}),
    "radio_gm02m13_3": frozenset({"au_radio_gm02m13_3_001"}),
    "radio_gm02m13_4": frozenset({"au_radio_gm02m13_4_001"}),
    "radio_gm02m13_5": frozenset({"au_radio_gm02m13_5_001"}),
    "radio_gm02m17_2": frozenset({"au_radio_gm02m17_2_001"}),
    "radio_gm02m17_4": frozenset({"au_radio_gm02m17_4_001"}),
    "radio_gm01m4_1": frozenset({"au_radio_gm01m4_1_001"}),
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
    "radio_gm01m17_4": frozenset({"au_radio_gm01m17_4_001"}),
    "radio_gm01m17_5": frozenset({"au_radio_gm01m17_5_001"}),
    "radio_gm01m17_9": frozenset({"au_radio_gm01m17_9_001"}),
    "radio_gm01m3_3d8": frozenset({"au_radio_gm01m3_3d8_001"}),
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
    "radio_gm01m27_1": frozenset({
        "au_radio_gm01m27_1_001",
        "au_radio_gm01m27_1_002",
    }),
    "radio_gm01m27_2": frozenset({"au_radio_gm01m27_2_001"}),
    "radio_gm01m27_3": frozenset({"au_radio_gm01m27_3_001"}),
    "radio_gm01m5_1": frozenset({
        "au_radio_gm01m5_1_001",
        "au_radio_gm01m5_1_002",
    }),
    "radio_gm01m5_2": frozenset({"au_radio_gm01m5_2_001"}),
    "radio_gm01m5_3": frozenset({"au_radio_gm01m5_3_001"}),
    "radio_gm01m5_4": frozenset({"au_radio_gm01m5_4_001"}),
    "radio_gm02m1_1": frozenset({
        "au_radio_gm02m1_1_001",
        "au_radio_gm02m1_1_002",
    }),
    "radio_gm02m1_2": frozenset({"au_radio_gm02m1_2_001"}),
    "radio_gm02m1_6": frozenset({
        "au_radio_gm02m1_6_001",
        "au_radio_gm02m1_6_002",
    }),
    "radio_gm02m1_7": frozenset({
        "au_radio_gm02m1_7_001",
        "au_radio_gm02m1_7_002",
    }),
    "radio_gm02m1_8": frozenset({"au_radio_gm02m1_8_001"}),
    "radio_gm02m20_7": frozenset({"au_radio_gm02m20_7_001"}),
    "radio_gm02m20_8": frozenset({
        "au_radio_gm02m20_8_001",
        "au_radio_gm02m20_8_002",
    }),
    "radio_gm02m20_10": frozenset({
        "au_radio_gm02m20_10_001",
        "au_radio_gm02m20_10_002",
    }),
    "radio_gm02m20_11": frozenset({"au_radio_gm02m20_11_001"}),
    "radio_gm02m20_13": frozenset({
        "au_radio_gm02m20_13_001",
        "au_radio_gm02m20_13_002",
    }),
    "radio_gm02m23_2": frozenset({"au_radio_gm02m23_2_001"}),
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
OFFLINE_EXHAUSTION_RADIO_LINE_FIELDS = frozenset({
    "actorName",
    "actorNameId",
    "audioEffect",
    "audioEvent",
    "audioEventDuration",
    "audioOverride",
    "emotionType",
    "iconSuffix",
    "id",
    "index",
    "infoActorName",
    "is3D",
    "radioText",
})
READING_POPUP_ROW_FIELDS = frozenset({
    "bgType",
    "contentId",
    "iconType",
    "id",
    "overrideRadioId",
    "title",
})
RICH_CONTENT_ROW_FIELDS = frozenset({"contentList", "title"})
RICH_CONTENT_ITEM_FIELDS = frozenset({"content"})
LOCALIZED_TEXT_FIELDS = frozenset({"id", "text"})
DIALOG_OPTION_ROW_FIELDS = frozenset({"iconType", "optionText"})


# Dialog rows whose full declaration the corpus-wide registry/TextAsset/action/
# native-consumer scan has superseded.  Only the key is read -- it suppresses the
# matching OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS entry -- so the filename, hash,
# line ids, option ids and branch groups are deliberately not declared here.
OFFLINE_EXHAUSTION_PATTERN_DIALOG_KEYS = frozenset({
    "dlg_a1m2_4",
    "dlg_a1m8d3_2",
    "dlg_e10m1_7",
    "dlg_e10m2_8",
    "dlg_e10m3_3",
    "dlg_e10m3_9",
    "dlg_e10m4_21",
    "dlg_e11m2_17",
    "dlg_e11m2_18",
    "dlg_e11m5_10",
    "dlg_e11m5_11",
    "dlg_e11m5_12",
    "dlg_e11m5_13",
    "dlg_e11m5_18",
    "dlg_e11m5_19",
    "dlg_e11m5_9",
    "dlg_e11m8_9",
    "dlg_e11m8d5_1",
    "dlg_e1m1_6",
    "dlg_e1m2_6",
    "dlg_e2m2_7",
    "dlg_e2m4_10",
    "dlg_e2m5_6",
    "dlg_e2m6_12",
    "dlg_e2m8d5_2",
    "dlg_e2m8d5_3",
    "dlg_e3m2_3",
    "dlg_e3m3_12",
    "dlg_e3m3_13",
    "dlg_e5m0d5_1",
    "dlg_e5m1_3",
    "dlg_e5m2_2",
    "dlg_e5m2_8",
    "dlg_e6m1_14",
    "dlg_e6m1_15",
    "dlg_e6m2_1",
    "dlg_e6m2_2",
    "dlg_e6m3_12",
    "dlg_e6m3_6",
    "dlg_e7m2_11",
    "dlg_e7m2_13",
    "dlg_e7m3_13",
    "dlg_e7m3_15",
    "dlg_e7m3_16",
    "dlg_e7m4_7",
    "dlg_e8m1_10",
    "dlg_e8m5_6",
    "dlg_e9m4_14",
    "dlg_gm01m12_6",
    "dlg_gm01m13_2",
    "dlg_gm01m13_3",
    "dlg_gm01m20_1",
    "dlg_gm01m20_5",
    "dlg_gm01m20_6",
    "dlg_gm01m20_7",
    "dlg_gm01m22_7",
    "dlg_gm01m26_5",
    "dlg_gm01m4_7",
    "dlg_gm01m6_6",
    "dlg_gm01m6_7",
    "dlg_gm01m7_1",
    "dlg_gm01m7_2",
    "dlg_gm01m7_3",
    "dlg_gm01m7_5",
    "dlg_gm01m7_7",
    "dlg_gm02m23_10",
    "dlg_gm02m23_3",
    "misc_dlg_e1m10_2d7",
    "misc_dlg_e1m3_5d5",
    "misc_dlg_e2m2_1d5",
    "misc_dlg_e2m2_4d5",
    "misc_dlg_e2m5d5_1d5",
    "misc_dlg_e2m5d5_1d7",
    "misc_dlg_e5m2_3d5",
    "misc_dlg_e6m3_3d5",
    "misc_dlg_gm01m22_2d5",
    "misc_dlg_gm01m22_3d2",
    "misc_dlg_gm01m22_3d8",
    "misc_dlg_gm01m22_4d0",
    "misc_dlg_gm01m3_1d5",
    "misc_dlg_gm01m4_3d5",
    "misc_dlg_gm01m6_1d5",
    "misc_dlg_gm01m6_3d7",
    "misc_dlg_gm01m6_4d5",
    "misc_dlg_gm01m6_4d7",
})

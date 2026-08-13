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
    "E85864F1A45827408073D83C45F9966E5AB7F6CD665F5E349A3078E557242CEA"
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
    "dlg_gm01m4_7": {
        "missionId": "gm01m4",
        "filename": "dlg_gm01m4_7_pFD9954043BA92F4B.json",
        "sha256":
            "1F5BFA67F3D8F63D9E21729746A16042E918AA6D96C8E90AAF5023CA1BAC6DE8",
        "extraConfigFilename":
            "dlg_gm01m4_7_extra_config_p3CB06BFD1EB1528E.json",
        "extraConfigSha256":
            "0457E91190591D4BBA58E38AF3386136240AB6F9C7679F3D96BF7BBC83507FC1",
        "lineIds": ("dlg_gm01m4_7_001", "dlg_gm01m4_7_002"),
        "optionIds": (),
        "missingAudioIds": (
            "au_dlg_gm01m4_7_001",
            "au_dlg_gm01m4_7_002",
        ),
        "treeBranchGroups": (),
    },
    "misc_dlg_gm01m4_3d5": {
        "missionId": "gm01m4",
        "registryKey": "dlg_gm01m4_3d5",
        "definitionName": "dlg_gm01m4_3d5",
        "linePrefix": "dlg_gm01m4_3d5",
        "filename": "dlg_gm01m4_3d5_p005943414CADFF30.json",
        "sha256":
            "8F63AF4A69F7ACC4D399A35D4B37C4DCA6DDF9CED735FF610EB61333356D6C3B",
        "extraConfigFilename":
            "dlg_gm01m4_3d5_extra_config_p763DAF129AD61F5C.json",
        "extraConfigSha256":
            "6178009F0AEE6189EF06A672B92BB6F03F8573FDE3D82183D122CF99DC3FB085",
        "lineIds": tuple(
            f"dlg_gm01m4_3d5_{number:03d}" for number in range(1, 7)
        ),
        "optionIds": (
            "option_dlg_gm01m4_3d5_1_001",
            "option_dlg_gm01m4_3d5_1_002",
            "option_dlg_gm01m4_3d5_2_001",
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m4_3d5_{number:03d}" for number in range(1, 7)
        ),
        "treeBranchGroups": ({
            "optionGroup": 1,
            "optionIds": (
                "option_dlg_gm01m4_3d5_1_001",
                "option_dlg_gm01m4_3d5_1_002",
            ),
            "targetLineIds": (
                "dlg_gm01m4_3d5_002",
                "dlg_gm01m4_3d5_004",
            ),
            "routeKind": "authored_split",
        },),
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
    },
}
OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS.update({
    "dlg_gm01m13_2": {
        "missionId": "gm01m13",
        "filename": "dlg_gm01m13_2_p6111EDB6915C69D3.json",
        "sha256":
            "4E43CCC1AD780AA52165A8CC418E0509BACEBBA9008E62AA574BFEB400DEC038",
        "extraConfigFilename":
            "dlg_gm01m13_2_extra_config_pC629794770766448.json",
        "extraConfigSha256":
            "2525EF2C9DFCE40DFF3B37A0B49FF7FF13B040F495896A74EE85144041831E04",
        "lineIds": tuple(
            f"dlg_gm01m13_2_{number:03d}" for number in range(1, 5)
        ),
        "optionIds": (
            "option_dlg_gm01m13_2_1_001",
            "option_dlg_gm01m13_2_1_002",
            "option_dlg_gm01m13_2_2_001",
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m13_2_{number:03d}" for number in range(1, 5)
        ),
        "treeBranchGroups": ({
            "optionGroup": 1,
            "optionIds": (
                "option_dlg_gm01m13_2_1_001",
                "option_dlg_gm01m13_2_1_002",
            ),
            "targetLineIds": (
                "dlg_gm01m13_2_002",
                "dlg_gm01m13_2_002",
            ),
            "routeKind": "authored_convergence",
        },),
    },
    "dlg_gm01m13_3": {
        "missionId": "gm01m13",
        "filename": "dlg_gm01m13_3_pDE9BBF7424BF26B3.json",
        "sha256":
            "62FF437E956572B46C0FFB91EA0769C43A9EF1DE8ABCE2354A80350CA281269F",
        "extraConfigFilename":
            "dlg_gm01m13_3_extra_config_pE937F7AF1D4BC1D4.json",
        "extraConfigSha256":
            "D0948F6D3B5FE518CDEBD1FF2D93F92ECCA7647C89656BDF3B8519DC9A231F28",
        "lineIds": tuple(
            f"dlg_gm01m13_3_{number:03d}" for number in range(1, 7)
        ),
        "optionIds": (
            "option_dlg_gm01m13_3_1_001",
            "option_dlg_gm01m13_3_1_002",
            "option_dlg_gm01m13_3_2_001",
            "option_dlg_gm01m13_3_3_001",
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm01m13_3_{number:03d}" for number in range(1, 7)
        ),
        "treeBranchGroups": ({
            "optionGroup": 1,
            "optionIds": (
                "option_dlg_gm01m13_3_1_001",
                "option_dlg_gm01m13_3_1_002",
            ),
            "targetLineIds": (
                "dlg_gm01m13_3_002",
                "dlg_gm01m13_3_002",
            ),
            "routeKind": "authored_convergence",
        },),
    },
    "misc_dlg_gm01m3_1d5": {
        "missionId": "gm01m3",
        "registryKey": "dlg_gm01m3_1d5",
        "definitionName": "dlg_gm01m3_1d5",
        "linePrefix": "dlg_gm01m3_1d5",
        "filename": "dlg_gm01m3_1d5_pB106A6457D8BF1BD.json",
        "sha256":
            "5ADAEB0133A3198723A5F4C1A502274702EE1B46C4D4A84C67C29A16976220AF",
        "extraConfigFilename":
            "dlg_gm01m3_1d5_extra_config_p268BC753F522C8BB.json",
        "extraConfigSha256":
            "721600663850AA7D05111E5B01D3E9059C931F9CE3F4DA29FA6A596D6D5B0AC7",
        "lineIds": (
            "dlg_gm01m3_1d5_001",
            "dlg_gm01m3_1d5_002",
        ),
        "optionIds": (),
        "missingAudioIds": (
            "au_dlg_gm01m3_1d5_001",
            "au_dlg_gm01m3_1d5_002",
        ),
    },
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
    "dlg_gm02m23_3": {
        "missionId": "gm02m23",
        "filename": "dlg_gm02m23_3_p74D15E007EC90CA9.json",
        "sha256":
            "F502E97DCE41E066F7613CC8A824F7A20A0E64FFEF1C78C5F284776515A477C5",
        "extraConfigFilename":
            "dlg_gm02m23_3_extra_config_pF338636E6A5CD416.json",
        "extraConfigSha256":
            "609B3B2E956C093B05455E0ACD96C2A6E314DAF43237F50DBFB8DFB2CE9648B0",
        "lineIds": tuple(
            f"dlg_gm02m23_3_{number:03d}"
            for number in (1, 2, 3, 4, 12, 13, *range(15, 26))
        ),
        "optionIds": tuple(
            f"option_dlg_gm02m23_3_{group}_{option:03d}"
            for group, option_count in ((1, 1), (2, 1), (3, 1), (4, 2), (5, 2), (6, 2))
            for option in range(1, option_count + 1)
        ),
        "missingAudioIds": tuple(
            f"au_dlg_gm02m23_3_{number:03d}"
            for number in (1, 2, 3, 4, 12, 13, *range(15, 26))
        ),
        "treeBranchGroups": ({
            "optionGroup": 4,
            "optionIds": (
                "option_dlg_gm02m23_3_4_001",
                "option_dlg_gm02m23_3_4_002",
            ),
            "targetLineIds": (
                "dlg_gm02m23_3_023",
                "dlg_gm02m23_3_023",
            ),
            "routeKind": "authored_convergence",
        }, {
            "optionGroup": 5,
            "optionIds": (
                "option_dlg_gm02m23_3_5_001",
                "option_dlg_gm02m23_3_5_002",
            ),
            "targetLineIds": (
                "dlg_gm02m23_3_024",
                "dlg_gm02m23_3_024",
            ),
            "routeKind": "authored_convergence",
        }),
        "terminalOptionRoutes": ({
            "optionGroup": 6,
            "routes": ({
                "optionId": "option_dlg_gm02m23_3_6_001",
                "targetKind": "finish",
                "finishId": None,
                "finishIdSerialized": False,
            }, {
                "optionId": "option_dlg_gm02m23_3_6_002",
                "targetKind": "finish",
                "finishId": 1,
                "finishIdSerialized": True,
            }),
        },),
    },
    "dlg_gm02m23_10": {
        "missionId": "gm02m23",
        "filename": "dlg_gm02m23_10_p99A23FBF0CB0A83A.json",
        "sha256":
            "5685E8729B73FDB33D4E10858844C57940506294F9E2B08A169D90A957B56FE5",
        "extraConfigFilename":
            "dlg_gm02m23_10_extra_config_pD2C5313C93130F58.json",
        "extraConfigSha256":
            "70722DB31C09A31993FCF6D76EDEC10DA6CA39131DD4F9B923E9FF94740AA60A",
        "lineIds": ("dlg_gm02m23_10_001",),
        "optionIds": (
            "option_dlg_gm02m23_10_1_001",
            "option_dlg_gm02m23_10_1_002",
        ),
        "missingAudioIds": ("au_dlg_gm02m23_10_001",),
        "treeBranchGroups": (),
        "terminalOptionRoutes": ({
            "optionGroup": 1,
            "routes": ({
                "optionId": "option_dlg_gm02m23_10_1_001",
                "targetKind": "finish",
                "finishId": None,
                "finishIdSerialized": False,
            }, {
                "optionId": "option_dlg_gm02m23_10_1_002",
                "targetKind": "finish",
                "finishId": 1,
                "finishIdSerialized": True,
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

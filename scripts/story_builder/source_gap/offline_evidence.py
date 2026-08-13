"""Build-locked offline exhaustion evidence and validators."""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[3]
from .foundation import (
    read_json,
    resolve_installed_native_inputs,
    safe_key,
)
from .contracts import target_set_sha256
from ..animestudio_story_objects import (
    CARRIER_REPORT_PATH,
    HIERARCHY_REPORT_PATH,
    REVERSE_REPORT_PATH,
)
from ..level_bindings import (
    LEVELSCRIPT_NATIVE_EXACT_CONTROL_PATH_STATUSES,
    _levelscript_native_control_paths_to_record,
    build_levelscript_unhosted_reading_popup_receiver_index,
    parse_leveldata_levelscript_brief_dictionary,
)
from ..levelscript_binary import (
    decode_levelscript_record_payload,
    decode_levelscript_task_conditions,
    extract_levelscript_uid_records,
    levelscript_action_map_membership,
    levelscript_record_semantic_key,
)
from ..anime_assets import recover_dialog_tree_definition_evidence
from ..mission_recovery import natural_key


from .data import (
    CORE_STORY_NODE_KINDS,
    NPC_PROXY_DIALOG_SELECTION_MAPPING_ID,
    NPC_PROXY_DIALOG_SELECTION_GAMEASSEMBLY_SHA256,
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
    OFFLINE_EXHAUSTION_TEXT_ONLY_CUTSCENES,
    OFFLINE_EXHAUSTION_SNS_DEFINITIONS,
    OFFLINE_EXHAUSTION_CUTSCENES_BY_MISSION,
    OFFLINE_EXHAUSTION_REVERSE_HOST_COUNTS,
    OFFLINE_EXHAUSTION_CUTSCENE_DEFINITIONS,
    OFFLINE_EXHAUSTION_GAMEOBJECT_ROW_COUNTS,
    OFFLINE_EXHAUSTION_ROOT_PLAYBACK_ALIASES,
    OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS,
    OFFLINE_EXHAUSTION_POSITIVE_DIALOG_KEYS,
    OFFLINE_EXHAUSTION_TEXT_ONLY_DIALOGS,
    OFFLINE_EXHAUSTION_DIALOG_ROW_FIELDS,
    OFFLINE_EXHAUSTION_RADIOS_BY_MISSION,
    OFFLINE_EXHAUSTION_RADIO_CONTEXTS,
    OFFLINE_EXHAUSTION_RADIO_AUDIO_VARIANTS,
    OFFLINE_EXHAUSTION_RADIO_MISSING_AUDIO_IDS,
)

from .providers import (
    _build_mission_npc_proxy_tracking_index,
    _configured_game_assembly_path,
    _generic_mission_npc_proxy_tracking_contexts,
    _generic_registered_dialog_tree_definition_facts,
    _merge_exact_interaction_trigger_with_native_playback,
    _repo_source_path,
    _sha256_file,
    _string_list,
)
from .content_evidence import (
    _compose_registered_dialog_tree_npc_proxy_evidence,
    _generic_dialog_timeline_definition_facts,
    _generic_missionless_npc_proxy_dialog_facts,
    _generic_partial_dialog_row_consumer_exhaustion_facts,
    _generic_radio_definition_facts,
    _generic_reading_popup_definition_facts,
    _generic_registered_dialog_tree_trunk_group_facts,
    _generic_registered_table_dialog_definition_facts,
    _generic_text_table_only_cutscene_definition_facts,
    _generic_unlinked_sns_definition_facts,
    _generic_unregistered_dialog_definition_facts,
    _offline_radio_definition_validation_failure,
)











def _literal_absence_census(
    literals: list[str],
    source_paths: list[Path],
) -> dict[str, Any]:
    """Search immutable binary inputs without assuming their object names.

    A byte-substring hit is deliberately conservative: it prevents an
    absence-based closure even when the surrounding record is not decoded.
    An absence is useful only because both UTF-8 and UTF-16LE encodings were
    searched across the complete supplied file set.
    """
    normalized_literals = sorted({safe_key(value) for value in literals} - {""})
    normalized_paths = sorted(
        {path.resolve() for path in source_paths if path.is_file()},
        key=lambda path: natural_key(str(path)),
    )
    digest = hashlib.sha256()
    matches: dict[str, list[str]] = defaultdict(list)
    for path in normalized_paths:
        payload = path.read_bytes()
        try:
            display_path = str(path.relative_to(ROOT)).replace("\\", "/")
        except ValueError:
            display_path = str(path).replace("\\", "/")
        digest.update(display_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(payload).digest())
        for literal in normalized_literals:
            if (
                literal.encode("utf-8") in payload
                or literal.encode("utf-16le") in payload
            ):
                matches[literal].append(display_path)
    return {
        "mappingId": "complete-file-set-literal-absence-census-v1",
        "literalIds": normalized_literals,
        "sourceFileCount": len(normalized_paths),
        "sourceSetSha256": digest.hexdigest().upper(),
        "matchesByLiteral": {
            literal: paths
            for literal, paths in sorted(
                matches.items(),
                key=lambda item: natural_key(item[0]),
            )
        },
        "encodingSearch": ["utf-8", "utf-16le"],
        "matchSemantics": "conservative_byte_substring",
    }

def _is_authored_sns_definition_candidate(
    story_key: str,
    sns_dialog_table: Any,
) -> bool:
    """Select candidates by exact authored table identity, never key shape."""
    return bool(
        isinstance(sns_dialog_table, dict)
        and isinstance(sns_dialog_table.get(story_key), dict)
        and safe_key(sns_dialog_table[story_key].get("dialogId"))
        == story_key
    )

OFFLINE_EXHAUSTION_TEXT_DEFINITIONS = {
    "text_gm01m15_1": {
        "missionId": "gm01m15",
        "readingPopupRowId": "text_gm01m15_1",
        "bgType": 1,
        "iconType": 1,
        "titleId": 5249534470886375510,
        "contentTextIds": (
            8242330289792353294,
            -2455707730206541547,
            -2339893156956209480,
            119766408319964938,
            -8714781499976003721,
        ),
        "prtsDefinition": {
            "rowId": "nar_digital_map01_research1_16_1",
            "row": {
                "contentId": "text_gm01m15_1",
                "desc": {"id": 0, "text": ""},
                "firstLvId": "digital_map01_research1_16",
                "id": "nar_digital_map01_research1_16_1",
                "name": {"id": -3724480734488975224, "text": ""},
                "order": 1,
                "overrideRadioId": "",
                "type": "text",
            },
        },
    },
    "text_gm01m15_8": {
        "missionId": "gm01m15",
        "readingPopupRowId": "text_gm01m15_8",
        "bgType": 0,
        "iconType": 1,
        "titleId": 6250703409374408529,
        "contentTextIds": (6649389232287698087,),
    },
    "text_gm01m13_1": {
        "missionId": "gm01m13",
        "readingPopupRowId": "text_gm01m13_1",
        "bgType": 1,
        "iconType": 1,
        "titleId": -7492450601852500945,
        "contentTextIds": (
            -2654932629375346098,
            -1909211100807560957,
            296752428137017004,
            -8195488846124280714,
            -8624547630771488929,
            2389739675065963780,
            8112352344191541483,
            3219624433628234345,
        ),
    },
    "text_gm01m17_1": {
        "missionId": "gm01m17",
        "readingPopupRowId": "text_gm01m17_1",
        "bgType": 2,
        "iconType": 0,
        "titleId": -5216252211990160921,
        "contentTextIds": (
            2833540280945742009,
            -8531949106363903611,
        ),
    },
    "text_gm01m14_4": {
        "missionId": "gm01m14",
        "readingPopupRowId": "text_gm01m14_4",
        "bgType": 0,
        "iconType": 1,
        "titleId": -1815196899219287791,
        "contentTextIds": (7825423282124136370,),
    },
    "text_gm01m14_5": {
        "missionId": "gm01m14",
        "readingPopupRowId": "text_gm01m14_5",
        "bgType": 1,
        "iconType": 1,
        "titleId": -6907858543972655543,
        "contentTextIds": (
            -9160925395685764986,
            3098739108941993286,
            -752533186137572878,
            141580649494390203,
            -8810372145751559528,
            -5510452575580863,
            443073140103742447,
        ),
    },
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

def _generic_missionless_native_playback_facts(
    story_key: str,
    occurrences: Any,
    *,
    source_root: Path = ROOT,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str | None]:
    """Validate exact local event-to-playback paths without mission identity.

    This is deliberately a playback classifier, not an ownership or ordering
    rule.  A row qualifies only when every typed occurrence is backed by a
    complete current-build GameAssembly mapping and every exact event owner is
    explicitly local (no serialized mission/quest id and no server exchange).
    """
    exact_statuses = LEVELSCRIPT_NATIVE_EXACT_CONTROL_PATH_STATUSES

    def failure(
        gate: str,
        occurrence: Any,
        expected: dict[str, Any],
        actual: dict[str, Any],
    ) -> tuple[None, dict[str, Any], None]:
        source_file = (
            safe_key(occurrence.get("sourceFile"))
            if isinstance(occurrence, dict) else ""
        )
        source_path = Path(source_file)
        if source_file and not source_path.is_absolute():
            source_path = source_root / source_path
        return None, {
            "validator": "genericMissionlessNativePlayback",
            "gate": gate,
            "storyKey": story_key,
            "sourcePaths": [source_file] if source_file else [],
            "sourceSha256": {
                source_file: _sha256_file(source_path)
            } if source_file else {},
            "expected": expected,
            "actual": actual,
        }, None

    if not isinstance(occurrences, list) or not occurrences:
        return None, None, "noNativePlayback"
    typed_occurrences = [
        occurrence
        for occurrence in occurrences
        if (
            isinstance(occurrence, dict)
            and safe_key(occurrence.get("actionMapRole")).startswith(
                "actionList#"
            )
            and safe_key(occurrence.get("recordClass")).startswith("play_")
            and safe_key(occurrence.get("actionName"))
        )
    ]
    if not typed_occurrences:
        return None, None, "noTypedPlayback"

    accepted_paths: list[dict[str, Any]] = []
    source_hashes: dict[str, str] = {}
    mapping_ids: set[str] = set()
    saw_exact_owner = False
    saw_mission_or_server_owner = False
    for occurrence in typed_occurrences:
        source_file = safe_key(occurrence.get("sourceFile"))
        source_path = Path(source_file)
        if source_file and not source_path.is_absolute():
            source_path = source_root / source_path
        action_name = safe_key(occurrence.get("actionName"))
        record_class = safe_key(occurrence.get("recordClass"))
        authored_story_key = (
            safe_key(occurrence.get("authoredStoryKey")) or story_key
        )
        alias_valid = (
            authored_story_key == story_key
            or (
                story_key.startswith("misc_dlg_")
                and authored_story_key == story_key.removeprefix("misc_")
            )
        )
        action_local_id = occurrence.get("localId")
        mapping_id = safe_key(occurrence.get("nativeMappingId"))
        story_keys = _string_list(occurrence.get("allStoryKeysInRecord"))
        if (
            not source_file
            or not source_path.is_file()
            or not safe_key(occurrence.get("actionMapRole")).startswith(
                "actionList#"
            )
            or not action_name
            or not record_class.startswith("play_")
            or not isinstance(action_local_id, int)
            or not mapping_id.startswith("gameassembly-")
            or not alias_valid
            or authored_story_key not in story_keys
        ):
            return failure(
                "exactTypedPlaybackRecord",
                occurrence,
                {
                    "existingSourceFile": True,
                    "actionMapRolePrefix": "actionList#",
                    "recordClassPrefix": "play_",
                    "integerLocalId": True,
                    "currentGameAssemblyMapping": True,
                    "recordContainsAuthoredStoryKey": authored_story_key,
                    "mechanicalAliasValid": True,
                },
                {
                    "sourceFile": source_file,
                    "sourceFileExists": source_path.is_file(),
                    "actionMapRole": occurrence.get("actionMapRole"),
                    "actionName": action_name,
                    "recordClass": record_class,
                    "localId": action_local_id,
                    "nativeMappingId": mapping_id,
                    "allStoryKeysInRecord": story_keys,
                },
            )
        exact_owners = [
            owner
            for owner in occurrence.get("nativeEventOwners") or []
            if isinstance(owner, dict)
            and safe_key(owner.get("status")) in exact_statuses
        ]
        if not exact_owners:
            return None, None, "incompleteNativeControlPath"
        saw_exact_owner = True
        mapping_ids.add(mapping_id)
        source_hashes[source_file] = _sha256_file(source_path)
        for owner in exact_owners:
            event_detail = (
                owner.get("eventDetail")
                if isinstance(owner.get("eventDetail"), dict) else {}
            )
            if (
                event_detail.get("serializedMissionOrQuestId") is not False
                or event_detail.get("serverExchange") is not False
            ):
                saw_mission_or_server_owner = True
                continue
            path = owner.get("path")
            terminal = path[-1] if isinstance(path, list) and path else None
            path_local_ids = [
                step.get("localId")
                for step in path or []
                if isinstance(step, dict)
            ]
            if (
                not safe_key(owner.get("headerName"))
                or not isinstance(owner.get("headerLocalId"), int)
                or not isinstance(path, list)
                or not path
                or len(path_local_ids) != len(path)
                or not all(isinstance(local_id, int) for local_id in path_local_ids)
                or not isinstance(terminal, dict)
                or terminal.get("localId") != action_local_id
                or safe_key(terminal.get("actionName")) != action_name
                or safe_key(terminal.get("recordClass")) != record_class
            ):
                return failure(
                    "exactMissionlessNativeControlPath",
                    occurrence,
                    {
                        "namedIntegerHeader": True,
                        "nonemptyIntegerPath": True,
                        "terminalLocalId": action_local_id,
                        "terminalActionName": action_name,
                        "terminalRecordClass": record_class,
                        "serializedMissionOrQuestId": False,
                        "serverExchange": False,
                    },
                    {
                        "headerName": owner.get("headerName"),
                        "headerLocalId": owner.get("headerLocalId"),
                        "pathLocalIds": path_local_ids,
                        "terminal": terminal,
                        "eventDetail": event_detail,
                    },
                )
            accepted_paths.append({
                "authoredStoryKey": authored_story_key,
                "levelId": safe_key(occurrence.get("levelId")),
                "scriptId": safe_key(occurrence.get("scriptId")),
                "sourceFile": source_file,
                "sourceSha256": source_hashes[source_file],
                "nativeMappingId": mapping_id,
                "controlPathStatus": safe_key(owner.get("status")),
                "headerName": safe_key(owner.get("headerName")),
                "headerLocalId": owner.get("headerLocalId"),
                "eventSummary": safe_key(event_detail.get("summary")),
                "eventType": safe_key(event_detail.get("type")),
                "actionName": action_name,
                "recordClass": record_class,
                "actionLocalId": action_local_id,
                "pathLocalIds": path_local_ids,
                "path": path,
            })

    if saw_mission_or_server_owner:
        return None, None, "missionOrServerBoundEventPath"
    if not saw_exact_owner or not accepted_paths:
        return None, None, "noExactMissionlessEventPath"
    return {
        "nativeEventPaths": accepted_paths,
        "nativeMappingIds": sorted(mapping_ids),
        "sourceFiles": sorted(source_hashes, key=natural_key),
        "sourceSha256": {
            path: source_hashes[path]
            for path in sorted(source_hashes, key=natural_key)
        },
    }, None, None

def _present_literal_keys(
    payload: bytes,
    literals: dict[str, str],
    encoding: str,
) -> set[str]:
    """Return keys whose exact literal bytes occur, including overlaps.

    One look-ahead alternation scans the binary once. Sorting longest first
    and expanding prefix matches preserves shorter literals that begin at the
    same byte offset without falling back to one full binary scan per key.
    """
    encoded_to_keys: dict[bytes, set[str]] = defaultdict(set)
    for key, literal in literals.items():
        if key and literal:
            encoded_to_keys[literal.encode(encoding)].add(key)
    if not payload or not encoded_to_keys:
        return set()
    patterns = sorted(encoded_to_keys, key=lambda value: (-len(value), value))
    matcher = re.compile(
        b"(?=(" + b"|".join(re.escape(value) for value in patterns) + b"))"
    )
    prefixes_by_match = {
        value: {
            key
            for prefix, keys in encoded_to_keys.items()
            if value.startswith(prefix)
            for key in keys
        }
        for value in patterns
    }
    present: set[str] = set()
    for match in matcher.finditer(payload):
        present.update(prefixes_by_match.get(match.group(1), set()))
    return present

def _configured_global_metadata_path() -> Path | None:
    return resolve_installed_native_inputs()[1]

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

def _audit_source_index_diagnostics(
    report: dict[str, Any],
) -> list[dict[str, Any]]:
    reported = {
        safe_key(row.get("source")): safe_key(
            row.get("stageSignatureSha256")
        ).lower()
        for row in report.get("sources") or []
        if isinstance(row, dict) and safe_key(row.get("source"))
    }
    failures: list[dict[str, Any]] = []
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
        signature = safe_key(
            (summary.get("stageSignature") or {}).get("sha256")
        ).lower() if isinstance(summary, dict) else ""
        expected_signature = reported.get(source, "")
        if (
            not summary_path.is_file()
            or not isinstance(summary, dict)
            or summary.get("complete") is not True
            or not signature
            or expected_signature != signature
        ):
            failures.append({
                "validator": "offlineAnimeStudioCarrierAudit",
                "gate": "exactCurrentPublishedObjectIndex",
                "source": source,
                "sourcePath": str(summary_path),
                "expected": {
                    "exists": True,
                    "complete": True,
                    "stageSignatureSha256": expected_signature,
                },
                "actual": {
                    "exists": summary_path.is_file(),
                    "payloadType": type(summary).__name__,
                    "complete": (
                        summary.get("complete")
                        if isinstance(summary, dict) else None
                    ),
                    "stageSignatureSha256": signature,
                },
            })
    return failures

def _audit_sources_match_current_indexes(report: dict[str, Any]) -> bool:
    return not _audit_source_index_diagnostics(report)

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

def _mission_related_original_data_validation(
    mission_id: str,
    declaration: dict[str, Any],
    prts_reading_table: Any,
    num_id_str_table: Any,
    str_id_num_table: Any,
    text_table: Any,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Validate a related mission-prefix bundle without creating Story edges."""
    group_id = declaration["groupId"]
    group = (
        prts_reading_table.get(group_id)
        if isinstance(prts_reading_table, dict) else None
    )
    rows = group.get("list") if isinstance(group, dict) else None
    actual_entries: list[dict[str, Any]] = []
    if isinstance(rows, dict):
        for key in sorted(rows, key=natural_key):
            row = rows.get(key)
            if not isinstance(row, dict):
                continue
            actual_entries.append({
                "order": row.get("order"),
                "contentId": safe_key(row.get("contentId")),
                "prtsId": safe_key(row.get("prtsId")),
                "uniqId": safe_key(row.get("uniqId")),
                "nameId": (
                    row.get("name", {}).get("id")
                    if isinstance(row.get("name"), dict) else None
                ),
                "overrideRadioId": safe_key(row.get("overrideRadioId")),
                "subtitleId": (
                    row.get("subtitle", {}).get("id")
                    if isinstance(row.get("subtitle"), dict) else None
                ),
            })
    expected_entries = [
        {
            "order": entry["order"],
            "contentId": entry["contentId"],
            "prtsId": entry["prtsId"],
            "uniqId": entry["uniqId"],
            "nameId": entry["nameId"],
            "overrideRadioId": "",
            "subtitleId": 0,
        }
        for entry in declaration["entries"]
    ]
    num_mapping = (
        num_id_str_table.get("prts_terminal_content_id", {}).get("dic")
        if isinstance(num_id_str_table, dict) else None
    )
    str_mapping = (
        str_id_num_table.get("prts_terminal_content_id", {}).get("dic")
        if isinstance(str_id_num_table, dict) else None
    )
    expected_num_mapping = {
        str(entry["numericId"]): entry["uniqId"]
        for entry in declaration["entries"]
    }
    actual_num_mapping = {
        numeric_id: num_mapping.get(numeric_id)
        for numeric_id in expected_num_mapping
    } if isinstance(num_mapping, dict) else None
    expected_str_mapping = {
        entry["uniqId"]: entry["numericId"]
        for entry in declaration["entries"]
    }
    actual_str_mapping = {
        uniq_id: str_mapping.get(uniq_id)
        for uniq_id in expected_str_mapping
    } if isinstance(str_mapping, dict) else None
    expected_text_rows = declaration["missionTextRows"]
    actual_text_rows = {
        key: (
            text_table.get(key, {}).get("id")
            if isinstance(text_table, dict)
            and isinstance(text_table.get(key), dict)
            else None
        )
        for key in expected_text_rows
    }
    if not (
        actual_entries == expected_entries
        and actual_num_mapping == expected_num_mapping
        and actual_str_mapping == expected_str_mapping
        and actual_text_rows == expected_text_rows
    ):
        return None, {
            "validator": "offlineMissionRelatedOriginalData",
            "gate": "exactPrtsTerminalBundleAndMissionTextRows",
            "mission": mission_id,
            "expected": {
                "entries": expected_entries,
                "numIdStr": expected_num_mapping,
                "strIdNum": expected_str_mapping,
                "missionTextRows": expected_text_rows,
            },
            "actual": {
                "entries": actual_entries,
                "numIdStr": actual_num_mapping,
                "strIdNum": actual_str_mapping,
                "missionTextRows": actual_text_rows,
            },
        }
    return {
        "relation": declaration["relation"],
        "groupId": group_id,
        "levelId": declaration["levelId"],
        "entries": [
            {
                "order": entry["order"],
                "contentId": entry["contentId"],
                "prtsId": entry["prtsId"],
                "uniqId": entry["uniqId"],
                "numericId": entry["numericId"],
            }
            for entry in declaration["entries"]
        ],
        "missionTextRowKeys": list(expected_text_rows),
        "storyRelationStatus": (
            "same_nominal_mission_only_no_scene_or_quest_join"
        ),
        "orderBoundary": (
            "PrtsReading order proves only the two terminal entries; it "
            "does not order or activate any dialog or radio Story file"
        ),
    }, None

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
        if not isinstance(node, dict):
            return None
        if node.get("$id") in (None, ""):
            if safe_key(node.get("$type")) != (
                "Beyond.Gameplay.DialogTreeExActorNode"
            ):
                return None
            continue
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
        target_nodes = [node_by_id[target_id] for target_id in targets]
        if not all(
            safe_key(target.get("$type")).endswith(".DialogTreeTrunkNode")
            for target in target_nodes
        ):
            # A multi-option terminal group belongs to the companion terminal
            # decoder. Accept only exact direct/linear-transition FinishNode
            # routes here; any mixed or branching shape reopens validation.
            resolved_terminal_flags: list[bool] = []
            for target_id in targets:
                seen: set[str] = set()
                current_id = target_id
                while current_id not in seen:
                    seen.add(current_id)
                    current = node_by_id[current_id]
                    current_type = safe_key(current.get("$type"))
                    if current_type.endswith(".DialogTreeFinishNode"):
                        resolved_terminal_flags.append(True)
                        break
                    if not current_type.endswith(".DialogTransitionNode"):
                        resolved_terminal_flags.append(False)
                        break
                    next_ids = targets_by_source.get(current_id) or []
                    if len(next_ids) != 1:
                        resolved_terminal_flags.append(False)
                        break
                    current_id = next_ids[0]
                else:
                    resolved_terminal_flags.append(False)
            if all(resolved_terminal_flags):
                continue
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
        if not isinstance(node, dict):
            return None
        if node.get("$id") in (None, ""):
            if safe_key(node.get("$type")) != (
                "Beyond.Gameplay.DialogTreeExActorNode"
            ):
                return None
            continue
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
        resolved_target_nodes: list[dict[str, Any]] = []
        for target_id in targets:
            seen: set[str] = set()
            current_id = target_id
            while current_id not in seen:
                seen.add(current_id)
                current = node_by_id[current_id]
                current_type = safe_key(current.get("$type"))
                if current_type.endswith(".DialogTreeFinishNode"):
                    resolved_target_nodes.append(current)
                    break
                if not current_type.endswith(".DialogTransitionNode"):
                    resolved_target_nodes.append(current)
                    break
                next_ids = targets_by_source.get(current_id) or []
                if len(next_ids) != 1:
                    return None
                current_id = next_ids[0]
            else:
                return None
        terminal_flags = [
            safe_key(target.get("$type")).endswith(".DialogTreeFinishNode")
            for target in resolved_target_nodes
        ]
        if not any(terminal_flags):
            continue
        if not all(terminal_flags):
            return None
        routes: list[dict[str, Any]] = []
        for option_id, target in zip(
            option_ids,
            resolved_target_nodes,
            strict=True,
        ):
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

def _declared_dialog_context_definitions() -> dict[str, dict[str, Any]]:
    """Return only manual rows that encode a typed external relationship.

    Plain registered DialogTree definitions are intentionally absent.  They
    are discovered from the current core-isolated target set, DialogId index,
    TextAsset corpus, Timeline index, action census, native playback census,
    object-carrier audit, and installed binaries.  A declaration remains only
    when it supplies an additional original-data relationship whose schema is
    validated by a dedicated decoder below.
    """
    context_fields = {
        "allowedNonOwningRoute",
        "sharedTimeline",
    }
    context_keys = {
        story_key
        for story_key, definition in OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS.items()
        if context_fields & set(definition)
    }
    context_keys.update(OFFLINE_EXHAUSTION_LEVELSCRIPT_TASK_CONSUMERS)
    for context in OFFLINE_EXHAUSTION_LEVELDATA_DIALOG_BRANCH_CONTEXTS.values():
        context_keys.update(
            safe_key(story_key)
            for story_key in (context.get("propertyDialogs") or {}).values()
            if safe_key(story_key)
        )
    return {
        story_key: OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS[story_key]
        for story_key in sorted(context_keys, key=natural_key)
        if story_key in OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS
    }

def build_offline_exhaustion_index(
    partial_report: dict[str, Any],
    table_root: Path,
    *,
    game_assembly_path: Path | None = None,
    global_metadata_path: Path | None = None,
    carrier_audit_path: Path | None = None,
    gameobject_audit_path: Path | None = None,
    reverse_pptr_audit_path: Path | None = None,
    native_playback_index: dict[str, list[dict[str, Any]]] | None = None,
    action_story_occurrences: dict[str, list[dict[str, Any]]] | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Build hash-locked current-build deferrals for exhausted offline rows.

    A deferral changes queue priority only. It never creates Story ownership,
    playback, or chronology. Every source gate must match the audited build;
    otherwise the complete set reopens automatically.
    """
    # Most registered DialogTree rows are now recovered by the corpus-wide
    # registry/TextAsset/action/native-consumer scan below.  Keep the legacy
    # declarations only for cases that add a separately typed relationship
    # which cannot be reconstructed from the DialogTree definition alone.
    # This deliberately makes a new plain DialogTree eligible without adding
    # its id, filename, hash, lines, options, or branch groups to this module.
    dialog_context_definitions = _declared_dialog_context_definitions()
    pattern_dialog_keys = (
        set(OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS)
        - set(dialog_context_definitions)
    )
    declared_absent_binary_tokens = {
        story_key: token
        for story_key, token
        in OFFLINE_EXHAUSTION_ABSENT_BINARY_TOKENS.items()
        if story_key not in pattern_dialog_keys
    }

    carrier_audit_path = carrier_audit_path or CARRIER_REPORT_PATH
    gameobject_audit_path = gameobject_audit_path or HIERARCHY_REPORT_PATH
    reverse_pptr_audit_path = reverse_pptr_audit_path or REVERSE_REPORT_PATH
    game_assembly_path = game_assembly_path or _configured_game_assembly_path()
    global_metadata_path = (
        global_metadata_path or _configured_global_metadata_path()
    )
    source_paths = {
        "radioTable": table_root / "RadioTable.json",
        "audioDialog": table_root / "AudioDialog.json",
        "numIdStrTable": table_root / "NumIdStrTable.json",
        "strIdNumTable": table_root / "StrIdNumTable.json",
        "textTable": table_root / "TextTable.json",
        "dialogTextTable": table_root / "DialogTextTable.json",
        "dialogOptionTable": table_root / "DialogOptionTable.json",
        "dialogSummaryMapTable": table_root / "DialogSummaryMapTable.json",
        "dialogSummaryTable": table_root / "DialogSummaryTable.json",
        "readingPopupTable": table_root / "ReadingPopUpTable.json",
        "richContentTable": table_root / "RichContentTable.json",
        "prtsAllItemTable": table_root / "PrtsAllItem.json",
        "prtsRecordTable": table_root / "PrtsRecord.json",
        "prtsReadingTable": table_root / "PrtsReading.json",
        "snsDialogTable": table_root / "SNSDialogTable.json",
        "snsOptionTable": table_root / "SNSDialogOptionTable.json",
        "snsChatTable": table_root / "SNSChatTable.json",
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
        "npcProxyTable": (
            ROOT
            / "export_full"
            / "structured"
            / "StreamingAssets"
            / "Data"
            / "Json"
            / "GameplayConfig"
            / "NpcProxyTable.json"
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
        "levelBasicInfoTable": (
            ROOT
            / "export_full"
            / "structured"
            / "StreamingAssets"
            / "Data"
            / "Json"
            / "GameplayConfig"
            / "LevelBasicInfoTable.json"
        ),
        "levelConfigRoot": (
            ROOT
            / "export_full"
            / "structured"
            / "StreamingAssets"
            / "Data"
            / "Json"
            / "LevelConfig"
        ),
        "levelDataRoot": (
            ROOT
            / "export_full"
            / "structured"
            / "StreamingAssets"
            / "Data"
            / "Json"
            / "LevelData"
        ),
        "levelScriptRoot": (
            ROOT
            / "export_full"
            / "structured"
            / "StreamingAssets"
            / "Data"
            / "Json"
            / "LevelScriptData"
        ),
        "subGameInstanceDataTable": (
            ROOT
            / "export_full"
            / "structured"
            / "StreamingAssets"
            / "Data"
            / "Json"
            / "GameplayConfig"
            / "SubGameInstanceDataTable.json"
        ),
        "scriptTaskExtraInfoTable": (
            ROOT
            / "export_full"
            / "structured"
            / "StreamingAssets"
            / "Data"
            / "Json"
            / "GameplayConfig"
            / "ScriptTaskExtraInfoTable.json"
        ),
        "timelineLineOrders": (
            ROOT
            / "export_full"
            / "recovered"
            / "AnimeStudio-cli"
            / "timeline_line_orders.json"
        ),
        "gameAssembly": game_assembly_path,
        "globalMetadata": global_metadata_path,
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
        dialog_context_definitions.items()
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
        for inventory_index, inventory in enumerate(
            context.get("levelScriptPlaybackInventories", ()),
            start=1,
        ):
            source_paths[
                f"missionTopologyPlayback:{mission_id}:{inventory_index}"
            ] = ROOT / inventory["sourceFile"]
    for mission_id, context in (
        OFFLINE_EXHAUSTION_LEVELDATA_DIALOG_BRANCH_CONTEXTS.items()
    ):
        source_paths[
            f"levelDataDialogBranch:{mission_id}"
        ] = ROOT / context["levelDataFile"]
        source_paths[
            f"levelScriptDialogBranch:{mission_id}"
        ] = ROOT / context["levelScriptFile"]
    for mission_id, context in (
        OFFLINE_EXHAUSTION_EMPTY_LEVELSCRIPT_CONTEXTS.items()
    ):
        source_paths[
            f"emptyLevelDataContext:{mission_id}"
        ] = ROOT / context["levelDataFile"]
        source_paths[
            f"emptyLevelScriptContext:{mission_id}"
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
        "strIdNumTable": OFFLINE_EXHAUSTION_STR_ID_NUM_TABLE_SHA256,
        "textTable": OFFLINE_EXHAUSTION_TEXT_TABLE_SHA256,
        "dialogTextTable": OFFLINE_EXHAUSTION_DIALOG_TEXT_TABLE_SHA256,
        "dialogOptionTable": OFFLINE_EXHAUSTION_DIALOG_OPTION_TABLE_SHA256,
        "dialogSummaryMapTable":
            OFFLINE_EXHAUSTION_DIALOG_SUMMARY_MAP_TABLE_SHA256,
        "dialogSummaryTable":
            OFFLINE_EXHAUSTION_DIALOG_SUMMARY_TABLE_SHA256,
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
        "snsChatTable": OFFLINE_EXHAUSTION_SNS_CHAT_TABLE_SHA256,
        "npcProxyExDataTable":
            OFFLINE_EXHAUSTION_NPC_PROXY_EX_TABLE_SHA256,
        "npcProxyTable": OFFLINE_EXHAUSTION_NPC_PROXY_TABLE_SHA256,
        "dialogIdSource": OFFLINE_EXHAUSTION_DIALOG_ID_SOURCE_SHA256,
        "dialogIdIndex": OFFLINE_EXHAUSTION_DIALOG_ID_INDEX_SHA256,
        "timelineLineOrders":
            OFFLINE_EXHAUSTION_TIMELINE_LINE_ORDERS_SHA256,
        "gameAssembly": OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
        "globalMetadata": OFFLINE_EXHAUSTION_METADATA_SHA256,
    }
    for context in OFFLINE_EXHAUSTION_RADIO_CONTEXTS.values():
        expected_hashes[context["sourceKey"]] = context["sha256"]
    for story_key, definition in (
        dialog_context_definitions.items()
    ):
        expected_hashes[
            f"dialogDefinition:{story_key}"
        ] = definition["sha256"]
        if definition.get("extraConfigFilename"):
            expected_hashes[
                f"dialogExtraConfig:{story_key}"
            ] = definition["extraConfigSha256"]
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
        for inventory_index, inventory in enumerate(
            context.get("levelScriptPlaybackInventories", ()),
            start=1,
        ):
            expected_hashes[
                f"missionTopologyPlayback:{mission_id}:{inventory_index}"
            ] = inventory["sourceSha256"]
    for mission_id, context in (
        OFFLINE_EXHAUSTION_LEVELDATA_DIALOG_BRANCH_CONTEXTS.items()
    ):
        expected_hashes[
            f"levelDataDialogBranch:{mission_id}"
        ] = context["levelDataSha256"]
        expected_hashes[
            f"levelScriptDialogBranch:{mission_id}"
        ] = context["levelScriptSha256"]
    for mission_id, context in (
        OFFLINE_EXHAUSTION_EMPTY_LEVELSCRIPT_CONTEXTS.items()
    ):
        expected_hashes[
            f"emptyLevelDataContext:{mission_id}"
        ] = context["levelDataSha256"]
        expected_hashes[
            f"emptyLevelScriptContext:{mission_id}"
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
        "sourcePaths": {
            name: _repo_source_path(path)
            for name, path in source_paths.items()
            if name in expected_hashes
        },
        "sourceHashMismatches": mismatches,
        "graphEffect": "none",
        "queueEffect": "defer only while every exact current-build gate matches",
    }
    if mismatches:
        return {}, status

    mission_related_original_data_by_mission: dict[
        str, dict[str, Any]
    ] = {}
    prts_reading_table = read_json(source_paths["prtsReadingTable"], {})
    num_id_str_table = read_json(source_paths["numIdStrTable"], {})
    str_id_num_table = read_json(source_paths["strIdNumTable"], {})
    text_table = read_json(source_paths["textTable"], {})
    for mission_id, declaration in (
        OFFLINE_EXHAUSTION_MISSION_RELATED_ORIGINAL_DATA.items()
    ):
        related_original_data, failure = (
            _mission_related_original_data_validation(
                mission_id,
                declaration,
                prts_reading_table,
                num_id_str_table,
                str_id_num_table,
                text_table,
            )
        )
        if failure:
            failure["sourcePaths"] = [
                str(source_paths[name])
                for name in declaration["sourceKeys"]
            ]
            failure["sourceSha256"] = {
                name: actual_hashes.get(name, "")
                for name in declaration["sourceKeys"]
            }
            status.update({
                "status": (
                    "inactive_mission_related_original_data_validation_failed"
                ),
                "validatorDiagnostics": [failure],
            })
            return {}, status
        related_original_data["sourceFiles"] = [
            str(source_paths[name].relative_to(ROOT)).replace("\\", "/")
            for name in declaration["sourceKeys"]
        ]
        mission_related_original_data_by_mission[
            mission_id
        ] = related_original_data

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
        in declared_absent_binary_tokens.items()
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

    try:
        global_metadata_bytes = source_paths["globalMetadata"].read_bytes()
    except (AttributeError, OSError) as exc:
        status.update({
            "status": "inactive_global_metadata_token_validation_failed",
            "validatorDiagnostics": [{
                "validator": "offlineGlobalMetadataTokenAbsence",
                "gate": "readCurrentGlobalMetadata",
                "sourcePaths": [str(source_paths["globalMetadata"])],
                "sourceSha256": {
                    "globalMetadata": actual_hashes.get(
                        "globalMetadata", ""
                    ),
                },
                "expected": {"readable": True},
                "actual": {
                    "readable": False,
                    "error": f"{type(exc).__name__}: {exc}",
                },
            }],
        })
        return {}, status
    metadata_token_counts = {
        story_key: {
            "token": token,
            "utf8": global_metadata_bytes.count(token.encode("utf-8")),
            "utf16le": global_metadata_bytes.count(
                token.encode("utf-16le")
            ),
        }
        for story_key, token
        in declared_absent_binary_tokens.items()
    }
    present_metadata_tokens = {
        story_key: counts
        for story_key, counts in metadata_token_counts.items()
        if counts["utf8"] or counts["utf16le"]
    }
    if present_metadata_tokens:
        status.update({
            "status": "inactive_global_metadata_token_validation_failed",
            "validatorDiagnostics": [{
                "validator": "offlineGlobalMetadataTokenAbsence",
                "gate": "exactRootTokensAbsent",
                "sourcePaths": [str(source_paths["globalMetadata"])],
                "sourceSha256": {
                    "globalMetadata": actual_hashes.get(
                        "globalMetadata", ""
                    ),
                },
                "expected": {"utf8Count": 0, "utf16leCount": 0},
                "actual": present_metadata_tokens,
            }],
        })
        return {}, status
    status["globalMetadataAbsentRootTokens"] = metadata_token_counts

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
        expected_failed_conditions = declaration.get(
            "failedConditionsByQuest"
        )
        actual_failed_conditions = (
            {
                quest_id: (
                    quest_dic.get(quest_id, {}).get("failedCondition")
                    if isinstance(quest_dic.get(quest_id), dict) else None
                )
                for quest_id in expected_failed_conditions
            }
            if isinstance(expected_failed_conditions, dict)
            and isinstance(quest_dic, dict)
            else None
        )
        expected_quest_state_dependencies = {
            quest_id: list(dependencies)
            for quest_id, dependencies in declaration.get(
                "questStateDependenciesByQuest", {}
            ).items()
        }
        expected_objective_conjunctions = {
            quest_id: [
                {
                    **conjunction,
                    "subConditions": list(
                        conjunction.get("subConditions") or []
                    ),
                }
                for conjunction in conjunctions
            ]
            for quest_id, conjunctions in declaration.get(
                "objectiveConjunctionsByQuest", {}
            ).items()
        }
        expected_levelscript_playback_inventories = [
            {
                **inventory,
                "playbackRecords": list(inventory["playbackRecords"]),
                "absentStoryKeys": list(inventory["absentStoryKeys"]),
            }
            for inventory in declaration.get(
                "levelScriptPlaybackInventories", ()
            )
        ]
        actual_quest_state_dependencies: dict[
            str, list[dict[str, Any]] | None
        ] = {}
        actual_objective_conjunctions: dict[
            str, list[dict[str, Any]] | None
        ] = {}
        actual_levelscript_playback_inventories: list[dict[str, Any]] = []

        def iter_quest_state_conditions(
            condition: Any,
            index_path: tuple[int, ...] = (),
        ) -> Iterator[tuple[tuple[int, ...], dict[str, Any]]]:
            if not isinstance(condition, dict):
                return
            if (
                safe_key(condition.get("$type")).split(",", 1)[0]
                == "Beyond.Gameplay.CheckQuestState"
            ):
                yield index_path, condition
            for sub_index, sub_condition in enumerate(
                condition.get("subConditions") or []
            ):
                yield from iter_quest_state_conditions(
                    sub_condition,
                    (*index_path, sub_index),
                )

        for quest_id in expected_quest_state_dependencies:
            quest = (
                quest_dic.get(quest_id)
                if isinstance(quest_dic, dict) else None
            )
            objectives = (
                quest.get("objectiveList")
                if isinstance(quest, dict) else None
            )
            if not isinstance(objectives, list):
                actual_quest_state_dependencies[quest_id] = None
                continue
            dependencies: list[dict[str, Any]] = []
            for objective_index, objective in enumerate(objectives, 1):
                condition = (
                    objective.get("condition")
                    if isinstance(objective, dict) else None
                )
                for condition_path, dependency in (
                    iter_quest_state_conditions(condition)
                ):
                    dependencies.append({
                        "objectiveIndex": objective_index,
                        **(
                            {"conditionIndexPath": condition_path}
                            if condition_path else {}
                        ),
                        "targetQuestId": safe_key(
                            (dependency.get("_questId") or {}).get(
                                "constValue"
                            )
                        ),
                        "comparer": (
                            dependency.get("_comparer") or {}
                        ).get("constValue"),
                        "targetQuestState": (
                            dependency.get("_targetQuestState") or {}
                        ).get("constValue"),
                        "scopeMask": dependency.get("scopeMask"),
                        "useGraphScope": dependency.get("useGraphScope"),
                    })
            actual_quest_state_dependencies[quest_id] = dependencies

        for quest_id, expected_conjunctions in (
            expected_objective_conjunctions.items()
        ):
            quest = (
                quest_dic.get(quest_id)
                if isinstance(quest_dic, dict) else None
            )
            objectives = (
                quest.get("objectiveList")
                if isinstance(quest, dict) else None
            )
            if not isinstance(objectives, list):
                actual_objective_conjunctions[quest_id] = None
                continue
            conjunctions: list[dict[str, Any]] = []
            for expected_conjunction in expected_conjunctions:
                objective_index = expected_conjunction["objectiveIndex"]
                objective = (
                    objectives[objective_index - 1]
                    if isinstance(objective_index, int)
                    and 0 < objective_index <= len(objectives)
                    and isinstance(objectives[objective_index - 1], dict)
                    else None
                )
                condition = (
                    objective.get("condition")
                    if isinstance(objective, dict) else None
                )
                if not isinstance(condition, dict):
                    conjunctions.append({
                        "objectiveIndex": objective_index,
                        "conditionType": "",
                        "conditionEvalString": "",
                        "subConditions": [],
                    })
                    continue
                sub_conditions = []
                for condition_index, sub_condition in enumerate(
                    condition.get("subConditions") or []
                ):
                    if not isinstance(sub_condition, dict):
                        continue
                    condition_type = safe_key(
                        sub_condition.get("$type")
                    ).split(",", 1)[0]
                    level_id_field = (
                        "levelId"
                        if condition_type
                        == "Beyond.Gameplay.CheckLevelScriptStage"
                        else "_mapId"
                    )
                    script_id_field = (
                        "scriptId"
                        if condition_type
                        == "Beyond.Gameplay.CheckLevelScriptStage"
                        else "_scriptId"
                    )
                    map_id = safe_key(
                        (sub_condition.get(level_id_field) or {}).get(
                            "constValue"
                        )
                    )
                    raw_script_id = (
                        sub_condition.get(script_id_field) or {}
                    ).get("constValue")
                    script_id = (
                        raw_script_id.get("scriptId")
                        if isinstance(raw_script_id, dict)
                        else raw_script_id
                    )
                    sub_condition_row = {
                        "conditionIndex": condition_index,
                        "conditionType": condition_type,
                        "mapId": map_id,
                        "scriptId": script_id,
                        "sourceFile": (
                            "export_full/structured/StreamingAssets/Data/Json/"
                            f"LevelScriptData/{map_id}/{script_id}.json"
                        ),
                    }
                    if (
                        condition_type
                        == "Beyond.Gameplay.CheckLevelScriptStage"
                    ):
                        sub_condition_row.update({
                            "stageValue": (
                                sub_condition.get("_progressToCompare") or {}
                            ).get("constValue"),
                            "compareOperator": (
                                sub_condition.get("_compareOperator") or {}
                            ).get("constValue"),
                        })
                    else:
                        sub_condition_row.update({
                            "key": safe_key(
                                (sub_condition.get("_key") or {}).get(
                                    "constValue"
                                )
                            ),
                            "value": (
                                sub_condition.get("_value") or {}
                            ).get("constValue"),
                            "comparer": (
                                sub_condition.get("_comparer") or {}
                            ).get("constValue"),
                        })
                    sub_conditions.append(sub_condition_row)
                conjunctions.append({
                    "objectiveIndex": objective_index,
                    "conditionType": safe_key(
                        condition.get("$type")
                    ).split(",", 1)[0],
                    "conditionEvalString": safe_key(
                        condition.get("conditionEvalString")
                    ),
                    "subConditions": sub_conditions,
                })
            actual_objective_conjunctions[quest_id] = conjunctions

        for inventory_index, expected_inventory in enumerate(
            expected_levelscript_playback_inventories,
            start=1,
        ):
            playback_source_name = (
                f"missionTopologyPlayback:{mission_id}:{inventory_index}"
            )
            playback_data = source_paths[playback_source_name].read_bytes()
            playback_records = extract_levelscript_uid_records(
                playback_data
            )
            _action_map, playback_membership = (
                levelscript_action_map_membership(
                    playback_data,
                    playback_records,
                )
            )
            actual_playback_records = []
            for record_index, record in enumerate(playback_records):
                action = {
                    (0x0363, 0x0D): "PlayRadio",
                    (0x0364, 0x0D): "PlayRadioAndWait",
                }.get(levelscript_record_semantic_key(record))
                if not action:
                    continue
                role = safe_key(
                    playback_membership.get(record.get("start"))
                )
                decoded_payload = decode_levelscript_record_payload(
                    playback_data,
                    record,
                    next_start=(
                        playback_records[record_index + 1].get("start")
                        if record_index + 1 < len(playback_records)
                        else None
                    ),
                    action_map_role=role,
                )
                story_values = [
                    safe_key(field.get("value"))
                    for field in decoded_payload.get("taggedFields") or []
                    if (
                        isinstance(field, dict)
                        and field.get("type") == "string"
                        and safe_key(field.get("value"))
                    )
                ]
                actual_playback_records.append({
                    "action": action,
                    "storyKey": (
                        story_values[0] if len(story_values) == 1 else ""
                    ),
                    "independentActionRoot": (
                        role.startswith("actionList#")
                        and role.endswith(" root")
                    ),
                })
            actual_playback_records.sort(
                key=lambda row: natural_key(row["storyKey"])
            )
            actual_story_keys = {
                row["storyKey"] for row in actual_playback_records
            }
            actual_levelscript_playback_inventories.append({
                "sourceFile": expected_inventory["sourceFile"],
                "sourceSha256": expected_inventory["sourceSha256"],
                "playbackRecords": actual_playback_records,
                "absentStoryKeys": [
                    story_key
                    for story_key in expected_inventory["absentStoryKeys"]
                    if story_key not in actual_story_keys
                ],
            })
        if (
            actual_levelscript_playback_inventories
            != expected_levelscript_playback_inventories
        ):
            playback_source_names = [
                f"missionTopologyPlayback:{mission_id}:{inventory_index}"
                for inventory_index in range(
                    1,
                    len(expected_levelscript_playback_inventories) + 1,
                )
            ]
            status.update({
                "status": (
                    "inactive_levelscript_playback_inventory_validation_failed"
                ),
                "validatorDiagnostics": [{
                    "validator": "offlineLevelScriptPlaybackInventory",
                    "gate": (
                        "exactTypedPlaybackRecordsIndependentRootsAndAbsentTargets"
                    ),
                    "mission": mission_id,
                    "sourcePaths": [
                        str(source_paths[name])
                        for name in playback_source_names
                    ],
                    "sourceSha256": {
                        name: actual_hashes.get(name, "")
                        for name in playback_source_names
                    },
                    "expected": expected_levelscript_playback_inventories,
                    "actual": actual_levelscript_playback_inventories,
                }],
            })
            return {}, status
        valid = (
            isinstance(quest_dic, dict)
            and set(quest_dic) == set(expected_prev)
            and actual_prev == expected_prev
            and actual_main_path == expected_main_path
            and (
                expected_failed_conditions is None
                or actual_failed_conditions == expected_failed_conditions
            )
            and actual_quest_state_dependencies
            == expected_quest_state_dependencies
            and actual_objective_conjunctions
            == expected_objective_conjunctions
        )
        if not valid:
            status.update({
                "status": "inactive_mission_topology_context_validation_failed",
                "validatorDiagnostics": [{
                    "validator": "offlineMissionTopologyContext",
                    "gate": (
                        "exactQuestPredecessorGraphMainPathStateDependencies"
                        "AndObjectiveConjunctions"
                    ),
                    "mission": mission_id,
                    "sourcePaths": [str(source_paths[source_name])],
                    "sourceSha256": {
                        source_name: actual_hashes.get(source_name, ""),
                    },
                    "expected": {
                        "questIds": sorted(expected_prev, key=natural_key),
                        "prevQuestIdListByQuest": expected_prev,
                        "mainPathQuests": expected_main_path,
                        "failedConditionsByQuest": expected_failed_conditions,
                        "questStateDependenciesByQuest": (
                            expected_quest_state_dependencies
                        ),
                        "objectiveConjunctionsByQuest": (
                            expected_objective_conjunctions
                        ),
                    },
                    "actual": {
                        "questIds": sorted(quest_dic, key=natural_key)
                        if isinstance(quest_dic, dict) else None,
                        "prevQuestIdListByQuest": actual_prev,
                        "mainPathQuests": actual_main_path,
                        "failedConditionsByQuest": actual_failed_conditions,
                        "questStateDependenciesByQuest": (
                            actual_quest_state_dependencies
                        ),
                        "objectiveConjunctionsByQuest": (
                            actual_objective_conjunctions
                        ),
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
        parallel_rendezvous = [
            {
                "forkQuestId": fork["questId"],
                "parallelQuestIds": fork["successorQuestIds"],
                "mergeQuestId": merge["questId"],
                "joinSemantics": "all_predecessor_quests_required",
                "playerChoice": False,
            }
            for fork in forks
            for merge in merges
            if set(fork["successorQuestIds"])
            == set(merge["predecessorQuestIds"])
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
            "parallelRendezvous": parallel_rendezvous,
            "terminalQuestIds": [
                quest_id for quest_id, quest_successors in successors.items()
                if not quest_successors
            ],
            "failedQuestStateGuards": [
                {
                    "questId": quest_id,
                    "conditionType": "CheckQuestState",
                    "targetQuestId": safe_key(
                        (condition.get("_questId") or {}).get("constValue")
                    ),
                    "comparer": (condition.get("_comparer") or {}).get(
                        "constValue"
                    ),
                    "targetQuestState": (
                        condition.get("_targetQuestState") or {}
                    ).get("constValue"),
                    "relation": "authored_quest_failure_guard",
                    "branchExclusivityStatus": (
                        "not_proven_by_one_way_failure_guard"
                    ),
                    "storyOrderEvidence": False,
                }
                for quest_id, condition in (
                    expected_failed_conditions or {}
                ).items()
                if (
                    isinstance(condition, dict)
                    and safe_key(condition.get("$type")).split(",", 1)[0]
                    == "Beyond.Gameplay.CheckQuestState"
                )
            ],
            "failedDialogGuards": [
                {
                    "questId": quest_id,
                    "conditionType": "CombineCondition",
                    "conditionEvalString": condition.get(
                        "conditionEvalString"
                    ),
                    "dialogFinishes": [
                        {
                            "dialogId": safe_key(
                                (leaf.get("_dialogId") or {}).get(
                                    "constValue"
                                )
                            ),
                            "finishId": (
                                leaf.get("_finishId") or {}
                            ).get("constValue"),
                        }
                        for leaf in condition.get("subConditions") or []
                    ],
                    "relation": "authored_quest_failure_guard",
                    "branchExclusivityStatus": (
                        "not_proven_by_failure_guards_alone"
                    ),
                    "storyOrderEvidence": False,
                }
                for quest_id, condition in (
                    expected_failed_conditions or {}
                ).items()
                if (
                    isinstance(condition, dict)
                    and safe_key(condition.get("$type")).split(",", 1)[0]
                    == "Beyond.Gameplay.CombineCondition"
                    and condition.get("subConditions")
                    and all(
                        isinstance(leaf, dict)
                        and safe_key(leaf.get("$type")).split(",", 1)[0]
                        == "Beyond.Gameplay.CheckTalkOptionFinish"
                        for leaf in condition.get("subConditions") or []
                    )
                )
            ],
            "questStateDependencies": [
                {"questId": quest_id, **dependency}
                for quest_id, dependencies
                in expected_quest_state_dependencies.items()
                for dependency in dependencies
            ],
            "objectiveConjunctions": [
                {
                    "questId": quest_id,
                    **conjunction,
                    "completionSemantics": (
                        "all_serialized_conditions_required"
                    ),
                    "executionOrderStatus": "not_serialized",
                    "storyOrderEvidence": False,
                    "relatedSourceFiles": sorted({
                        declaration["sourceFile"],
                        *(
                            sub_condition["sourceFile"]
                            for sub_condition in conjunction[
                                "subConditions"
                            ]
                        ),
                    }),
                }
                for quest_id, conjunctions
                in expected_objective_conjunctions.items()
                for conjunction in conjunctions
            ],
            "levelScriptPlaybackInventories": [
                {
                    **inventory,
                    "serializedListOrderStatus": "not_execution_order",
                    "ownershipBoundary": (
                        "exact playback ownership only for listed Story keys; "
                        "absent targets remain definition-only"
                    ),
                    "storyOrderEvidence": False,
                }
                for inventory in expected_levelscript_playback_inventories
            ],
            "relation": "authored_mission_quest_predecessor_topology",
            "storyPlacementStatus": "unresolved",
            "storyAssignments": [],
            "flowIndexExclusivityStatus": "not_evidence",
            "serverSuccessorSelectionStatus": "not_serialized_in_client_asset",
            "orderEvidence": False,
            "graphEffect": "none",
        }

    empty_levelscript_context_by_mission: dict[str, dict[str, Any]] = {}
    for mission_id, declaration in (
        OFFLINE_EXHAUSTION_EMPTY_LEVELSCRIPT_CONTEXTS.items()
    ):
        leveldata_name = f"emptyLevelDataContext:{mission_id}"
        levelscript_name = f"emptyLevelScriptContext:{mission_id}"
        leveldata_path = source_paths[leveldata_name]
        levelscript_path = source_paths[levelscript_name]
        script_id = int(declaration["scriptId"])
        leveldata_bytes = leveldata_path.read_bytes()
        levelscript_bytes = levelscript_path.read_bytes()
        brief_dictionary = parse_leveldata_levelscript_brief_dictionary(
            leveldata_bytes,
            {script_id},
        )
        brief = brief_dictionary.get(script_id) or {}
        records = extract_levelscript_uid_records(levelscript_bytes)
        action_map, _membership = levelscript_action_map_membership(
            levelscript_bytes,
            records,
        )
        task_maps = decode_levelscript_task_conditions(
            levelscript_bytes,
            script_id,
        )
        actual_brief = {
            "scriptId": safe_key(brief.get("scriptId")),
            "dataPathHash": safe_key(brief.get("dataPathHash")),
            "levelScriptType": brief.get("levelScriptType"),
            "maxStage": brief.get("maxStage"),
            "parentLevelScriptId": safe_key(
                brief.get("parentLevelScriptId")
            ),
            "propertyCount": brief.get("propertyCount"),
            "propertyMapCount": brief.get("propertyMapCount"),
            "refWorldEntityCount": brief.get("refWorldEntityCount"),
            "dictionaryEntryCount": brief.get("dictionaryEntryCount"),
        }
        expected_brief = {
            "scriptId": declaration["scriptId"],
            "dataPathHash": declaration["dataPathHash"],
            "levelScriptType": declaration["levelScriptType"],
            "maxStage": declaration["maxStage"],
            "parentLevelScriptId": "0",
            "propertyCount": 0,
            "propertyMapCount": 0,
            "refWorldEntityCount": 0,
            "dictionaryEntryCount": 1,
        }
        valid = (
            len(brief_dictionary) == 1
            and actual_brief == expected_brief
            and not records
            and action_map.get("status") == "present"
            and action_map.get("recordCount") == 0
            and not task_maps
        )
        if not valid:
            status.update({
                "status": "inactive_empty_levelscript_context_validation_failed",
                "validatorDiagnostics": [{
                    "validator": "offlineEmptyLevelScriptContext",
                    "gate": "exactSinglePropertylessHostAndNoActionRecords",
                    "mission": mission_id,
                    "sourcePaths": [str(leveldata_path), str(levelscript_path)],
                    "sourceSha256": {
                        leveldata_name: actual_hashes.get(leveldata_name, ""),
                        levelscript_name: actual_hashes.get(levelscript_name, ""),
                    },
                    "expected": {
                        "brief": expected_brief,
                        "uidRecordCount": 0,
                        "actionMapStatus": "present",
                        "actionListRecordCount": 0,
                        "taskMapCount": 0,
                    },
                    "actual": {
                        "brief": actual_brief,
                        "dictionaryScriptIds": sorted(
                            (str(value) for value in brief_dictionary),
                            key=int,
                        ),
                        "uidRecordCount": len(records),
                        "actionMapStatus": action_map.get("status"),
                        "actionListRecordCount": action_map.get("recordCount"),
                        "taskMapCount": len(task_maps),
                    },
                }],
            })
            return {}, status
        empty_levelscript_context_by_mission[mission_id] = {
            "missionId": mission_id,
            "levelId": declaration["levelId"],
            "scriptId": declaration["scriptId"],
            "levelDataFile": declaration["levelDataFile"],
            "levelScriptFile": declaration["levelScriptFile"],
            "dictionaryScriptIds": [declaration["scriptId"]],
            "dataPathHash": declaration["dataPathHash"],
            "propertyCount": 0,
            "propertyMapCount": 0,
            "refWorldEntityCount": 0,
            "uidRecordCount": 0,
            "actionListRecordCount": 0,
            "taskMapCount": 0,
            "storyReferences": [],
            "playbackActions": [],
            "orderEvidence": False,
            "graphEffect": "none",
            "evidenceBoundary": (
                "the mission-named LevelData contains one exact LevelScript "
                "BriefData entry, but that entry has no properties or world-"
                "entity references and its LevelScript has no decoded UID "
                "action/header/getter records or task maps; the host therefore "
                "cannot activate or order the nominal Story definitions"
            ),
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
            and brief.get("propertyCount") == declaration["propertyCount"]
            and brief.get("propertyMapCount") == declaration["propertyCount"]
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
    carrier_audit_target_digest = safe_key(
        carrier_audit.get("targetSetSha256")
        if isinstance(carrier_audit, dict)
        else ""
    ).lower()
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
        in dialog_context_definitions.items()
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
    required_key_missions = {
        **radio_mission_by_key,
        **cutscene_mission_by_key,
        **dialog_mission_by_key,
        **text_only_dialog_mission_by_key,
        **sns_mission_by_key,
        **text_mission_by_key,
    }
    required_keys = set(required_key_missions)
    carrier_audit_source_diagnostics = _audit_source_index_diagnostics(
        carrier_audit if isinstance(carrier_audit, dict) else {}
    )
    # The carrier audit is reusable per Story key when its published source
    # indexes still match.  Requiring equality with the whole gap-queue target
    # digest made one unrelated target-set change invalidate thousands of
    # independently negative rows.  Every candidate still fails closed unless
    # it is explicitly present in noCandidateStoryKeys; newly introduced keys
    # therefore remain actionable until a future carrier audit covers them.
    if (
        not isinstance(carrier_audit, dict)
        or carrier_audit.get("_schema") != "animestudioStoryCarrierAudit.v3"
        or safe_key(carrier_audit.get("targetField"))
        != "coreIsolatedSceneKeys"
        or not required_keys <= no_candidate_keys
        or any(
            core_targets.get(story_key) != {mission}
            for story_key, mission in required_key_missions.items()
        )
        or carrier_audit_source_diagnostics
    ):
        status.update({
            "status": "inactive_carrier_audit_stale_or_incomplete",
            "coreTargetSetSha256": core_target_digest,
            "carrierAuditTargetSetSha256": carrier_audit_target_digest,
            "missingRequiredCarrierAuditStoryKeys": sorted(
                required_keys - no_candidate_keys,
                key=natural_key,
            ),
            "validatorDiagnostics": carrier_audit_source_diagnostics,
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
    generic_radio_evidence_by_key: dict[str, dict[str, Any]] = {}
    generic_radio_validation_failures: list[dict[str, Any]] = []
    generic_radio_exclusions: dict[str, list[str]] = {
        "declaredSpecialCase": [],
        "ambiguousMission": [],
        "nativePlayback": [],
        "typedObjectCarrier": [],
        "binaryRootTokenPresent": [],
        "invalidDefinition": [],
    }
    generic_radio_definition_facts: dict[str, dict[str, Any]] = {}

    def source_display_path(path: Path) -> str:
        resolved = path.resolve()
        if resolved.is_relative_to(ROOT):
            return resolved.relative_to(ROOT).as_posix()
        return resolved.as_posix()

    missionless_native_evidence_by_key: dict[str, dict[str, Any]] = {}
    missionless_native_validation_failures: list[dict[str, Any]] = []
    missionless_native_exclusions: dict[str, list[str]] = defaultdict(list)
    if native_playback_index is not None:
        for story_key, missions in sorted(
            core_targets.items(),
            key=lambda item: natural_key(item[0]),
        ):
            occurrences = native_playback_index.get(story_key) or []
            if not occurrences:
                missionless_native_exclusions["noNativePlayback"].append(
                    story_key
                )
                continue
            if len(missions) != 1:
                missionless_native_exclusions["ambiguousMission"].append(
                    story_key
                )
                continue
            facts, failure, exclusion = (
                _generic_missionless_native_playback_facts(
                    story_key,
                    occurrences,
                )
            )
            if failure is not None:
                missionless_native_validation_failures.append(failure)
                missionless_native_exclusions["validationFailure"].append(
                    story_key
                )
                continue
            if facts is None:
                missionless_native_exclusions[
                    exclusion or "notQualified"
                ].append(story_key)
                continue
            missionless_native_evidence_by_key[story_key] = {
                "sceneKey": story_key,
                "missionId": next(iter(missions)),
                "recoveryStatus":
                    "deferred_exact_native_playback_without_mission_bridge",
                "evidenceKind":
                    "exact_missionless_native_event_playback_path",
                **facts,
                "originalBinaryFiles": [
                    source_display_path(source_paths["gameAssembly"]),
                ],
                "gameAssemblySha256": actual_hashes.get(
                    "gameAssembly", ""
                ),
                "playbackStatus": "exact_local_event_to_typed_action",
                "missionOwnership": False,
                "activationBoundary": (
                    "the current-build binary mapping and serialized "
                    "LevelScript prove the complete local event-to-playback "
                    "path, but this decoded event carries no mission/quest id "
                    "or server exchange; attachment as an unresolved mission "
                    "gap is admitted only when the mission flow has no "
                    "separate routed bridge for the Story key"
                ),
                "orderBoundary": (
                    "trigger-slot values, local ids, action-list positions, "
                    "source-file order, filename suffixes, OCR, and manual "
                    "display order do not place this playback relative to "
                    "other mission Story files"
                ),
                "reopenWhen": (
                    "LevelData, MissionRuntime, a receiver registry, or "
                    "another exact original-data source links this script or "
                    "trigger to a mission/quest, or any hashed source changes"
                ),
                "graphEffect": "none",
            }

    if native_playback_index is not None:
        for story_key, missions in sorted(
            core_targets.items(),
            key=lambda item: natural_key(item[0]),
        ):
            if not story_key.startswith("radio_"):
                continue
            if story_key in all_radio_keys:
                generic_radio_exclusions["declaredSpecialCase"].append(
                    story_key
                )
                continue
            if len(missions) != 1:
                generic_radio_exclusions["ambiguousMission"].append(story_key)
                continue
            if (native_playback_index.get(story_key) or []):
                generic_radio_exclusions["nativePlayback"].append(story_key)
                continue
            if story_key not in no_candidate_keys:
                generic_radio_exclusions["typedObjectCarrier"].append(
                    story_key
                )
                continue
            facts, failure = _generic_radio_definition_facts(
                story_key,
                radio_table.get(story_key)
                if isinstance(radio_table, dict) else None,
                audio_stems,
            )
            if failure is not None:
                failure["sourcePaths"] = [
                    str(source_paths["radioTable"]),
                    str(source_paths["audioDialog"]),
                ]
                failure["sourceSha256"] = {
                    "radioTable": actual_hashes.get("radioTable", ""),
                    "audioDialog": actual_hashes.get("audioDialog", ""),
                }
                generic_radio_validation_failures.append(failure)
                generic_radio_exclusions["invalidDefinition"].append(
                    story_key
                )
                continue
            if facts is not None:
                generic_radio_definition_facts[story_key] = facts

        generic_literals = {
            story_key: story_key
            for story_key in generic_radio_definition_facts
        }
        game_assembly_present = (
            _present_literal_keys(
                game_assembly_bytes,
                generic_literals,
                "utf-8",
            )
            | _present_literal_keys(
                game_assembly_bytes,
                generic_literals,
                "utf-16le",
            )
        )
        metadata_present = (
            _present_literal_keys(
                global_metadata_bytes,
                generic_literals,
                "utf-8",
            )
            | _present_literal_keys(
                global_metadata_bytes,
                generic_literals,
                "utf-16le",
            )
        )
        binary_present = game_assembly_present | metadata_present
        generic_radio_exclusions["binaryRootTokenPresent"] = sorted(
            binary_present,
            key=natural_key,
        )

        for story_key, facts in sorted(
            generic_radio_definition_facts.items(),
            key=lambda item: natural_key(item[0]),
        ):
            if story_key in binary_present:
                continue
            mission_id = next(iter(core_targets[story_key]))
            generic_radio_evidence_by_key[story_key] = {
                "sceneKey": story_key,
                "missionId": mission_id,
                "recoveryStatus":
                    "deferred_current_build_offline_surface_exhausted",
                "evidenceKind":
                    "radio_definition_binary_consumer_surface_exhausted",
                "definitionTable": "RadioTable",
                "definitionSourceFiles": [
                    source_display_path(source_paths["radioTable"]),
                    source_display_path(source_paths["audioDialog"]),
                ],
                "sourceFiles": [
                    source_display_path(carrier_audit_path),
                ],
                "originalBinaryFiles": [
                    source_display_path(source_paths["gameAssembly"]),
                    source_display_path(source_paths["globalMetadata"]),
                ],
                **facts,
                "carrierAuditStatus":
                    "no_typed_story_owner_or_runtime_carrier",
                "carrierAuditTargetSetSha256": core_target_digest,
                "binaryRootTokenStatus":
                    "absent_utf8_and_utf16le_in_current_game_binaries",
                "nativeMappingId": OFFLINE_EXHAUSTION_MAPPING_ID,
                "gameAssemblySha256":
                    OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
                "globalMetadataSha256": OFFLINE_EXHAUSTION_METADATA_SHA256,
                "searchedConsumerKinds": [
                    "MissionRuntime Story routes",
                    "typed LevelScript playback actions",
                    "GameplayConfig Story routes",
                    "missionless native playback receivers",
                    "typed AnimeStudio owner/runtime object carriers",
                    "GameAssembly exact UTF-8/UTF-16 root tokens",
                    "global-metadata exact UTF-8/UTF-16 root tokens",
                ],
                "consumerBoundary": (
                    "the exact current RadioTable definition survives, but "
                    "the complete generated Story-route census, typed native "
                    "LevelScript playback index, hash-matched AnimeStudio "
                    "object index, current GameAssembly, and current global "
                    "metadata expose no playback consumer or owner carrier"
                ),
                "orderBoundary": (
                    "RadioTable row order, line indices, filename suffixes, "
                    "audio membership, OCR, and manual display order do not "
                    "establish playback or relative Story chronology"
                ),
                "reopenWhen": (
                    "the installed binary, exported tables, generated route "
                    "census, object index, or another typed producer/consumer "
                    "registry changes"
                ),
                "graphEffect": "none",
            }

    generic_npc_proxy_evidence_by_key: dict[str, dict[str, Any]] = {}
    generic_npc_proxy_validation_failures: list[dict[str, Any]] = []
    generic_npc_proxy_exclusions: dict[str, list[str]] = {
        "ambiguousMission": [],
        "nativePlayback": [],
        "typedObjectCarrier": [],
        "noMissionlessProxyConsumer": [],
        "invalidConsumer": [],
        "invalidMissionTracking": [],
    }
    npc_proxy_ex_for_generic = read_json(
        source_paths["npcProxyExDataTable"],
        {},
    )
    npc_proxy_for_generic = read_json(source_paths["npcProxyTable"], {})
    dialog_id_index_for_generic = read_json(
        source_paths["dialogIdIndex"],
        {},
    )
    mission_tracking_corpus = _build_mission_npc_proxy_tracking_index(
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
    generic_mission_tracking_validation_failures = list(
        mission_tracking_corpus.get("scanFailures") or []
    )
    if native_playback_index is not None:
        for story_key, missions in sorted(
            core_targets.items(),
            key=lambda item: natural_key(item[0]),
        ):
            if not (
                story_key.startswith("dlg_")
                or story_key.startswith("misc_dlg_")
            ):
                continue
            if len(missions) != 1:
                generic_npc_proxy_exclusions["ambiguousMission"].append(
                    story_key
                )
                continue
            if native_playback_index.get(story_key) or []:
                generic_npc_proxy_exclusions["nativePlayback"].append(
                    story_key
                )
                continue
            if story_key not in no_candidate_keys:
                generic_npc_proxy_exclusions["typedObjectCarrier"].append(
                    story_key
                )
                continue
            facts, failure = _generic_missionless_npc_proxy_dialog_facts(
                story_key,
                npc_proxy_ex_for_generic,
                npc_proxy_for_generic,
                dialog_id_index_for_generic,
            )
            if failure is not None:
                failure["sourcePaths"] = [
                    str(source_paths["npcProxyExDataTable"]),
                    str(source_paths["npcProxyTable"]),
                    str(source_paths["dialogIdIndex"]),
                ]
                failure["sourceSha256"] = {
                    name: actual_hashes.get(name, "")
                    for name in (
                        "npcProxyExDataTable",
                        "npcProxyTable",
                        "dialogIdIndex",
                    )
                }
                generic_npc_proxy_validation_failures.append(failure)
                generic_npc_proxy_exclusions["invalidConsumer"].append(
                    story_key
                )
                continue
            if facts is None:
                generic_npc_proxy_exclusions[
                    "noMissionlessProxyConsumer"
                ].append(story_key)
                continue
            mission_id = next(iter(missions))
            tracking_contexts, tracking_failures = (
                _generic_mission_npc_proxy_tracking_contexts(
                    story_key,
                    mission_id,
                    facts,
                    mission_tracking_corpus,
                )
            )
            if tracking_failures:
                generic_mission_tracking_validation_failures.extend(
                    tracking_failures
                )
                generic_npc_proxy_exclusions[
                    "invalidMissionTracking"
                ].append(story_key)
            tracking_source_files = list(dict.fromkeys(
                source_file
                for context in tracking_contexts
                for source_file in context.get("sourceFiles") or []
            ))
            generic_npc_proxy_evidence_by_key[story_key] = {
                "sceneKey": story_key,
                "missionId": mission_id,
                "recoveryStatus":
                    "deferred_current_build_offline_surface_exhausted",
                "evidenceKind":
                    (
                        "mission_tracked_npc_proxy_dialog_context_without_playback_owner"
                        if tracking_contexts else
                        "missionless_npc_proxy_dialog_native_consumer"
                    ),
                "definitionTable": "NpcProxyExDataTable",
                "definitionSourceFiles": [
                    source_display_path(source_paths["npcProxyExDataTable"]),
                    source_display_path(source_paths["npcProxyTable"]),
                    source_display_path(source_paths["dialogIdIndex"]),
                ],
                "sourceFiles": [
                    source_display_path(carrier_audit_path),
                    *tracking_source_files,
                ],
                "originalBinaryFiles": [
                    source_display_path(source_paths["gameAssembly"]),
                ],
                **facts,
                "missionNpcProxyTracking": (
                    tracking_contexts[0]
                    if len(tracking_contexts) == 1 else None
                ),
                "missionNpcProxyTrackingContexts": tracking_contexts,
                "carrierAuditStatus":
                    "no_typed_story_owner_or_runtime_carrier",
                "carrierAuditTargetSetSha256": core_target_digest,
                "nativeMappingId": NPC_PROXY_DIALOG_SELECTION_MAPPING_ID,
                "gameAssemblySha256":
                    NPC_PROXY_DIALOG_SELECTION_GAMEASSEMBLY_SHA256,
                "nativeConsumerMethods": [{
                    "method": (
                        "Beyond.Gameplay.NpcInteractComponent."
                        "_TryGetNpcProxyInteractDialogId"
                    ),
                    "token": "0x06011381",
                    "address": "0x183564080",
                    "selectionField": "activeCondIndex",
                }],
                "searchedConsumerKinds": [
                    "exact NpcProxyExDataTable dialog selectors",
                    "exact NpcProxyTable proxy identities",
                    "MemoryPack DialogId registrations",
                    "typed native LevelScript playback actions",
                    "typed AnimeStudio owner/runtime object carriers",
                ],
                "consumerBoundary": (
                    "the hash-locked native NPC interaction method selects "
                    "the active NpcProxyEx row's exact dialogId; these "
                    "missionless rows therefore prove runtime consumption, "
                    "but expose no mission activator"
                ),
                "orderBoundary": (
                    "activeCondIndex, proxy table order, world registration, "
                    "filename suffixes, OCR, and manual display order do not "
                    "establish activation or relative Story chronology"
                ),
                "reopenWhen": (
                    "the installed binary, NpcProxy tables, DialogId "
                    "registry, carrier audit, or typed playback index changes"
                ),
                "graphEffect": "none",
            }

    generic_sns_evidence_by_key: dict[str, dict[str, Any]] = {}
    generic_sns_validation_failures: list[dict[str, Any]] = []
    generic_sns_exclusions: dict[str, list[str]] = {
        "declaredSpecialCase": [],
        "ambiguousMission": [],
        "nativePlayback": [],
        "typedObjectCarrier": [],
        "authoredMissionLink": [],
        "binaryRootTokenPresent": [],
        "invalidDefinition": [],
    }
    sns_dialog_for_generic = read_json(source_paths["snsDialogTable"], {})
    sns_option_for_generic = read_json(source_paths["snsOptionTable"], {})
    sns_chat_for_generic = read_json(source_paths["snsChatTable"], {})
    generic_sns_definition_facts: dict[str, dict[str, Any]] = {}
    if native_playback_index is not None:
        for story_key, missions in sorted(
            core_targets.items(),
            key=lambda item: natural_key(item[0]),
        ):
            # Candidate identity comes from an exact SNSDialogTable row, not
            # from a filename prefix. Shipped UI fixtures and future authored
            # SNS families may use other namespaces.
            if not _is_authored_sns_definition_candidate(
                story_key,
                sns_dialog_for_generic,
            ):
                continue
            if story_key in all_sns_keys:
                generic_sns_exclusions["declaredSpecialCase"].append(
                    story_key
                )
                continue
            if len(missions) != 1:
                generic_sns_exclusions["ambiguousMission"].append(story_key)
                continue
            if native_playback_index.get(story_key) or []:
                generic_sns_exclusions["nativePlayback"].append(story_key)
                continue
            if story_key not in no_candidate_keys:
                generic_sns_exclusions["typedObjectCarrier"].append(story_key)
                continue
            facts, failure, exclusion = _generic_unlinked_sns_definition_facts(
                story_key,
                sns_dialog_for_generic.get(story_key)
                if isinstance(sns_dialog_for_generic, dict) else None,
                sns_option_for_generic,
                sns_chat_for_generic,
            )
            if exclusion:
                generic_sns_exclusions[exclusion].append(story_key)
                if exclusion == "authoredMissionLink" and facts is not None:
                    mission_id = next(iter(missions))
                    generic_sns_evidence_by_key[story_key] = {
                        "sceneKey": story_key,
                        "missionId": mission_id,
                        "recoveryStatus": (
                            "deferred_exact_authored_sns_mission_link"
                        ),
                        "evidenceKind": "sns_authored_mission_link",
                        "definitionTable": "SNSDialogTable",
                        "definitionTables": [
                            "SNSDialogTable",
                            "SNSDialogOptionTable",
                        ],
                        "definitionSourceFiles": [
                            source_display_path(
                                source_paths["snsDialogTable"]
                            ),
                            source_display_path(
                                source_paths["snsOptionTable"]
                            ),
                            source_display_path(
                                source_paths["snsChatTable"]
                            ),
                        ],
                        **facts,
                        "consumerBoundary": (
                            "the exact SNSDialogTable relatedMissionId and "
                            "type-12 linkMissionId/contentParam triple attach "
                            "this SNS definition to the same mission"
                        ),
                        "orderBoundary": (
                            "the authored mission link is navigation context, "
                            "not a playback activator; the internal SNS graph "
                            "orders messages only"
                        ),
                        "reopenWhen": (
                            "SNSDialogTable, SNSDialogOptionTable, SNSChatTable, "
                            "or the generated authored-link relation changes"
                        ),
                        "graphEffect": "none",
                    }
                continue
            if failure is not None:
                failure["sourcePaths"] = [
                    str(source_paths["snsDialogTable"]),
                    str(source_paths["snsOptionTable"]),
                    str(source_paths["snsChatTable"]),
                ]
                failure["sourceSha256"] = {
                    name: actual_hashes.get(name, "")
                    for name in (
                        "snsDialogTable", "snsOptionTable", "snsChatTable"
                    )
                }
                generic_sns_validation_failures.append(failure)
                generic_sns_exclusions["invalidDefinition"].append(story_key)
                continue
            if facts is not None:
                generic_sns_definition_facts[story_key] = facts
        sns_literals = {
            story_key: story_key
            for story_key in generic_sns_definition_facts
        }
        sns_binary_present = (
            _present_literal_keys(game_assembly_bytes, sns_literals, "utf-8")
            | _present_literal_keys(
                game_assembly_bytes, sns_literals, "utf-16le"
            )
            | _present_literal_keys(
                global_metadata_bytes, sns_literals, "utf-8"
            )
            | _present_literal_keys(
                global_metadata_bytes, sns_literals, "utf-16le"
            )
        )
        generic_sns_exclusions["binaryRootTokenPresent"] = sorted(
            sns_binary_present,
            key=natural_key,
        )
        for story_key, facts in sorted(
            generic_sns_definition_facts.items(),
            key=lambda item: natural_key(item[0]),
        ):
            if story_key in sns_binary_present:
                continue
            generic_sns_evidence_by_key[story_key] = {
                "sceneKey": story_key,
                "missionId": next(iter(core_targets[story_key])),
                "recoveryStatus":
                    "deferred_current_build_offline_surface_exhausted",
                "evidenceKind":
                    "sns_definition_binary_consumer_surface_exhausted",
                "storyKind": "sns",
                "definitionTable": "SNSDialogTable",
                "definitionSourceFiles": [
                    source_display_path(source_paths["snsDialogTable"]),
                    source_display_path(source_paths["snsOptionTable"]),
                    source_display_path(source_paths["snsChatTable"]),
                ],
                "sourceFiles": [source_display_path(carrier_audit_path)],
                "originalBinaryFiles": [
                    source_display_path(source_paths["gameAssembly"]),
                    source_display_path(source_paths["globalMetadata"]),
                ],
                **facts,
                "carrierAuditStatus":
                    "no_typed_story_owner_or_runtime_carrier",
                "carrierAuditTargetSetSha256": core_target_digest,
                "binaryRootTokenStatus":
                    "absent_utf8_and_utf16le_in_current_game_binaries",
                "nativeMappingId": OFFLINE_EXHAUSTION_MAPPING_ID,
                "gameAssemblySha256":
                    OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
                "globalMetadataSha256": OFFLINE_EXHAUSTION_METADATA_SHA256,
                "searchedConsumerKinds": [
                    "authored SNS relatedMissionId/linkMissionId fields",
                    "MissionRuntime Story routes",
                    "typed native LevelScript playback actions",
                    "typed AnimeStudio owner/runtime object carriers",
                    "GameAssembly exact UTF-8/UTF-16 root tokens",
                    "global-metadata exact UTF-8/UTF-16 root tokens",
                ],
                "consumerBoundary": (
                    "the exact SNS dialog and chat definitions survive, but "
                    "their authored mission links are empty and the complete "
                    "typed route, native playback, object-carrier, and "
                    "current-binary token surfaces expose no consumer"
                ),
                "orderBoundary": (
                    "SNS content links describe only the internal message "
                    "graph; content ids, table order, filename suffixes, OCR, "
                    "and manual display order do not establish mission "
                    "activation or relative Story chronology"
                ),
                "reopenWhen": (
                    "the installed binary, SNS tables, generated route "
                    "census, object index, or another typed consumer changes"
                ),
                "graphEffect": "none",
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

    unhosted_reading_popup_receivers = (
        build_levelscript_unhosted_reading_popup_receiver_index(
            all_text_keys,
            reading_popup_path=source_paths["readingPopupTable"],
        )
    )

    generic_text_evidence_by_key: dict[str, dict[str, Any]] = {}
    generic_text_validation_failures: list[dict[str, Any]] = []
    generic_text_exclusions: dict[str, list[str]] = {
        "declaredSpecialCase": [],
        "ambiguousMission": [],
        "nativePlayback": [],
        "typedObjectCarrier": [],
        "dialogRegistry": [],
        "timelineRegistration": [],
        "textAssetCarrier": [],
        "missingPopupDefinition": [],
        "binaryRootTokenPresent": [],
        "invalidDefinition": [],
    }
    popup_rows_by_content_id: dict[str, dict[str, dict[str, Any]]] = (
        defaultdict(dict)
    )
    for popup_row_id, popup_row in reading_popup_table.items():
        content_id = (
            safe_key(popup_row.get("contentId"))
            if isinstance(popup_row, dict) else ""
        )
        if content_id:
            popup_rows_by_content_id[content_id][popup_row_id] = popup_row
    timeline_line_orders_for_generic = read_json(
        source_paths["timelineLineOrders"],
        {},
    )
    generic_text_definition_facts: dict[str, dict[str, Any]] = {}
    if native_playback_index is not None:
        for story_key, missions in sorted(
            core_targets.items(),
            key=lambda item: natural_key(item[0]),
        ):
            if not story_key.startswith("text_"):
                continue
            if story_key in all_text_keys:
                generic_text_exclusions["declaredSpecialCase"].append(
                    story_key
                )
                continue
            if len(missions) != 1:
                generic_text_exclusions["ambiguousMission"].append(
                    story_key
                )
                continue
            if native_playback_index.get(story_key) or []:
                generic_text_exclusions["nativePlayback"].append(story_key)
                continue
            if story_key not in no_candidate_keys:
                generic_text_exclusions["typedObjectCarrier"].append(
                    story_key
                )
                continue
            if (
                isinstance(dialog_id_index_for_generic, dict)
                and story_key in dialog_id_index_for_generic
            ):
                generic_text_exclusions["dialogRegistry"].append(story_key)
                continue
            if (
                isinstance(timeline_line_orders_for_generic, dict)
                and story_key in timeline_line_orders_for_generic
            ):
                generic_text_exclusions["timelineRegistration"].append(
                    story_key
                )
                continue
            text_assets = sorted(
                cutscene_definition_root.glob(f"{story_key}_p*.json")
            )
            if text_assets:
                generic_text_exclusions["textAssetCarrier"].append(story_key)
                continue
            popup_rows = popup_rows_by_content_id.get(story_key) or {}
            if not popup_rows:
                generic_text_exclusions["missingPopupDefinition"].append(
                    story_key
                )
                continue
            facts, failure = _generic_reading_popup_definition_facts(
                story_key,
                popup_rows,
                rich_content_table.get(story_key),
            )
            if failure is not None:
                failure["sourcePaths"] = [
                    str(source_paths["readingPopupTable"]),
                    str(source_paths["richContentTable"]),
                ]
                failure["sourceSha256"] = {
                    name: actual_hashes.get(name, "")
                    for name in ("readingPopupTable", "richContentTable")
                }
                generic_text_validation_failures.append(failure)
                generic_text_exclusions["invalidDefinition"].append(
                    story_key
                )
                continue
            if facts is not None:
                generic_text_definition_facts[story_key] = facts

        generic_text_literals = {
            story_key: story_key
            for story_key in generic_text_definition_facts
        }
        generic_text_binary_present = (
            _present_literal_keys(
                game_assembly_bytes,
                generic_text_literals,
                "utf-8",
            )
            | _present_literal_keys(
                game_assembly_bytes,
                generic_text_literals,
                "utf-16le",
            )
            | _present_literal_keys(
                global_metadata_bytes,
                generic_text_literals,
                "utf-8",
            )
            | _present_literal_keys(
                global_metadata_bytes,
                generic_text_literals,
                "utf-16le",
            )
        )
        generic_text_exclusions["binaryRootTokenPresent"] = sorted(
            generic_text_binary_present,
            key=natural_key,
        )
        for story_key, facts in sorted(
            generic_text_definition_facts.items(),
            key=lambda item: natural_key(item[0]),
        ):
            if story_key in generic_text_binary_present:
                continue
            mission_id = next(iter(core_targets[story_key]))
            generic_text_evidence_by_key[story_key] = {
                "sceneKey": story_key,
                "missionId": mission_id,
                "recoveryStatus":
                    "deferred_current_build_offline_surface_exhausted",
                "evidenceKind":
                    "reading_popup_definition_binary_consumer_surface_exhausted",
                "definitionTables": [
                    "ReadingPopUpTable",
                    "RichContentTable",
                ],
                "definitionSourceFiles": [
                    source_display_path(source_paths["readingPopupTable"]),
                    source_display_path(source_paths["richContentTable"]),
                ],
                "sourceFiles": [source_display_path(carrier_audit_path)],
                "originalBinaryFiles": [
                    source_display_path(source_paths["gameAssembly"]),
                    source_display_path(source_paths["globalMetadata"]),
                ],
                **facts,
                "carrierAuditStatus":
                    "no_typed_story_owner_or_runtime_carrier",
                "carrierAuditTargetSetSha256": core_target_digest,
                "binaryRootTokenStatus":
                    "absent_utf8_and_utf16le_in_current_game_binaries",
                "nativeMappingId": OFFLINE_EXHAUSTION_MAPPING_ID,
                "gameAssemblySha256": OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
                "globalMetadataSha256": OFFLINE_EXHAUSTION_METADATA_SHA256,
                "searchedConsumerKinds": [
                    "MissionRuntime Story routes",
                    "typed LevelScript playback actions",
                    "GameplayConfig Story routes",
                    "DialogId and Timeline registries",
                    "typed AnimeStudio owner/runtime object carriers",
                    "GameAssembly exact UTF-8/UTF-16 root tokens",
                    "global-metadata exact UTF-8/UTF-16 root tokens",
                ],
                "consumerBoundary": (
                    "the exact current ReadingPopUpTable carrier and "
                    "RichContentTable payload define this readable Story "
                    "object, but the complete generated Story-route census, "
                    "typed native playback index, DialogId/Timeline "
                    "registries, hash-matched AnimeStudio object index, "
                    "current GameAssembly, and current global metadata "
                    "expose no activator or owner carrier"
                ),
                "orderBoundary": (
                    "popup row order, content-node order, text ids, filename "
                    "suffixes, OCR, and manual display order do not establish "
                    "mission activation or relative Story chronology"
                ),
                "reopenWhen": (
                    "the installed binary, exported tables, generated route "
                    "census, object index, or another typed producer/consumer "
                    "registry changes"
                ),
                "graphEffect": "none",
            }

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
        link_mission_ids_by_content_id = (
            definition.get("linkMissionIdsByContentId") or {}
        )
        expected_related_mission_id = safe_key(
            definition.get("relatedMissionId")
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
            or dialog.get("relatedMissionId")
            != expected_related_mission_id
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
                    "relatedMissionId": expected_related_mission_id,
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
                    "relatedMissionId": (
                        dialog.get("relatedMissionId")
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
                or node.get("linkMissionId")
                != link_mission_ids_by_content_id.get(content_id, "")
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
                        "linkMissionId":
                            link_mission_ids_by_content_id.get(
                                content_id,
                                "",
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
            "relatedMissionId": expected_related_mission_id,
            "linkMissionIdsByContentId": {
                str(content_id): mission_id
                for content_id, mission_id
                in link_mission_ids_by_content_id.items()
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
    dialog_summary_map_table = read_json(
        source_paths["dialogSummaryMapTable"],
        {},
    )
    dialog_summary_table = read_json(source_paths["dialogSummaryTable"], {})
    dialog_id_index = read_json(source_paths["dialogIdIndex"], {})
    timeline_line_orders = read_json(source_paths["timelineLineOrders"], {})
    npc_proxy_ex_table = read_json(
        source_paths["npcProxyExDataTable"],
        {},
    )
    npc_proxy_table = read_json(source_paths["npcProxyTable"], {})
    dialog_validation_by_key: dict[str, dict[str, Any]] = {}
    dialog_validation_failures: list[dict[str, Any]] = []
    dialog_definitions_valid = (
        isinstance(dialog_text_table, dict)
        and isinstance(dialog_id_index, dict)
        and isinstance(timeline_line_orders, dict)
        and isinstance(npc_proxy_ex_table, dict)
    )
    for story_key, definition in (
        dialog_context_definitions.items()
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
        npc_proxy_facts, npc_proxy_failure = (
            _generic_missionless_npc_proxy_dialog_facts(
                story_key,
                npc_proxy_ex_table,
                npc_proxy_table,
                dialog_id_index,
            )
        )
        npc_proxy_consumer_valid = npc_proxy_failure is None
        npc_proxy_consumer_contexts = [
            {
                "proxyId": safe_key(row.get("npcProxyId")),
                "entryIndex": row.get("activeRowIndex"),
                "dialogId": registry_key,
                "missionId": "",
                "levelId": safe_key(row.get("levelId")),
                "npcId": safe_key(row.get("npcId")),
                "npcNameId": safe_key(row.get("npcNameId")),
                "mapId": safe_key(row.get("mapId")),
                "relation": "npc_proxy_ex_dialog_consumer_without_mission_id",
                "missionOwnership": False,
                "orderEvidence": False,
                "graphEffect": "none",
            }
            for row in (
                npc_proxy_facts.get("npcProxyConsumers")
                if isinstance(npc_proxy_facts, dict)
                else []
            )
            if isinstance(row, dict)
        ]
        npc_proxy_consumer_context = (
            npc_proxy_consumer_contexts[0]
            if len(npc_proxy_consumer_contexts) == 1
            else None
        )
        mission_tracking_contexts, tracking_failures = (
            _generic_mission_npc_proxy_tracking_contexts(
                story_key,
                safe_key(definition.get("missionId")),
                npc_proxy_facts,
                mission_tracking_corpus,
            )
        )
        if tracking_failures:
            generic_mission_tracking_validation_failures.extend(
                tracking_failures
            )
        mission_tracking_context = (
            mission_tracking_contexts[0]
            if len(mission_tracking_contexts) == 1 else None
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
                    *(
                        (
                            str(source_paths["npcProxyExDataTable"]),
                            str(source_paths["npcProxyTable"]),
                        )
                        if npc_proxy_failure is not None else ()
                    ),
                ],
                "sourceSha256": {
                    name: actual_hashes.get(name, "")
                    for name in (
                        "dialogTextTable",
                        "dialogIdIndex",
                        "audioDialog",
                        *(
                            ("npcProxyExDataTable", "npcProxyTable")
                            if npc_proxy_failure is not None else ()
                        ),
                    )
                },
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
                    "npcProxyConsumerFailure": npc_proxy_failure,
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
            "missionNpcProxyTrackingContexts": mission_tracking_contexts,
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
        definition_root_key = (
            safe_key(definition.get("definitionRootKey")) or story_key
        )
        expected_line_ids = tuple(definition["lineIds"])
        actual_line_ids = tuple(sorted(
            key
            for key in dialog_text_table
            if key.startswith(f"{definition_root_key}_")
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
            if key.startswith(f"option_{definition_root_key}_")
        )) if isinstance(dialog_option_table, dict) else ()
        expected_option_ids = tuple(sorted(
            expected_option_rows or {}
        ))
        cutscene_matches = sorted(
            str(path.relative_to(ROOT)).replace("\\", "/")
            for path in cutscene_definition_root.glob(
                f"{definition_root_key}_p*.json"
            )
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
        registry = dialog_id_index.get(definition_root_key)
        printable_only_tokens = tuple(
            definition.get("printableOnlyDialogTokens") or ()
        )
        if expected_registration_status == "present_table_only":
            expected_options_by_group: dict[str, list[str]] = defaultdict(list)
            option_prefix = f"option_{definition_root_key}_"
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
        timeline_registration_keys = {
            key for key in (story_key, definition_root_key) if key
        }
        registered_timeline_rows = {
            key: timeline_line_orders[key]
            for key in timeline_registration_keys
            if key in timeline_line_orders
        }
        if registered_timeline_rows:
            add_text_only_failure(
                "timelineRegistrationAbsent",
                ("timelineLineOrders",),
                {"present": False},
                {"present": True, "rows": registered_timeline_rows},
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
        summary_definition = definition.get("summaryDefinition")
        if summary_definition is not None:
            expected_summary_id = summary_definition["summaryId"]
            actual_summary_id = (
                dialog_summary_map_table.get(definition_root_key)
                if isinstance(dialog_summary_map_table, dict)
                else None
            )
            actual_summary_row = (
                dialog_summary_table.get(expected_summary_id)
                if isinstance(dialog_summary_table, dict)
                else None
            )
            if (
                actual_summary_id != expected_summary_id
                or actual_summary_row != summary_definition["row"]
            ):
                add_text_only_failure(
                    "exactDialogSummaryDefinition",
                    ("dialogSummaryMapTable", "dialogSummaryTable"),
                    {
                        "summaryId": expected_summary_id,
                        "row": summary_definition["row"],
                    },
                    {
                        "summaryId": actual_summary_id,
                        "row": actual_summary_row,
                    },
                )
        if len(text_only_dialog_validation_failures) != failures_before:
            continue
        text_only_dialog_validation_by_key[story_key] = {
            "definitionRootKey": definition_root_key,
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
            "summaryDefinition": (
                {
                    "summaryId": summary_definition["summaryId"],
                    "textId": str(summary_definition["row"]["id"]),
                    "relation": "dialog_summary_map_targets_dialog",
                    "missionOwnership": False,
                    "orderEvidence": False,
                }
                if summary_definition else None
            ),
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

    generic_dialog_evidence_by_key: dict[str, dict[str, Any]] = {}
    generic_dialog_validation_failures: list[dict[str, Any]] = []
    generic_dialog_exclusions: dict[str, list[str]] = {
        "declaredSpecialCase": [],
        "ambiguousMission": [],
        "nativePlayback": [],
        "typedLevelScriptAction": [],
        "typedObjectCarrier": [],
        "dialogRegistry": [],
        "timelineRegistration": [],
        "textAssetCarrier": [],
        "missingDialogTextDefinition": [],
        "binaryRootTokenPresent": [],
        "invalidDefinition": [],
    }
    declared_dialog_keys = set(all_dialog_mission_by_key)
    # Decode the registered DialogTree corpus once and index exact authored
    # line identities. A table group is not "unregistered" merely because its
    # runtime parent has a different root name such as ``dlg_gpl_*``.
    registered_dialog_tree_definitions_by_root = {
        dialog_key: definition
        for dialog_key in sorted(dialog_id_index, key=natural_key)
        if isinstance(
            definition := recover_dialog_tree_definition_evidence(dialog_key),
            dict,
        )
    } if isinstance(dialog_id_index, dict) else {}
    registered_dialog_tree_carriers_by_line: dict[str, list[str]] = defaultdict(list)
    for parent_key, definition in (
        registered_dialog_tree_definitions_by_root.items()
    ):
        for line_id in _string_list(definition.get("lineIds")):
            registered_dialog_tree_carriers_by_line[line_id].append(parent_key)
    generic_dialog_definition_facts: dict[str, dict[str, Any]] = {}
    generic_dialog_line_carriers_by_key: dict[str, list[dict[str, Any]]] = {}
    if native_playback_index is not None and action_story_occurrences is not None:
        for story_key, missions in sorted(
            core_targets.items(),
            key=lambda item: natural_key(item[0]),
        ):
            if not (
                story_key.startswith("dlg_")
                or story_key.startswith("misc_dlg_")
            ):
                continue
            definition_root_key = (
                story_key.removeprefix("misc_")
                if story_key.startswith("misc_dlg_")
                else story_key
            )
            authored_keys = tuple(dict.fromkeys((story_key, definition_root_key)))
            if any(key in declared_dialog_keys for key in authored_keys):
                generic_dialog_exclusions["declaredSpecialCase"].append(
                    story_key
                )
                continue
            if len(missions) != 1:
                generic_dialog_exclusions["ambiguousMission"].append(
                    story_key
                )
                continue
            if any(native_playback_index.get(key) for key in authored_keys):
                generic_dialog_exclusions["nativePlayback"].append(story_key)
                continue
            if any(action_story_occurrences.get(key) for key in authored_keys):
                generic_dialog_exclusions["typedLevelScriptAction"].append(
                    story_key
                )
                continue
            if story_key not in no_candidate_keys:
                generic_dialog_exclusions["typedObjectCarrier"].append(
                    story_key
                )
                continue
            if any(key in dialog_id_index for key in authored_keys):
                generic_dialog_exclusions["dialogRegistry"].append(story_key)
                continue
            if any(key in timeline_line_orders for key in authored_keys):
                generic_dialog_exclusions["timelineRegistration"].append(
                    story_key
                )
                continue
            line_pattern = re.compile(
                rf"^{re.escape(definition_root_key)}_\d+$"
            )
            candidate_line_ids = sorted(
                (
                    line_id
                    for line_id in dialog_text_table
                    if line_pattern.fullmatch(line_id)
                ),
                key=natural_key,
            )
            line_carrier_keys = sorted({
                parent_key
                for line_id in candidate_line_ids
                for parent_key in (
                    registered_dialog_tree_carriers_by_line.get(line_id) or []
                )
            }, key=natural_key)
            text_assets = sorted({
                path
                for key in authored_keys
                for path in cutscene_definition_root.glob(f"{key}_p*.json")
                if "_extra_config_p" not in path.name
            })
            if text_assets:
                generic_dialog_exclusions["textAssetCarrier"].append(
                    story_key
                )
                continue
            if not candidate_line_ids:
                generic_dialog_exclusions[
                    "missingDialogTextDefinition"
                ].append(story_key)
                continue
            facts, failure = _generic_unregistered_dialog_definition_facts(
                story_key,
                dialog_text_table,
                dialog_option_table,
                audio_stems,
                definition_root_key=definition_root_key,
            )
            if failure is not None:
                failure["sourcePaths"] = [
                    str(source_paths["dialogTextTable"]),
                    str(source_paths["dialogOptionTable"]),
                    str(source_paths["audioDialog"]),
                ]
                failure["sourceSha256"] = {
                    name: actual_hashes.get(name, "")
                    for name in (
                        "dialogTextTable",
                        "dialogOptionTable",
                        "audioDialog",
                    )
                }
                generic_dialog_validation_failures.append(failure)
                generic_dialog_exclusions["invalidDefinition"].append(
                    story_key
                )
                continue
            if facts is not None:
                generic_dialog_definition_facts[story_key] = facts
                generic_dialog_line_carriers_by_key[story_key] = [
                    {
                        "sceneKey": parent_key,
                        "lineIds": sorted(
                            set(candidate_line_ids)
                            & set(_string_list(
                                registered_dialog_tree_definitions_by_root[
                                    parent_key
                                ].get("lineIds")
                            )),
                            key=natural_key,
                        ),
                        "sourceFile": safe_key(
                            registered_dialog_tree_definitions_by_root[
                                parent_key
                            ].get("sourceFile")
                        ),
                        "sourceSha256": safe_key(
                            registered_dialog_tree_definitions_by_root[
                                parent_key
                            ].get("sourceSha256")
                        ),
                        "relation": "exact_dialog_text_row_reuse",
                        "missionOwnership": False,
                        "orderEvidence": False,
                    }
                    for parent_key in line_carrier_keys
                ]

        generic_dialog_binary_present = {
            story_key
            for story_key, facts in generic_dialog_definition_facts.items()
            if any(
                literal.encode(encoding) in payload
                for literal in tuple(dict.fromkeys((
                    story_key,
                    facts["definitionRootKey"],
                )))
                for encoding in ("utf-8", "utf-16le")
                for payload in (game_assembly_bytes, global_metadata_bytes)
            )
        }
        generic_dialog_exclusions["binaryRootTokenPresent"] = sorted(
            generic_dialog_binary_present,
            key=natural_key,
        )
        for story_key, facts in sorted(
            generic_dialog_definition_facts.items(),
            key=lambda item: natural_key(item[0]),
        ):
            if story_key in generic_dialog_binary_present:
                continue
            mission_id = next(iter(core_targets[story_key]))
            line_carriers = generic_dialog_line_carriers_by_key.get(
                story_key,
                [],
            )
            generic_dialog_evidence_by_key[story_key] = {
                "sceneKey": story_key,
                "missionId": mission_id,
                "recoveryStatus":
                    "deferred_current_build_offline_surface_exhausted",
                "evidenceKind": (
                    "dialog_text_rows_reused_by_registered_trees_without_"
                    "emitted_root_consumer"
                    if line_carriers else
                    "unregistered_dialog_definition_binary_consumer_surface_exhausted"
                ),
                "definitionTables": [
                    "DialogTextTable",
                    "DialogOptionTable",
                    "AudioDialog",
                ],
                "definitionSourceFiles": [
                    source_display_path(source_paths["dialogTextTable"]),
                    source_display_path(source_paths["dialogOptionTable"]),
                    source_display_path(source_paths["audioDialog"]),
                ],
                "sourceFiles": [source_display_path(carrier_audit_path)],
                "originalBinaryFiles": [
                    source_display_path(source_paths["gameAssembly"]),
                    source_display_path(source_paths["globalMetadata"]),
                ],
                **facts,
                "dialogIdRegistrationStatus": "absent",
                "dialogTreeAssetStatus": (
                    "exact_line_carriers_present_without_emitted_root"
                    if line_carriers else "absent"
                ),
                "registeredDialogTreeLineCarriers": line_carriers,
                "timelineStatus": "absent",
                "carrierAuditStatus":
                    "no_typed_story_owner_or_runtime_carrier",
                "carrierAuditTargetSetSha256": core_target_digest,
                "binaryRootTokenStatus":
                    "absent_utf8_and_utf16le_in_current_game_binaries",
                "nativeMappingId": OFFLINE_EXHAUSTION_MAPPING_ID,
                "gameAssemblySha256": OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
                "globalMetadataSha256": OFFLINE_EXHAUSTION_METADATA_SHA256,
                "searchedConsumerKinds": [
                    "MissionRuntime Story routes",
                    "typed LevelScript playback actions",
                    "GameplayConfig Story routes",
                    "DialogId and Timeline registries",
                    "typed DialogTree/TextAsset definitions",
                    "typed AnimeStudio owner/runtime object carriers",
                    "GameAssembly exact UTF-8/UTF-16 root tokens",
                    "global-metadata exact UTF-8/UTF-16 root tokens",
                ],
                "consumerBoundary": (
                    "the exact DialogText rows are reused inside the listed "
                    "registered DialogTrees, but no current DialogId, Timeline, "
                    "typed action, Story route, object carrier, GameAssembly, "
                    "or metadata entry exposes the emitted root as a loadable "
                    "consumer; row reuse proves content identity only"
                    if line_carriers else (
                        (
                            "the mechanical misc_dlg-to-dlg definition alias and "
                            if story_key.startswith("misc_dlg_") else ""
                        )
                        + "the exact current DialogTextTable line/audio group and "
                        "any DialogOptionTable choices survive, but the complete "
                        "generated Story-route census, typed native playback "
                        "index, DialogId/Timeline registries, DialogTree/TextAsset "
                        "corpus, hash-matched AnimeStudio object index, current "
                        "GameAssembly, and current global metadata expose no "
                        "loadable dialog root, activator, or owner carrier"
                    )
                ),
                "orderBoundary": (
                    "line ids order only lines inside the definition; option "
                    "ids define choices but not destinations; table order, "
                    "filename suffixes, OCR, and manual display order do not "
                    "establish mission activation or relative Story chronology"
                ),
                "reopenWhen": (
                    "the installed binary, exported tables, generated route "
                    "census, object index, or another typed producer/consumer "
                    "registry changes"
                ),
                "graphEffect": "none",
            }

    registered_table_dialog_evidence_by_key: dict[str, dict[str, Any]] = {}
    registered_table_dialog_validation_failures: list[dict[str, Any]] = []
    registered_table_dialog_exclusions: dict[str, list[str]] = {
        "ambiguousMission": [],
        "nativePlayback": [],
        "typedLevelScriptAction": [],
        "typedObjectCarrier": [],
        "timelineRegistration": [],
        "textAssetCarrier": [],
        "missingDialogRegistry": [],
        "binaryRootTokenPresent": [],
        "invalidDefinition": [],
    }
    registered_table_dialog_facts: dict[str, dict[str, Any]] = {}
    if native_playback_index is not None and action_story_occurrences is not None:
        for story_key, missions in sorted(
            core_targets.items(),
            key=lambda item: natural_key(item[0]),
        ):
            if not story_key.startswith("misc_dlg_"):
                continue
            definition_root_key = story_key.removeprefix("misc_")
            authored_keys = (story_key, definition_root_key)
            if len(missions) != 1:
                registered_table_dialog_exclusions["ambiguousMission"].append(
                    story_key
                )
                continue
            if any(native_playback_index.get(key) for key in authored_keys):
                registered_table_dialog_exclusions["nativePlayback"].append(
                    story_key
                )
                continue
            if any(action_story_occurrences.get(key) for key in authored_keys):
                registered_table_dialog_exclusions[
                    "typedLevelScriptAction"
                ].append(story_key)
                continue
            if story_key not in no_candidate_keys:
                registered_table_dialog_exclusions[
                    "typedObjectCarrier"
                ].append(story_key)
                continue
            if any(key in timeline_line_orders for key in authored_keys):
                registered_table_dialog_exclusions[
                    "timelineRegistration"
                ].append(story_key)
                continue
            text_assets = sorted(
                path
                for key in authored_keys
                for path in cutscene_definition_root.glob(f"{key}_p*.json")
            )
            if text_assets:
                registered_table_dialog_exclusions["textAssetCarrier"].append(
                    story_key
                )
                continue
            dialog_id_row = dialog_id_index.get(definition_root_key)
            if not isinstance(dialog_id_row, dict):
                registered_table_dialog_exclusions[
                    "missingDialogRegistry"
                ].append(story_key)
                continue
            facts, failure = _generic_registered_table_dialog_definition_facts(
                story_key,
                definition_root_key,
                dialog_id_row,
                dialog_text_table,
                dialog_option_table,
                audio_stems,
            )
            if failure is not None:
                failure["sourcePaths"] = [
                    str(source_paths["dialogIdIndex"]),
                    str(source_paths["dialogTextTable"]),
                    str(source_paths["dialogOptionTable"]),
                    str(source_paths["audioDialog"]),
                ]
                failure["sourceSha256"] = {
                    name: actual_hashes.get(name, "")
                    for name in (
                        "dialogIdIndex",
                        "dialogTextTable",
                        "dialogOptionTable",
                        "audioDialog",
                    )
                }
                registered_table_dialog_validation_failures.append(failure)
                registered_table_dialog_exclusions["invalidDefinition"].append(
                    story_key
                )
                continue
            registered_table_dialog_facts[story_key] = facts or {}

        binary_literals = {
            story_key: tuple(dict.fromkeys((story_key, facts["definitionRootKey"])))
            for story_key, facts in registered_table_dialog_facts.items()
        }
        binary_present = {
            story_key
            for story_key, literals in binary_literals.items()
            if any(
                literal.encode(encoding) in payload
                for literal in literals
                for encoding in ("utf-8", "utf-16le")
                for payload in (game_assembly_bytes, global_metadata_bytes)
            )
        }
        registered_table_dialog_exclusions["binaryRootTokenPresent"] = sorted(
            binary_present,
            key=natural_key,
        )
        for story_key, facts in sorted(
            registered_table_dialog_facts.items(),
            key=lambda item: natural_key(item[0]),
        ):
            if story_key in binary_present:
                continue
            mission_id = next(iter(core_targets[story_key]))
            registered_table_dialog_evidence_by_key[story_key] = {
                "sceneKey": story_key,
                "missionId": mission_id,
                "recoveryStatus":
                    "deferred_current_build_offline_surface_exhausted",
                "evidenceKind":
                    "registered_dialog_table_rows_without_tree_asset_or_consumer",
                **facts,
                "definitionTables": [
                    "DialogTextTable",
                    "DialogOptionTable",
                    "AudioDialog",
                ],
                "definitionSourceFiles": [
                    source_display_path(source_paths["dialogTextTable"]),
                    source_display_path(source_paths["dialogOptionTable"]),
                    source_display_path(source_paths["audioDialog"]),
                    source_display_path(source_paths["dialogIdIndex"]),
                ],
                "sourceFiles": [source_display_path(carrier_audit_path)],
                "originalBinaryFiles": [
                    source_display_path(source_paths["gameAssembly"]),
                    source_display_path(source_paths["globalMetadata"]),
                ],
                "dialogIdRegistrationStatus": "exact_current_dialog_id_registry",
                "dialogTreeAssetStatus": "absent",
                "timelineStatus": "absent",
                "nativePlaybackStatus": "zero_typed_native_playback_occurrences",
                "levelScriptActionCensusStatus": "zero_typed_action_occurrences",
                "carrierAuditStatus": "no_typed_story_owner_or_runtime_carrier",
                "carrierAuditTargetSetSha256": core_target_digest,
                "binaryRootTokenStatus":
                    "absent_utf8_and_utf16le_in_current_game_binaries",
                "nativeMappingId": OFFLINE_EXHAUSTION_MAPPING_ID,
                "gameAssemblySha256": OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
                "globalMetadataSha256": OFFLINE_EXHAUSTION_METADATA_SHA256,
                "consumerBoundary": (
                    "the mechanical misc_dlg-to-dlg alias, exact DialogId "
                    "MemoryPack registration, and exact DialogTextTable rows "
                    "prove a loadable table definition; the complete typed "
                    "LevelScript playback/action census, Timeline and TextAsset "
                    "indexes, carrier audit, GameAssembly, and metadata expose "
                    "no activator or mission owner"
                ),
                "orderBoundary": (
                    "registration and line order describe only the definition; "
                    "alias shape, table order, suffixes, OCR, and manual display "
                    "order do not establish activation or cross-file chronology"
                ),
                "reopenWhen": (
                    "the installed binary, DialogId registry, dialog tables, "
                    "typed action/playback census, or object indexes change"
                ),
                "graphEffect": "none",
            }

    registered_tree_evidence_by_key: dict[str, dict[str, Any]] = {}
    registered_tree_validation_failures: list[dict[str, Any]] = []
    registered_tree_exclusions: dict[str, list[str]] = {
        "declaredSpecialCase": [],
        "alreadyRecoveredHigherPrecedenceEvidence": [],
        "ambiguousMission": [],
        "nativePlayback": [],
        "typedLevelScriptAction": [],
        "typedObjectCarrier": [],
        "dialogRegistry": [],
        "missingDialogTreeDefinition": [],
        "binaryRootTokenPresent": [],
        "invalidDefinition": [],
    }
    registered_tree_definition_facts: dict[str, dict[str, Any]] = {}
    if native_playback_index is not None and action_story_occurrences is not None:
        for story_key, missions in sorted(
            core_targets.items(),
            key=lambda item: natural_key(item[0]),
        ):
            if not (
                story_key.startswith("dlg_")
                or story_key.startswith("misc_dlg_")
            ):
                continue
            definition_root_key = (
                story_key.removeprefix("misc_")
                if story_key.startswith("misc_dlg_")
                else story_key
            )
            authored_keys = (story_key, definition_root_key)
            if story_key in declared_dialog_keys:
                registered_tree_exclusions["declaredSpecialCase"].append(story_key)
                continue
            if len(missions) != 1:
                registered_tree_exclusions["ambiguousMission"].append(story_key)
                continue
            if any(native_playback_index.get(key) for key in authored_keys):
                registered_tree_exclusions["nativePlayback"].append(story_key)
                continue
            if any(action_story_occurrences.get(key) for key in authored_keys):
                registered_tree_exclusions["typedLevelScriptAction"].append(story_key)
                continue
            if story_key not in no_candidate_keys:
                registered_tree_exclusions["typedObjectCarrier"].append(story_key)
                continue
            dialog_id_row = dialog_id_index.get(definition_root_key)
            if not isinstance(dialog_id_row, dict):
                registered_tree_exclusions["dialogRegistry"].append(story_key)
                continue
            definition = recover_dialog_tree_definition_evidence(
                definition_root_key
            )
            if definition is None:
                registered_tree_exclusions["missingDialogTreeDefinition"].append(story_key)
                continue
            facts, failure = _generic_registered_dialog_tree_definition_facts(
                definition_root_key,
                dialog_id_row,
                definition,
            )
            if failure is not None:
                failure["sourcePaths"] = [
                    str(source_paths["dialogIdIndex"]),
                    str(cutscene_definition_root),
                ]
                failure["sourceSha256"] = {
                    "dialogIdIndex": actual_hashes.get("dialogIdIndex", ""),
                    "dialogTreeDefinition": safe_key(definition.get("sourceSha256")),
                }
                registered_tree_validation_failures.append(failure)
                registered_tree_exclusions["invalidDefinition"].append(story_key)
                continue
            timeline_facts, timeline_failure = (
                _generic_dialog_timeline_definition_facts(
                    definition_root_key,
                    timeline_line_orders.get(definition_root_key),
                )
            )
            if timeline_failure is not None:
                timeline_failure["sourcePaths"] = [
                    str(source_paths["timelineLineOrders"]),
                    *(
                        timeline_line_orders.get(
                            definition_root_key, {}
                        ).get("sourceRoots")
                        or []
                    ),
                ]
                timeline_failure["sourceSha256"] = {
                    "timelineLineOrders": actual_hashes.get(
                        "timelineLineOrders", ""
                    ),
                }
                registered_tree_validation_failures.append(timeline_failure)
                registered_tree_exclusions["invalidDefinition"].append(story_key)
                continue
            facts["dialogTimelineDefinition"] = timeline_facts
            facts["emittedStoryKey"] = story_key
            facts["definitionRootKey"] = definition_root_key
            registered_tree_definition_facts[story_key] = facts

        registered_tree_binary_present = (
            _present_literal_keys(
                game_assembly_bytes,
                {
                    key: facts["definitionRootKey"]
                    for key, facts in registered_tree_definition_facts.items()
                },
                "utf-8",
            )
            | _present_literal_keys(
                game_assembly_bytes,
                {
                    key: facts["definitionRootKey"]
                    for key, facts in registered_tree_definition_facts.items()
                },
                "utf-16le",
            )
            | _present_literal_keys(
                global_metadata_bytes,
                {
                    key: facts["definitionRootKey"]
                    for key, facts in registered_tree_definition_facts.items()
                },
                "utf-8",
            )
            | _present_literal_keys(
                global_metadata_bytes,
                {
                    key: facts["definitionRootKey"]
                    for key, facts in registered_tree_definition_facts.items()
                },
                "utf-16le",
            )
        )
        registered_tree_exclusions["binaryRootTokenPresent"] = sorted(
            registered_tree_binary_present
            - set(generic_npc_proxy_evidence_by_key),
            key=natural_key,
        )
        for story_key, facts in sorted(
            registered_tree_definition_facts.items(),
            key=lambda item: natural_key(item[0]),
        ):
            if (
                story_key in registered_tree_binary_present
                and story_key not in generic_npc_proxy_evidence_by_key
            ):
                continue
            mission_id = next(iter(core_targets[story_key]))
            registered_tree_evidence_by_key[story_key] = {
                "missionId": mission_id,
                "recoveryStatus": "deferred_current_build_offline_surface_exhausted",
                "evidenceKind": (
                    "registered_dialog_tree_definition_binary_consumer_surface_exhausted"
                ),
                "definitionRecoveryMethod": (
                    "pattern_discovered_current_original_data"
                ),
                **facts,
                "sceneKey": story_key,
                "definitionSourceFiles": [
                    facts["sourceFile"],
                    *((facts.get("dialogTimelineDefinition") or {}).get(
                        "sourceRoots"
                    ) or []),
                ],
                "sourceFiles": [
                    source_display_path(source_paths["dialogIdSource"]),
                    source_display_path(source_paths["dialogIdIndex"]),
                    source_display_path(carrier_audit_path),
                ],
                "originalBinaryFiles": [
                    source_display_path(source_paths["gameAssembly"]),
                    source_display_path(source_paths["globalMetadata"]),
                ],
                "dialogIdRegistrationStatus": "exact_current_dialog_id_registry",
                "dialogTreeDefinitionStatus": "exact_current_dialog_tree",
                "dialogTimelineDefinitionStatus": (
                    "exact_internal_dialog_timeline"
                    if facts.get("dialogTimelineDefinition")
                    else "absent"
                ),
                "levelScriptActionCensusStatus": "zero_typed_action_occurrences",
                "nativePlaybackStatus": "zero_typed_native_playback_occurrences",
                "carrierAuditStatus": "no_typed_story_owner_or_runtime_carrier",
                "carrierAuditTargetSetSha256": carrier_audit_target_digest,
                "currentCoreTargetSetSha256": core_target_digest,
                "binaryRootTokenStatus": (
                    "present_but_resolved_by_exact_typed_npc_proxy_consumer"
                    if story_key in registered_tree_binary_present else
                    "absent_utf8_and_utf16le_in_current_game_binaries"
                ),
                "nativeMappingId": OFFLINE_EXHAUSTION_MAPPING_ID,
                "gameAssemblySha256": OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
                "globalMetadataSha256": OFFLINE_EXHAUSTION_METADATA_SHA256,
                "searchedConsumerKinds": [
                    "MissionRuntime Story routes",
                    "complete typed LevelScript action-list census",
                    "typed native LevelScript playback index",
                    "GameplayConfig Story routes",
                    "dialog Timeline definitions and external Timeline routes",
                    "typed AnimeStudio owner/runtime object carriers",
                    "GameAssembly exact UTF-8/UTF-16 root tokens",
                    "global-metadata exact UTF-8/UTF-16 root tokens",
                ],
                "consumerBoundary": (
                    "the exact current DialogId registration proves a loadable root "
                    "and the exact DialogTree TextAsset proves its internal authored "
                    "graph and any exact dialog Timeline proves only internal "
                    "presentation; the complete current typed LevelScript action/native "
                    "playback census, MissionRuntime and GameplayConfig routes, "
                    "external Timeline routes, AnimeStudio carrier audit, GameAssembly, and "
                    "global metadata expose no mission activator or owner"
                ),
                "orderBoundary": (
                    "DialogTree nodes, connections, lines, and option groups order "
                    "content only inside this dialog; registry/table order, asset "
                    "paths, numeric suffixes, OCR, and manual display order do not "
                    "establish mission activation or cross-file chronology"
                ),
                "reopenWhen": (
                    "the installed binary, DialogId registry, DialogTree asset, "
                    "LevelScript action census, generated Story routes, object "
                    "index, or another typed producer/consumer changes"
                ),
                "graphEffect": "none",
            }

    registered_trunk_group_evidence_by_key: dict[str, dict[str, Any]] = {}
    registered_trunk_group_partial_evidence_by_key: dict[
        str, dict[str, Any]
    ] = {}
    registered_trunk_group_validation_failures: list[dict[str, Any]] = []
    registered_trunk_group_exclusions: dict[str, list[str]] = defaultdict(list)
    if native_playback_index is not None and action_story_occurrences is not None:
        level_basic_info_table = read_json(
            source_paths["levelBasicInfoTable"],
            {},
        )
        dungeon_table = read_json(table_root / "DungeonTable.json", {})
        subgame_table = read_json(
            source_paths["subGameInstanceDataTable"],
            {},
        )
        script_task_extra_info_table = read_json(
            source_paths["scriptTaskExtraInfoTable"],
            {},
        )
        definitions_by_root = registered_dialog_tree_definitions_by_root
        for story_key, missions in sorted(
            core_targets.items(),
            key=lambda item: natural_key(item[0]),
        ):
            if len(missions) != 1:
                registered_trunk_group_exclusions[
                    "ambiguousMission"
                ].append(story_key)
                continue
            if native_playback_index.get(story_key):
                registered_trunk_group_exclusions[
                    "nativePlayback"
                ].append(story_key)
                continue
            if action_story_occurrences.get(story_key):
                registered_trunk_group_exclusions[
                    "typedLevelScriptAction"
                ].append(story_key)
                continue
            if story_key not in no_candidate_keys:
                registered_trunk_group_exclusions[
                    "strongerTypedObjectCarrier"
                ].append(story_key)
                continue
            facts, failure, exclusion = (
                _generic_registered_dialog_tree_trunk_group_facts(
                    story_key,
                    dialog_text_table,
                    dialog_id_index,
                    definitions_by_root,
                    level_basic_info_table=level_basic_info_table,
                    dungeon_table=dungeon_table,
                    level_config_root=source_paths["levelConfigRoot"],
                    level_data_root=source_paths["levelDataRoot"],
                    text_asset_root=cutscene_definition_root,
                    subgame_table=subgame_table,
                    subgame_table_path=(
                        source_paths["subGameInstanceDataTable"]
                    ),
                    script_task_extra_info_table=(
                        script_task_extra_info_table
                    ),
                    script_task_extra_info_table_path=(
                        source_paths["scriptTaskExtraInfoTable"]
                    ),
                    level_script_root=source_paths["levelScriptRoot"],
                    native_playback_index=native_playback_index,
                )
            )
            if failure is not None:
                failure["sourcePaths"] = [
                    source_display_path(source_paths["dialogTextTable"]),
                    source_display_path(source_paths["dialogIdSource"]),
                    source_display_path(source_paths["dialogIdIndex"]),
                    *(
                        facts.get("definitionSourceFiles")
                        if isinstance(facts, dict)
                        else []
                    ),
                ]
                failure["sourceSha256"] = {
                    "dialogTextTable": actual_hashes.get(
                        "dialogTextTable", ""
                    ),
                    "dialogIdSource": actual_hashes.get(
                        "dialogIdSource", ""
                    ),
                    "dialogIdIndex": actual_hashes.get(
                        "dialogIdIndex", ""
                    ),
                }
                registered_trunk_group_validation_failures.append(failure)
                registered_trunk_group_exclusions[
                    "validationFailure"
                ].append(story_key)
                continue
            if facts is None:
                registered_trunk_group_exclusions[
                    exclusion or "notQualified"
                ].append(story_key)
                continue
            mission_id = next(iter(missions))
            partial_partition = (
                facts.get("partitionStatus") == "partial"
                and exclusion == "incompleteParentTreePartition"
            )
            evidence = {
                "sceneKey": story_key,
                "missionId": mission_id,
                "recoveryStatus": (
                    "actionable_partial_registered_dialog_tree_partition"
                    if partial_partition
                    else "deferred_current_build_offline_surface_exhausted"
                ),
                "evidenceKind": (
                    "partial_registered_dialog_tree_trunk_group_line_partition"
                    if partial_partition
                    else "registered_dialog_tree_trunk_group_exact_line_partition"
                ),
                "carrierStatus": (
                    "partial_exact_registered_dialog_tree_trunk_group_with_"
                    "unmatched_rows"
                    if partial_partition
                    else "exact_registered_dialog_tree_trunk_group_without_"
                    "activation_or_cross_parent_order"
                ),
                **facts,
                "definitionTables": ["DialogTextTable"],
                "runtimeRegistry": "Beyond.Gameplay.DialogIdTable",
                "runtimeRegistrationStatus": (
                    "every_parent_is_current_memorypack_record"
                ),
                "sourceFiles": [
                    source_display_path(source_paths["dialogTextTable"]),
                    source_display_path(source_paths["dialogIdSource"]),
                    source_display_path(source_paths["dialogIdIndex"]),
                    source_display_path(source_paths["levelBasicInfoTable"]),
                    source_display_path(table_root / "DungeonTable.json"),
                    source_display_path(
                        source_paths["subGameInstanceDataTable"]
                    ),
                    source_display_path(carrier_audit_path),
                    *facts["definitionSourceFiles"],
                    *(
                        source_file
                        for context in facts.get("parentLevelContexts") or []
                        for source_file in context.get("sourceFiles") or []
                    ),
                    *(
                        row.get("sourceFile")
                        for context in facts.get("parentLevelContexts") or []
                        for row in context.get("mapTextAssets") or []
                        if safe_key(row.get("sourceFile"))
                    ),
                ],
                "originalBinaryFiles": [
                    source_display_path(source_paths["gameAssembly"]),
                    source_display_path(source_paths["globalMetadata"]),
                ],
                "nativeMappingId": DIALOG_TREE_TRUNK_GROUP_MAPPING_ID,
                "nativeConsumers": [
                    dict(row) for row in DIALOG_TREE_TRUNK_NATIVE_CONSUMERS
                ],
                "gameAssemblySha256": actual_hashes.get(
                    "gameAssembly", ""
                ),
                "globalMetadataSha256": actual_hashes.get(
                    "globalMetadata", ""
                ),
                "levelScriptActionCensusStatus":
                    "zero_typed_action_occurrences",
                "nativePlaybackStatus":
                    "zero_typed_native_playback_occurrences",
                "carrierAuditStatus":
                    "no_typed_story_owner_or_runtime_carrier",
                "carrierAuditTargetSetSha256": core_target_digest,
                "consumerBoundary": (
                    (
                        "the covered DialogText rows are an exact one-parent-per-line "
                        "partition across registered, hash-validated DialogTree "
                        "assets, but the explicitly listed missing rows occur in no "
                        "selected registered parent; current typed LevelScript/native "
                        "playback indexes and the complete AnimeStudio carrier audit "
                        "expose no alternate mission activator or owner"
                    ) if partial_partition else (
                        "the complete current DialogText row group is an exact "
                        "one-parent-per-line partition across registered, "
                        "hash-validated DialogTree assets; current GameAssembly "
                        "executes their typed trunk ids through DialogTreeTrunkNode "
                        "and DialogManager, but no exact mission/quest or "
                        "factory-runtime source identifies what activates the "
                        "emitted aggregate"
                    )
                ),
                "orderBoundary": (
                    "each parentDialogTrees.lineConnections row is exact internal "
                    "authored order and option counts retain exact internal "
                    "branching; missing rows, separate parent roots, activation, "
                    "and cross-file chronology remain unresolved"
                    if partial_partition else
                    "each parentDialogTrees.lineConnections row is exact internal "
                    "authored order and option counts retain exact internal "
                    "branching; no current original-data source orders separate "
                    "parent roots or places this aggregate against another Story file"
                ),
                "reopenWhen": (
                    "the installed binary, DialogId registry, DialogTextTable, "
                    "DialogTree assets, or a typed mission/factory runtime "
                    "activation registry changes"
                ),
                "graphEffect": "none",
            }
            if partial_partition:
                registered_trunk_group_partial_evidence_by_key[story_key] = (
                    evidence
                )
            else:
                registered_trunk_group_evidence_by_key[story_key] = evidence

        # A partial partition is actionable until the unmatched row ids have
        # been checked as identities across every relevant current-build
        # consumer surface. Run each immutable corpus once for the whole batch,
        # then apply the same typed qualification to every candidate.
        partial_missing_line_ids = sorted({
            line_id
            for evidence in (
                registered_trunk_group_partial_evidence_by_key.values()
            )
            for line_id in _string_list(evidence.get("missingLineIds"))
        }, key=natural_key)
        if partial_missing_line_ids:
            level_script_paths = sorted(
                source_paths["levelScriptRoot"].rglob("*.json"),
                key=lambda path: natural_key(str(path)),
            )
            level_script_census = _literal_absence_census(
                partial_missing_line_ids,
                level_script_paths,
            )
            binary_census = _literal_absence_census(
                partial_missing_line_ids,
                [
                    source_paths["gameAssembly"],
                    source_paths["globalMetadata"],
                ],
            )
            for story_key, evidence in list(
                registered_trunk_group_partial_evidence_by_key.items()
            ):
                closure, failure, exclusion = (
                    _generic_partial_dialog_row_consumer_exhaustion_facts(
                        story_key,
                        evidence,
                        definitions_by_root,
                        level_script_census,
                        binary_census,
                    )
                )
                if failure is not None:
                    failure["sourcePaths"] = [
                        source_display_path(source_paths["dialogTextTable"]),
                        source_display_path(source_paths["dialogIdSource"]),
                        source_display_path(source_paths["dialogIdIndex"]),
                        source_display_path(source_paths["levelScriptRoot"]),
                        source_display_path(source_paths["gameAssembly"]),
                        source_display_path(source_paths["globalMetadata"]),
                    ]
                    failure["sourceSha256"] = {
                        "dialogTextTable": actual_hashes.get(
                            "dialogTextTable", ""
                        ),
                        "dialogIdSource": actual_hashes.get(
                            "dialogIdSource", ""
                        ),
                        "dialogIdIndex": actual_hashes.get(
                            "dialogIdIndex", ""
                        ),
                        "levelScriptSourceSet": level_script_census.get(
                            "sourceSetSha256", ""
                        ),
                        "gameBinarySourceSet": binary_census.get(
                            "sourceSetSha256", ""
                        ),
                    }
                    registered_trunk_group_validation_failures.append(failure)
                    continue
                if closure is None:
                    registered_trunk_group_exclusions[
                        exclusion or "partialConsumerSurfaceNotExhausted"
                    ].append(story_key)
                    continue
                evidence.update(closure)
                evidence.update({
                    "recoveryStatus": (
                        "deferred_current_build_offline_surface_exhausted"
                    ),
                    "evidenceKind": (
                        "partial_registered_dialog_tree_rows_without_"
                        "current_consumer"
                    ),
                    "carrierStatus": (
                        "exact_registered_parent_partition_with_"
                        "unmatched_definition_only_rows"
                    ),
                    "reopenWhen": (
                        "the installed binary, DialogId registry, "
                        "DialogTextTable, DialogTree assets, exported "
                        "LevelScripts, or typed SubGame playback changes"
                    ),
                })
                registered_trunk_group_evidence_by_key[story_key] = evidence
                del registered_trunk_group_partial_evidence_by_key[story_key]

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
        == "animestudioStoryReversePPtrAudit.v4"
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

    # General cutscene-definition recovery: discover current core gaps from
    # the audited target set, then require the same typed root/director facts
    # used by the older declared cases.  Identity comes from the original
    # Timeline registries, TextAsset payload, GameObject hierarchy, and reverse
    # PPtr graph; filename shape is only used to locate the candidate payload.
    generic_cutscene_evidence_by_key: dict[str, dict[str, Any]] = {}
    generic_cutscene_candidate_facts: dict[str, dict[str, Any]] = {}
    generic_cutscene_validation_failures: list[dict[str, Any]] = []
    generic_cutscene_qualification_diagnostics: list[dict[str, Any]] = []
    generic_cutscene_exclusions: dict[str, list[str]] = {
        "declaredSpecialCase": [],
        "ambiguousMission": [],
        "nativePlayback": [],
        "typedObjectCarrier": [],
        "binaryRootTokenPresent": [],
        "missingExactDefinition": [],
        "invalidTypedRootGraph": [],
    }
    str_timeline_ids = (
        ((str_id_num_table.get("timelines_id") or {}).get("dic") or {})
        if isinstance(str_id_num_table, dict)
        else {}
    )
    for story_key, missions in sorted(
        core_targets.items(),
        key=lambda item: natural_key(item[0]),
    ):
        if not story_key.startswith("cutscene_"):
            continue
        if story_key in all_cutscene_keys:
            generic_cutscene_exclusions["declaredSpecialCase"].append(
                story_key
            )
            continue
        if len(missions) != 1:
            generic_cutscene_exclusions["ambiguousMission"].append(
                story_key
            )
            continue
        if native_playback_index is None or native_playback_index.get(
            story_key
        ):
            generic_cutscene_exclusions["nativePlayback"].append(
                story_key
            )
            continue
        if story_key not in no_candidate_keys:
            generic_cutscene_exclusions["typedObjectCarrier"].append(
                story_key
            )
            continue

        mission_id = next(iter(missions))
        definition_paths = sorted(
            cutscene_definition_root.glob(f"{story_key}_p*.json")
        )
        registry_id = str_timeline_ids.get(story_key)
        reverse_registry_value = timeline_ids.get(str(registry_id))
        text_only_facts, text_only_failure = (
            _generic_text_table_only_cutscene_definition_facts(
                story_key,
                text_table,
            )
        )
        if (
            len(definition_paths) != 1
            or not isinstance(registry_id, int)
            or safe_key(reverse_registry_value) != story_key
        ):
            object_rows = [
                row
                for row in gameobject_audit.get("gameObjects") or []
                if isinstance(row, dict)
                and story_key in _string_list(row.get("storyKeys"))
            ]
            reverse_relations = [
                row
                for row in reverse_pptr_audit.get("relations") or []
                if isinstance(row, dict)
                and story_key in _string_list(row.get("targetStoryKeys"))
            ]
            director_hosts = [
                row
                for row in reverse_pptr_audit.get("directorHosts") or []
                if isinstance(row, dict)
                and story_key in _string_list(row.get("storyKeys"))
            ]
            action_rows = (
                (action_story_occurrences or {}).get(story_key) or []
            )
            binary_root_present = any(
                story_key.encode(encoding) in payload
                for encoding in ("utf-8", "utf-16le")
                for payload in (game_assembly_bytes, global_metadata_bytes)
            )
            text_only_surface_exhausted = (
                text_only_facts is not None
                and not definition_paths
                and registry_id is None
                and reverse_registry_value is None
                and not object_rows
                and not reverse_relations
                and not director_hosts
                and not action_rows
                and not binary_root_present
            )
            if text_only_surface_exhausted:
                generic_cutscene_evidence_by_key[story_key] = {
                    "sceneKey": story_key,
                    "missionId": mission_id,
                    "recoveryStatus":
                        "deferred_current_build_offline_surface_exhausted",
                    "evidenceKind":
                        "text_table_only_cutscene_without_recovered_original_story_consumer",
                    **text_only_facts,
                    "definitionTable": "TextTable",
                    "definitionSourceFiles": [
                        source_display_path(source_paths["textTable"]),
                    ],
                    "sourceFiles": [
                        source_display_path(carrier_audit_path),
                        source_display_path(gameobject_audit_path),
                        source_display_path(reverse_pptr_audit_path),
                    ],
                    "originalBinaryFiles": [
                        source_display_path(source_paths["gameAssembly"]),
                        source_display_path(source_paths["globalMetadata"]),
                    ],
                    "timelineStatus": "absent",
                    "cutsceneRootStatus": "absent",
                    "nativePlaybackStatus":
                        "zero_typed_native_playback_occurrences",
                    "levelScriptActionCensusStatus":
                        "zero_typed_action_occurrences",
                    "carrierAuditStatus":
                        "no_typed_story_owner_or_runtime_carrier",
                    "carrierAuditTargetSetSha256": core_target_digest,
                    "binaryRootTokenStatus":
                        "absent_utf8_and_utf16le_in_current_game_binaries",
                    "nativeMappingId": OFFLINE_EXHAUSTION_MAPPING_ID,
                    "gameAssemblySha256": OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
                    "globalMetadataSha256": OFFLINE_EXHAUSTION_METADATA_SHA256,
                    "consumerBoundary": (
                        "the exact TextTable group survives, while the current "
                        "Timeline registries, TextAsset/root and reverse-PPtr "
                        "indexes, typed LevelScript action/playback census, "
                        "carrier audit, GameAssembly, and metadata expose no "
                        "executable cutscene definition or activator"
                    ),
                    "orderBoundary": (
                        "localized row order, filename suffixes, OCR, and manual "
                        "display order do not establish playback, ownership, or "
                        "mission chronology"
                    ),
                    "reopenWhen": (
                        "the installed binary, TextTable, Timeline registry, "
                        "TextAsset/object indexes, or typed playback census changes"
                    ),
                    "graphEffect": "none",
                }
                continue
            generic_cutscene_exclusions[
                "missingExactDefinition"
            ].append(story_key)
            generic_cutscene_qualification_diagnostics.append({
                "validator": "genericCutsceneDefinitionConsumer",
                "gate": "uniqueTextAssetAndBidirectionalTimelineRegistry",
                "storyKey": story_key,
                "missionId": mission_id,
                "sourcePaths": [
                    str(source_paths["strIdNumTable"]),
                    str(source_paths["numIdStrTable"]),
                    str(cutscene_definition_root),
                ],
                "expected": {
                    "textAssetCount": 1,
                    "integerTimelineRegistryId": True,
                    "reverseRegistryValue": story_key,
                },
                "actual": {
                    "textAssets": [str(path) for path in definition_paths],
                    "timelineRegistryId": registry_id,
                    "reverseRegistryValue": reverse_registry_value,
                    "textTableDefinition": text_only_facts,
                    "textTableValidationFailure": text_only_failure,
                    "gameObjectRows": len(object_rows),
                    "reverseRelations": len(reverse_relations),
                    "directorHosts": len(director_hosts),
                    "typedActionOccurrences": len(action_rows),
                    "binaryRootTokenPresent": binary_root_present,
                },
            })
            continue

        definition_path = definition_paths[0]
        definition_payload = read_json(definition_path, {})
        decoded_definition: Any = None
        try:
            decoded_definition = json.loads(base64.b64decode(
                definition_payload["m_Script"],
                validate=True,
            ))
        except (KeyError, TypeError, ValueError, binascii.Error, json.JSONDecodeError):
            pass
        object_rows = [
            row
            for row in gameobject_audit.get("gameObjects") or []
            if isinstance(row, dict)
            and set(_string_list(row.get("storyKeys"))) == {story_key}
        ]
        director_hosts = [
            row
            for row in reverse_pptr_audit.get("directorHosts") or []
            if isinstance(row, dict)
            and set(_string_list(row.get("storyKeys"))) == {story_key}
        ]
        definition_valid = (
            isinstance(definition_payload, dict)
            and set(definition_payload) == {"Name", "m_Name", "m_Script"}
            and safe_key(definition_payload.get("Name")) == story_key
            and safe_key(definition_payload.get("m_Name")) == story_key
            and isinstance(decoded_definition, dict)
            and safe_key(decoded_definition.get("cutsceneName")) == story_key
            and safe_key(decoded_definition.get("path")).endswith(
                f"/{story_key}/Prefab/{story_key}"
            )
        )
        object_graph_valid = (
            bool(object_rows)
            and all(
                set(_string_list(row.get("expectedGapMissions")))
                == {mission_id}
                and safe_key((row.get("type") or {}).get("scriptFullName"))
                == "Beyond.Gameplay.View.CutsceneRootComponent"
                and row.get("candidateStatus")
                == "no_typed_owner_or_runtime_sibling_or_descendant"
                and row.get("edgeStatus") == "no_edge_candidate_only"
                and not row.get("candidateSiblingComponents")
                and not row.get("candidateDescendantComponents")
                and not row.get("unresolvedChildTransformPathIds")
                for row in object_rows
            )
        )
        embedded_root_graph_valid = (
            bool(director_hosts)
            and all(
                safe_key(row.get("rootGameObjectName")) == story_key
                and not row.get("unresolvedChildTransformPathIds")
                and any(
                    safe_key((component.get("type") or {}).get(
                        "scriptFullName"
                    )) == "Beyond.Gameplay.View.CutsceneRootComponent"
                    and component.get("gameObjectPathId")
                    == row.get("rootGameObjectPathId")
                    for component in row.get("typedComponents") or []
                    if isinstance(component, dict)
                )
                for row in director_hosts
            )
        )
        director_graph_valid = (
            bool(director_hosts)
            and all(
                set(_string_list(row.get("expectedGapMissions")))
                == {mission_id}
                and safe_key(row.get("pointerPath")) == "$.m_PlayableAsset"
                and not row.get("candidateComponents")
                and not row.get("crossStoryContainments")
                and not row.get("crossStoryPlaybackAliases")
                and any(
                    safe_key(binding.get("hostStoryKey")) == story_key
                    and safe_key(binding.get("pointerPath")) == "$._director"
                    and safe_key(binding.get("pointerStatus")) == "resolved"
                    for binding in row.get("rootDirectorBindings") or []
                    if isinstance(binding, dict)
                )
                for row in director_hosts
            )
        )
        root_bytes = story_key.encode("utf-8")
        binary_root_present = (
            root_bytes in game_assembly_bytes
            or story_key.encode("utf-16le") in game_assembly_bytes
            or root_bytes in global_metadata_bytes
            or story_key.encode("utf-16le") in global_metadata_bytes
        )
        if binary_root_present:
            generic_cutscene_exclusions[
                "binaryRootTokenPresent"
            ].append(story_key)
            continue
        generic_cutscene_candidate_facts[story_key] = {
            "storyKey": story_key,
            "missionId": mission_id,
            "registryId": registry_id,
            "definitionPath": definition_path,
            "decodedDefinition": decoded_definition,
            "definitionValid": definition_valid,
            "objectRows": object_rows,
            "objectGraphValid": object_graph_valid,
            "embeddedRootGraphValid": embedded_root_graph_valid,
            "directorHosts": director_hosts,
        }
        if not (
            definition_valid
            and (object_graph_valid or embedded_root_graph_valid)
            and director_graph_valid
        ):
            generic_cutscene_exclusions[
                "invalidTypedRootGraph"
            ].append(story_key)
            generic_cutscene_qualification_diagnostics.append({
                "validator": "genericCutsceneDefinitionConsumer",
                "gate": "exactDefinitionRootDirectorGraph",
                "storyKey": story_key,
                "missionId": mission_id,
                "sourcePaths": [
                    str(definition_path),
                    str(gameobject_audit_path),
                    str(reverse_pptr_audit_path),
                ],
                "expected": {
                    "definitionIdentity": story_key,
                    "typedCutsceneRootWithoutOwnerRuntimeCandidate": True,
                    "resolvedRootDirectorWithoutCrossStoryAlias": True,
                },
                "actual": {
                    "definitionValid": definition_valid,
                    "gameObjectRows": len(object_rows),
                    "objectGraphValid": object_graph_valid,
                    "embeddedRootGraphValid": embedded_root_graph_valid,
                    "directorHosts": len(director_hosts),
                    "directorGraphValid": director_graph_valid,
                },
            })
            continue
        generic_cutscene_evidence_by_key[story_key] = {
            "sceneKey": story_key,
            "missionId": mission_id,
            "recoveryStatus":
                "deferred_current_build_offline_surface_exhausted",
            "evidenceKind": "cutscene_root_without_recovered_activator",
            "timelineRegistryId": registry_id,
            "definitionRootNames": [story_key],
            "directorHostCount": len(director_hosts),
            "gameObjectRowCount": len(object_rows),
            "embeddedRootGraph": embedded_root_graph_valid,
            "definitionSourceFiles": [
                source_display_path(definition_path),
                source_display_path(source_paths["strIdNumTable"]),
                source_display_path(source_paths["numIdStrTable"]),
            ],
            "sourceFiles": [
                source_display_path(carrier_audit_path),
                source_display_path(gameobject_audit_path),
                source_display_path(reverse_pptr_audit_path),
            ],
            "originalBinaryFiles": [
                source_display_path(source_paths["gameAssembly"]),
                source_display_path(source_paths["globalMetadata"]),
            ],
            "originalGameFiles": sorted({
                safe_key((row.get("object") or {}).get("source"))
                for row in director_hosts
                if safe_key((row.get("object") or {}).get("source"))
            } | {
                safe_key((row.get("targetObject") or {}).get("source"))
                for row in director_hosts
                if safe_key((row.get("targetObject") or {}).get("source"))
            }),
            "definitionSha256": _sha256_file(definition_path),
            "definitionPath": safe_key(decoded_definition.get("path")),
            "isTransition": decoded_definition.get("isTransition"),
            "carrierAuditStatus":
                "no_typed_story_owner_or_runtime_carrier",
            "candidateStatus":
                "no_typed_owner_or_runtime_sibling_or_descendant",
            "binaryRootTokenStatus":
                "absent_utf8_and_utf16le_in_current_game_binaries",
            "nativeMappingId": OFFLINE_EXHAUSTION_MAPPING_ID,
            "playbackMappingId": OFFLINE_EXHAUSTION_REVERSE_PPTR_MAPPING_ID,
            "gameAssemblySha256": OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
            "globalMetadataSha256": OFFLINE_EXHAUSTION_METADATA_SHA256,
            "consumerBoundary": (
                "the bidirectional Timeline registry, decoded TextAsset, "
                "typed CutsceneRootComponent hierarchy, and resolved "
                "PlayableDirector prove an executable cutscene definition; "
                "the current typed carrier, reverse-PPtr, playback-index, "
                "GameAssembly, and metadata surfaces expose no activator or "
                "mission/quest owner"
            ),
            "orderBoundary": (
                "Timeline registration, object hierarchy, asset path, "
                "filename suffix, OCR, and manual display order do not place "
                "the cutscene in mission chronology"
            ),
            "reopenWhen": (
                "the installed binary, Timeline registries, TextAsset, object "
                "indexes, or typed playback route census changes"
            ),
            "graphEffect": "none",
        }

    # A CutsceneRoot can intentionally name one Story key while its exact
    # director plays a TimelineAsset registered under another.  Discover these
    # pairs from the original serialized pointer graph.  The relation proves
    # root/playable identity only: it neither orders the two nominal mission
    # memberships nor assigns an activator to either one.
    qualified_alias_keys: set[str] = set()
    for director_host in reverse_pptr_audit.get("directorHosts") or []:
        if not isinstance(director_host, dict):
            continue
        aliases = [
            row
            for row in director_host.get("crossStoryPlaybackAliases") or []
            if isinstance(row, dict)
        ]
        containments = [
            row
            for row in director_host.get("crossStoryContainments") or []
            if isinstance(row, dict)
        ]
        if len(aliases) != 1 or len(containments) != 1:
            continue
        alias = aliases[0]
        containment = containments[0]
        root_key = safe_key(alias.get("rootStoryKey"))
        playable_key = safe_key(alias.get("playableAssetStoryKey"))
        root_facts = generic_cutscene_candidate_facts.get(root_key)
        playable_facts = generic_cutscene_candidate_facts.get(playable_key)
        if not root_facts or not playable_facts:
            continue
        bindings = [
            row
            for row in director_host.get("rootDirectorBindings") or []
            if isinstance(row, dict)
        ]
        alias_valid = (
            root_key != playable_key
            and alias.get("relation")
            == "cutscene_root_director_playable_asset"
            and alias.get("edgeStatus")
            == "exact_root_playback_alias_no_chronology_or_mission_owner"
            and safe_key(containment.get("hostStoryKey")) == root_key
            and safe_key(containment.get("embeddedStoryKey")) == playable_key
            and containment.get("relation")
            == "cutscene_root_embedded_timeline_asset"
            and containment.get("edgeStatus")
            == "exact_containment_no_chronology_or_mission_owner"
            and set(_string_list(director_host.get("storyKeys")))
            == {playable_key}
            and set(_string_list(
                director_host.get("expectedGapMissions")
            )) == {playable_facts["missionId"]}
            and safe_key(director_host.get("pointerPath"))
            == "$.m_PlayableAsset"
            and not director_host.get("candidateComponents")
            and not director_host.get("unresolvedChildTransformPathIds")
            and len(bindings) == 1
            and safe_key(bindings[0].get("hostStoryKey")) == root_key
            and safe_key(bindings[0].get("pointerPath")) == "$._director"
            and safe_key(bindings[0].get("pointerStatus")) == "resolved"
            and root_facts["definitionValid"]
            and root_facts["objectGraphValid"]
            and playable_facts["definitionValid"]
            and playable_facts["embeddedRootGraphValid"]
            and director_host in playable_facts["directorHosts"]
        )
        if not alias_valid:
            continue
        alias_summary = {
            "rootStoryKey": root_key,
            "playableAssetStoryKey": playable_key,
            "relation": alias["relation"],
            "edgeStatus": alias["edgeStatus"],
        }
        original_game_files = sorted({
            safe_key((director_host.get("object") or {}).get("source")),
            safe_key((director_host.get("targetObject") or {}).get("source")),
        } - {""})
        for role, facts in (
            ("cutscene_root", root_facts),
            ("playable_timeline_asset", playable_facts),
        ):
            key = facts["storyKey"]
            decoded = facts["decodedDefinition"]
            definition_path = facts["definitionPath"]
            generic_cutscene_evidence_by_key[key] = {
                "sceneKey": key,
                "missionId": facts["missionId"],
                "recoveryStatus":
                    "deferred_current_build_offline_surface_exhausted",
                "evidenceKind":
                    "cutscene_root_playable_alias_without_recovered_activator",
                "cutsceneAliasRole": role,
                "rootPlaybackAlias": alias_summary,
                "timelineRegistryId": facts["registryId"],
                "definitionRootNames": [key],
                "directorHostCount": len(facts["directorHosts"]),
                "gameObjectRowCount": len(facts["objectRows"]),
                "definitionSourceFiles": [
                    source_display_path(definition_path),
                    source_display_path(source_paths["strIdNumTable"]),
                    source_display_path(source_paths["numIdStrTable"]),
                ],
                "sourceFiles": [
                    source_display_path(carrier_audit_path),
                    source_display_path(gameobject_audit_path),
                    source_display_path(reverse_pptr_audit_path),
                ],
                "originalBinaryFiles": [
                    source_display_path(source_paths["gameAssembly"]),
                    source_display_path(source_paths["globalMetadata"]),
                ],
                "originalGameFiles": original_game_files,
                "definitionSha256": _sha256_file(definition_path),
                "definitionPath": safe_key(decoded.get("path")),
                "isTransition": decoded.get("isTransition"),
                "carrierAuditStatus":
                    "no_typed_story_owner_or_runtime_carrier",
                "candidateStatus":
                    "no_typed_owner_or_runtime_sibling_or_descendant",
                "binaryRootTokenStatus":
                    "absent_utf8_and_utf16le_in_current_game_binaries",
                "nativeMappingId": OFFLINE_EXHAUSTION_MAPPING_ID,
                "playbackMappingId":
                    OFFLINE_EXHAUSTION_REVERSE_PPTR_MAPPING_ID,
                "gameAssemblySha256": OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
                "globalMetadataSha256": OFFLINE_EXHAUSTION_METADATA_SHA256,
                "consumerBoundary": (
                    "the original CutsceneRoot _director pointer and the "
                    "director's PlayableAsset pointer prove an exact cross-key "
                    "root/playable alias; current typed carrier, playback-index, "
                    "GameAssembly, and metadata surfaces expose no activator or "
                    "mission/quest owner"
                ),
                "orderBoundary": (
                    "the exact alias is playback composition, not evidence that "
                    "either nominal mission precedes the other; registry order, "
                    "filenames, OCR, and manual display order remain non-evidence"
                ),
                "reopenWhen": (
                    "the installed binary, Timeline registries, TextAssets, "
                    "object indexes, or typed playback route census changes"
                ),
                "graphEffect": "none",
            }
            qualified_alias_keys.add(key)
    if qualified_alias_keys:
        generic_cutscene_exclusions["invalidTypedRootGraph"] = [
            key
            for key in generic_cutscene_exclusions["invalidTypedRootGraph"]
            if key not in qualified_alias_keys
        ]
        generic_cutscene_qualification_diagnostics = [
            row
            for row in generic_cutscene_qualification_diagnostics
            if safe_key(row.get("storyKey")) not in qualified_alias_keys
        ]

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
        mission_id = radio_mission_by_key[story_key]
        empty_levelscript_context = (
            empty_levelscript_context_by_mission.get(mission_id)
        )
        index[story_key] = {
            "sceneKey": story_key,
            "missionId": mission_id,
            "recoveryStatus":
                "deferred_current_build_offline_surface_exhausted",
            "evidenceKind": (
                "leveldata_context_without_typed_story_activator"
                if context
                else (
                    "radio_definition_with_empty_levelscript_host"
                    if empty_levelscript_context
                    else "radio_definition_without_recovered_consumer"
                )
            ),
            "definitionTable": "RadioTable",
            "definitionSourceFiles": [
                str(source_paths[name].relative_to(ROOT)).replace("\\", "/")
                for name in ("radioTable", "audioDialog")
            ],
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
            "emptyLevelScriptContext": empty_levelscript_context,
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
                    if context else (
                    "the exact RadioTable rows define the radio, while the "
                    "mission-named LevelData contains one exact propertyless "
                    "LevelScript whose serialized action-list count and "
                    "decoded UID-record count are both zero; neither that "
                    "empty host nor the audited MissionRuntime, GameplayConfig, "
                    "object-index, and native playback surfaces expose a consumer"
                    if empty_levelscript_context else (
                    "the exact ids occur only in current RadioTable definitions; "
                    "every authored audio id is absent from AudioDialog, and the "
                    "audited MissionRuntime, LevelScript, GameplayConfig, "
                    "object-index, and direct native playback-caller surfaces "
                    "expose no consumer"
                    if set(missing_audio_ids_by_story.get(story_key, ()))
                    == radio_audio_ids_by_story[story_key] else
                    "exact ids occur only in current RadioTable definitions "
                    "and AudioDialog membership, including exact authored "
                    "variants where present, across the audited MissionRuntime, "
                    "LevelScript, GameplayConfig, Table, object-index, and "
                    "direct native playback-caller surfaces"
                    )
                    )
                )
            ),
            "orderBoundary": (
                "LevelData byte proximity, collection order, quest "
                "predecessors, and filename suffixes do not establish "
                "playback or relative Story order"
                if context else (
                    "the empty mission-named LevelScript, RadioTable order, "
                    "and filename suffixes do not establish playback or "
                    "relative Story order"
                    if empty_levelscript_context else
                    "RadioTable row order, filename suffixes, and any manual "
                    "display order do not establish playback or relative "
                    "Story chronology"
                )
            ),
            "reopenWhen": (
                "installed binary, exported tables, object index, "
                "or another typed producer/consumer registry changes"
            ),
            "graphEffect": "none",
        }
    for story_key, evidence in sorted(
        generic_radio_evidence_by_key.items(),
        key=lambda item: natural_key(item[0]),
    ):
        index.setdefault(story_key, evidence)
    for story_key in sorted(
        set(generic_npc_proxy_evidence_by_key)
        & set(registered_tree_evidence_by_key),
        key=natural_key,
    ):
        composed, failure = _compose_registered_dialog_tree_npc_proxy_evidence(
            registered_tree_evidence_by_key[story_key],
            generic_npc_proxy_evidence_by_key[story_key],
        )
        if failure is not None:
            generic_npc_proxy_validation_failures.append(failure)
            del generic_npc_proxy_evidence_by_key[story_key]
            continue
        generic_npc_proxy_evidence_by_key[story_key] = composed
        del registered_tree_evidence_by_key[story_key]
    for evidence_by_key in (
        generic_npc_proxy_evidence_by_key,
        generic_sns_evidence_by_key,
    ):
        for story_key, evidence in sorted(
            evidence_by_key.items(),
            key=lambda item: natural_key(item[0]),
        ):
            index.setdefault(story_key, evidence)
    for story_key in sorted(all_dialog_keys, key=natural_key):
        definition = dialog_context_definitions[story_key]
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
                        if validation["missionNpcProxyTrackingContexts"]
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
                dialog_context_definitions[story_key]["filename"],
            "definitionAssets": [
                filename
                for filename in (
                    dialog_context_definitions[story_key][
                        "filename"
                    ],
                    dialog_context_definitions[story_key].get(
                        "extraConfigFilename"
                    ),
                )
                if filename
            ],
            "definitionTable": "DialogTextTable",
            "definitionRootKey": validation["registryKey"],
            "definitionSourceFiles": [
                str(source_paths[name].relative_to(ROOT)).replace("\\", "/")
                for name in (
                    "dialogTextTable",
                    *(("dialogOptionTable",) if validation["optionIds"] else ()),
                    "audioDialog",
                    "dialogIdIndex",
                    "timelineLineOrders",
                    *(
                        ("npcProxyExDataTable", "npcProxyTable")
                        if validation["npcProxyConsumers"] else ()
                    ),
                )
            ],
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
            "missionNpcProxyTrackingContexts":
                validation["missionNpcProxyTrackingContexts"],
            "levelScriptTaskConsumer":
                validation["levelScriptTaskConsumer"],
            "levelDataDialogBranchContext":
                validation["levelDataDialogBranchContext"],
            "allowedNonOwningRoute": allowed_non_owning_route,
            "nativeMappingId": OFFLINE_EXHAUSTION_MAPPING_ID,
            "npcProxySelectionMappingId": (
                NPC_PROXY_DIALOG_SELECTION_MAPPING_ID
                if validation["npcProxyConsumers"] else None
            ),
            "originalBinaryFiles": (
                [source_display_path(source_paths["gameAssembly"])]
                if validation["npcProxyConsumers"] else []
            ),
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
                    if validation["missionNpcProxyTrackingContexts"]
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
        mission_id = text_only_dialog_mission_by_key[story_key]
        empty_levelscript_context = (
            empty_levelscript_context_by_mission.get(mission_id)
        )
        table_only_registration = (
            validation["dialogIdRegistrationStatus"]
            == "present_table_only"
        )
        index[story_key] = {
            "sceneKey": story_key,
            "missionId": mission_id,
            "recoveryStatus":
                "deferred_current_build_offline_surface_exhausted",
            "evidenceKind": (
                "dialog_text_table_branch_payload_with_parent_dialog_tree_context"
                if branch_context
                else (
                    "registered_dialog_table_rows_without_tree_asset_or_consumer"
                    if table_only_registration
                    else (
                        "dialog_text_table_only_with_empty_levelscript_host"
                        if empty_levelscript_context
                        else "dialog_text_table_only_without_registry_asset_or_consumer"
                    )
                )
            ),
            "definitionTable": "DialogTextTable",
            "definitionRootKey": validation["definitionRootKey"],
            "definitionSourceFiles": [
                str(source_paths[name].relative_to(ROOT)).replace("\\", "/")
                for name in (
                    "dialogTextTable",
                    *(("dialogOptionTable",) if validation["optionIds"] else ()),
                    *(
                        ("dialogSummaryMapTable", "dialogSummaryTable")
                        if validation["summaryDefinition"] else ()
                    ),
                    "audioDialog",
                    "dialogIdIndex",
                    "timelineLineOrders",
                )
            ],
            "definitionTables": (
                [
                    "DialogTextTable",
                    *(
                        ["DialogOptionTable"]
                        if validation["optionIds"] else []
                    ),
                    *(
                        ["DialogSummaryMapTable", "DialogSummaryTable"]
                        if validation["summaryDefinition"] else []
                    ),
                ]
            ),
            "lineIds": validation["lineIds"],
            "audioIds": validation["audioIds"],
            "audioVariants": validation["audioVariants"],
            "missingAudioIds": validation["missingAudioIds"],
            "optionIds": validation["optionIds"],
            "optionRows": validation["optionRows"],
            "summaryDefinition": validation["summaryDefinition"],
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
            "emptyLevelScriptContext": empty_levelscript_context,
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
                    else (
                    "the exact DialogTextTable line/audio group and exact "
                    "DialogOptionTable definitions have no DialogId registration, "
                    "DialogTree, Timeline, or AudioDialog membership; the exact "
                    "mission-named LevelData carries one propertyless LevelScript "
                    "whose serialized action-list and decoded UID-record counts "
                    "are zero, so it supplies no activator or option-route graph"
                    if empty_levelscript_context else
                    "the exact DialogTextTable line/audio group and any exact "
                    "DialogOptionTable option definitions plus any exact "
                    "DialogSummaryMapTable artifact have no current "
                    "DialogId registration, DialogTree asset, Timeline, "
                    "AudioDialog membership, typed MissionRuntime or "
                    "LevelScript consumer, Lua reference, or object-index "
                    "carrier; option definitions prove authored choices but "
                    "not their route graph"
                    )
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
                    (
                        "the empty mission-named LevelScript, line ids, option "
                        "suffixes, and fallback/manual display positions do not "
                        "establish playback, option routing, or mission chronology"
                        if empty_levelscript_context else
                        "line ids, printable-only token suffixes, and fallback/"
                        "manual display positions do not establish playback, "
                        "option routing, or mission chronology"
                    )
                )
            ),
            "reopenWhen": (
                "installed binary, DialogTextTable, DialogOptionTable, "
                "DialogSummaryMapTable, DialogSummaryTable, AudioDialog, "
                "DialogId index, TextAsset inventory, Timeline "
                "index, object index, Lua corpus, or another typed "
                "producer/consumer changes"
            ),
            "graphEffect": "none",
        }
    # Registered tree partitions carry stronger exact internal structure and
    # typed parent-runtime files than a table-row fallback, so install them
    # first. The generic definition evidence remains a truthful fallback for
    # row reuse that does not form a non-overlapping partition.
    for story_key, evidence in sorted(
        registered_trunk_group_evidence_by_key.items(),
        key=lambda item: natural_key(item[0]),
    ):
        index.setdefault(story_key, evidence)
    for story_key, evidence in sorted(
        registered_trunk_group_partial_evidence_by_key.items(),
        key=lambda item: natural_key(item[0]),
    ):
        index.setdefault(story_key, evidence)
    for story_key, evidence in sorted(
        generic_dialog_evidence_by_key.items(),
        key=lambda item: natural_key(item[0]),
    ):
        index.setdefault(story_key, evidence)
    for story_key, evidence in sorted(
        registered_table_dialog_evidence_by_key.items(),
        key=lambda item: natural_key(item[0]),
    ):
        index.setdefault(story_key, evidence)
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
            "relatedMissionId": validation["relatedMissionId"],
            "linkMissionIdsByContentId":
                validation["linkMissionIdsByContentId"],
            "runtimeTrackingContext": validation["runtimeTracking"],
            "nativeMappingId": OFFLINE_EXHAUSTION_MAPPING_ID,
            "gameAssemblySha256":
                OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
            "consumerBoundary": (
                (
                    "the exact SNSDialogTable content graph defines this "
                    "Story file, and an exact SnsTrackingInfo in the named "
                    "runtime mission points to it for HUD/navigation; "
                    "SnsTrackingInfo does not play SNS content, and no "
                    "original-data source assigns it to the "
                    "nominal mission or a branch arm"
                    if validation["runtimeTracking"]
                    else
                    "the exact SNSDialogTable content graph and "
                    "SNSDialogOptionTable routes define this current Story "
                    "file; no exact "
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
        receiver_rows = list(
            unhosted_reading_popup_receivers.get(story_key) or []
        )
        receiver_paths = [
            path
            for receiver in receiver_rows
            for path in receiver.get("nativeEventPaths") or []
            if isinstance(path, dict)
        ]
        interaction_triggers = [
            producer
            for receiver in receiver_rows
            if receiver.get("triggerRecovered") is True
            for producer in receiver.get("interactiveEventProducers") or []
            if isinstance(producer, dict)
        ]
        exact_interaction_trigger = len(interaction_triggers) == 1
        receiver_level_ids = sorted({
            str(receiver.get("levelId") or "")
            for receiver in receiver_rows
            if receiver.get("levelId")
        })
        index[story_key] = {
            "sceneKey": story_key,
            "missionId": text_mission_by_key[story_key],
            "levelId": (
                receiver_level_ids[0]
                if len(receiver_level_ids) == 1
                else None
            ),
            "recoveryStatus":
                (
                    "exact_current_build_interaction_trigger_recovered"
                    if exact_interaction_trigger
                    else "deferred_current_build_offline_surface_exhausted"
                ),
            "evidenceKind":
                (
                    "reading_popup_world_entity_interaction_trigger"
                    if exact_interaction_trigger
                    else (
                        "reading_popup_receiver_without_registered_producer"
                        if receiver_rows
                        else
                        "reading_popup_definition_without_recovered_activator"
                    )
                ),
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
            "unhostedReadingPopupReceivers": receiver_rows,
            "worldEntityInteractionTriggers": interaction_triggers,
            "nativeEventPaths": receiver_paths,
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
                (
                    "an exact WorldEntityRegistry script/slot resolves to a "
                    "complete map interaction whose eventName raises the same "
                    "custom event consumed by ShowUIReadingPopPanel; the "
                    "action's direct _readingPopId resolves through the exact "
                    "ReadingPopUpTable row to this Story file"
                    if exact_interaction_trigger
                    else
                    (
                        "an exact local custom-event receiver reaches "
                        "ShowUIReadingPopPanel with a direct _readingPopId "
                        "matching this ReadingPopUpTable row, but no exact "
                        "registered interactive event producer was decoded"
                        if receiver_rows
                        else
                        "the exact ReadingPopUpTable carrier and "
                        "RichContentTable payload define this current Story file"
                    )
                )
                + (
                    ", while the exact PRTS archive entry provides a second "
                    "non-activating content carrier"
                    if definition.get("prtsDefinition")
                    else ""
                )
                + (
                    "; this proves the map interaction trigger and playback "
                    "receiver, but not a mission/quest owner or mission-step "
                    "chronology"
                    if exact_interaction_trigger
                    else (
                        "; no exact MissionRuntime owner, registered interactive "
                        "custom-event producer, object-index owner, or direct "
                        "caller closes the activation gap"
                        if receiver_rows
                        else
                        "; no exact MissionRuntime, LevelScript/LevelData "
                        "interactive, object-index, or direct native caller "
                        "exposes its activator"
                    )
                )
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
    for story_key, evidence in sorted(
        generic_text_evidence_by_key.items(),
        key=lambda item: natural_key(item[0]),
    ):
        index.setdefault(story_key, evidence)
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
    for story_key, evidence in sorted(
        generic_cutscene_evidence_by_key.items(),
        key=lambda item: natural_key(item[0]),
    ):
        index.setdefault(story_key, evidence)
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
    for story_key, evidence in sorted(
        missionless_native_evidence_by_key.items(),
        key=lambda item: natural_key(item[0]),
    ):
        prior = index.get(story_key)
        evidence, interaction_merged = (
            _merge_exact_interaction_trigger_with_native_playback(
                prior,
                evidence,
            )
        )
        if interaction_merged:
            missionless_native_exclusions[
                "mergedExactInteractionTrigger"
            ].append(story_key)
        elif story_key in index:
            missionless_native_exclusions[
                "supersededWeakerOfflineEvidence"
            ].append(story_key)
        index[story_key] = evidence
    for story_key in sorted(
        set(registered_tree_evidence_by_key) & set(index),
        key=natural_key,
    ):
        registered_tree_exclusions[
            "alreadyRecoveredHigherPrecedenceEvidence"
        ].append(story_key)
        del registered_tree_evidence_by_key[story_key]
    for story_key, evidence in sorted(
        registered_tree_evidence_by_key.items(),
        key=lambda item: natural_key(item[0]),
    ):
        index[story_key] = evidence
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
        related_original_data = (
            mission_related_original_data_by_mission.get(mission_id)
        )
        if related_original_data:
            row["missionRelatedOriginalData"] = related_original_data
    deferred_radio_keys_by_mission: dict[str, set[str]] = defaultdict(set)
    for story_key, row in index.items():
        mission_id = safe_key(row.get("missionId"))
        if mission_id and story_key.startswith("radio_"):
            deferred_radio_keys_by_mission[mission_id].add(story_key)
    registered_trunk_task_topology_by_script: dict[str, dict[str, Any]] = {}
    for evidence_rows in (
        registered_trunk_group_evidence_by_key.values(),
        registered_trunk_group_partial_evidence_by_key.values(),
    ):
        for evidence_row in evidence_rows:
            for context in evidence_row.get("parentLevelContexts") or []:
                runtime = context.get("subGameRuntime")
                topology = (
                    runtime.get("taskTopology")
                    if isinstance(runtime, dict)
                    else None
                )
                script_id = safe_key(
                    topology.get("scriptId")
                    if isinstance(topology, dict)
                    else ""
                )
                if script_id:
                    registered_trunk_task_topology_by_script[script_id] = (
                        topology
                    )
    status.update({
        "status": "active",
        "coreTargetSetSha256": core_target_digest,
        "deferredStoryKeys": len(index),
        "dialogDefinitionRecovery": {
            "pattern": (
                "core isolated target -> mechanical misc_dlg alias -> exact "
                "DialogId registration -> exact hashed DialogTree TextAsset -> "
                "Timeline/action/native/object/binary consumer census"
            ),
            "declaredDefinitionRows": len(
                OFFLINE_EXHAUSTION_DIALOG_DEFINITIONS
            ),
            "declaredExternalContextRows": len(
                dialog_context_definitions
            ),
            "patternDiscoveredDefinitionRows": len(
                registered_tree_definition_facts
            ),
            "patternQualifiedDefinitionRows": len(
                registered_tree_evidence_by_key
            ),
            "carrierAuditTargetSetSha256": carrier_audit_target_digest,
            "currentCoreTargetSetSha256": core_target_digest,
            "carrierAuditReuseMode": "per_story_key_exact_current_source",
            "perObjectDefinitionDeclarationRequired": False,
            "perObjectBinaryTokenDeclarationRequired": False,
            "evidenceBoundary": (
                "declarations are retained only for separately typed external "
                "relationships; definition filenames, hashes, line ids, option "
                "ids, and internal branches are recovered from current original "
                "data and never create mission activation or cross-file order"
            ),
        },
        "missionRelatedOriginalData": (
            mission_related_original_data_by_mission
        ),
        "deferredMissions": sorted({
            row["missionId"]
            for row in index.values()
        }, key=natural_key),
        "deferredRadioStoryKeysByMission": {
            mission: sorted(story_keys, key=natural_key)
            for mission, story_keys
            in sorted(deferred_radio_keys_by_mission.items())
        },
        "genericMissionlessNativePlaybackEvidence": {
            "status": (
                "active"
                if native_playback_index is not None
                else "inactive_native_playback_index_unavailable"
            ),
            "qualifiedStoryKeys": len(
                missionless_native_evidence_by_key
            ),
            "qualifiedMissions": len({
                row["missionId"]
                for row in missionless_native_evidence_by_key.values()
            }),
            "validationFailures": missionless_native_validation_failures,
            "exclusions": {
                name: sorted(set(values), key=natural_key)
                for name, values in missionless_native_exclusions.items()
            },
            "sourcePaths": {
                "gameAssembly": str(source_paths["gameAssembly"]),
            },
            "sourceSha256": {
                "gameAssembly": actual_hashes.get("gameAssembly", ""),
            },
            "mappingId": OFFLINE_EXHAUSTION_MAPPING_ID,
            "graphEffect": "none",
        },
        "genericRadioNegativeConsumerEvidence": {
            "status": (
                "active"
                if native_playback_index is not None
                else "inactive_native_playback_index_unavailable"
            ),
            "qualifiedStoryKeys": len(generic_radio_evidence_by_key),
            "qualifiedMissions": len({
                safe_key(row.get("missionId"))
                for row in generic_radio_evidence_by_key.values()
                if safe_key(row.get("missionId"))
            }),
            "validationFailures": generic_radio_validation_failures,
            "exclusions": {
                name: sorted(set(values), key=natural_key)
                for name, values in generic_radio_exclusions.items()
            },
            "sourcePaths": {
                "radioTable": str(source_paths["radioTable"]),
                "audioDialog": str(source_paths["audioDialog"]),
                "carrierAudit": str(carrier_audit_path),
                "gameAssembly": str(source_paths["gameAssembly"]),
                "globalMetadata": str(source_paths["globalMetadata"]),
            },
            "sourceSha256": {
                "radioTable": actual_hashes.get("radioTable", ""),
                "audioDialog": actual_hashes.get("audioDialog", ""),
                "gameAssembly": actual_hashes.get("gameAssembly", ""),
                "globalMetadata": actual_hashes.get("globalMetadata", ""),
            },
            "carrierAuditTargetSetSha256": core_target_digest,
            "graphEffect": "none",
        },
        "genericMissionlessNpcProxyDialogEvidence": {
            "status": (
                "active"
                if native_playback_index is not None
                else "inactive_native_playback_index_unavailable"
            ),
            "qualifiedStoryKeys": len(generic_npc_proxy_evidence_by_key),
            "qualifiedConsumerRows": sum(
                len(row.get("npcProxyConsumers") or [])
                for row in generic_npc_proxy_evidence_by_key.values()
            ),
            "qualifiedDialogTreeDefinitions": sum(
                row.get("dialogTreeDefinitionStatus")
                == "exact_current_dialog_tree"
                for row in generic_npc_proxy_evidence_by_key.values()
            ),
            "validatedAuthoredOptionRoutes": sum(
                int(
                    ((row.get("optionRouteRecovery") or {}).get("counts") or {}).get(
                        "validatedNormalOptionRoutes", 0
                    )
                )
                for row in generic_npc_proxy_evidence_by_key.values()
            ),
            "failClosedOptionRouteIssues": sum(
                len((row.get("optionRouteRecovery") or {}).get("issues") or [])
                for row in generic_npc_proxy_evidence_by_key.values()
            ),
            "qualifiedMissions": len({
                safe_key(row.get("missionId"))
                for row in generic_npc_proxy_evidence_by_key.values()
                if safe_key(row.get("missionId"))
            }),
            "validationFailures": generic_npc_proxy_validation_failures,
            "exclusions": {
                name: sorted(set(values), key=natural_key)
                for name, values in generic_npc_proxy_exclusions.items()
            },
            "sourcePaths": {
                name: str(source_paths[name])
                for name in (
                    "npcProxyExDataTable",
                    "npcProxyTable",
                    "dialogIdIndex",
                    "gameAssembly",
                    "carrierAudit",
                )
            },
            "sourceSha256": {
                name: actual_hashes.get(name, "")
                for name in (
                    "npcProxyExDataTable",
                    "npcProxyTable",
                    "dialogIdIndex",
                    "gameAssembly",
                )
            },
            "nativeMappingId": NPC_PROXY_DIALOG_SELECTION_MAPPING_ID,
            "carrierAuditTargetSetSha256": core_target_digest,
            "graphEffect": "none",
        },
        "genericMissionNpcProxyTrackingEvidence": {
            "status": mission_tracking_corpus.get("status"),
            "selection": mission_tracking_corpus.get("selection"),
            "selectedRoot": mission_tracking_corpus.get("selectedRoot"),
            "streamingFileCount": mission_tracking_corpus.get(
                "streamingFileCount", 0
            ),
            "persistentFileCount": mission_tracking_corpus.get(
                "persistentFileCount", 0
            ),
            "scannedMissionFileCount": mission_tracking_corpus.get(
                "scannedMissionFileCount", 0
            ),
            "typedRowCount": mission_tracking_corpus.get("typedRowCount", 0),
            "qualifiedRowCount": mission_tracking_corpus.get(
                "qualifiedRowCount", 0
            ),
            "proxyCount": mission_tracking_corpus.get("proxyCount", 0),
            "scanFailureCount": mission_tracking_corpus.get(
                "scanFailureCount", 0
            ),
            "qualifiedStoryKeys": sum(
                bool(row.get("missionNpcProxyTrackingContexts"))
                for row in index.values()
            ),
            "qualifiedContexts": sum(
                len(row.get("missionNpcProxyTrackingContexts") or [])
                for row in index.values()
            ),
            "qualifiedQuestRows": sum(
                len(context.get("rows") or [])
                for row in index.values()
                for context in (
                    row.get("missionNpcProxyTrackingContexts") or []
                )
            ),
            "crossMissionContexts": sum(
                context.get("crossMission") is True
                for row in index.values()
                for context in (
                    row.get("missionNpcProxyTrackingContexts") or []
                )
            ),
            "validationFailures":
                generic_mission_tracking_validation_failures,
            "sourceSetSha256": mission_tracking_corpus.get(
                "sourceSetSha256", ""
            ),
            "relation": "mission_quest_npc_proxy_tracking_context",
            "missionOwnership": False,
            "questPlaybackOwnership": False,
            "orderEvidence": False,
            "graphEffect": "none",
        },
        "genericSnsNegativeConsumerEvidence": {
            "status": (
                "active"
                if native_playback_index is not None
                else "inactive_native_playback_index_unavailable"
            ),
            "qualifiedStoryKeys": len(generic_sns_evidence_by_key),
            "qualifiedAuthoredMissionLinkStoryKeys": len({
                story_key
                for story_key, row in generic_sns_evidence_by_key.items()
                if row.get("evidenceKind") == "sns_authored_mission_link"
            }),
            "qualifiedMissions": len({
                safe_key(row.get("missionId"))
                for row in generic_sns_evidence_by_key.values()
                if safe_key(row.get("missionId"))
            }),
            "validationFailures": generic_sns_validation_failures,
            "exclusions": {
                name: sorted(set(values), key=natural_key)
                for name, values in generic_sns_exclusions.items()
            },
            "sourcePaths": {
                name: str(source_paths[name])
                for name in (
                    "snsDialogTable",
                    "snsOptionTable",
                    "snsChatTable",
                    "carrierAudit",
                    "gameAssembly",
                    "globalMetadata",
                )
            },
            "sourceSha256": {
                name: actual_hashes.get(name, "")
                for name in (
                    "snsDialogTable",
                    "snsOptionTable",
                    "snsChatTable",
                    "gameAssembly",
                    "globalMetadata",
                )
            },
            "carrierAuditTargetSetSha256": core_target_digest,
            "graphEffect": "none",
        },
        "genericReadingPopupNegativeConsumerEvidence": {
            "status": (
                "active"
                if native_playback_index is not None
                else "inactive_native_playback_index_unavailable"
            ),
            "qualifiedStoryKeys": len(generic_text_evidence_by_key),
            "qualifiedMissions": len({
                row["missionId"]
                for row in generic_text_evidence_by_key.values()
            }),
            "validationFailures": generic_text_validation_failures,
            "exclusions": {
                key: sorted(values, key=natural_key)
                for key, values in generic_text_exclusions.items()
            },
            "sourcePaths": {
                "readingPopupTable": str(source_paths["readingPopupTable"]),
                "richContentTable": str(source_paths["richContentTable"]),
                "dialogIdIndex": str(source_paths["dialogIdIndex"]),
                "timelineLineOrders": str(source_paths["timelineLineOrders"]),
                "textAssetRoot": str(cutscene_definition_root),
                "carrierAudit": str(carrier_audit_path),
                "gameAssembly": str(source_paths["gameAssembly"]),
                "globalMetadata": str(source_paths["globalMetadata"]),
            },
            "sourceSha256": {
                name: actual_hashes.get(name, "")
                for name in (
                    "readingPopupTable",
                    "richContentTable",
                    "dialogIdIndex",
                    "timelineLineOrders",
                    "gameAssembly",
                    "globalMetadata",
                )
            },
            "carrierAuditTargetSetSha256": core_target_digest,
            "graphEffect": "none",
        },
        "genericUnregisteredDialogNegativeConsumerEvidence": {
            "status": (
                "active"
                if native_playback_index is not None
                else "inactive_native_playback_index_unavailable"
            ),
            "qualifiedStoryKeys": len(generic_dialog_evidence_by_key),
            "qualifiedRegisteredLineReuseStoryKeys": sum(
                1
                for row in generic_dialog_evidence_by_key.values()
                if row.get("registeredDialogTreeLineCarriers")
            ),
            "qualifiedRegisteredLineReuseCarriers": sum(
                len(row.get("registeredDialogTreeLineCarriers") or [])
                for row in generic_dialog_evidence_by_key.values()
            ),
            "qualifiedMissions": len({
                row["missionId"]
                for row in generic_dialog_evidence_by_key.values()
            }),
            "validationFailures": generic_dialog_validation_failures,
            "exclusions": {
                key: sorted(values, key=natural_key)
                for key, values in generic_dialog_exclusions.items()
            },
            "sourcePaths": {
                "dialogTextTable": str(source_paths["dialogTextTable"]),
                "dialogOptionTable": str(source_paths["dialogOptionTable"]),
                "audioDialog": str(source_paths["audioDialog"]),
                "dialogIdIndex": str(source_paths["dialogIdIndex"]),
                "timelineLineOrders": str(source_paths["timelineLineOrders"]),
                "textAssetRoot": str(cutscene_definition_root),
                "carrierAudit": str(carrier_audit_path),
                "gameAssembly": str(source_paths["gameAssembly"]),
                "globalMetadata": str(source_paths["globalMetadata"]),
            },
            "sourceSha256": {
                name: actual_hashes.get(name, "")
                for name in (
                    "dialogTextTable",
                    "dialogOptionTable",
                    "audioDialog",
                    "dialogIdIndex",
                    "timelineLineOrders",
                    "gameAssembly",
                    "globalMetadata",
                )
            },
            "carrierAuditTargetSetSha256": core_target_digest,
            "graphEffect": "none",
        },
        "genericRegisteredDialogTreeNegativeConsumerEvidence": {
            "status": (
                "active"
                if (
                    native_playback_index is not None
                    and action_story_occurrences is not None
                )
                else "inactive_action_or_native_playback_index_unavailable"
            ),
            "qualifiedStoryKeys": len(registered_tree_evidence_by_key),
            "qualifiedMissions": len({
                row["missionId"]
                for row in registered_tree_evidence_by_key.values()
            }),
            "validationFailures": registered_tree_validation_failures,
            "exclusions": {
                key: sorted(values, key=natural_key)
                for key, values in registered_tree_exclusions.items()
            },
            "sourcePaths": {
                "dialogIdSource": str(source_paths["dialogIdSource"]),
                "dialogIdIndex": str(source_paths["dialogIdIndex"]),
                "textAssetRoot": str(cutscene_definition_root),
                "carrierAudit": str(carrier_audit_path),
                "gameAssembly": str(source_paths["gameAssembly"]),
                "globalMetadata": str(source_paths["globalMetadata"]),
            },
            "sourceSha256": {
                name: actual_hashes.get(name, "")
                for name in (
                    "dialogIdSource",
                    "dialogIdIndex",
                    "gameAssembly",
                    "globalMetadata",
                )
            },
            "actionCensus": {
                "mappingId": "current-build-levelscript-action-story-occurrence-census-v1",
                "qualifiedKeysHaveZeroOccurrences": True,
            },
            "carrierAuditTargetSetSha256": carrier_audit_target_digest,
            "currentCoreTargetSetSha256": core_target_digest,
            "carrierAuditReuseMode": "per_story_key_exact_current_source",
            "graphEffect": "none",
        },
        "genericRegisteredDialogTreeTrunkGroupEvidence": {
            "status": (
                "validation_failed"
                if registered_trunk_group_validation_failures
                else "active"
            ),
            "qualifiedStoryKeys": len(
                registered_trunk_group_evidence_by_key
            ),
            "qualifiedMissions": len({
                row["missionId"]
                for row in registered_trunk_group_evidence_by_key.values()
            }),
            "qualifiedParentDialogTrees": len({
                safe_key(parent.get("sceneKey"))
                for row in registered_trunk_group_evidence_by_key.values()
                for parent in row.get("parentDialogTrees") or []
                if safe_key(parent.get("sceneKey"))
            }),
            "qualifiedLines": sum(
                int(row.get("lineCount") or 0)
                for row in registered_trunk_group_evidence_by_key.values()
            ),
            "consumerExhaustedPartialStoryKeys": sum(
                1
                for row in registered_trunk_group_evidence_by_key.values()
                if row.get("evidenceKind")
                == "partial_registered_dialog_tree_rows_without_current_consumer"
            ),
            "consumerExhaustedUnmatchedDefinitionRows": sum(
                int(row.get("missingLineCount") or 0)
                for row in registered_trunk_group_evidence_by_key.values()
                if row.get("evidenceKind")
                == "partial_registered_dialog_tree_rows_without_current_consumer"
            ),
            "partialStoryKeys": len(
                registered_trunk_group_partial_evidence_by_key
            ),
            "partialMissions": len({
                row["missionId"]
                for row in registered_trunk_group_partial_evidence_by_key.values()
            }),
            "partialParentDialogTrees": len({
                safe_key(parent.get("sceneKey"))
                for row in registered_trunk_group_partial_evidence_by_key.values()
                for parent in row.get("parentDialogTrees") or []
                if safe_key(parent.get("sceneKey"))
            }),
            "partialCoveredLines": sum(
                int(row.get("coveredLineCount") or 0)
                for row in registered_trunk_group_partial_evidence_by_key.values()
            ),
            "partialMissingLines": sum(
                int(row.get("missingLineCount") or 0)
                for row in registered_trunk_group_partial_evidence_by_key.values()
            ),
            "qualifiedParentLevelContexts": sum(
                int(row.get("parentLevelContextCount") or 0)
                for row in registered_trunk_group_evidence_by_key.values()
            ),
            "partialParentLevelContexts": sum(
                int(row.get("parentLevelContextCount") or 0)
                for row in registered_trunk_group_partial_evidence_by_key.values()
            ),
            "qualifiedBlackBoxSubGameRuntimeContexts": sum(
                1
                for row in registered_trunk_group_evidence_by_key.values()
                for context in row.get("parentLevelContexts") or []
                if isinstance(context.get("subGameRuntime"), dict)
            ),
            "partialBlackBoxSubGameRuntimeContexts": sum(
                1
                for row in registered_trunk_group_partial_evidence_by_key.values()
                for context in row.get("parentLevelContexts") or []
                if isinstance(context.get("subGameRuntime"), dict)
            ),
            "distinctBlackBoxTaskTopologyScripts": len(
                registered_trunk_task_topology_by_script
            ),
            "exactCompleteBlackBoxTaskTopologyScripts": sum(
                1
                for topology in registered_trunk_task_topology_by_script.values()
                if topology.get("status") == "exact_complete_task_map"
            ),
            "exactNullBlackBoxTaskTopologyScripts": sum(
                1
                for topology in registered_trunk_task_topology_by_script.values()
                if topology.get("status") == "exact_null_task_map"
            ),
            "decodedBlackBoxTasks": sum(
                int(topology.get("decodedTaskCount") or 0)
                for topology in registered_trunk_task_topology_by_script.values()
            ),
            "decodedBlackBoxTaskConditions": sum(
                int(topology.get("conditionCount") or 0)
                for topology in registered_trunk_task_topology_by_script.values()
            ),
            "partialExactParentDialogPlaybacks": sum(
                len(
                    context.get("subGameRuntime", {}).get(
                        "parentDialogPlayback"
                    ) or []
                )
                for row in registered_trunk_group_partial_evidence_by_key.values()
                for context in row.get("parentLevelContexts") or []
                if isinstance(context.get("subGameRuntime"), dict)
            ),
            "partialDefinitionOnlyParentsInBoundSubGameScripts": sum(
                len(
                    context.get("subGameRuntime", {}).get(
                        "definitionOnlyParentDialogTreeIds"
                    ) or []
                )
                for row in registered_trunk_group_partial_evidence_by_key.values()
                for context in row.get("parentLevelContexts") or []
                if isinstance(context.get("subGameRuntime"), dict)
            ),
            "partialMissingLineFragments": sum(
                len(row.get("missingLineFragments") or [])
                for row in registered_trunk_group_partial_evidence_by_key.values()
            ),
            "validationFailures": (
                registered_trunk_group_validation_failures
            ),
            "exclusions": {
                key: sorted(set(values), key=natural_key)
                for key, values in registered_trunk_group_exclusions.items()
            },
            "sourcePaths": {
                "dialogTextTable": str(source_paths["dialogTextTable"]),
                "dialogIdSource": str(source_paths["dialogIdSource"]),
                "dialogIdIndex": str(source_paths["dialogIdIndex"]),
                "levelBasicInfoTable": str(
                    source_paths["levelBasicInfoTable"]
                ),
                "dungeonTable": str(table_root / "DungeonTable.json"),
                "levelConfigRoot": str(source_paths["levelConfigRoot"]),
                "levelDataRoot": str(source_paths["levelDataRoot"]),
                "levelScriptRoot": str(source_paths["levelScriptRoot"]),
                "subGameInstanceDataTable": str(
                    source_paths["subGameInstanceDataTable"]
                ),
                "scriptTaskExtraInfoTable": str(
                    source_paths["scriptTaskExtraInfoTable"]
                ),
                "textAssetRoot": str(cutscene_definition_root),
                "gameAssembly": str(source_paths["gameAssembly"]),
                "globalMetadata": str(source_paths["globalMetadata"]),
            },
            "sourceSha256": {
                **{
                    name: actual_hashes.get(name, "")
                    for name in (
                        "dialogTextTable",
                        "dialogIdSource",
                        "dialogIdIndex",
                        "gameAssembly",
                        "globalMetadata",
                    )
                },
                "scriptTaskExtraInfoTable": _sha256_file(
                    source_paths["scriptTaskExtraInfoTable"]
                ),
            },
            "nativeMappingId": DIALOG_TREE_TRUNK_GROUP_MAPPING_ID,
            "graphEffect": "none",
        },
        "genericRegisteredTableDialogNegativeConsumerEvidence": {
            "status": (
                "active"
                if (
                    native_playback_index is not None
                    and action_story_occurrences is not None
                )
                else "inactive_action_or_native_playback_index_unavailable"
            ),
            "qualifiedStoryKeys": len(registered_table_dialog_evidence_by_key),
            "qualifiedMissions": len({
                row["missionId"]
                for row in registered_table_dialog_evidence_by_key.values()
            }),
            "validationFailures": registered_table_dialog_validation_failures,
            "exclusions": {
                key: sorted(values, key=natural_key)
                for key, values in registered_table_dialog_exclusions.items()
            },
            "sourcePaths": {
                "dialogIdIndex": str(source_paths["dialogIdIndex"]),
                "dialogTextTable": str(source_paths["dialogTextTable"]),
                "dialogOptionTable": str(source_paths["dialogOptionTable"]),
                "audioDialog": str(source_paths["audioDialog"]),
                "carrierAudit": str(carrier_audit_path),
                "gameAssembly": str(source_paths["gameAssembly"]),
                "globalMetadata": str(source_paths["globalMetadata"]),
            },
            "sourceSha256": {
                name: actual_hashes.get(name, "")
                for name in (
                    "dialogIdIndex",
                    "dialogTextTable",
                    "dialogOptionTable",
                    "audioDialog",
                    "gameAssembly",
                    "globalMetadata",
                )
            },
            "carrierAuditTargetSetSha256": core_target_digest,
            "graphEffect": "none",
        },
        "genericCutsceneDefinitionEvidence": {
            "status": (
                "active"
                if native_playback_index is not None
                else "inactive_native_playback_index_unavailable"
            ),
            "qualifiedStoryKeys": len(generic_cutscene_evidence_by_key),
            "qualifiedMissions": len({
                safe_key(row.get("missionId"))
                for row in generic_cutscene_evidence_by_key.values()
                if safe_key(row.get("missionId"))
            }),
            "validationFailures": generic_cutscene_validation_failures,
            "qualificationDiagnostics": (
                generic_cutscene_qualification_diagnostics
            ),
            "exclusions": {
                name: sorted(set(values), key=natural_key)
                for name, values in generic_cutscene_exclusions.items()
            },
            "sourcePaths": {
                "strIdNumTable": str(source_paths["strIdNumTable"]),
                "numIdStrTable": str(source_paths["numIdStrTable"]),
                "textAssetRoot": str(cutscene_definition_root),
                "carrierAudit": str(carrier_audit_path),
                "gameObjectAudit": str(gameobject_audit_path),
                "reversePptrAudit": str(reverse_pptr_audit_path),
                "gameAssembly": str(source_paths["gameAssembly"]),
                "globalMetadata": str(source_paths["globalMetadata"]),
            },
            "sourceSha256": {
                name: actual_hashes.get(name, "")
                for name in (
                    "strIdNumTable",
                    "numIdStrTable",
                    "gameAssembly",
                    "globalMetadata",
                )
            },
            "carrierAuditTargetSetSha256": core_target_digest,
            "graphEffect": "none",
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
        "deferredCutsceneStoryKeysByMission": {
            mission: sorted(story_keys, key=natural_key)
            for mission, story_keys
            in OFFLINE_EXHAUSTION_CUTSCENES_BY_MISSION.items()
        },
    })
    return index, status

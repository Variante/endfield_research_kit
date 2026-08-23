#!/usr/bin/env python3
"""Build experimental map-recovery datasets for the static WebUI.

Every level in `LevelBasicInfoTable` is recovered the same way, from the same
exact sources, instead of one hand-written builder per map. The join that makes
that possible is the registry id encoding: `WorldEntityRegistry` keys its world
entities, script entities and NPC proxies by a global id whose leading digits
are the level's own `idNum` (`idNum = id // 10**8`), so a level's plottable
entities can be selected without naming the level anywhere in code.

Story files reach the map only through authored identity bindings:

  * `flow.missionStoryConnections` - producer script/slot, exact when the
    registry resolves the entity (see `_story_index`);
  * `flow.mapPins` - authored map pins carrying an exact position plus the
    quests and NPC proxy the pin belongs to;
  * `timelineRecovery.npcProxyDialogAttachments` - a scene bound to a named NPC
    proxy, which the registry places exactly;
  * exact script/slot producers recovered from typed LevelScript actions.

Mission-area pins, quest centroids, script conditions, and spatial proximity
remain useful mission context, but they do not identify the point that plays a
Story file and therefore never add Story files to a map marker.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import struct
import sys
import zlib
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.story_builder.level_bindings import (
    ACTION_ENTITY_FIELD_DIAGNOSTICS_KEY,
    LevelDataNpcPatrolDecodeError,
    build_leveldata_interactive_narrative_story_contexts,
    build_levelscript_registered_action_target_index,
    build_levelscript_unhosted_reading_popup_receiver_index,
    decode_leveldata_npc_patrol_list,
)
from scripts.story_builder.levelscript_binary import decode_levelscript_binary_summary
from scripts.story_builder.native_contracts.cutscene_case_resolution import (
    load_cutscene_case_resolution_contract,
)
from scripts.map_recovery_sources import authored_streaming_scene, isolated_art_source


GAMEPLAY_CONFIG = "export_full/structured/StreamingAssets/Data/Json/GameplayConfig"
REGISTRY_REL = f"{GAMEPLAY_CONFIG}/WorldEntityRegistry.json"
REGISTRY = ROOT / REGISTRY_REL
NPC_PROXY_TABLE_REL = f"{GAMEPLAY_CONFIG}/NpcProxyTable.json"
LEVEL_BASIC_INFO_REL = f"{GAMEPLAY_CONFIG}/LevelBasicInfoTable.json"
MAP_ID_TABLE_REL = f"{GAMEPLAY_CONFIG}/MapIdTable.json"
TELEPORT_TABLE_REL = f"{GAMEPLAY_CONFIG}/LevelScriptTeleportValidationDataTable.json"
READING_POPUP_REL = "export_full/structured/StreamingAssets/Table/ReadingPopUpTable.json"
LEVEL_SCRIPT_DATA = "export_full/structured/StreamingAssets/Data/Json/LevelScriptData"
LEVEL_DATA = "export_full/structured/StreamingAssets/Data/Json/LevelData"
PERSISTENT_LEVEL_DATA = "export_full/structured/Persistent/Data/Json/LevelData"
MISSION_RUNTIME_DIR = "export_full/structured/Persistent/Data/Json/MissionRuntimeAsset"

LEVEL_DESC_REL = "export_full/structured/StreamingAssets/Table/LevelDescTable.json"
I18N_TEXT_REL = "export_full/structured/StreamingAssets/Table/I18nTextTable_{0}.json"
MISSION_NAMES_REL = "webui/data/lang/{0}/missions.json"
TEXT_TABLE_REL = "export_full/structured/StreamingAssets/Table/TextTable.json"
MAP_UI_CONFIG_DIR = "export_full/structured/StreamingAssets/Data/Json/UILevelMapLoadConfig"
MAP_TILE_DIR = "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Texture2D"
MODEL_ROOT_REL = "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Mesh"
MAP_MARK_TEMP_REL = "export_full/structured/StreamingAssets/Table/MapMarkTempTable.json"
MODEL_TABLE_REL = f"{GAMEPLAY_CONFIG}/ModelTable.json"
SPACESHIP_CONST_REL = "export_full/structured/StreamingAssets/Table/SpaceshipConst.json"
FACTORY_BUILDING_REL = "export_full/structured/StreamingAssets/Table/FactoryBuildingTable.json"
FACTORY_BATTLE_REL = "export_full/structured/StreamingAssets/Table/FactoryBattleTable.json"
ENEMY_TEMPLATE_REL = "export_full/structured/StreamingAssets/Table/EnemyTemplateTable.json"
ENEMY_TEMPLATE_DISPLAY_REL = "export_full/structured/StreamingAssets/Table/EnemyTemplateDisplayInfoTable.json"
MISSION_AREA_TABLE_REL = f"{GAMEPLAY_CONFIG}/MissionAreaTable.json"
NATIVE_TRIGGER_FRONTIER_REL = "reports/story/recovery/native_receiver_activation_frontier.json"
_NATIVE_TRIGGER_FRONTIER_CACHE: dict | None = None
_NATIVE_TRIGGER_FRONTIER_CACHE_KEY: tuple[str, int, int] | None = None


def _native_trigger_frontier() -> dict:
    global _NATIVE_TRIGGER_FRONTIER_CACHE, _NATIVE_TRIGGER_FRONTIER_CACHE_KEY
    path = ROOT / NATIVE_TRIGGER_FRONTIER_REL
    try:
        stat = path.stat()
        cache_key = (str(path.resolve()), stat.st_mtime_ns, stat.st_size)
    except OSError:
        cache_key = (str(path.resolve()), -1, -1)
    if _NATIVE_TRIGGER_FRONTIER_CACHE is None or cache_key != _NATIVE_TRIGGER_FRONTIER_CACHE_KEY:
        payload = _load_json(path, {}) or {}
        _NATIVE_TRIGGER_FRONTIER_CACHE = payload if isinstance(payload, dict) else {}
        _NATIVE_TRIGGER_FRONTIER_CACHE_KEY = cache_key
    return _NATIVE_TRIGGER_FRONTIER_CACHE
CAMPFIRE_TELEPORT_DETAIL_IDS = {"int_campfire_v2", "int_campfire_v2_smaller"}

OUT = ROOT / "webui/data/map_recovery"
ACTION_BINDING_REPORT = ROOT / "reports/assets/map_recovery/action_binding_index.json"
MAP_LEVEL_ID = "indie_dg002"
# Map recovery now advances in authored mainline order.  Keep the currently
# recovered scene explicit rather than allowing the largest free-roam map to
# replace it as the page entry point when generated counts change.
MAINLINE_MAP_SCENES = (
    {"missionId": "e0m0", "levelId": MAP_LEVEL_ID},
)
MAP_VARIANT_GROUPS = {
    "base01_lv001": ("base01_lv001", "base01_lv003"),
    "dung01_wrdg001": ("dung01_wrdg001", "dung01_wrdg001_guide"),
}
MISSION_RUNTIME_ASSET = f"{MISSION_RUNTIME_DIR}/e0m0.json"

# An OBJ whose filename contains a level id is useful for inspection in the
# Assets viewer, but it is not a scene placement record. Keep this fallback
# deliberately separate from the HLOD scene contract: a level-matched model
# must never acquire a fabricated translation just because it was exported.
MAX_UNPLACED_MODEL_ASSETS = 24
_MODEL_ASSET_INDEX: dict[Path, list[Path]] = {}
_MAP_TEXT_LOOKUPS: dict[tuple[str, str], dict[str, str]] = {}
_MISSION_AREA_DEFINITIONS: dict[str, list[dict]] | None = None
_WORLD_NARRATIVE_BINDINGS: dict[str, dict[str, list[dict]]] = {}

# A level id is encoded into the leading digits of every registry id it owns.
# `indie_dg002` has idNum 87, so its entities are 8_700_000_000 upward.
REGISTRY_ID_SCALE = 10 ** 8

AUTHORED_REGION_BACKGROUND_SCENES = {"base01", "map01", "map02"}

# A pinned file is published with the strength of the link that produced it, so
# the reader never has to guess whether a file proves the marker or merely
# shares a mission with it. Strong links come from an exact identity match
# (script/slot, mission-area id, registry row); weak links are diagnostic
# proximity or a whole-mission candidate set.
STRONG_RELATIONS = {
    "placement_source",
    "entity_registry",
    "level_script",
    "story_exact_producer",
    "mission_area_definition",
    "mission_runtime",
    "story_script_slot",
    "story_npc_proxy",
    "story_map_pin",
    "story_world_narrative",
    "script_action_target_source",
}

# Within one strength band the list is ordered by how specific the file is to
# the node, so the first entry is the one worth opening. WorldEntityRegistry is
# last of the strong pins: it proves the transform but is a level-wide 7 MB file
# that says nothing about this marker in particular.
RELATION_ORDER = [
    "story_exact_producer",
    "story_npc_proxy",
    "story_script_slot",
    "story_map_pin",
    "story_world_narrative",
    "script_action_target_source",
    "placement_source",
    "story_quest_anchor",
    "story_proximity",
    "mission_area_definition",
    "level_script",
    "story_script_condition",
    "story_script_reference",
    "story_anchor_script",
    "story_mission_area_candidate",
    "story_mission_scope",
    "story_source",
    "mission_runtime",
    "mission_reference",
    "level_definition",
    "entity_registry",
]

DETAIL_ALIAS_MAP = {
    "int_simple_travel_pole": {
        "canonical": "travel_pole_1",
        "zh": "滑索架",
        "en": "Travel Pole",
    },
    "int_fac_battle_cannon_1_dg002": {
        "canonical": "battle_cannon_1",
        "zh": "榴弹塔",
        "en": "Mortar Cannon",
    },
    "int_narrative_empty": {
        "canonical": "narrative_empty",
        "zh": "叙事锚点",
        "en": "Narrative Anchor",
    },
}

# Structural classification of a registry entity. The first matching rule wins,
# so the specific narrative/tomb rules are declared before the broad prefixes.
# `kind` drives the map layer and colour; `label` is what the node shows when no
# better name is recovered. None of these rules claim the entity is reachable in
# play - that stays in `interactionStatus`.
# Structural classification of a registry entity. The first matching rule wins,
# so the specific narrative/tomb rules are declared before the broad prefixes.
# `kind` drives the map layer and colour, `subKind` the second filter level - a
# reader who wants chests but not ore nodes is filtering inside `collectible`,
# not across kinds. `label` is what the node shows when no better name is
# recovered. None of these rules claim the entity is reachable in play; that
# stays in `interactionStatus`.
DETAIL_KIND_RULES: tuple[tuple[str, str, str, str, str], ...] = (
    ("int_system_spaceship_visit_portal", "travel", "spaceship_visit_portal", "访问传送门", "authored_visit_portal"),
    ("int_teleport", "travel", "teleport_point", "传送点", "interactive_type"),
    ("BTomb", "scenery", "tomb", "墓碑", "not_proven_interactive"),
    ("trigger_volume", "trigger", "trigger_volume", "触发区", "automatic_trigger"),
    ("int_trigger", "trigger", "trigger_volume", "触发区", "automatic_trigger"),
    ("battle_cannon", "device", "cannon", "榴弹塔", "interaction_unresolved"),
    ("int_narrative", "narrative", "narrative_anchor", "叙事锚点", "narrative_anchor"),
    ("int_trchest", "collectible", "chest", "宝箱", "interactive_type"),
    ("int_woodenbox", "collectible", "crate", "木箱", "interactive_type"),
    ("int_goldcoin", "collectible", "currency", "货币", "interactive_type"),
    ("int_shards", "collectible", "shards", "碎片", "interactive_type"),
    ("int_collection", "collectible", "gathering", "采集物", "interactive_type"),
    ("int_simple_travel_pole", "travel", "travel_pole", "滑索架", "interactive_type"),
    ("int_rope", "travel", "rope", "绳索", "interactive_type"),
    ("int_jumpmachine", "travel", "jump_pad", "弹射装置", "interactive_type"),
    ("int_lifter", "travel", "lift", "升降台", "interactive_type"),
    ("int_accelerate", "travel", "speed_pad", "加速带", "interactive_type"),
    ("int_platform", "travel", "platform", "平台", "interactive_type"),
    ("int_move", "travel", "mover", "移动装置", "interactive_type"),
    ("int_doodad", "scenery", "doodad", "场景物件", "not_proven_interactive"),
    ("int_stain", "scenery", "stain", "痕迹", "not_proven_interactive"),
    ("int_footprint", "scenery", "footprint", "足迹", "not_proven_interactive"),
    ("int_door", "device", "door", "门", "interactive_type"),
    ("int_switch", "device", "switch", "开关", "interactive_type"),
    ("int_laser", "device", "laser", "激光装置", "interactive_type"),
    ("int_fac", "device", "facility", "设施", "interaction_unresolved"),
    ("npc_obj", "npc", "npc_object", "NPC 物件", "interaction_unresolved"),
    ("eny_", "enemy", "enemy", "敌人", "not_user_interactive"),
)

# Fallback when no detailId rule matches. entityType is the registry's own
# coarse classification, so it is a weaker but still sourced answer.
ENTITY_TYPE_RULES = {
    16: ("enemy", "enemy", "敌人", "not_user_interactive"),
    32: ("device", "interactive", "可交互物", "interaction_unresolved"),
    128: ("scenery", "prop", "场景物件", "not_proven_interactive"),
    256: ("device", "device", "装置", "interaction_unresolved"),
}

# Level id families, used only to group the published map list for the reader.
# The two surface regions are named by the levels' own recovered display names
# (LevelDescTable + I18nTextTable): map01's levels all sit in 四号谷地
# (Valley-IV) and map02's in 武陵 (Wuling).
LEVEL_FAMILY_RULES = (
    ("map01", "四号谷地 / Valley-IV Map01"),
    ("map02", "武陵 / Wuling Map02"),
    ("base01", "基地 / Base01"),
    ("dung01", "副本 / Dungeon 01"),
    ("dung02", "副本 / Dungeon 02"),
    ("dung_", "副本 / Dungeon"),
    ("indie", "独立场景 / Indie"),
    ("blackbox", "黑箱教学 / Blackbox"),
)


def _canonical_detail(detail_id: str) -> dict[str, str] | None:
    if not detail_id:
        return None
    if detail_id in DETAIL_ALIAS_MAP:
        return dict(DETAIL_ALIAS_MAP[detail_id])
    if detail_id.startswith("int_fac_battle_cannon"):
        return {
            "canonical": detail_id.replace("int_fac_", ""),
            "zh": "榴弹塔",
            "en": "Mortar Cannon",
        }
    return None


def _classify_entity(detail_id: str, entity_type: object) -> tuple[str, str, str, str]:
    """Return `(kind, subKind, label, interactionStatus)` for a registry entity."""
    detail = str(detail_id or "")
    if detail == "int_empty":
        return "empty_slot", "unresolved_empty_slot", "未解析空槽", "empty_interactive_shell"
    if detail.startswith("int_fac_battle_cannon"):
        return "device", "grenade_tower", "榴弹塔", "authored_combat_device"
    if detail in CAMPFIRE_TELEPORT_DETAIL_IDS:
        return "travel", "campfire_teleport", "营火传送点", "teleport_related_map_mark"
    for needle, kind, sub_kind, label, interaction in DETAIL_KIND_RULES:
        if needle in detail:
            return kind, sub_kind, label, interaction
    if isinstance(entity_type, int) and entity_type in ENTITY_TYPE_RULES:
        return ENTITY_TYPE_RULES[entity_type]
    return "scenery", "unclassified", "未分类实体", "interaction_unresolved"


_ENTITY_NAMES: dict[str, dict[str, str]] = {}
_STORY_TITLES: dict[tuple[str, str], str] = {}


def _entity_display_name(detail_id: object, language: str) -> str:
    """Resolve exact localized enemy names; never manufacture one from an id."""
    detail = str(detail_id or "")
    if not detail.startswith("eny_"):
        return ""
    lang = language.upper()
    if lang not in _ENTITY_NAMES:
        table = _load_json(ROOT / ENEMY_TEMPLATE_DISPLAY_REL, {}) or {}
        i18n = _load_json(ROOT / I18N_TEXT_REL.format(lang), {}) or {}
        names: dict[str, str] = {}
        for entity_id, row in table.items():
            if not isinstance(row, dict):
                continue
            for field in ("name", "nickname"):
                ref = row.get(field) or {}
                text = i18n.get(str(ref.get("id"))) if isinstance(ref, dict) else None
                if isinstance(text, str) and text.strip():
                    names[str(entity_id)] = text.strip()
                    break
        _ENTITY_NAMES[lang] = names
    return _ENTITY_NAMES[lang].get(detail, "")


def _story_display_title(language: str, story_key: object) -> str:
    """Use the generated Story title, which already owns localization rules."""
    key = str(story_key or "")
    cache_key = (language.upper(), key)
    if cache_key in _STORY_TITLES:
        return _STORY_TITLES[cache_key]
    path = _conv_file_for_key(language, key)
    payload = _load_json(ROOT / path, {}) if path else {}
    title = str((payload or {}).get("title") or "").strip()
    _STORY_TITLES[cache_key] = title
    return title


def _interactive_semantic_files(detail_id: object) -> list[dict]:
    """Publish only exact table evidence supporting a specific interaction type."""
    detail = str(detail_id or "")
    if detail in CAMPFIRE_TELEPORT_DETAIL_IDS:
        return [
            _related(MAP_MARK_TEMP_REL, "interactive_type", "mark_sp_campfire is authored as teleport-related"),
            _related(TEXT_TABLE_REL, "interactive_type", "CS_TELEPORT_TO_CAMPFIRE_TOAST names campfire teleport"),
        ]
    if detail == "int_system_spaceship_visit_portal":
        return [
            _related(MODEL_TABLE_REL, "interactive_type", "exact interactive model id and portal prefab"),
            _related(SPACESHIP_CONST_REL, "interactive_type", "spaceship visit mode declaration"),
        ]
    if detail.startswith("int_fac_battle_cannon"):
        return [
            _related(FACTORY_BUILDING_REL, "interactive_type", "exact battle-cannon building declaration"),
            _related(FACTORY_BATTLE_REL, "interactive_type", "exact combat skill and attack-range declaration"),
            _related(MODEL_TABLE_REL, "interactive_model", "exact interactive post-model prefab"),
        ]
    if detail.startswith("eny_"):
        return [
            _related(ENEMY_TEMPLATE_REL, "entity_type", "exact enemy template declaration"),
            _related(ENEMY_TEMPLATE_DISPLAY_REL, "entity_name", "exact localized enemy display-name reference"),
            _related(MODEL_TABLE_REL, "entity_model", "enemy post-model identity when available"),
        ]
    if "BTomb" in detail:
        return [_related(MODEL_TABLE_REL, "scenery_model", "exact narrative tomb post-model family")]
    return []


def _exact_story_trigger_markers(level_id: str, language: str) -> list[dict]:
    """Project validated local Story trigger shapes without inventing ownership."""
    report = _native_trigger_frontier()
    markers: list[dict] = []
    markers_by_shape: dict[tuple[str, str, str], dict] = {}
    coverage_rows = (report.get("storyTriggerZoneCoverage") or {}).get("rows") or []
    for receiver in coverage_rows or report.get("rows") or []:
        if not isinstance(receiver, dict):
            continue
        receiver_level = str(receiver.get("levelId") or "")
        if receiver_level and receiver_level != level_id:
            continue
        confirmations = (
            [receiver]
            if receiver.get("storyKey") and isinstance(receiver.get("observations"), list)
            else receiver.get("storyTriggerZoneConfirmations") or []
        )
        for confirmation in confirmations:
            if not isinstance(confirmation, dict) or confirmation.get("status") not in {
                "exact_local_trigger_volume", "multiple_or_ambiguous_trigger_zones",
            }:
                continue
            story_key = str(confirmation.get("storyKey") or "")
            mission_match = re.search(r"(?:^|_)([a-z]+\d+m\d+(?:d\d+)?)(?:_|$)", story_key, re.IGNORECASE)
            mission_contexts = [mission_match.group(1)] if mission_match else []
            for observation in confirmation.get("observations") or []:
                if not isinstance(observation, dict) or observation.get("status") != "exact_local_trigger_volume":
                    continue
                script_id = str(observation.get("scriptId") or "")
                source_file = str(observation.get("sourceFile") or "")
                slot_raw = observation.get("triggerSlotIdFilter")
                context = observation.get("triggerVolumeContext") or {}
                volume = observation.get("triggerVolume") or {}
                playback = observation.get("playbackControlPathEvidence") or {}
                if (
                    str(observation.get("levelId") or "") != level_id
                    or not script_id or Path(source_file).stem != script_id
                    or not isinstance(slot_raw, int) or isinstance(slot_raw, bool) or slot_raw <= 0
                    or context.get("status") != "exact_local_levelscript_trigger_volume_without_foreign_identity"
                    or context.get("scriptIdVerified") is not True
                    or context.get("matchedSlotIds") != [slot_raw]
                    or context.get("missingSlotIds") not in (None, [])
                    or context.get("ambiguousSlotIds") not in (None, [])
                    or volume.get("slotId") != slot_raw
                    or volume.get("triggerVolumeType") != "Leader"
                    or (confirmation.get("status") == "multiple_or_ambiguous_trigger_zones"
                        and playback.get("status") != "exact_trigger_rooted_playback")
                ):
                    continue
                slot_id = str(slot_raw)
                for shape_index, shape in enumerate(observation.get("decodedShape") or []):
                    position = _finite_position((shape or {}).get("position"))
                    shape_type = str((shape or {}).get("shapeType") or "")
                    key = (script_id, slot_id, str((shape or {}).get("offset") or shape_index))
                    if not position or shape_type not in {"Box", "Sphere", "PolyLine"}:
                        continue
                    existing = markers_by_shape.get(key)
                    if existing is not None:
                        if story_key and story_key not in existing["sceneKeys"]:
                            existing["sceneKeys"].append(story_key)
                        existing["missionContexts"] = sorted(set(
                            existing["missionContexts"] + mission_contexts
                        ))
                        existing["relatedFiles"] = _sorted_related(_merge_related(
                            existing["relatedFiles"],
                            [
                                _related(source_file, "level_script", "serialized trigger volume and local event receiver"),
                                _related(_conv_file_for_key(language, story_key), "story_exact_trigger", "Story played by this exact local trigger receiver"),
                                _related(NATIVE_TRIGGER_FRONTIER_REL, "native_validation", "current-build validated trigger selector and decoded shape"),
                            ],
                        ))
                        if source_file:
                            existing["sourceFiles"] = sorted(set(
                                (existing.get("sourceFiles") or []) + [source_file]
                            ))
                        continue
                    row = {
                        "kind": "trigger", "subKind": "exact_story_trigger_volume",
                        "label": "剧情触发区", "identity": f"story_trigger:{script_id}:{slot_id}:{shape_index}",
                        "position": position, "detailId": f"{script_id}#{slot_id}",
                        "interactionStatus": "automatic_trigger",
                        "evidence": "exact current-build local LevelScript trigger volume",
                        "scriptId": script_id, "triggerSlotId": slot_id,
                        "triggerIdentityDomain": "LevelScriptData.triggerVolumes local slot",
                        "registryIdentityStatus": "not_applicable",
                        "triggerShape": {
                            "type": shape_type.lower(), "position": position,
                            "rotation": (shape or {}).get("rotation") or {},
                            "size": (shape or {}).get("size") or {}, "radius": (shape or {}).get("radius"),
                            "polyLinePoints": (
                                ((shape or {}).get("polyLinePoints") or {}).get("points")
                                or []
                            ),
                        },
                        "sceneKeys": [story_key] if story_key else [],
                        "missionContexts": mission_contexts,
                        "missionContextStatus": "nominal Story id context; receiver mission ownership unresolved",
                        "storyRelation": "exact_local_trigger_event; mission ownership unresolved",
                        "storyTriggerMultiplicityStatus": confirmation.get("status"),
                        "playbackControlPathEvidence": playback or None,
                        "relatedFiles": _sorted_related(_merge_related([], [
                            _related(source_file, "level_script", "serialized trigger volume and local event receiver"),
                            _related(_conv_file_for_key(language, story_key), "story_exact_trigger", "Story played by this exact local trigger receiver"),
                            _related(NATIVE_TRIGGER_FRONTIER_REL, "native_validation", "current-build validated trigger selector and decoded shape"),
                        ])),
                    }
                    if source_file:
                        row["sourceFiles"] = [source_file]
                        row["source"] = source_file
                    markers.append(row)
                    markers_by_shape[key] = row
    return markers


def _gender_select_casefold_trigger_markers(level_id: str, language: str) -> list[dict]:
    """Project only the reviewed, build-locked GenderSelect playback bridge."""
    if level_id != "indie_dg002":
        return []
    audit = load_cutscene_case_resolution_contract()
    if audit.get("status") != "validated":
        return []
    bridge = ((audit.get("nativeContract") or {}).get("genderSelectBridge") or {})
    script = bridge.get("levelScript") or {}
    if (
        bridge.get("status") != "validated"
        or bridge.get("storyKey") != "cutscene_e0m0_1"
        or bridge.get("conditionalPlayback") is not True
        or bridge.get("suppliesMissionOrQuestOwnership") is not False
        or script.get("levelId") != level_id
        or script.get("scriptId") != 8700020000
        or script.get("headerLocalId") != 12
        or script.get("triggerSlotId") != 80001
        or script.get("switchLocalId") != 13
        or script.get("switchCase") != 0
        or script.get("actionLocalId") != 16
        or script.get("actionName") != "StartGenderSelect"
    ):
        return []
    source_file = str(script.get("sourceFile") or "")
    try:
        data = (ROOT / source_file).read_bytes()
    except OSError:
        return []
    if hashlib.sha256(data).hexdigest().upper() != script.get("sourceSha256"):
        return []
    summary = decode_levelscript_binary_summary(data, int(script["scriptId"]))
    details = summary.get("triggerVolumesDetails") or {}
    volumes = [row for row in details.get("volumes") or [] if (
        isinstance(row, dict)
        and row.get("slotId") == script["triggerSlotId"]
        and row.get("keySlotId") == script["triggerSlotId"]
        and row.get("triggerVolumeType") == "Leader"
    )]
    if details.get("parseStatus") != "decoded" or len(volumes) != 1:
        return []
    shapes = ((volumes[0].get("shapeList") or {}).get("shapes") or [])
    if len(shapes) != 1:
        return []
    shape = shapes[0]
    position = _finite_position(shape.get("position"))
    if not position or shape.get("shapeType") not in {"Box", "Sphere", "PolyLine"}:
        return []
    story_key = str(bridge["storyKey"])
    return [{
        "kind": "trigger", "subKind": "exact_story_trigger_volume",
        "label": "剧情触发区",
        "identity": "story_trigger:8700020000:80001:gender_select",
        "position": position, "detailId": "8700020000#80001",
        "interactionStatus": "automatic_trigger",
        "evidence": "exact build-locked GenderSelect phase playback bridge",
        "scriptId": "8700020000", "triggerSlotId": "80001",
        "triggerIdentityDomain": "LevelScriptData.triggerVolumes local slot",
        "registryIdentityStatus": "not_applicable",
        "triggerShape": {
            "type": str(shape.get("shapeType") or "").lower(),
            "position": position, "rotation": shape.get("rotation") or {},
            "size": shape.get("size") or {}, "radius": shape.get("radius"),
            "polyLinePoints": ((shape.get("polyLinePoints") or {}).get("points") or []),
        },
        "sceneKeys": [story_key], "missionContexts": ["e0m0"],
        "missionContextStatus": "nominal Story id context; receiver mission ownership unresolved",
        "storyRelation": "exact_conditional_gender_select_phase_playback",
        "storyTriggerMultiplicityStatus": "exact_local_trigger_volume",
        "playbackControlPathEvidence": {
            "status": "exact_build_locked_gender_select_phase_bridge",
            "headerLocalId": 12, "switchLocalId": 13, "switchCase": 0,
            "actionLocalId": 16, "nativeMappingId": bridge.get("nativeMappingId"),
            "caseInsensitiveAssociation": "accepted_unique_ascii_case_insensitive",
            "conditionalPlayback": True, "noSiblingInheritance": True,
        },
        "relatedFiles": _sorted_related(_merge_related([], [
            _related(source_file, "level_script", "exact Leader trigger and StartGenderSelect control path"),
            _related(_conv_file_for_key(language, story_key), "story_exact_trigger", "case-insensitive GenderSelect phase playback"),
            _related(str(audit.get("sourceFile") or ""), "native_validation", "build-locked phase and cutscene lookup bridge"),
        ])),
        "sourceFiles": [source_file], "source": source_file,
    }]


_SPATIAL_SPAWNER_EVENT_TYPES = {
    "LevelEvent_OnSpawnerComplete",
    "LevelEvent_OnSpawnerEntityDie",
    "LevelEvent_OnSpawnerEntityDieStart",
    "LevelEvent_OnSpawnerEntityDieEnd",
    "LevelEvent_OnSpawnerEntitySpawn",
    "LevelEvent_OnSpawnerGroupBegin",
    "LevelEvent_OnSpawnerGroupComplete",
    "LevelEvent_OnSpawnerPause",
    "LevelEvent_OnSpawnerStart",
    "LevelEvent_OnSpawnerWaveBegin",
    "LevelEvent_OnSpawnerWaveComplete",
}


def _exact_story_spawner_markers(level_id: str, language: str) -> list[dict]:
    """Join exact SpawnerPtr event filters to typed LevelData host transforms."""
    report = _native_trigger_frontier()
    stories_by_id: dict[int, list[dict]] = {}
    for row in (report.get("storyTriggerZoneCoverage") or {}).get("rows") or []:
        if not isinstance(row, dict):
            continue
        story_key = str(row.get("storyKey") or "")
        for observation in row.get("observations") or []:
            detail = observation.get("eventDetail") or {}
            event_name = str(observation.get("eventName") or detail.get("type") or "")
            spawner_id = detail.get("spawnerFilterId")
            if (
                not story_key
                or str(observation.get("levelId") or "") != level_id
                or observation.get("status") != "exact_non_spatial_event_trigger"
                or event_name not in _SPATIAL_SPAWNER_EVENT_TYPES
                or detail.get("type") != event_name
                or detail.get("payloadDecodeStatus") != "exact_complete_subtype"
                or detail.get("payloadSchemaStatus") != "exact_current_build_memorypack_fields"
                or detail.get("payloadSchemaMappingId")
                != "gameassembly-2026-07-17-memorypack-native-event-fields"
                or not isinstance(spawner_id, int)
                or isinstance(spawner_id, bool)
                or spawner_id <= 0
            ):
                continue
            stories_by_id.setdefault(spawner_id, []).append({
                "storyKey": story_key,
                "eventName": event_name,
                "sourceFile": observation.get("sourceFile"),
                "sourceSha256": observation.get("sourceSha256"),
                "headerLocalId": observation.get("listenerHeaderLocalId"),
                "playbackControlPathEvidence": observation.get("playbackControlPathEvidence"),
            })
    if not stories_by_id:
        return []

    leveldata_roots = [
        ROOT / "export_full/structured/StreamingAssets/Data/Json/LevelData" / level_id,
        ROOT / "export_full/structured/Persistent/Data/Json/LevelData" / level_id,
    ]
    markers: list[dict] = []
    for spawner_id, bindings in sorted(stories_by_id.items()):
        config_matches = list((ROOT / "export_full/structured/StreamingAssets/Data/Json/SpawnerConfig" / level_id).glob(
            f"sc_{level_id}_{spawner_id}.json"
        ))
        if len(config_matches) != 1:
            continue
        name = f"sc_{level_id}_{spawner_id}".encode("ascii")
        host_rows: list[dict] = []
        for root in leveldata_roots:
            if not root.is_dir():
                continue
            for path in root.glob("*.json"):
                try:
                    data = path.read_bytes()
                except OSError:
                    continue
                cursor = 0
                while True:
                    offset = data.find(name, cursor)
                    if offset < 0:
                        break
                    cursor = offset + 1
                    end = offset + len(name)
                    if (
                        offset < 4
                        or int.from_bytes(data[offset - 4:offset], "little") != len(name)
                        or end + 25 > len(data)
                        or data[end] != 0
                    ):
                        continue
                    values = struct.unpack_from("<6f", data, end + 1)
                    if not all(math.isfinite(value) for value in values):
                        continue
                    host_rows.append({
                        "sourceFile": str(path.relative_to(ROOT)).replace("\\", "/"),
                        "sourceSha256": hashlib.sha256(data).hexdigest(),
                        "recordOffset": offset - 4,
                        "position": {"x": values[0], "y": values[1], "z": values[2]},
                        "rotation": {"x": values[3], "y": values[4], "z": values[5]},
                    })
        transforms = {
            tuple(row["position"].values()) + tuple(row["rotation"].values())
            for row in host_rows
        }
        logical_hosts = {Path(row["sourceFile"]).name for row in host_rows}
        if len(transforms) != 1 or len(logical_hosts) != 1:
            continue
        host = host_rows[0]
        story_keys = sorted({row["storyKey"] for row in bindings})
        markers.append({
            "kind": "trigger", "subKind": "exact_spawner_event_host",
            "label": "剧情生成器",
            "identity": f"spawner:{level_id}:{spawner_id}",
            "position": host["position"], "rotation": host["rotation"],
            "detailId": str(spawner_id), "sceneKeys": story_keys,
            "interactionStatus": "runtime_spawner_event",
            "evidence": "exact SpawnerPtr event filter and typed LevelData host transform",
            "storyRelation": "exact_spawner_event_host; mission ownership unresolved",
            "spawnerId": spawner_id, "spawnerEventStoryBindings": bindings,
            "missionContexts": sorted({
                match.group(1) for key in story_keys
                if (match := re.search(r"(?:^|_)([a-z]+\d+m\d+(?:d\d+)?)(?:_|$)", key, re.I))
            }),
            "relatedFiles": _sorted_related(_merge_related([], [
                _related(host["sourceFile"], "level_data", "typed spawner host transform"),
                _related(str(config_matches[0].relative_to(ROOT)).replace("\\", "/"), "spawner_config", "exact SpawnerConfig identity"),
                *[
                    _related(_conv_file_for_key(language, key), "story_exact_spawner", "Story played by exact SpawnerPtr event")
                    for key in story_keys
                ],
            ])),
            "sourceFiles": sorted({host["sourceFile"], str(config_matches[0].relative_to(ROOT)).replace("\\", "/")}),
            "source": host["sourceFile"],
        })
    return markers


_EXACT_ENTITY_EVENT_TYPES = {
    "EntityEvent_OnInteractiveStateChanged",
    "EntityEvent_OnSavePropertyChanged",
    "EntityEvent_OnCustomEventNew",
    "EntityEvent_OnBeingScanned",
    "EntityEvent_OnEntityDestroy",
    "EntityEvent_OnEntityStart",
    "EntityEvent_OnHpChanged",
    "EntityEvent_OnIntUnlocked",
    "EntityEvent_OnIntUnlockFailed",
    "EntityEvent_OnUIInteract",
    "LevelEvent_OnAnyEntityDie",
    "LevelEvent_OnEntityHpChanged",
    "LevelEvent_OnEnemyInFight",
    "LevelEvent_OnSpecificEntityDie",
    "LevelEvent_OnSpecificEntityListDie",
}


def _exact_story_entity_event_index(level_id: str) -> dict[str, list[dict]]:
    """Index exact specified-entity Story events by registry identity.

    These events do not own trigger geometry, but their current-build payload
    names one constant EntityPtr.  Publication remains attached to the exact
    WorldEntityRegistry marker and does not imply mission ownership, event
    firing, or Story order.
    """
    report = _native_trigger_frontier()
    index: dict[str, list[dict]] = {}
    for row in (report.get("storyTriggerZoneCoverage") or {}).get("rows") or []:
        if not isinstance(row, dict):
            continue
        story_key = str(row.get("storyKey") or "")
        if not story_key:
            continue
        for observation in row.get("observations") or []:
            if (
                not isinstance(observation, dict)
                or observation.get("status") not in {
                    "exact_non_spatial_event_trigger",
                    "non_spatial_event_payload_unresolved",
                }
                or str(observation.get("levelId") or "") != level_id
            ):
                continue
            detail = observation.get("eventDetail") or {}
            event_name = str(observation.get("eventName") or detail.get("type") or "")
            if (
                event_name not in _EXACT_ENTITY_EVENT_TYPES
                or detail.get("payloadSchemaStatus") not in {
                    "exact_current_build_memorypack_fields",
                    "exact_current_build_entity_event_scope_fields",
                }
                or detail.get("serverExchange") is not False
                or detail.get("serializedMissionOrQuestId") is not False
            ):
                continue
            if (
                detail.get("payloadSchemaStatus")
                == "exact_current_build_entity_event_scope_fields"
                and not event_name.startswith("EntityEvent_")
            ):
                continue

            pointers: list[dict] = []
            if event_name.startswith("EntityEvent_"):
                validate = detail.get("validateParam") or {}
                if not (
                    detail.get("entityEventScope") == "specified-entity"
                    and detail.get("triggerTarget") == "SPECIFY_ENTITY"
                    and detail.get("targetEntityListPresent") is False
                    and detail.get("targetEntityListOutputPresent") is False
                    and validate.get("constValue") is True
                    and validate.get("idRef") == -1
                    and validate.get("paramSource") == 0
                    and validate.get("path") is None
                ):
                    continue
                pointer = detail.get("targetEntity") or {}
                param = detail.get("targetEntityParam") or {}
                if not (
                    param.get("idRef") == -1
                    and param.get("paramSource") == 0
                    and param.get("path") is None
                ):
                    continue
                pointers = [pointer]
            elif event_name == "LevelEvent_OnEntityHpChanged":
                pointers = list(detail.get("entityFilter") or [])
            elif event_name == "LevelEvent_OnAnyEntityDie":
                if not (
                    detail.get("filterByList") is True
                    and detail.get("isMonsterFilter") is True
                    and detail.get("payloadShape")
                    == "constant-entity-list-and-bool-filters-exact-eof"
                ):
                    continue
                pointers = list(detail.get("entityListFilter") or [])
            elif event_name == "LevelEvent_OnSpecificEntityDie":
                pointer = detail.get("entityFilter") or {}
                if not (
                    pointer.get("idRef") == -1
                    and pointer.get("paramSource") == 0
                    and pointer.get("path") is None
                ):
                    continue
                pointers = [pointer]
            elif event_name == "LevelEvent_OnSpecificEntityListDie":
                if detail.get("payloadShape") != "specific-constant-entity-list-exact-eof":
                    continue
                pointers = list(detail.get("entityListFilter") or [])
            elif event_name == "LevelEvent_OnEnemyInFight":
                if detail.get("payloadShape") not in {
                    "enemy-in-fight-constant-entity-list-exact-eof",
                    "enemy-in-fight-constant-entity-list-exact-prefix",
                }:
                    continue
                pointers = list(detail.get("entityListFilter") or [])

            for pointer in pointers:
                if not isinstance(pointer, dict):
                    continue
                logic_id = pointer.get("logicId")
                slot_id = pointer.get("slotId")
                use_slot = pointer.get("useSlotId")
                identity = ""
                if (
                    use_slot is True
                    and logic_id == 0
                    and isinstance(slot_id, int)
                    and not isinstance(slot_id, bool)
                    and slot_id > 0
                ):
                    script_id = str(observation.get("scriptId") or "")
                    if script_id:
                        identity = f"script:{script_id}:{slot_id}"
                elif (
                    use_slot is False
                    and isinstance(logic_id, int)
                    and not isinstance(logic_id, bool)
                    and logic_id > 0
                    and slot_id == 0
                ):
                    identity = f"world:{logic_id}"
                if not identity:
                    continue
                index.setdefault(identity, []).append({
                    "storyKey": story_key,
                    "eventName": event_name,
                    "sourceFile": observation.get("sourceFile"),
                    "sourceSha256": observation.get("sourceSha256"),
                    "scriptId": observation.get("scriptId"),
                    "headerLocalId": observation.get(
                        "listenerHeaderLocalId",
                        observation.get("headerLocalId"),
                    ),
                    "playbackControlPathEvidence": observation.get(
                        "playbackControlPathEvidence"
                    ),
                    "nativeMappingId": detail.get("payloadSchemaMappingId"),
                    "identity": identity,
                    "status": "exact_entity_event_target",
                    "ownership": False,
                    "activation": False,
                    "orderEvidence": False,
                })
    return index


def _active_leveldata_files(level_id: str) -> list[Path]:
    """Return complete-file Streaming/Persistent LevelData overlays."""
    selected: dict[str, Path] = {}
    for root in (ROOT / LEVEL_DATA, ROOT / PERSISTENT_LEVEL_DATA):
        level_dir = root / level_id
        if not level_dir.is_dir():
            continue
        for path in sorted(level_dir.glob("*.json")):
            selected[path.name] = path
    return [selected[name] for name in sorted(selected)]


def _leveldata_patrols_by_id(level_id: str) -> dict[int, list[dict]] | None:
    """Decode every active LevelData patrol list or fail closed for the level."""
    patrols_by_id: dict[int, list[dict]] = {}
    for path in _active_leveldata_files(level_id):
        try:
            data = path.read_bytes()
            decoded = decode_leveldata_npc_patrol_list(data)
        except (OSError, LevelDataNpcPatrolDecodeError):
            # An undecoded active file could hide a competing patrol id.
            return None
        try:
            source_file = str(path.relative_to(ROOT)).replace("\\", "/")
        except ValueError:
            source_file = str(path).replace("\\", "/")
        for patrol in decoded.get("patrols") or []:
            patrol_id = patrol.get("patrolId")
            if not isinstance(patrol_id, int) or isinstance(patrol_id, bool):
                continue
            patrols_by_id.setdefault(patrol_id, []).append({
                **patrol,
                "sourceFile": source_file,
                "sourceSha256": hashlib.sha256(data).hexdigest().upper(),
            })
    return patrols_by_id


def _exact_story_proxy_patrol_checkpoint_contexts(level_id: str) -> list[dict]:
    """Resolve exact proxy-patrol listeners to authored patrol checkpoints."""
    patrols_by_id = _leveldata_patrols_by_id(level_id)
    if patrols_by_id is None:
        return []

    contexts: list[dict] = []
    for row in (_native_trigger_frontier().get("storyTriggerZoneCoverage") or {}).get("rows") or []:
        if not isinstance(row, dict) or not row.get("storyKey"):
            continue
        for observation in row.get("observations") or []:
            detail = observation.get("eventDetail") if isinstance(observation, dict) else None
            if not (
                isinstance(detail, dict)
                and observation.get("status") == "exact_non_spatial_event_trigger"
                and observation.get("levelId") == level_id
                and observation.get("eventName") == "LevelEvent_OnProxyPatrolCheckpointReach"
                and detail.get("payloadSchemaStatus") == "exact_current_build_memorypack_fields"
                and detail.get("payloadSchemaMappingId")
                == "gameassembly-2026-07-17-memorypack-native-event-fields"
                and detail.get("serverExchange") is False
                and detail.get("serializedMissionOrQuestId") is False
                and detail.get("payloadShape") in {
                    "constant-proxy-patrol-checkpoint-and-outputs-exact-eof",
                    "constant-proxy-patrol-checkpoint-and-outputs-exact-prefix",
                }
                and isinstance(detail.get("patrolIdFilter"), int)
                and not isinstance(detail.get("patrolIdFilter"), bool)
                and detail.get("patrolIdFilter") > 0
                and isinstance(detail.get("pointIndexFilter"), int)
                and not isinstance(detail.get("pointIndexFilter"), bool)
                and detail.get("pointIndexFilter") >= 0
                and str(detail.get("proxyIdFilter") or "")
            ):
                continue
            patrol_id = int(detail["patrolIdFilter"])
            point_index = int(detail["pointIndexFilter"])
            patrol_matches = patrols_by_id.get(patrol_id) or []
            if len(patrol_matches) != 1:
                continue
            patrol = patrol_matches[0]
            points = patrol.get("points") or []
            if not (
                point_index < len(points)
                and isinstance(points[point_index], dict)
                and points[point_index].get("pointIndex") == point_index
            ):
                continue
            position = _finite_position(points[point_index].get("position"))
            if position is None:
                continue
            contexts.append({
                "storyKey": row["storyKey"],
                "levelId": level_id,
                "scriptId": observation.get("scriptId"),
                "sourceFile": observation.get("sourceFile"),
                "sourceSha256": observation.get("sourceSha256"),
                "headerLocalId": observation.get("listenerHeaderLocalId"),
                "eventName": observation.get("eventName"),
                "proxyId": detail["proxyIdFilter"],
                "patrolId": patrol_id,
                "pointIndex": point_index,
                "position": position,
                "levelDataSourceFile": patrol["sourceFile"],
                "levelDataSourceSha256": patrol["sourceSha256"],
                "nativeMappingId": detail.get("payloadSchemaMappingId"),
                "playbackControlPathEvidence": observation.get(
                    "playbackControlPathEvidence"
                ),
                "status": "exact_proxy_patrol_checkpoint",
                "runtimeNpcPositionStatus": "unresolved",
                "ownership": False,
                "activation": False,
                "orderEvidence": False,
            })
    return contexts


def _exact_story_npc_patrol_checkpoint_contexts(level_id: str) -> list[dict]:
    """Resolve dynamic-NPC patrol listeners to their exact checkpoint tuple.

    The NPC alias remains runtime-bound. The constant patrol id and point
    index still identify one authored checkpoint whenever the active level's
    fully decoded patrol collection contains exactly one matching row.
    """
    patrols_by_id = _leveldata_patrols_by_id(level_id)
    if patrols_by_id is None:
        return []
    contexts: list[dict] = []
    for row in (_native_trigger_frontier().get("storyTriggerZoneCoverage") or {}).get("rows") or []:
        if not isinstance(row, dict) or not row.get("storyKey"):
            continue
        for observation in row.get("observations") or []:
            detail = observation.get("eventDetail") if isinstance(observation, dict) else None
            entity_filter = detail.get("npcEntityFilter") if isinstance(detail, dict) else None
            if not (
                isinstance(entity_filter, dict)
                and observation.get("status") == "exact_non_spatial_event_trigger"
                and observation.get("levelId") == level_id
                and observation.get("eventName") == "LevelEvent_OnNpcPatrolCheckpointReach"
                and detail.get("payloadSchemaStatus") == "exact_current_build_memorypack_fields"
                and detail.get("payloadSchemaMappingId")
                == "gameassembly-2026-07-17-memorypack-native-event-fields"
                and detail.get("payloadShape") == "dynamic-npc-patrol-checkpoint-fields"
                and detail.get("serverExchange") is False
                and detail.get("serializedMissionOrQuestId") is False
                and entity_filter.get("logicId") == 0
                and entity_filter.get("slotId") == 0
                and entity_filter.get("useSlotId") is False
                and entity_filter.get("idRef") == -1
                and entity_filter.get("paramSource") == 200
                and str(entity_filter.get("path") or "")
                and isinstance(detail.get("patrolIdFilter"), int)
                and not isinstance(detail.get("patrolIdFilter"), bool)
                and detail.get("patrolIdFilter") > 0
                and isinstance(detail.get("checkpointIndexFilter"), int)
                and not isinstance(detail.get("checkpointIndexFilter"), bool)
                and detail.get("checkpointIndexFilter") >= 0
            ):
                continue
            patrol_id = int(detail["patrolIdFilter"])
            point_index = int(detail["checkpointIndexFilter"])
            patrol_matches = patrols_by_id.get(patrol_id) or []
            if len(patrol_matches) != 1:
                continue
            patrol = patrol_matches[0]
            points = patrol.get("points") or []
            if not (
                point_index < len(points)
                and isinstance(points[point_index], dict)
                and points[point_index].get("pointIndex") == point_index
            ):
                continue
            position = _finite_position(points[point_index].get("position"))
            if position is None:
                continue
            contexts.append({
                "storyKey": row["storyKey"],
                "levelId": level_id,
                "scriptId": observation.get("scriptId"),
                "sourceFile": observation.get("sourceFile"),
                "sourceSha256": observation.get("sourceSha256"),
                "headerLocalId": observation.get("listenerHeaderLocalId"),
                "eventName": observation.get("eventName"),
                "npcEntityPropertyPath": entity_filter["path"],
                "patrolId": patrol_id,
                "pointIndex": point_index,
                "position": position,
                "levelDataSourceFile": patrol["sourceFile"],
                "levelDataSourceSha256": patrol["sourceSha256"],
                "nativeMappingId": detail.get("payloadSchemaMappingId"),
                "playbackControlPathEvidence": observation.get("playbackControlPathEvidence"),
                "status": "exact_npc_patrol_checkpoint",
                "runtimeNpcIdentityStatus": "dynamic_script_property",
                "runtimeNpcPositionStatus": "unresolved",
                "ownership": False,
                "activation": False,
                "orderEvidence": False,
            })
    return contexts


def _proxy_patrol_context_signature(row: dict) -> tuple[str, object, str]:
    return (
        str(row.get("sourceFile") or ""),
        row.get("headerLocalId"),
        str(row.get("storyKey") or ""),
    )


def _exact_story_proxy_patrol_event_index(
    level_id: str,
    checkpoint_contexts: list[dict] | None = None,
) -> dict[str, list[dict]]:
    """Index proxy-patrol Story events by exact authored NPC proxy identity.

    Patrol/checkpoint values describe runtime progress. The map point remains
    the proxy's exact authored placement, never a claimed checkpoint position.
    """
    registry = _load_json(REGISTRY, {}) or {}
    proxy_table = _load_json(ROOT / NPC_PROXY_TABLE_REL, {}) or {}
    briefs = registry.get("npcProxyBriefInfos") if isinstance(registry, dict) else {}
    table_rows = proxy_table.get("dataTable") if isinstance(proxy_table, dict) else {}
    if not isinstance(briefs, dict) or not isinstance(table_rows, dict):
        return {}

    expected_level_num = _level_catalog().get(level_id)
    index: dict[str, list[dict]] = {}
    checkpoint_signatures = {
        _proxy_patrol_context_signature(row)
        for row in checkpoint_contexts or []
    }
    for row in (_native_trigger_frontier().get("storyTriggerZoneCoverage") or {}).get("rows") or []:
        if not isinstance(row, dict) or not row.get("storyKey"):
            continue
        for observation in row.get("observations") or []:
            if (
                not isinstance(observation, dict)
                or observation.get("status") != "exact_non_spatial_event_trigger"
                or observation.get("levelId") != level_id
                or observation.get("eventName") != "LevelEvent_OnProxyPatrolCheckpointReach"
            ):
                continue
            detail = observation.get("eventDetail") or {}
            if _proxy_patrol_context_signature({
                "sourceFile": observation.get("sourceFile"),
                "headerLocalId": observation.get("listenerHeaderLocalId"),
                "storyKey": row.get("storyKey"),
            }) in checkpoint_signatures:
                continue
            if (
                detail.get("payloadSchemaStatus") != "exact_current_build_memorypack_fields"
                or detail.get("serverExchange") is not False
                or detail.get("serializedMissionOrQuestId") is not False
                or detail.get("payloadShape") not in {
                    "constant-proxy-patrol-checkpoint-and-outputs-exact-eof",
                    "constant-proxy-patrol-checkpoint-and-outputs-exact-prefix",
                }
            ):
                continue
            proxy_id = str(detail.get("proxyIdFilter") or "")
            if not proxy_id:
                continue
            matches: list[tuple[str, dict]] = []
            for segment_id, brief in briefs.items():
                if not isinstance(brief, dict) or brief.get("proxyId") != proxy_id:
                    continue
                try:
                    numeric_segment_id = int(segment_id)
                except (TypeError, ValueError):
                    continue
                if (
                    expected_level_num is None
                    or numeric_segment_id // REGISTRY_ID_SCALE != expected_level_num
                    or brief.get("segmentIdGlobal") != numeric_segment_id
                ):
                    continue
                matches.append((str(segment_id), brief))
            if len(matches) != 1:
                continue
            segment_id, brief = matches[0]
            table_match = table_rows.get(proxy_id)
            brief_position = _finite_position(brief.get("position"))
            table_position = _finite_position(
                table_match.get("position") if isinstance(table_match, dict) else None
            )
            table_rotation = _finite_position(
                table_match.get("rotation") if isinstance(table_match, dict) else None
            )
            if (
                not isinstance(table_match, dict)
                or brief_position is None
                or table_position is None
                or table_rotation is None
                or brief_position != table_position
            ):
                continue
            identity = f"npc:{segment_id}"
            index.setdefault(identity, []).append({
                "storyKey": row["storyKey"],
                "eventName": observation["eventName"],
                "sourceFile": observation.get("sourceFile"),
                "sourceSha256": observation.get("sourceSha256"),
                "scriptId": observation.get("scriptId"),
                "headerLocalId": observation.get("listenerHeaderLocalId"),
                "playbackControlPathEvidence": observation.get("playbackControlPathEvidence"),
                "nativeMappingId": detail.get("payloadSchemaMappingId"),
                "identity": identity,
                "npcProxyId": proxy_id,
                "patrolIdFilter": detail.get("patrolIdFilter"),
                "pointIndexFilter": detail.get("pointIndexFilter"),
                "status": "exact_proxy_patrol_event_target",
                "spatialResolutionEvidence": "exact_npc_proxy_brief_and_table_join",
                "runtimeCheckpointPositionStatus": "unresolved",
                "ownership": False,
                "activation": False,
                "orderEvidence": False,
            })
    return index


def _exact_story_patrol_checkpoint_markers(
    contexts: list[dict],
    language: str,
) -> list[dict]:
    """Publish exact authored patrol points without claiming runtime position."""
    grouped: dict[tuple[int, int, tuple[float, float, float]], list[dict]] = {}
    for context in contexts:
        position = _finite_position(context.get("position"))
        patrol_id = context.get("patrolId")
        point_index = context.get("pointIndex")
        if (
            position is None
            or not isinstance(patrol_id, int)
            or not isinstance(point_index, int)
        ):
            continue
        key = (
            patrol_id,
            point_index,
            (position["x"], position["y"], position["z"]),
        )
        grouped.setdefault(key, []).append(context)

    markers: list[dict] = []
    for (patrol_id, point_index, position_values), rows in sorted(grouped.items()):
        story_keys = sorted({str(row.get("storyKey") or "") for row in rows if row.get("storyKey")})
        proxy_ids = sorted({str(row.get("proxyId") or "") for row in rows if row.get("proxyId")})
        source_files = sorted({
            str(row.get(field) or "")
            for row in rows
            for field in ("sourceFile", "levelDataSourceFile")
            if row.get(field)
        })
        markers.append({
            "kind": "story",
            "subKind": "npc_patrol_checkpoint",
            "label": _story_display_title(language, story_keys[0]) if len(story_keys) == 1 else " / ".join(story_keys),
            "identity": f"npc-patrol-checkpoint:{patrol_id}:{point_index}",
            "position": dict(zip(("x", "y", "z"), position_values)),
            "interactionStatus": "exact_npc_patrol_checkpoint",
            "evidence": (
                "exact patrol/checkpoint event filters + unique fully "
                "decoded LevelData NpcPatrolData point"
            ),
            "sceneKeys": story_keys,
            "missions": sorted({
                match.group(1)
                for story_key in story_keys
                if (match := re.search(
                    r"(?:^|_)([a-z]+\d+m\d+(?:d\d+)?)(?:_|$)",
                    story_key,
                    re.IGNORECASE,
                ))
            }),
            "proxyIds": proxy_ids,
            "patrolId": patrol_id,
            "pointIndex": point_index,
            "authoredCheckpointPosition": True,
            "runtimeNpcPositionStatus": "unresolved",
            "ownership": False,
            "activation": False,
            "orderEvidence": False,
            "patrolCheckpointBindings": rows,
            "sourceFiles": source_files,
            "source": source_files[0] if source_files else "",
            "relatedFiles": _sorted_related(_merge_related([], [
                *[
                    _related(
                        row.get("sourceFile"),
                        "story_exact_npc_patrol_event",
                        "exact NPC, patrol id and checkpoint listener before playback",
                    )
                    for row in rows
                ],
                *[
                    _related(
                        row.get("levelDataSourceFile"),
                        "placement_source",
                        "fully decoded authored NpcPatrolData checkpoint position",
                    )
                    for row in rows
                ],
                *[
                    _related(
                        _conv_file_for_key(language, story_key),
                        "story_exact_npc_patrol_checkpoint",
                        "Story reached from this exact patrol checkpoint event",
                    )
                    for story_key in story_keys
                ],
            ])),
        })
    return markers


def _level_family(level_id: str) -> str:
    for prefix, label in LEVEL_FAMILY_RULES:
        if level_id.startswith(prefix):
            return label
    return "其他 / Other"


def _region_key(level_id: str) -> str:
    """Return the stable large-scene key for a level's shared world space.

    ``map01_lv*`` and ``map02_lv*`` are separate level screens, but their
    world rectangles are authored in one shared coordinate space per prefix.
    Keeping that key in generated data lets the reader fit all sibling screens
    against the union of their world bounds. Standalone/dungeon levels have no
    ``_lvNNN`` family and remain their own region.
    """
    value = str(level_id or "").strip()
    match = re.match(r"^(.+?)_lv\d+$", value, re.IGNORECASE)
    if match:
        return match.group(1)
    # Danger-reappearance maps are always separate gameplay maps, including
    # the cases that reuse a complete standalone scene rather than a mapXX
    # art level.
    if re.match(r"^dung\d+_bdg\d+$", value, re.IGNORECASE):
        return value
    # Dungeon maps are non-seamless gameplay maps. Their LevelConfig may
    # reuse a map01/map02 streaming root and one source art level, but that is
    # an asset relation rather than shared WebUI geography.
    if isolated_art_source(value):
        return value
    authored = authored_streaming_scene(value)
    return str(authored["sceneId"]) if authored else value


def _collect_references(node, script_file_map: dict[str, str], file_refs: set[str]) -> None:
    if isinstance(node, dict):
        file_ref = node.get("file")
        script_id = node.get("scriptId")
        if isinstance(file_ref, str):
            file_refs.add(file_ref)
            if script_id is not None and str(script_id) != "":
                script_file_map.setdefault(str(script_id), file_ref)
        for child in node.values():
            _collect_references(child, script_file_map, file_refs)
        return
    if isinstance(node, list):
        for child in node:
            _collect_references(child, script_file_map, file_refs)


def _script_file_for_id(script_id: str, level_id: str = MAP_LEVEL_ID) -> str | None:
    candidate = ROOT / f"{LEVEL_SCRIPT_DATA}/{level_id}/{script_id}.json"
    if candidate.exists():
        return str(candidate.relative_to(ROOT)).replace("\\", "/")
    return None


def _level_script_files(level_id: str) -> list[str]:
    root = ROOT / f"{LEVEL_SCRIPT_DATA}/{level_id}"
    if not root.is_dir():
        return []
    return sorted(str(path.relative_to(ROOT)).replace("\\", "/") for path in root.glob("*.json"))


def _level_data_files(level_id: str) -> list[str]:
    root = ROOT / f"{LEVEL_DATA}/{level_id}"
    if not root.is_dir():
        return []
    return sorted(str(path.relative_to(ROOT)).replace("\\", "/") for path in root.glob("*.json"))


def _mission_runtime_asset(mission_id: str) -> str | None:
    """Repo path of the runtime asset that declares one mission."""
    if not mission_id:
        return None
    candidate = ROOT / f"{MISSION_RUNTIME_DIR}/{mission_id}.json"
    if candidate.exists():
        return f"{MISSION_RUNTIME_DIR}/{mission_id}.json"
    return None


def _conv_file_for_key(language: str, story_key: str) -> str | None:
    """Repo path of the published dialog/text payload for a story key."""
    if not story_key:
        return None
    candidate = ROOT / f"webui/data/lang/{language}/conv/{story_key}.json"
    if candidate.exists():
        return f"webui/data/lang/{language}/conv/{story_key}.json"
    return None


def _world_narrative_bindings(language: str) -> dict[str, list[dict]]:
    """Index exact LevelData world-entity-to-Story narrative records.

    LevelData stores the world entity's ``embeddedLogicId`` and its
    NarrativeComponent ``typeId`` in the same counted interactive record. The
    Story builder exposes the original ``dlg_*`` id, while generated WebUI
    conversations use ``misc_dlg_*`` for these otherwise unowned dialogs.
    """
    lang = language.upper()
    cached = _WORLD_NARRATIVE_BINDINGS.get(lang)
    if cached is not None:
        return cached
    conv_root = ROOT / f"webui/data/lang/{lang}/conv"
    published = {path.stem for path in conv_root.glob("*.json")} if conv_root.is_dir() else set()
    original_keys = {
        key.removeprefix("misc_") if key.startswith("misc_dlg_") else key
        for key in published
    }
    rows = build_leveldata_interactive_narrative_story_contexts(original_keys)
    index: dict[str, list[dict]] = {}
    for row in rows:
        logic_id = str(row.get("embeddedLogicId") or "")
        level_id = str(row.get("levelId") or "")
        original_key = str(row.get("storyKey") or "")
        webui_key = f"misc_{original_key}" if f"misc_{original_key}" in published else original_key
        if not logic_id or not level_id or webui_key not in published:
            continue
        enriched = dict(row)
        enriched["originalStoryKey"] = original_key
        enriched["webuiStoryKey"] = webui_key
        index.setdefault(f"{level_id}:{logic_id}", []).append(enriched)
    for bindings in index.values():
        bindings.sort(key=lambda row: str(row.get("webuiStoryKey") or ""))
    _WORLD_NARRATIVE_BINDINGS[lang] = index
    return index


def _href(path: str) -> str:
    """Map a repo-relative path onto the URL the WebUI server publishes it at.

    `serve.py` mounts the repository's `webui/` directory at `/` and the raw
    export tree at `/export_full/`, so the two path spaces that appear in one
    pinned-file list need different prefixes to stay fetchable.
    """
    clean = str(path or "").replace("\\", "/").lstrip("/")
    if clean.startswith("webui/"):
        clean = clean[len("webui/"):]
    return "/" + clean


def _related(path: str | None, relation: str, note: str) -> dict | None:
    if not path:
        return None
    clean = str(path).replace("\\", "/")
    return {
        "path": clean,
        "href": _href(clean),
        "relation": relation,
        "strength": "strong" if relation in STRONG_RELATIONS else "weak",
        "note": note,
    }


def _merge_related(target: list[dict], rows: Iterable[dict | None]) -> list[dict]:
    """Append pins, keeping the first (strongest) note for a repeated path."""
    seen = {row["path"] for row in target}
    for row in rows:
        if not row or row["path"] in seen:
            continue
        seen.add(row["path"])
        target.append(row)
    return target


def _sorted_related(rows: list[dict]) -> list[dict]:
    strength = {"strong": 0, "weak": 1}
    relation = {name: index for index, name in enumerate(RELATION_ORDER)}
    return sorted(
        rows,
        key=lambda row: (
            strength.get(row["strength"], 2),
            relation.get(row["relation"], len(RELATION_ORDER)),
            row["path"],
        ),
    )


def _story_pins(story_rows: Iterable[dict], relation: str, note: str) -> list[dict]:
    """Pin the published dialog payload plus the raw sources behind each story."""
    pins: list[dict] = []
    for story in story_rows:
        _merge_related(pins, [_related(story["convFile"], relation, f"{note} ({story['key']})")])
        for path in story["sourceFiles"]:
            _merge_related(pins, [_related(path, "story_source", f"source behind {story['key']}")])
    return pins


def _story_missions(*story_groups: Iterable[dict]) -> list[str]:
    """Missions that own the stories pinned to one node.

    This is what the page's mission filter selects on. A registry entity has no
    mission of its own - it is a piece of level art - so it belongs to whichever
    missions authored the dialog that plays there, and to none if no dialog does.
    """
    missions = {
        str(story.get("mission") or "")
        for group in story_groups for story in group
    }
    return sorted(mission for mission in missions if mission)


def _npc_mission_phases(stories: Iterable[dict]) -> list[dict]:
    """Explicit mission/quest bindings for one positioned NPC proxy.

    Quest ids come only from `npcProxyDialogAttachments`. Their lexical order
    is deterministic presentation, not a claim about runtime chronology.
    """
    phases: dict[tuple[str, str], set[str]] = {}
    for story in stories:
        mission_id = str(story.get("mission") or "")
        quest_id = str(story.get("questId") or "")
        scene_key = str(story.get("key") or "")
        if not mission_id or not quest_id:
            continue
        phases.setdefault((mission_id, quest_id), set())
        if scene_key:
            phases[(mission_id, quest_id)].add(scene_key)
    return [
        {"missionId": mission_id, "questId": quest_id, "sceneKeys": sorted(scene_keys)}
        for (mission_id, quest_id), scene_keys in sorted(phases.items())
    ]


def _story_index(mission: dict, language: str, mission_id: str = "") -> dict[str, list[dict]]:
    """Group mission story connections by the map identity they can be tied to.

    The buckets carry different evidence weights and are kept apart so the
    published pin can say which one it came from:
      * `slot:<scriptId>:<slotId>` - exact registry-backed producer entity
      * `scriptslot:<scriptId>:<slotId>` - the connection names the producer's
        entity slots, but no registry row was resolved for them
      * `script:<scriptId>` - producer/listener script with no slot resolution
      * `anchor:<scriptId>` - ordering-anchor script, which is not the entity
        that plays the story
      * `quest:<questId>` - the story's declared anchor quests
      * `area:<missionAreaId>` - the mission-area candidate set (whole-mission)

    Slot resolution is a gate, not an extra hint: once a connection names the
    slot its story is produced from, the story must not also be pinned to the
    script's other slots. `entitySlotIds` are slots on the *producer* script
    only, so they are never applied to a listener or anchor script - those are
    different entities whose identically numbered slots are unrelated.
    """
    connections = [row for row in mission.get("flow", {}).get("missionStoryConnections") or [] if isinstance(row, dict)]
    # A story that lists every mission area says nothing about any single
    # trigger, so it is filed under `mission:` instead of repeating the same
    # candidate list on all of them.
    all_area_ids = {str(area) for row in connections for area in row.get("missionAreaIds") or []}

    index: dict[str, list[dict]] = {}
    for connection in connections:
        key = str(connection.get("key") or "")
        conv_file = _conv_file_for_key(language, key)
        if not conv_file:
            continue
        source_files = _coalesce_file_paths(
            [path for path in (connection.get("sourceFiles") or []) if isinstance(path, str)]
            + [path for path in (connection.get("levelDataFiles") or []) if isinstance(path, str)]
        )
        story = {
            "key": key,
            "kind": connection.get("kind"),
            "relation": connection.get("relation"),
            "confidence": connection.get("confidence"),
            "convFile": conv_file,
            "sourceFiles": source_files,
            # A level pools the stories of every mission that plays in it, so
            # each row remembers its owner or the mission filter cannot tell
            # one mission's nodes from another's.
            "mission": mission_id,
        }

        exact = connection.get("producerEntityPositionStatus") == "exact_unique_world_entity_registry_script_slot"
        exact_entities = [
            entity for entity in connection.get("producerEntities") or []
            if isinstance(entity, dict) and exact and entity.get("scriptIdGlobal") and entity.get("slotId")
        ]
        producer_ids = [str(row) for row in connection.get("producerScriptIds") or []]
        slot_ids = [str(row) for row in connection.get("entitySlotIds") or []]

        if exact_entities:
            # The placement question is answered. Fanning the same story across
            # the script's other slots would pin it to entities this very row
            # proves are the wrong ones, so nothing else is indexed.
            for entity in exact_entities:
                index.setdefault(f"slot:{entity['scriptIdGlobal']}:{entity['slotId']}", []).append(story)
        elif slot_ids and producer_ids:
            for script_id in producer_ids:
                for slot_id in slot_ids:
                    index.setdefault(f"scriptslot:{script_id}:{slot_id}", []).append(story)
        else:
            for field in ("producerScriptIds", "listenerScriptIds"):
                for script_id in connection.get(field) or []:
                    index.setdefault(f"script:{script_id}", []).append(story)
            for script_id in connection.get("anchorScriptIds") or []:
                index.setdefault(f"anchor:{script_id}", []).append(story)
        for quest_id in connection.get("anchorQuestIds") or []:
            index.setdefault(f"quest:{quest_id}", []).append(story)

        area_ids = {str(area) for area in connection.get("missionAreaIds") or []}
        if area_ids and area_ids < all_area_ids:
            for area_id in sorted(area_ids):
                index.setdefault(f"area:{area_id}", []).append(story)
        elif area_ids:
            index.setdefault("mission:areas", []).append(story)
    return index


def _attachment_story_index(mission: dict, language: str, mission_id: str = "") -> dict[str, list[dict]]:
    """Index scenes that name the exact entity they are attached to.

    Two timeline-recovery fields bind a scene to an identity that the registry
    can place without going through a mission area:

      * `npcProxyDialogAttachments` names an `npcProxyId`, and every proxy id in
        the payload resolves to one `npcProxyBriefInfos` row with a position;
      * `scriptConditionAttachments` names a `scriptId` in a named `mapId`,
        which places the scene on that script's entities but not on one slot.

    Both are keyed here the same way `_story_index` keys its buckets, so the
    marker builders can merge them without knowing which field they came from.
    """
    timeline = mission.get("timelineRecovery") or {}
    index: dict[str, list[dict]] = {}

    for row in timeline.get("npcProxyDialogAttachments") or []:
        if not isinstance(row, dict):
            continue
        key = str(row.get("sceneKey") or "")
        proxy_id = str(row.get("npcProxyId") or "")
        conv_file = _conv_file_for_key(language, key)
        if not key or not proxy_id or not conv_file:
            continue
        index.setdefault(f"proxy:{proxy_id}", []).append({
            "key": key,
            "kind": "dialog",
            "questId": row.get("questId"),
            "convFile": conv_file,
            "sourceFiles": [],
            "mission": mission_id,
        })

    for row in timeline.get("scriptConditionAttachments") or []:
        if not isinstance(row, dict):
            continue
        key = str(row.get("sceneKey") or "")
        script_id = str(row.get("scriptId") or "")
        conv_file = _conv_file_for_key(language, key)
        if not key or not script_id or not conv_file:
            continue
        source = _script_file_for_id(script_id, str(row.get("mapId") or ""))
        index.setdefault(f"condition:{script_id}", []).append({
            "key": key,
            "kind": "dialog",
            "questId": row.get("questId"),
            "convFile": conv_file,
            "sourceFiles": [source] if source else [],
            "mission": mission_id,
        })
    return index


def marker(kind: str, label: str, identity: str, info: dict, evidence: str, interaction: str, sub_kind: str = "") -> dict:
    row = {
        "kind": kind,
        "subKind": sub_kind or kind,
        "label": label,
        "identity": identity,
        "position": info["position"],
        "detailId": info.get("detailId"),
        "interactionStatus": interaction,
        "evidence": evidence,
    }
    alias = _canonical_detail(row["detailId"] or "")
    if alias:
        row["detailAlias"] = alias
    return row


def _coalesce_file_paths(paths: Iterable[str | None]) -> list[str]:
    return sorted({path for path in paths if isinstance(path, str) and path})


def _finite_position(position: object) -> dict[str, float] | None:
    if not isinstance(position, dict):
        return None
    x = position.get("x")
    y = position.get("y")
    z = position.get("z")
    if not isinstance(x, (int, float)) or not isinstance(z, (int, float)):
        return None
    return {
        "x": float(x),
        "y": None if y is None or not isinstance(y, (int, float)) else float(y),
        "z": float(z),
    }


def _mission_area_definitions() -> dict[str, list[dict]]:
    """Index authored MissionAreaTable rows without guessing across duplicates."""
    global _MISSION_AREA_DEFINITIONS
    if _MISSION_AREA_DEFINITIONS is not None:
        return _MISSION_AREA_DEFINITIONS
    payload = _load_json(ROOT / MISSION_AREA_TABLE_REL, {}) or {}
    rows: dict[str, list[dict]] = {}
    for level_num, areas in (payload.get("m_areas") or {}).items():
        if not isinstance(areas, dict):
            continue
        for area_id, area in areas.items():
            if isinstance(area, dict):
                rows.setdefault(str(area_id), []).append({**area, "levelNum": str(level_num)})
    _MISSION_AREA_DEFINITIONS = rows
    return rows


def _exact_mission_area_definition(area_id: object, position: dict[str, float]) -> dict | None:
    """Resolve one MissionArea row by authored id and identical X/Z center."""
    matches = []
    for row in _mission_area_definitions().get(str(area_id), []):
        center = _finite_position((row.get("shape") or {}).get("position"))
        if center and abs(center["x"] - position["x"]) < 0.001 and abs(center["z"] - position["z"]) < 0.001:
            matches.append(row)
    return matches[0] if len(matches) == 1 else None


def _iter_timeline_scene_entries(timeline_recovery: dict) -> list[dict]:
    entries: list[dict] = []
    for row in timeline_recovery.get("levelscriptSpatialProximity") or []:
        if isinstance(row, dict):
            entries.append(row)
    scene_placement = timeline_recovery.get("scenePlacement") or {}
    if not isinstance(scene_placement, dict):
        scene_placement = {}
    for scene_key, item in scene_placement.items():
        if not isinstance(item, dict):
            continue
        for row in item.get("inheritedSpatialQuestCandidates") or []:
            if not isinstance(row, dict):
                continue
            # The candidate rows are nested under their scene, so the scene key
            # only exists on the parent. Carry it down; the pinned dialog file
            # is looked up from it.
            entries.append({**row, "sceneKey": row.get("sceneKey") or item.get("sceneKey") or scene_key})
    return entries


def _collect_trigger_markers(
    mission: dict,
    mission_id: str = "e0m0",
    level_id: str = MAP_LEVEL_ID,
) -> list[dict]:
    markers: list[dict] = []
    area_occurrences: dict[str, int] = {}
    runtime_asset = _mission_runtime_asset(mission_id) or MISSION_RUNTIME_ASSET
    for index, pin in enumerate((mission.get("flow") or {}).get("mapPins") or []):
        if not isinstance(pin, dict) or pin.get("sourceType") != "missionArea":
            continue
        mission_area_id = pin.get("missionAreaId")
        if not mission_area_id:
            continue
        # A proximity row may pin into a level other than the mission's own, so
        # the row is only plotted on the map whose coordinate space it names.
        pin_map = str(pin.get("scene") or pin.get("mapId") or "")
        if pin_map and pin_map != level_id:
            continue

        position = _finite_position(pin.get("position"))
        if not position:
            continue

        occurrence = area_occurrences.get(str(mission_area_id), 0)
        area_occurrences[str(mission_area_id)] = occurrence + 1

        marker_row = {
            "kind": "trigger",
            "subKind": "mission_area",
            "label": "触发区",
            "identity": f"mission_area:{mission_id}:{mission_area_id}:{occurrence}",
            "position": position,
            "detailId": mission_area_id,
            "interactionStatus": "automatic_trigger",
            "evidence": "MissionRuntime authored MissionAreaTrackingInfo position; Story trigger unresolved",
            "missionId": mission_id,
            "questIds": [str(value) for value in pin.get("questIds") or [] if value],
            "storyBindingStatus": "unresolved",
        }
        area_definition = _exact_mission_area_definition(mission_area_id, position)
        if area_definition is not None:
            shape = area_definition.get("shape") or {}
            shape_type = {1: "box", 2: "sphere"}.get(shape.get("type"))
            if shape_type:
                marker_row["triggerShape"] = {
                    "type": shape_type,
                    "position": _finite_position(shape.get("position")) or position,
                    "rotation": shape.get("eulerAngles") or {},
                    "size": shape.get("size") or {},
                    "radius": shape.get("radius"),
                }
                marker_row["missionAreaDefinitionStatus"] = "exact_id_and_center"
            marker_row["subDataParentId"] = area_definition.get("subDataParentId")
        if pin.get("trackingType"):
            marker_row["trackingType"] = pin["trackingType"]
        if pin.get("label"):
            marker_row["pinLabel"] = pin["label"]
        marker_row["mapId"] = pin_map
        if pin.get("radius") is not None:
            marker_row["radius"] = pin["radius"]
        marker_row["pinPosition"] = pin["position"]
        marker_row["sceneKeys"] = []
        marker_row["missions"] = [mission_id] if mission_id else []
        marker_row["relatedFiles"] = _merge_related([], [
            _related(runtime_asset, "mission_area_definition", "MissionRuntime row that authors this area pin"),
            _related(
                MISSION_AREA_TABLE_REL if area_definition is not None else None,
                "mission_area_definition",
                "exact mission-area id and center with authored shape",
            ),
        ])
        markers.append(marker_row)
    for row in markers:
        row["relatedFiles"] = _sorted_related(row["relatedFiles"])
    return markers


def _map_pin_markers(
    mission: dict,
    language: str,
    story_index: dict[str, list[dict]],
    attachment_index: dict[str, list[dict]],
    mission_id: str,
    level_id: str,
) -> list[dict]:
    """Plot the mission's authored map pins that belong to this level.

    `flow.mapPins` names the level in its own `scene` field, carries an exact
    position, and says which quests the pin serves. NPC pins additionally name
    the proxy the pin follows, which is the same identity
    `npcProxyDialogAttachments` binds scenes to - so an NPC pin can carry the
    exact dialog its proxy plays, not just the quests it belongs to.
    """
    runtime_asset = _mission_runtime_asset(mission_id)
    markers: list[dict] = []
    for index, pin in enumerate(mission.get("flow", {}).get("mapPins") or []):
        if not isinstance(pin, dict) or str(pin.get("scene") or "") != level_id:
            continue
        source_type = str(pin.get("sourceType") or "")
        # Mission-area pins are published separately with an explicit
        # unresolved Story-binding boundary.
        if source_type == "missionArea":
            continue
        position = _finite_position(pin.get("position"))
        if not position:
            continue
        proxy_id = str(pin.get("npcProxyId") or "")
        quest_ids = [str(quest) for quest in pin.get("questIds") or [] if quest]
        proxy_stories = attachment_index.get(f"proxy:{proxy_id}", []) if proxy_id else []
        # Quest membership gives this pin mission context, not ownership of
        # every Story file mentioning the same quest. Only the NPC proxy
        # attachment below is an exact entity identity join.
        quest_stories: list[dict] = []

        if proxy_id:
            kind, sub_kind, label, interaction = "npc", "npc_proxy", proxy_id.split("_", 1)[0], "npc_proxy"
            evidence = "mission map pin with an exact npcProxy transform"
        else:
            kind, sub_kind, label, interaction = "waypoint", "quest_track", "任务坐标", "quest_tracking_position"
            evidence = "mission map pin tracking position"

        row = {
            "kind": kind,
            "subKind": sub_kind,
            "label": label,
            "identity": f"mappin:{mission_id}:{source_type}:{index}",
            "position": position,
            "detailId": proxy_id or (quest_ids[0] if quest_ids else source_type),
            "interactionStatus": interaction,
            "evidence": evidence,
            "missionId": mission_id,
            "sourceType": source_type,
            "questIds": quest_ids,
        }
        if proxy_id:
            row["npcProxyId"] = proxy_id
        if pin.get("trackingType"):
            row["trackingType"] = pin["trackingType"]
        if proxy_id:
            row["registryBacked"] = True
        row["sceneKeys"] = sorted({story["key"] for story in [*proxy_stories, *quest_stories]})
        row["missions"] = sorted({mission_id, *_story_missions(proxy_stories, quest_stories)})
        row["relatedFiles"] = _sorted_related(_merge_related([], [
            *_story_pins(proxy_stories, "story_npc_proxy", "dialog attached to this NPC proxy"),
            *_story_pins(quest_stories, "story_map_pin", "story anchored to a quest this pin serves"),
            _related(runtime_asset, "mission_runtime", "mission that declares this pin"),
        ]))
        markers.append(row)
    return markers


def _unresolved_trigger_slots(mission: dict, registry: dict) -> dict:
    """Report stories bound to a trigger volume that has no plottable entity.

    `triggerSlotIds` come from `ScriptEvent_OnLeaderEnterTriggerVolume` and are
    numbered in a level-script-local space (80001..82464) that shares no id with
    the WorldEntityRegistry script/slot space, so they cannot be placed on the
    map. Publishing the gap keeps the mission-area pins from reading as the
    story's real binding.
    """
    known_slots = {str(row["slotId"]) for row in registry.get("m_scriptEntityIdList") or []}
    rows = []
    for connection in mission.get("flow", {}).get("missionStoryConnections") or []:
        if not isinstance(connection, dict):
            continue
        slot_ids = [str(row) for row in connection.get("triggerSlotIds") or []]
        if not slot_ids or any(slot in known_slots for slot in slot_ids):
            continue
        rows.append({"key": str(connection.get("key") or ""), "triggerSlotIds": sorted(slot_ids)})
    return {
        "count": len(rows),
        "stories": sorted(rows, key=lambda row: row["key"]),
        "boundary": (
            "These stories are bound to a trigger volume by a level-script-local slot id that no "
            "WorldEntityRegistry entity carries. Their mission-area pins are scope context, not the "
            "recovered trigger position."
        ),
    }


def _mission_scene_universe(mission: dict) -> dict[str, str]:
    """Every story scene this mission owns, mapped to its declared kind."""
    flow = mission.get("flow") or {}
    timeline = mission.get("timelineRecovery") or {}
    universe: dict[str, str] = {}
    for node in (flow.get("sceneGraph") or {}).get("nodes") or []:
        if isinstance(node, dict) and node.get("key"):
            universe.setdefault(str(node["key"]), str(node.get("kind") or ""))
    for key, item in (timeline.get("scenePlacement") or {}).items():
        universe.setdefault(str(key), str((item or {}).get("kind") or ""))
    for row in flow.get("missionStoryConnections") or []:
        if isinstance(row, dict) and row.get("key"):
            universe.setdefault(str(row["key"]), str(row.get("kind") or ""))
    for row in flow.get("unlinked") or []:
        key = row if isinstance(row, str) else (row or {}).get("key")
        if key:
            universe.setdefault(str(key), "")
    return universe


def _cross_level_scenes(mission: dict, level_id: str) -> dict[str, set[str]]:
    """Scenes whose authored chain runs in a level other than `level_id`."""
    bindings = (mission.get("extras") or {}).get("sceneBindings") or {}
    cross_level: dict[str, set[str]] = {}
    for scene_key, binding in bindings.items():
        for chain in (binding or {}).get("chains") or []:
            chain_level = str((chain or {}).get("levelId") or "")
            if chain_level and chain_level != level_id:
                cross_level.setdefault(str(scene_key), set()).add(chain_level)
            for step in (chain or {}).get("steps") or []:
                for payload in (step or {}).get("payloads") or []:
                    key = str((payload or {}).get("sceneKey") or "")
                    if key and chain_level and chain_level != level_id:
                        cross_level.setdefault(key, set()).add(chain_level)
    return cross_level


def _unplaced_story_rows(
    universe: dict[str, str],
    cross_level: dict[str, set[str]],
    level_id: str,
    language: str,
    pinned_paths: set[str],
    map_paths: set[str],
) -> list[dict]:
    """Explain every mission scene that no plotted node could claim.

    A scene reaches a node only through a spatial anchor: an exact producer
    entity, an NPC proxy, a mission-area pin, or a proximity row. Scenes that
    are scoped to the whole mission, that carry only graph evidence (scene-to-
    scene ordering), or that are driven from another level have no coordinate to
    sit on, so the page reports them by reason instead of leaving the reader to
    wonder what happened to them.
    """
    rows = []
    for key, kind in sorted(universe.items()):
        conv_file = _conv_file_for_key(language, key)
        if not conv_file or conv_file in pinned_paths:
            continue
        if conv_file in map_paths:
            reason = "mission_scope_only"
            detail = "scoped to the mission's whole area set; listed under map-wide files"
        elif key in cross_level:
            reason = "cross_level_binding"
            detail = f"driven from {', '.join(sorted(cross_level[key]))}, not from {level_id}"
        elif kind == "__placed__":
            reason = "graph_evidence_only"
            detail = "ordering edges only; no mission area, producer entity or proximity row"
        else:
            reason = "no_placement_evidence"
            detail = "no spatial evidence of any kind in the mission payload"
        rows.append({
            "key": key,
            "kind": "" if kind == "__placed__" else kind,
            "reason": reason,
            "detail": detail,
            "path": conv_file,
            "href": _href(conv_file),
        })
    return rows


def _unplaced_report(rows: list[dict], boundary: str | None = None) -> dict:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["reason"]] = counts.get(row["reason"], 0) + 1
    return {
        "count": len(rows),
        "reasonCounts": dict(sorted(counts.items())),
        "carrierAbsenceCounts": dict(sorted(Counter(
            str((row.get("storyCarrierAbsenceEvidence") or {}).get("status") or "")
            for row in rows if row.get("storyCarrierAbsenceEvidence")
        ).items())),
        "definitionEvidenceCounts": dict(sorted(Counter(
            str((row.get("storyDefinitionEvidence") or {}).get("status") or "")
            for row in rows if row.get("storyDefinitionEvidence")
        ).items())),
        "stories": sorted(rows, key=lambda row: row["key"]),
        "boundary": boundary or (
            "These mission scenes are published in the Story view but no plotted node can claim them, so "
            "they are absent from the map by evidence rather than by omission."
        ),
    }


def _annotate_unplaced_story_trigger_evidence(rows: list[dict], level_id: str) -> None:
    """Expose exact receiver evidence without turning non-spatial events into pins."""
    report = _native_trigger_frontier()
    by_story: dict[str, list[dict]] = {}
    coverage_rows = (report.get("storyTriggerZoneCoverage") or {}).get("rows") or []
    confirmations = coverage_rows or [
        confirmation
        for receiver in report.get("rows") or []
        if isinstance(receiver, dict)
        for confirmation in receiver.get("storyTriggerZoneConfirmations") or []
        if isinstance(confirmation, dict)
    ]
    coverage_story_keys = {
        str(confirmation.get("storyKey") or "")
        for confirmation in confirmations
        if isinstance(confirmation, dict) and confirmation.get("storyKey")
    }
    complete_coverage_validated = bool(
        coverage_rows
        and str((report.get("storyTriggerZoneCoverage") or {}).get("schema") or "")
        == "nativeReceiverStoryTriggerZone.v1"
        and str(((report.get("storyTriggerZoneCoverage") or {}).get("overlay") or {}).get("status") or "")
        == "validated_active_overlay"
        and not (((report.get("storyTriggerZoneCoverage") or {}).get("overlay") or {}).get("validationFailures") or [])
    )
    for confirmation in confirmations:
        if not isinstance(confirmation, dict) or not confirmation.get("storyKey"):
            continue
        observations = [
            observation
            for observation in confirmation.get("observations") or []
            if isinstance(observation, dict)
            and str(observation.get("levelId") or "") == level_id
        ]
        if not observations:
            continue
        by_story.setdefault(str(confirmation["storyKey"]), []).append({
            "status": str(confirmation.get("status") or ""),
            "scriptIds": sorted({
                str(observation.get("scriptId") or "")
                for observation in observations
                if observation.get("scriptId")
            }),
            "observationCount": len(observations),
        })
    for row in rows:
        evidence = by_story.get(str(row.get("key") or "")) or []
        if not evidence:
            story_key = str(row.get("key") or "")
            if complete_coverage_validated and story_key not in coverage_story_keys:
                row["storyCarrierAbsenceEvidence"] = {
                    "status": "not_observed_in_active_direct_playback_frontier",
                    "failureGate": "story_key_absent_from_complete_active_playback_coverage",
                    "coverageSchema": "nativeReceiverStoryTriggerZone.v1",
                    "overlayStatus": "validated_active_overlay",
                    "spatialPromotion": False,
                    "boundary": (
                        "No active direct-playback carrier for this Story key was observed in the complete "
                        "current coverage. This does not prove that no runtime, server, or indirect carrier exists."
                    ),
                }
            continue
        statuses = {item["status"] for item in evidence}
        if statuses == {"exact_non_spatial_event_trigger"}:
            resolution_class = "exact_non_spatial_trigger_context_only"
            failure_gate = "trigger_has_no_authored_spatial_shape"
        elif "exact_local_trigger_volume" in statuses:
            resolution_class = "exact_spatial_trigger_not_projected"
            failure_gate = "exact_trigger_marker_missing_from_current_map_payload"
        else:
            resolution_class = "ambiguous_trigger_context_only"
            failure_gate = "trigger_zone_not_unique"
        row["storyTriggerEvidence"] = {
            "resolutionClass": resolution_class,
            "failureGate": failure_gate,
            "confirmations": evidence,
            "boundary": (
                "Receiver evidence identifies the Story event in this level, but only a unique decoded "
                "authored trigger shape can place it on the map."
            ),
        }


def _annotate_unplaced_story_definition_evidence(rows: list[dict]) -> None:
    """Publish exact authored cutscene assets without implying playback or place."""
    for row in rows:
        story_key = str(row.get("key") or "")
        conv_path = str(row.get("path") or "")
        if not story_key or not conv_path:
            continue
        payload = _load_json(ROOT / conv_path, {}) or {}
        cutscene = payload.get("cutscene") or {}
        variants = [
            variant for variant in cutscene.get("variants") or []
            if isinstance(variant, dict) and str(variant.get("file") or "")
        ]
        if str(payload.get("key") or "") != story_key or not variants:
            continue
        related = [
            _related(
                str(variant["file"]),
                "story_definition_asset",
                "exact published cutscene definition variant; playback and spatial activation unresolved",
            )
            for variant in variants
        ]
        row["relatedFiles"] = _sorted_related(_merge_related(
            row.get("relatedFiles") or [], related,
        ))
        row["storyDefinitionEvidence"] = {
            "status": "exact_published_cutscene_definition",
            "semanticShape": str(cutscene.get("semanticShape") or ""),
            "variantCount": len(variants),
            "hasSubtitleTrack": bool(cutscene.get("hasSubtitleTrack")),
            "audioEvents": sorted({
                str(value) for value in cutscene.get("audioEvents") or [] if value
            }),
            "spatialPromotion": False,
            "playbackStatus": "unresolved_without_strict_playback_carrier",
            "boundary": (
                "These files prove an authored cutscene definition and media composition only. "
                "They do not prove playback, trigger activation, mission ownership, or map position."
            ),
        }


def _placement_marked_scene_universe(mission: dict) -> dict[str, str]:
    """`_mission_scene_universe` with placed scenes flagged for the row builder.

    `scenePlacement` membership is what separates "ordering edges only" from
    "no spatial evidence at all", and it is the only reason the raw mission is
    needed at all, so it is folded into the universe as a sentinel kind and the
    mission itself is then dropped.
    """
    placement = (mission.get("timelineRecovery") or {}).get("scenePlacement") or {}
    return {
        key: ("__placed__" if key in placement else kind)
        for key, kind in _mission_scene_universe(mission).items()
    }


def _quest_proximity_index(timeline_recovery: dict) -> dict[str, list[dict]]:
    """Group every spatial proximity row by the quest it names.

    `_collect_trigger_markers` only consumes rows pinned to a mission area, so
    rows pinned to a `trackingPos` used to be dropped from the payload
    altogether even though they name a quest, a scene and a level-script file.
    """
    index: dict[str, list[dict]] = {}
    for row in _iter_timeline_scene_entries(timeline_recovery):
        quest_id = str(row.get("questId") or "")
        if quest_id:
            index.setdefault(quest_id, []).append(row)
    return index


def _quest_belongs_to_level(row: dict, level_id: str) -> bool:
    """Whether a quest centroid may be plotted in `level_id`'s coordinate space.

    `scenes` names every level the quest's tracked pins sit in. A quest whose
    pins span two levels has a centroid averaged across two unrelated coordinate
    spaces, so it is plotted on neither map rather than at a position that
    exists in neither. A row that declares no scene claims no other level, so it
    stays with the mission's own level.
    """
    scenes = {str(scene) for scene in row.get("scenes") or [] if scene}
    return not scenes or scenes == {level_id}


def _quest_point(
    row: dict,
    language: str,
    script_file_map: dict[str, str],
    story_index: dict[str, list[dict]],
    proximity_index: dict[str, list[dict]],
    mission_id: str = "e0m0",
    level_id: str = MAP_LEVEL_ID,
) -> dict:
    """One plotted quest centroid with definition evidence only.

    Spatially nearby scenes and quest-wide Story membership are deliberately
    excluded: neither identifies a playback point.
    """
    quest_id = row["questId"]
    runtime_asset = _mission_runtime_asset(mission_id) or MISSION_RUNTIME_ASSET
    pins: list[dict] = [
        row_pin
        for row_pin in [_related(runtime_asset, "mission_runtime", "mission that declares this quest")]
        if row_pin
    ]

    # The mission-area pins name the level-script rows that define the quest's
    # tracked volumes, so those files belong to the quest even when no scene
    # was ever placed near it.
    for pin in row.get("pins") or []:
        if not isinstance(pin, dict):
            continue
        for field in ("subDataParentId", "levelDataParentId"):
            _merge_related(pins, [
                _related(
                    _script_file_for_id(str(pin.get(field) or ""), level_id),
                    "mission_area_definition",
                    f"level script that defines area {pin.get('missionAreaId') or ''}".strip(),
                ),
            ])

    return {
        "questId": quest_id,
        "questOrder": row.get("questOrder"),
        "missionId": mission_id,
        "missions": [mission_id] if mission_id else [],
        "position": row["centroid"],
        "objective": " / ".join(x.get("text", "") for x in row.get("objectiveInstructions", []) if x.get("text")),
        "sceneKeys": [],
        "storyBindingStatus": "unresolved",
        "relatedFiles": _sorted_related(pins),
    }


# --------------------------------------------------------------------------
# Level catalog and registry indexing
# --------------------------------------------------------------------------


def _load_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default


def _level_names(language: str) -> dict[str, str]:
    """`levelId -> display name` from the level's own table rows.

    `LevelDescTable` keys every level by id and points `showName` at the
    per-language `I18nTextTable`. A level whose text is empty or a placeholder
    ("?", "？？？") publishes no name, so the reader falls back to the level id
    instead of printing a placeholder.
    """
    desc = _load_json(ROOT / LEVEL_DESC_REL, {}) or {}
    i18n = _load_json(ROOT / I18N_TEXT_REL.format(language.upper()), {}) or {}
    names: dict[str, str] = {}
    for level_id, row in desc.items():
        if not isinstance(row, dict):
            continue
        show = row.get("showName") or {}
        text = i18n.get(str(show.get("id"))) if isinstance(show, dict) else None
        if not isinstance(text, str):
            continue
        text = text.strip()
        if text and not set(text) <= {"?", "？"}:
            names[str(level_id)] = text
    return names


def _mission_names(language: str) -> dict[str, str]:
    """Published localized mission names keyed by mission code."""
    payload = _load_json(ROOT / MISSION_NAMES_REL.format(language.upper()), {}) or {}
    rows = payload.get("missionNames") if isinstance(payload, dict) else {}
    if not isinstance(rows, dict):
        return {}
    return {
        str(mission_id): str(name).strip()
        for mission_id, name in rows.items()
        if str(mission_id).strip() and str(name).strip()
    }


# --------------------------------------------------------------------------
# In-game map screen (minimap) textures
# --------------------------------------------------------------------------
#
# The exported map chunk textures are 8-bit PNGs, so the composite stays
# stdlib-only: a minimal PNG decoder (filter types 0-4) and an RGBA encoder.
# The game's own map screen tiles the level with square chunks whose (x, y)
# indices and exact world rectangles `UILevelMapLoadConfig` declares; the
# composite keeps the config as the placement authority and only borrows
# pixels from the exported chunk art.


def _png_decode(path: Path) -> tuple[int, int, list[bytearray]]:
    """Decode an 8-bit truecolor/grayscale/gray+alpha PNG into RGBA rows."""
    data = path.read_bytes()
    pos = 8
    idat = b""
    width = height = bit_depth = color_type = None
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        if kind == b"IHDR":
            width, height, bit_depth, color_type = struct.unpack(">IIBB", body[:10])
        elif kind == b"IDAT":
            idat += body
        pos += 12 + length
    if bit_depth != 8 or color_type not in (0, 2, 4, 6) or width is None:
        raise ValueError(f"unsupported PNG (depth {bit_depth}, type {color_type}): {path.name}")
    channels = {0: 1, 2: 3, 4: 2, 6: 4}[color_type]
    stride = width * channels
    raw = zlib.decompress(idat)
    rows = []
    prev = bytearray(stride)
    i = 0
    for _ in range(height):
        filter_type = raw[i]
        i += 1
        line = bytearray(raw[i:i + stride])
        i += stride
        if filter_type == 1:
            for x in range(channels, stride):
                line[x] = (line[x] + line[x - channels]) & 255
        elif filter_type == 2:
            for x in range(stride):
                line[x] = (line[x] + prev[x]) & 255
        elif filter_type == 3:
            for x in range(stride):
                left = line[x - channels] if x >= channels else 0
                line[x] = (line[x] + ((left + prev[x]) >> 1)) & 255
        elif filter_type == 4:
            for x in range(stride):
                left = line[x - channels] if x >= channels else 0
                up = prev[x]
                up_left = prev[x - channels] if x >= channels else 0
                p = left + up - up_left
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - up_left)
                pr = left if (pa <= pb and pa <= pc) else (up if pb <= pc else up_left)
                line[x] = (line[x] + pr) & 255
        elif filter_type > 4:
            raise ValueError(f"unsupported PNG filter {filter_type}: {path.name}")
        prev = line
        rows.append(line)
    rgba = []
    for line in rows:
        out = bytearray()
        for x in range(width):
            p = line[x * channels:(x + 1) * channels]
            if color_type == 6:
                out += bytes(p)
            elif color_type == 2:
                out += bytes((p[0], p[1], p[2], 255))
            elif color_type == 4:
                out += bytes((p[0], p[0], p[0], p[1]))
            else:
                out += bytes((p[0], p[0], p[0], 255))
        rgba.append(out)
    return width, height, rgba


def _png_size(path: Path) -> tuple[int, int]:
    """The (width, height) of a PNG from its IHDR, without decoding pixels."""
    with path.open("rb") as handle:
        head = handle.read(33)
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        raise ValueError(f"not a PNG: {path.name}")
    width, height = struct.unpack(">II", head[16:24])
    return width, height


def _png_write(path: Path, width: int, height: int, rows: list[bytearray]) -> None:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(b"".join(b"\x00" + bytes(row) for row in rows), 6))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


def _minimap_tiles(layer: str, level_id: str) -> dict[tuple[int, int], Path]:
    """`(x, y) -> texture file` for one map-screen layer of one level.

    Chunk art is exported once per unique PathId, so a cell can own several
    near-identical files (the variants differ by single-digit channels at most);
    the lexicographically first filename is the stable choice, and the composite
    records every chosen file by hash so a rebuilt export that changed the art
    is never silently reused.
    """
    root = ROOT / MAP_TILE_DIR
    if not root.is_dir():
        return {}
    pattern = re.compile(rf"^{layer}_{re.escape(level_id)}_(\d+)_(\d+)_p[0-9A-Fa-f]+\.png$")
    by_cell: dict[tuple[int, int], list[str]] = {}
    for name in os.listdir(root):
        match = pattern.match(name)
        if match:
            by_cell.setdefault((int(match.group(1)), int(match.group(2))), []).append(name)
    return {cell: root / sorted(names)[0] for cell, names in by_cell.items()}


def _minimap_tier_tiles(layer: str, level_id: str, tier_id: str) -> dict[tuple[int, int], Path]:
    """Return exported transparent map-layer art for one config tier.

    Tier images use the same cell coordinates as the base map image, but carry
    ``_tier_<tierId>`` before the PathID suffix.  Keeping this selector
    separate from :func:`_minimap_tiles` is important: a base tile and a tier
    overlay are different map layers, not near-duplicate variants of one tile.
    """
    root = ROOT / MAP_TILE_DIR
    if not root.is_dir():
        return {}
    pattern = re.compile(
        rf"^{layer}_{re.escape(level_id)}_(\d+)_(\d+)_tier_{re.escape(str(tier_id))}_p[0-9A-Fa-f]+\.png$"
    )
    by_cell: dict[tuple[int, int], list[str]] = {}
    for name in os.listdir(root):
        match = pattern.match(name)
        if match:
            by_cell.setdefault((int(match.group(1)), int(match.group(2))), []).append(name)
    return {cell: root / sorted(names)[0] for cell, names in by_cell.items()}


def _world_rect(row: object) -> tuple[float, float, float, float] | None:
    """Read one config rectangle as ``(left, bottom, right, top)``."""
    if not isinstance(row, dict):
        return None
    left_bottom = row.get("worldLeftBottom") or {}
    right_top = row.get("worldRightTop") or {}
    values = (left_bottom.get("x"), left_bottom.get("y"), right_top.get("x"), right_top.get("y"))
    if not all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values):
        return None
    left, bottom, right, top = map(float, values)
    if right <= left or top <= bottom:
        return None
    return left, bottom, right, top


def _config_tier_rows(config: dict) -> dict[str, list[dict]]:
    """Group ``tierInfos`` by tier id, retaining the raw cell rectangles.

    ``tierNames`` is the source of truth for which layers the game exposes;
    ``tierInfos`` is the source of truth for where each layer image belongs.
    There is deliberately no visual/manual tier list here.
    """
    names = config.get("tierNames") or {}
    infos = config.get("tierInfos") or {}
    if not isinstance(names, dict) or not isinstance(infos, dict):
        return {}
    rows: dict[str, list[dict]] = {str(tier_id): [] for tier_id in names}
    for raw in infos.values():
        if not isinstance(raw, dict) or raw.get("tierId") is None:
            continue
        tier_id = str(raw.get("tierId"))
        if tier_id not in rows:
            continue
        rect = _world_rect(raw)
        if not rect:
            continue
        load_id = str(raw.get("tierLoadId") or "")
        match = re.match(r"^(?P<layer>[mhl])_[^_]+(?:_[^_]+)*_(?P<x>\d+)_(?P<y>\d+)_tier_", load_id)
        row = {"rect": rect, "loadId": load_id}
        if match:
            row.update({"layer": match.group("layer"), "x": int(match.group("x")), "y": int(match.group("y"))})
        rows[tier_id].append(row)
    return {tier_id: rows[tier_id] for tier_id in rows if rows[tier_id]}


def _union_rects(rects: Iterable[tuple[float, float, float, float] | None]) -> dict[str, float] | None:
    # Configs for focused/unit-test levels may omit worldRect entirely. A
    # missing rectangle is absence of evidence, not a zero-sized extent.
    values = [row for row in rects if row is not None]
    if not values:
        return None
    return {
        "minX": min(row[0] for row in values),
        "maxX": max(row[2] for row in values),
        "minZ": min(row[1] for row in values),
        "maxZ": max(row[3] for row in values),
    }


def _point_in_rect(position: dict, rect: tuple[float, float, float, float]) -> bool:
    x, z = position.get("x"), position.get("z")
    return isinstance(x, (int, float)) and isinstance(z, (int, float)) and rect[0] <= x <= rect[2] and rect[1] <= z <= rect[3]


def _map_ui_config(level_id: str) -> dict:
    """Load the level's map-UI config, or an empty config when it is absent.

    ``UILevelMapLoadConfig`` is optional for private/dungeon scenes.  Keeping
    the read in one helper makes the coordinate contract explicit and lets the
    static-element and tile builders use exactly the same source file.
    """
    return _load_json(ROOT / f"{MAP_UI_CONFIG_DIR}/{level_id}.json", {}) or {}


def _map_ui_world_bounds(config: dict) -> dict[str, float] | None:
    """Return the authored map-UI world rectangle as X/Z bounds."""
    basic = config.get("basic") or {}
    left_bottom = basic.get("worldRectLeftBottom") or {}
    right_top = basic.get("worldRectRightTop") or {}
    values = (left_bottom.get("x"), left_bottom.get("y"), right_top.get("x"), right_top.get("y"))
    if not all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values):
        return None
    left, bottom, right, top = map(float, values)
    if right <= left or top <= bottom:
        return None
    return {"minX": left, "maxX": right, "minZ": bottom, "maxZ": top}


def _map_text_lookup(language: str) -> dict[str, str]:
    """Resolve map config text keys through TextTable into localized text."""
    cache_key = (str(ROOT.resolve()), language.upper())
    if cache_key in _MAP_TEXT_LOOKUPS:
        return _MAP_TEXT_LOOKUPS[cache_key]
    text_table = _load_json(ROOT / TEXT_TABLE_REL, {}) or {}
    i18n = _load_json(ROOT / I18N_TEXT_REL.format(language.upper()), {}) or {}
    result: dict[str, str] = {}
    for key, row in text_table.items():
        if not isinstance(row, dict) or row.get("id") is None:
            continue
        text = i18n.get(str(row["id"]))
        if isinstance(text, str) and text.strip():
            result[str(key)] = text.strip()
    _MAP_TEXT_LOOKUPS[cache_key] = result
    return result


def _map_ui_static_elements(level_id: str, language: str = "CN") -> dict:
    """Publish authored map-screen points in the same world X/Z space.

    These are not registry entities: ``staticElements`` contains location-tip
    and level-transition points owned by the map UI itself.  They are useful as
    an independent alignment witness, so keep their exact source identity and
    do not turn them into semantic/entity markers.
    """
    config = _map_ui_config(level_id)
    localized = _map_text_lookup(language)
    source = f"{MAP_UI_CONFIG_DIR}/{level_id}.json" if config else None
    basic = config.get("basic") or {}
    rows: list[dict] = []
    static = config.get("staticElements") or {}
    values = static.items() if isinstance(static, dict) else enumerate(static)
    for key, raw in values:
        if not isinstance(raw, dict):
            continue
        position = _finite_position(raw.get("position"))
        if not position:
            continue
        row = {
            "id": str(raw.get("id") or key),
            "type": raw.get("type"),
            "position": position,
            "directionAngle": raw.get("directionAngle"),
            "targetLevelId": raw.get("targetLevelId"),
            "textId": raw.get("textId"),
            "text": localized.get(str(raw.get("textId") or "")),
            "evidence": "UILevelMapLoadConfig.staticElements exact X/Z position",
        }
        if source:
            row["source"] = source
        rows.append({key: value for key, value in row.items() if value is not None and value != ""})
    return {
        "source": source,
        "worldBounds": _map_ui_world_bounds(config),
        "needInverseXZ": bool(basic.get("needInverseXZ")),
        "orientation": "world_xz_quarter_turn_clockwise" if basic.get("needInverseXZ") else "identity",
        "coordinateSystem": "UILevelMapLoadConfig world X/Z; image top is +Z",
        "staticElements": sorted(rows, key=lambda row: row["id"]),
    }


def _map_layer_metadata(level_id: str, nodes: Iterable[dict], language: str = "CN") -> dict:
    """Publish map UI layers and evidence-based marker-to-tier membership.

    The game does not serialize a ``tierId`` onto WorldEntityRegistry rows.
    We therefore join a marker to a tier only when its X/Z point lies inside a
    raw ``tierInfos`` rectangle.  The resulting Y range is diagnostic evidence
    from those exact transforms, not a visual guess; overlapping tiers remain
    distinct and a marker can list more than one candidate tier.
    """
    config = _load_json(ROOT / f"{MAP_UI_CONFIG_DIR}/{level_id}.json", {}) or {}
    basic = config.get("basic") or {}
    world_bounds = _union_rects([_world_rect({"worldLeftBottom": basic.get("worldRectLeftBottom"), "worldRightTop": basic.get("worldRectRightTop")})])
    rows_by_tier = _config_tier_rows(config)
    names = config.get("tierNames") or {}
    layers: list[dict] = []
    # Accept full marker/quest rows (the production path) and bare position
    # dictionaries (focused probes). Membership belongs on the node beside its
    # other facets; mutating only node["position"] would publish no filterable
    # mapLayerIds even though the in-memory point had been classified.
    point_rows: list[tuple[dict, dict]] = []
    for row in nodes:
        if not isinstance(row, dict):
            continue
        position = row.get("position") if isinstance(row.get("position"), dict) else row
        if isinstance(position, dict):
            point_rows.append((row, position))
    for tier_id in sorted(rows_by_tier, key=lambda value: (int(value) if value.isdigit() else 10**9, value)):
        rows = rows_by_tier[tier_id]
        rects = [row["rect"] for row in rows]
        points = [point for _node, point in point_rows if any(_point_in_rect(point, rect) for rect in rects)]
        ys = [float(point["y"]) for point in points if isinstance(point.get("y"), (int, float))]
        layer = {
            "id": f"tier:{tier_id}",
            "tierId": int(tier_id) if tier_id.isdigit() else tier_id,
            "nameKey": str(names.get(tier_id, "")),
            "worldBounds": _union_rects(rects),
            "cellCount": len(rects),
            "heightRange": {"minY": min(ys), "maxY": max(ys)} if ys else None,
            "heightEvidence": "WorldEntityRegistry positions within UILevelMapLoadConfig.tierInfos rectangles" if ys else "no marker Y samples within tierInfos rectangles",
            "src": None,
        }
        layers.append(layer)

        # Keep the ephemeral rectangles off the JSON payload while allowing
        # build_level to assign memberships below.
        layer["_rects"] = rects
    for node, point in point_rows:
        matches = [layer["id"] for layer in layers if any(_point_in_rect(point, rect) for rect in layer["_rects"])]
        if matches:
            node["mapLayerIds"] = matches
    for layer in layers:
        layer.pop("_rects", None)
    static_metadata = _map_ui_static_elements(level_id, language)
    return {
        "source": f"{MAP_UI_CONFIG_DIR}/{level_id}.json" if config else None,
        "worldBounds": world_bounds,
        "needInverseXZ": bool(basic.get("needInverseXZ")),
        "orientation": "world_xz_quarter_turn_clockwise" if basic.get("needInverseXZ") else "identity",
        "coordinateSystem": "UILevelMapLoadConfig world X/Z; image top is +Z",
        "staticElements": static_metadata["staticElements"],
        "layers": layers,
    }


def _render_tier_layers(level_id: str, config: dict, inverted: bool) -> list[dict]:
    """Composite transparent tier PNGs from the config's exact tier cells."""
    tier_names = config.get("tierNames") or {}
    rows_by_tier = _config_tier_rows(config)
    if not tier_names or not rows_by_tier:
        return []
    render_root = ROOT / "webui/data/map_recovery/render"
    rendered: list[dict] = []
    # Tier art is only useful when a cell-level source exists.  Prefer the
    # game's medium/high/low export in that order, using the same config rects
    # rather than inferring a grid from the PNG dimensions.
    for tier_id in sorted(rows_by_tier, key=lambda value: (int(value) if value.isdigit() else 10**9, value)):
        rows = rows_by_tier[tier_id]
        chosen_layer = None
        rects: dict[tuple[int, int], tuple[float, float, float, float]] = {}
        tiles: dict[tuple[int, int], Path] = {}
        for layer in ("m", "h", "l"):
            candidate_rows = [row for row in rows if row.get("layer") == layer and row.get("x") is not None and row.get("y") is not None]
            candidate_rects = {(row["x"], row["y"]): row["rect"] for row in candidate_rows}
            candidate_tiles = _minimap_tier_tiles(layer, level_id, tier_id)
            matched = set(candidate_rects) & set(candidate_tiles)
            if matched and (chosen_layer is None or len(matched) > len(tiles)):
                chosen_layer = layer
                rects = {cell: candidate_rects[cell] for cell in matched}
                tiles = {cell: candidate_tiles[cell] for cell in matched}
        layer_info = {
            "id": f"tier:{tier_id}",
            "tierId": int(tier_id) if str(tier_id).isdigit() else tier_id,
            "nameKey": str(tier_names.get(tier_id, "")),
            "src": None,
            "status": "map_tier_art_missing",
            "tileCount": 0,
            "layer": chosen_layer,
            "worldBounds": _union_rects(rects.values()),
            "inverted": inverted,
        }
        if not rects:
            rendered.append(layer_info)
            continue
        world_bounds = _union_rects(rects.values())
        assert world_bounds is not None
        weight_x: dict[float, float] = {}
        weight_y: dict[float, float] = {}
        sizes: dict[tuple[int, int], tuple[int, int]] = {}
        for cell in sorted(rects):
            tex_w, tex_h = _png_size(tiles[cell])
            sizes[cell] = (tex_w, tex_h)
            left, bottom, right, top = rects[cell]
            if right > left and tex_w > 0:
                ratio = round(tex_w / (right - left), 6)
                weight_x[ratio] = weight_x.get(ratio, 0.0) + right - left
            if top > bottom and tex_h > 0:
                ratio = round(tex_h / (top - bottom), 6)
                weight_y[ratio] = weight_y.get(ratio, 0.0) + top - bottom
        if not weight_x or not weight_y:
            rendered.append(layer_info)
            continue
        scale_x = max(weight_x, key=lambda ratio: (weight_x[ratio], ratio))
        scale_y = max(weight_y, key=lambda ratio: (weight_y[ratio], ratio))
        img_w = max(1, round((world_bounds["maxX"] - world_bounds["minX"]) * scale_x))
        img_h = max(1, round((world_bounds["maxZ"] - world_bounds["minZ"]) * scale_y))
        sources = {f"{x}_{y}": hashlib.sha256(tiles[(x, y)].read_bytes()).hexdigest() for x, y in sorted(rects)}
        png_path = render_root / f"{level_id}_tier_{tier_id}.png"
        sidecar_path = render_root / f"{level_id}_tier_{tier_id}.sources.json"
        sidecar = {
            "tierId": int(tier_id) if str(tier_id).isdigit() else tier_id,
            "layer": chosen_layer,
            "inverted": inverted,
            "imageOrientation": "exported",
            "rowOrientation": "top_to_bottom_plus_z",
            "worldBounds": world_bounds,
            "imgSize": [img_w, img_h],
            "sources": sources,
        }
        if not (png_path.exists() and _load_json(sidecar_path) == sidecar):
            decoded = {cell: _png_decode(tiles[cell]) for cell in sorted(rects)}
            canvas = [bytearray(img_w * 4) for _ in range(img_h)]
            for cell in sorted(rects):
                left, bottom, right, top = rects[cell]
                tex_w, tex_h, rows_rgba = decoded[cell]
                x0 = round((left - world_bounds["minX"]) * scale_x)
                x1 = round((right - world_bounds["minX"]) * scale_x)
                y0 = round((world_bounds["maxZ"] - top) * scale_y)
                y1 = round((world_bounds["maxZ"] - bottom) * scale_y)
                dst_w, dst_h = x1 - x0, y1 - y0
                if dst_w <= 0 or dst_h <= 0:
                    continue
                for j in range(dst_h):
                    # Exported tier rows use the same top-to-bottom, +Z-at-top
                    # convention as base minimap chunks. Flipping every tile
                    # here inverted local art while leaving its world rect in
                    # place, producing discontinuous edges in multi-cell tiers.
                    src_row = rows_rgba[min(tex_h - 1, (j * tex_h + tex_h // 2) // dst_h)]
                    dst = canvas[y0 + j]
                    for i in range(dst_w):
                        src_i = min(tex_w - 1, (i * tex_w + tex_w // 2) // dst_w) * 4
                        s = src_row[src_i:src_i + 4]
                        if s[3] == 0:
                            continue
                        dst_i = (x0 + i) * 4
                        if s[3] == 255:
                            dst[dst_i:dst_i + 4] = s
                        else:
                            alpha = s[3]
                            inverse = 255 - alpha
                            dst[dst_i] = (s[0] * alpha + dst[dst_i] * inverse) // 255
                            dst[dst_i + 1] = (s[1] * alpha + dst[dst_i + 1] * inverse) // 255
                            dst[dst_i + 2] = (s[2] * alpha + dst[dst_i + 2] * inverse) // 255
                            dst[dst_i + 3] = max(dst[dst_i + 3], alpha)
            render_root.mkdir(parents=True, exist_ok=True)
            _png_write(png_path, img_w, img_h, canvas)
            sidecar_path.write_text(json.dumps(sidecar, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        layer_info.update({
            "src": f"render/{level_id}_tier_{tier_id}.png",
            "status": "in_game_map_tier",
            "tileCount": len(rects),
            "worldBounds": world_bounds,
        })
        rendered.append(layer_info)
    return rendered


_MINIMAP_BOUNDARY = (
    "Background is the game's own map-screen texture: `UILevelMapLoadConfig` declares each chunk's "
    "(x, y) index and exact world rectangle, and the exported chunk art under "
    "`convert_by_type/Texture2D` supplies the pixels. Image top is +Z, matching the marker "
    "projection, and the config world rectangle is published as `worldBounds` so the image "
    "stretches onto exactly the plotted coordinate space."
)


def _minimap_background(level_id: str) -> dict:
    """The in-game map screen for this level, composited from its own chunks.

    Tries the medium, high and low LOD layers in order and publishes a layer
    only when the config declares a complete, rectangular chunk grid whose
    every cell has exported art; anything partial falls through to the next
    layer and finally to the HLOD fallback, because a stretched image with a
    hole would misplace every plotted marker. Half-size chunks draw at reduced
    resolution, exactly as the game's map screen stretches each chunk to its
    own world rectangle.

    `basic.needInverseXZ` is a world-pin projection flag, not an image rotation.
    The in-game Dijiang reference keeps the exported prow on the left while its
    raw world pins require X'=Z, Z'=-X. The composite therefore preserves the
    exported image orientation; the frontend applies the quarter turn to pins.
    """
    render_root = ROOT / "webui/data/map_recovery/render"
    png_path = render_root / f"{level_id}_minimap.png"
    sidecar_path = render_root / f"{level_id}_minimap.sources.json"
    config = _load_json(ROOT / f"{MAP_UI_CONFIG_DIR}/{level_id}.json", {}) or {}
    inverted = bool((config.get("basic") or {}).get("needInverseXZ"))
    tier_layers = _render_tier_layers(level_id, config, inverted)
    for layer, config_key in (("m", "mediumChunks"), ("h", "highChunks"), ("l", "lowChunks")):
        chunks = config.get(config_key) or {}
        rects: dict[tuple[int, int], tuple[float, float, float, float]] = {}
        for chunk in chunks.values():
            if not isinstance(chunk, dict):
                continue
            left_bottom = chunk.get("worldLeftBottom") or {}
            right_top = chunk.get("worldRightTop") or {}
            x, y = chunk.get("x"), chunk.get("y")
            values = (x, y, left_bottom.get("x"), left_bottom.get("y"), right_top.get("x"), right_top.get("y"))
            if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
                continue
            rects[(int(x), int(y))] = (float(left_bottom["x"]), float(left_bottom["y"]), float(right_top["x"]), float(right_top["y"]))
        if not rects:
            continue
        tiles = _minimap_tiles(layer, level_id)
        if set(rects) - set(tiles):
            continue
        min_x = min(c[0] for c in rects)
        max_x = max(c[0] for c in rects)
        min_y = min(c[1] for c in rects)
        max_y = max(c[1] for c in rects)
        # A hole in the grid would leave transparent cells in a stretched
        # background; the composite refuses to paint one.
        if (max_x - min_x + 1) * (max_y - min_y + 1) != len(rects):
            continue
        world_bounds = {
            "minX": min(r[0] for r in rects.values()),
            "maxX": max(r[2] for r in rects.values()),
            "minZ": min(r[1] for r in rects.values()),
            "maxZ": max(r[3] for r in rects.values()),
        }
        # A level's chunks may cover different world sizes (some cells are
        # half-size) with textures to match (600x600, 600x300, 300x300...), so
        # the canvas is laid out in world units at the level's dominant
        # pixels-per-unit ratio, and each tile is stretched to exactly its
        # config rectangle - the same geometry the game's own map screen
        # draws. The ratio that covers the most world extent wins, so one
        # outlier texture cannot rescale the whole map. IHDRs are enough here,
        # which keeps the reuse path below from decoding any pixel.
        weight_x: dict[float, float] = {}
        weight_y: dict[float, float] = {}
        for (x, y) in sorted(rects):
            tex_w, tex_h = _png_size(tiles[(x, y)])
            left, bottom, right, top = rects[(x, y)]
            if right - left > 0 and tex_w > 0:
                weight_x[round(tex_w / (right - left), 6)] = weight_x.get(round(tex_w / (right - left), 6), 0.0) + (right - left)
            if top - bottom > 0 and tex_h > 0:
                weight_y[round(tex_h / (top - bottom), 6)] = weight_y.get(round(tex_h / (top - bottom), 6), 0.0) + (top - bottom)
        if not weight_x or not weight_y:
            continue
        scale_x = max(weight_x, key=lambda r: (weight_x[r], r))
        scale_y = max(weight_y, key=lambda r: (weight_y[r], r))
        img_w = max(1, round((world_bounds["maxX"] - world_bounds["minX"]) * scale_x))
        img_h = max(1, round((world_bounds["maxZ"] - world_bounds["minZ"]) * scale_y))
        sources = {f"{x}_{y}": hashlib.sha256(tiles[(x, y)].read_bytes()).hexdigest() for (x, y) in sorted(rects)}
        # The image size is part of the sidecar so a scale-logic change can
        # never reuse a composite painted at the old scale.
        # The inversion flag is part of the sidecar so a config change can
        # never reuse a composite painted without it.
        sidecar = {"layer": layer, "inverted": inverted, "imageOrientation": "exported", "worldBounds": world_bounds, "imgSize": [img_w, img_h], "sources": sources}
        if png_path.exists() and _load_json(sidecar_path) == sidecar:
            return {
                "status": "in_game_minimap",
                "src": f"render/{level_id}_minimap.png",
                "worldBounds": world_bounds,
                "layer": layer,
                "tileCount": len(rects),
                "inverted": inverted,
                "layers": tier_layers,
                "boundary": _MINIMAP_BOUNDARY,
            }
        decoded = {cell: _png_decode(tiles[cell]) for cell in sorted(rects)}
        min_world_x = world_bounds["minX"]
        max_world_z = world_bounds["maxZ"]
        canvas = [bytearray(img_w * 4) for _ in range(img_h)]
        for (x, y), (cell_w, cell_h, rows) in sorted(decoded.items()):
            left, bottom, right, top = rects[(x, y)]
            x0 = round((left - min_world_x) * scale_x)
            x1 = round((right - min_world_x) * scale_x)
            # The config's y index grows with world Z, while image rows grow
            # downward.  The tile is therefore placed from its world rect
            # (higher-Z rects get smaller y0); exported PNG rows are already
            # top-to-bottom with +Z at the image top and must not be flipped
            # per tile.  A configured inverse is applied only to the complete
            # composite below.
            y0 = round((max_world_z - top) * scale_y)
            y1 = round((max_world_z - bottom) * scale_y)
            dst_w = x1 - x0
            dst_h = y1 - y0
            if dst_w <= 0 or dst_h <= 0:
                continue
            if (dst_w, dst_h) != (cell_w, cell_h):
                # A half-size chunk draws at reduced resolution; nearest
                # neighbour is exact for the 2:1 cells the game uses.
                for j in range(dst_h):
                    src_row = rows[min(cell_h - 1, (j * cell_h + cell_h // 2) // dst_h)]
                    dst = canvas[y0 + j]
                    for i in range(dst_w):
                        s = src_row[min(cell_w - 1, (i * cell_w + cell_w // 2) // dst_w) * 4:
                                    min(cell_w - 1, (i * cell_w + cell_w // 2) // dst_w) * 4 + 4]
                        a = s[3]
                        if a == 0:
                            continue
                        k = (x0 + i) * 4
                        if a == 255:
                            dst[k:k + 4] = s
                        else:
                            ia = 255 - a
                            dst[k] = (s[0] * a + dst[k] * ia) // 255
                            dst[k + 1] = (s[1] * a + dst[k + 1] * ia) // 255
                            dst[k + 2] = (s[2] * a + dst[k + 2] * ia) // 255
                            dst[k + 3] = a if a > dst[k + 3] else dst[k + 3]
                continue
            for j in range(cell_h):
                src = rows[j]
                alpha = bytes(src[3::4])
                if not any(alpha):
                    continue
                dst = canvas[y0 + j]
                base = x0 * 4
                if alpha.count(255) == cell_w:
                    dst[base:base + cell_w * 4] = src
                    continue
                for i in range(cell_w):
                    a = src[i * 4 + 3]
                    if a == 0:
                        continue
                    k = base + i * 4
                    if a == 255:
                        dst[k:k + 4] = src[i * 4:i * 4 + 4]
                    else:
                        ia = 255 - a
                        dst[k] = (src[i * 4] * a + dst[k] * ia) // 255
                        dst[k + 1] = (src[i * 4 + 1] * a + dst[k + 1] * ia) // 255
                        dst[k + 2] = (src[i * 4 + 2] * a + dst[k + 2] * ia) // 255
                        dst[k + 3] = a if a > dst[k + 3] else dst[k + 3]
        render_root.mkdir(parents=True, exist_ok=True)
        _png_write(png_path, img_w, img_h, canvas)
        sidecar_path.write_text(json.dumps(sidecar, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        return {
            "status": "in_game_minimap",
            "src": f"render/{level_id}_minimap.png",
            "worldBounds": world_bounds,
            "layer": layer,
                "tileCount": len(rects),
                "inverted": inverted,
                "layers": tier_layers,
                "boundary": _MINIMAP_BOUNDARY,
        }
    return {
        "status": "in_game_minimap_missing",
        "src": None,
            "worldBounds": None,
            "layers": tier_layers,
            "boundary": (
            "The in-game map screen publishes no complete chunk grid or no exported chunk art for "
            "this level, so the background falls back to the strongest available diagnostic preview."
        ),
    }


def _level_catalog() -> dict[str, int]:
    """`levelId -> idNum` for every declared level."""
    table = _load_json(ROOT / LEVEL_BASIC_INFO_REL, {}) or {}
    catalog: dict[str, int] = {}
    for level_id, row in table.items():
        if isinstance(row, dict) and isinstance(row.get("idNum"), int):
            catalog[str(level_id)] = int(row["idNum"])
    return catalog


def _exact_story_trigger_level_ids() -> set[str]:
    """Return levels that own at least one exact decoded Story trigger shape.

    Some authored dungeon sub-levels have LevelScriptData and exact world-space
    trigger geometry but no LevelBasicInfoTable row. They still have a valid
    trigger coordinate space; excluding them silently drops exact map evidence.
    """
    report = _native_trigger_frontier()
    levels: set[str] = set()
    for row in (report.get("storyTriggerZoneCoverage") or {}).get("rows") or []:
        if not isinstance(row, dict):
            continue
        for observation in row.get("observations") or []:
            if not isinstance(observation, dict) or observation.get("status") != "exact_local_trigger_volume":
                continue
            level_id = str(observation.get("levelId") or "")
            if level_id and any(
                _finite_position((shape or {}).get("position"))
                and str((shape or {}).get("shapeType") or "") in {"Box", "Sphere", "PolyLine"}
                for shape in observation.get("decodedShape") or []
            ):
                levels.add(level_id)
    return levels


def _registry_by_level(registry: dict, catalog: dict[str, int]) -> dict[str, dict[str, list]]:
    """Bucket every registry entity onto the level its global id encodes.

    An id whose `idNum` is not declared in `LevelBasicInfoTable` is dropped
    rather than guessed at: without a level row there is no coordinate space to
    plot it in.
    """
    by_num: dict[int, str] = {}
    for level_id, id_num in catalog.items():
        by_num.setdefault(id_num, level_id)

    buckets: dict[str, dict[str, list]] = {}

    def bucket(level_id: str) -> dict[str, list]:
        return buckets.setdefault(level_id, {"world": [], "script": [], "npc": []})

    for logic_id, info in (registry.get("worldEntityBriefInfos") or {}).items():
        try:
            level_id = by_num.get(int(logic_id) // REGISTRY_ID_SCALE)
        except (TypeError, ValueError):
            continue
        if level_id and isinstance(info, dict):
            bucket(level_id)["world"].append((str(logic_id), info))

    idents = registry.get("m_scriptEntityIdList") or []
    briefs = registry.get("m_scriptEntityBriefInfo") or []
    for ident, info in zip(idents, briefs):
        if not isinstance(ident, dict) or not isinstance(info, dict):
            continue
        try:
            level_id = by_num.get(int(ident.get("scriptIdGlobal")) // REGISTRY_ID_SCALE)
        except (TypeError, ValueError):
            continue
        if level_id:
            bucket(level_id)["script"].append((ident, info))

    for segment_id, info in (registry.get("npcProxyBriefInfos") or {}).items():
        try:
            level_id = by_num.get(int(segment_id) // REGISTRY_ID_SCALE)
        except (TypeError, ValueError):
            continue
        if level_id and isinstance(info, dict):
            bucket(level_id)["npc"].append((str(segment_id), info))
    return buckets


def _teleports_by_level() -> dict[str, list[dict]]:
    table = _load_json(ROOT / TELEPORT_TABLE_REL, {}) or {}
    index: dict[str, list[dict]] = {}
    for entry in (table.get("teleportValidationDatas") or {}).values():
        if isinstance(entry, dict) and entry.get("sceneId"):
            index.setdefault(str(entry["sceneId"]), []).append(entry)
    return index


def _reading_receiver_index(language: str) -> dict[str, list[dict]]:
    """Reading-popup receivers for every published text row, not just e0m0's."""
    rows = _load_json(ROOT / READING_POPUP_REL, {}) or {}
    keys = {key for key in rows if _conv_file_for_key(language, str(key))}
    if not keys:
        return {}
    try:
        return build_levelscript_unhosted_reading_popup_receiver_index(keys)
    except Exception:  # noqa: BLE001 - a recovery helper must not fail the build
        return {}


# --------------------------------------------------------------------------
# Mission digests
# --------------------------------------------------------------------------


def _mission_levels(mission: dict) -> set[str]:
    """Every level this mission can plot content in."""
    flow = mission.get("flow") or {}
    levels = set()
    level_id = str(flow.get("level") or "")
    if level_id:
        levels.add(level_id)
    meta_level = str(((mission.get("timelineRecovery") or {}).get("metadata") or {}).get("levelId") or "")
    if meta_level:
        levels.add(meta_level)
    for pin in flow.get("mapPins") or []:
        if isinstance(pin, dict) and pin.get("scene"):
            levels.add(str(pin["scene"]))
    for ref in (mission.get("extras") or {}).get("levelRefs") or []:
        if isinstance(ref, str) and ref:
            levels.add(ref)
        elif isinstance(ref, dict) and ref.get("levelId"):
            levels.add(str(ref["levelId"]))
    return levels


def _mission_digest(mission_id: str, mission: dict, language: str, level_id: str, registry: dict) -> dict:
    """Everything one mission contributes to one level, in compact form.

    Missions are read one at a time and reduced here so the whole 100 MB mission
    corpus never has to be resident at once.
    """
    script_file_map: dict[str, str] = {}
    file_refs: set[str] = set()
    _collect_references(mission, script_file_map, file_refs)

    story_index = _story_index(mission, language, mission_id)
    attachment_index = _attachment_story_index(mission, language, mission_id)
    timeline = mission.get("timelineRecovery") or {}

    markers = _collect_trigger_markers(mission, mission_id, level_id)
    markers.extend(_map_pin_markers(mission, language, story_index, attachment_index, mission_id, level_id))

    proximity_index = _quest_proximity_index(timeline)
    quest_points = [
        _quest_point(row, language, script_file_map, story_index, proximity_index, mission_id, level_id)
        for row in timeline.get("questSpatialTrack") or []
        if isinstance(row, dict) and row.get("centroid") and _quest_belongs_to_level(row, level_id)
    ]

    return {
        "missionId": mission_id,
        "storyIndex": story_index,
        "attachmentIndex": attachment_index,
        "markers": markers,
        "questPoints": quest_points,
        "scriptFileMap": {key: value for key, value in script_file_map.items() if value},
        "fileRefs": file_refs,
        "sceneUniverse": _placement_marked_scene_universe(mission),
        "crossLevel": _cross_level_scenes(mission, level_id),
        "unresolvedTriggerSlots": _unresolved_trigger_slots(mission, registry),
        "runtimeAsset": _mission_runtime_asset(mission_id),
    }


def _merge_story_index(target: dict[str, list[dict]], source: dict[str, list[dict]]) -> None:
    for key, rows in source.items():
        bucket = target.setdefault(key, [])
        known = {row["key"] for row in bucket}
        for row in rows:
            if row["key"] not in known:
                known.add(row["key"])
                bucket.append(row)


# --------------------------------------------------------------------------
# Level builder
# --------------------------------------------------------------------------


def _registry_markers(
    entities: dict[str, list],
    level_id: str,
    language: str,
    story_index: dict[str, list[dict]],
    attachment_index: dict[str, list[dict]],
    reading_by_script: dict[str, list[dict]],
    script_file_map: dict[str, str],
    action_target_index: dict[str, list[dict]] | None = None,
    world_narrative_index: dict[str, list[dict]] | None = None,
    entity_event_story_index: dict[str, list[dict]] | None = None,
) -> list[dict]:
    """Plot every registry entity this level owns, with its story pins."""
    markers: list[dict] = []

    def action_story_missions(targets: Iterable[dict]) -> list[str]:
        missions = set()
        for target in targets:
            if not target.get("storyPlaybackBinding"):
                continue
            match = re.search(
                r"(?:^|_)([a-z]+\d+m\d+(?:d\d+)?)(?:_|$)",
                str(target.get("storyKey") or ""),
                re.IGNORECASE,
            )
            if match:
                missions.add(match.group(1))
        return sorted(missions)

    def action_story_pins(targets: Iterable[dict]) -> list[dict | None]:
        return [
            _related(
                _conv_file_for_key(language, str(target.get("storyKey") or "")),
                "story_exact_action_target",
                (
                    "Story payload and exact EntityPtr serialized by the same "
                    f"{target.get('actionName')} record"
                ),
            )
            for target in targets
            if target.get("storyPlaybackBinding") and target.get("storyKey")
        ]

    def attach_action_bindings(row: dict, targets: list[dict]) -> tuple[list[dict], list[dict]]:
        """Attach an observational action state to one registry identity."""
        exact = [
            target for target in targets
            if str(target.get("status") or "").startswith("exact_")
        ]
        unresolved = [target for target in targets if target not in exact]

        def compact(target: dict) -> dict:
            return {
                "status": target.get("status"),
                "name": target.get("actionName"),
                "actionLocalId": target.get("actionLocalId"),
                "actionRecordOffset": target.get("actionRecordOffset"),
                "pointerOffset": target.get("pointerOffset"),
                "pointerEndOffset": target.get("pointerEndOffset"),
                "fieldName": target.get("fieldName"),
                "fieldManagedType": target.get("fieldManagedType"),
                "memberOrdinalZeroBased": target.get("memberOrdinalZeroBased"),
                "nativeFieldMappingId": target.get("nativeFieldMappingId"),
                "actionFieldContractKnown": target.get("actionFieldContractKnown"),
                "runtimeLifecycleStatus": target.get("runtimeLifecycleStatus"),
                "levelInteractiveAlignmentStatus": target.get("levelInteractiveAlignmentStatus"),
                "nativeScriptSlotMappingId": target.get("nativeScriptSlotMappingId"),
                "nativeScriptSlotContractStatus": target.get("nativeScriptSlotContractStatus"),
                "entityPtrGetterResolution": target.get(
                    "entityPtrGetterResolution"
                ),
                "entityPtrOutputAliasEvidence": target.get(
                    "entityPtrOutputAliasEvidence"
                ),
                "nativeGetterContractStatus": target.get(
                    "nativeGetterContractStatus"
                ),
                "targetDomain": target.get("targetDomain"),
                "registryResolutionStatus": target.get("registryResolutionStatus"),
                "registryMatchCount": target.get("registryMatchCount"),
                "npcProxyId": target.get("npcProxyId"),
                "spatialResolutionEvidence": target.get(
                    "spatialResolutionEvidence"
                ),
                "spatialResolutionDiagnostics": target.get(
                    "spatialResolutionDiagnostics"
                ) or [],
                "placementSourceFiles": target.get("placementSourceFiles") or [],
                "controlTriggers": target.get("controlTriggers") or [],
                "storyPlaybackBinding": target.get("storyPlaybackBinding"),
                "sourceFile": target.get("sourceFile"),
            }

        row["actions"] = [compact(target) for target in exact]
        row["unresolvedActionReferences"] = []
        for target in unresolved:
            field_exact = target.get("fieldNameStatus") == "exact_native_formatter_member"
            row["unresolvedActionReferences"].append({
                **compact(target),
                "reasonCode": (
                    "registered_slot_levelinteractive_alignment_missing"
                    if field_exact
                    and target.get("targetDomain") == "registered_script_slot_unresolved"
                    else "serialized_member_layout_unresolved"
                    if target.get("actionFieldContractKnown")
                    else "unresolved_formatter_member"
                ),
                "fieldNameStatus": target.get("fieldNameStatus"),
                "nativeFieldContractStatus": target.get("nativeFieldContractStatus"),
            })
        registry_bridge_only = bool(unresolved) and all(
            reference.get("reasonCode")
            == "registered_slot_levelinteractive_alignment_missing"
            for reference in row["unresolvedActionReferences"]
        )
        serialized_layout_unresolved = any(
            reference.get("reasonCode") == "serialized_member_layout_unresolved"
            for reference in row["unresolvedActionReferences"]
        )
        row["actionBindingStatus"] = (
            "exact_plus_unresolved" if exact and unresolved
            else "exact_bound" if exact
            else "unresolved_registry_bridge" if registry_bridge_only
            else "unresolved_member_layout" if serialized_layout_unresolved
            else "unresolved_decoder" if unresolved
            else "no_reference_observed"
        )
        row["actionBindingBoundary"] = (
            "No action reference was observed within decoded current-build "
            "LevelScript evidence; this is not proof that the slot is unused."
            if not targets else
            "Only build-validated formatter fields and constant EntityPtr identities are exact bindings."
        )
        return exact, unresolved

    def attach_entity_event_stories(row: dict, identity: str) -> list[dict]:
        bindings = list((entity_event_story_index or {}).get(identity, []))
        if not bindings:
            return []
        row["entityEventStoryBindings"] = bindings
        row["sceneKeys"] = sorted(set(row.get("sceneKeys") or []) | {
            str(binding.get("storyKey") or "")
            for binding in bindings
            if binding.get("storyKey")
        })
        row["relatedFiles"] = _sorted_related(_merge_related(
            row.get("relatedFiles") or [],
            [
                _related(
                    binding.get("sourceFile"),
                    "story_exact_entity_event_target",
                    (
                        f"{binding.get('eventName')} names this exact "
                        + (
                            "NPC proxy before the Story playback path"
                            if binding.get("status")
                            == "exact_proxy_patrol_event_target"
                            else "constant EntityPtr before the Story playback path"
                        )
                    ),
                )
                for binding in bindings
            ] + [
                _related(
                    _conv_file_for_key(language, str(binding.get("storyKey") or "")),
                    "story_exact_entity_event_target",
                    "Story reached from the exact specified-entity event carrier",
                )
                for binding in bindings
            ],
        ))
        return bindings

    for logic_id, info in entities.get("world") or []:
        position = _finite_position(info.get("position"))
        if not position:
            continue
        kind, sub_kind, label, interaction = _classify_entity(info.get("detailId", ""), info.get("entityType"))
        label = _entity_display_name(info.get("detailId"), language) or label
        row = marker(kind, label, f"world:{logic_id}", info, "WorldEntityRegistry exact transform", interaction, sub_kind)
        row["position"] = position
        action_targets = (action_target_index or {}).get(f"world:{logic_id}", [])
        exact_action_targets, unresolved_action_targets = attach_action_bindings(row, action_targets)
        if exact_action_targets:
            row["controlledByTriggers"] = []
            for target in exact_action_targets:
                for trigger in target.get("controlTriggers") or []:
                    if trigger not in row["controlledByTriggers"]:
                        row["controlledByTriggers"].append(trigger)
            row["actionSourceFiles"] = _coalesce_file_paths(
                [target.get("sourceFile") for target in exact_action_targets]
            )
            if row["kind"] == "empty_slot":
                action_names = sorted({
                    str(target.get("actionName") or "")
                    for target in exact_action_targets
                    if target.get("actionName")
                })
                row["kind"] = "script_target"
                row["subKind"] = "world_action_target"
                row["interactionStatus"] = "exact_world_entity_action_target"
                row["label"] = " / ".join(action_names) or row["label"]
                row["evidence"] = (
                    "build-locked native formatter member + exact constant "
                    "global EntityPtr + WorldEntityRegistry transform"
                )
        narrative_bindings = (world_narrative_index or {}).get(f"{level_id}:{logic_id}", [])
        row["sceneKeys"] = sorted({
            str(binding.get("webuiStoryKey") or "")
            for binding in narrative_bindings
            if binding.get("webuiStoryKey")
        } | {
            str(target.get("storyKey") or "")
            for target in exact_action_targets
            if target.get("storyPlaybackBinding") and target.get("storyKey")
        })
        row["missions"] = action_story_missions(exact_action_targets)
        if narrative_bindings:
            row["interactionStatus"] = "exact_narrative_component"
            row["evidence"] = (
                "WorldEntityRegistry exact transform + LevelData exact "
                "embeddedLogicId/NarrativeComponent.typeId"
            )
            row["narrativeBindings"] = [{
                "storyKey": binding.get("webuiStoryKey"),
                "originalStoryKey": binding.get("originalStoryKey"),
                "entityDetailId": binding.get("entityDetailId"),
                "levelDataAsset": binding.get("levelDataAsset"),
                "recordIndex": binding.get("recordIndex"),
                "recordOffset": binding.get("recordOffset"),
                "nativeConsumer": binding.get("nativeConsumer"),
                "nativeMappingId": binding.get("nativeMappingId"),
            } for binding in narrative_bindings]
        # `registryBacked` stands in for the repeated level-wide registry file;
        # exact narrative bindings retain their narrower LevelData source below.
        row["registryBacked"] = True
        row["relatedFiles"] = _sorted_related(_merge_related([], [
            *[
                _related(
                    str(binding.get("sourceFile") or ""),
                    "story_world_narrative",
                    "same counted LevelInteractiveData record stores this embeddedLogicId and NarrativeComponent.typeId",
                )
                for binding in narrative_bindings
            ],
            *[
                _related(
                    _conv_file_for_key(language, str(binding.get("webuiStoryKey") or "")),
                    "story_world_narrative",
                    "published conversation bound by the exact LevelData narrative record",
                )
                for binding in narrative_bindings
            ],
            _related(_script_file_for_id(str(logic_id), level_id), "level_script", "level script sharing this entity id"),
            *[
                _related(
                    target.get("sourceFile"),
                    "script_action_target_source",
                    f"{target.get('actionName')} names this exact global EntityPtr",
                )
                for target in exact_action_targets
            ],
            *action_story_pins(exact_action_targets),
            *_interactive_semantic_files(info.get("detailId")),
        ]))
        attach_entity_event_stories(row, f"world:{logic_id}")
        markers.append(row)

    for ident, info in entities.get("script") or []:
        position = _finite_position(info.get("position"))
        if not position:
            continue
        script_id = str(ident.get("scriptIdGlobal"))
        slot_id = str(ident.get("slotId"))
        kind, sub_kind, label, interaction = _classify_entity(info.get("detailId", ""), info.get("entityType"))
        label = _entity_display_name(info.get("detailId"), language) or label
        row = marker(
            kind,
            label,
            f"script:{script_id}:{slot_id}",
            info,
            "WorldEntityRegistry exact script/slot transform",
            interaction,
            sub_kind,
        )
        row["position"] = position

        exact_stories = story_index.get(f"slot:{script_id}:{slot_id}", [])
        slot_stories = story_index.get(f"scriptslot:{script_id}:{slot_id}", [])
        readings = reading_by_script.get(script_id, [])
        action_targets = (action_target_index or {}).get(f"{script_id}:{slot_id}", [])

        # The registry already proves this exact script/slot transform.  A
        # LevelScript file owns every slot in its script, so attaching that
        # container file (or script-wide Story context) to every sibling point
        # creates a false many-point binding.  Only slot-specific consumers
        # below may add files or Story rows to this marker.
        source_files: list[str] = []
        reading_pins: list[dict | None] = []
        exact_action_targets, unresolved_action_targets = attach_action_bindings(row, action_targets)
        if action_targets:
            all_action_targets_exact = len(exact_action_targets) == len(action_targets)
            unresolved_registry_bridge = (
                row.get("actionBindingStatus") == "unresolved_registry_bridge"
            )
            unresolved_member_layout = (
                row.get("actionBindingStatus") == "unresolved_member_layout"
            )
            row["kind"] = "script_target" if exact_action_targets else "script_target_candidate"
            row["subKind"] = (
                "registered_action_target" if exact_action_targets
                else "registered_action_target_candidate"
            )
            row["interactionStatus"] = (
                "exact_script_action_target" if exact_action_targets
                else (
                    "unresolved_registered_slot_bridge" if unresolved_registry_bridge
                    else "unresolved_serialized_member_layout" if unresolved_member_layout
                    else "unresolved_action_formatter_member"
                )
            )
            action_names = sorted({str(target.get("actionName") or "") for target in action_targets if target.get("actionName")})
            row["label"] = " / ".join(action_names) or "脚本动作目标"
            row["controlledByTriggers"] = []
            for target in exact_action_targets:
                for trigger in target.get("controlTriggers") or []:
                    if trigger not in row["controlledByTriggers"]:
                        row["controlledByTriggers"].append(trigger)
            row["evidence"] = (
                "build-locked native formatter member + exact constant EntityPtr + unique registered script slot"
                if exact_action_targets else
                (
                    "build-locked native formatter member + exact current-script slot pointer; "
                    "LevelInteractiveData registration alignment unresolved"
                    if unresolved_registry_bridge else
                    "native formatter field is known; this record's nullable/dynamic/member boundary remains unresolved"
                    if unresolved_member_layout else
                    "exact constant EntityPtr bytes inside a validated action record; formatter member unresolved"
                )
            )
            row["actionSourceFiles"] = _coalesce_file_paths([target.get("sourceFile") for target in exact_action_targets])
        for reading in readings:
            producer = next(
                (
                    entry for entry in reading.get("interactiveEventProducers") or []
                    if str(entry.get("scriptIdGlobal")) == script_id and str(entry.get("entitySlotId")) == slot_id
                ),
                None,
            )
            story_key = str(reading.get("key") or reading.get("readingPopupId") or "")
            if producer is not None:
                # The exact producing entity is known, so this marker is the
                # thing the player reads, not merely its owning script.
                row["kind"] = "story"
                row["subKind"] = "reading_popup"
                row["label"] = f"{story_key} 敏点" if story_key else row["label"]
                row["interactionStatus"] = "exact_interaction"
                document_title = _story_display_title(language, story_key)
                row["label"] = document_title or story_key or row["label"]
                if document_title:
                    row["documentTitle"] = document_title
                row["evidence"] = "exact script/slot + custom event + ShowUIReadingPopPanel"
                row["storyKey"] = story_key
                row["eventName"] = producer.get("eventName")
                row["action"] = "ShowUIReadingPopPanel"
                source_files = _coalesce_file_paths([*source_files, reading.get("sourceFile")])
                reading_pins.append(_related(
                    _conv_file_for_key(language, story_key),
                    "story_exact_producer",
                    f"text this entity shows ({story_key})",
                ))
            if producer is not None and reading.get("sourceFile"):
                reading_pins.append(_related(reading["sourceFile"], "level_script", "level script that shows the reading popup"))

        if source_files:
            row["sourceFiles"] = source_files
            row["source"] = source_files[0]
        row["sceneKeys"] = sorted({
            story["key"] for story in [*exact_stories, *slot_stories]
        } | ({row["storyKey"]} if row.get("storyKey") else set()) | {
            str(target.get("storyKey") or "")
            for target in exact_action_targets
            if target.get("storyPlaybackBinding") and target.get("storyKey")
        })
        row["missions"] = sorted({
            *_story_missions(exact_stories, slot_stories),
            *action_story_missions(exact_action_targets),
        })
        row["registryBacked"] = True
        row["relatedFiles"] = _sorted_related(_merge_related([], [
            *[_related(path, "placement_source", "file that proves this placement") for path in source_files],
            *reading_pins,
            *_story_pins(exact_stories, "story_exact_producer", "story produced by this exact script/slot"),
            *_story_pins(slot_stories, "story_script_slot", "story whose producer names this script/slot"),
            *action_story_pins(exact_action_targets),
            *[
                _related(
                    target.get("sourceFile"),
                    (
                        "script_action_target_source"
                        if target.get("status") == "exact_registered_script_action_target"
                        else "script_action_target_candidate_source"
                    ),
                    f"{target.get('actionName')} contains this exact registered script/slot pointer",
                )
                for target in action_targets
            ],
            *_interactive_semantic_files(info.get("detailId")),
        ]))
        attach_entity_event_stories(row, f"script:{script_id}:{slot_id}")
        markers.append(row)

    for segment_id, info in entities.get("npc") or []:
        position = _finite_position(info.get("position"))
        if not position:
            continue
        proxy_id = str(info.get("proxyId") or "")
        stories = attachment_index.get(f"proxy:{proxy_id}", []) if proxy_id else []
        world_fallback_action_targets = [
            target
            for target in (action_target_index or {}).get(
                f"world:{segment_id}", []
            )
            if target.get("spatialResolutionEvidence")
            == "exact_npc_proxy_brief_and_table_join"
        ]
        npc_getter_action_targets = [
            target
            for target in (action_target_index or {}).get(
                f"npc:{segment_id}", []
            )
            if target.get("targetDomain") == "npc_proxy_logic_id"
            and target.get("npcProxyId") == proxy_id
            and target.get("entityLogicId") == int(segment_id)
        ]
        action_targets = (
            npc_getter_action_targets
            if npc_getter_action_targets
            else world_fallback_action_targets
        )
        row = {
            "kind": "npc",
            "subKind": "npc_proxy",
            "label": proxy_id.split("_", 1)[0] if proxy_id else "NPC",
            "identity": (
                f"npc:{segment_id}" if npc_getter_action_targets
                else f"world:{segment_id}" if world_fallback_action_targets
                else f"npc:{segment_id}"
            ),
            "position": position,
            "detailId": proxy_id,
            "interactionStatus": "npc_proxy",
            "evidence": "WorldEntityRegistry exact npc proxy transform",
            "npcProxyId": proxy_id,
            "registryBacked": True,
            "sceneKeys": sorted({story["key"] for story in stories}),
            "missions": _story_missions(stories),
            "missionPhases": _npc_mission_phases(stories),
            "relatedFiles": _sorted_related(_merge_related([], [
                *_story_pins(stories, "story_npc_proxy", "dialog attached to this NPC proxy"),
            ])),
        }
        exact_action_targets, _unresolved_action_targets = attach_action_bindings(
            row,
            action_targets,
        )
        row["sceneKeys"] = sorted(set(row.get("sceneKeys") or []) | {
            str(target.get("storyKey") or "")
            for target in exact_action_targets
            if target.get("storyPlaybackBinding") and target.get("storyKey")
        })
        row["missions"] = sorted({
            *row.get("missions", []),
            *action_story_missions(exact_action_targets),
        })
        row["relatedFiles"] = _sorted_related(_merge_related(
            row.get("relatedFiles") or [],
            action_story_pins(exact_action_targets),
        ))
        if exact_action_targets:
            row["interactionStatus"] = (
                "exact_npc_proxy_action_target"
                if npc_getter_action_targets
                else "exact_world_entity_action_target"
            )
            row["evidence"] = (
                "build-locked EntityPtr getter + exact constant proxy id + "
                "exact npcProxyBriefInfos/NpcProxyTable identity and transform"
                if npc_getter_action_targets
                else "build-locked native formatter member + exact constant global "
                     "EntityPtr + exact npcProxyBriefInfos/NpcProxyTable transform"
            )
            row["placementEvidenceStatus"] = (
                "exact_npc_proxy_brief_and_table_join"
            )
            row["sourceFiles"] = [REGISTRY_REL, NPC_PROXY_TABLE_REL]
            row["source"] = REGISTRY_REL
            row["actionSourceFiles"] = _coalesce_file_paths(
                [target.get("sourceFile") for target in exact_action_targets]
            )
            if npc_getter_action_targets and world_fallback_action_targets:
                row["worldFallbackActionTargets"] = world_fallback_action_targets
            row["relatedFiles"] = _sorted_related(_merge_related(
                row["relatedFiles"],
                [
                    _related(
                        REGISTRY_REL,
                        "placement_source",
                        "exact npc proxy segment identity and authored position",
                    ),
                    _related(
                        NPC_PROXY_TABLE_REL,
                        "placement_source",
                        "exact proxy id row corroborates position and supplies rotation",
                    ),
                    *[
                        _related(
                            target.get("sourceFile"),
                            "script_action_target_source",
                            (
                                f"{target.get('actionName')} resolves through this exact NPC proxy getter"
                                if npc_getter_action_targets
                                else f"{target.get('actionName')} names this exact global EntityPtr"
                            ),
                        )
                        for target in exact_action_targets
                    ],
                ],
            ))
        attach_entity_event_stories(row, f"npc:{segment_id}")
        markers.append(row)
    return markers


def _teleport_markers(level_id: str, entries: list[dict], attachment_index: dict[str, list[dict]], language: str) -> list[dict]:
    markers: list[dict] = []
    for entry in entries:
        position = _finite_position(entry.get("position"))
        if not position:
            continue
        parent = str(entry.get("subDataParentId") or "")
        script_file = _script_file_for_id(parent, level_id)
        stories = attachment_index.get(f"condition:{parent}", [])
        markers.append({
            "kind": "spawn",
            "subKind": "teleport_arrival",
            "label": "传送落点",
            "identity": f"teleport:{entry.get('id')}",
            "position": position,
            "detailId": str(entry.get("id") or ""),
            "interactionStatus": "teleport_arrival",
            "detailAlias": {"canonical": "teleport_arrival", "zh": "传送落点", "en": "Teleport Arrival"},
            "evidence": "LevelScriptTeleportValidationDataTable exact arrival transform",
            "teleportReason": entry.get("teleportReason"),
            "sceneKeys": sorted({story["key"] for story in stories}),
            "missions": _story_missions(stories),
            "sourceFiles": [TELEPORT_TABLE_REL],
            "source": TELEPORT_TABLE_REL,
            "relatedFiles": _sorted_related(_merge_related([], [
                _related(TELEPORT_TABLE_REL, "placement_source", "table row that fixes this arrival transform"),
                _related(script_file, "level_script", "level script that requests this teleport"),
                *_story_pins(stories, "story_script_condition", "scene conditioned on the script that teleports here"),
            ])),
        })
    return markers


def _model_asset_index(mesh_root: Path) -> list[Path]:
    """Return exported OBJ files once, so level fallback checks stay linear.

    The map builder handles many levels and the asset export can contain tens
    of thousands of OBJ files. A process-local cache avoids rescanning that
    directory for every level while keeping tests that patch ``ROOT`` safe.
    """
    root = mesh_root.resolve()
    cached = _MODEL_ASSET_INDEX.get(root)
    if cached is not None:
        return cached
    if not root.is_dir():
        _MODEL_ASSET_INDEX[root] = []
        return []
    files = sorted(path for path in root.glob("*.obj") if path.is_file())
    _MODEL_ASSET_INDEX[root] = files
    return files


def _unplaced_model_scene(level_id: str) -> dict:
    """Publish level-matched OBJ assets without claiming scene placement.

    Some levels (notably the base01 decks) have exported models but no HLOD
    cluster containers. Their OBJ vertices do not carry a GameObject/Transform
    owner, so they cannot be rendered onto the map safely. The Assets viewer
    can still inspect exact filename matches; this manifest is intentionally
    asset-only and has no ``src``/``worldBounds`` background fields.
    """
    mesh_root = ROOT / MODEL_ROOT_REL
    needle = str(level_id or "").strip().lower()
    if not needle:
        return {
            "status": "obj_level_assets_unavailable",
            "method": "level_filename_match_only",
            "meshes": [],
            "meshCount": 0,
            "triangleCount": 0,
            "positionStatus": "unplaced",
            "boundary": (
                "No level id was available for a safe OBJ filename match; no model asset is claimed."
            ),
        }

    # Match a complete level token, not a shared family token such as
    # ``base01`` or ``dung02``. A family-wide match would make the three
    # 帝江号 decks look identical and would falsely assign assets to them.
    candidates = [path for path in _model_asset_index(mesh_root) if needle in path.stem.lower()]
    rows: list[dict] = []
    export_root = (ROOT / "export_full").resolve()
    for path in candidates:
        try:
            relative = path.resolve().relative_to(export_root).as_posix()
        except (OSError, ValueError):
            continue
        parts = relative.split("/")
        if len(parts) < 5 or parts[:2] != ["recovered", "AnimeStudio-cli"]:
            continue
        if parts[2] != "StreamingAssets" or parts[3] != "convert_by_type":
            continue
        asset_rel = f"{parts[2]}/{'/'.join(parts[4:])}"
        rows.append({
            "name": path.stem,
            "pathId": path.stem.rsplit("_p", 1)[-1].upper() if "_p" in path.stem else None,
            "src": f"/export_full/{relative}",
            "assetRel": asset_rel,
            "triangles": None,
            "positionStatus": "unplaced",
        })
        if len(rows) >= MAX_UNPLACED_MODEL_ASSETS:
            break
    return {
        "status": "obj_level_assets_unplaced" if rows else "obj_level_assets_unavailable",
        "method": "level_filename_match_only",
        "meshes": rows,
        "meshCount": len(rows),
        "triangleCount": None,
        "positionStatus": "unplaced",
        "boundary": (
            "These OBJ files match the level id in their exported filename, but no authored "
            "GameObject/Transform or mesh-to-scene placement was recovered. Open them in Assets "
            "for inspection; they are not drawn on this map."
        ),
    }


def _render_background(level_id: str) -> dict:
    """Published top-down background, with a non-spatial OBJ fallback."""
    # Resolved from ROOT rather than the module-level OUT so a relocated repo
    # root (and the focused tests that patch it) reads its own render folder.
    # Keep this lookup ahead of shared-region suppression: a level can own an
    # authoritative minimap and still expose its aligned HLOD/model layers.
    render_root = ROOT / "webui/data/map_recovery/render"
    preview_path = render_root / f"{level_id}_hlod_grid_inferred.json"
    preview = _load_json(preview_path) if preview_path.exists() else None
    if preview:
        # Legacy image-registration experiments are not part of the game's map
        # coordinate contract. Ignore stale generated manifests until their
        # expensive HLOD rasters are next rebuilt.
        preview.pop("renderAlignment", None)
        if str(preview.get("status") or "").startswith("inferred_hlod_"):
            exact_fallback = preview.get("exactPointFallback")
            if (
                isinstance(exact_fallback, dict)
                and exact_fallback.get("status") == "exact_registry_transform_point_cloud"
                and exact_fallback.get("src")
                and exact_fallback.get("worldBounds")
            ):
                return {
                    **exact_fallback,
                    "diagnosticManifest": preview_path.relative_to(
                        ROOT / "webui/data/map_recovery"
                    ).as_posix(),
                    "suppressedInferredSurface": True,
                    "boundary": (
                        "This level has no in-game minimap. Its inferred HLOD surface remains suppressed, "
                        "while the recovered layer is restored from exact published registry and quest "
                        "X/Y/Z transforms only. Points are not connected into invented terrain."
                    ),
                }
            model_scene = _unplaced_model_scene(level_id)
            return {
                "status": "inferred_hlod_alignment_suppressed",
                "src": None,
                "worldBounds": None,
                "diagnosticManifest": preview_path.relative_to(ROOT / "webui/data/map_recovery").as_posix(),
                "modelScene": model_scene,
                "boundary": (
                    "The exported HLOD mesh has no recovered authored GameObject/Transform. Its grid-name "
                    "placement and region origin are inferred, so it is deliberately not drawn on the map. "
                    "Only authored minimap rectangles, exact marker transforms, or scene geometry with an "
                    "exact recovered transform may participate in spatial alignment."
                ),
            }
        evidence = _danger_surface_evidence(level_id, preview)
        if evidence:
            preview["surfaceEvidence"] = evidence
        return preview
    authored = authored_streaming_scene(level_id)
    if authored and authored.get("sceneId") in AUTHORED_REGION_BACKGROUND_SCENES and not isolated_art_source(level_id):
        scene_id = str(authored["sceneId"])
        return {
            "status": "shared_authored_region_background",
            "src": None,
            "worldBounds": None,
            "modelScene": {"status": "represented_by_shared_region", "meshCount": 0},
            "boundary": (
                f"This gameplay level declares the shared {scene_id} streaming scene. Its exact markers are "
                "drawn over that region's exported minimap screens; the sparse per-level point cloud is "
                "suppressed so it cannot darken or duplicate the authored regional surface."
            ),
        }
    model_scene = _unplaced_model_scene(level_id)
    return {
        "status": "asset_transform_recovery_required",
        "src": None,
        "worldBounds": None,
        "hlodTextureCandidateCount": 0,
        "modelScene": model_scene,
        "boundary": (
            "No top-down background is published for this level. Markers are plotted from exact "
            "recovered transforms; a background is only added once HLOD meshes and scene transforms "
            "are reconstructed and rendered with an orthographic +Y camera. Level-matched OBJ files "
            "remain available below as unplaced Assets viewer links."
        ),
    }


# Current danger-reappearance presentation set: three map01 contracts and
# three map02 contracts. Keep the labels tied to the evidence actually
# published by the preview, rather than treating every ``bdg`` prefix alike.
_DANGER_INFERRED_HLOD_CROPS = frozenset({
    "dung01_bdg001",
    "dung01_bdg002",
    "dung01_bdg003",
    "dung02_bdg001",
})


def _danger_surface_evidence(level_id: str, preview: dict) -> dict | None:
    """Concise, fail-closed surface accuracy label for the active danger maps."""
    status = str((preview or {}).get("status") or "")
    if level_id in _DANGER_INFERRED_HLOD_CROPS and status.startswith("inferred_hlod_"):
        return {
            "accuracy": "inferred_hlod_crop",
            "label": "Inferred HLOD crop",
            "evidence": (
                "Crop bounds come from exact danger-map markers; geometry placement reuses an inferred "
                "source-art HLOD grid."
            ),
        }
    if level_id == "dung02_bdg002" and status == "recovered_streaming_mesh_topdown":
        return {
            "accuracy": "exact_mesh_color_unverified",
            "label": "Exact mesh placement - color unverified",
            "evidence": (
                "Streaming matrices and matched mesh geometry are exact; no reliable texture color is "
                "visible in the recovered surface."
            ),
        }
    if level_id == "dung02_bdg005" and status == "recovered_streaming_textured_topdown":
        return {
            "accuracy": "exact_mesh_partial_base_color",
            "label": "Exact mesh placement - partial base color",
            "evidence": (
                "Streaming matrices and matched mesh geometry are exact; recovered base color is visible "
                "only on surfaces with a supported material binding."
            ),
        }
    return None


def _facets(markers: list[dict], quest_points: list[dict], missions: list[str]) -> dict:
    """Counts the page needs to build its filter tree without rescanning nodes.

    `kinds` is the two-level layer tree (kind -> subKind), and `missions` says
    how much of the map each mission actually accounts for, so a reader can see
    which missions are worth isolating before selecting one.
    """
    kinds: dict[str, dict] = {}
    for row in markers:
        bucket = kinds.setdefault(row["kind"], {"count": 0, "storyCount": 0, "subKinds": {}})
        bucket["count"] += 1
        bucket["storyCount"] += 1 if row.get("storyCount") else 0
        sub_kind = row.get("subKind") or row["kind"]
        sub = bucket["subKinds"].setdefault(
            sub_kind,
            {"count": 0, "label": row.get("label") or ""},
        )
        sub["count"] += 1

    mission_rows: dict[str, dict] = {mission: {"markers": 0, "questPoints": 0, "stories": 0} for mission in missions}
    for row in markers:
        for mission in row.get("missions") or []:
            entry = mission_rows.setdefault(mission, {"markers": 0, "questPoints": 0, "stories": 0})
            entry["markers"] += 1
            entry["stories"] += len(row.get("sceneKeys") or [])
    for row in quest_points:
        for mission in row.get("missions") or []:
            entry = mission_rows.setdefault(mission, {"markers": 0, "questPoints": 0, "stories": 0})
            entry["questPoints"] += 1
    return {
        "kinds": {key: kinds[key] for key in sorted(kinds)},
        "missions": {key: mission_rows[key] for key in sorted(mission_rows)},
    }


def build_level(
    level_id: str,
    id_num: int | None,
    language: str,
    registry: dict,
    entities: dict[str, list],
    digests: list[dict],
    teleports: list[dict],
    reading_by_level: dict[str, dict[str, list[dict]]],
    names: dict[str, str] | None = None,
) -> dict:
    """Recover one level from its own exact evidence.

    Nothing in here is level-specific: the same registry buckets, mission
    digests, teleport rows and reading receivers are consulted for every map,
    and a level simply publishes fewer nodes when it owns less evidence.
    """
    if names is None:
        names = _level_names(language)
    mission_names = _mission_names(language)
    story_index: dict[str, list[dict]] = {}
    attachment_index: dict[str, list[dict]] = {}
    script_file_map: dict[str, str] = {}
    file_refs: set[str] = set()
    markers: list[dict] = []
    quest_points: list[dict] = []
    unresolved_rows: list[dict] = []
    missions: list[str] = []

    for digest in digests:
        if digest["missionId"] and digest["missionId"] not in missions:
            missions.append(digest["missionId"])
        _merge_story_index(story_index, digest["storyIndex"])
        _merge_story_index(attachment_index, digest["attachmentIndex"])
        for key, value in digest["scriptFileMap"].items():
            script_file_map.setdefault(key, value)
        file_refs.update(digest["fileRefs"])
        markers.extend(digest["markers"])
        quest_points.extend(digest["questPoints"])
        unresolved_rows.extend(digest["unresolvedTriggerSlots"]["stories"])

    readings: dict[str, list[dict]] = {}
    for scope in (reading_by_level.get("") or {}, reading_by_level.get(level_id) or {}):
        for script_id, rows in scope.items():
            readings.setdefault(script_id, []).extend(rows)

    action_target_index = build_levelscript_registered_action_target_index(level_id)
    action_entity_field_diagnostics = action_target_index.pop(
        ACTION_ENTITY_FIELD_DIAGNOSTICS_KEY,
        [],
    )
    unplaced_action_targets = [
        target
        for key, targets in action_target_index.items()
        if key.startswith("unplaced-")
        for target in targets
    ]
    proxy_patrol_contexts = _exact_story_proxy_patrol_checkpoint_contexts(level_id)
    npc_patrol_contexts = _exact_story_npc_patrol_checkpoint_contexts(level_id)
    entity_event_story_index = _exact_story_entity_event_index(level_id)
    for identity, bindings in _exact_story_proxy_patrol_event_index(
        level_id,
        proxy_patrol_contexts,
    ).items():
        entity_event_story_index.setdefault(identity, []).extend(bindings)
    markers = _registry_markers(
        entities,
        level_id,
        language,
        story_index,
        attachment_index,
        readings,
        script_file_map,
        action_target_index,
        _world_narrative_bindings(language),
        entity_event_story_index,
    ) + markers
    markers.extend(_exact_story_trigger_markers(level_id, language))
    markers.extend(_gender_select_casefold_trigger_markers(level_id, language))
    markers.extend(_exact_story_spawner_markers(level_id, language))
    markers.extend(_exact_story_patrol_checkpoint_markers(
        [*proxy_patrol_contexts, *npc_patrol_contexts],
        language,
    ))
    markers.extend(_teleport_markers(level_id, teleports, attachment_index, language))

    # The map UI config is also the authority for map floors/overlays.  Join
    # exact marker transforms to its tier rectangles before sorting/publishing
    # so the frontend can hide a floor without guessing from a screenshot.
    map_config = _map_layer_metadata(
        level_id,
        [*markers, *quest_points],
        language,
    )

    level_scripts = _level_script_files(level_id)
    level_data = _level_data_files(level_id)

    pinned_files: set[str] = set()
    for node in [*markers, *quest_points]:
        pinned_files.update(path for path in node.get("sourceFiles") or [])
        pinned_files.update(pin["path"] for pin in node.get("relatedFiles") or [])
    marker_file_refs = sorted({path for row in markers for path in row.get("sourceFiles") or []})
    unlinked_mission_files = sorted(path for path in file_refs if path and path not in pinned_files)

    map_related_files = _sorted_related(_merge_related([], [
        _related(REGISTRY_REL, "entity_registry", "exact world/script entity transforms for this level"),
        _related(LEVEL_BASIC_INFO_REL, "level_definition", f"declares {level_id} (idNum {id_num})")
        if id_num is not None else None,
        _related(MAP_ID_TABLE_REL, "level_definition", f"registers the map id for {level_id}"),
        _related(map_config.get("source"), "level_definition", "raw UILevelMapLoadConfig map rectangles and tier names"),
        *[
            _related(_mission_runtime_asset(mission), "mission_runtime", f"mission that plays in this level ({mission})")
            for mission in missions
        ],
        *_story_pins(
            story_index.get("mission:areas", []),
            "story_mission_scope",
            "story scoped to a mission's whole area set, not to one trigger",
        ),
        _related(TELEPORT_TABLE_REL, "level_script", "teleport arrivals validated for this level") if teleports else None,
        *[_related(path, "level_script", "level script in this level") for path in level_scripts],
        *[_related(path, "mission_reference", "mission sub-level data hosted in this level") for path in level_data],
        *[
            _related(path, "mission_reference", "referenced by a mission but not pinned to a plotted node")
            for path in unlinked_mission_files
        ],
    ]))
    map_paths = {pin["path"] for pin in map_related_files}

    unplaced_rows: list[dict] = []
    for digest in digests:
        unplaced_rows.extend(_unplaced_story_rows(
            digest["sceneUniverse"], digest["crossLevel"], level_id, language, pinned_files, map_paths
        ))
    seen_keys: set[str] = set()
    deduped = []
    for row in unplaced_rows:
        if row["key"] in seen_keys:
            continue
        seen_keys.add(row["key"])
        deduped.append(row)
    _annotate_unplaced_story_trigger_evidence(deduped, level_id)
    _annotate_unplaced_story_definition_evidence(deduped)

    story_keys = {key for node in [*markers, *quest_points] for key in node.get("sceneKeys") or []}
    for row in markers:
        row["storyCount"] = len(row.get("sceneKeys") or [])
        if not row.get("missions"):
            row.pop("missions", None)
        # Most nodes on a large map are registry scenery whose only evidence is
        # the level-wide registry row, so an empty list is dropped rather than
        # repeated 3,000 times. Readers already treat a missing list as empty.
        if not row.get("relatedFiles"):
            row.pop("relatedFiles", None)

    action_binding_counts = Counter(
        str(row.get("actionBindingStatus") or "")
        for row in markers
        if row.get("registryBacked")
        and str(row.get("identity") or "").startswith(("world:", "script:", "npc:"))
    )
    action_binding_slot_count = sum(action_binding_counts.values())

    minimap = _minimap_background(level_id)
    rendered_tiers = {str(row.get("id")): row for row in minimap.get("layers") or []}
    for layer in map_config.get("layers") or []:
        rendered = rendered_tiers.get(str(layer.get("id")))
        if rendered:
            for key in ("src", "status", "tileCount", "layer", "inverted"):
                if key in rendered:
                    layer[key] = rendered[key]

    facets = _facets(markers, quest_points, missions)
    digest_files = {
        digest["missionId"]: set(digest.get("fileRefs") or [])
        for digest in digests if digest.get("missionId")
    }
    mission_details: dict[str, dict] = {}
    for mission in sorted(missions):
        files = set(digest_files.get(mission) or [])
        runtime_asset = _mission_runtime_asset(mission)
        if runtime_asset:
            files.add(runtime_asset)
        for node in [*markers, *quest_points]:
            if mission not in (node.get("missions") or []):
                continue
            files.update(path for path in node.get("sourceFiles") or [] if path)
            files.update(pin.get("path") for pin in node.get("relatedFiles") or [] if pin.get("path"))
        mission_details[mission] = {
            **(facets["missions"].get(mission) or {"markers": 0, "questPoints": 0, "stories": 0}),
            "name": mission_names.get(mission, ""),
            "files": sorted(files),
        }

    return {
        "schemaVersion": 1,
        "id": level_id,
        "label": level_id,
        # The level id stays as the stable handle; the display name comes from
        # the level's own table rows and is absent when the game has no name.
        "name": names.get(level_id, ""),
        # The region key is deliberately separate from the display family:
        # it is the coordinate-space contract used to stitch sibling level
        # screens, not a translated UI label.
        "regionKey": _region_key(level_id),
        "facets": facets,
        "levelId": level_id,
        "idNum": id_num,
        "family": _level_family(level_id),
        "missions": sorted(missions),
        "defaultMission": next((
            row["missionId"] for row in MAINLINE_MAP_SCENES
            if row["levelId"] == level_id and row["missionId"] in missions
        ), ""),
        "missionDetails": mission_details,
        "coordinateSystem": "Unity world X/Y/Z; map projection uses X/Z with +Z upward",
        "questPoints": sorted(quest_points, key=lambda row: (str(row.get("missionId") or ""), str(row["questId"]))),
        "markers": sorted(markers, key=lambda row: (row["kind"], row["identity"])),
        "npcCoverage": {
            "exactProxyCount": len(entities.get("npc") or []),
            "boundary": (
                "NPC nodes are the exact `npcProxyBriefInfos` transforms this level owns. A level with no "
                "proxy rows is not proven to be visually empty of NPCs."
            ),
        },
        "actionBindingCoverage": {
            "slotCount": action_binding_slot_count,
            "statusCounts": {
                key: action_binding_counts[key]
                for key in sorted(action_binding_counts)
                if key
            },
            "boundary": (
                "Every authored spatial WorldEntityRegistry world/script slot has an observational status. "
                "no_reference_observed means only that the current decoded LevelScript evidence contains "
                "no matching constant EntityPtr; it does not prove that the slot has no action."
            ),
        },
        "renderBackground": _render_background(level_id),
        # The in-game map screen is the preferred background; `src` stays
        # null when the level's chunk grid or art is incomplete, and the
        # reader then falls back to the HLOD preview above.
        "mapConfig": map_config,
        "minimap": minimap,
        "scriptSources": {**{Path(path).stem: path for path in level_scripts}, **script_file_map},
        "relatedFiles": map_related_files,
        "unresolvedTriggerSlots": {
            "count": len(unresolved_rows),
            "stories": sorted({row["key"]: row for row in unresolved_rows}.values(), key=lambda row: row["key"]),
            "boundary": (
                "These stories are bound to a trigger volume by a level-script-local slot id that no "
                "WorldEntityRegistry entity carries. Their mission-area pins are scope context, not the "
                "recovered trigger position."
            ),
        },
        "unplacedStories": _unplaced_report(deduped),
        "unplacedActionTargets": {
            "count": len(unplaced_action_targets),
            "targets": sorted(
                unplaced_action_targets,
                key=lambda row: (
                    int(row.get("entityLogicId") or 0),
                    str(row.get("scriptId") or ""),
                    int(row.get("actionLocalId") or 0),
                ),
            ),
            "boundary": (
                "These actions contain a constant EntityPtr identity that does not resolve "
                "to one spatial WorldEntityRegistry world/script slot in this build. Exact "
                "formatter fields remain exact references; unresolved fields remain decoder diagnostics."
            ),
        },
        "actionEntityFieldDiagnostics": {
            "count": len(action_entity_field_diagnostics),
            "fields": action_entity_field_diagnostics,
            "boundary": (
                "These are serialized states for native-contracted EntityPtr fields. "
                "Only existing exact constant references participate in registry binding; "
                "dynamic, null, and opaque states are diagnostics and create no map placement."
            ),
        },
        "storyKeyCount": len(story_keys),
        "pinnedFileCount": len(pinned_files | map_paths),
        "missionFileReferences": sorted(file_refs),
        "linkedMissionFiles": marker_file_refs,
        "unlinkedMissionFiles": unlinked_mission_files,
        "sources": [REGISTRY_REL, LEVEL_BASIC_INFO_REL, MAP_ID_TABLE_REL, TELEPORT_TABLE_REL],
    }


def _scene_binding_pins_by_level(mission: dict, mission_id: str, language: str) -> dict[str, dict[str, list[dict]]]:
    """Scenes this mission's chains run in, as `levelId -> condition:<scriptId>`.

    A chain names the level-script file it runs in but never an entity slot, so
    the scene is pinned to that script as a whole. This is what places dialog in
    levels that host no mission of their own, such as the sub-levels missions
    teleport into. Bucketing by the chain's own level during the single mission
    pass keeps the whole-game build linear; asking each level to rescan every
    mission for its own chains would be quadratic.
    """
    index: dict[str, dict[str, list[dict]]] = {}
    for binding in ((mission.get("extras") or {}).get("sceneBindings") or {}).values():
        for chain in (binding or {}).get("chains") or []:
            level_id = str((chain or {}).get("levelId") or "")
            chain_file = chain.get("file") if isinstance(chain.get("file"), str) else None
            script_id = Path(chain_file).stem if chain_file else ""
            if not level_id or not script_id:
                continue
            for step in chain.get("steps") or []:
                for payload in (step or {}).get("payloads") or []:
                    key = str((payload or {}).get("sceneKey") or "")
                    conv_file = _conv_file_for_key(language, key)
                    if not key or not conv_file:
                        continue
                    rows = index.setdefault(level_id, {}).setdefault(f"condition:{script_id}", [])
                    if any(row["key"] == key for row in rows):
                        continue
                    rows.append({
                        "key": key,
                        "kind": (payload or {}).get("kind"),
                        "mission": mission_id,
                        "convFile": conv_file,
                        "sourceFiles": [chain_file],
                    })
    return index


def _reading_receivers_by_level(index: dict[str, list[dict]]) -> dict[str, dict[str, list[dict]]]:
    """Regroup reading-popup receivers as `levelId -> scriptId -> rows`.

    A row is indexed under the script that runs the popup action and under every
    script that serializes a producing entity for it, because those are two
    different identities and only the second one places the text on a slot. Rows
    that declare no level are filed under the `""` key, which every level merges
    in and then matches on the script id alone.
    """
    out: dict[str, dict[str, list[dict]]] = {}
    for key, rows in (index or {}).items():
        for row in rows:
            if not isinstance(row, dict):
                continue
            entry = {**row, "key": key}
            script_ids = {str(row.get("scriptId") or "")}
            script_ids.update(
                str(producer.get("scriptIdGlobal") or "")
                for producer in row.get("interactiveEventProducers") or []
                if isinstance(producer, dict)
            )
            bucket = out.setdefault(str(row.get("levelId") or ""), {})
            for script_id in script_ids:
                if script_id:
                    bucket.setdefault(script_id, []).append(entry)
    return out


# --------------------------------------------------------------------------
# Whole-game build
# --------------------------------------------------------------------------


MISSION_ID_RE = re.compile(r"^[A-Za-z0-9_]+$")


def _action_binding_report(payloads: Iterable[dict], language: str) -> dict:
    """Build the exhaustive, fail-closed action status for published slots.

    This deliberately derives from the same payloads written to the WebUI. It
    therefore inventories published registry-backed map slots and published
    unplaced action references without claiming that an absent constant
    pointer proves the runtime never targets the entity dynamically.
    """
    maps: list[dict] = []
    registry_status_counts: Counter[str] = Counter()
    all_status_counts: Counter[str] = Counter()
    missing_refs: list[dict] = []
    field_state_diagnostics: list[dict] = []
    field_state_counts: Counter[str] = Counter()
    dynamic_kind_counts: Counter[str] = Counter()
    dynamic_action_counts: Counter[str] = Counter()
    dynamic_field_counts: Counter[str] = Counter()
    dynamic_level_counts: Counter[str] = Counter()
    dynamic_source_counts: Counter[str] = Counter()
    spatially_resolved_dynamic_keys: set[tuple[str, int, int]] = set()

    def dynamic_reference_key(row: dict) -> tuple[str, int, int]:
        return (
            str(row.get("sourceFile") or ""),
            int(row.get("actionRecordOffset") or -1),
            int(row.get("pointerOffset") or -1),
        )

    def compact_action(action: dict) -> dict:
        return {
            key: value
            for key, value in {
                "status": action.get("status"),
                "name": action.get("name") or action.get("actionName"),
                "fieldName": action.get("fieldName"),
                "fieldNameStatus": action.get("fieldNameStatus"),
                "memberOrdinalZeroBased": action.get("memberOrdinalZeroBased"),
                "actionLocalId": action.get("actionLocalId"),
                "actionRecordOffset": action.get("actionRecordOffset"),
                "pointerOffset": action.get("pointerOffset"),
                "pointerEndOffset": action.get("pointerEndOffset"),
                "reasonCode": action.get("reasonCode"),
                "nativeFieldContractStatus": action.get("nativeFieldContractStatus"),
                "runtimeLifecycleStatus": action.get("runtimeLifecycleStatus"),
                "levelInteractiveAlignmentStatus": action.get("levelInteractiveAlignmentStatus"),
                "nativeScriptSlotMappingId": action.get("nativeScriptSlotMappingId"),
                "entityPtrGetterResolution": action.get(
                    "entityPtrGetterResolution"
                ),
                "entityPtrOutputAliasEvidence": action.get(
                    "entityPtrOutputAliasEvidence"
                ),
                "nativeGetterContractStatus": action.get(
                    "nativeGetterContractStatus"
                ),
                "npcProxyId": action.get("npcProxyId"),
                "targetDomain": action.get("targetDomain"),
                "entityLogicId": action.get("entityLogicId"),
                "entityPtrGetterResolution": action.get("entityPtrGetterResolution"),
                "nativeGetterContractStatus": action.get("nativeGetterContractStatus"),
                "spatialResolutionEvidence": action.get(
                    "spatialResolutionEvidence"
                ),
                "spatialResolutionDiagnostics": action.get(
                    "spatialResolutionDiagnostics"
                ),
                "placementSourceFiles": action.get("placementSourceFiles"),
                "storyKey": action.get("storyKey"),
                "storyPlaybackBinding": action.get("storyPlaybackBinding"),
                "sourceFile": action.get("sourceFile"),
            }.items()
            if value not in (None, "")
        }

    for payload in sorted(payloads, key=lambda row: str(row.get("id") or "")):
        slot_rows: list[dict] = []
        map_counts: Counter[str] = Counter()
        for field in (payload.get("actionEntityFieldDiagnostics") or {}).get("fields") or []:
            if not isinstance(field, dict):
                continue
            row = {"mapId": payload.get("id"), **field}
            field_state_diagnostics.append(row)
            state = str(field.get("state") or "opaque")
            field_state_counts[state] += 1
            if state == "dynamic":
                dynamic_kind_counts[str(field.get("dynamicKind") or "opaque_dynamic")] += 1
                dynamic_action_counts[str(field.get("actionName") or "unknown")] += 1
                dynamic_field_counts[
                    f"{field.get('actionName') or 'unknown'}.{field.get('fieldName') or 'unknown'}"
                ] += 1
                dynamic_level_counts[str(field.get("levelId") or payload.get("levelId") or "unknown")] += 1
                dynamic_source_counts[str(field.get("sourceFile") or "unknown")] += 1
        for marker_row in payload.get("markers") or []:
            identity = str(marker_row.get("identity") or "")
            if identity.startswith("world:"):
                domain = "world_logic_id"
            elif identity.startswith("script:"):
                domain = "registered_script_slot"
            elif identity.startswith("npc:"):
                domain = "npc_proxy_logic_id"
            else:
                continue
            for action in marker_row.get("actions") or []:
                if not isinstance(action, dict):
                    continue
                if (
                    action.get("entityPtrGetterResolution")
                    or action.get("entityPtrOutputAliasEvidence")
                ):
                    spatially_resolved_dynamic_keys.add(
                        dynamic_reference_key(action)
                    )
            exact_actions = [
                compact_action(action)
                for action in marker_row.get("actions") or []
                if isinstance(action, dict)
            ]
            unresolved_actions = [
                compact_action(action)
                for action in marker_row.get("unresolvedActionReferences") or []
                if isinstance(action, dict)
            ]
            actions = [*exact_actions, *unresolved_actions]
            unresolved_count = len(unresolved_actions)
            exact_count = len(exact_actions)
            if unresolved_count:
                status = (
                    "unresolved_registry_bridge"
                    if all(
                        action.get("reasonCode")
                        == "registered_slot_levelinteractive_alignment_missing"
                        for action in unresolved_actions
                    )
                    else "unresolved_serialized_member_layout"
                    if any(
                        action.get("reasonCode") == "serialized_member_layout_unresolved"
                        for action in unresolved_actions
                    )
                    else "unresolved_action_format"
                )
            elif exact_count:
                status = "exact_action_bound"
            else:
                status = "no_observed_action_reference"
            row = {
                "identity": identity,
                "domain": domain,
                "status": status,
                "registryResolutionStatus": "exact_unique_spatial",
                "exactActionCount": exact_count,
                "unresolvedActionCount": unresolved_count,
                "actions": actions,
            }
            slot_rows.append(row)
            registry_status_counts[status] += 1
            all_status_counts[status] += 1
            map_counts[status] += 1

            world_fallback_actions = [
                compact_action(action)
                for action in marker_row.get("worldFallbackActionTargets") or []
                if isinstance(action, dict)
            ]
            if world_fallback_actions:
                world_identity = f"world:{identity.split(':', 1)[1]}"
                fallback_row = {
                    "identity": world_identity,
                    "domain": "world_logic_id",
                    "status": "exact_action_bound",
                    "registryResolutionStatus": "exact_unique_spatial",
                    "exactActionCount": len(world_fallback_actions),
                    "unresolvedActionCount": 0,
                    "actions": world_fallback_actions,
                    "spatialAliasIdentity": identity,
                }
                slot_rows.append(fallback_row)
                registry_status_counts["exact_action_bound"] += 1
                all_status_counts["exact_action_bound"] += 1
                map_counts["exact_action_bound"] += 1

        unplaced_by_identity: dict[str, list[dict]] = {}
        for target in (payload.get("unplacedActionTargets") or {}).get("targets") or []:
            if not isinstance(target, dict):
                continue
            target_domain = str(target.get("targetDomain") or "")
            if target_domain.startswith("world_logic_id"):
                identity = f"world:{target.get('entityLogicId')}"
                domain = "world_logic_id"
            elif target_domain.startswith("registered_script_slot"):
                identity = f"script:{target.get('scriptId')}:{target.get('entitySlotId')}"
                domain = "registered_script_slot"
            elif target_domain == "npc_proxy_logic_id":
                identity = f"npc:{target.get('entityLogicId')}"
                domain = "npc_proxy_logic_id"
            else:
                identity = (
                    f"unresolved:{target.get('scriptId')}:{target.get('entitySlotId')}:"
                    f"{target.get('actionRecordOffset')}:{target.get('pointerOffset')}"
                )
                domain = target_domain or "unresolved"
            unplaced_by_identity.setdefault(identity, []).append({
                **compact_action(target),
                "targetDomain": target_domain or None,
                "entityLogicId": target.get("entityLogicId"),
                "entitySlotId": target.get("entitySlotId"),
                "scriptId": target.get("scriptId"),
            })
        for identity, actions in sorted(unplaced_by_identity.items()):
            domain = (
                "world_logic_id" if identity.startswith("world:") else
                "registered_script_slot" if identity.startswith("script:") else
                "npc_proxy_logic_id" if identity.startswith("npc:") else
                str(actions[0].get("targetDomain") or "unresolved")
            )
            unresolved_count = sum(
                not str(action.get("status") or "").startswith("exact_")
                for action in actions
            )
            row = {
                "identity": identity,
                "domain": domain,
                "status": "non_spatial",
                "registryResolutionStatus": "missing_or_unplaced",
                "exactActionCount": len(actions) - unresolved_count,
                "unresolvedActionCount": unresolved_count,
                "actions": actions,
            }
            slot_rows.append(row)
            missing_refs.append({"mapId": payload.get("id"), **row})
            all_status_counts["non_spatial"] += 1
            map_counts["non_spatial"] += 1

        maps.append({
            "mapId": payload.get("id"),
            "levelId": payload.get("levelId"),
            "registryBackedSlotCount": sum(
                row.get("registryResolutionStatus") == "exact_unique_spatial"
                for row in slot_rows
            ),
            "rowCount": len(slot_rows),
            "statusCounts": dict(sorted(map_counts.items())),
            "slots": sorted(slot_rows, key=lambda row: (row["domain"], row["identity"])),
        })

    dynamic_diagnostics = [
        row for row in field_state_diagnostics if row.get("state") == "dynamic"
    ]
    def dynamic_resolution_class(row: dict) -> str:
        if dynamic_reference_key(row) in spatially_resolved_dynamic_keys:
            return "exact_spatially_resolved"
        output_alias = row.get("localOutputAliasResolution") or {}
        named_entity = row.get("namedEntityPtrResolution") or {}
        getter = row.get("getterResolution") or {}
        getter_value = getter.get("resolvedValue") or {}
        if (
            (
                output_alias.get("status") in {
                    "validated_non_alias",
                    "runtime_list_element_non_spatial",
                    "validated_dynamic_filter_alias",
                }
                and output_alias.get("nativeMappingId")
                and row.get("nativeOutputAliasContractStatus") == "validated"
            )
            or (
                named_entity.get("status")
                == "validated_initial_entityptr_value_nonfinal"
                and named_entity.get("nativeMappingId")
                and row.get("nativePropertyInitializationContractStatus")
                == "validated"
                and named_entity.get("allowTargetPromotion") is False
            )
            or (
                getter.get("status") == "exact_constant_param_alias"
                and getter_value.get("logicId") == 0
                and getter_value.get("slotId") == 0
                and getter_value.get("useSlotId") is False
                and row.get("nativeGetterContractStatus") == "validated"
            )
        ):
            return "validated_runtime_non_spatial"
        return "unresolved"

    def dynamic_resolution_failure_gate(row: dict, resolution_class: str) -> str | None:
        if resolution_class == "exact_spatially_resolved":
            return None
        output_alias = row.get("localOutputAliasResolution") or {}
        named_entity = row.get("namedEntityPtrResolution") or {}
        getter = row.get("getterResolution") or {}
        if resolution_class == "validated_runtime_non_spatial":
            if (
                getter.get("status") == "exact_constant_param_alias"
                and (getter.get("resolvedValue") or {}).get("logicId") == 0
                and (getter.get("resolvedValue") or {}).get("slotId") == 0
                and (getter.get("resolvedValue") or {}).get("useSlotId") is False
            ):
                return "validated_null_entityptr_value"
            return str(
                output_alias.get("failureGate")
                or named_entity.get("failureGate")
                or "native_validated_runtime_non_spatial"
            )
        dynamic_kind = str(row.get("dynamicKind") or "opaque_dynamic")
        if dynamic_kind == "getter_id_ref":
            getter_status = str(getter.get("status") or "")
            return (
                "exact_getter_value_not_spatially_placed"
                if getter_status.startswith("exact_")
                else getter_status or "getter_resolution_unavailable"
            )
        if dynamic_kind == "local_output_ref":
            return str(
                output_alias.get("failureGate")
                or (
                    "exact_output_alias_not_spatially_placed"
                    if output_alias.get("status") == "exact_constant_filter_alias"
                    else "local_output_resolution_unavailable"
                )
            )
        if dynamic_kind == "named_script_variable":
            return str(
                named_entity.get("failureGate")
                or "named_script_property_initial_value_unavailable"
            )
        if dynamic_kind == "named_action_argument":
            return "runtime_named_action_argument"
        if dynamic_kind == "unnamed_script_variable":
            return "unnamed_script_property"
        return "opaque_dynamic_form"

    classified_dynamic_diagnostics = [
        {
            **row,
            "dynamicResolutionClass": resolution_class,
            "dynamicResolutionFailureGate": dynamic_resolution_failure_gate(
                row, resolution_class
            ),
        }
        for row in dynamic_diagnostics
        for resolution_class in (dynamic_resolution_class(row),)
    ]
    exact_spatial_dynamic_count = sum(
        row["dynamicResolutionClass"] == "exact_spatially_resolved"
        for row in classified_dynamic_diagnostics
    )
    validated_non_spatial_count = sum(
        row["dynamicResolutionClass"] == "validated_runtime_non_spatial"
        for row in classified_dynamic_diagnostics
    )
    unresolved_dynamic_count = (
        len(classified_dynamic_diagnostics)
        - exact_spatial_dynamic_count
        - validated_non_spatial_count
    )
    dynamic_resolution_failure_counts = Counter(
        str(row.get("dynamicResolutionFailureGate"))
        for row in classified_dynamic_diagnostics
        if row.get("dynamicResolutionFailureGate")
    )
    unplaced_dynamic_diagnostics = [
        row for row in classified_dynamic_diagnostics
        if row["dynamicResolutionClass"] != "exact_spatially_resolved"
    ]

    return {
        "schema": "mapActionBindingIndex.v1",
        "language": language,
        "summary": {
            "mapCount": len(maps),
            "registryBackedSlotCount": sum(registry_status_counts.values()),
            "missingOrUnplacedIdentityCount": len(missing_refs),
            "missingOrUnplacedReferenceCount": sum(
                len(row.get("actions") or []) for row in missing_refs
            ),
            "registrySlotStatusCounts": dict(sorted(registry_status_counts.items())),
            "allRowStatusCounts": dict(sorted(all_status_counts.items())),
            "domainCounts": dict(sorted(Counter(
                row["domain"] for map_row in maps for row in map_row["slots"]
            ).items())),
            "entityPtrFieldStateCounts": dict(sorted(field_state_counts.items())),
        },
        "dynamicReferenceSummary": {
            "count": field_state_counts.get("dynamic", 0),
            "resolvedDynamicReferenceCount": exact_spatial_dynamic_count,
            "exactSpatiallyResolvedDynamicReferenceCount": exact_spatial_dynamic_count,
            "validatedRuntimeNonSpatialReferenceCount": validated_non_spatial_count,
            "unresolvedDynamicReferenceCount": unresolved_dynamic_count,
            "resolutionFailureGateCounts": dict(
                sorted(dynamic_resolution_failure_counts.items())
            ),
            "kindCounts": dict(sorted(dynamic_kind_counts.items())),
            "actionCounts": dict(sorted(dynamic_action_counts.items())),
            "actionFieldCounts": dict(sorted(dynamic_field_counts.items())),
            "levelCounts": dict(sorted(dynamic_level_counts.items())),
            "sourceCounts": dict(sorted(dynamic_source_counts.items())),
            "boundary": (
                "Dynamic EntityPtr values retain their exact serialized idRef, paramSource, path, "
                "source/action/field identity, and offsets when decoded. The count inventories serialized "
                "dynamic forms; build-validated getter or producer-output contracts may resolve a subset "
                "to exact placed identities. Native contracts may separately prove runtime-only, "
                "non-spatial outputs. unplacedDynamicReferences retains both those explicitly labeled "
                "runtime values and the unresolved remainder."
            ),
        },
        "evidenceBoundary": (
            "Statuses describe constant EntityPtr evidence published by the current map builder. "
            "All 78 observed EntityPtr action shapes have build-locked field contracts; two "
            "additional byte-collision shapes are explicitly negative. no_observed_action_reference "
            "still does not prove that no dynamic or opaque runtime value can target the slot; "
            "non_spatial records are references, not "
            "fabricated map placements."
        ),
        "maps": maps,
        "missingOrUnplacedReferences": missing_refs,
        "unplacedDynamicReferences": unplaced_dynamic_diagnostics,
        "entityPtrFieldDiagnostics": field_state_diagnostics,
    }


def _write_action_binding_report(payloads: Iterable[dict], language: str) -> None:
    report = _action_binding_report(payloads, language)
    ACTION_BINDING_REPORT.parent.mkdir(parents=True, exist_ok=True)
    ACTION_BINDING_REPORT.write_text(
        json.dumps(report, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def build_all(language: str, only: set[str] | None = None) -> list[dict]:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    catalog: dict[str, int | None] = _level_catalog()
    exact_story_trigger_levels = _exact_story_trigger_level_ids()
    for trigger_level_id in exact_story_trigger_levels:
        catalog.setdefault(trigger_level_id, None)
    names = _level_names(language)
    entities_by_level = _registry_by_level(registry, catalog)
    teleports = _teleports_by_level()
    reading_by_level = _reading_receivers_by_level(_reading_receiver_index(language))

    mission_root = ROOT / f"webui/data/lang/{language}/mission"
    digests_by_level: dict[str, list[dict]] = {}
    bindings_by_level: dict[str, dict[str, list[dict]]] = {}
    if mission_root.is_dir():
        for path in sorted(mission_root.glob("*.json")):
            mission_id = path.stem
            if not MISSION_ID_RE.match(mission_id):
                continue
            mission = _load_json(path)
            if not isinstance(mission, dict):
                continue
            for level_id in _mission_levels(mission) & catalog.keys():
                if only and level_id not in only:
                    continue
                digests_by_level.setdefault(level_id, []).append(
                    _mission_digest(mission_id, mission, language, level_id, registry)
                )
            # A chain can name a level the mission never declares, which is the
            # only story evidence some sub-levels have, so bindings are
            # collected independently of the mission's own level set.
            for level_id, rows in _scene_binding_pins_by_level(mission, mission_id, language).items():
                if level_id not in catalog or (only and level_id not in only):
                    continue
                bucket = bindings_by_level.setdefault(level_id, {})
                for script_key, stories in rows.items():
                    known = {row["key"] for row in bucket.setdefault(script_key, [])}
                    bucket[script_key].extend(row for row in stories if row["key"] not in known)
            del mission

    payloads: list[dict] = []
    for level_id, id_num in sorted(catalog.items()):
        if only and level_id not in only:
            continue
        entities = entities_by_level.get(level_id, {"world": [], "script": [], "npc": []})
        digests = digests_by_level.get(level_id, [])
        level_teleports = teleports.get(level_id, [])
        if not any((
            entities["world"], entities["script"], entities["npc"], digests,
            level_teleports, level_id in exact_story_trigger_levels,
        )):
            continue
        # Chains that run inside a level are the only story evidence some
        # sub-levels have, and they come from the mission that teleports in.
        bindings = bindings_by_level.get(level_id) or {}
        if bindings:
            digests = [*digests, {
                # A synthetic digest carries only chain-derived story pins; the
                # missions it came from are already listed by their own digests.
                "missionId": "",
                "storyIndex": {},
                "attachmentIndex": bindings,
                "markers": [],
                "questPoints": [],
                "scriptFileMap": {},
                "fileRefs": set(),
                "sceneUniverse": {},
                "crossLevel": {},
                "unresolvedTriggerSlots": {"count": 0, "stories": []},
                "runtimeAsset": None,
            }]
        payload = build_level(
            level_id, id_num, language, registry, entities, digests, level_teleports, reading_by_level, names
        )
        if not payload["markers"] and not payload["questPoints"]:
            continue
        payloads.append(payload)

    return payloads


def _expand_index_variants(entries: Iterable[dict]) -> list[dict]:
    """Return physical level rows from either the old or grouped index shape."""
    expanded = []
    for row in entries:
        variants = row.get("variants") or []
        if variants:
            expanded.extend(dict(variant) for variant in variants)
        else:
            expanded.append(dict(row))
    return expanded


def _collapse_index_variants(entries: Iterable[dict]) -> list[dict]:
    """Group alternate payloads under one map without discarding task data."""
    remaining = {str(row["id"]): dict(row) for row in entries}
    collapsed = []
    for canonical_id, variant_ids in MAP_VARIANT_GROUPS.items():
        variants = [remaining.pop(level_id) for level_id in variant_ids if level_id in remaining]
        if not variants:
            continue
        canonical = next((row for row in variants if row["id"] == canonical_id), variants[0])
        mission_names = {}
        for variant in variants:
            mission_names.update(variant.get("missionNames") or {})
        missions = sorted({mission for variant in variants for mission in variant.get("missions") or []})
        grouped = dict(canonical)
        grouped.update({
            "missions": missions,
            "missionNames": {mission: mission_names.get(mission, "") for mission in missions},
            "markerCount": sum(int(row.get("markerCount") or 0) for row in variants),
            "questPointCount": sum(int(row.get("questPointCount") or 0) for row in variants),
            "storyKeyCount": sum(int(row.get("storyKeyCount") or 0) for row in variants),
            "missionCount": len(missions),
            "variants": variants,
        })
        collapsed.append(grouped)
    collapsed.extend(remaining.values())
    return collapsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", default="CN")
    parser.add_argument("--level", action="append", default=[], help="build only these level ids (repeatable)")
    args = parser.parse_args()
    language = args.language.upper()

    payloads = build_all(language, set(args.level) if args.level else None)
    maps = OUT / "maps"
    maps.mkdir(parents=True, exist_ok=True)
    existing_index = _load_json(OUT / "index.json", {}) if args.level else {}
    if not args.level:
        for stale in maps.glob("*.json"):
            stale.unlink()

    entries = []
    for payload in payloads:
        name = f"{payload['id']}.json"
        (maps / name).write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        entries.append({
            "id": payload["id"],
            "label": payload["label"],
            "name": payload.get("name", ""),
            "missions": payload.get("missions", []),
            "missionNames": {
                mission_id: str((payload.get("missionDetails", {}).get(mission_id) or {}).get("name") or "")
                for mission_id in payload.get("missions", [])
            },
            "levelId": payload["levelId"],
            "family": payload["family"],
            "regionKey": payload.get("regionKey") or _region_key(payload["levelId"]),
            "src": f"maps/{name}",
            "markerCount": len(payload["markers"]),
            "questPointCount": len(payload["questPoints"]),
            "storyKeyCount": payload["storyKeyCount"],
            "missionCount": len(payload["missions"]),
        })

    if not args.level:
        _write_action_binding_report(payloads, language)

    # Open on the first recovered mainline scene.  Before mainline scene
    # recovery began this used the richest level, but changing generated counts
    # could then move the entry point away from the authored progression.
    # A level dropped from the catalog leaves behind the map-screen composite
    # the previous build made. A focused --level run must not touch the
    # composites of the levels it did not rebuild, so this only runs for full
    # builds.
    render_root = OUT / "render"
    if not args.level and render_root.is_dir():
        catalog_ids = {str(level_id) for level_id in _level_catalog()}
        for stale in [*render_root.glob("*_minimap.png"), *render_root.glob("*_minimap.sources.json")]:
            if stale.name.split("_minimap", 1)[0] not in catalog_ids:
                stale.unlink()

    if args.level:
        replaced = {row["id"] for row in entries}
        entries = [
            row for row in _expand_index_variants(existing_index.get("maps") or [])
            if row.get("id") not in replaced
        ] + entries
    entries = _collapse_index_variants(entries)
    entry_ids = {row["id"] for row in entries}
    default_map = str(existing_index.get("defaultMap") or "") if args.level else ""
    default_map = next((
        canonical_id for canonical_id, variant_ids in MAP_VARIANT_GROUPS.items()
        if default_map in variant_ids
    ), default_map)
    if default_map not in entry_ids:
        default_map = next((
            row["levelId"] for row in MAINLINE_MAP_SCENES
            if row["levelId"] in entry_ids
        ), max(entries, key=lambda row: (row["storyKeyCount"], row["markerCount"]))["id"] if entries else "")
    index = {
        "schemaVersion": 3,
        "defaultMap": default_map,
        "language": language,
        "maps": sorted(entries, key=lambda row: (
            0 if row["regionKey"] == "base01" else
            1 if row["regionKey"] == "map01" else
            2 if row["regionKey"] == "map02" else 3,
            row["family"], row["id"],
        )),
    }
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(
        f"map recovery: {len(entries)} levels, "
        f"{sum(row['markerCount'] for row in entries)} markers, "
        f"{sum(row['questPointCount'] for row in entries)} quest points, "
        f"{sum(row['storyKeyCount'] for row in entries)} pinned story keys"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

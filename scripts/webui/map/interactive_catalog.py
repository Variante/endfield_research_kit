"""Map presentation of Interactive identities, without claiming live usability.

Template and facility-name joins use exact exported keys. The small taxonomy
describes identifier families only: it does not decode behaviour or upgrade a
name to an observed consumer. Binary framing belongs to game_data.
"""
from __future__ import annotations

from collections import defaultdict
from functools import lru_cache
import json
from pathlib import Path

from scripts.game_data.interactive_binary import (
    InteractiveBinaryDecodeError, decode_interactive_table,
)


# subKind, Chinese, English, glyph, complete identifier stems. A stem must end
# at an underscore boundary; e.g. int_fac does not match int_factory_gas.
FAMILIES = (
    ("power_supply", "供电设施", "Power supply", "power", ("int_fac_power_diffuser", "int_fac_power_terminal", "int_fac_power_station", "int_epowersupply")),
    ("power_pole", "输电设施", "Power transmission", "power", ("int_fac_power_pole", "int_fac_power_port")),
    ("protocol_core", "协议核心与支点", "Protocol cores & outposts", "hub", ("int_fac_sp_hub", "int_fac_sp_sub_hub", "int_base_core")),
    ("logistics", "物流设施", "Logistics", "box", ("int_fac_udpipe",)),
    ("gas_core", "气体核心", "Gas cores", "hub", ("int_factory_gas_core",)),
    ("gas_device", "气体装置", "Gas devices", "water", ("int_factory_gas",)),
    ("travel_pole", "滑索架", "Zipline pylons", "travel", ("int_simple_travel_pole", "int_fac_travel_pole")),
    ("combat_support", "战斗支援设施", "Combat support", "combat", ("int_fac_battle_medic", "int_fac_battle_fog", "int_fac_battle_debuff")),
    ("combat_tower", "防御装置", "Defense devices", "combat", ("int_fac_battle", "int_xirang_battleturret")),
    ("pressure_plate", "压力板", "Pressure plates", "plate", ("int_super_pressure_board",)),
    ("energy_lock", "能量锁", "Energy locks", "lock", ("int_aether_energy_lock", "int_aether_energy_locked_collection", "int_aether_energy_locked_empty")),
    ("electric_switch", "电力开关", "Electrical switches", "power", ("int_switch_attack_electric", "int_switch_electric")),
    ("water_switch", "水力开关", "Water switches", "water", ("int_switch_waterstate", "int_switch_waterdrone", "int_water_volume_switch")),
    ("attack_switch", "攻击开关", "Hit switches", "switch", ("int_switch_attack",)),
    ("repair_switch", "可修复开关", "Repairable switches", "repair", ("int_switch_fixable",)),
    ("lock_switch", "锁定开关", "Lock switches", "lock", ("int_switch_lock",)),
    ("switch", "通用开关", "Switches", "switch", ("int_switch", "int_trigger_button")),
    ("laser", "激光装置", "Laser devices", "laser", ("int_laser", "int_uav_laser")),
    ("repair_robot", "可修复机器人", "Repairable robots", "repair", ("int_fixable_robot",)),
    ("repair_device", "可修复装置", "Repairable devices", "repair", ("int_fixable_props", "int_fix_empty", "int_fix_map01_lv001_destroyed_door")),
    ("purifier", "净化装置", "Purifiers", "purify", ("int_purification_device",)),
    ("electric_fence", "电力屏障", "Electric barriers", "barrier", ("int_electric_fence",)),
    ("steam_blocker", "蒸汽障碍", "Steam barriers", "barrier", ("int_steam_blocker",)),
    ("fire_barrier", "火焰障碍", "Fire barriers", "barrier", ("int_fire_wall",)),
    ("door", "门与闸门", "Doors & gates", "door", ("int_door", "int_challenge_door", "int_dung02_stone_new_door", "int_system_spaceship_room_door")),
    ("bomb_device", "爆炸装置", "Explosive devices", "combat", ("int_interact_bomb_spawner", "int_explosive_drone", "int_activity_oil_container_bomb")),
    ("water_device", "水量机关", "Water mechanisms", "water", ("int_water_volume_floater", "int_water_volume_transferer", "int_water_hydrant", "int_xiranite_hydrant", "int_waterwheel", "int_water_gun_drive_ball", "int_waterdrone_cooler_unit")),
    ("crane_control", "起重机控制装置", "Crane controls", "switch", ("int_gantry_terminal", "int_003craneGoodsTerminal", "gantry_terminal1", "gantry_terminal2", "gantry_terminal3")),
    ("scan_trace", "扫描线索", "Scannable traces", "scan", ("int_scannable_trace", "int_hidden_mark")),
    ("camera_point", "拍照点", "Photo points", "camera", ("int_system_snapshot", "int_snapshot_empty")),
    ("guide_butterfly", "引导蝶", "Guide butterflies", "guide", ("int_leader_butterfly", "int_small_butterfly")),
    ("guide_drone", "引导无人机", "Guide drones", "guide", ("int_drone_guidelight",)),
    ("challenge_point", "挑战装置", "Challenge devices", "flag", ("int_challenge_start_point", "int_rune_checkpoint", "int_checkpoint")),
    ("rune_device", "符文机关", "Rune devices", "scan", ("int_rune_column", "int_weekraid_rune")),
    ("spot_difference", "找不同机关", "Spot-the-difference devices", "scan", ("int_spot_difference_main_stake", "int_spot_difference_sub_stake")),
    ("reading_terminal", "阅读终端", "Reading terminals", "terminal", ("int_terminal_reading",)),
    ("control_terminal", "控制终端", "Control terminals", "terminal", ("int_system_cabin_console", "int_warning_terminal", "int_spacestation_center_controller", "int_system_spaceship_guest_terminal")),
    ("shop", "商店与售货机", "Shops & vending machines", "shop", ("int_system_domain_shop", "int_vending_machine", "int_system_spaceship_credit_shop")),
    ("depot", "地区仓库", "Regional depots", "box", ("int_system_domain_depot",)),
    ("dungeon_entry", "副本入口", "Dungeon entrances", "door", ("int_system_dungeon_entry", "int_system_week_raid_entry", "int_system_racing_dungeon_battle_entry", "int_dungeon_spot")),
    ("mission_beacon", "任务信标", "Mission beacons", "flag", ("int_mission_beacon", "int_signal_tower")),
    ("erosion_core", "侵蚀核心", "Erosion cores", "purify", ("int_erosion_core", "int_erosion_sludge_core")),
    ("fog_nest", "雾巢", "Fog nests", "purify", ("int_fog_nest", "int_fognest_bossfightonly")),
)


def classify(detail_id: str) -> dict:
    """Return presentation metadata only for a bounded identifier family."""
    # Keep the builder's already evidenced cannon classification intact.
    if detail_id == "int_fac_battle_cannon" or detail_id.startswith("int_fac_battle_cannon_"):
        return {"subKind": "grenade_tower", "labels": {"zh": "榴弹塔", "en": "Mortar cannons"}, "icon": "combat"}
    for sub_kind, zh, en, icon, stems in FAMILIES:
        if any(detail_id == stem or detail_id.startswith(stem + "_") for stem in stems):
            return {"subKind": sub_kind, "labels": {"zh": zh, "en": en}, "icon": icon}
    return {}


def _read_object(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"object expected: {path.name}")
    return data


@lru_cache(maxsize=4)
def load_catalog(export_root: Path) -> tuple[dict, dict]:
    """Fail closed on a changed table; names require an unambiguous wrapper."""
    table_path = "game/Json/Interactive/InteractiveTable.json"
    audit = {"status": "unavailable", "source": table_path}
    try:
        table = decode_interactive_table((export_root / table_path).read_bytes())
    except (OSError, InteractiveBinaryDecodeError) as exc:
        audit["diagnostic"] = str(exc)[:400]
        return {}, audit
    sources = {"table": table_path}
    wrappers: dict[str, list[str]] = defaultdict(list)
    buildings, texts = {}, {}
    try:
        wrapper_path = "game/Table/InteractiveFacWrapperTable.json"
        building_path = "game/Table/FactoryBuildingTable.json"
        for key, value in _read_object(export_root / wrapper_path).items():
            if isinstance(value, dict) and isinstance(value.get("interactiveTemplateId"), str):
                wrappers[value["interactiveTemplateId"]].append(key)
        buildings = _read_object(export_root / building_path)
        for language in ("CN", "EN"):
            try:
                texts[language] = _read_object(export_root / f"game/Table/I18nTextTable_{language}.json")
            except (OSError, ValueError):
                texts[language] = {}
        sources.update(wrapper=wrapper_path, building=building_path)
        sources.update({lang: f"game/Table/I18nTextTable_{lang}.json"
                        for lang, values in texts.items() if values})
    except (OSError, ValueError) as exc:
        audit["nameDiagnostic"] = str(exc)[:400]
    result = {}
    for detail, template in table["objectToTemplate"].items():
        category = classify(detail) or classify(template)
        # Variants such as *_inert_core retain their authored core template;
        # do not let a broad gas-device stem erase that more specific identity.
        if category.get("subKind") == "gas_device" and classify(template).get("subKind") == "gas_core":
            category = classify(template)
        row = {"templateId": template, "templatePath": table["coreTemplatePaths"][template],
               "templateEvidence": "exact"}
        if category:
            row.update(category, classificationEvidence="structuralOnly",
                       classificationId=detail if category == classify(detail) else template)
        matches = wrappers.get(template, [])
        if len(matches) == 1 and isinstance(buildings.get(matches[0]), dict):
            building = buildings[matches[0]]
            ref = building.get("name") or {}
            ref = ref if isinstance(ref, dict) else {}
            names = {ui: texts.get(lang, {}).get(str(ref.get("id")), "")
                     for ui, lang in (("zh", "CN"), ("en", "EN"))}
            names = {key: value for key, value in names.items() if isinstance(value, str) and value.strip()}
            if names:
                row.update(names=names, nameEvidence="exact", buildingId=matches[0])
        result[detail] = row
    audit.update(status="decoded", objectCount=len(result), sources=sources)
    return result, audit


def enrich_markers(markers: list[dict], catalog: dict, language: str) -> None:
    """Add identity evidence without changing positions, missions or stories."""
    for marker in markers:
        # Only registry placements carry the Interactive detailId identity;
        # Story/quest labels and synthetic map annotations have separate owners.
        if not marker.get("registryBacked"):
            continue
        entry = catalog.get(str(marker.get("detailId") or ""))
        if not entry:
            continue
        marker["interactive"] = entry
        if marker.get("kind") not in {"device", "travel", "scenery"}:
            continue
        if entry.get("subKind"):
            marker["subKind"] = entry["subKind"]
            marker["kind"] = "travel" if entry["subKind"] == "travel_pole" else "device"
            marker["label"] = entry["labels"]["zh" if language.upper() == "CN" else "en"]
        name = entry.get("names", {}).get("zh" if language.upper() == "CN" else "en")
        if name:
            marker["label"] = name

"""Build compact authored factory/economy data for the static WebUI.

Examples:
    python scripts/build_economy_data.py
    python scripts/build_economy_data.py --languages CN EN JP
    python scripts/build_economy_data.py --summary-json reports/assets/economy_build_summary.json

The output describes static table configuration. It intentionally does not
calculate live throughput, unlock availability, shop rotation state, or player
inventory/account state.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import EXPORT_ROOT, LANG_DIR, rel_path, write_json


TABLE_SOURCE_RELS = (
    ("StreamingAssets", Path("structured") / "StreamingAssets" / "Table"),
    ("Persistent", Path("structured") / "Persistent" / "Table"),
)

RECIPE_TABLES = (
    ("machine", "FactoryMachineCraftTable.json"),
    ("hub", "FactoryHubCraftTable.json"),
    ("manual", "FactoryManualCraftTable.json"),
)

MACHINE_CAPABILITY_TABLES: dict[str, tuple[str, ...]] = {
    "FactoryMachineCrafterTable.json": ("modeMap", "modeUnlockDefaultMap"),
    "FactoryMinerTable.json": ("hasDroneMode", "minePosition", "mineable", "msPerRound", "msTransferCD"),
    "FactoryPowerStationTable.json": ("msPerRound", "powerProvide"),
    "FactoryPowerPoleTable.json": ("autoConnect", "autoConnectLength", "defaultCanBeWireStart", "defaultEnableDiffuser", "rangeExtend"),
    "FactorySpecialPowerPoleTable.json": ("autoConnect", "autoConnectLength", "defaultCanBeWireStart", "defaultEnableDiffuser", "rangeExtend"),
    "FactoryStoragerTable.json": ("capacity", "msTransferCD"),
    "FactoryFluidContainerTable.json": ("capacity",),
    "FactoryFluidConsumeTable.json": ("liquidable", "msPerRound"),
    "FactoryFluidPumpInTable.json": ("liquidable", "msPerRound", "volume"),
    "FactoryFluidPumpOutTable.json": ("liquidable", "msPerRound", "volume"),
    "FactoryFluidReactionTable.json": (),
    "FactorySewageTreatImportTable.json": ("liquidable", "msPerRound"),
    "FactorySewageTreatExportTable.json": ("liquidable", "countCost", "countProduce", "productItemId"),
    "FactoryHubTable.json": ("powerGenerate", "powerStorageCapacity"),
}

LOGISTICS_TABLES = (
    ("belt", "FactoryGridBeltTable.json"),
    ("connector", "FactoryGridConnecterTable.json"),
    ("router", "FactoryGridRouterTable.json"),
    ("bus", "FactoryBusStructureTable.json"),
    ("freeBus", "FactoryFreeBusTable.json"),
    ("liquidPipe", "FactoryLiquidPipeTable.json"),
    ("liquidConnector", "FactoryLiquidConnectorTable.json"),
    ("liquidRouter", "FactoryLiquidRouterTable.json"),
    ("undergroundPipe", "FactoryUndergroundPipeTable.json"),
)

SOURCE_TABLES = tuple(dict.fromkeys([
    "I18nTextTable_{language}.json",
    "ItemTable.json",
    "FactoryItemTable.json",
    "FactoryBuildingTable.json",
    "FactoryBuildingItemTable.json",
    "FactoryResourceItemId2MachineIdTable.json",
    "FactoryItem2LogisticIdTable.json",
    "FactoryFuelItemTable.json",
    "FactoryBatteryItemTable.json",
    "LiquidTable.json",
    "FactoryFluidConsumeItemTable.json",
    "FactorySewageTreatPlantStoreTable.json",
    "FacSTTGroupTable.json",
    "FacSTTCategoryTable.json",
    "FacSTTLayerTable.json",
    "FacSTTNodeTable.json",
    "MachineId2MachineTechIdTable.json",
    "FactorySpecialCraftTable.json",
    "RewardTable.json",
    "ShopGroupTable.json",
    "ShopTable.json",
    "ShopGoodsTable.json",
    "ActivityTable.json",
    "ActivityLevelRewardsTable.json",
    *[name for _kind, name in RECIPE_TABLES],
    *MACHINE_CAPABILITY_TABLES,
    *[name for _kind, name in LOGISTICS_TABLES],
]))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build compact WebUI economy data from authored Endfield tables.",
        epilog=("Outputs data/lang/<LANG>/economy/index.json. Values are static authored "
                "configuration, not live throughput, availability, or account state."),
    )
    parser.add_argument("--languages", nargs="+", default=["CN"], help="Language codes to build; default: CN.")
    parser.add_argument("--default-language", default="CN", help="Fallback language; default: CN.")
    parser.add_argument("--export-root", type=Path, default=EXPORT_ROOT, help="Export root containing structured table roots.")
    parser.add_argument("--out-dir", type=Path, default=LANG_DIR, help="WebUI language output root.")
    parser.add_argument("--summary-json", type=Path, help="Optional path for a compact build summary JSON.")
    return parser.parse_args(argv)


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return default


def table_roots(export_root: Path) -> list[tuple[str, Path]]:
    return [(label, export_root / rel) for label, rel in TABLE_SOURCE_RELS if (export_root / rel).is_dir()]


def merge_payload(base: Any, overlay: Any) -> Any:
    if isinstance(base, dict) and isinstance(overlay, dict):
        result = dict(base)
        result.update(overlay)
        return result
    if isinstance(base, list) and isinstance(overlay, list):
        return [*base, *overlay]
    return overlay


def load_table(roots: list[tuple[str, Path]], name: str, default: Any = None) -> Any:
    result: Any = None
    found = False
    for _label, root in roots:
        payload = read_json(root / name, None)
        if payload is None:
            continue
        result = payload if not found else merge_payload(result, payload)
        found = True
    if found:
        return result
    if isinstance(default, dict):
        return dict(default)
    if isinstance(default, list):
        return list(default)
    return default


def clean_id(value: Any) -> str:
    return "" if value in (None, "") else str(value)


def localized_text(i18n: dict[str, Any], node: Any, fallback: dict[str, Any]) -> str:
    if isinstance(node, str):
        return node.strip()
    if isinstance(node, (int, float)):
        key = str(int(node))
        return str(i18n.get(key) or fallback.get(key) or "").strip()
    if not isinstance(node, dict):
        return ""
    if node.get("text"):
        return str(node["text"]).strip()
    key = clean_id(node.get("id"))
    return str(i18n.get(key) or fallback.get(key) or "").strip() if key and key != "0" else ""


def first_text(i18n: dict[str, Any], fallback: dict[str, Any], *nodes: Any) -> str:
    for node in nodes:
        value = localized_text(i18n, node, fallback)
        if value:
            return value
    return ""


def sorted_rows(table: Any) -> Iterable[tuple[str, dict[str, Any]]]:
    if not isinstance(table, dict):
        return []
    return ((str(key), value) for key, value in sorted(table.items(), key=lambda item: str(item[0])) if isinstance(value, dict))


def copy_fields(row: dict[str, Any], fields: Iterable[str]) -> dict[str, Any]:
    return {field: row[field] for field in fields if field in row and row[field] not in (None, "", [], {})}


def bundle_rows(value: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    if not isinstance(value, list):
        return result
    for row in value:
        if not isinstance(row, dict):
            continue
        item_id = clean_id(row.get("id") or row.get("itemId"))
        if item_id:
            result.append({"itemId": item_id, "count": row.get("count", row.get("itemCount", 0))})
    return result


def recipe_groups(value: Any) -> list[list[dict[str, Any]]]:
    """Preserve authored alternatives: outer rows are slots, inner rows choices."""
    result: list[list[dict[str, Any]]] = []
    if not isinstance(value, list):
        return result
    for slot in value:
        choices = slot.get("group") if isinstance(slot, dict) and isinstance(slot.get("group"), list) else [slot]
        parsed = bundle_rows(choices)
        if parsed:
            result.append(parsed)
    return result


def item_ids_from_groups(groups: list[list[dict[str, Any]]]) -> set[str]:
    return {row["itemId"] for group in groups for row in group if row.get("itemId")}


def reward_payload(reward_id: str, rewards: dict[str, Any]) -> dict[str, Any]:
    row = rewards.get(reward_id) if reward_id else None
    if not isinstance(row, dict):
        return {"id": reward_id, "items": []} if reward_id else {}
    items = bundle_rows(row.get("itemBundles"))
    probable = bundle_rows(row.get("probItemBundles"))
    payload: dict[str, Any] = {"id": reward_id, "items": items}
    if probable:
        payload["probableItems"] = probable
    return payload


def build_recipes(tables: dict[str, Any], i18n: dict[str, Any], fallback: dict[str, Any]) -> tuple[list[dict[str, Any]], set[str]]:
    recipes: list[dict[str, Any]] = []
    item_ids: set[str] = set()
    for kind, table_name in RECIPE_TABLES:
        for key, row in sorted_rows(tables.get(table_name)):
            recipe_id = clean_id(row.get("id") or key)
            inputs = recipe_groups(row.get("ingredients"))
            outputs = recipe_groups(row.get("outcomes"))
            item_ids.update(item_ids_from_groups(inputs))
            item_ids.update(item_ids_from_groups(outputs))
            payload: dict[str, Any] = {
                "id": recipe_id,
                "kind": kind,
                "name": first_text(i18n, fallback, row.get("name"), row.get("formulaDesc")) or recipe_id,
                "inputs": inputs,
                "outputs": outputs,
                "source": {"table": table_name, "id": key},
            }
            payload.update(copy_fields(row, (
                "machineId", "formulaGroupId", "domainId", "itemId", "belongingGroupIds",
                "defaultUnlock", "rarity", "showingType", "sortId", "progressRound", "totalProgress", "signal", "usableLevel",
            )))
            recipes.append(payload)
    recipes.sort(key=lambda row: (row["kind"], row["id"]))
    return recipes, item_ids


def build_machines(tables: dict[str, Any], i18n: dict[str, Any], fallback: dict[str, Any]) -> tuple[list[dict[str, Any]], set[str]]:
    building_table = tables.get("FactoryBuildingTable.json") or {}
    building_items = tables.get("FactoryBuildingItemTable.json") or {}
    item_by_building = {
        clean_id(row.get("buildingId")): clean_id(row.get("itemId") or key)
        for key, row in sorted_rows(building_items)
        if clean_id(row.get("buildingId"))
    }
    machines: dict[str, dict[str, Any]] = {}
    item_ids: set[str] = set()
    for key, row in sorted_rows(building_table):
        machine_id = clean_id(row.get("id") or key)
        build_item = item_by_building.get(machine_id, "")
        if build_item:
            item_ids.add(build_item)
        machines[machine_id] = {
            "id": machine_id,
            "name": first_text(i18n, fallback, row.get("name")) or machine_id,
            "description": first_text(i18n, fallback, row.get("desc")),
            "buildItemId": build_item,
            "config": copy_fields(row, (
                "type", "needPower", "powerConsume", "bandwidth", "liquidEnabled", "range",
                "inputPorts", "outputPorts", "placeDomains", "recommendDomains", "iconOnPanel",
            )),
            "capabilities": [],
            "source": {"table": "FactoryBuildingTable.json", "id": key},
        }
    for table_name, fields in MACHINE_CAPABILITY_TABLES.items():
        for key, row in sorted_rows(tables.get(table_name)):
            machine_id = clean_id(row.get("id") or row.get("buildingId") or key)
            machine = machines.setdefault(machine_id, {
                "id": machine_id, "name": machine_id, "description": "", "buildItemId": item_by_building.get(machine_id, ""),
                "config": {}, "capabilities": [], "source": {"table": table_name, "id": key},
            })
            capability = {"kind": table_name.removeprefix("Factory").removesuffix("Table.json"), "sourceTable": table_name}
            capability.update(copy_fields(row, fields))
            machine["capabilities"].append(capability)
    resource_map = tables.get("FactoryResourceItemId2MachineIdTable.json") or {}
    for item_id, row in sorted_rows(resource_map):
        normalized_item = clean_id(row.get("itemId") or item_id)
        machine_ids = sorted({clean_id(value) for value in row.get("machineIds") or [] if clean_id(value)})
        if normalized_item:
            item_ids.add(normalized_item)
        for machine_id in machine_ids:
            machine = machines.get(machine_id)
            if machine is not None:
                machine.setdefault("resourceItemIds", []).append(normalized_item)
    for machine in machines.values():
        machine["capabilities"].sort(key=lambda row: row["kind"])
        if machine.get("resourceItemIds"):
            machine["resourceItemIds"] = sorted(set(machine["resourceItemIds"]))
    return sorted(machines.values(), key=lambda row: row["id"]), item_ids


def logistics_data(tables: dict[str, Any], i18n: dict[str, Any], fallback: dict[str, Any]) -> tuple[list[dict[str, Any]], set[str]]:
    entries: list[dict[str, Any]] = []
    item_ids: set[str] = set()
    for kind, table_name in LOGISTICS_TABLES:
        for key, row in sorted_rows(tables.get(table_name)):
            entry_id = clean_id(row.get("id") or key)
            unit = row.get("beltData") or row.get("gridUnitData") or row.get("liquidUnitData") or row.get("pipeData") or {}
            item_id = clean_id(unit.get("itemId") if isinstance(unit, dict) else "")
            if item_id:
                item_ids.add(item_id)
            entries.append({
                "id": entry_id,
                "kind": kind,
                "name": first_text(i18n, fallback, unit.get("name") if isinstance(unit, dict) else None) or entry_id,
                "itemId": item_id,
                "config": {
                    **copy_fields(unit if isinstance(unit, dict) else {}, ("msPerRound", "volume", "iconOnPanel")),
                    **copy_fields(row, ("range", "inputPorts", "outputPorts", "defaultRendererTemplate")),
                },
                "source": {"table": table_name, "id": key},
            })
    mapping = tables.get("FactoryItem2LogisticIdTable.json") or {}
    for key, row in sorted_rows(mapping):
        item_id = clean_id(row.get("itemId") or key)
        item_ids.add(item_id)
        entries.append({
            "id": clean_id(row.get("logisticId")) or key,
            "kind": "itemMapping",
            "name": clean_id(row.get("logisticId")) or key,
            "itemId": item_id,
            "config": copy_fields(row, ("type",)),
            "source": {"table": "FactoryItem2LogisticIdTable.json", "id": key},
        })
    entries.sort(key=lambda row: (row["kind"], row["id"], row.get("itemId", "")))
    return entries, item_ids


def build_technologies(tables: dict[str, Any], i18n: dict[str, Any], fallback: dict[str, Any]) -> tuple[dict[str, Any], set[str]]:
    item_ids: set[str] = set()
    groups = []
    for key, row in sorted_rows(tables.get("FacSTTGroupTable.json")):
        cost_item = clean_id(row.get("costPointType"))
        if cost_item:
            item_ids.add(cost_item)
        groups.append({
            "id": clean_id(row.get("groupId") or key),
            "name": first_text(i18n, fallback, row.get("groupName")) or key,
            "description": first_text(i18n, fallback, row.get("desc")),
            "domainId": clean_id(row.get("domainId")),
            "costItemId": cost_item,
            "categoryIds": sorted(clean_id(v) for v in row.get("categoryIds") or [] if clean_id(v)),
            "layerIds": sorted(clean_id(v) for v in row.get("layerIds") or [] if clean_id(v)),
            "source": {"table": "FacSTTGroupTable.json", "id": key},
        })
    categories = []
    for key, row in sorted_rows(tables.get("FacSTTCategoryTable.json")):
        categories.append({
            "id": clean_id(row.get("category") or key), "groupId": clean_id(row.get("groupId")),
            "name": first_text(i18n, fallback, row.get("name")) or key, "order": row.get("order"),
            "techIds": [clean_id(v) for v in row.get("techIds") or [] if clean_id(v)],
            "source": {"table": "FacSTTCategoryTable.json", "id": key},
        })
    layers = []
    for key, row in sorted_rows(tables.get("FacSTTLayerTable.json")):
        costs = [{"itemId": clean_id(v.get("costItemId")), "count": v.get("costItemCount", 0)} for v in row.get("costItems") or [] if isinstance(v, dict) and clean_id(v.get("costItemId"))]
        item_ids.update(v["itemId"] for v in costs)
        layers.append({
            "id": clean_id(row.get("layerId") or key), "groupId": clean_id(row.get("groupId")),
            "name": first_text(i18n, fallback, row.get("name")) or key,
            "description": first_text(i18n, fallback, row.get("desc")), "order": row.get("order"),
            "preLayerId": clean_id(row.get("preLayer")), "costs": costs,
            "techIds": [clean_id(v) for v in row.get("techIds") or [] if clean_id(v)],
            "source": {"table": "FacSTTLayerTable.json", "id": key},
        })
    machine_tech = {
        clean_id(machine_id): clean_id(row.get("techId"))
        for machine_id, row in sorted_rows(tables.get("MachineId2MachineTechIdTable.json"))
        if clean_id(row.get("techId"))
    }
    nodes = []
    for key, row in sorted_rows(tables.get("FacSTTNodeTable.json")):
        rewards = [{"itemId": clean_id(v.get("itemId")), "count": v.get("count", 0)} for v in row.get("unlockReward") or [] if isinstance(v, dict) and clean_id(v.get("itemId"))]
        costs = [{"itemId": clean_id(v.get("itemId") or v.get("costItemId")), "count": v.get("count", v.get("costItemCount", 0))} for v in row.get("costItems") or [] if isinstance(v, dict) and clean_id(v.get("itemId") or v.get("costItemId"))]
        item_ids.update(v["itemId"] for v in [*rewards, *costs])
        tech_id = clean_id(row.get("techId") or key)
        nodes.append({
            "id": tech_id, "name": first_text(i18n, fallback, row.get("name")) or tech_id,
            "description": first_text(i18n, fallback, row.get("desc")),
            "unlockDescription": first_text(i18n, fallback, row.get("unlockDesc")),
            "groupId": clean_id(row.get("groupId")), "categoryId": clean_id(row.get("category")),
            "layerId": clean_id(row.get("layer")), "preNodeIds": [clean_id(v) for v in row.get("preNode") or [] if clean_id(v)],
            "costPointCount": row.get("costPointCount"), "costs": costs, "rewards": rewards,
            "action": row.get("action") if isinstance(row.get("action"), dict) else {},
            "authoredAlreadyUnlock": row.get("alreadyUnlock"), "defaultHidden": row.get("defaultHidden"),
            "source": {"table": "FacSTTNodeTable.json", "id": key},
        })
    return {"groups": groups, "categories": categories, "layers": layers, "nodes": nodes, "machineTech": machine_tech}, item_ids


def build_resources(tables: dict[str, Any], i18n: dict[str, Any], fallback: dict[str, Any]) -> tuple[dict[str, Any], set[str]]:
    item_ids: set[str] = set()
    fuels = []
    for key, row in sorted_rows(tables.get("FactoryFuelItemTable.json")):
        item_id = clean_id(row.get("id") or key); item_ids.add(item_id)
        fuels.append({"itemId": item_id, **copy_fields(row, ("fuelEnergy", "powerProvide", "progressRound")), "source": {"table": "FactoryFuelItemTable.json", "id": key}})
    batteries = []
    for key, row in sorted_rows(tables.get("FactoryBatteryItemTable.json")):
        item_id = clean_id(row.get("id") or key); item_ids.add(item_id)
        batteries.append({"itemId": item_id, **copy_fields(row, ("BatteryEnergy", "batteryEnergy")), "source": {"table": "FactoryBatteryItemTable.json", "id": key}})
    liquids = []
    for key, row in sorted_rows(tables.get("LiquidTable.json")):
        item_id = clean_id(row.get("id") or key); item_ids.add(item_id)
        empty = sorted(clean_id(v) for v in row.get("emptyBottleItems") or [] if clean_id(v))
        full = sorted(clean_id(v) for v in row.get("fullBottleItems") or [] if clean_id(v))
        item_ids.update(empty); item_ids.update(full)
        liquids.append({"itemId": item_id, "emptyBottleItemIds": empty, "fullBottleItemIds": full, "source": {"table": "LiquidTable.json", "id": key}})
    power = []
    for table_name in ("FactoryPowerStationTable.json", "FactoryHubTable.json", "FactoryPowerPoleTable.json", "FactorySpecialPowerPoleTable.json"):
        for key, row in sorted_rows(tables.get(table_name)):
            power.append({
                "id": clean_id(row.get("id") or row.get("buildingId") or key),
                "config": copy_fields(row, ("msPerRound", "powerProvide", "powerGenerate", "powerStorageCapacity", "autoConnect", "autoConnectLength", "rangeExtend")),
                "source": {"table": table_name, "id": key},
            })
    mining = []
    for key, row in sorted_rows(tables.get("FactoryMinerTable.json")):
        mineable = []
        for authored in row.get("mineable") or []:
            if not isinstance(authored, dict):
                continue
            mining_item = clean_id(authored.get("miningItemId"))
            consume = authored.get("consumeItem") if isinstance(authored.get("consumeItem"), dict) else {}
            consume_item = clean_id(consume.get("id"))
            if mining_item: item_ids.add(mining_item)
            if consume_item: item_ids.add(consume_item)
            mineable.append({"itemId": mining_item, "produceRate": authored.get("produceRate"), "consumeItem": {"itemId": consume_item, "count": consume.get("count", 0)} if consume_item else {}})
        mining.append({"id": clean_id(row.get("id") or key), "mineable": mineable, "config": copy_fields(row, ("hasDroneMode", "minePosition", "msPerRound", "msTransferCD")), "source": {"table": "FactoryMinerTable.json", "id": key}})
    sewage = []
    for table_name in ("FactoryFluidConsumeItemTable.json", "FactorySewageTreatPlantStoreTable.json"):
        for key, row in sorted_rows(tables.get(table_name)):
            item_id = clean_id(row.get("itemId"))
            if item_id: item_ids.add(item_id)
            sewage.append({"id": clean_id(row.get("id") or key), "name": first_text(i18n, fallback, row.get("name")) or clean_id(row.get("id") or key), "itemId": item_id, "config": copy_fields(row, ("buildingIds", "domainId", "levelId", "levelList", "sortId")), "source": {"table": table_name, "id": key}})
    return {"power": power, "fuels": fuels, "batteries": batteries, "liquids": liquids, "mining": mining, "sewage": sewage}, item_ids


def build_shops_activities(tables: dict[str, Any], i18n: dict[str, Any], fallback: dict[str, Any]) -> tuple[dict[str, Any], set[str]]:
    item_ids: set[str] = set()
    rewards = tables.get("RewardTable.json") or {}
    shops = []
    for key, row in sorted_rows(tables.get("ShopTable.json")):
        shops.append({"id": clean_id(row.get("shopId") or key), "name": first_text(i18n, fallback, row.get("shopName"), row.get("shopEnName")) or key, "goodsIds": [clean_id(v) for v in row.get("shopGoodsIds") or [] if clean_id(v)], "source": {"table": "ShopTable.json", "id": key}})
    shop_groups = []
    for key, row in sorted_rows(tables.get("ShopGroupTable.json")):
        shop_groups.append({"id": clean_id(row.get("shopGroupId") or key), "name": first_text(i18n, fallback, row.get("shopGroupName")) or key, "type": row.get("shopGroupType"), "shopIds": [clean_id(v) for v in row.get("shopIds") or [] if clean_id(v)], "source": {"table": "ShopGroupTable.json", "id": key}})
    goods = []
    for key, row in sorted_rows(tables.get("ShopGoodsTable.json")):
        reward_id = clean_id(row.get("rewardId")); reward = reward_payload(reward_id, rewards)
        money_id = clean_id(row.get("moneyId"))
        if money_id: item_ids.add(money_id)
        item_ids.update(v["itemId"] for v in reward.get("items") or [])
        item_ids.update(v["itemId"] for v in reward.get("probableItems") or [])
        goods.append({
            "id": clean_id(row.get("goodsId") or key), "shopId": clean_id(row.get("shopId")),
            "moneyItemId": money_id, "price": row.get("price"), "discount": row.get("cnDiscount"),
            "limitCount": row.get("limitCount"), "limitRefreshType": row.get("limitCountRefreshType"),
            "reward": reward, "authoredVisibleWhenLocked": row.get("isShowWhenLock"),
            "source": {"table": "ShopGoodsTable.json", "id": key},
        })
    activities = []
    for key, row in sorted_rows(tables.get("ActivityTable.json")):
        reward_id = clean_id(row.get("rewardId")); reward = reward_payload(reward_id, rewards)
        item_ids.update(v["itemId"] for v in reward.get("items") or [])
        activities.append({
            "id": clean_id(row.get("id") or key), "name": first_text(i18n, fallback, row.get("name")) or key,
            "description": first_text(i18n, fallback, row.get("desc")), "type": row.get("type"),
            "timeId": clean_id(row.get("timeId")), "tagIds": [clean_id(v) for v in row.get("tagIds") or [] if clean_id(v)],
            "reward": reward, "source": {"table": "ActivityTable.json", "id": key},
        })
    milestones = []
    for key, row in sorted_rows(tables.get("ActivityLevelRewardsTable.json")):
        for stage in row.get("stageList") or []:
            if not isinstance(stage, dict): continue
            reward_id = clean_id(stage.get("rewardId")); reward = reward_payload(reward_id, rewards)
            item_ids.update(v["itemId"] for v in reward.get("items") or [])
            milestones.append({"activityId": clean_id(stage.get("activityId") or key), "stageId": stage.get("stageId"), "stageKey": clean_id(stage.get("stageStrId")), "reward": reward, "source": {"table": "ActivityLevelRewardsTable.json", "id": key}})
    return {"shopGroups": shop_groups, "shops": shops, "goods": goods, "activities": activities, "activityMilestones": milestones}, item_ids


def build_items(tables: dict[str, Any], ids: set[str], i18n: dict[str, Any], fallback: dict[str, Any]) -> list[dict[str, Any]]:
    items = tables.get("ItemTable.json") or {}
    factory_items = tables.get("FactoryItemTable.json") or {}
    result = []
    for item_id in sorted(value for value in ids if value):
        row = items.get(item_id) if isinstance(items.get(item_id), dict) else {}
        factory = factory_items.get(item_id) if isinstance(factory_items.get(item_id), dict) else {}
        result.append({
            "id": item_id, "name": first_text(i18n, fallback, row.get("name")) or item_id,
            "description": first_text(i18n, fallback, row.get("desc")), "rarity": row.get("rarity"),
            "type": row.get("type"), "showingType": row.get("showingType"), "iconId": clean_id(row.get("iconId")),
            "factory": copy_fields(factory, ("subType", "value", "buildingBufferStackLimit", "showInUnloader", "dischargeType", "showInHubDomainIds", "transferDomainIds")),
            "source": {"table": "ItemTable.json" if row else "FactoryItemTable.json", "id": item_id},
        })
    return result


def build_relations(
    recipes: list[dict[str, Any]],
    technologies: dict[str, Any],
    shop_activity: dict[str, Any],
    building_items: dict[str, Any],
) -> list[dict[str, Any]]:
    edges: set[tuple[str, str, str, str]] = set()
    def add(src: str, dst: str, kind: str, source: str) -> None:
        if src and dst and not src.endswith(":") and not dst.endswith(":"):
            edges.add((src, dst, kind, source))
    for recipe in recipes:
        rid = f"recipe:{recipe['id']}"
        for group in recipe.get("inputs") or []:
            for row in group: add(f"item:{row['itemId']}", rid, "ingredientFor", recipe["source"]["table"])
        for group in recipe.get("outputs") or []:
            for row in group: add(rid, f"item:{row['itemId']}", "produces", recipe["source"]["table"])
        add(rid, f"machine:{clean_id(recipe.get('machineId'))}", "authoredForMachine", recipe["source"]["table"])
    for building_item_id, tech_id in (technologies.get("machineTech") or {}).items():
        building_item = building_items.get(building_item_id) if isinstance(building_items.get(building_item_id), dict) else {}
        machine_id = clean_id(building_item.get("buildingId"))
        add(f"tech:{tech_id}", f"machine:{machine_id}", "unlocksMachine", "MachineId2MachineTechIdTable.json + FactoryBuildingItemTable.json")
    for node in technologies.get("nodes") or []:
        for pre in node.get("preNodeIds") or []: add(f"tech:{pre}", f"tech:{node['id']}", "precedes", "FacSTTNodeTable.json")
        for reward in node.get("rewards") or []: add(f"tech:{node['id']}", f"item:{reward['itemId']}", "authoredUnlockReward", "FacSTTNodeTable.json")
    for good in shop_activity.get("goods") or []:
        add(f"item:{good.get('moneyItemId','')}", f"shopGood:{good['id']}", "pricedWith", "ShopGoodsTable.json")
        for row in (good.get("reward") or {}).get("items") or []: add(f"shopGood:{good['id']}", f"item:{row['itemId']}", "grants", "RewardTable.json")
    for activity in shop_activity.get("activities") or []:
        for row in (activity.get("reward") or {}).get("items") or []: add(f"activity:{activity['id']}", f"item:{row['itemId']}", "grants", "RewardTable.json")
    return [{"from": src, "to": dst, "kind": kind, "sourceTable": source} for src, dst, kind, source in sorted(edges)]


def build_language(language: str, fallback_language: str, roots: list[tuple[str, Path]]) -> dict[str, Any]:
    fallback_i18n = load_table(roots, f"I18nTextTable_{fallback_language}.json", {}) or {}
    i18n = fallback_i18n if language == fallback_language else (load_table(roots, f"I18nTextTable_{language}.json", {}) or fallback_i18n)
    tables = {name: load_table(roots, name, {}) for name in SOURCE_TABLES if "{language}" not in name}
    recipes, recipe_items = build_recipes(tables, i18n, fallback_i18n)
    machines, machine_items = build_machines(tables, i18n, fallback_i18n)
    logistics, logistics_items = logistics_data(tables, i18n, fallback_i18n)
    technologies, technology_items = build_technologies(tables, i18n, fallback_i18n)
    resources, resource_items = build_resources(tables, i18n, fallback_i18n)
    shop_activity, commerce_items = build_shops_activities(tables, i18n, fallback_i18n)
    all_item_ids = set().union(recipe_items, machine_items, logistics_items, technology_items, resource_items, commerce_items)
    items = build_items(tables, all_item_ids, i18n, fallback_i18n)
    relations = build_relations(recipes, technologies, shop_activity, tables.get("FactoryBuildingItemTable.json") or {})
    counts = {
        "items": len(items), "recipes": len(recipes), "machines": len(machines), "technologies": len(technologies["nodes"]),
        "logistics": len(logistics), "power": len(resources["power"]), "fuels": len(resources["fuels"]), "batteries": len(resources["batteries"]),
        "liquids": len(resources["liquids"]), "mining": len(resources["mining"]), "sewage": len(resources["sewage"]), "shops": len(shop_activity["shops"]),
        "shopGoods": len(shop_activity["goods"]), "activities": len(shop_activity["activities"]), "relations": len(relations),
    }
    return {
        "language": language,
        "scopeNote": "Static authored configuration; no live throughput, availability, rotation, inventory, or account state is inferred.",
        "sourceRoots": [{"source": label, "root": rel_path(root)} for label, root in roots],
        "tables": sorted(name for name in tables if tables[name]), "counts": counts,
        "items": items, "recipes": recipes, "machines": machines, "technologies": technologies,
        "logistics": logistics, "resources": resources, **shop_activity, "relations": relations,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    roots = table_roots(args.export_root)
    if not roots:
        print(f"Missing structured table roots under {args.export_root}", file=sys.stderr)
        return 2
    default_language = str(args.default_language).strip().upper()
    summaries = []
    for raw_language in args.languages:
        language = str(raw_language).strip().upper()
        if not language: continue
        payload = build_language(language, default_language, roots)
        output = args.out_dir / language / "economy" / "index.json"
        changed = write_json(output, payload)
        summaries.append({"language": language, "path": rel_path(output), "changed": changed, "counts": payload["counts"]})
        counts = payload["counts"]
        print(f"{language}: wrote {rel_path(output)} ({counts['recipes']} recipes, {counts['machines']} machines, {counts['technologies']} technologies, {counts['items']} referenced items, {counts['relations']} relations)")
    summary = {"generated": int(time.time()), "sourceRoots": [rel_path(root) for _label, root in roots], "outputs": summaries}
    if args.summary_json:
        write_json(args.summary_json, summary, indent=2, compact=False, trailing_newline=True)
        print(f"Summary: {rel_path(args.summary_json)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

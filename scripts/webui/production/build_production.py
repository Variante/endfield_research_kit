"""Publish item sources, production recipes and exact reverse table references.

Run ``python -m scripts.webui.production.build_production --languages CN``.
Tables provide the catalog; already exported images provide optional icons.
No installed data, other page publication or native/runtime inference is
required. The page registry owns freshness checks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from scripts.common import require_export_layout, write_json
from scripts.repo_paths import REPO_ROOT
from scripts.source_paths import ExportLayout
from scripts.webui.production.icons import load_icons
from scripts.webui.production.limited_items import group_limited_items
from scripts.webui.production.medals import group_medals
from scripts.webui.production.recipes import group_recipes


SCHEMA = "endfield.production.v1"
TABLE_NAMES = (
    "ItemTable", "ItemTypeTable", "ItemShowingTypeTable", "FactoryItemTable",
    "FactoryMachineCraftTable", "FactoryMachineCraftGroupTable", "FactoryHubCraftTable",
    "FactoryManualCraftTable", "FactoryBuildingTable", "FactoryBuildingItemTable",
    "FactoryManualCraftUpgradeTable", "ShopGoodsTable", "ShopTable", "ShopGroupTable",
    "RewardTable", "WeaponBasicTable", "WeaponBreakThroughTemplateTable",
    "WeaponExpItemTable", "EquipEnhanceCostTable", "WikiGroupTable", "WikiEntryDataTable",
    "AchievementTable", "AchievementTypeTable", "LTItemTable", "UserAvatarTable",
    "FullBottleTable", "FullGasJarTable", "FactoryEnvDisplayTable",
    "ActivityLimitedFormulaTable", "LimitedFormulaCraftIdReverseTable",
)
BOUNDARY = (
    "Stored table configuration and exact identifier joins. Recipe groups retain their "
    "stored boundaries. Configured machine time is progressRound * msPerRound / 1000 "
    "seconds, as displayed by FactoryUtils.getCraftNeedTime; it does not establish "
    "effective rates or runtime unlocks. Shop itemBundles are configured rewards; random bundles and "
    "conditions are not resolved into guaranteed or currently available items. Upgrade "
    "coverage is limited to the named source tables, not all possible item uses."
)


def localized(value: Any, texts: dict[str, Any]) -> str:
    if isinstance(value, dict):
        translated = texts.get(str(value.get("id", "")))
        if isinstance(translated, dict):
            translated = translated.get("text", "")
        return str(translated or value.get("text") or "")
    return str(value or "")


def source(table: str, key: str, field: str = "") -> dict[str, str]:
    return {"table": table, "row": str(key), "field": field}


def _positive(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def build_catalog(tables: dict[str, dict[str, Any]], texts: dict[str, Any]) -> dict[str, Any]:
    """Build exact joins without filesystem access (also the bounded fixture seam)."""
    items: dict[str, dict[str, Any]] = {}
    recipes: dict[str, dict[str, Any]] = {}
    machines: dict[str, dict[str, Any]] = {}
    unresolved: list[dict[str, str]] = []

    def table(name: str) -> dict[str, Any]:
        return tables.get(name, {})

    # Several internal item types share a displayed category. Give that union
    # one stable representative while retaining each item's original type.
    type_groups: dict[str, str] = {}
    for key, row in sorted(table("ItemTypeTable").items()):
        type_groups.setdefault(localized(row.get("name"), texts) or key, key)

    building_categories = {
        group["groupId"]: {"id": group["groupId"],
                           "title": localized(group.get("groupName"), texts) or group["groupId"],
                           "iconId": group.get("iconId", "")}
        for group in table("WikiGroupTable").get("wiki_type_building", {}).get("list", [])
    }
    wiki_by_item: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    for key, row in table("WikiEntryDataTable").items():
        if row.get("refItemId") and row.get("groupId") in building_categories:
            wiki_by_item[str(row["refItemId"])].append((key, row))

    avatars = {str(row["itemId"]): (key, row) for key, row in table("UserAvatarTable").items()
               if row.get("itemId") and row.get("icon")}

    def item_icon(key: str, row: dict[str, Any]) -> dict[str, str]:
        icon = {"iconId": row.get("iconId", "")}
        if key in avatars:
            icon["iconId"] = str(avatars[key][1]["icon"]).rsplit("/", 1)[-1]
        for name, field in (("FullBottleTable", "liquidId"), ("FullGasJarTable", "gasId")):
            container = table(name).get(key)
            if container and container.get(field) in table("ItemTable"):
                icon["contentIconId"] = table("ItemTable")[container[field]].get("iconId", "")
        return icon

    def item_ref(item_id: Any, count: Any = None) -> dict[str, Any]:
        key = str(item_id or "")
        row = table("ItemTable").get(key)
        result = {"id": key, "title": localized(row.get("name"), texts) or key if row else key,
                  "resolved": row is not None, **(item_icon(key, row) if row else {"iconId": ""})}
        if count is not None:
            result["count"] = count
        return result

    for key, row in table("ItemTable").items():
        type_row = table("ItemTypeTable").get(str(row.get("type")), {})
        showing_row = table("ItemShowingTypeTable").get(str(row.get("showingType")), {})
        factory = table("FactoryItemTable").get(key)
        type_name = localized(type_row.get("name"), texts) or str(row.get("type", ""))
        items[key] = {
            "id": key, "kind": "items", "title": localized(row.get("name"), texts) or key,
            "description": localized(row.get("desc"), texts),
            "lore": localized(row.get("decoDesc"), texts),
            "type": str(row.get("type", "")),
            "typeName": type_name, "typeGroup": type_groups.get(type_name, str(row.get("type", ""))),
            "showingType": row.get("showingType"),
            "showingTypeName": localized(showing_row.get("name"), texts),
            "rarity": row.get("rarity", 0), **item_icon(key, row),
            "stackLimit": row.get("maxStackCount"),
            "backpackStackLimit": row.get("maxBackpackStackCount"),
            "obtainWayIds": row.get("obtainWayIds", []),
            "outputReferences": [item_ref(value) for value in row.get("outcomeItemIds", [])],
            "factory": factory, "producedBy": [], "usedBy": [], "shops": [], "upgrades": [],
            "buildingIds": [], "buildingDimensions": [], "sources": [source("ItemTable", key)], "tags": [],
        }
        if factory is not None:
            items[key]["sources"].append(source("FactoryItemTable", key))
            items[key]["tags"].append("factory_item")
        if key in avatars:
            items[key]["sources"].append(source("UserAvatarTable", avatars[key][0], "itemId, icon"))
        for name in ("FullBottleTable", "FullGasJarTable"):
            if key in table(name):
                items[key]["sources"].append(source(name, key))

    def append_item(item_id: str, field: str, value: dict[str, Any], table_name: str, row_id: str) -> None:
        if item_id in items:
            items[item_id][field].append(value)
        else:
            unresolved.append({"table": table_name, "row": row_id, "target": str(item_id), "field": field})

    for key, row in table("FactoryBuildingTable").items():
        machines[key] = {
            "id": key, "kind": "machines", "title": localized(row.get("name"), texts) or key,
            "description": localized(row.get("desc"), texts), "type": str(row.get("type", "")),
            "rarity": 0, "needPower": row.get("needPower"), "powerConsume": row.get("powerConsume"),
            "inputPorts": row.get("inputPorts"), "outputPorts": row.get("outputPorts"),
            "range": row.get("range"), "placeDomains": row.get("placeDomains", []),
            "recommendDomains": row.get("recommendDomains", []), "items": [], "recipes": [],
            "categories": [], "iconId": "",
            "rendererTemplateMap": row.get("rendererTemplateMap", {}), "tags": [],
            "sources": [source("FactoryBuildingTable", key)],
        }
    for key, row in table("FactoryBuildingItemTable").items():
        building_id, item_id = str(row.get("buildingId", "")), str(row.get("itemId", ""))
        if building_id in machines:
            machine = machines[building_id]
            ref = item_ref(item_id)
            machine["items"].append(ref)
            machine["iconId"] = machine["iconId"] or ref["iconId"]
            machine["sources"].append(source("FactoryBuildingItemTable", key))
            for wiki_key, entry in wiki_by_item.get(item_id, []):
                category = building_categories[entry["groupId"]]
                if category not in machine["categories"]:
                    machine["categories"].append(category)
                machine["sources"].extend([
                    source("WikiEntryDataTable", wiki_key, "refItemId, groupId"),
                    source("WikiGroupTable", "wiki_type_building", "list"),
                ])
        if item_id in items:
            items[item_id]["buildingIds"].append(building_id)
            items[item_id]["sources"].append(source("FactoryBuildingItemTable", key))
            if building_id in machines:
                machine = machines[building_id]
                items[item_id]["buildingDimensions"].append({
                    "id": building_id, "title": machine["title"],
                    **{field: value for field, value in (machine["range"] or {}).items()
                       if field in {"depth", "height", "width"}},
                })
                items[item_id]["sources"].append(source("FactoryBuildingTable", building_id, "range"))

    for recipe_type, table_name in (
        ("machine", "FactoryMachineCraftTable"), ("hub", "FactoryHubCraftTable"),
        ("manual", "FactoryManualCraftTable"),
    ):
        for key, row in table(table_name).items():
            recipe_id = f"{recipe_type}:{key}"
            groups: dict[str, list[list[dict[str, Any]]]] = {}
            for field in ("ingredients", "outcomes"):
                raw = row.get(field, [])
                # A machine group can contain several simultaneous outputs. Keep
                # the stored nesting rather than interpreting it as alternatives.
                raw_groups = [group.get("group", []) for group in raw] if recipe_type == "machine" else [raw]
                groups[field] = [[item_ref(entry.get("id"), entry.get("count")) for entry in group]
                                 for group in raw_groups]
            outcome_titles = [entry["title"] for group in groups["outcomes"] for entry in group]
            title = localized(row.get("name"), texts) or " + ".join(outcome_titles) or key
            machine_id = str(row.get("machineId", ""))
            group_id = str(row.get("formulaGroupId", ""))
            craft_group = table("FactoryMachineCraftGroupTable").get(group_id)
            recipe = {
                "id": recipe_id, "sourceId": key, "kind": "recipes", "type": recipe_type,
                "title": title, "description": localized(row.get("formulaDesc"), texts),
                "rarity": row.get("rarity", 0), **groups, "machineId": machine_id,
                "machineResolved": machine_id in machines,
                "machineName": machines.get(machine_id, {}).get("title", machine_id),
                "formulaGroupId": group_id, "formulaItem": item_ref(row["itemId"]) if row.get("itemId") else None,
                "conditions": {field: row[field] for field in (
                    "defaultUnlock", "domainId", "belongingGroupIds", "usableLevel", "gasEnv", "signal",
                ) if field in row},
                "timing": {field: row[field] for field in ("progressRound", "totalProgress") if field in row},
                "configuration": {field: row[field] for field in (
                    "formulaGroupId", "buffers", "sortId", "craftFilterType", "rarity", "showingType",
                ) if field in row},
                "sources": [source(table_name, key)], "tags": [recipe_type],
            }
            if craft_group is not None:
                recipe["timing"]["msPerRound"] = craft_group.get("msPerRound")
                recipe["sources"].append(source("FactoryMachineCraftGroupTable", group_id))
                rounds, ms = row.get("progressRound"), craft_group.get("msPerRound")
                if recipe_type == "machine" and _positive(rounds) and _positive(ms):
                    recipe["durationSeconds"] = rounds * ms / 1000
            gas_env = recipe["conditions"].get("gasEnv")
            if gas_env:
                env = table("FactoryEnvDisplayTable").get(str(gas_env), {})
                recipe["gasEnvironment"] = {"id": gas_env, "iconId": env.get("EnvIconAtlas", "")}
                if env:
                    recipe["sources"].append(source("FactoryEnvDisplayTable", str(gas_env)))
            activity_id = table("LimitedFormulaCraftIdReverseTable").get(key)
            if isinstance(activity_id, str) and activity_id:
                activity = table("ActivityLimitedFormulaTable").get(activity_id, {})
                recipe["activityId"] = activity_id
                recipe["tags"].append("activity_only")
                recipe["sources"].append(source("LimitedFormulaCraftIdReverseTable", key))
                if key in activity.get("timeLimitFormula", []):
                    recipe["sources"].append(source("ActivityLimitedFormulaTable", activity_id, "timeLimitFormula"))
            if machine_id:
                if machine_id in machines:
                    machines[machine_id]["recipes"].append({field: recipe[field] for field in (
                        "id", "title", "type", "ingredients", "outcomes", "durationSeconds", "gasEnvironment", "activityId",
                    ) if field in recipe})
                else:
                    unresolved.append({"table": table_name, "row": key, "field": "machineId", "target": machine_id})
            recipes[recipe_id] = recipe
            for field, target in (("ingredients", "usedBy"), ("outcomes", "producedBy")):
                for group_index, group in enumerate(groups[field]):
                    for entry in group:
                        if not _positive(entry.get("count")):
                            continue
                        append_item(entry["id"], target, {
                            "id": recipe_id, "title": title, "type": recipe_type,
                            "count": entry["count"], "group": group_index,
                            "machineId": machine_id, "machineName": recipe["machineName"],
                            **({"gasEnvironment": recipe["gasEnvironment"]} if "gasEnvironment" in recipe else {}),
                            **({"activityId": recipe["activityId"]} if "activityId" in recipe else {}),
                        }, table_name, key)
            if row.get("itemId"):
                append_item(str(row["itemId"]), "upgrades", {
                    "type": "recipe_formula", "targetId": recipe_id, "targetKind": "recipes", "title": title,
                    **({"gasEnvironment": recipe["gasEnvironment"]} if "gasEnvironment" in recipe else {}),
                    "sources": [source(table_name, key, "itemId")],
                }, table_name, key)

    # Classify every positive output, including co-products. Broad item types,
    # displayed item categories and the building encyclopedia provide filters;
    # the crafting method remains a separate dimension.
    output_categories = {}
    for row in items.values():
        candidates = []
        for building_id in row["buildingIds"]:
            candidates.extend(machines.get(building_id, {}).get("categories", []))
        showing = table("ItemShowingTypeTable").get(str(row["showingType"]), {})
        if row["showingTypeName"]:
            candidates.append({"id": f"showing:{row['showingType']}", "title": row["showingTypeName"],
                               "iconId": showing.get("icon", "")})
        if row["type"] in table("ItemTypeTable") and row["typeName"]:
            candidates.append({"id": f"item-type:{row['typeGroup']}", "title": row["typeName"], "iconId": ""})
        output_categories[row["id"]] = candidates
    # Identical localized labels have one chip even across the two type tables.
    category_by_title = {}
    for category in sorted((entry for rows in output_categories.values() for entry in rows), key=lambda entry: entry["id"]):
        category_by_title.setdefault(category["title"], category)
    for recipe in recipes.values():
        selected = {}
        for group in recipe["outcomes"]:
            for output in group:
                if _positive(output.get("count")):
                    for category in output_categories.get(output["id"], []):
                        canonical = category_by_title[category["title"]]
                        selected[canonical["id"]] = canonical
        recipe["categories"] = list(selected.values())

    shop_listing_count = 0
    random_shop_count = 0
    for key, goods in table("ShopGoodsTable").items():
        reward_id, shop_id = str(goods.get("rewardId", "")), str(goods.get("shopId", ""))
        reward = table("RewardTable").get(reward_id)
        shop = table("ShopTable").get(shop_id, {})
        group_id = str(shop.get("shopGroupId", ""))
        shop_group = table("ShopGroupTable").get(group_id, {})
        if reward is None:
            unresolved.append({"table": "ShopGoodsTable", "row": key, "field": "rewardId", "target": reward_id})
            continue
        random = bool(reward.get("probItemBundles"))
        random_shop_count += int(random)
        bundles = [item_ref(entry.get("id"), entry.get("count")) for entry in reward.get("itemBundles", [])
                   if _positive(entry.get("count"))]
        listing = {
            "id": key, "shopId": shop_id, "shopName": localized(shop.get("shopName"), texts) or shop_id,
            "shopGroupName": localized(shop_group.get("shopGroupName"), texts) or group_id,
            "rewardId": reward_id, "currency": item_ref(goods.get("moneyId")), "price": goods.get("price"),
            "cnDiscount": goods.get("cnDiscount"), "limitCount": goods.get("limitCount"),
            "limitCountRefreshType": goods.get("limitCountRefreshType"),
            "shopRefreshType": shop.get("shopRefreshType"),
            "shopRefreshCycleType": shop.get("shopRefreshCycleType"),
            "conditions": {"goods": goods.get("unlockConditions", []), "shop": shop.get("unlockConditions", []),
                           "group": shop_group.get("unlockConditions", [])},
            "lockDescription": localized(goods.get("lockDesc"), texts),
            "hasRandomRewards": random, "items": bundles,
            "sources": [source("ShopGoodsTable", key), source("RewardTable", reward_id)]
                + ([source("ShopTable", shop_id)] if shop else [])
                + ([source("ShopGroupTable", group_id)] if shop_group else []),
        }
        for bundle in bundles:
            append_item(bundle["id"], "shops", {**listing, "count": bundle["count"]}, "ShopGoodsTable", key)
            shop_listing_count += 1
        currency_id = str(goods.get("moneyId", ""))
        if currency_id and _positive(goods.get("price")):
            append_item(currency_id, "upgrades", {
                "type": "shop_currency", "title": listing["shopName"], "count": goods["price"],
                "goodsId": key, "items": bundles, "hasRandomRewards": random,
                "sources": listing["sources"],
            }, "ShopGoodsTable", key)

    for weapon_id, weapon in table("WeaponBasicTable").items():
        template_id = str(weapon.get("breakthroughTemplateId", ""))
        template = table("WeaponBreakThroughTemplateTable").get(template_id)
        if template is None:
            if template_id:
                unresolved.append({"table": "WeaponBasicTable", "row": weapon_id, "field": "breakthroughTemplateId", "target": template_id})
            continue
        for step in template.get("list", []):
            for bundle in step.get("breakItemList", []):
                if not _positive(bundle.get("count")):
                    continue
                append_item(str(bundle.get("id", "")), "upgrades", {
                    "type": "weapon_breakthrough", "targetId": weapon_id, "targetKind": "items",
                    "title": item_ref(weapon_id)["title"], "count": bundle["count"],
                    "level": step.get("breakthroughLv"), "displayLevel": step.get("breakthroughShowLv"),
                    "sources": [source("WeaponBasicTable", weapon_id, "breakthroughTemplateId"),
                                source("WeaponBreakThroughTemplateTable", template_id, "breakItemList")],
                }, "WeaponBreakThroughTemplateTable", template_id)
    for key, row in table("WeaponExpItemTable").items():
        if row.get("expItemId"):
            append_item(str(row["expItemId"]), "upgrades", {
                "type": "weapon_experience", "title": "", "itemExp": row.get("itemExp"),
                "weaponExp": row.get("weaponExp"), "weaponExpConvertRatio": row.get("weaponExpConvertRatio"),
                "sources": [source("WeaponExpItemTable", key)],
            }, "WeaponExpItemTable", key)
    for key, row in table("EquipEnhanceCostTable").items():
        if _positive(row.get("consumeItemCnt")):
            append_item(str(row.get("consumeItemId", "")), "upgrades", {
                "type": "equipment_enhance", "title": str(row.get("domainId", key)),
                "count": row["consumeItemCnt"], "sources": [source("EquipEnhanceCostTable", key)],
            }, "EquipEnhanceCostTable", key)
    for key, row in table("FactoryManualCraftUpgradeTable").items():
        target_id = str(row.get("levelUpItemId", ""))
        append_item(str(row.get("itemId", "")), "upgrades", {
            "type": "manual_upgrade_mapping", "targetId": target_id, "targetKind": "items",
            "title": item_ref(target_id)["title"], "sources": [source("FactoryManualCraftUpgradeTable", key)],
        }, "FactoryManualCraftUpgradeTable", key)

    for row in items.values():
        for field, tag in (("producedBy", "craftable"), ("usedBy", "ingredient"), ("shops", "shop_reward"),
                           ("upgrades", "other_uses"), ("buildingIds", "building_item")):
            if row[field]:
                row["tags"].append(tag)
        if not row["producedBy"] and not row["shops"]:
            row["tags"].append("no_source_link")
    for row in machines.values():
        row["tags"] = (["has_recipes"] if row["recipes"] else []) + (["needs_power"] if row["needPower"] else [])
    item_count = len(items)
    aliases = group_limited_items(items, tables)
    aliases.update(group_medals(items, tables, lambda value: localized(value, texts)))
    source_recipe_count = len(recipes)
    recipe_types = dict(Counter(row["type"] for row in recipes.values()))
    recipe_aliases = group_recipes(recipes)
    return {
        "records": {"items": items, "recipes": recipes, "machines": machines},
        "itemAliases": aliases,
        "recipeAliases": recipe_aliases,
        "machineCategories": list(building_categories.values()),
        "stats": {"items": len(items), "recipes": len(recipes), "machines": len(machines),
                  "sourceItems": item_count, "medalGroups": sum("medalLevels" in row for row in items.values()),
                  "sourceRecipes": source_recipe_count, "recipeTypes": recipe_types,
                  "craftableItems": sum(bool(row["producedBy"]) for row in items.values()),
                  "shopItemLinks": shop_listing_count, "shopsWithRandomRewards": random_shop_count,
                  "upgradeUseLinks": sum(len(row["upgrades"]) for row in items.values()),
                  "unresolvedReferences": len(unresolved)},
        "unresolvedReferences": unresolved,
    }


def read_table(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = path.read_bytes()  # Missing or malformed inputs must not publish an empty catalog.
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError(f"Production table must be an object: {path}")
    return payload, {"file": path.name, "sha256": hashlib.sha256(raw).hexdigest(), "rows": len(payload)}


def publish(catalog: dict[str, Any], language: str, out_dir: Path, inputs: list[dict[str, Any]]) -> dict[str, Any]:
    index: dict[str, Any] = {
        "schema": SCHEMA, "language": language, "evidenceBoundary": BOUNDARY,
        "stats": catalog["stats"], "inputs": inputs, "items": [], "recipes": [], "machines": [],
        "unresolvedReferences": catalog["unresolvedReferences"],
        "icons": catalog.get("icons", {}), "iconStatus": catalog.get("iconStatus", {}),
        "itemAliases": catalog.get("itemAliases", {}),
        "recipeAliases": catalog.get("recipeAliases", {}),
        "machineCategories": catalog.get("machineCategories", []),
    }
    for kind, records in catalog["records"].items():
        shards: dict[str, dict[str, Any]] = defaultdict(dict)
        for key, row in sorted(records.items()):
            bucket = hashlib.sha256(key.encode("utf-8")).hexdigest()[0]
            shard = f"{kind}/{bucket}.json"
            shards[shard][key] = row
            fields = ("id", "kind", "title", "type", "typeName", "typeGroup", "showingTypeName",
                      "rarity", "tags", "sources", "iconId", "contentIconId", "categories", "aliases")
            summary = {field: row[field] for field in fields if field in row}
            summary["detail"] = shard
            summary["description"] = row.get("description", "")
            if kind == "items":
                summary["counts"] = {field: len(row[field]) for field in ("producedBy", "usedBy", "shops", "upgrades")}
                if row.get("medalLevels"):
                    summary["medalLevelCount"] = len({str(tier["level"]) for tier in row["medalLevels"]})
                    summary["medalIcons"] = [
                        {"iconId": tier["item"].get("iconId", ""),
                         "level": tier["level"], "plated": tier["plated"]}
                        for tier in row["medalLevels"]
                    ]
            elif kind == "recipes":
                summary.update({field: row[field] for field in ("ingredients", "outcomes", "machineId", "machineName")})
                summary.update({field: row[field] for field in ("types", "machineNames", "machineIds", "durationSeconds")
                                if field in row})
                summary["variantCount"] = len(row.get("recipeVariants", [])) or 1
            else:
                summary["recipeCount"] = len(row["recipes"])
            index[kind].append(summary)
        for shard, rows in sorted(shards.items()):
            write_json(out_dir / shard, {"schema": SCHEMA, "language": language, "records": rows})
    # Publish the index after every referenced shard has been written.
    write_json(out_dir / "index.json", index)
    return index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-root", type=Path, default=ExportLayout.configured().root)
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "webui" / "data")
    parser.add_argument("--languages", nargs="+", default=["CN"])
    parser.add_argument("--default-language", default="CN")
    args = parser.parse_args(argv)
    languages = list(dict.fromkeys(language.upper() for language in args.languages))
    default_language = args.default_language.upper()
    if default_language not in languages:
        parser.error("--default-language must be included in --languages")
    if any(not language.isalpha() or len(language) > 8 for language in languages):
        parser.error("language codes must contain 1–8 letters")
    require_export_layout(args.export_root)
    layout = ExportLayout(args.export_root)
    tables, inputs = {}, []
    for name in TABLE_NAMES:
        tables[name], receipt = read_table(layout.table_dir / f"{name}.json")
        inputs.append(receipt)
    localizations = {language: read_table(layout.table_dir / f"I18nTextTable_{language}.json") for language in languages}
    icon_ids = {str(row.get("iconId") or "") for row in tables["ItemTable"].values()}
    icon_ids.update(str(row.get("iconId") or "") for row in
                    tables["WikiGroupTable"].get("wiki_type_building", {}).get("list", []))
    icon_ids.update(str(row.get("icon") or "") for row in tables["ItemShowingTypeTable"].values())
    # Presentation icons for the named gas environments, independent of the
    # effect-atlas tokens stored by FactoryEnvDisplayTable.
    icon_ids.update({"icon_gas_env_stable", "icon_gas_env_humidity",
                     "icon_gas_env_acid", "icon_gas_env_xiranite"})
    square_icon_ids = {str(row["icon"]).rsplit("/", 1)[-1] for row in tables["UserAvatarTable"].values()
                       if str(row.get("itemId", "")).startswith("item_user_avatar_chr") and row.get("icon")}
    icon_ids.update(str(row["icon"]).rsplit("/", 1)[-1] for row in tables["UserAvatarTable"].values()
                    if row.get("icon"))
    for key, achievement in tables["AchievementTable"].items():
        for info in achievement.get("levelInfos", {}).values():
            level = info.get("achieveLevel")
            if isinstance(level, int):
                token = f"{key}_lv{level:02d}"
                icon_ids.add(token)
                if achievement.get("canBePlated"):
                    icon_ids.add(token + "_plating")
    icons, icon_status = load_icons(layout, icon_ids - {""}, square_icon_ids=square_icon_ids)
    for language, (texts, receipt) in localizations.items():
        catalog = build_catalog(tables, texts)
        catalog.update(icons=icons, iconStatus=icon_status)
        index = publish(catalog, language, args.out_dir / "lang" / language / "production", inputs + [receipt])
        print(f"{language}: {json.dumps(index['stats'], ensure_ascii=False)}")
    write_json(args.out_dir / "production" / "manifest.json", {
        "schema": SCHEMA, "languages": languages, "defaultLanguage": default_language,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

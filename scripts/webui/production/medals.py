"""Group authored achievement tiers without merging items by displayed names."""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable


def _handle(value: Any) -> str:
    return str(value.get("id") or "") if isinstance(value, dict) else ""


def group_medals(items: dict[str, dict[str, Any]], tables: dict[str, dict[str, Any]],
                 text: Callable[[Any], str]) -> dict[str, str]:
    """Return old item-ID aliases; keep every tier's full item and conditions.

    A tier joins only when its authored name and completion-text handles match
    the item's name and decorative description. Ambiguous matches additionally
    require the achievement/level item ID; a plated suffix requires canBePlated.
    These are presentation groups, not a claim about a native item-ID consumer.
    """
    by_text: dict[tuple[str, str], list[str]] = defaultdict(list)
    for key, row in tables.get("ItemTable", {}).items():
        if str(row.get("type")) != "100":
            continue
        signature = (_handle(row.get("name")), _handle(row.get("decoDesc")))
        if all(signature):
            by_text[signature].append(key)
    classifications: dict[str, list[dict[str, str]]] = defaultdict(list)
    for key, row in tables.get("AchievementTypeTable", {}).items():
        for group in row.get("achievementGroupData", []):
            categories = [{"id": key, "title": text(row.get("categoryName")) or key,
                           "sourceRow": key}]
            if text(group.get("groupName")):
                categories.append({"id": group["groupId"], "title": text(group["groupName"]),
                                   "sourceRow": key})
            classifications[group["groupId"]].extend(categories)
    candidates = {}
    owners: dict[str, set[str]] = defaultdict(set)
    for key, row in sorted(tables.get("AchievementTable", {}).items()):
        levels = []
        for level_key, info in sorted(row.get("levelInfos", {}).items(),
                                      key=lambda entry: (int(entry[0]) if str(entry[0]).isdigit() else 0, str(entry[0]))):
            level = info.get("achieveLevel", level_key)
            matches = by_text.get((_handle(row.get("name")), _handle(info.get("completeDesc"))), [])
            expected = f"{key}_{level}"
            if len(matches) > 1:
                allowed = {expected}
                if row.get("canBePlated"):
                    allowed.add(f"{expected}_plate")
                matches = [item_id for item_id in matches if item_id in allowed]
            for item_id in matches:
                if item_id not in items or (item_id == f"{expected}_plate" and not row.get("canBePlated")):
                    continue
                plated = bool(row.get("canBePlated") and item_id == f"{expected}_plate")
                conditions = row.get("plateConditions", []) if plated else info.get("conditions", [])
                levels.append({"level": level, "plated": plated, "item": items[item_id],
                               "conditions": [{**condition, "description": text(condition.get("desc"))}
                                              for condition in conditions]})
                owners[item_id].add(key)
        if levels:
            candidates[key] = (row, levels)
    aliases = {}
    for key, (achievement, levels) in candidates.items():
        ids = [level["item"]["id"] for level in levels]
        if key in items or len(set(ids)) != len(ids) or any(len(owners[item_id]) != 1 for item_id in ids):
            continue
        categories = classifications.get(achievement.get("groupId", ""), [])
        first = levels[0]["item"]
        group = {**first, "id": key, "title": text(achievement.get("name")) or first["title"],
                 "lore": "", "aliases": ids, "medalLevels": levels,
                 "achievementId": key, "categories": categories,
                 "sources": [{"table": "AchievementTable", "row": key, "field": ""}],
                 "tags": list(dict.fromkeys(tag for level in levels for tag in level["item"]["tags"]))}
        for category in categories:
            source = {"table": "AchievementTypeTable", "row": category["sourceRow"], "field": ""}
            if source not in group["sources"]:
                group["sources"].append(source)
        for field in ("producedBy", "usedBy", "shops", "upgrades", "buildingIds",
                      "buildingDimensions", "outputReferences", "sources"):
            values = [value for level in levels for value in level["item"][field]]
            group[field] = (group["sources"] + values) if field == "sources" else values
        for item_id in ids:
            aliases[item_id] = key
            del items[item_id]
        items[key] = group
    return aliases

"""Group matching item records through the authored LTItemTable mapping."""
from __future__ import annotations

from collections import defaultdict
from typing import Any


def group_limited_items(items: dict[str, dict[str, Any]],
                        tables: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Keep the target item as the display identity and retain every source row.

    LTItemTable supplies the direction; names and prefixes never create links.
    Only records equal apart from ID and internal type share an entry. This is
    presentation grouping, not a claim that the two runtime item types coincide.
    """
    links = tables.get("LTItemTable", {})
    raw_items = tables.get("ItemTable", {})
    groups: dict[str, list[str]] = defaultdict(list)
    for alias, link in sorted(links.items()):
        target = link.get("itemId") if isinstance(link, dict) else None
        if not isinstance(target, str) or target == alias or target in links:
            continue
        if alias not in items or target not in items:
            continue
        rows = [raw_items.get(key) for key in (alias, target)]
        if not all(isinstance(row, dict) for row in rows):
            continue
        values = [{key: value for key, value in row.items() if key not in {"id", "type"}}
                  for row in rows]
        if values[0] == values[1]:
            groups[target].append(alias)

    aliases = {}
    for target, members in sorted(groups.items()):
        ids = [target, *members]
        originals = [items[key] for key in ids]
        group = {**originals[0], "aliases": ids, "itemVariants": originals}
        for field in ("producedBy", "usedBy", "shops", "upgrades", "buildingIds",
                      "buildingDimensions", "outputReferences", "sources", "tags"):
            values = []
            for row in originals:
                for value in row[field]:
                    if value not in values:
                        values.append(value)
            group[field] = values
        group["tags"] = [tag for tag in group["tags"] if tag != "no_source_link"]
        if not group["producedBy"] and not group["shops"]:
            group["tags"].append("no_source_link")
        group["sources"].extend({"table": "LTItemTable", "row": key, "field": "itemId"}
                                for key in members)
        for key in members:
            aliases[key] = target
            del items[key]
        items[target] = group
    return aliases

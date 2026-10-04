"""Presentation groups for recipes with the same positive output item set."""
from __future__ import annotations

from collections import defaultdict
from typing import Any


def group_recipes(recipes: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Keep complete variants, including co-products, counts and group boundaries."""
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in recipes.values():
        output_ids = tuple(sorted({ref["id"] for group in row["outcomes"] for ref in group
                                   if isinstance(ref.get("count"), (int, float))
                                   and not isinstance(ref["count"], bool) and ref["count"] > 0}))
        if output_ids:
            groups[output_ids].append(row)
    aliases = {}
    for output_ids, variants in sorted(groups.items()):
        if len(variants) < 2:
            continue
        variants.sort(key=lambda row: row["id"])
        first = variants[0]
        group_id = "output:" + "|".join(output_ids)
        titles = {ref["id"]: ref["title"] for row in variants
                  for group in row["outcomes"] for ref in group}
        grouped = {
            **first, "id": group_id, "title": " + ".join(titles[key] for key in output_ids),
            "description": "", "aliases": [row["id"] for row in variants],
            "recipeVariants": variants,
            "types": sorted({row["type"] for row in variants}),
            "machineNames": sorted({row["machineName"] for row in variants if row["machineName"]}),
            "machineIds": sorted({row["machineId"] for row in variants if row["machineId"]}),
            "rarity": max(row["rarity"] for row in variants),
            "tags": sorted({tag for row in variants for tag in row["tags"]}),
            "sources": [ref for row in variants for ref in row["sources"]],
            "categories": list({ref["id"]: ref for row in variants for ref in row["categories"]}.values()),
            # The index uses these for searching. Each detail variant keeps its
            # own authored nesting; this union never describes a single craft.
            "ingredients": [group for row in variants for group in row["ingredients"]],
            "outcomes": [group for row in variants for group in row["outcomes"]],
        }
        grouped.pop("durationSeconds", None)
        for row in variants:
            aliases[row["id"]] = group_id
            del recipes[row["id"]]
        recipes[group_id] = grouped
    return aliases

"""Authored sources behind Production, projected equally for both exports."""
from __future__ import annotations

from typing import Any

from scripts.webui.production.build_production import build_catalog


def production_source_records(tables: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Collect exact displayed relationships, without a transitive recipe crawl.

    Use the catalog's joins and medal/limited-item display groups. Compare source
    rows and their text handles, never generated page JSON or translated labels.
    """
    publication = build_catalog(tables, {})
    catalog = publication["records"]
    aliases = publication["itemAliases"]
    result = {}
    for kind, records in catalog.items():
        for key, record in records.items():
            sources = {}

            def add(table, row_id):
                row_id = str(row_id)
                if row_id in tables.get(table, {}):
                    sources[f"{table}/{row_id}"] = tables[table][row_id]

            def receipts(row):
                for source in row.get("sources", []):
                    add(source["table"], source["row"])

            def building(building_id):
                row = catalog["machines"].get(str(building_id), {})
                receipts(row)
                for ref in row.get("items", []):
                    add("ItemTable", ref["id"])

            def item(item_id):
                item_id = str(item_id)
                row = catalog["items"].get(aliases.get(item_id, item_id), {})
                for source_id in sorted({item_id, row.get("id", item_id)}):
                    raw = tables.get("ItemTable", {}).get(source_id, {})
                    add("ItemTable", source_id)
                    add("ItemTypeTable", raw.get("type", ""))
                    add("ItemShowingTypeTable", raw.get("showingType", ""))
                receipts(row)
                for building_id in row.get("buildingIds", []):
                    building(building_id)

            def visit(value):
                if isinstance(value, list):
                    for child in value:
                        visit(child)
                elif isinstance(value, dict):
                    receipts(value)
                    if value.get("resolved") is True:
                        item(value.get("id", ""))
                    if value.get("machineId"):
                        building(value["machineId"])
                    for building_id in value.get("buildingIds", []):
                        building(building_id)
                    recipe = catalog["recipes"].get(str(value.get("id", "")))
                    if str(value.get("type")) in {"machine", "hub", "manual"} and recipe:
                        receipts(recipe)
                        building(recipe["machineId"])
                        for group in recipe["outcomes"]:
                            for ref in group:
                                item(ref["id"])
                    if value.get("targetKind") == "items":
                        item(value.get("targetId", ""))
                    for child in value.values():
                        visit(child)

            if kind == "items":
                for item_id in record.get("aliases", [key]):
                    item(item_id)
            visit(record)
            result[f"{kind}:{key}"] = sources
    return result

"""Authored sources behind Gameplay items, projected equally for both exports."""
from __future__ import annotations

from typing import Any

from scripts.webui.gameplay.items.build import build_catalog


def item_source_records(tables: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Collect exact displayed relationships, without a transitive recipe crawl.

    Use the catalog's joins and medal/limited-item display groups. Compare source
    rows and their text handles, never generated page JSON or translated labels.
    """
    publication = build_catalog(tables, {})
    catalog = publication["records"]
    aliases = publication["itemAliases"]
    recipe_aliases = publication.get("recipeAliases", {})
    result = {}
    for kind, records in catalog.items():
        for key, record in records.items():
            sources = {}
            full_sources = set()

            def add(table, row_id, fields=None):
                row_id = str(row_id)
                if row_id in tables.get(table, {}):
                    source = f'{table}/{row_id}'
                    row = tables[table][row_id]
                    if fields is None:
                        sources[source] = row
                        full_sources.add(source)
                    elif source not in full_sources and isinstance(row, dict):
                        sources[source] = {**sources.get(source, {}),
                                           **{field: row[field] for field in fields if field in row}}

            def receipts(row):
                for source in row.get("sources", []):
                    fields = source.get('field')
                    add(source["table"], source["row"],
                        tuple(field.strip() for field in fields.split(',')) if fields else None)

            def building(building_id):
                row = catalog["machines"].get(str(building_id), {})
                # A linked machine supplies its label/footprint, not ownership
                # of that machine's complete recipes and configuration.
                for source in row.get('sources', []):
                    if source['table'] == 'FactoryBuildingTable':
                        add(source['table'], source['row'], ('range',))
                for ref in row.get("items", []):
                    add("ItemTable", ref["id"], ('name', 'iconId', 'rarity', 'type'))

            def item(item_id, *, owned=False):
                item_id = str(item_id)
                row = catalog["items"].get(aliases.get(item_id, item_id), {})
                for source_id in sorted({item_id, row.get("id", item_id)}):
                    raw = tables.get("ItemTable", {}).get(source_id, {})
                    add("ItemTable", source_id, None if owned else ('name', 'iconId', 'rarity', 'type'))
                    if owned:
                        add("ItemTypeTable", raw.get("type", ""))
                        add("ItemShowingTypeTable", raw.get("showingType", ""))
                if owned:
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
                    recipe_id = str(value.get("id", ""))
                    recipe = catalog["recipes"].get(recipe_aliases.get(recipe_id, recipe_id))
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
                    item(item_id, owned=True)
            visit(record)
            result[f"{kind}:{key}"] = sources
    return result

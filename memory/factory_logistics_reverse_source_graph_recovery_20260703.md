# Factory Logistics Reverse Source Graph Recovery - 2026-07-03

## Context

Factory logistics and crafting tables had forward graph edges from items to
logistic units, hubs to displayed items, craft groups to recipes, and recipes to
ingredient tags. Reverse lookup from the unit, displayed item, recipe, or tag
still required manual SQL.

## Change

`tools/endfield_source_graph.py` now emits reverse edges for:

- `factory_logistic_unit_built_from_item`
- `item_shown_in_factory_hub`
- `factory_recipe_in_craft_group`
- `factory_ingredient_tag_used_by_recipe_item`

The reverse edges preserve the same source, evidence, index/type payload, and
item id payloads as the forward edges where available.

## Validation

```bat
python -B -m py_compile tools\endfield_source_graph.py
python tools\endfield_source_graph.py build --db tmp\factory_logistics_reverse_validation_20260703.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Temporary graph result:

```text
Source graph: 1691485 nodes, 3806630 edges, 2289338 aliases
```

SQLite reverse-pair checks:

| Forward | Reverse | Count |
|---|---|---:|
| `item_builds_factory_logistic_unit` | `factory_logistic_unit_built_from_item` | 20 |
| `factory_hub_shows_item` | `item_shown_in_factory_hub` | 238 |
| `factory_craft_group_has_recipe` | `factory_recipe_in_craft_group` | 257 |
| `factory_recipe_item_uses_ingredient_tag` | `factory_ingredient_tag_used_by_recipe_item` | 241 |

All four pairs had `0` missing reverse edges and `0` extra reverse edges.

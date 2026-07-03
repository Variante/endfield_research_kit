# Factory Logistics Reverse Source Graph Recovery - 2026-07-03

## Context

Factory logistics and resource-index tables already connected hub item
visibility, machine craft groups, recipe ingredient tags, and build items to
their factory targets in the forward direction. Starting from an item, recipe,
ingredient tag, or logistic unit still missed direct reverse lookup for factory
availability and crafting context.

## Change

`tools/endfield_source_graph.py` now emits reverse edges for selected factory
logistics relationships:

- `item_shown_in_factory_hub`
- `factory_recipe_in_craft_group`
- `factory_ingredient_tag_used_by_recipe_item`
- `factory_logistic_unit_built_from_item`

The reverse edges preserve the same source, evidence, and payload data as the
existing forward edges.

## Validation

Syntax and diff checks:

```bat
python -m py_compile tools\endfield_source_graph.py
git diff --check -- tools/endfield_source_graph.py
```

Temporary graph:

```bat
python tools\endfield_source_graph.py build --db tmp\factory_logistics_reverse_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

The graph built successfully with 1,691,485 nodes and 3,806,630 edges.
Forward/reverse counts matched:

- `factory_hub_shows_item`: 238 / `item_shown_in_factory_hub`: 238
- `factory_craft_group_has_recipe`: 257 / `factory_recipe_in_craft_group`: 257
- `factory_recipe_item_uses_ingredient_tag`: 241 / `factory_ingredient_tag_used_by_recipe_item`: 241
- `item_builds_factory_logistic_unit`: 20 / `factory_logistic_unit_built_from_item`: 20

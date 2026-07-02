# Factory item reverse source graph recovery - 2026-07-02

## Context

Factory recipe ingestion already linked canonical craft recipes to item
ingredients and outcomes:

- `factory_consumes_item`
- `factory_produces_item`

Those edges are good when starting from a recipe, but item-centric
investigations had to inspect incoming edges to understand where an item is
consumed or produced by factory recipes.

## Graph Change

`tools/endfield_source_graph.py` now emits reverse item-centric edges from the
shared factory recipe item helper:

- `item_consumed_by_factory_recipe`
- `item_produced_by_factory_recipe`

The reverse edges preserve the same `count`, `groupIndex`, and `itemIndex`
metadata as the forward recipe edges. This is declarative recipe evidence from
factory tables; it does not simulate factory throughput, logistics, or runtime
production state.

## Validation

Focused build command:

```bat
python tools\endfield_source_graph.py build --db tmp\factory_item_reverse_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- graph size: 1,688,009 nodes, 3,142,369 edges, 2,277,554 aliases
- `factory_recipe`: 393 nodes
- `item`: 2,483 nodes
- `factory_consumes_item`: 615 edges
- `item_consumed_by_factory_recipe`: 615 edges
- `factory_produces_item`: 468 edges
- `item_produced_by_factory_recipe`: 468 edges

Existing related edges remain separate:

- `item_input_to_factory_recipe`: 442 edges
- `factory_recipe_outputs_item`: 468 edges

Top item-centric ingredient targets:

- `item_glass_bottle`: 23 consuming recipes
- `item_iron_bottle`: 21 consuming recipes
- `item_iron_enr_bottle`: 17 consuming recipes
- `item_liquid_water`: 16 consuming recipes

Top item-centric output targets:

- `item_copper_bottle`: 12 producing recipes
- `item_copper_enr_bottle`: 12 producing recipes
- `item_glass_bottle`: 12 producing recipes
- `item_glass_enr_bottle`: 12 producing recipes
- `item_iron_bottle`: 12 producing recipes
- `item_iron_enr_bottle`: 12 producing recipes

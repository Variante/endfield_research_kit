# Factory recipe reverse source graph recovery - 2026-07-02

## Context

Canonical factory recipe rows already exposed recipe-to-target relationships:

- `unlocked_by_factory_formula_item`
- `crafted_by_machine`
- `factory_recipe_domain`
- `belongs_to_factory_craft_group`

Those edges are useful from the recipe side. This slice adds target-centric
edges so item, machine, domain, and craft-group queries show the canonical
recipes they unlock, craft, contain, or scope.

## Graph Change

`tools/endfield_source_graph.py` now emits reverse edges in
`add_factory_recipe_edges`:

- `factory_formula_item_unlocks_recipe`
- `factory_machine_crafts_recipe`
- `domain_has_factory_recipe`
- `factory_craft_group_has_canonical_recipe`

The source evidence remains the decoded table fields `itemId`, `machineId`,
`domainId`, `formulaGroupId`, and `belongingGroupIds`. These are declarative
factory recipe relationships, not runtime logistics or throughput simulation.

## Validation

Focused build command:

```bat
python tools\endfield_source_graph.py build --db tmp\factory_recipe_reverse_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- graph size: 1,688,009 nodes, 3,143,094 edges, 2,277,554 aliases
- `unlocked_by_factory_formula_item`: 76 edges
- `factory_formula_item_unlocks_recipe`: 76 edges
- `crafted_by_machine`: 257 edges
- `factory_machine_crafts_recipe`: 257 edges
- `factory_recipe_domain`: 76 edges
- `domain_has_factory_recipe`: 76 edges
- `belongs_to_factory_craft_group`: 316 edges
- `factory_craft_group_has_canonical_recipe`: 316 edges
- existing `factory_craft_group_has_recipe`: 257 edges

Top target-centric machine recipe counts:

- `filling_powder_mc_1`: 73 recipes
- `dismantler_1`: 67 recipes
- `furnance_1`: 26 recipes
- `tools_assebling_mc_1`: 13 recipes
- `grinder_1`: 12 recipes
- `seedcollector_1`: 10 recipes

Domain recipe counts:

- `domain_1`: 47 recipes
- `domain_2`: 29 recipes

The `factory_craft_group_has_canonical_recipe` edge is intentionally separate
from `factory_craft_group_has_recipe`: the former mirrors canonical recipe row
fields, while the latter comes from craft-group list structures.

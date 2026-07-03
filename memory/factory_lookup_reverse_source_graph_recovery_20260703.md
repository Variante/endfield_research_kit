# Factory Lookup Reverse Source-Graph Recovery - 2026-07-03

## Scope

Several factory interaction lookup tables already had forward graph edges from
small mapping/config nodes to their targets. This pass adds reverse lookup edges
for the same table evidence so item, recipe, building, and item-type queries can
show the mapping rows that use them.

## Added Edges

- `factory_recipe_has_limited_formula_reverse`
- `limited_formula_source_has_reverse_entry`
- `factory_building_in_hub_craft_type_list`
- `item_type_source_for_conversion`
- `item_type_target_for_conversion`
- `item_has_exp_value_config`

## Validation

Focused temp graph:
`tmp/factory_lookup_reverse_validate.sqlite`

The validation seeded `ingest_factory_interaction_lookup_semantics()` only.

| Edge | Count |
| --- | ---: |
| `limited_formula_reverse_formula` | 17 |
| `factory_recipe_has_limited_formula_reverse` | 17 |
| `limited_formula_reverse_source` | 17 |
| `limited_formula_source_has_reverse_entry` | 17 |
| `factory_hub_craft_type_has_building` | 59 |
| `factory_building_in_hub_craft_type_list` | 59 |
| `item_type_conversion_from` | 5 |
| `item_type_source_for_conversion` | 5 |
| `item_type_conversion_to` | 5 |
| `item_type_target_for_conversion` | 5 |
| `exp_item_value_item` | 10 |
| `item_has_exp_value_config` | 10 |

Node counts in the focused graph:

| Node kind | Count |
| --- | ---: |
| `limited_formula_reverse` | 17 |
| `factory_recipe` | 10 |
| `factory_building` | 59 |
| `factory_hub_craft_type_list` | 6 |
| `item_type_conversion` | 5 |
| `item_type` | 10 |
| `exp_item_value` | 5 |
| `item` | 45 |

`python -m py_compile tools\endfield_source_graph.py` passed.

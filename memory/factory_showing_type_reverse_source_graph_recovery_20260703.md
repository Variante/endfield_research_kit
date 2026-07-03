# Factory Showing-Type Reverse Source-Graph Recovery - 2026-07-03

## Scope

Factory manual and hub craft recipe rows already linked recipes to
`factory_craft_showing_type` nodes through `showingType`. This pass adds the
reverse edge so queries starting from a craft showing type can discover all
recipes displayed in that category.

## Added Reverse Edge

- `factory_showing_type_has_recipe`

## Validation

Focused temp graph:
`tmp/factory_showing_type_reverse_validate.sqlite`

The validation seeded `FactoryManualCraftTable`, `FactoryMachineCraftTable`,
`FactoryHubCraftTable`, and `FactoryCraftShowingTypeTable` through the
structured-row ingester.

| Forward edge | Count | Reverse edge | Count |
| --- | ---: | --- | ---: |
| `has_factory_showing_type` | 135 | `factory_showing_type_has_recipe` | 135 |

Source split:

| Source table | Count |
| --- | ---: |
| `FactoryManualCraftTable` | 76 |
| `FactoryHubCraftTable` | 59 |

`FactoryMachineCraftTable` currently has no populated `showingType` rows in
the focused export.

`python -m py_compile tools\endfield_source_graph.py` passed.

# Factory Reverse And Social Source Graph Recovery - 2026-07-02

A focused source-graph pass now ingests factory reverse-lookup and social factory
tables from `export_full/structured/StreamingAssets/Table/`:

- `FactoryItemAsHubCraftIncomeTable.json`
- `FactoryItemAsHubCraftOutcomeTable.json`
- `FactoryItemAsMachineCrafterIncomeTable.json`
- `FactoryItemAsMachineCrafterOutcomeTable.json`
- `FactoryItemAsManualCraftOutcomeTable.json`
- `FactoryBuildingItemReverseTable.json`
- `FactoryManualCraftReverseTable.json`
- `FactorySocialBuildingTable.json`
- `FactorySocialBuildingNpcTable.json`
- `FactorySpecialCraftTable.json`
- `FactoryStoragerTable.json`

This closes the factory reverse-index gap identified during the original game
data understanding follow-up. Existing graph coverage already modeled many
forward recipe/building relationships; this pass adds the game-authored reverse
indexes that answer "which recipes use or output this item?" and "which item
builds this factory building?" while linking back to canonical `item`,
`factory_recipe`, `factory_building`, `factory_craft_group`, and
`factory_building_type` nodes.

Validation build:

```bat
python tools\endfield_source_graph.py build --db tmp\factory_reverse_social_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- Nodes: 1,585,175
- Edges: 2,963,641
- Aliases: 2,152,769

New node counts in the validation DB:

- `factory_item_reverse_index`: 537
- `factory_building_item_reverse`: 89
- `factory_social_building`: 4
- `factory_social_npc`: 1
- `factory_special_craft`: 2
- `factory_storage_rule`: 2

Selected new edge counts:

- `factory_reverse_index_recipe`: 910
- `item_input_to_factory_recipe`: 442
- `factory_recipe_outputs_item`: 468
- `item_builds_factory_building`: 89
- `manual_craft_reverse_points_to_recipe`: 75
- `factory_social_building_type`: 4
- `factory_special_craft_group`: 2
- `factory_storage_rule_for_building`: 2

The reverse-index nodes are kept as evidence wrappers, not replacements for the
canonical recipe/building/item nodes. This preserves the original authored table
surface while keeping normal graph queries centered on the reusable entity
nodes.

# Equipment formula reverse source graph recovery - 2026-07-02

## Context

Equipment formula recovery already linked formulas to outputs, cost items,
currency items, packs, and unlock keys. Output equipment already had the
reverse `equipment_crafted_by_formula` edge, but formula costs and unlock keys
were still one-way.

This made item- or unlock-centric investigations less direct: a query for a
material or unlock key had to inspect incoming edges instead of seeing an
explicit "this target participates in these formulas" relationship.

## Graph Change

`tools/endfield_source_graph.py` now emits reverse edges for decoded
`EquipFormulaTable` fields:

- `item_cost_for_equipment_formula`
- `currency_cost_for_equipment_formula`
- `unlock_key_unlocks_equipment_formula`

The reverse edges preserve the same count/index metadata and field evidence as
the forward formula edges. These are declarative formula-table relationships,
not runtime crafting or economy simulation.

## Validation

Focused build command:

```bat
python tools\endfield_source_graph.py build --db tmp\equipment_formula_reverse_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- graph size: 1,688,009 nodes, 3,143,663 edges, 2,277,554 aliases
- `equipment_formula`: 220 nodes
- `equipment_formula_cost_item`: 224 edges
- `item_cost_for_equipment_formula`: 224 edges
- `equipment_formula_cost_currency`: 216 edges
- `currency_cost_for_equipment_formula`: 216 edges
- `equipment_formula_unlock_key`: 129 edges
- `unlock_key_unlocks_equipment_formula`: 129 edges
- retained `equipment_formula_outputs_equipment`: 220 edges
- retained `equipment_crafted_by_formula`: 220 edges

Top item-cost formula targets:

- `item_equip_script_4`: 74 formulas
- `item_equip_script_3`: 44 formulas
- `item_equip_script_4_1`: 30 formulas
- `item_equip_script_4_2`: 25 formulas
- `item_equip_script_2`: 23 formulas
- `item_equip_script_1`: 20 formulas

Top unlock-key formula targets:

- `domainshop_channel_map02_1`: 29 formulas
- `reward_eco_indie_dg007_int_187`: 5 formulas
- `reward_eco_map02_lv001_int_23213`: 5 formulas
- `reward_eco_map02_lv001_int_23214`: 5 formulas
- `reward_eco_map02_lv001_int_360036`: 5 formulas
- `reward_eco_map02_lv001_int_360037`: 5 formulas

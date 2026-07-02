# Equipment progression source graph recovery - 2026-07-02

## Scope

Added structured source-graph recovery for the equipment crafting, formula-pack,
enhancement, and character-potential tables that were not covered by the
equipment/gem semantic pass:

- `EquipFormulaTable.json`
- `EquipFormulaReverseTable.json`
- `EquipPackTable.json`
- `EquipPackFormulaTable.json`
- `CharacterPotentialTable.json`
- `CharPotentialDecoTable.json`
- `EquipEnhanceCostTable.json`
- `EquipEnhanceGuaranteeTimesRuleTable.json`
- `EquipConst.json`
- `EquipTechConst.json`

## Recovered semantics

- Equipment formulas now link formula ids to output equipment, formula packs,
  required item/currency costs, and unlock keys.
- Reverse formula rows now preserve the equipment-to-formula lookup table as
  first-class `equipment_formula_reverse` evidence.
- Formula packs now link display names/icons to their included formula ids.
- Character potential rows now link characters to first unlock items, potential
  levels, cost items, potential effect ids, unlocked picture items, and card
  topic items.
- The single potential decoration config now links to its mission and exposes
  model/animation asset stems as aliases.
- Equipment enhancement cost and guarantee rows are queryable, including domain,
  consumed item, refund item, and guarantee rule evidence.
- Equipment progression constants from `EquipConst` and `EquipTechConst` are
  queryable as `equipment_const` nodes.

## Validation

Commands run:

```bat
python -m py_compile tools\endfield_source_graph.py
python tools\endfield_source_graph.py build --db tmp\equipment_progression_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

The validation build completed with:

```text
Source graph: 1587074 nodes, 3010690 edges, 2157175 aliases
```

Targeted count checks:

```text
equipment_formula                          220 nodes
equipment_formula_pack                      27 nodes
equipment_formula_reverse                  220 nodes
equipment_enhance_cost                       1 node
equipment_enhance_guarantee_rule             3 nodes
equipment_const                              6 nodes
character_potential                        150 nodes
character_potential_deco                     1 node

defines_equipment_formula                  220 edges
equipment_formula_outputs_equipment        220 edges
equipment_formula_in_pack                  440 edges
equipment_formula_cost_item                224 edges
equipment_formula_cost_currency            216 edges
equipment_formula_unlock_key               129 edges
defines_equipment_formula_reverse          220 edges
equipment_formula_reverse_equipment        220 edges
equipment_formula_reverse_formula          220 edges
equipment_reverse_points_to_formula        220 edges
defines_equipment_formula_pack              54 edges
equipment_formula_pack_has_formula         220 edges
defines_character_potential                 29 edges
character_uses_potential_item               29 edges
has_character_potential                    285 edges
character_potential_cost_item              145 edges
character_potential_effect                 145 edges
character_potential_unlock_picture_item     91 edges
character_potential_unlock_card_topic_item  12 edges
defines_character_potential_deco             1 edge
character_potential_deco_mission             1 edge
defines_equipment_enhance_cost               1 edge
equipment_enhance_cost_domain                1 edge
equipment_enhance_cost_consumes_item         1 edge
equipment_enhance_cost_refund_item           1 edge
defines_equipment_enhance_guarantee_rule     3 edges
defines_equipment_const                      6 edges
```


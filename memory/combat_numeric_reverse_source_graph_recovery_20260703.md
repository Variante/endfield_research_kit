# Combat Numeric Reverse Source Graph Recovery - 2026-07-03

## Scope

This pass adds reverse source-graph indexes for authored combat numeric
relationships that were already present as forward edges:

- ability-entity base stat rows in `AbilityEntityAttrTable.json`;
- potential-talent attribute modifiers in `PotentialTalentEffectTable.json`.

The change improves graph queries such as "which authored rows set or modify
this stat/attribute?" It does not evaluate combat formulas, modifier order, or
runtime final values.

## Graph Change

New reverse edge kinds:

- `stat_property_set_by_ability_entity`
- `stat_property_modified_by_potential_talent`
- `attribute_meta_modified_by_potential_talent`

These mirror existing direct evidence edges:

- `ability_entity_sets_stat_property`
- `potential_talent_modifies_stat_property`
- `potential_talent_modifies_attribute_meta`

Each reverse edge preserves the original value payload, including stat value,
attribute type, modifier type, modify type, and source `dataList` index where
applicable.

## Validation

Focused temporary graph build:

```bat
python -B -m py_compile tools\endfield_source_graph.py
```

Temporary DB:

```bat
tmp\combat_numeric_reverse_validation.sqlite
```

Focused ingest steps:

- `ingest_attribute_dictionary()`
- `ingest_combat_semantics()`

Edge counts:

- `ability_entity_sets_stat_property`: 28
- `stat_property_set_by_ability_entity`: 28
- `potential_talent_modifies_stat_property`: 51
- `stat_property_modified_by_potential_talent`: 51
- `potential_talent_modifies_attribute_meta`: 51
- `attribute_meta_modified_by_potential_talent`: 51

Sample evidence:

- `gameplay_stat_property:atk -> ability_entity:abilityentity_eny_0051_rodin_wall`
  from `AbilityEntityAttrTable`, evidence `atk`, payload `{"value":10.0}`.
- `attribute_meta:1 -> potential_talent_effect:chr_0023_antal_potential_4`
  from `PotentialTalentEffectTable`, evidence
  `dataList[1].attrModifier.attrType`, payload includes
  `attrValue: 0.1`, `modifierType: 6`, and `modifyType: 4`.
- `gameplay_stat_property:1 -> potential_talent_effect:chr_0023_antal_potential_4`
  from `PotentialTalentEffectTable`, evidence `dataList[1].attrModifier`.

CLI smoke queries:

```bat
python tools\endfield_source_graph.py query atk --kind gameplay_stat_property --db tmp\combat_numeric_reverse_validation.sqlite --limit 12
python tools\endfield_source_graph.py query 1 --kind attribute_meta --db tmp\combat_numeric_reverse_validation.sqlite --limit 12
python tools\endfield_source_graph.py query chr_0023_antal_potential_4 --kind potential_talent_effect --db tmp\combat_numeric_reverse_validation.sqlite --limit 12
```

The `attribute_meta:1` query now exposes
`attribute_meta_modified_by_potential_talent` edges, and the
`chr_0023_antal_potential_4` query shows both forward and reverse potential
talent attribute/stat relationships.

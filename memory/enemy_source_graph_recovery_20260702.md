# Enemy Source Graph Recovery - 2026-07-02

A focused source-graph pass now ingests structured enemy tables from
`export_full/structured/StreamingAssets/Table/`:

- `EnemyTable.json`
- `EnemyDisplayInfoTable.json`
- `EnemyAbilityDescTable.json`
- `EnemyAttributeTemplateTable.json`
- `EnemyTemplateTable.json`
- `EnemyTemplateDisplayInfoTable.json`
- `DisplayEnemyTypeTable.json`
- `EnemyDamageTakenLevelTable.json`

This closes a major combat/numerical semantic gap from the original game data
understanding follow-up. Enemy rows now connect to templates, attribute
templates, AI configs, born buffs, display info, ability descriptions, display
types, distribution IDs, tags, model asset tokens, and attribute metadata.

Validation build:

```bat
python tools\endfield_source_graph.py build --db tmp\enemy_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- Nodes: 1,586,355
- Edges: 3,006,368
- Aliases: 2,154,730

Enemy-layer node counts in the validation DB:

- `enemy`: 289
- `enemy_template`: 104
- `enemy_attribute_template`: 113
- `enemy_display_type`: 5
- `enemy_ability`: 133
- `enemy_distribution`: 22
- `enemy_damage_taken_level`: 5
- `enemy_tag`: 5

Selected new edge counts:

- `defines_enemy`: 282
- `defines_enemy_display_info`: 224
- `defines_enemy_ability`: 133
- `defines_enemy_attribute_template`: 113
- `defines_enemy_template`: 78
- `defines_enemy_template_display_info`: 75
- `uses_enemy_template`: 584
- `uses_enemy_attribute_template`: 360
- `enemy_uses_ai_config`: 159
- `starts_with_buff`: 338
- `enemy_attribute_modifier_meta`: 67
- `enemy_attribute_template_independent_attr`: 1,695
- `enemy_attribute_template_level_attr`: 36,800
- `enemy_poise_knot_buff`: 34
- `has_enemy_ability`: 149
- `enemy_template_has_ability`: 115
- `has_enemy_display_type`: 150
- `enemy_template_distribution`: 199

The pass intentionally preserves raw numeric fields such as damage resistance
scalars, max resilience, attribute values, and per-level attribute indexes as
node or edge data. It does not infer runtime combat formulas beyond table-proven
relationships.

# Mode Constant And Lookup Asset Reverse Source-Graph Recovery - 2026-07-03

## Scope

This pass added reverse lookup edges for direct source-graph relationships in
the factory/interaction lookup helper and mode-constant tables.

Covered relationships:

- Factory/interaction lookup metadata asset aliases.
- Map reminder tab membership.
- Activity cleaning stage overlays.
- `InteractiveFacWrapperTable` wrapper to interactive template.
- `FactoryNodeTypeToBuildingType` and `FactoryBuildingTypeToNodeType`
  building-type maps.
- `ActivityHighDifficultySpecialStageTable` stage to activity-stage rows.

These edges are direct inverses of table fields or helper-emitted asset
references. They do not infer runtime unlocks, stage availability, interaction
state, or building placement behavior.

## Added Edges

- `asset_ref_used_by_lookup`
- `map_reminder_tab_has_reminder`
- `activity_cleaning_stage_overlay`
- `activity_stage_has_cleaning_stage_overlay`
- `interactive_template_has_fac_wrapper`
- `factory_building_type_source_for_map`
- `factory_building_type_target_for_map`
- `activity_stage_has_high_difficulty_special_stage`

## Validation

Commands:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Focused temp graphs:

- `tmp/factory_lookup_reverse_next_validate.sqlite`
- `tmp/mode_constant_reverse_next_validate.sqlite`

The validations seeded `ingest_factory_interaction_lookup_semantics()` and
`ingest_mode_constant_semantics()` separately.

| Edge | Count |
| --- | ---: |
| `lookup_references_asset` | 79 |
| `asset_ref_used_by_lookup` | 79 |
| `map_reminder_in_tab` | 13 |
| `map_reminder_tab_has_reminder` | 13 |
| `activity_cleaning_stage_overlay` | 7 |
| `activity_stage_has_cleaning_stage_overlay` | 7 |
| `interactive_fac_wrapper_template` | 46 |
| `interactive_template_has_fac_wrapper` | 46 |
| `factory_building_type_map_source` | 65 |
| `factory_building_type_source_for_map` | 65 |
| `factory_building_type_map_target` | 65 |
| `factory_building_type_target_for_map` | 65 |
| `high_difficulty_special_stage_activity_stage` | 32 |
| `activity_stage_has_high_difficulty_special_stage` | 32 |

Focused factory lookup graph node counts:

| Node kind | Count |
| --- | ---: |
| `asset_ref` | 61 |
| `map_reminder_tab` | 2 |
| `activity_cleaning_stage` | 7 |
| `activity_stage` | 15 |
| `level` | 8 |
| `quest_task` | 7 |

Focused mode constants graph node counts:

| Node kind | Count |
| --- | ---: |
| `interactive_fac_wrapper` | 46 |
| `interactive_template` | 29 |
| `factory_building_type_map` | 65 |
| `factory_building_type` | 84 |
| `activity_high_difficulty_special_stage` | 32 |
| `activity_stage` | 32 |

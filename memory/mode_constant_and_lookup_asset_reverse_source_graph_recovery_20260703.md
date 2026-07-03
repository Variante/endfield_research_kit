# Mode Constant And Lookup Asset Reverse Source-Graph Recovery - 2026-07-03

## Scope

This pass added reverse lookup edges for direct source-graph relationships in
the factory/interaction lookup helper and mode-constant tables.

Covered relationships:

- Factory/interaction lookup metadata asset aliases.
- `InteractiveFacWrapperTable` wrapper to interactive template.
- `FactoryNodeTypeToBuildingType` and `FactoryBuildingTypeToNodeType`
  building-type maps.
- `ActivityHighDifficultySpecialStageTable` stage to activity-stage rows.

These edges are direct inverses of table fields or helper-emitted asset
references. They do not infer runtime unlocks, stage availability, or building
placement behavior.

## Added Edges

- `asset_referenced_by_lookup`
- `interactive_template_has_fac_wrapper`
- `factory_building_type_source_for_map`
- `factory_building_type_target_for_map`
- `activity_stage_has_high_difficulty_special_stage`

## Validation

Commands:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Focused temp graph:
`tmp/mode_constant_and_lookup_asset_reverse_validate.sqlite`

The validation seeded `ingest_factory_interaction_lookup_semantics()` and
`ingest_mode_constant_semantics()`.

| Edge | Count |
| --- | ---: |
| `lookup_references_asset` | 79 |
| `asset_referenced_by_lookup` | 79 |
| `interactive_fac_wrapper_template` | 46 |
| `interactive_template_has_fac_wrapper` | 46 |
| `factory_building_type_map_source` | 65 |
| `factory_building_type_source_for_map` | 65 |
| `factory_building_type_map_target` | 65 |
| `factory_building_type_target_for_map` | 65 |
| `high_difficulty_special_stage_activity_stage` | 32 |
| `activity_stage_has_high_difficulty_special_stage` | 32 |

Focused node counts:

| Node kind | Count |
| --- | ---: |
| `asset_ref` | 61 |
| `interactive_fac_wrapper` | 46 |
| `interactive_template` | 29 |
| `factory_building_type_map` | 65 |
| `factory_building_type` | 84 |
| `activity_high_difficulty_special_stage` | 32 |
| `activity_stage` | 40 |

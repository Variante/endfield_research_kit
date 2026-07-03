# Planting Step Type Source-Graph Recovery - 2026-07-03

## Scope

`PlantingDataTable.plantingSteps[].plantingStepType` identifies the authored
step type for each crop planting step, and `PlantingStepConstTable` defines the
four step type rows. The source graph previously kept the type number only in
`planting_step` payloads. This pass adds explicit links between each planting
step and its step type.

## Added Edges

- `planting_step_has_type`
- `planting_step_type_used_by_step`

## Validation

Focused temp graph:
`tmp/planting_step_type_validate.sqlite`

The validation seeded `ingest_world_harvestable_semantics()` only.

| Edge | Count |
| --- | ---: |
| `planting_crop_has_step` | 92 |
| `planting_step_has_type` | 92 |
| `planting_step_type_used_by_step` | 92 |
| `defines_planting_step_type` | 4 |

Type distribution:

| Step type | Count |
| --- | ---: |
| `1` | 16 |
| `2` | 30 |
| `3` | 30 |
| `4` | 16 |

`python -m py_compile tools\endfield_source_graph.py` passed.

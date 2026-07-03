# Global effect parameter target source graph recovery - 2026-07-03

## Context

`GlobalEffectTable.json` stores authored parameter payloads under `dps` and
`extraArgs`. The limited-formula stage effects include string parameters that
are not generic labels: they point at settlements, the limited-formula
activity, and its terminal stage. Before this recovery those values were only
kept inside opaque `global_effect_param` payloads.

## Implementation

Updated `tools/endfield_source_graph.py` near `add_global_effect_edges()`.

Promoted recognized `valueStringList` entries to existing semantic targets:

- `stm_*` -> `settlement`
- `activity_limited_formula_*_stage_*` -> `activity_limited_formula_stage`
- other `activity_limited_formula_*` -> `activity_limited_formula`

New edge families:

- `global_effect_param_refers_settlement`
- `settlement_referenced_by_global_effect_param`
- `global_effect_param_refers_activity_limited_formula`
- `activity_limited_formula_referenced_by_global_effect_param`
- `global_effect_param_refers_activity_limited_formula_stage`
- `activity_limited_formula_stage_referenced_by_global_effect_param`

No new node kinds or ingest passes were needed.

## Validation

Focused temp graph build:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Then built `tmp/global_effect_param_target_validation.sqlite` with:

- `ingest_domain_core_semantics()`
- `ingest_activity_catalog_semantics()`
- `ingest_combat_semantics()`

Observed counts:

- `global_effect_param_refers_settlement`: 4
- `settlement_referenced_by_global_effect_param`: 4
- `global_effect_param_refers_activity_limited_formula`: 4
- `activity_limited_formula_referenced_by_global_effect_param`: 4
- `global_effect_param_refers_activity_limited_formula_stage`: 4
- `activity_limited_formula_stage_referenced_by_global_effect_param`: 4

Smoke queries confirmed:

- `stm_hongs_1` now shows reverse references from
  `activity_limited_formula_1_stage_1_1_effect:dps:0` and
  `activity_limited_formula_1_stage_2_1_effect:dps:0`.
- `activity_limited_formula_1_stage_4` now shows four reverse global-effect
  param references.
- `activity_limited_formula_1_stage_1_1_effect:dps:2` now links to
  `activity_limited_formula_1`.

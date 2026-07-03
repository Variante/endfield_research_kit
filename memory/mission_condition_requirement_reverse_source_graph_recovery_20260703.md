# Mission Condition Requirement Reverse Source Graph Recovery - 2026-07-03

## Context

Decoded `MissionRuntimeAsset` condition nodes already exposed forward edges for
objective gates that require item counts or unlocked factory tech. Item- or
tech-centered graph queries could not directly enumerate which mission runtime
conditions depended on a given requirement.

## Finding

`tools/endfield_source_graph.py` now emits reverse edges for mission runtime
requirement conditions:

- `item_required_by_condition`
- `factory_tech_required_by_condition`

The item reverse edge preserves the same runtime condition payload as
`condition_requires_item_count`, including condition type, required count, and
comparer/operator values. Factory-tech reverse edges preserve the same
`_facTechId` evidence path as the forward condition edge.

## Validation

Focused temporary graph build:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Temporary DB: `tmp/condition_requirement_reverse.sqlite`

Decoded-config semantic counts from `ingest_decoded_config_semantics()`:

- `condition_requires_item_count`: 231
- `item_required_by_condition`: 231
- `condition_requires_factory_tech`: 60
- `factory_tech_required_by_condition`: 60

Sample reverse edges showed factory tech nodes such as
`factory_tech:tech_jinlong_1_planter_mode_1` pointing back to specific
`mission_runtime_condition:*:CheckUnlockTech:*` objective conditions with the
original `_facTechId` evidence path.

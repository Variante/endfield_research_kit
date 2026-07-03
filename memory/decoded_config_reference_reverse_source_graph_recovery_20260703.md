# Decoded Config Reference Reverse Source Graph Recovery - 2026-07-03

## Context

Decoded game-data configs already emitted many forward links to story keys,
missions, effects, buffs, level-script templates, and montage ids. Several of
those links were only queryable from the owning config toward the referenced
target.

## Change

`tools/endfield_source_graph.py` now adds reverse edges for decoded-config
reference families across:

- `level_data`
- `level_script`
- `level_script_template`
- `story_source_links` source rows
- `buff_data`
- `skill_data`
- `char_interact`
- `animation_config`
- `model_view_state_controller`
- `model_view_state_controller_animator`

Reverse edge prefixes include:

- `story_used_by_*`
- `mission_used_by_*`
- `gameplay_effect_used_by_*`
- `buff_used_by_*`
- `level_script_template_used_by_*`
- `level_script_montage_used_by_*`

The edges preserve the same source/evidence and reference payloads as the
forward edges where those payloads are available.

## Validation

```bat
python -B -m py_compile tools\endfield_source_graph.py
python tools\endfield_source_graph.py build --db tmp\decoded_config_reference_reverse_validation_20260703.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Temporary graph result:

```text
Source graph: 1691485 nodes, 3818804 edges, 2289338 aliases
```

The SQLite parity query covered 25 forward/reverse edge-kind pairs:

- total forward edges: 27,476
- total reverse edges: 27,476
- missing reverse edges: 0
- extra reverse edges: 0

Largest validated pairs:

| Forward | Reverse | Count |
|---|---|---:|
| `skill_data_references_effect` | `gameplay_effect_used_by_skill_data` | 9,527 |
| `level_script_references_story` | `story_used_by_level_script` | 4,416 |
| `skill_data_references_buff` | `buff_used_by_skill_data` | 3,000 |
| `buff_data_references_buff` | `buff_used_by_buff_data` | 1,862 |
| `buff_data_references_effect` | `gameplay_effect_used_by_buff_data` | 1,404 |
| `source_references_story` | `story_used_by_source` | 933 |
| `level_script_references_effect` | `gameplay_effect_used_by_level_script` | 941 |
| `level_script_references_buff` | `buff_used_by_level_script` | 873 |
| `model_view_state_controller_animator_references_effect` | `gameplay_effect_used_by_model_view_state_controller_animator` | 872 |

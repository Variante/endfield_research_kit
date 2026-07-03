# World reward reverse source graph recovery - 2026-07-03

## Context

World-energy and harvestable tables already emitted forward reward references,
but reward-centered queries could not directly enumerate the authored world
systems that consumed those reward IDs. This left rewards from energy points,
ether submit levels, doodad pickables, breakable trees, and planting crops
harder to trace from the reward side.

## Implementation

Updated the shared `add_reward_ref_edge()` reverse map in
`tools/endfield_source_graph.py`.

New reverse edge families:

- `reward_used_by_world_energy_group_first_pass`
- `reward_used_by_ether_submit_level`
- `reward_used_by_world_doodad_pickable`
- `reward_used_by_world_tree_breaking`
- `reward_used_by_world_tree_broken`
- `reward_used_by_planting_crop`
- `reward_used_by_planting_crop_increased`

No new node kinds or ingest passes were needed.

## Validation

Focused temp graph build:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Then built `tmp/world_reward_reverse_validation.sqlite` with:

- `ingest_world_energy_semantics()`
- `ingest_world_harvestable_semantics()`

Forward and reverse counts matched:

- `world_energy_group_first_pass_reward`: 9 /
  `reward_used_by_world_energy_group_first_pass`: 9
- `ether_submit_reward`: 33 /
  `reward_used_by_ether_submit_level`: 33
- `world_doodad_pickable_reward`: 48 /
  `reward_used_by_world_doodad_pickable`: 48
- `world_tree_breaking_reward`: 24 /
  `reward_used_by_world_tree_breaking`: 24
- `world_tree_broken_reward`: 24 /
  `reward_used_by_world_tree_broken`: 24
- `planting_crop_reward`: 16 /
  `reward_used_by_planting_crop`: 16
- `planting_crop_increased_reward`: 16 /
  `reward_used_by_planting_crop_increased`: 16

Smoke queries confirmed:

- `reward_world_energy_point01` resolves back to
  `world_energy_point_group01`.
- `reward_doodad_moss_1` resolves back to three pickable doodad owners.
- `reward_ether_level10` resolves back to ether submit level `10`.

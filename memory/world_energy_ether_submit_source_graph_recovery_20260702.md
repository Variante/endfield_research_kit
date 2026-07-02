# World Energy And Ether Submit Source Graph Recovery - 2026-07-02

A focused source-graph pass now ingests the World Energy Point and Ether Submit
progression tables from `export_full/structured/StreamingAssets/Table/`:

- `WorldEnergyPointTable.json`
- `WorldEnergyPointGroupTable.json`
- `WorldEnergyPointConst.json`
- `EtherSubmitInfoTable.json`
- `EtherSubmitBuffShowTable.json`
- `EtherSubmitDomainShowTable.json`
- `EtherSubmitGlobalEffectTable.json`

This pass closes a numerical/gameplay loop gap identified while following up on
`memory/original_game_data_understanding_report_20260701.md`: energy points now
connect world-level entries to levels, enemies, rewards, probable gem drops,
gem term pools, game-mechanic rows, ether-submit costs, and global effects.

Validation build:

```bat
python tools\endfield_source_graph.py build --db tmp\world_energy_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- Nodes: 1,583,771
- Edges: 2,959,120
- Aliases: 2,149,864

New World Energy/Ether node counts in the validation DB:

- `world_energy_point_group`: 9
- `world_energy_point`: 63
- `world_energy_const`: 2
- `ether_submit_level`: 33
- `ether_submit_effect`: 10
- `ether_submit_effect_type`: 5
- `ether_submit_domain`: 2

Selected new edge counts:

- `world_energy_point_enemy`: 441
- `world_energy_point_probable_gem`: 567
- `world_energy_point_regular_item`: 36
- `world_energy_point_in_level`: 63
- `world_energy_point_game_mechanic`: 63
- `world_energy_group_has_point`: 126
- `world_energy_group_primary_gem_term`: 45
- `world_energy_group_secondary_gem_term`: 72
- `world_energy_group_skill_gem_term`: 72
- `world_energy_group_first_pass_reward`: 9
- `ether_submit_requires_item`: 33
- `ether_submit_reward`: 33
- `ether_submit_applies_effect`: 70
- `defines_ether_submit_global_effect`: 19
- `ether_submit_global_effect_blackboard`: 21

The graph records numeric gameplay fields such as `worldLevel`, `recommendLv`,
`costStamina`, enemy levels, ether submit `level`, required item `count`, and
global effect `effectType`/`dp1` as node or edge data. It does not infer runtime
formula behavior beyond table-proven references.

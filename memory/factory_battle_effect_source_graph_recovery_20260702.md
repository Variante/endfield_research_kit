# Factory battle effect source graph recovery - 2026-07-02

## Context

`FactoryBattleTable.attackRangeEffect` was decoded and stored only as an
`asset_stem` alias on `factory_battle_config`. The field is more specific than
a loose asset stem: it names the gameplay effect used by factory battle configs
for attack-range presentation.

## Graph Change

`tools/endfield_source_graph.py` now materializes this field as:

- `gameplay_effect` nodes for each `attackRangeEffect`
- `factory_battle_attack_range_effect` edges from `factory_battle_config`
  to the effect

The edge data preserves `attackRange`, `attackRangeType`, and
`minAttackRange`. This is declarative table evidence for range effect
configuration; it does not recover damage, cooldown, targeting, overload, or
runtime formula execution.

## Validation

Focused build command:

```bat
python tools\endfield_source_graph.py build --db tmp\factory_battle_effect_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- graph size: 1,688,009 nodes, 3,141,286 edges, 2,277,554 aliases
- `factory_battle_config`: 17 nodes
- `gameplay_effect`: 5,340 nodes
- `factory_battle_attack_range_effect`: 16 edges
- retained `factory_battle_common_skill`: 17 edges
- retained `factory_battle_overload_skill`: 16 edges

Effect targets:

- `P_interactive_boundary_weapontower_01`: 14 configs
- `P_interactive_rectangle_boundary_weapontower_01`: 2 configs

Example edge payloads preserve circle/rectangle range metadata such as
`battle_cannon_1 -> P_interactive_boundary_weapontower_01` with attack range
`12.5` and type `circle`, and
`battle_jet_1 -> P_interactive_rectangle_boundary_weapontower_01` with attack
range `7.0` and type `rectangle`.

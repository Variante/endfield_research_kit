# Recommend Training Threshold Source Graph Recovery - 2026-07-03

## Context

`RecommendTraining.json` contains the combat-readiness curve used by the game
to map enemy levels to recommended squad investment. The graph already created
`training_recommendation` nodes, but the threshold fields only lived inside the
node JSON payload:

- `enemyLv`
- `squadLvSum`
- `squadWeaponLvSum`
- `squadSkillLvSum`
- `squadEquipLvSum`

This made the data visible but not traversable by enemy level or by readiness
axis.

## Implementation

`tools/endfield_source_graph.py` now adds:

- `combat_enemy_level` nodes for `enemyLv`
- `training_power_axis` nodes for the four squad investment axes
- `training_recommendation_for_enemy_level`
- `enemy_level_has_training_recommendation`
- `training_recommendation_requires_axis`
- `training_power_axis_used_by_recommendation`

Axis edges preserve the numeric threshold as edge data.

## Validation

Focused validation graph:

```text
nodes training_recommendation 80
nodes combat_enemy_level 80
nodes training_power_axis 4
edges training_recommendation_for_enemy_level 80
edges enemy_level_has_training_recommendation 80
edges training_recommendation_requires_axis 320
edges training_power_axis_used_by_recommendation 320
```

Sample threshold evidence for `training_recommendation:40`:

```text
training_recommendation_for_enemy_level -> combat_enemy_level:40
training_recommendation_requires_axis -> training_power_axis:squadLvSum {"value":160}
training_recommendation_requires_axis -> training_power_axis:squadWeaponLvSum {"value":160}
training_recommendation_requires_axis -> training_power_axis:squadSkillLvSum {"value":64}
training_recommendation_requires_axis -> training_power_axis:squadEquipLvSum {"value":800}
```

CLI smoke queries:

```bat
python tools\endfield_source_graph.py query 40 --kind training_recommendation --db tmp\recommend_training_validation.sqlite --limit 12
python tools\endfield_source_graph.py query 40 --kind combat_enemy_level --db tmp\recommend_training_validation.sqlite --limit 12
python tools\endfield_source_graph.py query squadSkillLvSum --kind training_power_axis --db tmp\recommend_training_validation.sqlite --limit 12
```

The queries showed recommendation-to-enemy-level traversal and axis-to-
recommendation traversal. Focused SQL confirmed the axis threshold values in
edge data.

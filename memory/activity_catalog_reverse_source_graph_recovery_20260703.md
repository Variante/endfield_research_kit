# Activity Catalog Reverse Source-Graph Recovery - 2026-07-03

## Scope

Activity catalog tables already linked event UI/catalog surfaces to
achievements, showcase rewards, and adventure reward items. This pass adds the
reverse edges so queries starting from the reward target, item, character, or
achievement can discover the event surface that uses it.

## Added Reverse Edges

- `achievement_used_by_activity_game_entrance_series`
- `achievement_used_by_high_difficulty_series`
- `showcase_ref_used_by_activity_benefit_big_reward`
- `showcase_ref_used_by_activity_benefit_reward`
- `item_used_by_adventure_activity_reward`

## Validation

Focused temp graph:
`tmp/activity_catalog_reverse_validate.sqlite`

The validation seeded item economy, activity achievement rows, and activity
catalog rows.

| Forward edge | Count | Reverse edge | Count |
| --- | ---: | --- | ---: |
| `activity_game_entrance_series_achievement` | 4 | `achievement_used_by_activity_game_entrance_series` | 4 |
| `high_difficulty_series_achievement` | 4 | `achievement_used_by_high_difficulty_series` | 4 |
| `activity_benefit_big_reward_ref` | 8 | `showcase_ref_used_by_activity_benefit_big_reward` | 8 |
| `activity_benefit_reward_ref` | 19 | `showcase_ref_used_by_activity_benefit_reward` | 19 |
| `adventure_activity_reward_item` | 4 | `item_used_by_adventure_activity_reward` | 4 |

`python -m py_compile tools\endfield_source_graph.py` passed.

# Soil Reward Item Reverse Source Graph Recovery - 2026-07-03

## Context

Standard reward bundle and reward-drop item edges already supported item-first
lookups. `RewardSoilTable` used the same bundle helper, but its
`soil_reward_grants_item` edge kind did not yet map to an item-to-soil-reward
reverse edge.

## Finding

`tools/endfield_source_graph.py` now maps soil reward bundle edges to:

- `item_granted_by_soil_reward`
- `item_may_be_granted_by_soil_reward`

The reverse edges keep the same `itemBundles[...]` / `probItemBundles[...]`
evidence and count/index payloads as the forward soil reward item edges.

## Validation

Focused temporary graph build:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Temporary DB: `tmp/soil_reward_reverse.sqlite`

World-harvestable semantic counts:

- `soil_reward_grants_item`: 20
- `item_granted_by_soil_reward`: 20
- `soil_reward_prob_item`: 0
- `item_may_be_granted_by_soil_reward`: 0

Sample reverse edges showed plant items such as `item:item_plant_bbflower_1`
pointing back to normal and increased `soil_reward:*` rows with preserved
`itemBundles[0]` evidence and counts.

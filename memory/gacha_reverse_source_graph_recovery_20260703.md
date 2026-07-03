# Gacha reverse source graph recovery - 2026-07-03

## Context

The gacha semantic ingest already modeled authored forward links from character
and weapon gacha pools to rewards, ticket costs, trial activity jumps, and
gacha constants. The shared `add_system_jump_edge()` and `add_reward_ref_edge()`
reverse maps did not include the gacha edge kinds, so queries starting from a
`system_jump` or `reward` could not discover the gacha pool or constant that
used it.

## Implementation

Updated `tools/endfield_source_graph.py` reverse mappings only:

- `gacha_pool_trial_jump` now emits `system_jump_used_by_gacha_pool`.
- `gacha_recommendation_jump` now emits
  `system_jump_used_by_gacha_recommendation` when recommendation rows contain
  a jump.
- `gacha_const_reward_ref` now emits `reward_used_by_gacha_const`.
- `gacha_pool_once_reward` now emits `reward_used_by_gacha_pool_once`.
- `gacha_pool_every_pull_reward` now emits
  `reward_used_by_gacha_pool_every_pull`.
- `gacha_pool_cumulative_reward` now emits
  `reward_used_by_gacha_pool_cumulative`.
- `gacha_pool_interval_reward` now emits
  `reward_used_by_gacha_pool_interval`.
- `gacha_weapon_pool_interval_reward` now emits
  `reward_used_by_gacha_weapon_pool_interval`.

No new node kinds or ingest passes were needed.

## Validation

Focused temp graph build:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Then built `tmp/gacha_reverse_validation.sqlite` with only
`ingest_gacha_semantics()`.

Expected and observed reverse edge counts:

- `system_jump_used_by_gacha_pool`: 7
- `system_jump_used_by_gacha_recommendation`: 0, matching current
  `GachaEntryRecommendTable.json` rows with no non-empty `jump` values
- `reward_used_by_gacha_const`: 7
- `reward_used_by_gacha_pool_once`: 2
- `reward_used_by_gacha_pool_every_pull`: 1
- `reward_used_by_gacha_pool_cumulative`: 1
- `reward_used_by_gacha_pool_interval`: 8
- `reward_used_by_gacha_weapon_pool_interval`: 28

Smoke queries confirmed:

- `jump_center_activity_char_trial_1` now returns
  `system_jump_used_by_gacha_pool -> special_1_0_1`.
- `reward_ticketgacha_standard_1_2_2` now returns
  `reward_used_by_gacha_pool_once -> joint_1_2_2`.
- `reward_6starChar_charTicket` now returns both repeat-star-six gacha
  constants through `reward_used_by_gacha_const`.

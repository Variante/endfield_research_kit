# Activity character trial source graph recovery - 2026-07-03

## Context

`ActivityCharTrial.json` is authored game data that binds each character trial
activity to its trial dungeon, gacha/system jump, and reward. The source graph
already created `character_trial` nodes and `trial_grants_reward` edges, but
`activityId` and `jumpId` were aliases only, and the activity-trial dungeon
relationship was not navigable from activity, dungeon, jump, or reward queries.

## Implementation

Updated `tools/endfield_source_graph.py` in `add_activity_char_trial_edges()`.
No new node kinds or ingest passes were needed.

New or newly-reversed edge families:

- `activity_has_character_trial`
- `character_trial_in_activity`
- `activity_character_trial_uses_dungeon`
- `dungeon_used_by_activity_character_trial`
- `character_trial_jumps_to`
- `system_jump_used_by_character_trial`
- `reward_granted_by_character_trial`

`trial_grants_reward` now uses `add_reward_ref_edge()` so the reverse reward
edge is emitted consistently with other reward references.

## Validation

Focused temp graph build:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Then built `tmp/activity_char_trial_validation.sqlite` with only
`ingest_character_support_semantics()`.

Expected and observed edge counts:

- `activity_has_character_trial`: 7
- `character_trial_in_activity`: 7
- `activity_character_trial_uses_dungeon`: 7
- `dungeon_used_by_activity_character_trial`: 7
- `character_trial_jumps_to`: 7
- `system_jump_used_by_character_trial`: 7
- `trial_grants_reward`: 7
- `reward_granted_by_character_trial`: 7

Smoke queries confirmed `dung_aglina_chartrial` links to:

- activity `activity_char_trial_3`
- dungeon `dung_aglina_chartrial`
- system jump `jump_gacha_limit_3`
- reward `reward_activity_dung_aglina_chartrial`

Reverse queries from `jump_gacha_limit_3` and
`reward_activity_dung_aglina_chartrial` now return the character trial.

# Decoded Config Reverse Source Graph Recovery - 2026-07-03

## Context

Several decoded WebUI game-data config relationships were forward-only. This
made level- or enemy-centered queries miss authored consumers such as
atmospheric NPC rows, spawner entries, mission runtime assets, quest tracking,
map sublevel enemy lists, and interactive collections.

## Change

`tools/endfield_source_graph.py` now emits reverse lookup edges for selected
decoded-config relationships:

- `level_has_atmospheric_npc`
- `enemy_used_by_spawner_entry`
- `enemy_used_by_map_sublevel_brief`
- `level_has_mission_runtime`
- `level_has_quest_tracking`
- `level_has_interactive_collection`

Each reverse edge is emitted next to the corresponding forward edge and keeps
the same evidence/data payload where the forward edge had one.

## Validation

Syntax:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Targeted temporary DB:

```bat
tmp/decoded_level_enemy_reverse_minimal.sqlite
```

The DB was built by running only `ingest_decoded_config_semantics()`.
Forward/reverse counts matched:

- `atmospheric_npc_in_level`: 7,760 / reverse 7,760
- `spawner_enemy_uses_enemy`: 1,057 / reverse 1,057
- `map_sublevel_brief_has_enemy`: 1,009 / reverse 1,009
- `mission_runtime_in_level`: 813 / reverse 813
- `quest_tracking_in_level`: 2,755 / reverse 2,755
- `interactive_collection_in_level`: 935 / reverse 935

Sample reverse rows showed `enemy:eny_0007_mimicw` linking back to multiple
`map_sublevel_brief:*` rows with the original `enemyIdSet[...]` evidence.

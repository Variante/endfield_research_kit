# System Tip Reverse Source-Graph Recovery - 2026-07-03

## Scope

System-tip tables already linked loading tips, hyperlink text rows, and death
tips to missions, wiki entries, enemies, and dungeons. This pass added reverse
edges so those gameplay nodes can answer which system-tip text references or
depends on them.

## Added Reverse Edges

- `mission_unlocks_loading_tip`
- `wiki_entry_used_by_hyperlink`
- `enemy_has_death_tip`
- `dungeon_has_death_tip`

## Validation

Focused temp graph:
`tmp/system_tip_reverse_validate.sqlite`

Counts from `ingest_system_tip_semantics()`:

| Forward edge | Count | Reverse edge | Count |
| --- | ---: | --- | ---: |
| `loading_tip_unlocks_after_mission` | 98 | `mission_unlocks_loading_tip` | 98 |
| `hyperlink_jumps_to_wiki` | 32 | `wiki_entry_used_by_hyperlink` | 32 |
| `death_tip_related_enemy` | 86 | `enemy_has_death_tip` | 86 |
| `death_tip_related_dungeon` | 82 | `dungeon_has_death_tip` | 82 |

CLI smoke checks:

- `python tools\endfield_source_graph.py query e1m1 --kind mission --db tmp\system_tip_reverse_validate.sqlite --limit 12`
  showed loading tips unlocked after mission `e1m1`.
- `python tools\endfield_source_graph.py query dung01_actmonster01 --kind dungeon --db tmp\system_tip_reverse_validate.sqlite --limit 12`
  showed `dungeon_has_death_tip`.
- `python tools\endfield_source_graph.py query eny_0007_mimicw --kind enemy --db tmp\system_tip_reverse_validate.sqlite --limit 12`
  showed `enemy_has_death_tip`.

SQL sampling showed hyperlink reverse rows such as
`wiki_entry:wiki_tut_bat_airborne -> hyperlink_text:ba.airborne` through
`wiki_entry_used_by_hyperlink`.

`python -m py_compile tools\endfield_source_graph.py` passed.

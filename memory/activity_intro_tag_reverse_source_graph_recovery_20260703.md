# Activity Intro Mission And Tag Reverse Source-Graph Recovery - 2026-07-03

## Scope

`ActivityTable` already linked activities to intro mission/quest IDs and
activity tags. Nearby activity task, stage, reward, condition, and system-jump
relationships already had reverse graph coverage. This pass added the missing
reverse edges for the core activity intro/tag relationships.

## Added Reverse Edges

- `mission_used_by_activity_intro`
- `activity_tag_used_by_activity`

## Validation

Focused temp graph:
`tmp/activity_intro_tag_reverse_validate.sqlite`

Counts from `ingest_activity_achievement_semantics()`:

| Forward edge | Count | Reverse edge | Count |
| --- | ---: | --- | ---: |
| `activity_intro_mission` | 13 | `mission_used_by_activity_intro` | 13 |
| `activity_has_tag` | 63 | `activity_tag_used_by_activity` | 63 |

CLI smoke checks:

- `python tools\endfield_source_graph.py query activity_tag_chartrial --kind activity_tag --db tmp\activity_intro_tag_reverse_validate.sqlite --limit 12`
  showed character-trial activities through `activity_tag_used_by_activity`.
- `python tools\endfield_source_graph.py query a1m10_q#2 --kind mission --db tmp\activity_intro_tag_reverse_validate.sqlite --limit 12`
  showed `activity_phototaking_universe` through
  `mission_used_by_activity_intro`.

`python -m py_compile tools\endfield_source_graph.py` passed.

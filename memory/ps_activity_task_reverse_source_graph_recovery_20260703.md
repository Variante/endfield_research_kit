# PS Activity Task Reverse Source-Graph Recovery - 2026-07-03

## Scope

The activity catalog graph already modeled PS activities, PS activity tasks, and
their authored start/end mission windows. This pass added reverse lookup edges
from PS tasks back to PS activities and from missions back to the PS tasks that
start or end at them.

## Added Reverse Edges

- `ps_activity_task_in_activity`
- `mission_used_by_ps_activity_task_start`
- `mission_used_by_ps_activity_task_end`

## Validation

Focused temp graph:
`tmp/ps_activity_task_reverse_validate.sqlite`

Counts from `ingest_activity_catalog_semantics()`:

| Forward edge | Count | Reverse edge | Count |
| --- | ---: | --- | ---: |
| `ps_activity_has_task` | 22 | `ps_activity_task_in_activity` | 22 |
| `ps_activity_task_start_mission` | 11 | `mission_used_by_ps_activity_task_start` | 11 |
| `ps_activity_task_end_mission` | 11 | `mission_used_by_ps_activity_task_end` | 11 |

CLI smoke checks:

- `python tools\endfield_source_graph.py query a1t1 --kind ps_activity_task --db tmp\ps_activity_task_reverse_validate.sqlite --limit 12`
  showed both PS activity membership and mission start/end reverse edges.
- `python tools\endfield_source_graph.py query e1m1 --kind mission --db tmp\ps_activity_task_reverse_validate.sqlite --limit 12`
  showed `mission_used_by_ps_activity_task_start`.

`python -m py_compile tools\endfield_source_graph.py` passed.

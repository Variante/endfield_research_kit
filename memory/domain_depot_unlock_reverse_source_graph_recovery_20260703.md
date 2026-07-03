# Domain Depot Unlock Reverse Source-Graph Recovery - 2026-07-03

## Scope

`DomainDepotTable.unlockQuestId` already linked each depot to the mission/quest
that unlocks it. This pass adds the reverse edge so mission queries can discover
which domain depot entries they unlock.

## Added Reverse Edge

- `mission_unlocks_domain_depot`

## Validation

Focused temp graph:
`tmp/domain_depot_unlock_reverse_validate.sqlite`

The validation seeded `ingest_domain_depot_semantics()` only.

| Forward edge | Count | Reverse edge | Count |
| --- | ---: | --- | ---: |
| `domain_depot_unlock_quest` | 5 | `mission_unlocks_domain_depot` | 5 |

Observed unlock quests:

- `f1m24_q#2` unlocks `domain_1_lv005_depot_1`
- `f1m24d1_q#2` unlocks four later depot rows

`python -m py_compile tools\endfield_source_graph.py` passed.

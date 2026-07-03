# Battle Pass Business Card Topic Source-Graph Recovery - 2026-07-03

## Scope

`BattlePassSeasonTable` has a `bussinessCardId` field that points at
`BusinessCardTopicTable` entries. The graph previously preserved that value
only as a `business_card_id` alias on the battle-pass season, which made search
work but did not expose the authored season-to-card-topic relationship.

## Added Semantics

- `battlepass_season_business_card_topic`
- `business_card_topic_used_by_battlepass_season`

The existing alias is still emitted for compatibility.

## Validation

Focused temp graph:
`tmp/battlepass_business_card_validate.sqlite`

The validation ingested both `ingest_profile_social_semantics()` and
`ingest_battlepass_semantics()` so topic definitions and season references were
visible together.

Counts:

| Edge kind | Count |
| --- | ---: |
| `battlepass_season_business_card_topic` | 4 |
| `business_card_topic_used_by_battlepass_season` | 4 |

Validated pairs:

| Season | Business card topic |
| --- | --- |
| `bp_01` | `business_card_topic_bp_1` |
| `bp_02` | `business_card_topic_bp_1_1` |
| `bp_03` | `business_card_topic_bp_1_2` |
| `bp_04` | `business_card_topic_bp_1_3` |

CLI smoke checks:

- `python tools\endfield_source_graph.py query business_card_topic_bp_1 --kind business_card_topic --db tmp\battlepass_business_card_validate.sqlite --limit 12`
  showed both the `BusinessCardTopicTable` definition and the `bp_01` season
  usage.
- `python tools\endfield_source_graph.py query bp_01 --kind battlepass_season --db tmp\battlepass_business_card_validate.sqlite --limit 12`
  showed `battlepass_season_business_card_topic`.
- `python tools\endfield_source_graph.py query business_card_topic_bp_1_3 --kind business_card_topic --db tmp\battlepass_business_card_validate.sqlite --limit 12`
  showed the `bp_04` reverse usage.

`python -m py_compile tools\endfield_source_graph.py` passed.

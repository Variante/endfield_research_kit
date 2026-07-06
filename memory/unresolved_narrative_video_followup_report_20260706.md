# Unresolved Narrative Video Follow-Up Report - 2026-07-06

## Scope

This pass added a source-graph follow-up output for the remaining unresolved
narrative-video audit groups. The underlying graph already had nodes and edges
for unresolved candidates; the missing piece was a compact query-oriented
report that separates generated-story-target candidates from likely no-target
or standalone candidates.

Generated outputs:

- `reports/source_graph/unresolved_narrative_video_candidates.json`
- `reports/source_graph/unresolved_narrative_video_candidates.md`

These files are generated reports and remain ignored by git. The durable
conclusion lives here in `memory/`.

## Current Counts

Validation against the current
`reports/source_graph/endfield_source_graph.sqlite` produced:

| Metric | Count |
| --- | ---: |
| unresolved candidate groups | 7 |
| `hasGeneratedStoryTarget` groups | 3 |
| `noGeneratedStoryTarget` groups | 4 |

Actionable generated-story-target stems:

- `cs_video_dlg_e1m2_1`
- `cs_video_e1m3_3`
- `cs_video_e6m1_1`

No-generated-target stems:

- `cs_video_dlg_e9m2_3`
- `cs_video_e2m8_2`
- `remotecomm_e1m2_2`
- `remotecomm_e1m2_3`

## Validation

Commands:

```bat
python -m py_compile tools\endfield_source_graph.py
python -c "import sqlite3,json; from tools.endfield_source_graph import DEFAULT_DB, emit_unresolved_narrative_video_candidates, GRAPH_DIR; conn=sqlite3.connect(DEFAULT_DB); conn.row_factory=sqlite3.Row; emit_unresolved_narrative_video_candidates(conn); conn.close(); payload=json.loads((GRAPH_DIR/'unresolved_narrative_video_candidates.json').read_text(encoding='utf-8')); print(payload['count'], payload['statusCounts'], payload['actionableCount']); print([item['stem'] for item in payload['actionable']])"
```

Output:

```text
7 {'hasGeneratedStoryTarget': 3, 'noGeneratedStoryTarget': 4} 3
['cs_video_dlg_e1m2_1', 'cs_video_e1m3_3', 'cs_video_e6m1_1']
```

## Interpretation

This report does not attach or suppress videos. It narrows P8 cleanup by making
the three unresolved groups with existing generated story targets immediately
visible, while keeping the four no-target groups separate for later false-match
or standalone-key review.

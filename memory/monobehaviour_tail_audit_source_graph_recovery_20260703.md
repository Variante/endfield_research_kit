# MonoBehaviour Tail Audit Source-Graph Recovery - 2026-07-03

## Scope

This pass adds `reports/monobehaviour_frontier_tail_audit.json` to the source
graph. The audit ranks MonoBehaviour layout types whose residual tails remain
important for schema recovery, then links those ranked/watch types back to the
frontier groups they affect.

The graph records audit evidence only. It does not decode additional
MonoBehaviour payload bytes or promote any schema interpretation by itself.

## Added Node Kinds

- `monobehaviour_frontier_tail_audit_report`
- `monobehaviour_tail_audit_type`
- `monobehaviour_tail_audit_band`
- `monobehaviour_tail_audit_recommendation`

Existing node kinds reused by this pass:

- `monobehaviour_schema`
- `monobehaviour_decode_error`
- `monobehaviour_frontier_group`

## Added Edges

- `monobehaviour_tail_audit_ranked_type`
- `monobehaviour_tail_audit_watch_type`
- `monobehaviour_tail_type_in_band`
- `monobehaviour_tail_type_recommendation`
- `monobehaviour_tail_type_top_schema`
- `monobehaviour_tail_type_top_error`
- `monobehaviour_tail_type_affects_group`
- `monobehaviour_frontier_group_has_tail_type`

## Validation

Commands:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Focused temp graph:
`tmp/monobehaviour_tail_audit_validate.sqlite`

The validation seeded `ingest_monobehaviour_frontier_tail_audit()`.

| Edge | Count |
| --- | ---: |
| `monobehaviour_tail_audit_ranked_type` | 18 |
| `monobehaviour_tail_audit_watch_type` | 14 |
| `monobehaviour_tail_type_in_band` | 18 |
| `monobehaviour_tail_type_recommendation` | 32 |
| `monobehaviour_tail_type_top_schema` | 21 |
| `monobehaviour_tail_type_top_error` | 18 |
| `monobehaviour_tail_type_affects_group` | 78 |
| `monobehaviour_frontier_group_has_tail_type` | 78 |

Focused node counts:

| Node kind | Count |
| --- | ---: |
| `monobehaviour_frontier_tail_audit_report` | 1 |
| `monobehaviour_tail_audit_type` | 32 |
| `monobehaviour_tail_audit_band` | 4 |
| `monobehaviour_tail_audit_recommendation` | 6 |
| `monobehaviour_schema` | 4 |
| `monobehaviour_decode_error` | 1 |
| `monobehaviour_frontier_group` | 8 |

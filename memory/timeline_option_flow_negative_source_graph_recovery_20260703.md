# Timeline Option-Flow Negative Source Graph Recovery - 2026-07-03

## Context

`reports/timeline_option_flow_audit_CN_interesting.json` captures 14 inferred
response groups where static adjacency looks tempting but IL2CPP/runtime field
evidence says the candidate response lines should not be promoted without a
runtime rule. The source graph previously had runtime jump route evidence and
conflict diagnostics, but not this newer negative option-flow audit.

This evidence is diagnostic. It explains why the current Story recovery should
remain conservative for these groups; it must not delete or override existing
option route edges.

## Change

`tools/endfield_source_graph.py` now ingests the timeline option-flow audit
after runtime option-route audits.

New node kinds:

- `timeline_option_flow_audit_group`
- `il2cpp_option_flow_fact`
- `option_flow_verdict`

New edges:

- `has_timeline_option_flow_audit`
- `story_has_option_flow_audit`
- `option_group_has_option_flow_audit`
- `timeline_option_flow_audit_has_il2cpp_fact`
- `option_flow_audit_uses_il2cpp_fact`
- `option_flow_audit_has_verdict`
- `option_flow_audit_candidate_option`
- `option_flow_candidate_option_line`
- `option_flow_audit_candidate_line`
- `option_flow_audit_window_line`

Audit groups are keyed by `storyKey:group:<group>`. Candidate options and lines
link to existing `option` and `line` node kinds, while the IL2CPP facts and
runtime verdict remain separate diagnostic nodes.

## Validation

Static checks passed:

```bat
python -B -m py_compile tools\endfield_source_graph.py
git diff --check -- tools/endfield_source_graph.py
```

A focused temporary database called only
`ingest_timeline_option_flow_audit()` against the real audit JSON. Results:

| Item | Count |
|---|---:|
| `timeline_option_flow_audit_group` nodes | 14 |
| `il2cpp_option_flow_fact` nodes | 14 |
| `option_flow_verdict` nodes | 1 |
| `option` nodes | 33 |
| `line` nodes | 46 |
| `option_group` nodes | 14 |
| `story` nodes | 11 |
| `has_timeline_option_flow_audit` edges | 14 |
| `story_has_option_flow_audit` edges | 14 |
| `option_group_has_option_flow_audit` edges | 14 |
| `option_flow_audit_candidate_option` edges | 33 |
| `option_flow_candidate_option_line` edges | 33 |
| `option_flow_audit_candidate_line` edges | 33 |
| `option_flow_audit_window_line` edges | 46 |
| `timeline_option_flow_audit_has_il2cpp_fact` edges | 14 |
| `option_flow_audit_uses_il2cpp_fact` edges | 196 |
| `option_flow_audit_has_verdict` edges | 14 |

All 14 verdict edges point to
`option_flow_verdict:strictOptionRowsButAllZeroCandidateRuntimeField`, and all
33 candidate option edges have a corresponding candidate-line edge.

## Notes

The `option_flow_audit_uses_il2cpp_fact` count is 196 because each of the 14
audit groups references the same 14 IL2CPP option-flow facts. This keeps the
group-level negative conclusion self-contained when querying any one group.

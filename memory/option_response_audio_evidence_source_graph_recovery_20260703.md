# Option Response Audio Evidence Source Graph Recovery - 2026-07-03

## Scope

The source graph now ingests
`reports/option_response_audio_evidence_CN.json` as diagnostic evidence for
inferred option response groups. This bridges option-response candidates to
timeline placement, anchor lines, candidate lines, options, speakers, audio ids,
AudioDialog path evidence, and boolean audit checks.

This report remains diagnostic. It does not emit `option_first_line`,
`option_path_line`, route, or branch-promotion edges.

## Graph Additions

New node kinds:

- `option_response_audio_audit`
- `option_response_audio_group`
- `option_response_audio_check`

New edges:

- `defines_option_response_audio_audit`
- `option_response_audio_audit_has_group`
- `story_has_option_response_audio_group`
- `mission_has_option_response_audio_group`
- `option_group_has_response_audio_evidence`
- `response_audio_anchor_line`
- `response_audio_candidate_line`
- `response_audio_candidate_option`
- `response_audio_anchor_line_audio`
- `response_audio_candidate_line_audio`
- `response_audio_anchor_speaker`
- `response_audio_candidate_speaker`
- `response_audio_group_timeline`
- `response_audio_group_check`

## Validation

Static check:

```bat
python -B -m py_compile tools\endfield_source_graph.py
```

Focused temp graph using `ingest_webui_story()`,
`ingest_timeline_line_orders()`, and
`ingest_option_response_audio_evidence()`:

- `option_response_audio_audit`: 1
- `option_response_audio_group`: 20
- `option_response_audio_check`: 11
- `response_audio_candidate_option`: 47
- `response_audio_candidate_line`: 47
- `response_audio_anchor_line`: 20
- `response_audio_candidate_line_audio`: 47
- `response_audio_anchor_line_audio`: 20
- candidate audio links with `.wem` AudioDialog paths in edge data: 45
- candidate audio links with line audio ids but no AudioDialog path:
  `dlg_e1m10_7_007` and `dlg_e1m10_7_008`

Check counts:

- `timelineStartMonotonic:true`: 19
- `timelineStartMonotonic:false`: 1
- `audioDialogKeyMonotonic:true`: 15
- `audioDialogKeyMonotonic:false`: 5
- `candidatesAllAfterAnchor:true`: 19
- `candidatesAllAfterAnchor:false`: 1
- `speakerConsistent:true`: 13
- `speakerConsistent:false`: 7
- `anchorIsDifferentSpeaker:true`: 3
- `anchorIsDifferentSpeaker:false`: 17
- `timelinesSameAsAnchor:true`: 20

Query checks:

- `dlg_c28m3_23#group:1 --kind option_response_audio_group` resolves the
  anchor `dlg_c28m3_23_008`, options
  `option_dlg_c28m3_23_1_001/002`, candidate lines
  `dlg_c28m3_23_009/010`, timeline `dlgtl_c28m3_23_sub_1`, and the audit
  check nodes.
- `au_dlg_c28m3_23_009 --kind audio` shows both existing story line usage and
  `response_audio_candidate_line_audio`.
- `timelineStartMonotonic:true --kind option_response_audio_check` returns the
  19 groups that passed the timeline-start monotonicity check.

## Interpretation

This adds graph-addressable corroboration for option response recovery. The
strongest groups are those where candidates share the anchor timeline, occur
after the anchor, have monotonic timeline starts, and carry candidate-line audio
ids. The graph still treats this as evidence for review, not as an automatic
branch route or response-line promotion rule.
